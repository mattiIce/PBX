# Voicemail System Voice Prompts

This directory contains voice prompt files for the voicemail system.

## Generate Voice Files

Voice files are **not included** in the repository to keep it clean. You need to generate them:

### Option 1: Google TTS (RECOMMENDED - Best Quality)

**Requirements:** Internet connection

```bash
pip3 install gTTS pydub
python3 scripts/generate_tts_prompts.py --company "Your Company Name"
```

**Result:** Natural, human-sounding voices (FREE)

### Option 2: Festival (Good Quality, Offline)

**Requirements:** No internet needed

```bash
sudo apt-get install festival festvox-us-slt-hts
python3 scripts/generate_espeak_voices.py --engine festival
```

**Result:** Better than eSpeak, works offline

### Option 3: eSpeak (Basic Quality, Offline)

**Requirements:** No internet needed

```bash
python3 scripts/generate_espeak_voices.py
```

**Result:** Robotic but functional

## Required Files

This directory needs these 12 voice files:

- `enter_pin.wav` - PIN entry prompt
- `invalid_pin.wav` - Invalid PIN message
- `main_menu.wav` - Voicemail main menu
- `message_menu.wav` - Message playback menu
- `no_messages.wav` - No messages notification
- `you_have_messages.wav` - Message count announcement
- `goodbye.wav` - Goodbye message
- `leave_message.wav` - Leave message prompt
- `recording_greeting.wav` - Record greeting prompt
- `greeting_saved.wav` - Greeting saved confirmation
- `message_deleted.wav` - Message deleted confirmation
- `end_of_messages.wav` - End of messages notification

## File Format

All files must be:
- Format: WAV
- Sample Rate: 8000 Hz
- Bit Depth: 16-bit
- Channels: Mono

## More Info

See `RUN_THIS_ON_SERVER.txt` in the root directory for simple instructions.
