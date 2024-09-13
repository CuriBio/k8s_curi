from models.models import NotificationResponse, SaveNotificationRequest, SaveNotificationResponse
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

    async def get_all(self) -> list[NotificationResponse]:
        query = "SELECT * FROM notifications"

        async with self.pool.acquire() as con:
            notifications = await con.fetch(query)

        return [NotificationResponse(**dict(notification)) for notification in notifications]
