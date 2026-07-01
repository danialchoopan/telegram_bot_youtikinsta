#!/bin/bash
# ==========================================
#   Media Downloader Bot - Update Script
# ==========================================
#
# Run this after git pull to update everything safely:
#   1. Back up database
#   2. Pull latest code
#   3. Install new dependencies
#   4. Run database migrations
#   5. Restart the bot service
#
# Usage:
#     chmod +x update.sh
#     ./update.sh
#
# ==========================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

APP_DIR="/opt/media-downloader-bot"
REPO_DIR="$HOME/telegram_bot_youtikinsta"
SERVICE_NAME="media-downloader-bot"
DB_DIR="$APP_DIR/database"
BACKUP_DIR="$APP_DIR/backups"

print_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Media Downloader Bot - Update${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Step 1: Backup database
print_info "Step 1/5: Backing up database..."
mkdir -p "$BACKUP_DIR"
if [ -f "$DB_DIR/bot.db" ]; then
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    cp "$DB_DIR/bot.db" "$BACKUP_DIR/bot_$TIMESTAMP.db"
    # Keep only last 5 backups
    ls -t "$BACKUP_DIR"/bot_*.db 2>/dev/null | tail -n +6 | xargs rm -f 2>/dev/null
    print_info "Database backed up to bot_$TIMESTAMP.db"
else
    print_warn "No database found, skipping backup"
fi

# Step 2: Stop bot service
print_info "Step 2/5: Stopping bot service..."
systemctl stop "$SERVICE_NAME" 2>/dev/null || true
print_info "Service stopped"

# Step 3: Pull latest code
print_info "Step 3/5: Pulling latest code..."
cd "$REPO_DIR"
git pull origin main
print_info "Code pulled from repo"

# Step 4: Copy files to /opt and install dependencies
print_info "Step 4/5: Copying files and installing dependencies..."
# Copy bot code (preserves .env and database)
cp -r "$REPO_DIR/bot" "$APP_DIR/"
cp "$REPO_DIR/runBot.py" "$APP_DIR/"
cp "$REPO_DIR/requirements.txt" "$APP_DIR/"
cp "$REPO_DIR/update.sh" "$APP_DIR/"
# Only copy .env.example if .env doesn't exist
if [ ! -f "$APP_DIR/.env" ] && [ -f "$REPO_DIR/.env.example" ]; then
    cp "$REPO_DIR/.env.example" "$APP_DIR/.env"
    print_warn ".env file created from template — configure it!"
fi

# Install dependencies
if [ -d "$APP_DIR/venv" ]; then
    source "$APP_DIR/venv/bin/activate"
    pip install -q -r "$APP_DIR/requirements.txt"
    print_info "Dependencies installed"
else
    print_warn "No venv found, creating one..."
    python3.11 -m venv "$APP_DIR/venv"
    source "$APP_DIR/venv/bin/activate"
    pip install -q -r "$APP_DIR/requirements.txt"
    print_info "Virtual environment created and dependencies installed"
fi

# Step 5: Copy code files
print_info "Step 5/5: Updating bot files..."
# Code is already updated by git pull in step 3
# Ensure directories exist
mkdir -p "$APP_DIR/downloads/temp"
mkdir -p "$APP_DIR/downloads/optimized"
mkdir -p "$APP_DIR/logs"
mkdir -p "$APP_DIR/database"

# Set permissions
chmod +x "$APP_DIR/runBot.py" 2>/dev/null || true

# Step 6: Restart service
print_info "Restarting bot service..."
systemctl start "$SERVICE_NAME"

# Wait and check status
sleep 2
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  Update Complete!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    print_info "Bot is running with latest code"
    print_info "Database backed up and preserved"
    echo ""
    echo "Useful commands:"
    echo "  View logs:    journalctl -u $SERVICE_NAME -f"
    echo "  Check status: systemctl status $SERVICE_NAME"
    echo "  Restart:      sudo systemctl restart $SERVICE_NAME"
    echo ""
else
    print_error "Bot failed to start! Check logs:"
    echo "  journalctl -u $SERVICE_NAME -n 50"
    echo ""
    # Try to restore backup if bot fails
    if [ -f "$BACKUP_DIR/bot_$TIMESTAMP.db" ]; then
        print_warn "Restoring database backup..."
        cp "$BACKUP_DIR/bot_$TIMESTAMP.db" "$DB_DIR/bot.db"
        systemctl restart "$SERVICE_NAME"
        sleep 2
        if systemctl is-active --quiet "$SERVICE_NAME"; then
            print_info "Bot restarted with restored database"
        fi
    fi
fi
