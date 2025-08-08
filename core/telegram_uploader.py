import logging
from typing import Optional

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID

logger = logging.getLogger(__name__)

class TelegramUploader:
    """Simplified Telegram uploader - disabled for no external dependencies"""
    
    def __init__(self):
        logger.info("Telegram uploader disabled - no external dependencies")
    
    def upload_video(self, video_url: str, title: str) -> Optional[str]:
        """Upload disabled - return None"""
        logger.info("Telegram upload disabled")
        return None
    
    def test_connection(self) -> bool:
        """Connection test disabled"""
        return False
