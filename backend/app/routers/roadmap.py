from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from psycopg.types.json import Jsonb

from app.ai.provider import AIProviderError, get_ai_provider
from app.auth import CurrentUser, get_current_user
from app.db import get_conn
from app.schemas import GenerateRoadmapRequest, ProgressRequest
from app.services.permissions import require_member, require_owner
from app.services.roadmap import generate_roadmap
from app.services.usage import check_and_record_usage

router = APIRouter(prefix="/api", tags=["roadmap"])

def _fetch_roadmap(conn, workspace_id: UUID, user_id: str) -> list[dict]:
    return conn.execute(
        """
        SELECT r.id, r.week_number, r.title, r.summary, r.topics, r.readings,
               (p.user_id IS NOT NULL) AS completed,
               (SELECT count(*) FROM roadmap_progress x WHERE x.roadmap_item_id = r.id) AS completed_count
        FROM roadmap_items r
        LEFT JOIN roadmap_progress p ON p.roadmap_item_id = r.id AND p.user_id = %s
        WHERE r.workspace_id = %s
        ORDER BY r.week_number
        """,
        (user_id, workspace_id),
    ).fetchall()

@router.get("/workspaces/{workspace_id}/roadmap")
def get_roadmap(workspace_id: UUID, user: CurrentUser = Depends(get_current_user)):
    with get_conn() as conn:
        require_member(conn, workspace_id, user.id)
        return _fetch_roadmap(conn, workspace_id, user.id)


@router.post("/workspaces/{workspace_id}/roadmap/generate")
def generate(workspace_id: UUID, body: GenerateRoadmapRequest, user: CurrentUser = Depends(get_current_user)):
    # transaction 1: permissions, limits, load syllabus text
    with get_conn() as conn:
        require_owner(conn, workspace_id, user.id)
        document = conn.execute(
            "SELECT id, status FROM documents WHERE id = %s AND workspace_id = %s",
            (body.document_id, workspace_id),
        ).fetchone()
        if document is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found in this workspace")
        if document["status"] != "ready":  # FIX: was document["statis"] -> KeyError.
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Document is not ready yet")
        check_and_record_usage(conn, user, "roadmap")
        rows = conn.execute(
            "SELECT content FROM document_chunks WHERE document_id = %s ORDER BY chunk_index",
            # FIX: (x) is just x in parentheses, not a tuple. psycopg needs a sequence
            # of parameters, so the trailing comma is what makes it one.
            (body.document_id,),
        ).fetchall()

    syllabus_text = "\n".join(row["content"] for row in rows)

    # AI call (no connection held)
    try:
        plan = generate_roadmap(get_ai_provider(), syllabus_text)
    except AIProviderError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "The AI service is busy. Please try again shortly")
    if not plan.weeks:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Couldn't find a course schedule in that document")

    # Transaction 2: replace roadmap atomically

    with get_conn() as conn:
        # FIX: table is roadmap_items (plural), and (workspace_id) needed to be a tuple.
        conn.execute("DELETE FROM roadmap_items WHERE workspace_id = %s", (workspace_id,))
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO roadmap_items
                    -- FIX: was "source,document_id" — a stray comma split one column
                    -- into two, giving 8 column names for 7 values.
                    (workspace_id, source_document_id, week_number, title, summary, topics, readings)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    (workspace_id, body.document_id, w.week_number, w.title[:255], w.summary, Jsonb(w.topics), Jsonb(w.readings))
                    for w in plan.weeks
                ],
            )
        return _fetch_roadmap(conn, workspace_id, user.id)


@router.put("/roadmap/items/{item_id}/progress")
def set_progress(item_id: UUID, body: ProgressRequest, user: CurrentUser = Depends(get_current_user)):
    with get_conn() as conn:
        # FIX: table is roadmap_items (plural).
        item = conn.execute("SELECT workspace_id FROM roadmap_items WHERE id = %s", (item_id,)).fetchone()
        if item is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Roadmap item not found")
        require_member(conn, item["workspace_id"], user.id)
        if body.completed:
            conn.execute(
                "INSERT INTO roadmap_progress (user_id, roadmap_item_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (user.id, item_id),
            )
        else:
            conn.execute(
                "DELETE FROM roadmap_progress WHERE user_id = %s AND roadmap_item_id = %s",
                (user.id, item_id),
            )
    return {"completed": body.completed}