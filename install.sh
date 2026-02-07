#!/bin/bash
# Claude Remote Bridge Installer
# One-command install for remote Claude Code communication

set -e

REPO="ARTIFACTIQ/claude-remote-bridge"
INSTALL_DIR="${HOME}/.local/share/claude-remote-bridge"
BIN_DIR="${HOME}/.local/bin"

echo ""
echo "  Claude Remote Bridge Installer"
echo "  ==============================="
echo ""
echo "  Repo:    github.com/${REPO}"
echo "  Install: ${INSTALL_DIR}"
echo "  CLI:     ${BIN_DIR}/crb"
echo ""

# Check dependencies
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is required but not found"
    exit 1
fi

if ! python3 -c "import requests" 2>/dev/null; then
    echo "==> Installing requests..."
    pip3 install --user requests
fi

# Clone or update
if [ -d "$INSTALL_DIR" ]; then
    echo "==> Updating existing installation..."
    cd "$INSTALL_DIR"
    git pull --quiet
else
    echo "==> Cloning repository..."
    mkdir -p "$(dirname "$INSTALL_DIR")"
    git clone --quiet "https://github.com/${REPO}.git" "$INSTALL_DIR"
fi

# Create bin directory and symlink
mkdir -p "$BIN_DIR"
chmod +x "${INSTALL_DIR}/src/crb"
ln -sf "${INSTALL_DIR}/src/crb" "${BIN_DIR}/crb"

# Verify
if command -v crb &> /dev/null; then
    echo ""
    echo "  Installed successfully!"
    echo ""
    echo "  Quick start:"
    echo "    crb start my-topic     # Start bridge"
    echo "    crb hook               # Install Claude Code hook"
    echo ""
    echo "  Then from your phone (ntfy app):"
    echo "    Subscribe to: my-topic"
    echo "    Send: q: training"
    echo ""
elif [ -f "${BIN_DIR}/crb" ]; then
    echo ""
    echo "  Installed to ${BIN_DIR}/crb"
    echo "  Add to PATH: export PATH=\"${BIN_DIR}:\$PATH\""
    echo ""
else
    echo ""
    echo "  Error: Installation failed"
    exit 1
fi
