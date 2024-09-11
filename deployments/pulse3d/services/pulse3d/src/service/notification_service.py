from models.models import SaveNotificationRequest, SaveNotificationResponse
from repository.notification_repository import NotificationRepository


class NotificationService:
    def __init__(self, repository: NotificationRepository):
        self.repository = repository

    async def create(self, notification: SaveNotificationRequest) -> SaveNotificationResponse:
        result = await self.repository.create(notification)
        return result
