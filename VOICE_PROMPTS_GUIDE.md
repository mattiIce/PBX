# Voice Prompts Guide

**Last Updated**: December 29, 2025  
**Purpose**: Complete guide for creating, generating, and customizing voice prompts

## Table of Contents
- [Overview](#overview)
- [Quick Start - Generate Voice Prompts](#quick-start---generate-voice-prompts)
- [Voice Generation Options](#voice-generation-options)
- [Repository Design](#repository-design)
- [Generated Prompt Files](#generated-prompt-files)
- [Creating Professional Voice Prompts](#creating-professional-voice-prompts)
- [Best Practices](#best-practices)

---

## Overview

The PBX system uses voice prompts for Auto Attendant and Voicemail features. Voice files are **NOT included in the repository** - you must generate them after installation.

**Why generate prompts?**
- Customize company name in greetings
- Choose voice quality level (Google TTS vs eSpeak)
- Keep repository size small
- Allow different organizations to customize

---

## Quick Start - Generate Voice Prompts

### Option 1: Google TTS (RECOMMENDED - Best Quality)

**Quality**: ⭐⭐⭐⭐⭐ Natural, human-sounding  
**Cost**: FREE - No API key needed  
**Requirement**: Internet connection

```bash
cd /path/to/PBX

# Install dependencies
pip3 install gTTS pydub
sudo apt-get install ffmpeg

# Generate voice prompts
python3 scripts/generate_tts_prompts.py --company "Your Company Name"

# Verify files were created (should see 17 files)
ls -lh auto_attendant/*.wav voicemail_prompts/*.wav
```

### Option 2: Festival (Good Quality, Offline)

**Quality**: ⭐⭐⭐⭐☆ Better than eSpeak  
**Cost**: FREE  
**Requirement**: No internet needed

```bash
# Install Festival
sudo apt-get install festival festvox-us-slt-hts ffmpeg

# Generate prompts
python3 scripts/generate_espeak_voices.py --engine festival --company "Your Company Name"
```

### Option 3: eSpeak (Basic Quality, Offline)

**Quality**: ⭐⭐⭐☆☆ Robotic but clear  
**Cost**: FREE  
**Requirement**: No internet needed

```bash
# Install eSpeak
sudo apt-get install espeak ffmpeg

# Generate prompts
python3 scripts/generate_espeak_voices.py --company "Your Company Name"
```

### Verify Generation

```bash
# Check which files exist
bash scripts/verify_and_commit_voice_files.sh

# Expected: 17 voice files
# - 5 auto attendant prompts
# - 12 voicemail prompts
```

### Restart PBX

```bash
# If using systemd service
sudo systemctl restart pbx

# Or run manually
python3 main.py
```

---

## Voice Generation Options

### Google TTS (gTTS) - RECOMMENDED

**Advantages:**
- ✅ Natural, human-sounding voice
- ✅ FREE with no limits
- ✅ Used by Google Translate and Google Assistant
- ✅ No account or API key required
- ✅ Best quality available

**Disadvantages:**
- ❌ Requires internet connection
- ❌ Requires pip packages: gTTS, pydub

**Setup:**
```bash
pip3 install gTTS pydub
python3 scripts/generate_tts_prompts.py --company "Your Company"
```

**Listen to Samples:** Google TTS is the same voice used in Google products - very natural!

### Festival TTS

**Advantages:**
- ✅ Better quality than eSpeak
- ✅ Works offline
- ✅ FREE

**Disadvantages:**
- ❌ Still sounds somewhat robotic
- ❌ Larger package size

**Setup:**
```bash
sudo apt-get install festival festvox-us-slt-hts
python3 scripts/generate_espeak_voices.py --engine festival
```

### eSpeak TTS

**Advantages:**
- ✅ Works offline
- ✅ Small package size
- ✅ Fast generation
- ✅ FREE

**Disadvantages:**
- ❌ Robotic, mechanical voice
- ❌ Lowest quality option

**Setup:**
```bash
sudo apt-get install espeak
python3 scripts/generate_espeak_voices.py
```

### Quality Comparison

| TTS Engine | Quality | Internet? | Setup Complexity | Recommendation |
|------------|---------|-----------|-----------------|----------------|
| **Google TTS** | ⭐⭐⭐⭐⭐ | Required | Easy | **Production** |
| **Festival** | ⭐⭐⭐⭐☆ | Not required | Easy | Development |
| **eSpeak** | ⭐⭐⭐☆☆ | Not required | Easiest | Testing only |
| **Professional Recording** | ⭐⭐⭐⭐⭐+ | N/A | Complex | Enterprise |

---

## Repository Design

### Why Voice Files Are Not Included

Voice `.wav` files are intentionally excluded from the repository (see `.gitignore`):

```gitignore
# Generated voice files (generate with scripts/generate_tts_prompts.py)
auto_attendant/*.wav
voicemail_prompts/*.wav
```

**Reasons for exclusion:**
1. ✅ Binary files increase repository size significantly
2. ✅ Generated files should be created by users, not in version control
3. ✅ Allows each organization to customize with their own company name
4. ✅ Follows software development best practices
5. ✅ Users can choose TTS engine based on their needs

### Do You Have Voice Files?

Check your current status:
```bash
cd /path/to/PBX
bash scripts/verify_and_commit_voice_files.sh
```

This script will:
- ✓ Show which voice files exist
- ✓ Show which are missing
- ✓ Offer to generate missing files
- ✓ Offer to commit them to git (if desired for your fork)

### Committing Voice Files (Optional)

If you want to include pre-generated voice files in your own fork:

1. Generate the files:
   ```bash
   python3 scripts/generate_tts_prompts.py --company "Your Company"
   ```

2. Remove .gitignore exclusion:
   ```bash
   # Edit .gitignore and comment out or remove:
   # auto_attendant/*.wav
   # voicemail_prompts/*.wav
   ```

3. Commit the files:
   ```bash
   git add auto_attendant/*.wav voicemail_prompts/*.wav
   git commit -m "Add pre-generated voice prompts"
   ```

**Note:** This is NOT recommended for the main repository, but may be useful for your own organization's fork.

---

## Generated Prompt Files

### Auto Attendant Prompts (`auto_attendant/`)
- `welcome.wav` - Welcome greeting
- `main_menu.wav` - Main menu options
- `invalid.wav` - Invalid option message
- `timeout.wav` - Timeout/no input message
- `transferring.wav` - Call transfer message

### Voicemail System Prompts (`voicemail_prompts/`)
- `enter_pin.wav` - PIN entry prompt
- `invalid_pin.wav` - Invalid PIN message
- `main_menu.wav` - Voicemail main menu
- `message_menu.wav` - Message playback menu
- `no_messages.wav` - No messages notification
- `you_have_messages.wav` - Message count announcement
- `goodbye.wav` - Goodbye message
- `leave_message.wav` - Leave a message prompt
- `recording_greeting.wav` - Record greeting prompt
- `greeting_saved.wav` - Greeting saved confirmation
- `message_deleted.wav` - Message deleted confirmation
- `end_of_messages.wav` - End of messages notification

## Creating Professional Voice Prompts

### Recording Requirements

All audio files must meet these specifications:
- **Format**: WAV (uncompressed)
- **Sample Rate**: 8000 Hz
- **Bit Depth**: 16-bit
- **Channels**: Mono (1 channel)
- **File Naming**: Must match the exact filenames listed above

### Recording Scripts

#### Auto Attendant Scripts

**welcome.wav**
```
"Thank you for calling [Your Company Name]."
```

**main_menu.wav**
```
"For Sales, press 1.
For Support, press 2.
For Accounting, press 3.
Or press 0 to speak with an operator."
```

**invalid.wav**
```
"That is not a valid option. Please try again."
```

**timeout.wav**
```
"We did not receive your selection. Please try again."
```

**transferring.wav**
```
"Please hold while we transfer your call."
```

#### Voicemail Scripts

**enter_pin.wav**
```
"Please enter your PIN followed by the pound key."
```

**invalid_pin.wav**
```
"Invalid PIN. Please try again."
```

**main_menu.wav**
```
"You have [X] new messages.
To listen to your messages, press 1.
For options, press 2.
To exit, press star."
```

**message_menu.wav**
```
"To replay this message, press 1.
For the next message, press 2.
To delete this message, press 3.
To return to the main menu, press star."
```

**no_messages.wav**
```
"You have no new messages."
```

**you_have_messages.wav**
```
"You have [X] new messages."
```

**goodbye.wav**
```
"Goodbye."
```

**leave_message.wav**
```
"Please leave a message after the tone. When you are finished, hang up or press pound."
```

**recording_greeting.wav**
```
"Record your greeting after the tone. When finished, press pound."
```

**greeting_saved.wav**
```
"Your greeting has been saved."
```

**message_deleted.wav**
```
"Message deleted."
```

**end_of_messages.wav**
```
"End of messages."
```

## Recording Methods

### Method 1: DIY Recording

**Equipment Needed:**
- Good quality USB microphone
- Quiet recording environment
- Audio recording software (Audacity is free and recommended)

**Steps:**
1. Download and install Audacity (https://www.audacityteam.org/)
2. Connect your microphone
3. Set project rate to 8000 Hz (bottom left corner)
4. Record your prompt
5. Edit out any mistakes or background noise
6. Export as WAV: File → Export → Export Audio
   - Format: WAV (Microsoft) signed 16-bit PCM
   - Sample Rate: 8000 Hz
   - Channels: Mono
7. Save with the correct filename
8. Copy file to appropriate directory

**Tips for Better Recording:**
- Record in a quiet room away from noise
- Use a pop filter or record at an angle to microphone
- Speak clearly and at a moderate pace
- Use a friendly, professional tone
- Record multiple takes and choose the best one
- Keep consistent volume across all prompts

### Method 2: Text-to-Speech (TTS)

#### Google Cloud Text-to-Speech

```bash
# Install the SDK
pip install google-cloud-texttospeech

# Python script example
from google.cloud import texttospeech
import io

client = texttospeech.TextToSpeechClient()

text = "Thank you for calling"
synthesis_input = texttospeech.SynthesisInput(text=text)

voice = texttospeech.VoiceSelectionParams(
    language_code="en-US",
    name="en-US-Standard-A",  # Female voice
    # or "en-US-Standard-D" for male voice
)

audio_config = texttospeech.AudioConfig(
    audio_encoding=texttospeech.AudioEncoding.LINEAR16,
    sample_rate_hertz=8000,
)

response = client.synthesize_speech(
    input=synthesis_input,
    voice=voice,
    audio_config=audio_config
)

# Save to file
with open("welcome.wav", "wb") as f:
    f.write(response.audio_content)
```

Pricing: $4 per 1 million characters (Standard voices)

#### Amazon Polly

```bash
# Using AWS CLI
aws polly synthesize-speech \
    --output-format pcm \
    --sample-rate 8000 \
    --text "Thank you for calling" \
    --voice-id Joanna \
    welcome.raw

# Convert to WAV using ffmpeg
ffmpeg -f s16le -ar 8000 -ac 1 -i welcome.raw welcome.wav
```

Pricing: $4 per 1 million characters

#### Azure Speech Services

```python
import azure.cognitiveservices.speech as speechsdk

speech_config = speechsdk.SpeechConfig(subscription="YOUR_KEY", region="YOUR_REGION")
speech_config.speech_synthesis_voice_name = "en-US-JennyNeural"

audio_config = speechsdk.audio.AudioOutputConfig(filename="welcome.wav")

synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
synthesizer.speak_text_async("Thank you for calling").get()
```

Pricing: $4 per 1 million characters

#### Free TTS Options

**espeak** (Linux)
```bash
# Install
sudo apt-get install espeak

# Generate audio
espeak -w welcome.wav -s 120 "Thank you for calling"

# Convert to proper format
ffmpeg -i welcome.wav -ar 8000 -ac 1 welcome_8k.wav
```

**pyttsx3** (Python, offline)
```python
import pyttsx3

engine = pyttsx3.init()
engine.setProperty('rate', 150)  # Speed
engine.save_to_file("Thank you for calling", "welcome.wav")
engine.runAndWait()

# Then convert with ffmpeg to proper format
```

### Method 3: Professional Voice Actor

**Where to Find:**
- Fiverr (https://www.fiverr.com) - $5-$50 per recording
- Voices.com (https://www.voices.com) - Professional voice actors
- Upwork (https://www.upwork.com) - Freelance voice talent
- Local recording studios

**What to Provide:**
- Complete script with all prompts
- Desired tone (professional, friendly, formal, etc.)
- Gender preference for voice
- Technical requirements (8000 Hz, 16-bit, mono WAV)

**Cost:** $50-$500 depending on number of prompts and voice actor experience

## Installing Custom Prompts

### Step 1: Prepare Your Files
Ensure all files:
- Are in WAV format, 8000 Hz, 16-bit, mono
- Have correct filenames (case-sensitive)
- Are between 2-30 seconds in length

### Step 2: Test Audio Quality
```bash
# Check file properties
file auto_attendant/welcome.wav
# Should show: WAVE audio, Microsoft PCM, 16 bit, mono 8000 Hz

# Or use soxi if installed
soxi auto_attendant/welcome.wav
```

### Step 3: Copy Files to PBX
```bash
# For Auto Attendant
cp your_recordings/*.wav /path/to/pbx/auto_attendant/

# For Voicemail
cp your_voicemail_recordings/*.wav /path/to/pbx/voicemail_prompts/
```

### Step 4: Restart PBX (if needed)
```bash
# Restart the PBX service
sudo systemctl restart pbx
# Or
python main.py
```

## Converting Audio Formats

If your recordings are in different formats, use ffmpeg to convert:

```bash
# From MP3 to proper WAV
ffmpeg -i input.mp3 -ar 8000 -ac 1 -sample_fmt s16 output.wav

# From M4A to proper WAV
ffmpeg -i input.m4a -ar 8000 -ac 1 -sample_fmt s16 output.wav

# Resample existing WAV
ffmpeg -i input.wav -ar 8000 -ac 1 output.wav

# Batch convert all MP3 files
for file in *.mp3; do
    ffmpeg -i "$file" -ar 8000 -ac 1 -sample_fmt s16 "${file%.mp3}.wav"
done
```

## Updating Configuration

### Auto Attendant

Edit `config.yml` to customize menu options:

```yaml
auto_attendant:
  enabled: true
  extension: '0'
  audio_path: 'auto_attendant'
  menu_options:
    - digit: '1'
      destination: '8001'
      description: 'Sales Queue'
    - digit: '2'
      destination: '8002'
      description: 'Support Queue'
```

### Voicemail

The voicemail system automatically uses prompts from `voicemail_prompts/` directory.

## Troubleshooting

### Audio Not Playing
1. Check file exists in correct directory
2. Verify file permissions (readable by PBX user)
3. Check file format (must be 8000 Hz, 16-bit, mono WAV)
4. Check PBX logs for errors

### Audio Quality Issues
1. Re-record at 8000 Hz natively (don't upsample from lower rate)
2. Remove background noise using Audacity's noise reduction
3. Normalize audio levels (Effect → Normalize in Audacity)
4. Avoid clipping (audio too loud, causes distortion)

### Wrong Prompt Playing
1. Check filename matches exactly (case-sensitive)
2. Clear any caches
3. Restart PBX service

## Testing Your Prompts

### Test Before Deployment
```bash
# Play prompt to verify
aplay auto_attendant/welcome.wav

# Or use ffplay
ffplay -nodisp -autoexit auto_attendant/welcome.wav
```

### Test on Live System
1. Call into the auto attendant (dial extension 0)
2. Listen to each prompt
3. Verify clarity and volume
4. Test all menu options
5. Call voicemail system (dial *XXXX)
6. Test all voicemail menu options

## Best Practices

1. **Consistency**: Use the same voice/speaker for all prompts
2. **Clarity**: Speak clearly with proper enunciation
3. **Pacing**: Not too fast, not too slow (150-160 words per minute)
4. **Tone**: Professional but friendly
5. **Volume**: Consistent across all prompts
6. **Testing**: Test every prompt on actual phones
7. **Backup**: Keep original recordings in case you need to re-edit
8. **Updates**: Plan for easy updates (e.g., when menu options change)

## Examples of Good vs Bad Prompts

### ❌ Bad Prompt
"Um, hi, thanks for, like, calling us. Press 1 if you want sales or something."

Problems:
- Filler words (um, like)
- Unprofessional tone
- Vague ("or something")

### ✅ Good Prompt
"Thank you for calling ABC Company. For Sales, press 1. For Support, press 2."

Good because:
- Clear and professional
- No filler words
- Specific instructions

## Additional Resources

- **Audacity Manual**: https://manual.audacityteam.org/
- **Audio Recording Guide**: https://www.audio-issues.com/recording-tips/
- **Telephone Audio Standards**: ITU-T G.711
- **Sample Voice Prompts**: Many telecom vendors provide free sample prompts online

## Support

If you need help with voice prompts:
1. Check PBX logs: `logs/pbx.log`
2. Test audio format: `file your_prompt.wav`
3. Review this guide
4. Open a GitHub issue with details

---

**Remember**: The tone-based prompts work fine for testing and development, but professional voice prompts significantly improve the caller experience in production environments.
