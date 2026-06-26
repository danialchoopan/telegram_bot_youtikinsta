# Media Downloader Bot

A Telegram bot for downloading videos from YouTube, Instagram, and TikTok in various formats with automatic optimization for Telegram's platform.

## Disclaimer

**This software is provided "as is" without warranty of any kind. The authors are not responsible for any misuse of this tool. Users are solely responsible for ensuring they comply with the terms of service of YouTube, Instagram, TikTok, and Telegram when using this bot. Downloading copyrighted content without permission may violate applicable laws. Use at your own risk.**

## Features

- **Multi-platform support**: YouTube, Instagram, TikTok, and direct media links
- **Format selection**: MP4, MKV, MP3, M4A output formats
- **4K blocking**: Automatically blocks 4K/8K downloads to save bandwidth
- **Telegram optimization**: H.264/AAC codec, max 1080p, compressed for Telegram's limits
- **Queue system**: Handles concurrent users with priority-based queuing
- **Bilingual interface**: Persian (Farsi) and English support
- **User preferences**: Customizable default format, quality, and language
- **Admin dashboard**: User management, ban system, quality statistics
- **Real-time progress**: Multi-stage progress updates during download/optimization
- **SQLite database**: Tracks users, downloads, queue, and quality statistics

## Quick Start (Ubuntu Server)

### One-Command Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/telegram_bot_youtikinsta.git
cd telegram_bot_youtikinsta

# Make setup script executable and run it
chmod +x setup.sh
sudo ./setup.sh
```

The setup script will:
1. Install Python 3.11, ffmpeg, and other dependencies
2. Create a virtual environment
3. Install Python packages
4. Prompt you for your Telegram bot token and admin username
5. Set up systemd service for auto-start
6. Start the bot

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
ADMIN_USERNAME=your_telegram_username
```

### 6. Run the bot

```bash
python runBot.py
```

## Docker Deployment

```bash
# Build image
docker build -t media-downloader-bot .

# Run container
docker run -d \
  --name media-bot \
  --env-file .env \
  -v $(pwd)/downloads:/app/downloads \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/database:/app/database \
  media-downloader-bot
```

## Bot Commands

| Command | Description | Access |
|---------|-------------|--------|
| `/start` | Start the bot and select language | All users |
| `/settings` | View and change preferences | All users |
| `/admin_stats` | View bot statistics | Admin only |
| `/addallow <user_id>` | Add user to allowed list | Admin only |
| `/ban <user_id> [hours]` | Ban a user | Admin only |
| `/setadmin <user_id>` | Grant admin access | Admin only |

## Configuration

All configuration is done through the `.env` file. See `.env.example` for all available options.

### Key Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | - | Your Telegram bot token |
| `ADMIN_USERNAME` | - | Telegram username of the admin |
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
