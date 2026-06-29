# Media Downloader Bot

A Telegram bot for downloading videos from YouTube, Instagram, and TikTok in various formats with automatic optimization for Telegram's platform.

## Disclaimer

**This software is provided "as is" without warranty of any kind. The authors are not responsible for any misuse of this tool. Users are solely responsible for ensuring they comply with the terms of service of YouTube, Instagram, TikTok, and Telegram when using this bot. Downloading copyrighted content without permission may violate applicable laws. Use at your own risk.**

## Features

- **Multi-platform support**: YouTube, Instagram, TikTok, and direct media links
- **Format selection**: MP4, MKV, MP3, M4A output formats
- **4K blocking**: Automatically blocks 4K/8K downloads to save bandwidth
- **Telegram optimization**: H.264/AAC codec, max 1080p, compressed for Telegram's limits
- **Smart queue system**: Priority-based queuing with real-time progress
- **Whitelist mode**: Only allowed users can use the bot (admin toggles on/off)
- **Bilingual interface**: Persian (Farsi) and English support
- **User preferences**: Customizable default format, quality, and language
- **Admin dashboard**: Full inline keyboard panel (stats, users, bans, settings)
- **Real-time progress**: Single-message progress updates (downloading → optimizing → uploading)
- **Proxy support**: SOCKS5/HTTP proxy for Telegram and downloads
- **Auto-cleanup**: Temp files deleted after upload and periodically
- **SQLite database**: Tracks users, downloads, queue, and quality statistics

## Quick Start (Ubuntu Server)

### One-Command Setup

```bash
# Clone the repository
git clone https://github.com/danialchoopan/telegram_bot_youtikinsta.git
cd telegram_bot_youtikinsta

# Make setup script executable and run it
chmod +x setup.sh
sudo ./setup.sh
```

The setup script will:
1. Install Python 3.11, ffmpeg, and other dependencies
2. Create a virtual environment
3. Install Python packages
4. Prompt you for your Telegram bot token and admin user ID
5. Ask if you need a proxy (for restricted regions)
6. Configure max resolution, daily limits, and 4K blocking
7. Set up systemd service for auto-start
8. Start the bot

### After Setup

```bash
# View bot logs
journalctl -u media-downloader-bot -f

# Restart bot
sudo systemctl restart media-downloader-bot

# Stop bot
sudo systemctl stop media-downloader-bot

# Check status
sudo systemctl status media-downloader-bot
```

## Manual Installation

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/telegram_bot_youtikinsta.git
cd telegram_bot_youtikinsta
```

### 2. Install system dependencies

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip ffmpeg git
```

**macOS:**
```bash
brew install python@3.11 ffmpeg git
```

### 3. Create virtual environment

```bash
python3.11 -m venv venv
source venv/bin/activate
```

### 4. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure environment

```bash
cp .env.example .env
nano .env
```

Edit `.env` with your settings:
```
TELEGRAM_BOT_TOKEN=your_bot_token_here
# Send /start to @userinfobot on Telegram to get your user ID
ADMIN_USER_ID=123456789
```

### 6. Run the bot

```bash
python runBot.py
```

## Docker Deployment

### Quick Start with Docker

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/telegram_bot_youtikinsta.git
cd telegram_bot_youtikinsta

# 2. Create your .env file
cp .env.example .env
nano .env  # Add your TELEGRAM_BOT_TOKEN and ADMIN_USER_ID

# 3. Build and run with Docker
docker build -t media-downloader-bot .
docker run -d \
  --name media-bot \
  --restart unless-stopped \
  --env-file .env \
  -v $(pwd)/downloads:/app/downloads \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/database:/app/database \
  media-downloader-bot
```

### Docker Compose (Recommended)

Create a `docker-compose.yml` file:

```yaml
version: '3.8'

services:
  media-bot:
    build: .
    container_name: media-downloader-bot
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./downloads:/app/downloads
      - ./logs:/app/logs
      - ./database:/app/database
    environment:
      - TZ=UTC
    healthcheck:
      test: ["CMD", "python", "-c", "import sys; sys.exit(0)"]
      interval: 30s
      timeout: 10s
      retries: 3
```

Then run:

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down

# Restart
docker-compose restart

# Rebuild after changes
docker-compose up -d --build
```

### Docker Commands Reference

| Command | Description |
|---------|-------------|
| `docker build -t media-downloader-bot .` | Build the Docker image |
| `docker run -d --name media-bot --env-file .env media-downloader-bot` | Start container |
| `docker logs -f media-bot` | View container logs |
| `docker stop media-bot` | Stop the container |
| `docker start media-bot` | Start stopped container |
| `docker restart media-bot` | Restart the container |
| `docker rm -f media-bot` | Remove the container |
| `docker exec -it media-bot bash` | Open shell in container |

### Persistent Data

The Docker setup uses volumes to persist data outside the container:

| Volume | Container Path | Purpose |
|--------|---------------|---------|
| `./downloads` | `/app/downloads` | Downloaded and optimized files |
| `./logs` | `/app/logs` | Application logs |
| `./database` | `/app/database` | SQLite database |

This ensures your data survives container restarts and updates.

### Environment Variables in Docker

