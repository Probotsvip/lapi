import logging
from typing import Dict, Any, Optional

from .logging import LOGGER

logger = LOGGER(__name__)

class SmartCacheManager:
    """No-cache manager - user requested no local storage"""
    
    def __init__(self):
        """Initialize with no caching as per user requirements"""
        logger.info("Cache disabled - no local storage as requested")
        self.enabled = False
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Always return None - no caching"""
        return None
    
    def set(self, key: str, value: Dict[str, Any], ttl: int = 3600) -> bool:
        """No-op - no caching"""
        return False
    
    def delete(self, key: str) -> bool:
        """No-op - no caching"""
        return False
    
    def clear(self) -> int:
        """No-op - no caching"""
        return 0
    
    def get_cache_size(self) -> int:
        """Return 0 - no caching"""
        return 0
    
    def clear_cache(self) -> int:
        """No-op - no caching"""
        return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Return empty stats"""
        return {
            'enabled': False,
            'memory_size': 0,
            'total_items': 0,
            'hit_rate': 0.0,
            'total_gets': 0,
            'total_hits': 0
        }
    
    def cleanup_expired(self):
        """No-op - no caching"""
        pass