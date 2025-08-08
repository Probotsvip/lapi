# YouTube Downloader API

## Overview

This is a professional Flask-based YouTube video downloader API that provides video extraction capabilities with advanced features including caching, MongoDB storage, Telegram integration, and proxy management. The system uses AES decryption to process YouTube video data from savetube.me and offers both RESTful API endpoints and a web interface for testing.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Core Flask Application
- **Main Application**: Built with Flask framework using modular architecture
- **WSGI Configuration**: Uses ProxyFix middleware for proper header handling behind proxies
- **Request Tracking**: Global statistics tracking for monitoring requests, cache hits, and uploads

### Data Storage Architecture
- **Primary Database**: MongoDB Atlas integration using Motor async driver
- **Database Manager**: Async MongoDB operations with sync wrapper for Flask compatibility
- **Collections**: Stores video metadata, download history, and cached video information

### Caching System
- **Multi-Layer Caching**: SmartCacheManager with in-memory cache and MongoDB persistence
- **TTL Management**: Automatic expiration with background cleanup threads
- **Thread Safety**: Thread-safe operations using RLock for concurrent access

### Video Processing Pipeline
- **YouTube Processor**: Extracts video data using AES-CBC decryption from savetube.me API
- **Quality Selection**: Prioritized quality selection (1080p > 720p > 480p > 360p)
- **Format Support**: Both video (MP4) and audio (MP3, M4A) extraction

### Privacy and Security
- **Proxy Manager**: UUID-based URL masking system for privacy protection
- **Rate Limiting**: Configurable rate limits (30/minute, 500/hour)
- **File Size Limits**: 50MB limit for Telegram uploads
- **Session Management**: Secure session handling with configurable secrets

### File Storage Integration
- **Telegram Uploader**: Permanent file storage using Telegram Bot API
- **Async Downloads**: Non-blocking file download and upload operations
- **Temporary File Handling**: Secure temporary file management with cleanup

### Frontend Interface
- **Web Dashboard**: Professional dark-themed interface for API testing
- **Real-time Stats**: Live application statistics and monitoring
- **Interactive Testing**: Built-in tools for testing all API endpoints

## External Dependencies

### Required Services
- **MongoDB Atlas**: Primary database for persistent storage and caching
- **Telegram Bot API**: File storage and sharing service
- **SaveTube.me API**: YouTube video data extraction service

### Python Libraries
- **Flask**: Web application framework
- **Motor**: Async MongoDB driver
- **Requests/aiohttp**: HTTP client libraries for API calls
- **PyCryptodome**: AES encryption/decryption for video data
- **Werkzeug**: WSGI utilities and proxy handling

### Configuration Requirements
- **MONGO_DB_URI**: MongoDB connection string
- **TELEGRAM_BOT_TOKEN**: Bot token for Telegram integration
- **TELEGRAM_CHANNEL_ID**: Target channel for file uploads
- **SESSION_SECRET**: Flask session encryption key

### API Integrations
- **YouTube Data Extraction**: Via savetube.me with AES-CBC decryption
- **CDN Services**: Random CDN selection for optimized downloads
- **File Hosting**: Telegram as permanent storage backend

### Development Tools
- **Bootstrap 5**: Frontend UI framework
- **Feather Icons**: Icon library for interface
- **JavaScript**: Client-side API interaction and testing tools