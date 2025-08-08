import os
from datetime import timedelta

class Config:
    """Application configuration"""
    
    # Flask configuration
    SECRET_KEY = os.getenv('SESSION_SECRET', 'dev-secret-key-change-in-production')
    
    # MongoDB configuration for tracking Telegram files only
    MONGO_DB_URI = os.getenv('MONGO_DB_URI')
    
    # Telegram configuration for primary storage
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')
    
    # Rate limiting configuration
    RATE_LIMIT_PER_MINUTE = int(os.getenv('RATE_LIMIT_PER_MINUTE', '30'))
    RATE_LIMIT_PER_HOUR = int(os.getenv('RATE_LIMIT_PER_HOUR', '500'))
    
    # File size limits
    MAX_FILE_SIZE_MB = int(os.getenv('MAX_FILE_SIZE_MB', '50'))  # Telegram limit
    
    # External API configuration
    SAVETUBE_API_BASE = 'https://savetube.me/api/v1'
    
    # Cache configuration (disabled as per user request)
    CACHE_ENABLED = False
    
    # Background processing
    BACKGROUND_PROCESSING = True
    
    # Quality priorities for auto selection
    QUALITY_PRIORITIES = ['1080p', '720p', '480p', '360p']
    
    # Supported formats
    SUPPORTED_FORMATS = ['video', 'audio']
    
    @staticmethod
    def validate():
        """Validate configuration"""
        warnings = []
        
        if not Config.MONGO_DB_URI:
            warnings.append("MONGO_DB_URI not set - Telegram file tracking disabled")
        
        if not Config.TELEGRAM_BOT_TOKEN:
            warnings.append("TELEGRAM_BOT_TOKEN not set - File storage disabled")
        
        if not Config.TELEGRAM_CHANNEL_ID:
            warnings.append("TELEGRAM_CHANNEL_ID not set - File storage disabled")
        
        return warnings

# Legacy constants for YouTube processor compatibility
AES_KEY = "2aQF@#4sJzY9Xp8G6vBn1Kw5Eq3Rt7Mu"  # 32-byte AES key
VIDEO_QUALITY_PRIORITY = Config.QUALITY_PRIORITIES
API_TIMEOUT = 30