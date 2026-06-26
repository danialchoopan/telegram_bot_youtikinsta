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

## Requirements

- Python 3.10+
- ffmpeg (installed and in PATH)
- yt-dlp (installed and in PATH)

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/telegram_bot_youtikinsta.git
cd telegram_bot_youtikinsta
```

### 2. Create virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Install ffmpeg

**Windows:**
Download from https://ffmpeg.org/download.html and add to PATH.

**Linux:**
```bash
sudo apt update && sudo apt install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

### 5. Configure environment

```bash
cp .env.example .env
```

Edit `.env` with your Telegram bot token and admin username.

### 6. Run the bot

```bash
python -m bot.main
```

## Docker Deployment

```bash
docker build -t media-downloader-bot .
docker run -d --name bot --env-file .env media-downloader-bot
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
├── bot/
│   ├── __init__.py
│   ├── main.py              # Entry point
│   ├── config.py             # Configuration management
│   ├── database.py           # SQLite database
│   ├── handlers/
│   │   ├── start.py          # /start and language selection
│   │   ├── download.py       # URL handling and format selection
│   │   ├── admin.py          # Admin commands
│   │   └── settings.py       # User preferences
│   ├── services/
│   │   ├── downloader.py     # yt-dlp wrapper
│   │   ├── optimizer.py      # ffmpeg optimization
│   │   ├── analyzer.py       # Media analysis
│   │   └── queue_worker.py   # Background queue processor
│   └── utils/
│       ├── messages.py       # Bilingual message templates
│       └── helpers.py        # Utility functions
├── downloads/
│   ├── temp/                 # Temporary download files
│   └── optimized/            # Optimized output files
├── database/                 # SQLite database files
├── logs/                     # Application logs
├── requirements.txt
├── Dockerfile
├── .env.example
└── .gitignore
```

## License

This project is for educational purposes only.
