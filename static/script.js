// YouTube Downloader API - Frontend JavaScript

class YouTubeDownloaderAPI {
    constructor() {
        this.baseUrl = '';
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadStats();
        this.startStatsRefresh();
    }

    bindEvents() {
        // Button event listeners
        document.getElementById('btnGetInfo').addEventListener('click', () => this.getVideoInfo());
        document.getElementById('btnDownload').addEventListener('click', () => this.downloadVideo());
        document.getElementById('btnClearCache').addEventListener('click', () => this.clearCache());

        // Enter key support for URL input
        document.getElementById('testUrl').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.getVideoInfo();
            }
        });

        // Smooth scrolling for navigation links
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });
    }

    async makeRequest(endpoint, method = 'GET', data = null) {
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            }
        };

        if (data) {
            options.body = JSON.stringify(data);
        }

        try {
            const response = await fetch(`${this.baseUrl}${endpoint}`, options);
            return await response.json();
        } catch (error) {
            console.error('API Request failed:', error);
            return {
                success: false,
                error: `Network error: ${error.message}`
            };
        }
    }

    showLoading(show = true) {
        const spinner = document.getElementById('loadingSpinner');
        const buttons = document.querySelectorAll('#btnGetInfo, #btnDownload, #btnClearCache');
        
        if (show) {
            spinner.classList.remove('d-none');
            buttons.forEach(btn => btn.disabled = true);
        } else {
            spinner.classList.add('d-none');
            buttons.forEach(btn => btn.disabled = false);
        }
    }

    validateYouTubeUrl(url) {
        const patterns = [
            /^https?:\/\/(www\.)?(youtube\.com|youtu\.be)\/.+$/,
            /^https?:\/\/(www\.)?youtube\.com\/watch\?v=[\w-]+/,
            /^https?:\/\/youtu\.be\/[\w-]+/
        ];
        
        return patterns.some(pattern => pattern.test(url));
    }

    formatDuration(seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;
        
        if (hours > 0) {
            return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        }
        return `${minutes}:${secs.toString().padStart(2, '0')}`;
    }

    formatFileSize(bytes) {
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        if (bytes === 0) return '0 Bytes';
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
    }

    showResult(data, title, isError = false) {
        const resultsContainer = document.getElementById('testResults');
        
        const resultCard = document.createElement('div');
        resultCard.className = `result-card ${isError ? 'result-error' : 'result-success'} animate-fade-in-up`;
        
        const timestamp = new Date().toLocaleTimeString();
        const responseTime = data.response_time ? ` (${data.response_time.toFixed(2)}s)` : '';
        
        resultCard.innerHTML = `
            <div class="result-header">
                <h5 class="result-title">
                    <i data-feather="${isError ? 'x-circle' : 'check-circle'}" class="me-2"></i>
                    ${title}
                </h5>
                <span class="result-time">${timestamp}${responseTime}</span>
            </div>
            <div class="result-data">
                <pre><code>${JSON.stringify(data, null, 2)}</code></pre>
            </div>
        `;
        
        resultsContainer.appendChild(resultCard);
        
        // Replace feather icons
        feather.replace();
        
        // Scroll to result
        resultCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        
        // Auto-remove old results (keep last 3)
        const results = resultsContainer.querySelectorAll('.result-card');
        if (results.length > 3) {
            results[0].remove();
        }
    }

    async getVideoInfo() {
        const url = document.getElementById('testUrl').value.trim();
        
        if (!url) {
            this.showResult({ error: 'Please enter a YouTube URL' }, 'Validation Error', true);
            return;
        }
        
        if (!this.validateYouTubeUrl(url)) {
            this.showResult({ error: 'Invalid YouTube URL format' }, 'Validation Error', true);
            return;
        }
        
        this.showLoading(true);
        
        const response = await this.makeRequest('/api/video-info', 'POST', { url });
        
        this.showLoading(false);
        
        if (response.success) {
            this.showResult(response, 'Video Info Retrieved');
        } else {
            this.showResult(response, 'Error Getting Video Info', true);
        }
    }

    async downloadVideo() {
        const url = document.getElementById('testUrl').value.trim();
        const quality = document.getElementById('testQuality').value;
        const format = document.getElementById('testFormat').value;
        
        if (!url) {
            this.showResult({ error: 'Please enter a YouTube URL' }, 'Validation Error', true);
            return;
        }
        
        if (!this.validateYouTubeUrl(url)) {
            this.showResult({ error: 'Invalid YouTube URL format' }, 'Validation Error', true);
            return;
        }
        
        this.showLoading(true);
        
        const response = await this.makeRequest('/api/download', 'POST', {
            url,
            quality,
            format
        });
        
        this.showLoading(false);
        
        if (response.success) {
            this.showResult(response, 'Download Link Generated');
            
            // Show download options
            if (response.data && response.data.url) {
                setTimeout(() => {
                    this.showDownloadOptions(response.data);
                }, 1000);
            }
        } else {
            this.showResult(response, 'Error Getting Download Link', true);
        }
    }

    showDownloadOptions(data) {
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.innerHTML = `
            <div class="modal-dialog modal-lg">
                <div class="modal-content bg-dark text-light">
                    <div class="modal-header border-secondary">
                        <h5 class="modal-title">
                            <i data-feather="download" class="me-2"></i>
                            Download Ready
                        </h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="mb-4">
                            <h6 class="text-primary">Video Information:</h6>
                            <div class="bg-darker p-3 rounded">
                                <p class="mb-2"><strong>Title:</strong> ${data.title}</p>
                                <p class="mb-2"><strong>Quality:</strong> ${data.quality}</p>
                                <p class="mb-2"><strong>Format:</strong> ${data.format}</p>
                                ${data.duration ? `<p class="mb-2"><strong>Duration:</strong> ${data.duration}</p>` : ''}
                                ${data.file_size_estimate ? `<p class="mb-0"><strong>Estimated Size:</strong> ${data.file_size_estimate}</p>` : ''}
                            </div>
                        </div>
                        
                        <div class="download-options">
                            <h6 class="text-primary">Download Options:</h6>
                            <div class="d-grid gap-2">
                                <a href="${data.url}" target="_blank" class="btn btn-success">
                                    <i data-feather="external-link" class="me-2"></i>
                                    Direct Download
                                </a>
                                ${data.masked_url ? `
                                    <a href="${data.masked_url}" target="_blank" class="btn btn-outline-primary">
                                        <i data-feather="shield" class="me-2"></i>
                                        Privacy Protected Link
                                    </a>
                                ` : ''}
                                ${data.telegram_url ? `
                                    <a href="${data.telegram_url}" target="_blank" class="btn btn-outline-info">
                                        <i data-feather="send" class="me-2"></i>
                                        Telegram Storage
                                    </a>
                                ` : ''}
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer border-secondary">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
        
        // Replace feather icons
        feather.replace();
        
        // Clean up modal after hiding
        modal.addEventListener('hidden.bs.modal', () => {
            modal.remove();
        });
    }

    async clearCache() {
        this.showLoading(true);
        
        const response = await this.makeRequest('/api/cache/clear', 'POST');
        
        this.showLoading(false);
        
        if (response.success) {
            this.showResult(response, 'Cache Cleared');
            // Refresh stats after clearing cache
            setTimeout(() => this.loadStats(), 1000);
        } else {
            this.showResult(response, 'Error Clearing Cache', true);
        }
    }

    async loadStats() {
        try {
            const response = await this.makeRequest('/api/stats');
            
            if (response.success) {
                this.updateStatsDisplay(response.data);
            }
        } catch (error) {
            console.error('Failed to load stats:', error);
        }
    }

    updateStatsDisplay(stats) {
        const elements = {
            totalRequests: document.getElementById('totalRequests'),
            cacheHitRate: document.getElementById('cacheHitRate'),
            telegramUploads: document.getElementById('telegramUploads'),
            uptime: document.getElementById('uptime')
        };
        
        if (elements.totalRequests) {
            elements.totalRequests.textContent = stats.requests_total?.toLocaleString() || '0';
        }
        
        if (elements.cacheHitRate) {
            elements.cacheHitRate.textContent = `${stats.cache_hit_rate || 0}%`;
        }
        
        if (elements.telegramUploads) {
            elements.telegramUploads.textContent = stats.telegram_uploads?.toLocaleString() || '0';
        }
        
        if (elements.uptime) {
            elements.uptime.textContent = stats.uptime_human || '0:00:00';
        }
    }

    startStatsRefresh() {
        // Refresh stats every 30 seconds
        setInterval(() => {
            this.loadStats();
        }, 30000);
    }

    // Utility method for copying text to clipboard
    async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            return true;
        } catch (error) {
            console.error('Failed to copy to clipboard:', error);
            return false;
        }
    }

    // Method to format JSON for display
    formatJSON(obj) {
        return JSON.stringify(obj, null, 2);
    }

    // Method to validate and format URLs
    sanitizeUrl(url) {
        try {
            const urlObj = new URL(url);
            return urlObj.toString();
        } catch (error) {
            return null;
        }
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.ytAPI = new YouTubeDownloaderAPI();
});

// Add some utility functions for enhanced UX
document.addEventListener('DOMContentLoaded', () => {
    // Add copy buttons to code examples
    const codeBlocks = document.querySelectorAll('pre code');
    codeBlocks.forEach(block => {
        const pre = block.parentElement;
        const copyBtn = document.createElement('button');
        copyBtn.className = 'btn btn-sm btn-outline-secondary position-absolute top-0 end-0 m-2';
        copyBtn.innerHTML = '<i data-feather="copy" width="16" height="16"></i>';
        copyBtn.title = 'Copy to clipboard';
        
        pre.style.position = 'relative';
        pre.appendChild(copyBtn);
        
        copyBtn.addEventListener('click', async () => {
            try {
                await navigator.clipboard.writeText(block.textContent);
                copyBtn.innerHTML = '<i data-feather="check" width="16" height="16"></i>';
                copyBtn.classList.remove('btn-outline-secondary');
                copyBtn.classList.add('btn-success');
                
                setTimeout(() => {
                    copyBtn.innerHTML = '<i data-feather="copy" width="16" height="16"></i>';
                    copyBtn.classList.remove('btn-success');
                    copyBtn.classList.add('btn-outline-secondary');
                    feather.replace();
                }, 2000);
            } catch (error) {
                console.error('Failed to copy:', error);
            }
            
            feather.replace();
        });
    });
    
    feather.replace();
});

// Add keyboard shortcuts
document.addEventListener('keydown', (e) => {
    // Ctrl/Cmd + Enter to get video info
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        window.ytAPI?.getVideoInfo();
    }
    
    // Ctrl/Cmd + Shift + Enter to download
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'Enter') {
        e.preventDefault();
        window.ytAPI?.downloadVideo();
    }
});

// Add progressive enhancement for better performance
if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-fade-in-up');
            }
        });
    });
    
    // Observe sections for animation
    document.querySelectorAll('.endpoint-card, .stat-card, .feature-card').forEach(el => {
        observer.observe(el);
    });
}
