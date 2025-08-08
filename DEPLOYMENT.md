# YouTube Downloader - Deployment Guide

This guide will help you deploy the YouTube Downloader application on various platforms including Heroku, Koyeb, VPS, and Docker.

## 🔧 Prerequisites

Before deploying, make sure you have:

1. **MongoDB Atlas Database** - Get connection string from MongoDB Atlas
2. **Telegram Bot Token** - Create a bot via @BotFather on Telegram
3. **Telegram Channel ID** - Create a channel and get its ID

## 🚀 Deployment Options

### 1. Heroku Deployment

1. **Install Heroku CLI** and login:
   ```bash
   heroku login
   ```

2. **Create Heroku app**:
   ```bash
   heroku create your-app-name
   ```

3. **Set environment variables**:
   ```bash
   heroku config:set MONGODB_URI="your_mongodb_connection_string"
   heroku config:set BOT_TOKEN="your_telegram_bot_token" 
   heroku config:set CHANNEL_ID="your_telegram_channel_id"
   heroku config:set SESSION_SECRET="your_random_secret_key"
   ```

4. **Deploy**:
   ```bash
   git add .
   git commit -m "Deploy to Heroku"
   git push heroku main
   ```

**Files used**: `Procfile`, `runtime.txt`, `deploy_requirements.txt`

### 2. Koyeb Deployment

1. **Fork/Upload** your code to GitHub
2. **Connect Koyeb** to your GitHub repository
3. **Set environment variables** in Koyeb dashboard:
   - `MONGODB_URI`: Your MongoDB connection string
   - `BOT_TOKEN`: Your Telegram bot token
   - `CHANNEL_ID`: Your Telegram channel ID
   - `SESSION_SECRET`: Random secret key
4. **Deploy** using the web interface

**Build command**: `pip install -r deploy_requirements.txt`
**Run command**: `gunicorn --bind 0.0.0.0:$PORT main:app`

### 3. VPS Deployment (Ubuntu/Debian)

1. **Upload files** to your VPS:
   ```bash
   scp -r . user@your-server-ip:/tmp/youtube-downloader
   ```

2. **Connect to VPS** and run deployment script:
   ```bash
   ssh user@your-server-ip
   cd /tmp/youtube-downloader
   chmod +x deploy.sh
   sudo ./deploy.sh
   ```

3. **Configure environment variables**:
   ```bash
   nano /opt/youtube-downloader/.env
   ```
   Add your credentials:
   ```
   MONGODB_URI=your_mongodb_connection_string
   BOT_TOKEN=your_telegram_bot_token
   CHANNEL_ID=your_telegram_channel_id
   SESSION_SECRET=your_random_secret_key
   ```

4. **Restart service**:
   ```bash
   sudo systemctl restart youtube-downloader
   ```

### 4. Docker Deployment

1. **Create environment file**:
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

2. **Run with Docker Compose**:
   ```bash
   docker-compose up -d
   ```

3. **Or run with Docker directly**:
   ```bash
   docker build -t youtube-downloader .
   docker run -d -p 5000:5000 --env-file .env youtube-downloader
   ```

## 🔑 Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `MONGODB_URI` | MongoDB Atlas connection string | Yes |
| `BOT_TOKEN` | Telegram bot token from @BotFather | Yes |
| `CHANNEL_ID` | Telegram channel ID for file storage | Yes |
| `SESSION_SECRET` | Random secret key for Flask sessions | Yes |
| `PORT` | Port number (auto-set by most platforms) | No |
| `FLASK_DEBUG` | Enable debug mode (set to "false" in production) | No |

## 🔍 Verification

After deployment, test your application:

1. **Visit your deployed URL**
2. **Test with a YouTube video**:
   - Enter: `https://youtu.be/Qrhl4uxAeu8`
   - Should download and upload to Telegram
3. **Check Telegram channel** for uploaded files

## 🛠️ Troubleshooting

### Common Issues:

1. **Port binding errors**: Make sure PORT environment variable is set correctly
2. **Database connection**: Verify MONGODB_URI is correct and database is accessible
3. **Telegram errors**: Check BOT_TOKEN and CHANNEL_ID are valid
4. **File size limits**: Videos larger than 50MB cannot be uploaded to Telegram

### View Logs:

- **Heroku**: `heroku logs --tail`
- **VPS**: `sudo journalctl -u youtube-downloader -f`
- **Docker**: `docker logs container_name`

## 📁 Deployment Files

- `Procfile` - Heroku process definition
- `runtime.txt` - Python version specification
- `deploy_requirements.txt` - Python dependencies
- `deploy.sh` - VPS deployment script
- `Dockerfile` - Docker container definition
- `docker-compose.yml` - Docker Compose configuration

## 🔒 Security Notes

- Never commit `.env` files or credentials to version control
- Use strong, random values for `SESSION_SECRET`
- Ensure MongoDB database has proper access controls
- Consider using HTTPS in production (Let's Encrypt for VPS)