# How to Add Voice Files to the Repository

## Current Status

✅ **Voice generation scripts** are in the repository  
✅ **Documentation** is in the repository  
❌ **Voice .wav files** are NOT in the repository (intentionally excluded via `.gitignore`)

## Why Voice Files Are Not Included

The repository intentionally excludes `.wav` files (see lines 45-46 in `.gitignore`):
```gitignore
# Generated voice files (generate with scripts/generate_tts_prompts.py)
auto_attendant/*.wav
voicemail_prompts/*.wav
```

**Reasons for exclusion:**
1. Binary files increase repository size
2. Generated files should be created by users, not stored in version control
3. Allows each organization to customize with their own company name
4. Follows software development best practices

## Quick Check: Do You Have Voice Files?

Run this command to check:
```bash
cd /home/runner/work/PBX/PBX
bash scripts/verify_and_commit_voice_files.sh
```

This script will:
- ✓ Show which voice files exist
- ✓ Show which are missing
- ✓ Offer to generate missing files
- ✓ Offer to commit them to git (if desired)

## Option 1: Keep Current Design (RECOMMENDED)

**Best Practice:** Users generate voice files after cloning the repository.

**Advantages:**
- Smaller repository size
- Customized company name for each installation
- No binary files in version control
- Flexibility to choose TTS engine

**What users do:**
```bash
# After cloning the repository
cd PBX
pip3 install gTTS pydub
python3 scripts/generate_tts_prompts.py --company "Their Company Name"
```

**No action needed** - this is already configured correctly!

## Option 2: Commit Voice Files to Repository

If you want to provide pre-generated voice files in the repository, follow these steps:

### Step-by-Step Instructions

#### 1. Generate the Voice Files

Choose ONE of these methods:

**Method A: Google TTS (Best Quality, Requires Internet)**
```bash
cd /home/runner/work/PBX/PBX
pip3 install gTTS pydub
python3 scripts/generate_tts_prompts.py --company "Aluminum Blanking Company"
```

**Method B: eSpeak (Offline, Robotic)**
```bash
cd /home/runner/work/PBX/PBX
python3 scripts/generate_espeak_voices.py --company "Aluminum Blanking Company"
```

**Method C: Festival (Offline, Better Quality)**
```bash
sudo apt-get install festival festvox-us-slt-hts
cd /home/runner/work/PBX/PBX
python3 scripts/generate_espeak_voices.py --engine festival --company "Aluminum Blanking Company"
```

#### 2. Verify Files Were Generated

```bash
# Should show 5 files
ls -lh auto_attendant/*.wav

# Should show 12 files
ls -lh voicemail_prompts/*.wav

# Verify format (should be: WAVE audio, Microsoft PCM, 16 bit, mono 8000 Hz)
file auto_attendant/welcome.wav
```

#### 3. Add Files to Git (Override .gitignore)

```bash
# Force add the files (bypasses .gitignore)
git add -f auto_attendant/*.wav
git add -f voicemail_prompts/*.wav

# Verify what will be committed
git status
```

#### 4. Commit the Files

```bash
git commit -m "Add pre-generated voice prompts for auto attendant and voicemail

- Added 5 auto attendant voice files
- Added 12 voicemail prompt voice files  
- Format: 8000 Hz, 16-bit, mono WAV
- Generated using [Google TTS/eSpeak/Festival]"
```

#### 5. Push to GitHub

```bash
git push origin main
```

### Automated Script Method

Or use the automated script:

```bash
cd /home/runner/work/PBX/PBX
bash scripts/verify_and_commit_voice_files.sh
```

This interactive script will:
1. Check for existing files
2. Offer to generate missing files
3. Offer to commit them to git
4. Guide you through the entire process

## Expected Files

### Auto Attendant (5 files)
Located in `auto_attendant/`:
- `welcome.wav` - "Thank you for calling [Company]"
- `main_menu.wav` - "For Sales, press 1. For Support, press 2..."
- `invalid.wav` - "That is not a valid option..."
- `timeout.wav` - "We did not receive your selection..."
- `transferring.wav` - "Please hold while we transfer..."

### Voicemail (12 files)
Located in `voicemail_prompts/`:
- `enter_pin.wav` - "Please enter your PIN..."
- `invalid_pin.wav` - "Invalid PIN..."
- `main_menu.wav` - "To listen to messages, press 1..."
- `message_menu.wav` - "To replay, press 1..."
- `no_messages.wav` - "You have no new messages"
- `you_have_messages.wav` - "You have new messages"
- `goodbye.wav` - "Goodbye"
- `leave_message.wav` - "Please leave a message..."
- `recording_greeting.wav` - "Record your greeting..."
- `greeting_saved.wav` - "Your greeting has been saved"
- `message_deleted.wav` - "Message deleted"
- `end_of_messages.wav` - "End of messages"

## File Requirements

All voice files must meet these specifications:
- **Format:** WAV (uncompressed)
- **Sample Rate:** 8000 Hz
- **Bit Depth:** 16-bit
- **Channels:** Mono (1 channel)

## Verification Commands

### Check if files exist locally:
```bash
ls -1 auto_attendant/*.wav voicemail_prompts/*.wav 2>/dev/null | wc -l
# Should output: 17
```

### Check if files are tracked in git:
```bash
git ls-files auto_attendant/*.wav voicemail_prompts/*.wav | wc -l
# If 0: files not tracked
# If 17: all files tracked
```

### Check file format:
```bash
file auto_attendant/welcome.wav
# Should show: WAVE audio, Microsoft PCM, 16 bit, mono 8000 Hz
```

### Listen to a file (Linux):
```bash
aplay auto_attendant/welcome.wav
# or
ffplay -nodisp -autoexit auto_attendant/welcome.wav
```

## Troubleshooting

### "Command not found: python3"
Install Python 3:
```bash
sudo apt-get update
sudo apt-get install python3 python3-pip
```

### "No module named 'gtts'"
Install dependencies:
```bash
pip3 install gTTS pydub
```

### "ffmpeg not found"
Install ffmpeg:
```bash
sudo apt-get install ffmpeg
```

### "Failed to connect" (Google TTS)
- Check internet connection: `ping google.com`
- Check firewall settings
- Use offline option (eSpeak or Festival)

### Files generated but not showing in git
The files are in `.gitignore`. Use `-f` flag:
```bash
git add -f auto_attendant/*.wav voicemail_prompts/*.wav
```

## Recommendation

**I recommend Option 1 (keep current design)** because:

✅ Follows best practices (generated files not in version control)  
✅ Keeps repository size small  
✅ Allows customization per installation  
✅ More flexible (users choose TTS engine)  

However, **Option 2 is valid** if you want to provide immediate convenience for users who clone the repository.

## Summary

- **Current Status:** Voice files are NOT in the repository (by design)
- **To Add Them:** Follow Option 2 instructions above
- **To Keep As-Is:** No action needed, users generate their own files
- **Quick Tool:** Use `scripts/verify_and_commit_voice_files.sh` for guided process

## Questions?

See these documents for more information:
- `VOICE_FILES_STATUS_REPORT.md` - Detailed analysis
- `SETUP_GTTS_VOICES.md` - Google TTS setup guide
- `VOICE_PROMPTS_GUIDE.md` - Complete voice prompts documentation
- `GENERATE_VOICES_README.txt` - Quick start guide
