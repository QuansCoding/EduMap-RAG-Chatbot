import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from psycopg.types.json import Jsonb

from app.ai.provider import AIProviderError, get_ai_provider
from app.auth import CurrentUser, get_current_user
from app.config import get_settings
from app.db import get_conn
from app.schemas import CreateSessionRequest, SendMessageRequest
from app.services.permissions import require_member
from app.services.rag import answer_question
from app.services.usage import check_and_record_usage

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["chat"])

# FIX: "created at" (no underscore) is parsed by SQL as column `created` aliased to `at`.
MESSAGE_COLUMNS = "id, sender, content, key_points, citations, found_in_materials, created_at"


def _get_owned_session(conn, session_id: UUID, user: CurrentUser) -> dict:
    session = conn.execute(
        # FIX: table is chat_sessions (plural). This query runs first, so it was THE 500.
        "SELECT id, workspace_id, title FROM chat_sessions WHERE id = %s AND user_id = %s",
        (session_id, user.id),
    ).fetchone()
    if session is None:  # doesn't exist OR belongs to someone else (404)
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chat session not found")
    require_member(conn, session["workspace_id"], user.id)  # removed members lose access
    return session

# FIX: path was /chat/session; the guide (and the frontend in Part 11) uses /chat/sessions.
@router.post("/workspaces/{workspace_id}/chat/sessions", status_code=status.HTTP_201_CREATED)
def create_session(workspace_id: UUID, body: CreateSessionRequest, user: CurrentUser = Depends(get_current_user)):
    with get_conn() as conn:
        require_member(conn, workspace_id, user.id)
        return conn.execute(
            """
            INSERT INTO chat_sessions (workspace_id, user_id, title)
            VALUES (%s, %s, %s)
            RETURNING id, title, created_at
            """,
            (workspace_id, user.id, (body.title or "New chat").strip() or "New chat"),
        ).fetchone()


@router.get("/workspaces/{workspace_id}/chat/sessions")
def list_my_sessions(workspace_id: UUID, user: CurrentUser = Depends(get_current_user)):
    with get_conn() as conn:
        require_member(conn, workspace_id, user.id)
        return conn.execute(
            """
            SELECT id, title, created_at FROM chat_sessions
            WHERE workspace_id = %s AND user_id = %s
            ORDER BY created_at DESC
            """,
            (workspace_id, user.id),
        ).fetchall()

@router.get("/chat/sessions/{session_id}/messages")
def list_messages(session_id: UUID, user: CurrentUser = Depends(get_current_user)):
    with get_conn() as conn:
        _get_owned_session(conn, session_id, user)
        return conn.execute(
            f"SELECT {MESSAGE_COLUMNS} FROM messages WHERE session_id = %s ORDER BY created_at",
            (session_id,),
        ).fetchall()


@router.post("/chat/sessions/{session_id}/messages")
def send_message(session_id: UUID, body: SendMessageRequest, user: CurrentUser = Depends(get_current_user)):
    settings = get_settings()
    question = body.content.strip()
    if not question:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Message cannot be blank")

    # Transaction 1, checks & history.
    # Released before slow AI calls

    with get_conn() as conn:
        session = _get_owned_session(conn, session_id, user)
        check_and_record_usage(conn, user, "chat")
        history = conn.execute(
            """
            SELECT sender, content FROM (
                SELECT sender, content, created_at FROM messages
                WHERE session_id = %s ORDER BY created_at DESC LIMIT 10
            ) recent ORDER BY created_at
            """,
            (session_id,),
        ).fetchall()

    # FIX: everything below was indented inside the `with` above, so the pooled
    # connection was held open across the whole (slow) AI call, and a SECOND
    # connection was opened while still holding the first. With max_size=5 that
    # exhausts the pool under very little traffic. De-indented to match the guide:
    # transaction 1 closes here, the AI runs with no connection held.

    # AI work (several seconds, no DB connection held)
    try:
        result, citations = answer_question(get_ai_provider(), settings, session["workspace_id"], question, history)
    except AIProviderError:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "The AI service is busy or unavailable right now. Please try again in a minute.",
        )

    # Transaction 2: save both messages atomically
    with get_conn() as conn:
        user_message = conn.execute(
            f"INSERT INTO messages (session_id, sender, content) VALUES (%s, 'user', %s) RETURNING {MESSAGE_COLUMNS}",
            (session_id, question),
        ).fetchone()
        assistant_message = conn.execute(
            f"""
            INSERT INTO messages (session_id, sender, content, key_points, citations, found_in_materials)
            VALUES (%s, 'assistant', %s, %s, %s, %s)
            RETURNING {MESSAGE_COLUMNS}
            """,
            (session_id, result.answer, Jsonb(result.key_points), Jsonb(citations), result.found_in_materials),
        ).fetchone()
        if session["title"] == "New chat":  # auto-title from the first question
            conn.execute("UPDATE chat_sessions SET title = %s WHERE id = %s", (question[:60], session_id))

    return {"user_message": user_message, "assistant_message": assistant_message}


@router.post("/chat/messages/{message_id}/share", status_code=status.HTTP_201_CREATED)
def share_message(message_id: UUID, user: CurrentUser = Depends(get_current_user)):
    """Copy ONE assistant answer (and the question before it) into the group's Shared Insights."""
    with get_conn() as conn:
        message = conn.execute(
            """
            SELECT m.id, m.session_id, m.sender, m.content, m.key_points, m.citations,
                   m.found_in_materials, m.created_at, s.workspace_id, s.user_id
            FROM messages m JOIN chat_sessions s ON s.id = m.session_id
            WHERE m.id = %s
            """,
            (message_id,),
        ).fetchone()
        if message is None or str(message["user_id"]) != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Message not found")
        if message["sender"] != "assistant":
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only AI answers can be shared")
        require_member(conn, message["workspace_id"], user.id)

        question = conn.execute(
            """
            SELECT content FROM messages
            WHERE session_id = %s AND sender = 'user' AND created_at < %s
            ORDER BY created_at DESC LIMIT 1
            """,
            (message["session_id"], message["created_at"]),
        ).fetchone()

        conn.execute(
            """
            INSERT INTO shared_insights
                (workspace_id, shared_by, source_message_id, question, answer, key_points, citations, found_in_materials)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (source_message_id) DO NOTHING
            """,
            (
                message["workspace_id"],
                user.id,
                message_id,
                question["content"] if question else "(question unavailable)",
                message["content"],
                Jsonb(message["key_points"]),
                Jsonb(message["citations"]),
                message["found_in_materials"],
            ),
        )
    return {"shared": True}