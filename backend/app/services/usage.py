from fastapi import HTTPException, status
from psycopg import Connection

from app.auth import CurrentUser
from app.config import get_settings

_USER_LIMIT_FIELDS = {
    "chat": "daily_chat_limit",
    "upload": "daily_upload_limit",
    "roadmap": "daily_roadmap_limit",
}

def check_and_record_usage(conn: Connection, user: CurrentUser, kind: str) -> None:
    """Enforces per-user and global limits over a 24hr window, then records the event.
    
    Recording BEFORE the AI call means failed AI calls can still count.
    failed calls can still consume provider quota
    """
    settings = get_settings()
    if user.email and user.email.lower() == settings.demo_email.lower():
        user_limit = settings.demo_daily_limit
    else:
        user_limit = getattr(settings, _USER_LIMIT_FIELDS[kind])

    row = conn.execute(
        """
        SELECT
            count(*) FILTER (WHERE user_id = %s AND kind = %s) AS mine,
            count(*)                                           AS total
        FROM usage_events
        WHERE created_at > now() - interval '24 hours'
        """,
        (user.id, kind),
    ).fetchone()

    if row["mine"] >= user_limit:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Daily{kind} limit reached ({user_limit} per 24 hours). Please try again later.",
        )
    if row["total"] >= settings.global_daily_ai_limit:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "EduMap has reached its daily AI budget. Please try again tomorrow.",
        )

    conn.execute("INSERT INTO user_events (user_id, kind) VALUES (%s, %s)", (user.id, kind))
    