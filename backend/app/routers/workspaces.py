from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import CurrentUser, get_current_user
from app.db import get_conn
from app.schemas import CreateWorkspaceRequest, JoinWorkspaceRequest
from app.services.invite_codes import generate_invite_code, normalize_invite_code
from app.services.permissions import require_member

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])

@router.post("", status_code=status.HTTP_201_CREATED)
def create_workspace(body: CreateWorkspaceRequest, user: CurrentUser = Depends(get_current_user)):
    name = body.name.strip()
    if not name:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,"Name cannot be blank")

    # Both INSERTs run in one transaction
    # Never end up with an owner-less workspace.
    with get_conn() as conn:
        workspace = conn.execute(
            """
            INSERT INTO workspaces (name, invite_code, created_by)
            VALUES (%s, %s, %s)
            RETURNING id, name, invite_code, created_at
            """,
            (name, generate_invite_code(), user.id)
        ).fetchone()
        conn.execute(
            "INSERT INTO workspace_members (workspace_id, user_id, role) VALUES (%s, %s, 'owner')",
            (workspace["id"], user.id),
        )
    return {**workspace, "role": "owner", "member_count": 1}

@router.get("")
def list_my_workspaces(user: CurrentUser = Depends(get_current_user)):
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT w.id, w.name, w.invite_code, w.created_at, m.role,
                   (SELECT count(*) FROM workspace_members x WHERE x.workspace_id = w.id) AS member_count
            FROM workspaces w
            JOIN workspace_members m ON m.workspace_id = w.id
            WHERE m.user_id = %s
            ORDER BY w.created_at DESC
            """,
            (user.id,),
        ).fetchall()

@router.post("/join")
def join_workspace(body: JoinWorkspaceRequest, user: CurrentUser = Depends(get_current_user)):
    code = normalize_invite_code(body.invite_code)
    with get_conn() as conn:
        workspace = conn.execute(
            "SELECT id, name, invite_code, created_at FROM workspaces WHERE invite_code = %s",
            (code,),
        ).fetchone()
        if workspace is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Invalid invite code")

        # ON CONFLICT DO NOTHING makes joining idempotent (joining twice is harmless).
        conn.execute(
            """
            INSERT INTO workspace_members (workspace_id, user_id, role)
            VALUES (%s, %s, 'member')
            ON CONFLICT (workspace_id, user_id) DO NOTHING
            """,
            (workspace["id"], user.id),
        )
        role = require_member(conn, workspace["id"], user.id)
    return {**workspace, "role": role}

@router.get("/{workspace_id}")
def get_workspace(workspace_id: UUID, user: CurrentUser = Depends(get_current_user)):
    with get_conn() as conn:
        role = require_member(conn, workspace_id, user.id)
        workspace = conn.execute(
            "SELECT id, name, invite_code, created_at FROM workspaces WHERE id = %s",
            (workspace_id,),
        ).fetchone()
        members = conn.execute(
            """
            SELECT u.id, u.email, u.display_name, m.role, m.joined_at
            FROM workspace_members m
            JOIN users u ON u.id = m.user_id
            WHERE m.workspace_id = %s
            ORDER BY m.joined_at
            """,
            (workspace_id,),
        ).fetchall()
        return {**workspace, "role": role, "members": members, "member_count": len(members)}


@router.get("/{workspace_id}/shared")
def list_shared_insights(workspace_id: UUID, user: CurrentUser = Depends(get_current_user)):
    with get_conn() as conn:
        require_member(conn, workspace_id, user.id)
        return conn.execute(
            """
            SELECT s.id, s.question, s.answer, s.key_points, s.citations,
                   s.found_in_materials, s.created_at, u.email AS shared_by_email
            FROM shared_insights s
            LEFT JOIN users u ON u.id = s.shared_by
            WHERE s.workspace_id = %s
            ORDER BY s.created_at DESC
            LIMIT 50
            """,
            (workspace_id,),
        ).fetchall()