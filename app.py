import os
import logging
import asyncio
from flask import Flask, request, jsonify, render_template, redirect, url_for
from werkzeug.middleware.proxy_fix import ProxyFix
import threading
import time
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Import core modules
from core.cache_manager import SmartCacheManager
from core.database_manager import MongoDBManager
from core.youtube_processor import YouTubeProcessor
from core.telegram_uploader import TelegramUploader
from core.proxy_manager import ProxyManager

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "fallback_secret_key_for_development")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Initialize components
cache_manager = SmartCacheManager()
db_manager = MongoDBManager()
youtube_processor = YouTubeProcessor()
telegram_uploader = TelegramUploader()
proxy_manager = ProxyManager()

# Global stats
app_stats = {
    'requests_total': 0,
    'cache_hits': 0,
    'telegram_uploads': 0,
    'start_time': datetime.now(),
    'active_requests': 0
}

@app.before_request
def before_request():
    app_stats['requests_total'] += 1
    app_stats['active_requests'] += 1

@app.after_request
def after_request(response):
    app_stats['active_requests'] -= 1
    return response

@app.route('/')
def index():
    """Professional API documentation page"""
    return render_template('index.html')

@app.route('/api/video-info', methods=['POST'])
def video_info():
    """Get video metadata - Telegram-first approach"""
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({
                'success': False,
                'error': 'URL parameter is required'
            }), 400

        url = data['url']
        logger.info(f"Video info requested for: {url}")

        # Extract video ID for Telegram tracking
        video_id = youtube_processor.extract_video_id(url)
        if not video_id:
            return jsonify({
                'success': False,
                'error': 'Invalid YouTube URL'
            }), 400

        # Step 1: Check Telegram channel first via database
        telegram_file = asyncio.run(db_manager.get_telegram_file(video_id))
        if telegram_file:
            logger.info(f"Found video info in Telegram storage: {video_id}")
            return jsonify({
                'success': True,
                'cached': True,
                'source': 'telegram',
                'data': {
                    'video_id': video_id,
                    'title': telegram_file.get('title', 'Unknown'),
                    'duration': telegram_file.get('duration', 'Unknown'),
                    'uploader': 'YouTube',
                    'thumbnail': f'https://img.youtube.com/vi/{video_id}/maxresdefault.jpg'
                }
            })

        # Step 2: Hit external API if not found in Telegram
        start_time = time.time()
        video_info = youtube_processor.get_video_info(url)
        
        if video_info:
            response_time = time.time() - start_time
            logger.info(f"Video info retrieved from external API in {response_time:.2f}s")
            
            # Step 3: Return response to user immediately
            return jsonify({
                'success': True,
                'cached': False,
                'source': 'external_api',
                'response_time': response_time,
                'data': video_info
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to retrieve video information'
            }), 400

    except Exception as e:
        logger.error(f"Error in video_info: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500

@app.route('/api/download', methods=['POST'])
def download():
    """Get download links - Telegram-first with background processing"""
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({
                'success': False,
                'error': 'URL parameter is required'
            }), 400

        url = data['url']
        quality = data.get('quality', 'auto')  # auto, 1080p, 720p, 480p, 360p
        format_type = data.get('format', 'video')  # video, audio
        
        logger.info(f"Download requested for: {url}, quality: {quality}, format: {format_type}")

        # Extract video ID for Telegram tracking
        video_id = youtube_processor.extract_video_id(url)
        if not video_id:
            return jsonify({
                'success': False,
                'error': 'Invalid YouTube URL'
            }), 400

        # Step 1: Check Telegram channel first
        logger.info(f"🔍 STEP 1: Checking Telegram channel for video: {video_id}")
        quality_param = None if quality == 'auto' else quality
        telegram_file = asyncio.run(db_manager.get_telegram_file(video_id, quality_param))
        if telegram_file:
            logger.info(f"✅ FOUND in Telegram storage: {video_id} ({telegram_file.get('quality')})")
            
            # Get direct Telegram download URL
            telegram_url = None
            if telegram_file.get('telegram_file_id') and telegram_uploader.is_enabled():
                telegram_url = asyncio.run(telegram_uploader.get_file_url(telegram_file['telegram_file_id']))
            
            return jsonify({
                'success': True,
                'cached': True,
                'source': 'telegram',
                'data': {
                    'title': telegram_file.get('title', 'Unknown'),
                    'quality': telegram_file.get('quality', quality),
                    'format': telegram_file.get('format', format_type),
                    'duration': telegram_file.get('duration'),
                    'url': telegram_url or telegram_file.get('telegram_url'),
                    'telegram_url': telegram_file.get('telegram_url'),
                    'permanent_storage': True,
                    'file_size_estimate': telegram_file.get('file_size', 'Unknown')
                }
            })

        # Check if already processing to avoid duplicates
        actual_quality = quality if quality != 'auto' else '720p'  # Default for auto
        is_processing = asyncio.run(db_manager.is_processing(video_id, actual_quality))
        if is_processing:
            logger.info(f"File already being processed: {video_id} ({actual_quality})")

        # Step 2: Hit external API if not found in Telegram
        logger.info(f"❌ NOT FOUND in Telegram channel for: {video_id}")
        logger.info(f"🌐 STEP 2: Hitting external savetube.me API for: {video_id}")
        start_time = time.time()
        download_data = youtube_processor.get_download_links(url, quality, format_type)
        
        if download_data:
            response_time = time.time() - start_time
            logger.info(f"✅ EXTERNAL API SUCCESS: Download links retrieved in {response_time:.2f}s")
            logger.info(f"📊 Download data received: {list(download_data.keys()) if download_data else 'None'}")
            
            # Get video info for background processing
            video_info = youtube_processor.get_video_info(url)
            if video_info:
                video_info['video_id'] = video_id
            
            # Step 4: Start background download and upload to Telegram (if enabled and not already processing)
            if telegram_uploader.is_enabled() and video_info and not is_processing:
                asyncio.run(telegram_uploader.start_background_upload(
                    download_data['url'],
                    video_info,
                    download_data['quality'],
                    db_manager
                ))
                logger.info(f"Started background Telegram upload for {video_id}")
            
            # Add permanent storage info
            download_data['permanent_storage'] = telegram_uploader.is_enabled()
            download_data['background_processing'] = telegram_uploader.is_enabled() and not is_processing
            
            # Step 3: Return response to user immediately
            return jsonify({
                'success': True,
                'cached': False,
                'source': 'external_api',
                'response_time': response_time,
                'data': download_data
            })

            # Create masked URLs
            if 'url' in download_data:
                masked_id = proxy_manager.create_masked_url(download_data['url'], download_data['title'])
                download_data['masked_url'] = f"/api/proxy/{masked_id}/{download_data['title']}.mp4"

            # Cache for 30 minutes
            cache_manager.set(cache_key, download_data, ttl=1800)
            
            response_time = time.time() - start_time
            logger.info(f"Download links retrieved in {response_time:.2f}s")
            
            return jsonify({
                'success': True,
                'cached': False,
                'response_time': response_time,
                'data': download_data
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to retrieve download links'
            }), 400

    except Exception as e:
        logger.error(f"Error in download: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500

@app.route('/api/proxy/<masked_id>/<filename>')
def proxy_download(masked_id, filename):
    """Masked download URLs for privacy"""
    try:
        original_url = proxy_manager.get_original_url(masked_id)
        if not original_url:
            return jsonify({
                'success': False,
                'error': 'Invalid or expired download link'
            }), 404

        # Redirect to original URL
        return redirect(original_url)

    except Exception as e:
        logger.error(f"Error in proxy_download: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Proxy error'
        }), 500

@app.route('/api/stats')
def stats():
    """System performance statistics"""
    uptime = datetime.now() - app_stats['start_time']
    
    return jsonify({
        'success': True,
        'data': {
            'uptime_seconds': int(uptime.total_seconds()),
            'uptime_human': str(uptime).split('.')[0],
            'requests_total': app_stats['requests_total'],
            'cache_hits': app_stats['cache_hits'],
            'cache_hit_rate': round((app_stats['cache_hits'] / max(app_stats['requests_total'], 1)) * 100, 2),
            'telegram_uploads': app_stats['telegram_uploads'],
            'active_requests': app_stats['active_requests'],
            'memory_cache_size': cache_manager.get_cache_size(),
            'mongodb_connection': db_manager.is_connected()
        }
    })

@app.route('/api/cache/clear', methods=['POST'])
def clear_cache():
    """Clear application cache"""
    try:
        cleared_items = cache_manager.clear_cache()
        logger.info(f"Cache cleared: {cleared_items} items removed")
        
        return jsonify({
            'success': True,
            'message': f'Cache cleared successfully. {cleared_items} items removed.'
        })

    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to clear cache: {str(e)}'
        }), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
