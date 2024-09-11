from models.models import SaveNotificationRequest, SaveNotificationResponse
import asyncpg


class NotificationRepository:
    def __init__(self, pool: asyncpg.pool.Pool):
        self.pool = pool

    async def create(self, notification: SaveNotificationRequest) -> SaveNotificationResponse:
        query = (
            "INSERT INTO notifications (subject, body, notification_type) VALUES ($1, $2, $3) RETURNING id"
        )

        async with self.pool.acquire() as con:
            notification_id = await con.fetchval(
                query, notification.subject, notification.body, notification.notification_type
            )

        return SaveNotificationResponse(id=notification_id)
