import requests
import json
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import time
import re
from typing import Dict, Any, Optional, List
import logging

from config import AES_KEY, VIDEO_QUALITY_PRIORITY, API_TIMEOUT

logger = logging.getLogger(__name__)

class YouTubeProcessor:
    """YouTube processor adapted from provided JavaScript code with AES decryption"""
    
    def __init__(self):
        self.hex_key = AES_KEY
        self.session = requests.Session()
        # Set timeout in request calls instead
    
    def _hex_to_bytes(self, hex_string: str) -> bytes:
        """Convert hex string to bytes"""
        try:
            # Remove any whitespace and convert to bytes
            clean_hex = hex_string.replace(" ", "").upper()
            return bytes.fromhex(clean_hex)
        except Exception as e:
            logger.error(f"Error converting hex to bytes: {e}")
            raise ValueError("Invalid hex format")
    
    def _base64_to_bytes(self, b64_string: str) -> bytes:
        """Convert base64 string to bytes"""
        try:
            clean_b64 = b64_string.replace(" ", "").replace("\n", "")
            return base64.b64decode(clean_b64)
        except Exception as e:
            logger.error(f"Error converting base64 to bytes: {e}")
            raise ValueError("Invalid base64 format")
    
    def _decrypt_data(self, encrypted_base64: str) -> Dict[str, Any]:
        """Decrypt AES-CBC encrypted data from savetube.me"""
        try:
            # Convert base64 to bytes
            encrypted_data = self._base64_to_bytes(encrypted_base64)
            
            if len(encrypted_data) < 16:
                raise ValueError("Encrypted data too short")
            
            # Extract IV (first 16 bytes) and ciphertext
            iv = encrypted_data[:16]
            ciphertext = encrypted_data[16:]
            
            # Convert hex key to bytes
            key = self._hex_to_bytes(self.hex_key)
            
            # Decrypt using AES-CBC
            cipher = AES.new(key, AES.MODE_CBC, iv)
            decrypted = cipher.decrypt(ciphertext)
            
            # Remove padding
            unpadded = unpad(decrypted, AES.block_size)
            
            # Convert to string and parse JSON
            decrypted_text = unpadded.decode('utf-8')
            return json.loads(decrypted_text)
            
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            raise ValueError(f"Failed to decrypt data: {e}")
    
    def _get_cdn(self) -> str:
        """Get CDN endpoint from savetube.me"""
        max_retries = 5
        
        for attempt in range(max_retries):
            try:
                response = self.session.get("https://media.savetube.me/api/random-cdn", timeout=API_TIMEOUT)
                response.raise_for_status()
                
                data = response.json()
                if data and 'cdn' in data:
                    logger.debug(f"Got CDN: {data['cdn']}")
                    return data['cdn']
                    
            except Exception as e:
                logger.warning(f"CDN retrieval attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)  # Wait before retry
        
        raise Exception("Failed to get CDN after maximum retries")
    
    def _extract_video_id(self, url: str) -> str:
        """Extract YouTube video ID from URL"""
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com\/v\/([a-zA-Z0-9_-]{11})',
            r'youtube\.com\/watch\?.*?v=([a-zA-Z0-9_-]{11})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        raise ValueError("Invalid YouTube URL")
    
    def get_video_info(self, youtube_url: str) -> Optional[Dict[str, Any]]:
        """Get video information from YouTube URL"""
        try:
            # Validate URL
            video_id = self._extract_video_id(youtube_url)
            logger.info(f"Processing video ID: {video_id}")
            
            # Get CDN
            cdn = self._get_cdn()
            
            # Make request to get video info
            info_url = f"https://{cdn}/v2/info"
            payload = {"url": youtube_url}
            
            response = self.session.post(
                info_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=API_TIMEOUT
            )
            response.raise_for_status()
            
            result = response.json()
            
            if not result.get('status'):
                error_msg = result.get('message', 'Failed to get video info')
                logger.error(f"API error: {error_msg}")
                return None
            
            # Decrypt the response data
            decrypted_data = self._decrypt_data(result['data'])
            
            # Format the response
            video_info = {
                'video_id': video_id,
                'title': decrypted_data.get('title', 'Unknown Title'),
                'duration': decrypted_data.get('durationLabel', 'Unknown'),
                'thumbnail': decrypted_data.get('thumbnail', ''),
                'key': decrypted_data.get('key', ''),
                'uploader': decrypted_data.get('uploader', 'Unknown'),
                'view_count': decrypted_data.get('viewCount', 0),
                'upload_date': decrypted_data.get('uploadDate', ''),
                'description': decrypted_data.get('description', '')[:500]  # Limit description
            }
            
            logger.info(f"Successfully retrieved info for: {video_info['title']}")
            return video_info
            
        except Exception as e:
            logger.error(f"Error getting video info: {e}")
            return None
    
    def _get_download_link(self, video_key: str, quality: str) -> Optional[str]:
        """Get download link for specific quality"""
        max_retries = 5
        
        for attempt in range(max_retries):
            try:
                cdn = self._get_cdn()
                download_url = f"https://{cdn}/download"
                
                payload = {
                    'downloadType': 'video',
                    'quality': quality,
                    'key': video_key
                }
                
                response = self.session.post(
                    download_url,
                    json=payload,
                    headers={'Content-Type': 'application/json'},
                    timeout=API_TIMEOUT
                )
                response.raise_for_status()
                
                result = response.json()
                
                if result.get('status') and result.get('data', {}).get('downloadUrl'):
                    download_link = result['data']['downloadUrl']
                    logger.debug(f"Got download link for quality {quality}")
                    return download_link
                    
            except Exception as e:
                logger.warning(f"Download link attempt {attempt + 1} failed for quality {quality}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
        
        logger.warning(f"Failed to get download link for quality {quality}")
        return None
    
    def get_download_links(self, youtube_url: str, requested_quality: str = 'auto', format_type: str = 'video') -> Optional[Dict[str, Any]]:
        """Get download links with quality priority"""
        try:
            # First get video info to get the key
            video_info = self.get_video_info(youtube_url)
            if not video_info or not video_info.get('key'):
                logger.error("Failed to get video key")
                return None
            
            video_key = video_info['key']
            
            # Determine quality priorities
            if requested_quality == 'auto':
                qualities_to_try = VIDEO_QUALITY_PRIORITY
            else:
                # Try requested quality first, then fallback to priorities
                qualities_to_try = [requested_quality] + [q for q in VIDEO_QUALITY_PRIORITY if q != requested_quality]
            
            # Try each quality until we get a working link
            successful_quality = None
            download_url = None
            
            for quality in qualities_to_try:
                # Convert quality format (remove 'p' suffix for API)
                api_quality = quality.replace('p', '') if quality.endswith('p') else quality
                
                download_url = self._get_download_link(video_key, api_quality)
                if download_url:
                    successful_quality = quality
                    break
            
            if not download_url:
                logger.error("No download links available for any quality")
                return None
            
            # Prepare response
            download_data = {
                'title': video_info['title'],
                'duration': video_info['duration'],
                'thumbnail': video_info['thumbnail'],
                'quality': successful_quality,
                'format': format_type,
                'url': download_url,
                'video_id': video_info['video_id'],
                'uploader': video_info['uploader'],
                'file_size_estimate': self._estimate_file_size(successful_quality or '360p', video_info['duration'])
            }
            
            logger.info(f"Successfully got download link for: {video_info['title']} ({successful_quality})")
            return download_data
            
        except Exception as e:
            logger.error(f"Error getting download links: {e}")
            return None
    
    def _estimate_file_size(self, quality: str, duration: str) -> str:
        """Estimate file size based on quality and duration"""
        try:
            # Parse duration (format: "MM:SS" or "HH:MM:SS")
            duration_parts = duration.split(':')
            if len(duration_parts) == 2:
                minutes, seconds = map(int, duration_parts)
                total_seconds = minutes * 60 + seconds
            elif len(duration_parts) == 3:
                hours, minutes, seconds = map(int, duration_parts)
                total_seconds = hours * 3600 + minutes * 60 + seconds
            else:
                return "Unknown"
            
            # Rough bitrate estimates (kbps)
            bitrates = {
                '360p': 1000,
                '480p': 2500,
                '720p': 5000,
                '1080p': 8000
            }
            
            bitrate = bitrates.get(quality, 2500)  # Default to 480p bitrate
            estimated_mb = (bitrate * total_seconds) / (8 * 1024)  # Convert to MB
            
            if estimated_mb < 1:
                return f"{estimated_mb * 1024:.0f} KB"
            else:
                return f"{estimated_mb:.1f} MB"
                
        except Exception:
            return "Unknown"
