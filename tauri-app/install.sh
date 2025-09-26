#!/bin/bash
#
# VibeSafe Desktop App Setup Script
#

set -e

echo "🖥️  VibeSafe Desktop App Setup"
echo "=============================="
echo

# Check if VibeSafe CLI is available
if ! command -v vibesafe &> /dev/null; then
    echo "❌ VibeSafe CLI not found"
    echo "   Please install VibeSafe CLI first:"
    echo "   cd .. && ./install.sh"
    exit 1
fi

echo "✓ VibeSafe CLI detected"

# Check Node.js version
node_version=$(node --version 2>&1 | cut -d'v' -f2)
major=$(echo $node_version | cut -d. -f1)

if [ "$major" -lt 18 ]; then
    echo "❌ Error: Node.js 18 or higher is required"
    echo "   Found: Node.js $node_version"
    exit 1
fi

echo "✓ Node.js $node_version detected"

# Check Rust
if ! command -v rustc &> /dev/null; then
    echo "❌ Rust not found"
    echo "   Install from: https://rustup.rs/"
    exit 1
fi

rust_version=$(rustc --version | awk '{print $2}')
echo "✓ Rust $rust_version detected"

# Install dependencies
echo
echo "Installing dependencies..."
npm install

# Install Tauri CLI if not present
if ! npx tauri --version &> /dev/null; then
    echo "Installing Tauri CLI..."
    npm install -g @tauri-apps/cli
fi

echo "✓ Dependencies installed"

# Build icons (placeholder for now)
echo
echo "Setting up icons..."
echo "⚠️  Note: Icon files need to be created manually"
echo "   Required: 32x32.png, 128x128.png, 128x128@2x.png, icon.icns, icon.ico"

echo
echo "🎉 VibeSafe Desktop App setup complete!"
echo
echo "Next steps:"
echo "1. Create app icons in the icons/ directory"
echo "2. Run development server: npm run tauri:dev"
echo "3. Build for production: npm run tauri:build"
echo
echo "For more information, see README.md"