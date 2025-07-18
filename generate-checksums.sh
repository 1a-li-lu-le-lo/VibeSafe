#!/bin/bash

# Generate checksums for README
echo "Generating checksums..."

# App bundle
if [ -d "src-tauri/target/release/bundle/macos/VibeSafe.app" ]; then
    tar -cf /tmp/VibeSafe.app.tar -C src-tauri/target/release/bundle/macos VibeSafe.app
    APP_HASH=$(shasum -a 256 /tmp/VibeSafe.app.tar | awk '{print $1}')
    rm /tmp/VibeSafe.app.tar
    echo "VibeSafe.app.tar: $APP_HASH"
fi

# Binary
if [ -f "src-tauri/target/release/vibesafe-app" ]; then
    BINARY_HASH=$(shasum -a 256 src-tauri/target/release/vibesafe-app | awk '{print $1}')
    echo "vibesafe-app: $BINARY_HASH"
fi

# Frontend
if [ -d "dist" ]; then
    tar -czf /tmp/vibesafe-frontend.tar.gz -C dist .
    FRONTEND_HASH=$(shasum -a 256 /tmp/vibesafe-frontend.tar.gz | awk '{print $1}')
    rm /tmp/vibesafe-frontend.tar.gz
    echo "vibesafe-frontend.tar.gz: $FRONTEND_HASH"
fi