#!/bin/bash
# ==========================================
#   Media Downloader Bot - Setup Script
# ==========================================
#
# This script automates the setup process for Ubuntu servers.
# It installs dependencies, creates virtual environment,
# configures the bot, and sets up systemd service.
#
# Usage:
#     chmod +x setup.sh
#     sudo ./setup.sh
#
# What this script does:
#     1. Installs Python 3.11, pip, venv, ffmpeg
#     2. Creates project directory structure
#     3. Creates and activates virtual environment
#     4. Installs Python dependencies
#     5. Copies .env.example to .env (prompts for bot token)
#     6. Sets up systemd service for auto-start
#     7. Enables and starts the bot service
#
# ==========================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="media-downloader-bot"
APP_DIR="/opt/$APP_NAME"
VENV_DIR="$APP_DIR/venv"
SERVICE_FILE="/etc/systemd/system/$APP_NAME.service"
BOT_USER="media-bot"

# Print colored messages
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Install system dependencies
install_dependencies() {
    print_info "Installing system dependencies..."

    apt-get update
    apt-get install -y \
        python3.11 \
        python3.11-venv \
        python3-pip \
        ffmpeg \
        git \
        curl

    print_success "System dependencies installed"
}

# Create bot user (non-root)
create_bot_user() {
    print_info "Creating bot user..."

    if ! id -u "$BOT_USER" &>/dev/null; then
        useradd -r -s /bin/false -d "$APP_DIR" "$BOT_USER"
        print_success "Bot user '$BOT_USER' created"
    else
        print_warning "Bot user '$BOT_USER' already exists"
    fi
}

# Setup project directory
setup_directory() {
    print_info "Setting up project directory..."

    mkdir -p "$APP_DIR"
    mkdir -p "$APP_DIR/downloads/temp"
    mkdir -p "$APP_DIR/downloads/optimized"
    mkdir -p "$APP_DIR/logs"
    mkdir -p "$APP_DIR/database"

    # Copy project files (assuming script is run from project root)
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

    cp -r "$SCRIPT_DIR/bot" "$APP_DIR/"
    cp -r "$SCRIPT_DIR/requirements.txt" "$APP_DIR/"
    cp "$SCRIPT_DIR/runBot.py" "$APP_DIR/"
    cp "$SCRIPT_DIR/.env.example" "$APP_DIR/"

    print_success "Project directory setup complete"
}

# Create and activate virtual environment
setup_venv() {
    print_info "Creating virtual environment..."

    python3.11 -m venv "$VENV_DIR"
    source "$VENV_DIR/bin/activate"

    # Upgrade pip
    pip install --upgrade pip

    # Install Python dependencies
    pip install -r "$APP_DIR/requirements.txt"

    print_success "Virtual environment and dependencies installed"
}

