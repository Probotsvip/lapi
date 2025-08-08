import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure, OperationFailure
import os
import threading
from concurrent.futures import ThreadPoolExecutor

from .logging import LOGGER

logger = LOGGER(__name__)

class MongoDBManager:
    """MongoDB manager for tracking Telegram-stored files only"""
    
    def __init__(self):
        """Initialize MongoDB connection for tracking Telegram files"""
        self.client = None
        self.db = None
        self.collection = None
        self.enabled = False
        self._lock = None
        self._initialized = False
        self.executor = ThreadPoolExecutor(max_workers=2)
        self._loop = None
    
    async def _ensure_connected(self):
        """Ensure MongoDB connection is established"""
        if self._initialized:
            return
        
        if self._lock is None:
            self._lock = asyncio.Lock()
        
        async with self._lock:
            if self._initialized:
                return
            
            try:
                # Check both possible environment variable names
                mongo_uri = os.getenv('MONGODB_URI') or os.getenv('MONGO_DB_URI')
                if not mongo_uri:
                    logger.warning("MONGODB_URI not provided - Telegram tracking disabled")
                    self._initialized = True
                    return
                
                logger.info(f"Attempting MongoDB connection to: {mongo_uri[:50]}...")
                
                self.client = AsyncIOMotorClient(mongo_uri)
                self.db = self.client.youtube_downloader
                self.collection = self.db.telegram_files
                
                # Test connection
                await self.client.admin.command('ping')
                self.enabled = True
                logger.info("Connected to MongoDB for Telegram file tracking")
                
            except Exception as e:
                logger.error(f"Failed to connect to MongoDB: {e}")
                logger.error(f"MongoDB URI format: {mongo_uri[:20]}... (length: {len(mongo_uri) if mongo_uri else 0})")
                import traceback
                logger.error(f"Full traceback: {traceback.format_exc()}")
                self.enabled = False
            
            self._initialized = True
    
    def is_connected(self) -> bool:
        """Check if MongoDB is connected"""
        return self.enabled
    
    def _run_async(self, coro):
        """Run async function in thread-safe way"""
        try:
            # Try to get current event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, use thread executor
                return self.executor.submit(asyncio.run, coro).result(timeout=10)
            else:
                # If no loop is running, run directly
                return loop.run_until_complete(coro)
        except RuntimeError:
            # No event loop, create new one
            return asyncio.run(coro)
        except Exception as e:
            logger.error(f"Async execution error: {e}")
            return None
    
    async def store_telegram_file(self, video_id: str, quality: str, telegram_data: Dict[str, Any]) -> bool:
        """Store Telegram file information for future retrieval"""
        await self._ensure_connected()
        
        if not self.enabled:
            return False
        
        async with self._lock:
            try:
                document = {
                    'video_id': video_id,
                    'quality': quality,
                    'telegram_file_id': telegram_data.get('file_id'),
                    'telegram_url': telegram_data.get('url'),
                    'file_size': telegram_data.get('file_size'),
                    'title': telegram_data.get('title'),
                    'duration': telegram_data.get('duration'),
                    'format': telegram_data.get('format', 'video'),
                    'created_at': datetime.utcnow(),
                    'last_accessed': datetime.utcnow(),
                    'access_count': 1
                }
                
                # Upsert - update if exists, insert if not
                await self.collection.update_one(
                    {'video_id': video_id, 'quality': quality},
                    {'$set': document},
                    upsert=True
                )
                
                logger.info(f"Stored Telegram file info for {video_id} ({quality})")
                return True
                
            except Exception as e:
                logger.error(f"Failed to store Telegram file info: {e}")
                return False
    
    async def get_telegram_file(self, video_id: str, quality: str = None) -> Optional[Dict[str, Any]]:
        """Get Telegram file information by video ID"""
        await self._ensure_connected()
        
        if not self.enabled:
            return None
        
        try:
            if quality:
                # Get specific quality
                query = {'video_id': video_id, 'quality': quality, 'telegram_file_id': {'$exists': True}}
                document = await self.collection.find_one(query)
            else:
                # Get best available quality
                cursor = self.collection.find(
                    {'video_id': video_id, 'telegram_file_id': {'$exists': True}}
                ).sort('quality', -1)
                documents = await cursor.to_list(length=None)
                
                if not documents:
                    return None
                
                # Quality priority: 1080p > 720p > 480p > 360p
                quality_order = ['1080p', '720p', '480p', '360p']
                document = None
                for q in quality_order:
                    for doc in documents:
                        if doc.get('quality') == q:
                            document = doc
                            break
                    if document:
                        break
                
                if not document:
                    document = documents[0]  # Fallback to first available
            
            if document:
                # Update access statistics
                await self.collection.update_one(
                    {'_id': document['_id']},
                    {
                        '$set': {'last_accessed': datetime.utcnow()},
                        '$inc': {'access_count': 1}
                    }
                )
                
                logger.info(f"Retrieved Telegram file for {video_id} ({document.get('quality')})")
                return document
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get Telegram file info: {e}")
            return None
    
    async def mark_processing(self, video_id: str, quality: str) -> bool:
        """Mark a video as being processed to avoid duplicate downloads"""
        await self._ensure_connected()
        
        if not self.enabled:
            return False
        
        try:
            document = {
                'video_id': video_id,
                'quality': quality,
                'status': 'processing',
                'started_at': datetime.utcnow()
            }
            
            await self.collection.update_one(
                {'video_id': video_id, 'quality': quality},
                {'$set': document},
                upsert=True
            )
            
            logger.info(f"Marked {video_id} ({quality}) as processing")
            return True
            
        except Exception as e:
            logger.error(f"Failed to mark as processing: {e}")
            return False
    
    async def is_processing(self, video_id: str, quality: str) -> bool:
        """Check if a video is currently being processed"""
        await self._ensure_connected()
        
        if not self.enabled:
            return False
        
        try:
            document = await self.collection.find_one({
                'video_id': video_id,
                'quality': quality,
                'status': 'processing'
            })
            
            if document:
                # Check if processing started more than 10 minutes ago (timeout)
                started_at = document.get('started_at')
                if started_at and datetime.utcnow() - started_at > timedelta(minutes=10):
                    # Remove stale processing status
                    await self.collection.delete_one({'_id': document['_id']})
                    logger.info(f"Removed stale processing status for {video_id}")
                    return False
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to check processing status: {e}")
            return False
    
    async def get_video_qualities(self, video_id: str) -> List[str]:
        """Get all available qualities for a video in Telegram"""
        await self._ensure_connected()
        
        if not self.enabled:
            return []
        
        try:
            cursor = self.collection.find(
                {'video_id': video_id, 'telegram_file_id': {'$exists': True}},
                {'quality': 1}
            )
            documents = await cursor.to_list(length=None)
            return [doc['quality'] for doc in documents]
            
        except Exception as e:
            logger.error(f"Failed to get video qualities: {e}")
            return []
    
    async def cleanup_old_entries(self, days: int = 30) -> int:
        """Cleanup old entries and processing statuses"""
        await self._ensure_connected()
        
        if not self.enabled:
            return 0
        
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Remove old processing statuses
            processing_result = await self.collection.delete_many({
                'status': 'processing',
                'started_at': {'$lt': cutoff_date}
            })
            
            # Remove old file entries that haven't been accessed
            old_files_result = await self.collection.delete_many({
                'last_accessed': {'$lt': cutoff_date},
                'access_count': {'$lt': 3}  # Only remove if accessed less than 3 times
            })
            
            total_removed = processing_result.deleted_count + old_files_result.deleted_count
            if total_removed > 0:
                logger.info(f"Cleaned up {total_removed} old entries")
            return total_removed
            
        except Exception as e:
            logger.error(f"Failed to cleanup old entries: {e}")
            return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        await self._ensure_connected()
        
        if not self.enabled:
            return {'connected': False, 'total_files': 0}
        
        try:
            total_files = await self.collection.count_documents({
                'telegram_file_id': {'$exists': True}
            })
            
            processing_count = await self.collection.count_documents({
                'status': 'processing'
            })
            
            return {
                'connected': True,
                'total_files': total_files,
                'processing_count': processing_count
            }
            
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {'connected': False, 'error': str(e)}
    
    # Legacy methods for compatibility (no-op since we only track Telegram files)
    def store_video_info(self, url: str, video_info: Dict[str, Any]):
        """No-op - we only track Telegram files"""
        pass
    
    def get_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """Always return None - we only track Telegram files"""
        return None
    
    def store_download_data(self, url: str, quality: str, format_type: str, download_data: Dict[str, Any]):
        """No-op - we only track Telegram files"""
        pass
    
    def get_download_data(self, url: str, quality: str, format_type: str) -> Optional[Dict[str, Any]]:
        """Always return None - we only track Telegram files"""
        return None
    
    def cleanup_expired(self):
        """No-op - use async cleanup_old_entries instead"""
        pass
    
    # Sync wrapper methods for Flask compatibility
    def store_telegram_file_sync(self, video_id: str, quality: str, telegram_data: Dict[str, Any]) -> bool:
        """Sync wrapper for store_telegram_file"""
        return self._run_async(self.store_telegram_file(video_id, quality, telegram_data))
    
    def get_telegram_file_sync(self, video_id: str, quality: str = None) -> Optional[Dict[str, Any]]:
        """Sync wrapper for get_telegram_file"""
        return self._run_async(self.get_telegram_file(video_id, quality))
    
    def is_processing_sync(self, video_id: str, quality: str) -> bool:
        """Sync wrapper for is_processing"""
        result = self._run_async(self.is_processing(video_id, quality))
        return result if result is not None else False
    
    def mark_processing_sync(self, video_id: str, quality: str) -> bool:
        """Sync wrapper for mark_processing"""
        result = self._run_async(self.mark_processing(video_id, quality))
        return result if result is not None else False