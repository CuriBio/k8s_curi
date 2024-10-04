from models.models import (
    NotificationMessageResponse,
    NotificationResponse,
    SaveNotificationRequest,
    SaveNotificationResponse,
)
from repository.notification_repository import NotificationRepository


class NotificationService:
    def __init__(self, repository: NotificationRepository):
        self.repository = repository

    async def create(self, notification: SaveNotificationRequest) -> SaveNotificationResponse:
        result = await self.repository.create(notification)
        return result

    async def get_all(self) -> list[NotificationResponse]:
        notifications = await self.repository.get_all()
        return notifications

    async def get_notification_messages(
        self, account_id: str, notification_message_id: str
    ) -> list[NotificationMessageResponse]:
        notification_messages = await self.repository.get_notification_messages(
            account_id, notification_message_id
        )
        return notification_messages
