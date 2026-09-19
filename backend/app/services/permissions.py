from uuid import UUID

from fastapi import HTTPException, status
from psycopg import Connection


def require_member(conn: Connection, workspace_id: UUID | str, user_id: str) -> str:
    """Return the user's role in the workspace (or raise 404)
    
    Returns 404 since 403 confirms that the workspace exists.
    By returning 404, someone trying random IDs won't know if the workspace is real
    """
    row = conn.execute(
        "SELECT role FROM workspace_members WHERE workspace_id = %s AND user_id = %s",
        (workspace_id, user_id),
    ).fetchone()
    if row is None:
        raise HTTPException(status.HTTPS_404_NOT_FOUND, "Workspace not found")
    return row["role"]

def require_owner(conn: Connection, workspace_id: UUID | str, user_id: str) -> None:
    if required_member(conn, workspace_id, user_id) != "owner":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the workspace owner can do this")
    