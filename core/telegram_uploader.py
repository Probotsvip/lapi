import asyncio
import aiohttp
import tempfile
import os
from typing import Dict, Any, Optional
from urllib.parse import urlparse

from .logging import LOGGER

logger = LOGGER(__name__)

class TelegramUploader:
    """Telegram Bot API uploader for permanent file storage"""
    
    def __init__(self):
        """Initialize Telegram uploader"""
        self.bot_token = os.getenv('BOT_TOKEN')  # Fixed to match environment variable
        self.channel_id = os.getenv('CHANNEL_ID')  # Fixed to match environment variable
        self.enabled = bool(self.bot_token and self.channel_id)
        
        if not self.enabled:
            logger.warning("Telegram credentials not provided - file storage disabled")
        else:
            logger.info("Telegram uploader initialized for permanent storage")
    
    def is_enabled(self) -> bool:
        """Check if Telegram uploader is enabled"""
        return self.enabled
    
    async def search_file_in_channel(self, video_id: str, quality: str = None) -> Optional[Dict[str, Any]]:
        """Search for existing file in Telegram channel by video ID
        Note: Telegram Bot API doesn't have search functionality,
        so we skip search and rely on database tracking instead
        """
        if not self.enabled:
            return None
        
        # Telegram Bot API doesn't support message search for bots
        # We rely on database tracking instead in db_manager.get_telegram_file()
        logger.debug(f"Search skipped - relying on database tracking for {video_id}")
        return None
    
    def _is_matching_message(self, message: Dict[str, Any], video_id: str, quality: str = None) -> bool:
        """Check if a Telegram message matches the search criteria"""
        caption = message.get('caption', '').lower()
        
        # Must contain video ID
        if f"#{video_id.lower()}" not in caption:
            return False
        
        # If quality specified, must match
        if quality and f"#{quality.lower()}" not in caption:
            return False
        
        # Must have video or document
        return bool(message.get('video') or message.get('document'))
    
    def _extract_file_info(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Extract file information from Telegram message"""
        try:
            file_info = {}
            
            # Get file from video or document
            if message.get('video'):
                video = message['video']
                file_info = {
                    'file_id': video['file_id'],
                    'file_size': video.get('file_size', 0),
                    'duration': video.get('duration', 0),
                    'format': 'video'
                }
            elif message.get('document'):
                document = message['document']
                file_info = {
                    'file_id': document['file_id'],
                    'file_size': document.get('file_size', 0),
                    'format': 'audio' if document.get('mime_type', '').startswith('audio') else 'video'
                }
            
            # Extract metadata from caption
            caption = message.get('caption', '')
            lines = caption.split('\n')
            
            for line in lines:
                if line.startswith('Title:'):
                    file_info['title'] = line.replace('Title:', '').strip()
                elif line.startswith('Quality:'):
                    file_info['quality'] = line.replace('Quality:', '').strip()
                elif line.startswith('Duration:'):
                    file_info['duration'] = line.replace('Duration:', '').strip()
            
            # Generate Telegram URL
            file_info['telegram_url'] = f"https://t.me/c/{str(self.channel_id).replace('-100', '')}/{message['message_id']}"
            
            return file_info
            
        except Exception as e:
            logger.error(f"Failed to extract file info: {e}")
            return {}
    
    async def upload_file(self, download_url: str, video_info: Dict[str, Any], quality: str) -> Optional[Dict[str, Any]]:
        """Download and upload file to Telegram channel"""
        if not self.enabled:
            return None
        
        temp_file_path = None
        
        try:
            logger.info(f"Starting background upload for {video_info.get('title', 'Unknown')} ({quality})")
            
            # Download file to temporary storage
            temp_file_path = await self._download_file(download_url)
            if not temp_file_path:
                return None
            
            # Upload to Telegram
            file_info = await self._upload_to_telegram(temp_file_path, video_info, quality)
            
            if file_info:
                logger.info(f"Successfully uploaded {video_info.get('title')} to Telegram")
                return file_info
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to upload file: {e}")
            return None
        
        finally:
            # Clean up temporary file
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except Exception as e:
                    logger.error(f"Failed to cleanup temp file: {e}")
    
    async def _download_file(self, url: str) -> Optional[str]:
        """Download file to temporary storage"""
        try:
            # Create temporary file
            temp_fd, temp_path = tempfile.mkstemp(suffix='.tmp')
            os.close(temp_fd)
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return None
                    
                    # Check file size (limit to 50MB for Telegram)
                    content_length = response.headers.get('content-length')
                    if content_length and int(content_length) > 50 * 1024 * 1024:
                        logger.warning("File too large for Telegram upload (>50MB)")
                        return None
                    
                    # Download file
                    with open(temp_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)
            
            return temp_path
            
        except Exception as e:
            logger.error(f"Failed to download file: {e}")
            return None
    
    async def _upload_to_telegram(self, file_path: str, video_info: Dict[str, Any], quality: str) -> Optional[Dict[str, Any]]:
        """Upload file to Telegram channel"""
        try:
            # Prepare file data with video ID prominent
            video_id = video_info.get('video_id', 'video')
            filename = f"[{video_id}]_{quality}.mp4"
            
            # Create caption with metadata and hashtags
            caption = self._create_caption(video_info, quality)
            
            # Upload file
            url = f"https://api.telegram.org/bot{self.bot_token}/sendVideo"
            
            logger.info(f"🔄 Starting Telegram upload for {filename}")
            logger.debug(f"Upload URL: {url}")
            logger.debug(f"Channel ID: {self.channel_id}")
            logger.debug(f"Caption: {caption[:100]}...")
            
            data = aiohttp.FormData()
            data.add_field('chat_id', self.channel_id)
            data.add_field('caption', caption)
            data.add_field('parse_mode', 'HTML')
            
            # Add file
            with open(file_path, 'rb') as f:
                data.add_field('video', f, filename=filename, content_type='video/mp4')
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, data=data) as response:
                        response_text = await response.text()
                        logger.debug(f"Telegram API response status: {response.status}")
                        logger.debug(f"Telegram API response: {response_text[:500]}...")
                        
                        if response.status == 200:
                            result = await response.json()
                            
                            if result.get('ok'):
                                message = result['result']
                                logger.info(f"✅ Successfully uploaded {filename} to Telegram")
                                
                                # Extract file info with stream URL
                                file_info = self._extract_file_info(message)
                                
                                # Add Telegram stream URL
                                if file_info and file_info.get('file_id'):
                                    stream_url = await self.get_file_url(file_info['file_id'])
                                    if stream_url:
                                        file_info['telegram_stream_url'] = stream_url
                                        logger.info(f"📺 Stream URL generated: {stream_url[:100]}...")
                                
                                return file_info
                            else:
                                logger.error(f"❌ Telegram API error: {result.get('description', 'Unknown error')}")
                                return None
                        else:
                            logger.error(f"❌ HTTP error {response.status}: {response_text}")
                            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to upload to Telegram: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return None
    
    def _create_caption(self, video_info: Dict[str, Any], quality: str) -> str:
        """Create caption with metadata and searchable hashtags"""
        video_id = video_info.get('video_id', 'unknown')
        title = video_info.get('title', 'Unknown Title')
        duration = video_info.get('duration', 'Unknown')
        uploader = video_info.get('uploader', 'Unknown')
        
        caption = f"""🎬 <b>{title}</b>

📺 <b>Video ID:</b> <code>{video_id}</code>
🎯 <b>Quality:</b> {quality}
⏱️ <b>Duration:</b> {duration}
👤 <b>Uploader:</b> {uploader}

🏷️ #{video_id} #{quality} #youtube_downloader
📱 Stream URL available via bot"""
        
        return caption
    
    async def get_file_url(self, file_id: str) -> Optional[str]:
        """Get direct download URL for Telegram file"""
        if not self.enabled:
            return None
        
        try:
            # Get file path
            url = f"https://api.telegram.org/bot{self.bot_token}/getFile"
            params = {'file_id': file_id}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data.get('ok'):
                            file_path = data['result']['file_path']
                            return f"https://api.telegram.org/file/bot{self.bot_token}/{file_path}"
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get file URL: {e}")
            return None
    
    def start_background_upload(self, download_url: str, video_info: Dict[str, Any], quality: str, db_manager):
        """Start background upload in thread"""
        if not self.enabled:
            return
        
        def upload_task():
            try:
                import asyncio
                import threading
                
                # Create new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                async def async_upload():
                    video_id = video_info.get('video_id')
                    
                    # Mark as processing in database
                    if db_manager.is_connected():
                        await db_manager.mark_processing(video_id, quality)
                    
                    # Upload file
                    file_info = await self.upload_file(download_url, video_info, quality)
                    
                    # Store in database if successful
                    if file_info and db_manager.is_connected():
                        await db_manager.store_telegram_file(video_id, quality, file_info)
                        logger.info(f"✅ Background upload completed for {video_id} ({quality})")
                
                # Run async operations in the new loop
                try:
                    loop.run_until_complete(async_upload())
                finally:
                    loop.close()
                
            except Exception as e:
                logger.error(f"❌ Background upload failed: {e}")
                import traceback
                logger.error(f"Full traceback: {traceback.format_exc()}")
        
        # Start in background thread
        import threading
        thread = threading.Thread(target=upload_task, daemon=True)
        thread.start()
        logger.info(f"🚀 Started background upload for {video_info.get('title')} ({quality})")