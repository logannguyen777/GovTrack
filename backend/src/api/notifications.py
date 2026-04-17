"""backend/src/api/notifications.py"""

from fastapi import APIRouter

from ..auth import CurrentUser
from ..database import pg_connection
from ..models.schemas import NotificationResponse

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=list[NotificationResponse])
async def list_notifications(user: CurrentUser, unread_only: bool = False):
    """List notifications for the current user."""
    sql = "SELECT * FROM notifications WHERE user_id = $1"
    params: list = [user.sub]
    if unread_only:
        sql += " AND is_read = FALSE"
    sql += " ORDER BY created_at DESC LIMIT 50"

    async with pg_connection() as conn:
        rows = await conn.fetch(sql, *params)
    results = []
    for r in rows:
        d = dict(r)
        # Coerce UUID to str, handle unknown category values
        d["id"] = str(d["id"])
        from ..models.enums import NotificationCategory as _NC

        valid_cats = {c.value for c in _NC}
        if d.get("category") not in valid_cats:
            d["category"] = "info"
        results.append(NotificationResponse(**d))
    return results


@router.patch("/{notification_id}/read")
async def mark_read(notification_id: str, user: CurrentUser):
    """Mark a notification as read."""
    async with pg_connection() as conn:
        await conn.execute(
            "UPDATE notifications SET is_read = TRUE WHERE id = $1 AND user_id = $2",
            notification_id,
            user.sub,
        )
    return {"id": notification_id, "is_read": True}
