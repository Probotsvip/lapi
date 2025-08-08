import os
import logging
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
    """Get video metadata with fast caching"""
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({
                'success': False,
                'error': 'URL parameter is required'
            }), 400

        url = data['url']
        logger.info(f"Video info requested for: {url}")

        # Check cache first
        cache_key = f"info:{url}"
        cached_info = cache_manager.get(cache_key)
        
        if cached_info:
            app_stats['cache_hits'] += 1
            logger.info("Returning cached video info")
            return jsonify({
                'success': True,
                'cached': True,
                'data': cached_info
            })

        # Get fresh data
        start_time = time.time()
        video_info = youtube_processor.get_video_info(url)
        
        if video_info:
            # Cache for 1 hour
            cache_manager.set(cache_key, video_info, ttl=3600)
            
            response_time = time.time() - start_time
            logger.info(f"Video info retrieved in {response_time:.2f}s")
            
            return jsonify({
                'success': True,
                'cached': False,
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
    """Get download links with quality priority and Telegram storage"""
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

        # Check cache first
        cache_key = f"download:{url}:{quality}:{format_type}"
        cached_download = cache_manager.get(cache_key)
        
        if cached_download:
            app_stats['cache_hits'] += 1
            logger.info("Returning cached download links")
            return jsonify({
                'success': True,
                'cached': True,
                'data': cached_download
            })

        # Get fresh download data
        start_time = time.time()
        download_data = youtube_processor.get_download_links(url, quality, format_type)
        
        if download_data:
            # Telegram upload disabled
            download_data['permanent_storage'] = False

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
