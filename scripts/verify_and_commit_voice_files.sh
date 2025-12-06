#!/bin/bash
# Script to verify and optionally commit voice files to the repository

set -e  # Exit on error

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "================================================"
echo "Voice Files Verification and Commit Script"
echo "================================================"
echo ""

# Define expected files
declare -a AA_FILES=(
    "welcome.wav"
    "main_menu.wav"
    "invalid.wav"
    "timeout.wav"
    "transferring.wav"
)

declare -a VM_FILES=(
    "enter_pin.wav"
    "invalid_pin.wav"
    "main_menu.wav"
    "message_menu.wav"
    "no_messages.wav"
    "you_have_messages.wav"
    "goodbye.wav"
    "leave_message.wav"
    "recording_greeting.wav"
    "greeting_saved.wav"
    "message_deleted.wav"
    "end_of_messages.wav"
)

# Check if voice files exist
echo "Step 1: Checking for existing voice files..."
echo ""

AA_COUNT=0
VM_COUNT=0
MISSING_FILES=()

echo "Auto Attendant files (auto_attendant/):"
for file in "${AA_FILES[@]}"; do
    if [ -f "auto_attendant/$file" ]; then
        SIZE=$(stat -f%z "auto_attendant/$file" 2>/dev/null || stat -c%s "auto_attendant/$file" 2>/dev/null)
        echo "  ✓ $file ($SIZE bytes)"
        ((AA_COUNT++))
    else
        echo "  ✗ $file (missing)"
        MISSING_FILES+=("auto_attendant/$file")
    fi
done

echo ""
echo "Voicemail Prompt files (voicemail_prompts/):"
for file in "${VM_FILES[@]}"; do
    if [ -f "voicemail_prompts/$file" ]; then
        SIZE=$(stat -f%z "voicemail_prompts/$file" 2>/dev/null || stat -c%s "voicemail_prompts/$file" 2>/dev/null)
        echo "  ✓ $file ($SIZE bytes)"
        ((VM_COUNT++))
    else
        echo "  ✗ $file (missing)"
        MISSING_FILES+=("voicemail_prompts/$file")
    fi
done

echo ""
echo "Summary: Found $AA_COUNT/5 auto attendant files and $VM_COUNT/12 voicemail files"
echo ""