# Configure environment
setup_env() {
    print_info "Configuring environment..."

    ENV_FILE="$APP_DIR/.env"

    if [[ ! -f "$ENV_FILE" ]]; then
        cp "$APP_DIR/.env.example" "$ENV_FILE"

        echo ""
        echo -e "${YELLOW}========================================${NC}"
        echo -e "${YELLOW}  Bot Configuration${NC}"
        echo -e "${YELLOW}========================================${NC}"
        echo ""

        # Prompt for bot token
        read -p "Enter your Telegram Bot Token: " BOT_TOKEN
        if [[ -n "$BOT_TOKEN" ]]; then
            sed -i "s/TELEGRAM_BOT_TOKEN=.*/TELEGRAM_BOT_TOKEN=$BOT_TOKEN/" "$ENV_FILE"
        fi

        # Prompt for admin user ID (chat ID)
        echo ""
        echo -e "${YELLOW}To get your chat ID, send /start to @userinfobot on Telegram${NC}"
        echo ""
        read -p "Enter admin Telegram user ID (chat ID): " ADMIN_UID
        if [[ -n "$ADMIN_UID" ]]; then
            sed -i "s/ADMIN_USER_ID=.*/ADMIN_USER_ID=$ADMIN_UID/" "$ENV_FILE"
        fi

        # Proxy configuration
        echo ""
        echo -e "${YELLOW}Do you need a proxy to access Telegram/YouTube? (y/N)${NC}"
        echo -e "${YELLOW}Default: No proxy${NC}"
        read -p "Use proxy? " USE_PROXY
        if [[ "$USE_PROXY" == "y" || "$USE_PROXY" == "Y" ]]; then
            echo ""
            read -p "Proxy address (e.g. socks5://127.0.0.1:10808): " PROXY_ADDR
            if [[ -n "$PROXY_ADDR" ]]; then
                sed -i "s|TELEGRAM_PROXY=.*|TELEGRAM_PROXY=$PROXY_ADDR|" "$ENV_FILE"
                sed -i "s|DOWNLOAD_PROXY=.*|DOWNLOAD_PROXY=$PROXY_ADDR|" "$ENV_FILE"
            fi
        else
            sed -i "s|TELEGRAM_PROXY=.*|TELEGRAM_PROXY=|" "$ENV_FILE"
            sed -i "s|DOWNLOAD_PROXY=.*|DOWNLOAD_PROXY=|" "$ENV_FILE"
        fi

        # Max resolution
        echo ""
        read -p "Max resolution (default 1080): " MAX_RES
        if [[ -n "$MAX_RES" ]]; then
            sed -i "s/MAX_RESOLUTION=.*/MAX_RESOLUTION=$MAX_RES/" "$ENV_FILE"
        fi

        # Daily download limit
        read -p "Max downloads per user per day (default 10): " DAILY_LIMIT
        if [[ -n "$DAILY_LIMIT" ]]; then
            sed -i "s/MAX_DAILY_DOWNLOADS_PER_USER=.*/MAX_DAILY_DOWNLOADS_PER_USER=$DAILY_LIMIT/" "$ENV_FILE"
        fi

        # Enable 4K blocking
        echo ""
        echo -e "${YELLOW}Block 4K downloads? (Y/n)${NC}"
        read -p "Block 4K: " BLOCK_4K
        if [[ "$BLOCK_4K" == "n" || "$BLOCK_4K" == "N" ]]; then
            sed -i "s/ENABLE_4K_BLOCKING=.*/ENABLE_4K_BLOCKING=false/" "$ENV_FILE"
        fi

        print_success ".env file configured"
    else
        print_warning ".env file already exists, skipping configuration"
    fi
}

# Setup systemd service
setup_service() {
    print_info "Setting up systemd service..."

    cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Media Downloader Telegram Bot
After=network.target

[Service]
Type=simple
User=$BOT_USER
Group=$BOT_USER
WorkingDirectory=$APP_DIR
ExecStart=$VENV_DIR/bin/python runBot.py
Restart=always
RestartSec=10
Environment=PATH=$VENV_DIR/bin:/usr/bin
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$APP_DIR/downloads $APP_DIR/logs $APP_DIR/database
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd and enable service
    systemctl daemon-reload
    systemctl enable "$APP_NAME"

    print_success "Systemd service created and enabled"
}

# Set permissions
set_permissions() {
    print_info "Setting permissions..."

    chown -R "$BOT_USER:$BOT_USER" "$APP_DIR"
    chmod -R 755 "$APP_DIR"
    chmod +x "$APP_DIR/runBot.py"

    print_success "Permissions set"
}

# Start the bot
start_bot() {
    print_info "Starting bot service..."

    systemctl start "$APP_NAME"

    # Check if service started successfully
    if systemctl is-active --quiet "$APP_NAME"; then
        print_success "Bot service started successfully!"
    else
        print_error "Failed to start bot service"
        echo "Check logs with: journalctl -u $APP_NAME -f"
        exit 1
    fi
}

# Print summary
print_summary() {
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  Setup Complete!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "Bot is installed at: $APP_DIR"
    echo "Bot is running as:   $APP_NAME"
    echo ""
    echo "Useful commands:"
    echo "  View logs:      journalctl -u $APP_NAME -f"
    echo "  Restart bot:    systemctl restart $APP_NAME"
    echo "  Stop bot:       systemctl stop $APP_NAME"
    echo "  Bot status:     systemctl status $APP_NAME"
    echo "  Edit config:    nano $APP_DIR/.env"
    echo ""
    echo "The bot will automatically start on system boot."
    echo ""
}

# Main execution
main() {
    check_root
    install_dependencies
    create_bot_user
    setup_directory
    setup_venv
    setup_env
    setup_service
    set_permissions
    start_bot
    print_summary
}

# Run main function
main "$@"
