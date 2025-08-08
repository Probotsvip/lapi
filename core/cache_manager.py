import threading
import time
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class SmartCacheManager:
    """Thread-safe memory cache with TTL expiration"""
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._cleanup_thread = None
        self._start_cleanup_thread()
    
    def _start_cleanup_thread(self):
        """Start background thread for cache cleanup"""
        def cleanup_expired():
            while True:
                try:
                    time.sleep(60)  # Check every minute
                    self._cleanup_expired_items()
                except Exception as e:
                    logger.error(f"Cache cleanup error: {e}")
        
        self._cleanup_thread = threading.Thread(target=cleanup_expired, daemon=True)
        self._cleanup_thread.start()
        logger.info("Cache cleanup thread started")
    
    def _cleanup_expired_items(self):
        """Remove expired items from cache"""
        current_time = time.time()
        expired_keys = []
        
        with self._lock:
            for key, item in self._cache.items():
                if current_time > item['expires_at']:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._cache[key]
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache items")
    
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache if not expired"""
        with self._lock:
            if key not in self._cache:
                return None
            
            item = self._cache[key]
            if time.time() > item['expires_at']:
                del self._cache[key]
                return None
            
            # Update access time for LRU tracking
            item['last_accessed'] = time.time()
            return item['value']
    
    def set(self, key: str, value: Any, ttl: int = 3600):
        """Set item in cache with TTL in seconds"""
        expires_at = time.time() + ttl
        
        with self._lock:
            self._cache[key] = {
                'value': value,
                'expires_at': expires_at,
                'created_at': time.time(),
                'last_accessed': time.time()
            }
        
        logger.debug(f"Cached item: {key} (TTL: {ttl}s)")
    
    def delete(self, key: str) -> bool:
        """Delete specific item from cache"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Deleted cache item: {key}")
                return True
            return False
    
    def clear_cache(self) -> int:
        """Clear all cache items and return count of cleared items"""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"Cache cleared: {count} items removed")
            return count
    
    def get_cache_size(self) -> int:
        """Get current cache size"""
        with self._lock:
            return len(self._cache)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        current_time = time.time()
        
        with self._lock:
            total_items = len(self._cache)
            expired_items = sum(1 for item in self._cache.values() 
                              if current_time > item['expires_at'])
            
            return {
                'total_items': total_items,
                'active_items': total_items - expired_items,
                'expired_items': expired_items,
                'memory_usage_estimate': total_items * 1024  # Rough estimate
            }
    
    def has_key(self, key: str) -> bool:
        """Check if key exists and is not expired"""
        return self.get(key) is not None
