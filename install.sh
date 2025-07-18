#!/bin/bash
#
# VibeSafe Installation Script
#

set -e

echo "🔐 VibeSafe Installer"
echo "===================="
echo

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
major=$(echo $python_version | cut -d. -f1)
minor=$(echo $python_version | cut -d. -f2)

if [ "$major" -lt 3 ] || ([ "$major" -eq 3 ] && [ "$minor" -lt 8 ]); then
    echo "❌ Error: Python 3.8 or higher is required"
    echo "   Found: Python $python_version"
    exit 1
fi

echo "✓ Python $python_version detected"

# Detect platform
platform=$(uname -s)
echo "✓ Platform: $platform"

# Create virtual environment (optional)
if [ "$1" == "--venv" ]; then
    echo
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    echo "✓ Virtual environment created and activated"
fi

# Install base package
echo
echo "Installing VibeSafe..."
pip install -e .

# Install platform-specific extras
if [ "$platform" == "Darwin" ]; then
    echo
    echo "Installing macOS extras (Touch ID/Face ID support)..."
    pip install -e ".[macos]"
    echo "✓ macOS passkey support installed"
fi

# Ask about FIDO2 support
echo
read -p "Install FIDO2/WebAuthn support for security keys? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    pip install -e ".[fido2]"
    echo "✓ FIDO2 support installed"
fi

# Ask about development dependencies
echo
read -p "Install development dependencies? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    pip install -e ".[dev]"
    echo "✓ Development dependencies installed"
fi

# Verify installation
echo
echo "Verifying installation..."
if command -v vibesafe &> /dev/null; then
    echo "✓ VibeSafe CLI is available"
    vibesafe --version
else
    echo "⚠️  VibeSafe CLI not in PATH"
    echo "   Try: python -m vibesafe.vibesafe"
fi

echo
echo "🎉 Installation complete!"
echo
echo "Next steps:"
echo "1. Initialize VibeSafe: vibesafe init"
echo "2. Add your first secret: vibesafe add API_KEY"
echo "3. Enable passkey protection: vibesafe passkey enable"
echo
echo "For more information, see README.md"