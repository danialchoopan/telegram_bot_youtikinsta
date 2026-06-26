#!/bin/bash
# ==========================================
#   Media Downloader Bot - Uninstall Script
# ==========================================
#
# This script removes the bot service, application files,
# and optionally the database and logs.
#
# Usage:
#     chmod +x uninstall.sh
#     sudo ./uninstall.sh
#
# ==========================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

APP_NAME="media-downloader-bot"
APP_DIR="/opt/$APP_NAME"
SERVICE_FILE="/etc/systemd/system/$APP_NAME.service"
BOT_USER="media-bot"

print_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check root
if [[ $EUID -ne 0 ]]; then
    print_error "This script must be run as root (use sudo)"
    exit 1
fi

echo ""
echo -e "${RED}========================================${NC}"
echo -e "${RED}  Media Downloader Bot - Uninstall${NC}"
echo -e "${RED}========================================${NC}"
echo ""

# Confirm
read -p "Are you sure you want to uninstall? This will remove all bot files. (y/N): " confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    print_info "Uninstall cancelled."
    exit 0
fi

# Step 1: Stop and disable service
print_info "Stopping bot service..."
systemctl stop "$APP_NAME" 2>/dev/null || true
systemctl disable "$APP_NAME" 2>/dev/null || true

# Step 2: Remove systemd service file
print_info "Removing systemd service..."
rm -f "$SERVICE_FILE"
systemctl daemon-reload
print_info "Service removed"

# Step 3: Ask about data removal
echo ""
read -p "Remove application files and data? (y/N): " remove_data
if [[ "$remove_data" == "y" || "$remove_data" == "Y" ]]; then
    print_info "Removing application directory..."
    rm -rf "$APP_DIR"
    print_info "Application files removed"
else
    print_warning "Application files kept at $APP_DIR"
fi

# Step 4: Ask about bot user
read -p "Remove bot user '$BOT_USER'? (y/N): " remove_user
if [[ "$remove_user" == "y" || "$remove_user" == "Y" ]]; then
    if id -u "$BOT_USER" &>/dev/null; then
        userdel "$BOT_USER" 2>/dev/null || true
        print_info "Bot user removed"
    else
        print_warning "Bot user '$BOT_USER' not found"
    fi
else
    print_warning "Bot user '$BOT_USER' kept"
fi

echo ""
print_info "========================================"
print_info "  Uninstall Complete!"
print_info "========================================"
echo ""
print_info "The bot service has been stopped and removed."
echo ""
