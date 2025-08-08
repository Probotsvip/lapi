import os

# No database configuration needed

# Telegram configuration (disabled)
TELEGRAM_BOT_TOKEN = ""
TELEGRAM_CHANNEL_ID = ""

# AES encryption key for savetube.me
AES_KEY = "C5D58EF67A7584E4A29F6C35BBC4EB12"

# Session configuration
SESSION_SECRET = os.getenv("SESSION_SECRET", "your_secret_key_here")

# Cache configuration
MEMORY_CACHE_TTL = 3600  # 1 hour
MONGODB_CACHE_TTL = 86400  # 24 hours

# Rate limiting
RATE_LIMIT_PER_MINUTE = 30
RATE_LIMIT_PER_HOUR = 500

# File size limits
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB for Telegram

# Quality priorities
VIDEO_QUALITY_PRIORITY = ['1080p', '720p', '480p', '360p']
AUDIO_QUALITY_PRIORITY = ['mp3', 'm4a']

# API timeouts
API_TIMEOUT = 30
DOWNLOAD_TIMEOUT = 300
