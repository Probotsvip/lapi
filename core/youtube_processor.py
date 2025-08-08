import requests
import json
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import time
import re
from typing import Dict, Any, Optional, List
import logging
import hashlib

from config import AES_KEY, VIDEO_QUALITY_PRIORITY, API_TIMEOUT

logger = logging.getLogger(__name__)

class YouTubeProcessor:
    """YouTube processor adapted from provided JavaScript code with AES decryption"""
    
    def __init__(self):
        self.hex_key = AES_KEY
        self.session = requests.Session()
        # Set timeout in request calls instead
    
    def extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from YouTube URL"""
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com\/v\/([a-zA-Z0-9_-]{11})',
            r'youtube\.com\/watch\?.*?v=([a-zA-Z0-9_-]{11})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
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
    
    def _decrypt_data(self, response_data: str) -> Dict[str, Any]:
        """Decrypt AES-CBC encrypted data from savetube.me or return direct JSON"""
        try:
            # First try direct JSON parsing (many APIs return plain JSON now)
            try:
                data = json.loads(response_data)
                logger.debug("Response is direct JSON")
                return data
            except json.JSONDecodeError:
                pass
            
            # If not JSON, try base64 decoding + AES decryption
            try:
                encrypted_data = self._base64_to_bytes(response_data)
                
                if len(encrypted_data) < 16:
                    raise ValueError("Encrypted data too short")
                
                # Extract IV (first 16 bytes) and ciphertext
                iv = encrypted_data[:16]
                ciphertext = encrypted_data[16:]
                
                # Try multiple key derivation methods
                # Common savetube.me keys from various sources
                possible_keys = [
                    "2aQF@#4sJzY9Xp8G6vBn1Kw5Eq3Rt7Mu",  # Current key
                    "savetube2024keyfordownload321",  # Common pattern
                    "ytdownloader2024secretkey",      # Alternative
                    "c8b8f8c8f8c8f8c8f8c8f8c8f8c8f8c8",  # Hex pattern
                    "SaveTubeMeApiKey2024Secret32Char"  # Service name based
                ]
                
                key_variants = []
                for possible_key in possible_keys:
                    # Direct string to bytes (32 bytes)
                    key_variants.append(possible_key.encode('utf-8')[:32].ljust(32, b'\x00'))
                    # MD5 hash doubled (32 bytes)
                    key_variants.append(hashlib.md5(possible_key.encode()).digest() * 2)
                    # SHA256 (32 bytes)
                    key_variants.append(hashlib.sha256(possible_key.encode()).digest())
                    # Try hex decode if it's valid hex
                    if len(possible_key) >= 32 and all(c in '0123456789abcdefABCDEF' for c in possible_key[:32]):
                        try:
                            key_variants.append(bytes.fromhex(possible_key[:32]))
                        except:
                            pass
                
                for key_bytes in key_variants:
                    if key_bytes is None:
                        continue
                        
                    try:
                        # Decrypt using AES-CBC
                        cipher = AES.new(key_bytes[:32], AES.MODE_CBC, iv)
                        decrypted = cipher.decrypt(ciphertext)
                        
                        # Try proper unpadding first
                        try:
                            unpadded = unpad(decrypted, AES.block_size)
                            logger.debug(f"Successfully unpadded data, length: {len(unpadded)}")
                        except Exception as unpad_error:
                            logger.debug(f"Unpadding failed: {unpad_error}, trying manual padding removal")
                            # If unpadding fails, try manual padding removal
                            unpadded = decrypted.rstrip(b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10')
                        
                        # Convert to string and parse JSON
                        decrypted_text = unpadded.decode('utf-8', errors='ignore')
                        logger.debug(f"Decrypted text preview: {decrypted_text[:200]}...")
                        
                        # Clean up any non-JSON content
                        start = decrypted_text.find('{')
                        end = decrypted_text.rfind('}') + 1
                        if start >= 0 and end > start:
                            clean_json = decrypted_text[start:end]
                            logger.debug(f"Clean JSON preview: {clean_json[:200]}...")
                            return json.loads(clean_json)
                        else:
                            logger.debug(f"No valid JSON braces found, trying to parse full text")
                            # Try parsing the entire decrypted text
                            return json.loads(decrypted_text.strip())
                            
                    except Exception as inner_e:
                        logger.debug(f"Key variant {key_bytes[:8].hex() if key_bytes else 'None'}... failed: {str(inner_e)[:50]}")
                        continue
                
                raise ValueError("All decryption methods failed")
                
            except Exception as decrypt_e:
                logger.error(f"Decryption failed: {decrypt_e}")
                raise ValueError(f"Failed to decrypt data: {decrypt_e}")
            
        except Exception as e:
            logger.error(f"Data processing error: {e}")
            raise ValueError(f"Failed to process response: {e}")
    
    def _get_cdn(self) -> str:
        """Get CDN endpoint from savetube.me"""
        try:
            response = self.session.get("https://media.savetube.me/api/random-cdn", timeout=API_TIMEOUT)
            response.raise_for_status()
            
            data = response.json()
            if data and 'cdn' in data:
                logger.debug(f"Got CDN: {data['cdn']}")
                return data['cdn']
        except Exception as e:
            logger.error(f"Failed to get CDN: {e}")
        
        # Fallback CDNs
        fallback_cdns = [
            'cdn404.savetube.su',
            'cdn403.savetube.su', 
            'cdn402.savetube.su',
            'cdn401.savetube.su'
        ]
        import random
        selected = random.choice(fallback_cdns)
        logger.debug(f"Using fallback CDN: {selected}")
        return selected
    
    def _make_api_request(self, cdn: str, video_id: str) -> Optional[Dict[str, Any]]:
        """Make API request to get video data"""
        try:
            url = f"https://{cdn}/v2/info"
            
            payload = {
                'url': f'https://www.youtube.com/watch?v={video_id}',
                'vt': 'youtube'
            }
            
            logger.debug(f"Making API request to: {url}")
            response = self.session.post(url, json=payload, timeout=API_TIMEOUT)
            response.raise_for_status()
            
            response_data = response.text.strip()
            
            if not response_data:
                logger.error("Empty response from API")
                return None
            
            logger.debug(f"Raw response length: {len(response_data)}")
            logger.debug(f"Response preview: {response_data[:100]}...")
            
            # Process the response
            data = self._decrypt_data(response_data)
            logger.debug(f"Successfully processed data for video: {video_id}")
            return data
            
        except Exception as e:
            logger.error(f"API request failed: {e}")
            return None
    
    def get_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """Get basic video information"""
        try:
            video_id = self.extract_video_id(url)
            if not video_id:
                logger.error("Invalid YouTube URL")
                return None
            
            logger.info(f"Processing video ID: {video_id}")
            
            # Get CDN and make request
            cdn = self._get_cdn()
            data = self._make_api_request(cdn, video_id)
            
            if not data:
                return None
            
            # Debug: Log the actual data structure
            logger.debug(f"API response structure: {list(data.keys()) if isinstance(data, dict) else type(data)}")
            logger.debug(f"Full API response: {data}")
            
            # Extract video information
            if 'data' in data and isinstance(data['data'], dict):
                video_data = data['data']
                
                return {
                    'video_id': video_id,
                    'title': video_data.get('title', 'Unknown Title'),
                    'duration': video_data.get('duration', 'Unknown'),
                    'thumbnail': video_data.get('thumbnail') or f'https://img.youtube.com/vi/{video_id}/maxresdefault.jpg',
                    'uploader': video_data.get('uploader', 'YouTube'),
                    'view_count': video_data.get('view_count', 0)
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting video info: {e}")
            return None
    
    def get_download_links(self, url: str, quality: str = 'auto', format_type: str = 'video') -> Optional[Dict[str, Any]]:
        """Get download links for video"""
        try:
            video_id = self.extract_video_id(url)
            if not video_id:
                logger.error("Invalid YouTube URL")
                return None
            
            logger.info(f"Getting download links for: {video_id}")
            
            # Get CDN and make request
            cdn = self._get_cdn()
            data = self._make_api_request(cdn, video_id)
            
            if not data:
                return None
            
            # Extract download information
            logger.debug(f"API Response structure: {list(data.keys()) if isinstance(data, dict) else type(data)}")
            
            # The 'data' field contains encrypted video information, need to decrypt it first
            if 'data' in data and data.get('status') == True:
                encrypted_data = data['data']
                logger.info(f"🔓 Decrypting video data...")
                
                # Decrypt the data field
                try:
                    decrypted_data = self._decrypt_data(encrypted_data)
                    logger.debug(f"Decrypted data keys: {list(decrypted_data.keys()) if isinstance(decrypted_data, dict) else type(decrypted_data)}")
                    
                    if isinstance(decrypted_data, dict):
                        video_data = decrypted_data
                    else:
                        logger.error("❌ Decrypted data is not a dictionary")
                        return None
                        
                except Exception as decrypt_error:
                    logger.error(f"❌ Failed to decrypt video data: {decrypt_error}")
                    return None
                
                # Get available qualities from decrypted data
                download_links = video_data.get('download_links', {})
                
                # Try alternative key names if download_links is empty
                if not download_links:
                    download_links = video_data.get('links', {})
                if not download_links:
                    download_links = video_data.get('formats', {})
                if not download_links:
                    download_links = video_data.get('qualities', {})
                
                logger.info(f"📊 Available download qualities: {list(download_links.keys()) if download_links else 'None found'}")
                logger.debug(f"Full video data structure: {list(video_data.keys())}")
                
                # Select quality
                selected_quality = quality
                selected_url = None
                
                if quality == 'auto':
                    # Try quality priority
                    for q in VIDEO_QUALITY_PRIORITY:
                        if q in download_links:
                            selected_quality = q
                            selected_url = download_links[q]
                            break
                else:
                    selected_url = download_links.get(quality)
                
                if not selected_url and download_links:
                    # Fallback to any available quality
                    selected_quality = list(download_links.keys())[0]
                    selected_url = download_links[selected_quality]
                
                if selected_url:
                    logger.info(f"✅ Selected download URL for {selected_quality}: {selected_url[:100]}...")
                    return {
                        'title': video_data.get('title', 'Unknown Title'),
                        'quality': selected_quality,
                        'format': format_type,
                        'url': selected_url,
                        'duration': video_data.get('duration', 'Unknown'),
                        'file_size_estimate': self._estimate_file_size(video_data.get('duration', '0:00'), selected_quality)
                    }
                else:
                    logger.error(f"❌ No download URL found for quality: {quality}. Available: {list(download_links.keys())}")
            
            logger.error(f"❌ Invalid API response structure or status = False")
            return None
            
        except Exception as e:
            logger.error(f"Error getting download links: {e}")
            return None
    
    def _estimate_file_size(self, duration: str, quality: str) -> str:
        """Estimate file size based on duration and quality"""
        try:
            # Parse duration (format: "mm:ss" or "hh:mm:ss")
            parts = duration.split(':')
            if len(parts) == 2:
                minutes, seconds = map(int, parts)
                total_seconds = minutes * 60 + seconds
            elif len(parts) == 3:
                hours, minutes, seconds = map(int, parts)
                total_seconds = hours * 3600 + minutes * 60 + seconds
            else:
                return "Unknown"
            
            # Estimate based on quality (MB per minute)
            quality_rates = {
                '1080p': 12,  # 12 MB/min
                '720p': 8,    # 8 MB/min
                '480p': 5,    # 5 MB/min
                '360p': 3     # 3 MB/min
            }
            
            rate = quality_rates.get(quality, 5)  # Default 5 MB/min
            estimated_mb = (total_seconds / 60) * rate
            
            if estimated_mb > 1024:
                return f"{estimated_mb / 1024:.1f} GB"
            else:
                return f"{estimated_mb:.1f} MB"
                
        except:
            return "Unknown"