#!/bin/bash
# VPS Deployment Script for YouTube Downloader

echo "🚀 Starting deployment of YouTube Downloader..."

# Update system packages
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install Python 3.11 and pip
echo "🐍 Installing Python 3.11..."
sudo apt install -y python3.11 python3.11-venv python3-pip nginx

# Create application directory
APP_DIR="/opt/youtube-downloader"
sudo mkdir -p $APP_DIR
sudo chown $USER:$USER $APP_DIR

# Copy application files
echo "📁 Copying application files..."
cp -r . $APP_DIR/
cd $APP_DIR

# Create virtual environment
echo "🔨 Setting up virtual environment..."
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
echo "📚 Installing Python dependencies..."
pip install --upgrade pip
pip install -r deploy_requirements.txt

# Set up environment variables
echo "⚙️ Setting up environment variables..."
cat > .env << EOF
# MongoDB Configuration
MONGODB_URI=your_mongodb_connection_string

# Telegram Bot Configuration  
BOT_TOKEN=your_telegram_bot_token
CHANNEL_ID=your_telegram_channel_id

# Flask Configuration
SESSION_SECRET=your_secret_key_here
FLASK_DEBUG=false

# Server Configuration
PORT=5000
EOF

echo "📝 Please edit .env file with your actual credentials:"
echo "nano .env"

# Create systemd service
echo "🔧 Creating systemd service..."
sudo tee /etc/systemd/system/youtube-downloader.service > /dev/null << EOF
[Unit]
Description=YouTube Downloader Flask App
After=network.target

[Service]
Type=exec
User=$USER
Group=$USER
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/venv/bin
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/venv/bin/gunicorn --bind 127.0.0.1:5000 --workers 4 main:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Configure Nginx
echo "🌐 Configuring Nginx..."
sudo tee /etc/nginx/sites-available/youtube-downloader > /dev/null << EOF
server {
    listen 80;
    server_name your_domain.com;  # Replace with your domain

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Enable Nginx site
sudo ln -sf /etc/nginx/sites-available/youtube-downloader /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Enable and start service
echo "🎯 Starting services..."
sudo systemctl daemon-reload
sudo systemctl enable youtube-downloader
sudo systemctl start youtube-downloader

echo "✅ Deployment completed!"
echo "📋 Next steps:"
echo "1. Edit .env file: nano $APP_DIR/.env"
echo "2. Update Nginx config with your domain: sudo nano /etc/nginx/sites-available/youtube-downloader"
echo "3. Check service status: sudo systemctl status youtube-downloader"
echo "4. View logs: sudo journalctl -u youtube-downloader -f"