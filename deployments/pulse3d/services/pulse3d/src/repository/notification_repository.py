from models.models import (
    NotificationMessageResponse,
    NotificationResponse,
    NotificationType,
    SaveNotificationRequest,
    SaveNotificationResponse,
)
import asyncpg


class NotificationRepository:
    def __init__(self, pool: asyncpg.pool.Pool):
        self.pool = pool

    async def create(self, notification: SaveNotificationRequest) -> SaveNotificationResponse:
        async with self.pool.acquire() as con:
            async with con.transaction():
                insert_notification_query = "INSERT INTO notifications (subject, body, notification_type) VALUES ($1, $2, $3) RETURNING id"

                notification_id = await con.fetchval(
                    insert_notification_query,
                    notification.subject,
                    notification.body,
                    notification.notification_type,
                )

                select_customer_ids_query = "SELECT id FROM customers"
                select_user_ids_query = "SELECT id FROM users"

                match notification.notification_type:
                    case NotificationType.CUSTOMERS_AND_USERS:
                        audience_sub_query = f"({select_customer_ids_query} UNION {select_user_ids_query})"
                    case NotificationType.CUSTOMERS:
                        audience_sub_query = f"({select_customer_ids_query})"
                    case NotificationType.USERS:
                        audience_sub_query = f"({select_user_ids_query})"

                insert_notification_messages_query = f"""
                    INSERT INTO notification_messages (notification_id, recipient_id)
                    SELECT '{notification_id}', id from {audience_sub_query} audience;
                """

                await con.execute(insert_notification_messages_query)

        return SaveNotificationResponse(id=notification_id)

    async def get_all(self) -> list[NotificationResponse]:
        query = "SELECT * FROM notifications"

        async with self.pool.acquire() as con:
            notifications = await con.fetch(query)

        return [NotificationResponse(**dict(notification)) for notification in notifications]

    async def get_notification_messages(
        self, account_id: str, notification_message_id: str
    ) -> list[NotificationMessageResponse]:
        query = f"""
            SELECT m.id, m.created_at, m.viewed_at, n.subject, n.body
            FROM notification_messages m, notifications n
            WHERE m.recipient_id = '{account_id}'
            AND m.notification_id = n.id
        """

        if notification_message_id:
            query += f" AND m.id = '{notification_message_id}'"

        async with self.pool.acquire() as con:
            notification_messages = await con.fetch(query)

        return [
            NotificationMessageResponse(**dict(notification_message))
            for notification_message in notification_messages
        ]
