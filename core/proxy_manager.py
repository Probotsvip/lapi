import uuid
import time
import threading
from typing import Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)

class ProxyManager:
    """UUID-based URL masking system for privacy protection"""
    
    def __init__(self):
        self._masked_urls: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._cleanup_thread = None
        self.default_ttl = 3600  # 1 hour
        self._start_cleanup_thread()
    
    def _start_cleanup_thread(self):
        """Start background thread for cleanup of expired URLs"""
        def cleanup_expired():
            while True:
                try:
                    time.sleep(300)  # Check every 5 minutes
                    self._cleanup_expired_urls()
                except Exception as e:
                    logger.error(f"Proxy cleanup error: {e}")
        
        self._cleanup_thread = threading.Thread(target=cleanup_expired, daemon=True)
        self._cleanup_thread.start()
        logger.info("Proxy cleanup thread started")
    
    def _cleanup_expired_urls(self):
        """Remove expired masked URLs"""
        current_time = time.time()
        expired_keys = []
        
        with self._lock:
            for masked_id, data in self._masked_urls.items():
                if current_time > data['expires_at']:
                    expired_keys.append(masked_id)
            
            for key in expired_keys:
                del self._masked_urls[key]
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired proxy URLs")
    
    def create_masked_url(self, original_url: str, filename: str = "video", ttl: Optional[int] = None) -> str:
        """Create a masked UUID-based URL for the original URL"""
        if ttl is None:
            ttl = self.default_ttl
        
        # Generate UUID
        masked_id = str(uuid.uuid4())
        
        # Store mapping
        expires_at = time.time() + ttl
        
        with self._lock:
            self._masked_urls[masked_id] = {
                'original_url': original_url,
                'filename': filename,
                'created_at': time.time(),
                'expires_at': expires_at,
                'access_count': 0,
                'last_accessed': None
            }
        
        logger.debug(f"Created masked URL: {masked_id} -> {original_url}")
        return masked_id
    
    def get_original_url(self, masked_id: str) -> Optional[str]:
        """Get original URL from masked ID and update access statistics"""
        with self._lock:
            if masked_id not in self._masked_urls:
                logger.warning(f"Masked URL not found: {masked_id}")
                return None
            
            data = self._masked_urls[masked_id]
            
            # Check if expired
            if time.time() > data['expires_at']:
                logger.warning(f"Masked URL expired: {masked_id}")
                del self._masked_urls[masked_id]
                return None
            
            # Update access statistics
            data['access_count'] += 1
            data['last_accessed'] = time.time()
            
            original_url = data['original_url']
            logger.debug(f"Proxy access: {masked_id} -> {original_url}")
            
            return original_url
    
    def get_url_info(self, masked_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a masked URL"""
        with self._lock:
            if masked_id not in self._masked_urls:
                return None
            
            data = self._masked_urls[masked_id].copy()
            
            # Check if expired
            if time.time() > data['expires_at']:
                del self._masked_urls[masked_id]
                return None
            
            # Add additional info
            data['is_expired'] = False
            data['time_to_expire'] = data['expires_at'] - time.time()
            
            return data
    
    def revoke_masked_url(self, masked_id: str) -> bool:
        """Manually revoke a masked URL"""
        with self._lock:
            if masked_id in self._masked_urls:
                del self._masked_urls[masked_id]
                logger.info(f"Revoked masked URL: {masked_id}")
                return True
            return False
    
    def extend_ttl(self, masked_id: str, additional_seconds: int) -> bool:
        """Extend the TTL of a masked URL"""
        with self._lock:
            if masked_id not in self._masked_urls:
                return False
            
            data = self._masked_urls[masked_id]
            
            # Check if already expired
            if time.time() > data['expires_at']:
                del self._masked_urls[masked_id]
                return False
            
            # Extend TTL
            data['expires_at'] += additional_seconds
            logger.debug(f"Extended TTL for masked URL: {masked_id}")
            
            return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get proxy manager statistics"""
        current_time = time.time()
        
        with self._lock:
            total_urls = len(self._masked_urls)
            expired_urls = sum(1 for data in self._masked_urls.values() 
                             if current_time > data['expires_at'])
            active_urls = total_urls - expired_urls
            
            # Calculate total access count
            total_accesses = sum(data['access_count'] for data in self._masked_urls.values())
            
            return {
                'total_masked_urls': total_urls,
                'active_urls': active_urls,
                'expired_urls': expired_urls,
                'total_accesses': total_accesses,
                'average_accesses': total_accesses / max(total_urls, 1)
            }
    
    def list_active_urls(self, limit: int = 50) -> list:
        """List active masked URLs with their info"""
        current_time = time.time()
        active_urls = []
        
        with self._lock:
            for masked_id, data in self._masked_urls.items():
                if current_time <= data['expires_at']:
                    url_info = {
                        'masked_id': masked_id,
                        'filename': data['filename'],
                        'created_at': data['created_at'],
                        'expires_at': data['expires_at'],
                        'time_to_expire': data['expires_at'] - current_time,
                        'access_count': data['access_count'],
                        'last_accessed': data['last_accessed']
                    }
                    active_urls.append(url_info)
        
        # Sort by creation time (newest first) and limit
        active_urls.sort(key=lambda x: x['created_at'], reverse=True)
        return active_urls[:limit]
