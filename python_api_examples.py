"""
YouTube Downloader API - Python Client Examples
Professional examples for integrating with the YouTube Downloader API
"""

import requests
import json
import time
from typing import Dict, Any, Optional, List
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class YouTubeDownloaderClient:
    """Professional Python client for YouTube Downloader API"""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        """
        Initialize the client
        
        Args:
            base_url: Base URL of the API server
        """
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.timeout = 30
        
        # Set headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'YouTubeDownloaderClient/1.0'
        })
    
    def _make_request(self, endpoint: str, method: str = 'GET', data: Dict = None) -> Dict[str, Any]:
        """
        Make HTTP request to API
        
        Args:
            endpoint: API endpoint
            method: HTTP method
            data: Request data
            
        Returns:
            API response as dictionary
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return {
                'success': False,
                'error': f'Request failed: {str(e)}'
            }
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return {
                'success': False,
                'error': f'Invalid JSON response: {str(e)}'
            }
    
    def get_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Get video information
        
        Args:
            url: YouTube video URL
            
        Returns:
            Video information or None if failed
        """
        logger.info(f"Getting video info for: {url}")
        
        response = self._make_request('/api/video-info', 'POST', {'url': url})
        
        if response.get('success'):
            logger.info(f"Got video info: {response['data']['title']}")
            return response['data']
        else:
            logger.error(f"Failed to get video info: {response.get('error')}")
            return None
    
    def download_video(self, url: str, quality: str = 'auto', format_type: str = 'video') -> Optional[Dict[str, Any]]:
        """
        Get download links for video
        
        Args:
            url: YouTube video URL
            quality: Video quality (auto, 1080p, 720p, 480p, 360p)
            format_type: Format type (video, audio)
            
        Returns:
            Download information or None if failed
        """
        logger.info(f"Getting download links for: {url} ({quality}, {format_type})")
        
        response = self._make_request('/api/download', 'POST', {
            'url': url,
            'quality': quality,
            'format': format_type
        })
        
        if response.get('success'):
            data = response['data']
            logger.info(f"Got download links for: {data['title']}")
            return data
        else:
            logger.error(f"Failed to get download links: {response.get('error')}")
            return None
    
    def get_stats(self) -> Optional[Dict[str, Any]]:
        """
        Get API statistics
        
        Returns:
            API statistics or None if failed
        """
        response = self._make_request('/api/stats')
        
        if response.get('success'):
            return response['data']
        else:
            logger.error(f"Failed to get stats: {response.get('error')}")
            return None
    
    def clear_cache(self) -> bool:
        """
        Clear API cache
        
        Returns:
            True if successful, False otherwise
        """
        logger.info("Clearing API cache")
        
        response = self._make_request('/api/cache/clear', 'POST')
        
        if response.get('success'):
            logger.info("Cache cleared successfully")
            return True
        else:
            logger.error(f"Failed to clear cache: {response.get('error')}")
            return False

def download_video_example():
    """Example: Download a YouTube video"""
    print("=== Download Video Example ===")
    
    client = YouTubeDownloaderClient()
    
    # Example YouTube URL (replace with actual URL)
    url = "https://youtu.be/dQw4w9WgXcQ"  # Rick Roll for testing
    
    # Get video info first
    print(f"Getting info for: {url}")
    video_info = client.get_video_info(url)
    
    if video_info:
        print(f"Title: {video_info['title']}")
        print(f"Duration: {video_info['duration']}")
        print(f"Uploader: {video_info['uploader']}")
        
        # Get download links
        print("\nGetting download links...")
        download_data = client.download_video(url, quality='720p')
        
        if download_data:
            print(f"Download URL: {download_data['url']}")
            print(f"Quality: {download_data['quality']}")
            print(f"File Size: {download_data['file_size_estimate']}")
            
            if download_data.get('telegram_url'):
                print(f"Telegram URL: {download_data['telegram_url']}")
            
            if download_data.get('masked_url'):
                print(f"Masked URL: {download_data['masked_url']}")
        else:
            print("Failed to get download links")
    else:
        print("Failed to get video info")

def batch_download_example():
    """Example: Batch download multiple videos"""
    print("\n=== Batch Download Example ===")
    
    client = YouTubeDownloaderClient()
    
    # List of YouTube URLs
    urls = [
        "https://youtu.be/dQw4w9WgXcQ",
        "https://youtu.be/oHg5SJYRHA0",
        # Add more URLs as needed
    ]
    
    results = []
    
    for i, url in enumerate(urls, 1):
        print(f"\nProcessing video {i}/{len(urls)}: {url}")
        
        try:
            # Get video info
            video_info = client.get_video_info(url)
            if not video_info:
                print(f"Skipping {url} - Failed to get info")
                continue
            
            # Get download links with different qualities
            for quality in ['1080p', '720p', '480p']:
                download_data = client.download_video(url, quality=quality)
                if download_data:
                    result = {
                        'url': url,
                        'title': video_info['title'],
                        'quality': quality,
                        'download_url': download_data['url'],
                        'file_size': download_data['file_size_estimate']
                    }
                    results.append(result)
                    print(f"✓ Got {quality} link for: {video_info['title']}")
                    break
            else:
                print(f"✗ No download links available for: {video_info['title']}")
            
            # Add delay to avoid rate limiting
            time.sleep(1)
            
        except Exception as e:
            print(f"Error processing {url}: {e}")
    
    # Print summary
    print(f"\n=== Summary ===")
    print(f"Successfully processed: {len(results)} videos")
    for result in results:
        print(f"- {result['title']} ({result['quality']}) - {result['file_size']}")

