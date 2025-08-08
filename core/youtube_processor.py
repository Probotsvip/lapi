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
        """Decrypt AES-CBC encrypted data using exact JavaScript method"""
        try:
            # First try direct JSON parsing
            try:
                data = json.loads(response_data)
                logger.debug("Response is direct JSON")
                return data
            except json.JSONDecodeError:
                pass

            # Base64 decode + AES decryption (following JavaScript exactly)
            try:
                # Clean and decode base64 (exactly like JavaScript b64Byte method)
                clean_b64 = response_data.replace(" ", "").replace("\n", "")
                encrypted_data = base64.b64decode(clean_b64)
                
                if len(encrypted_data) < 16:
                    raise ValueError("Data too short")

                # Extract IV and ciphertext (exactly like JavaScript)
                iv = encrypted_data[:16]
                ciphertext = encrypted_data[16:]

                # Convert hex key to bytes (exactly like JavaScript uint8 method)
                key_bytes = bytes.fromhex(self.hex_key)
                logger.debug(f"✅ Using hex key: {self.hex_key}, converted to {len(key_bytes)} bytes")

                # AES-CBC decryption (exactly like JavaScript crypto.subtle.decrypt)
                cipher = AES.new(key_bytes, AES.MODE_CBC, iv)
                decrypted = cipher.decrypt(ciphertext)

                # Convert to text and parse JSON (exactly like JavaScript TextDecoder)
                try:
                    # Try proper PKCS7 unpadding first
                    unpadded = unpad(decrypted, AES.block_size)
                    decrypted_text = unpadded.decode('utf-8')
                except:
                    # If unpadding fails, try without unpadding (some data might not be padded)
                    decrypted_text = decrypted.decode('utf-8', errors='ignore')
                    # Remove null bytes and common padding bytes
                    decrypted_text = decrypted_text.rstrip('\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10')

                logger.debug(f"Decrypted text preview: {decrypted_text[:200]}...")

                # Parse JSON (exactly like JavaScript JSON.parse)
                return json.loads(decrypted_text.strip())

            except Exception as decrypt_e:
                logger.error(f"AES decryption failed: {decrypt_e}")
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
                'url': f'https://www.youtube.com/watch?v={video_id}'
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

            # Extract video information - Follow same pattern as download
            if 'data' in data and data.get('status') == True:
                encrypted_data = data['data']
                logger.info(f"🔓 Decrypting video info data...")

                try:
                    video_info = self._decrypt_data(encrypted_data)
                    logger.debug(f"Video info keys: {list(video_info.keys()) if isinstance(video_info, dict) else type(video_info)}")

                    if not isinstance(video_info, dict):
                        logger.error("❌ Decrypted video info is not a dictionary")
                        return None

                    return {
                        'video_id': video_id,
                        'title': video_info.get('title', 'Unknown Title'),
                        'duration': video_info.get('durationLabel', 'Unknown'),
                        'thumbnail': video_info.get('thumbnail') or f'https://img.youtube.com/vi/{video_id}/maxresdefault.jpg',
                        'uploader': 'YouTube',
                        'view_count': video_info.get('view_count', 0)
                    }

                except Exception as decrypt_error:
                    logger.error(f"❌ Failed to decrypt video info: {decrypt_error}")
                    return None

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

            # Get CDN and make request with retry logic
            cdn = self._get_cdn()
            data = self._make_api_request(cdn, video_id)

            if not data:
                logger.error(f"❌ Failed to get video data from all CDN endpoints for: {video_id}")
                return None

            # Follow JerryCoder approach: First get video info, then use key to get download link
            logger.debug(f"API Response structure: {list(data.keys()) if isinstance(data, dict) else type(data)}")

            # Step 1: Get and decrypt video info to extract the video key
            if 'data' in data and data.get('status') == True:
                encrypted_data = data['data']
                logger.info(f"🔓 Decrypting video info data...")

                try:
                    video_info = self._decrypt_data(encrypted_data)
                    logger.debug(f"Video info keys: {list(video_info.keys()) if isinstance(video_info, dict) else type(video_info)}")

                    if not isinstance(video_info, dict):
                        logger.error("❌ Decrypted video info is not a dictionary")
                        return None

                    # Extract the video key (this is crucial for the download step)
                    video_key = video_info.get('key')
                    if not video_key:
                        logger.error("❌ No video key found in decrypted data")
                        return None

                    logger.info(f"✅ Video key extracted: {video_key[:20]}...")

                except Exception as decrypt_error:
                    logger.error(f"❌ Failed to decrypt video info: {decrypt_error}")
                    return None

                # Step 2: Use the video key to get download link from /download endpoint
                logger.info(f"📥 Getting download link for quality {quality}...")
                download_url = self._get_download_link(video_key, quality)

                if download_url:
                    logger.info(f"✅ Download URL obtained: {download_url[:100]}...")

                    # Resolve "auto" quality to actual quality for consistent storage
                    resolved_quality = quality
                    if quality == 'auto':
                        resolved_quality = '360p'  # Default resolution for auto

                    return {
                        'title': video_info.get('title', 'Unknown Title'),
                        'quality': resolved_quality,  # Return resolved quality, not original request
                        'format': format_type,
                        'url': download_url,
                        'duration': video_info.get('durationLabel', 'Unknown'),
                        'file_size_estimate': self._estimate_file_size(video_info.get('durationLabel', '0:00'), resolved_quality)
                    }
                else:
                    logger.error(f"❌ Failed to get download link for quality: {quality}")

            logger.error(f"❌ Invalid API response structure or status = False")
            return None

        except Exception as e:
            logger.error(f"Error getting download links: {e}")
            return None

    def _get_download_link(self, video_key: str, quality: str) -> Optional[str]:
        """Get download link using video key - following JerryCoder approach exactly"""
        retries = 5  # Increased retries like JavaScript version

        # Convert quality to numeric format (JavaScript approach)
        quality_map = {
            'auto': '360',
            '360p': '360', 
            '480p': '480',
            '720p': '720',
            '1080p': '1080'
        }

        # Clean quality value - extract just the number like JavaScript
        numeric_quality = quality_map.get(quality, quality)
        if 'p' in numeric_quality:
            numeric_quality = numeric_quality.replace('p', '')
        # Keep only numbers
        numeric_quality = ''.join(filter(str.isdigit, numeric_quality)) or '360'

        logger.debug(f"Using quality: {numeric_quality} (converted from: {quality})")

        while retries > 0:
            try:
                # Get CDN for download request - exactly like JavaScript
                cdn = self._get_cdn()

                # Make download request with video key - EXACT JavaScript payload
                url = f"https://{cdn}/download"
                payload = {
                    'downloadType': 'video',
                    'quality': numeric_quality,  # Use numeric quality like JavaScript
                    'key': video_key
                }

                logger.debug(f"Making download request to: {url} with payload: {payload}")
                response = self.session.post(url, json=payload, timeout=API_TIMEOUT)
                response.raise_for_status()

                download_data = response.json()
                logger.debug(f"Download response: {download_data}")

                # Check response structure exactly like JavaScript
                if download_data.get('status') and download_data.get('data', {}).get('downloadUrl'):
                    download_url = download_data['data']['downloadUrl']
                    logger.info(f"✅ Download link retrieved successfully for quality {numeric_quality}")
                    return download_url
                else:
                    logger.warning(f"⚠️ Download response invalid: {download_data}, retrying... ({retries-1} left)")

            except Exception as e:
                logger.warning(f"⚠️ Download request failed: {e}, retrying... ({retries-1} left)")

            retries -= 1

        logger.error("❌ Failed to get download link after all retries")
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