You can pass environment variables in three ways:

1. **Using .env file** (recommended):
   ```bash
   docker run -d --env-file .env media-downloader-bot
   ```

2. **Using -e flag**:
   ```bash
   docker run -d \
     -e TELEGRAM_BOT_TOKEN=your_token \
     -e ADMIN_USER_ID=123456789 \
     media-downloader-bot
   ```

3. **Using docker-compose.yml**:
   ```yaml
   environment:
     - TELEGRAM_BOT_TOKEN=your_token
     - ADMIN_USER_ID=123456789
   ```

## Proxy Configuration

If you need a proxy to access Telegram or YouTube (e.g., in restricted regions):

Edit `.env`:
```env
# SOCKS5 proxy (recommended)
TELEGRAM_PROXY=socks5://127.0.0.1:10808
DOWNLOAD_PROXY=socks5://127.0.0.1:10808

# Or HTTP proxy
TELEGRAM_PROXY=http://127.0.0.1:8080
DOWNLOAD_PROXY=http://127.0.0.1:8080

# Leave empty for no proxy
TELEGRAM_PROXY=
DOWNLOAD_PROXY=
```

For SOCKS5 proxy, install extra dependency:
```bash
pip install "python-telegram-bot[socks]" pysocks socksio
```

## Bot Commands

| Command | Description | Access |
|---------|-------------|--------|
| `/start` | Start the bot, select language, admin panel | All users |
| `/settings` | View and change preferences | All users |

All admin features are available through the **Admin Panel** (inline keyboard) after `/start`.

## Whitelist Mode

By default, everyone can use the bot. Admin can enable whitelist mode:

1. Open Admin Panel (`/start` → 🔧 Admin Panel)
2. Tap "🔒 Turn On Whitelist"
3. Tap "➕ Whitelist User" → select users

When whitelist is ON:
- Only whitelisted users can download
- Admin is always whitelisted
- Non-whitelisted users see "Access denied"

## Configuration

All configuration is done through the `.env` file. See `.env.example` for all available options.

### Key Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | - | Your Telegram bot token |
| `ADMIN_USER_ID` | 0 | Telegram user ID of the admin (get from @userinfobot) |
| `MAX_RESOLUTION` | 1080 | Maximum download resolution |
| `DEFAULT_FORMAT` | mp4 | Default output format |
| `ENABLE_4K_BLOCKING` | true | Block 4K downloads |
| `VIDEO_BITRATE_MBPS` | 4 | Video bitrate for optimization |
| `AUDIO_BITRATE_KBPS` | 128 | Audio bitrate for optimization |
| `MAX_DAILY_DOWNLOADS_PER_USER` | 10 | Daily download limit per user |
| `MAX_CONCURRENT_QUEUED_PER_USER` | 3 | Max queue items per user |

## How It Works

1. User sends a link to the bot
2. Bot analyzes the link and shows available formats
3. User selects output format (MP4/MKV/MP3/M4A)
4. Download is added to the queue
5. Queue worker processes downloads in priority order
6. Media is optimized for Telegram (H.264, AAC, max 1080p)
7. Optimized file is sent to the user
8. Temporary files are cleaned up

## Project Structure

```
telegram_bot_youtikinsta/
├── runBot.py                  # Entry point - run this to start the bot
├── bot/
│   ├── __init__.py
│   ├── config.py              # Configuration from .env
│   ├── database.py            # SQLite database manager
│   ├── handlers/
│   │   ├── start.py           # /start and language selection
│   │   ├── download.py        # URL handling and format selection
│   │   ├── admin.py           # Admin commands
│   │   └── settings.py        # User preferences
│   ├── services/
│   │   ├── downloader.py      # yt-dlp download wrapper
│   │   ├── optimizer.py       # ffmpeg optimization
│   │   ├── analyzer.py        # Media analysis (yt-dlp)
│   │   └── queue_worker.py    # Background queue processor
│   └── utils/
│       ├── messages.py        # Bilingual message templates
│       └── helpers.py         # Utility functions
├── downloads/
│   ├── temp/                  # Temporary download files
│   └── optimized/             # Optimized output files
├── database/                  # SQLite database files
├── logs/                      # Application logs
├── legacy/                    # Old bot code (reference only)
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Docker configuration
├── setup.sh                   # Ubuntu server setup script
├── media-downloader-bot.service # Systemd service file
├── .env.example               # Environment template
└── .gitignore
```

## Legacy Code

The `legacy/` folder contains the original bot code (`telbot_yutikinsta_original.py`) for reference. The new modular code in `bot/` completely replaces it.

## Troubleshooting

### Bot won't start
- Check `.env` file has valid `TELEGRAM_BOT_TOKEN`
- Ensure ffmpeg is installed: `ffmpeg -version`
- Check logs: `journalctl -u media-downloader-bot -n 50`

### Downloads failing
- Check disk space: `df -h`
- Check ffmpeg can process: `ffmpeg -i test.mp4`
- Verify yt-dlp works: `yt-dlp --version`

### Permission errors
```bash
sudo chown -R media-bot:media-bot /opt/media-downloader-bot
sudo chmod -R 755 /opt/media-downloader-bot
```

## License

This project is for educational purposes only.
