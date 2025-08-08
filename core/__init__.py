"""
YouTube Downloader API Core Modules
Professional Flask-based YouTube video downloader with advanced features
"""

__version__ = "1.0.0"
__author__ = "YouTube Downloader API"

# Core module imports
from .cache_manager import SmartCacheManager
from .database_manager import MongoDBManager
from .youtube_processor import YouTubeProcessor
from .telegram_uploader import TelegramUploader
from .proxy_manager import ProxyManager

__all__ = [
    'SmartCacheManager',
    'MongoDBManager', 
    'YouTubeProcessor',
    'TelegramUploader',
    'ProxyManager'
]
