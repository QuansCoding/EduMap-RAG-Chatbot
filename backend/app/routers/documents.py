from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status

from app.auth import CurrentUser, get_current_user
from app.config import get_settings
from app.db import get_conn
from app.ingestion.loaders import UnsupportedFileTypeError, get_loader
from app.services.ingestion import process_document
from app.services.permissions import require_member
from app.services.usage import check_and_record_usage

router = APIRouter(prefix="/api", tags=["documents"])

ALLOWED_FILE_TYPES = {"syllabus", "slides", "textbook", "notes", "other"}


@router.post("/workspaces/{workspace_id}/documents", status_code=status.HTTP_202_ACCEPTED)
def upload_document(
    workspace_id: UUID,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    file_type: str = Form("other"),
    user: CurrentUser = Depends(get_current_user),
):
    settings = get_settings()
    filename = file.filename or "upload"

    # Validate cheaply BEFORE doing work
    if file_type not in ALLOWED_FILE_TYPES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,f"file_type must be one of the {sorted(ALLOWED_FILE_TYPES)}")
    try:
        get_loader(filename, settings.max_pdf_pages)
    except UnsupportedFileTypeError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))

    max_bytes = settings.max_upload_mb * 1024 * 1024
    data = file.file.read(max_bytes + 1)  # read at most limit + 1 bytes (never load huge file into memory)
    if len(data) > max_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, f"File exceeds {settings.max_upload_mb} MB")
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "File is empty")

    title = filename.rsplit(".", 1)[0][:255]

    with get_conn() as conn:
        require_member(conn, workspace_id, user.id)
        check_and_record_usage(conn, user, "upload")
        document = conn.execute(
            """
            INSERT INTO documents (workspace_id, uploaded_by, title, file_type, status)
            VALUES (%s, %s, %s, %s, 'processing')
            RETURNING id, title, file_type, status, error_message, page_count, chunk_count, created_at
            """,
            (workspace_id, user.id, title, file_type),
        ).fetchone()

    background_tasks.add_task(process_document, document["id"], workspace_id, title, filename, data)
    return {**document, "uploaded_by_email": user.email}

@router.get("/workspaces/{workspace_id}/documents")
def list_documents(workspace_id: UUID, user: CurrentUser = Depends(get_current_user)):
    with get_conn() as conn:
        require_member(conn, workspace_id, user.id)
        return conn.execute(
            """
            SELECT d.id, d.title, d.file_type, d.status, d.error_message, d.page_count,
                   d.chunk_count, d.created_at, u.email AS uploaded_by_email
            FROM documents d
            LEFT JOIN users u ON u.id = d.uploaded_by
            WHERE d.workspace_id = %s
            ORDER BY d.created_at DESC
            """,
            (workspace_id,),
        ).fetchall()

@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: UUID, user: CurrentUser = Depends(get_current_user)):
    with get_conn() as conn:
        document = conn.execute(
            "SELECT workspace_id, uploaded_by FROM documents WHERE id = %s", (document_id,)
        ).fetchone()
        if document is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
        role = require_member(conn, document["workspace_id"], user.id)
        if role != "owner" and str(document["uploaded_by"]) != user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the uploader or workspace owner can delete this")
        # ON DELETE CASCADE removes all its chunks and their vector
        conn.execute("DELETE FROM documents where id = %s", (document_id,))