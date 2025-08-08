from typing import Dict, Any, Optional
import logging

from .logging import LOGGER

logger = LOGGER(__name__)

class MongoDBManager:
    """No-database manager - memory only for simplicity"""
    
    def __init__(self):
        self._connected = False
        logger.info("Database disabled - using memory-only storage")
    
    def is_connected(self) -> bool:
        """Always return False since no database"""
        return False
    
    def store_video_info(self, url: str, video_info: Dict[str, Any]):
        """No-op - database disabled"""
        pass
    
    def get_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """Always return None - no database"""
        return None
    
    def store_download_data(self, url: str, quality: str, format_type: str, download_data: Dict[str, Any]):
        """No-op - database disabled"""
        pass
    
    def get_download_data(self, url: str, quality: str, format_type: str) -> Optional[Dict[str, Any]]:
        """Always return None - no database"""
        return None
    
    def cleanup_expired(self):
        """No-op - no database to clean"""
        pass