def api_stats_example():
    """Example: Monitor API statistics"""
    print("\n=== API Statistics Example ===")
    
    client = YouTubeDownloaderClient()
    
    stats = client.get_stats()
    if stats:
        print(f"Total Requests: {stats['requests_total']:,}")
        print(f"Cache Hit Rate: {stats['cache_hit_rate']}%")
        print(f"Telegram Uploads: {stats['telegram_uploads']:,}")
        print(f"Uptime: {stats['uptime_human']}")
        print(f"Active Requests: {stats['active_requests']}")
        print(f"Memory Cache Size: {stats.get('memory_cache_size', 'N/A')}")
        print(f"MongoDB Connected: {stats.get('mongodb_connection', False)}")
    else:
        print("Failed to get API statistics")

def quality_priority_example():
    """Example: Download with quality priority fallback"""
    print("\n=== Quality Priority Example ===")
    
    client = YouTubeDownloaderClient()
    
    url = "https://youtu.be/dQw4w9WgXcQ"
    
    # Define quality priority order
    quality_priorities = ['1080p', '720p', '480p', '360p']
    
    print(f"Attempting download with quality priority: {' → '.join(quality_priorities)}")
    
    for quality in quality_priorities:
        print(f"\nTrying {quality}...")
        download_data = client.download_video(url, quality=quality)
        
        if download_data:
            print(f"✓ Success! Downloaded in {download_data['quality']}")
            print(f"File size: {download_data['file_size_estimate']}")
            print(f"Download URL: {download_data['url']}")
            break
        else:
            print(f"✗ {quality} not available")
    else:
        print("No quality available for download")

def cache_management_example():
    """Example: Cache management operations"""
    print("\n=== Cache Management Example ===")
    
    client = YouTubeDownloaderClient()
    
    # Get initial stats
    print("Initial cache stats:")
    stats = client.get_stats()
    if stats:
        print(f"Cache hit rate: {stats['cache_hit_rate']}%")
        print(f"Memory cache size: {stats.get('memory_cache_size', 'N/A')}")
    
    # Make some requests to populate cache
    print("\nMaking requests to populate cache...")
    url = "https://youtu.be/dQw4w9WgXcQ"
    
    for i in range(3):
        print(f"Request {i+1}/3")
        video_info = client.get_video_info(url)
        if video_info:
            print(f"✓ Got info (cached: probably {'yes' if i > 0 else 'no'})")
        time.sleep(0.5)
    
    # Check updated stats
    print("\nUpdated cache stats:")
    stats = client.get_stats()
    if stats:
        print(f"Cache hit rate: {stats['cache_hit_rate']}%")
        print(f"Total requests: {stats['requests_total']}")
    
    # Clear cache
    print("\nClearing cache...")
    if client.clear_cache():
        print("✓ Cache cleared successfully")
        
        # Check stats after clearing
        stats = client.get_stats()
        if stats:
            print(f"Memory cache size after clear: {stats.get('memory_cache_size', 'N/A')}")
    else:
        print("✗ Failed to clear cache")

class AsyncYouTubeDownloaderClient:
    """Async version of the client using aiohttp"""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        import aiohttp
        self.base_url = base_url.rstrip('/')
        self.session = None
    
    async def __aenter__(self):
        import aiohttp
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'AsyncYouTubeDownloaderClient/1.0'
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """Async version of get_video_info"""
        async with self.session.post(
            f"{self.base_url}/api/video-info",
            json={'url': url}
        ) as response:
            data = await response.json()
            return data['data'] if data.get('success') else None

async def async_example():
    """Example: Async operations"""
    print("\n=== Async Example ===")
    
    urls = [
        "https://youtu.be/dQw4w9WgXcQ",
        "https://youtu.be/oHg5SJYRHA0",
    ]
    
    async with AsyncYouTubeDownloaderClient() as client:
        import asyncio
        
        # Process multiple URLs concurrently
        tasks = [client.get_video_info(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for url, result in zip(urls, results):
            if isinstance(result, Exception):
                print(f"Error for {url}: {result}")
            elif result:
                print(f"✓ {result['title']} - {result['duration']}")
            else:
                print(f"✗ Failed to get info for {url}")

def main():
    """Run all examples"""
    print("YouTube Downloader API - Python Client Examples")
    print("=" * 50)
    
    try:
        # Basic examples
        download_video_example()
        batch_download_example()
        api_stats_example()
        quality_priority_example()
        cache_management_example()
        
        # Async example (requires aiohttp)
        try:
            import asyncio
            import aiohttp
            asyncio.run(async_example())
        except ImportError:
            print("\n=== Async Example ===")
            print("Install aiohttp to run async examples: pip install aiohttp")
        
    except KeyboardInterrupt:
        print("\nExamples interrupted by user")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        logger.exception("Error in examples")

if __name__ == "__main__":
    main()
