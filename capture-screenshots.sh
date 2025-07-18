#!/bin/bash

# Create screenshots directory
mkdir -p screenshots

echo "📸 VibeSafe App Screenshot Capture"
echo "=================================="
echo ""
echo "Please follow these steps to capture screenshots:"
echo ""
echo "1. Make sure VibeSafe app is open and visible"
echo "2. For each screen, I'll wait for you to navigate"
echo "3. Screenshots will be saved to the screenshots/ directory"
echo ""

# Function to capture a screenshot
capture_screen() {
    local name=$1
    local description=$2
    
    echo "📷 Next screenshot: $description"
    echo "   Please set up the screen and press Enter when ready..."
    read -r
    
    # Capture the screen after a 2-second delay
    echo "   Capturing in 2 seconds..."
    sleep 2
    screencapture -w "screenshots/${name}.png"
    echo "   ✅ Saved: screenshots/${name}.png"
    echo ""
}

# Capture all screens
echo "Starting screenshot capture session..."
echo ""

capture_screen "01-home-tab" "Home tab with logo and feature cards"
capture_screen "02-home-status" "Home tab with status section visible (click Show Status first)"
capture_screen "03-secrets-tab" "Secrets tab showing the list of secrets"
capture_screen "04-add-secret-modal" "Add Secret modal (click Add Secret button)"
capture_screen "05-form-validation" "Form validation errors (try to submit empty form)"
capture_screen "06-settings-tab" "Settings tab with Touch ID options"
capture_screen "07-claude-tab" "Claude integration tab"
capture_screen "08-toast-notification" "Toast notification (trigger any action)"
capture_screen "09-touch-id-prompt" "Touch ID prompt (if visible when adding secret)"

echo "✅ Screenshot capture complete!"
echo "   All screenshots saved to: ./screenshots/"
echo ""
echo "📝 Next steps:"
echo "   1. Review screenshots in the screenshots/ directory"
echo "   2. Rename or edit as needed"
echo "   3. They will be included in the documentation"