# If files are missing, offer to generate them
if [ ${#MISSING_FILES[@]} -gt 0 ]; then
    echo "Missing ${#MISSING_FILES[@]} voice files."
    echo ""
    echo "Would you like to generate the missing files? (y/n)"
    read -r GENERATE
    
    if [[ "$GENERATE" =~ ^[Yy]$ ]]; then
        echo ""
        echo "Generating voice files..."
        echo ""
        echo "Please enter your company name (or press Enter for 'your company'):"
        read -r COMPANY_NAME
        COMPANY_NAME=${COMPANY_NAME:-"your company"}
        
        if command -v python3 &> /dev/null; then
            # Try Google TTS first
            if python3 -c "import gtts" 2>/dev/null; then
                echo "Using Google TTS (best quality)..."
                python3 scripts/generate_tts_prompts.py --company "$COMPANY_NAME"
            # Try Festival
            elif command -v festival &> /dev/null; then
                echo "Using Festival TTS..."
                python3 scripts/generate_natural_voices.py --engine festival --company "$COMPANY_NAME"
            # Fall back to eSpeak
            else
                echo "Using eSpeak TTS..."
                python3 scripts/generate_espeak_voices.py --company "$COMPANY_NAME"
            fi
        else
            echo "Error: Python 3 is not installed."
            exit 1
        fi
        
        # Recount after generation
        AA_COUNT=0
        VM_COUNT=0
        for file in "${AA_FILES[@]}"; do
            [ -f "auto_attendant/$file" ] && ((AA_COUNT++))
        done
        for file in "${VM_FILES[@]}"; do
            [ -f "voicemail_prompts/$file" ] && ((VM_COUNT++))
        done
        
        echo ""
        echo "Generation complete: $AA_COUNT/5 auto attendant and $VM_COUNT/12 voicemail files"
    fi
fi

TOTAL_FOUND=$((AA_COUNT + VM_COUNT))

if [ $TOTAL_FOUND -eq 0 ]; then
    echo ""
    echo "No voice files found. Please generate them first."
    echo ""
    echo "Run one of these commands:"
    echo "  python3 scripts/generate_tts_prompts.py --company 'Your Company'"
    echo "  python3 scripts/generate_espeak_voices.py --company 'Your Company'"
    exit 1
fi

echo ""
echo "Step 2: Checking git status..."
echo ""

# Check if files are already tracked
TRACKED=$(git ls-files auto_attendant/*.wav voicemail_prompts/*.wav 2>/dev/null | wc -l | tr -d ' ')

echo "Currently tracked voice files in git: $TRACKED"
echo ""

if [ "$TRACKED" -eq 0 ]; then
    echo "Voice files are NOT currently tracked in git (they are in .gitignore)."
    echo ""
    echo "Do you want to commit these voice files to the repository? (y/n)"
    echo ""
    echo "Note: This will:"
    echo "  - Add all .wav files to git (overriding .gitignore)"
    echo "  - Create a commit with the voice files"
    echo "  - These files will be ~1-3 MB total"
    echo ""
    read -r COMMIT_CHOICE
    
    if [[ "$COMMIT_CHOICE" =~ ^[Yy]$ ]]; then
        echo ""
        echo "Step 3: Adding voice files to git..."
        
        # Force add the files (overriding .gitignore)
        git add -f auto_attendant/*.wav voicemail_prompts/*.wav 2>/dev/null || true
        
        # Check what was staged
        STAGED=$(git diff --cached --name-only | grep -E '\.wav$' | wc -l | tr -d ' ')
        
        if [ "$STAGED" -gt 0 ]; then
            echo "  ✓ Staged $STAGED voice files"
            echo ""
            echo "Files to be committed:"
            git diff --cached --name-only | grep -E '\.wav$'
            echo ""
            
            echo "Step 4: Creating commit..."
            git commit -m "Add pre-generated voice prompts for auto attendant and voicemail

- Added $AA_COUNT auto attendant voice files
- Added $VM_COUNT voicemail prompt voice files
- Format: 8000 Hz, 16-bit, mono WAV
- Generated using TTS for immediate use"
            
            echo ""
            echo "✓ Voice files committed successfully!"
            echo ""
            echo "To push to remote:"
            echo "  git push origin main"
            echo ""
        else
            echo "  ✗ No voice files were staged. They may already be committed."
        fi
    else
        echo "Skipping commit. Voice files remain local only."
    fi
else
    echo "Voice files are already tracked in git."
    echo ""
    
    # Check for uncommitted changes
    UNSTAGED=$(git diff --name-only auto_attendant/*.wav voicemail_prompts/*.wav 2>/dev/null | wc -l | tr -d ' ')
    
    if [ "$UNSTAGED" -gt 0 ]; then
        echo "Warning: You have uncommitted changes to voice files:"
        git diff --name-only auto_attendant/*.wav voicemail_prompts/*.wav 2>/dev/null
        echo ""
        echo "Run 'git status' to see details."
    else
        echo "All voice files are committed and up to date."
    fi
fi

echo ""
echo "================================================"
echo "Verification Complete"
echo "================================================"
echo ""
echo "Summary:"
echo "  - Auto Attendant: $AA_COUNT/5 files"
echo "  - Voicemail: $VM_COUNT/12 files"
echo "  - Git tracked: $TRACKED files"
echo ""

if [ $TOTAL_FOUND -eq 17 ]; then
    echo "✓ All voice files are present!"
else
    echo "⚠ Some voice files are missing. Generate them with:"
    echo "  python3 scripts/generate_tts_prompts.py --company 'Your Company'"
fi

echo ""
