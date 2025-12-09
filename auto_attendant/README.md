# Auto Attendant Voice Prompts

This directory contains voice prompt files for the auto attendant system.

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
python3 scripts/generate_espeak_voices.py --company "Your Company"
```

**Result:** Robotic but functional

## Required Files

This directory needs these 5 voice files:

- `welcome.wav` - Welcome greeting
- `main_menu.wav` - Main menu options
- `invalid.wav` - Invalid option message
- `timeout.wav` - Timeout message
- `transferring.wav` - Transfer message

## File Format

All files must be:
- Format: WAV
- Sample Rate: 8000 Hz
- Bit Depth: 16-bit
- Channels: Mono

## More Info

See `RUN_THIS_ON_SERVER.txt` in the root directory for simple instructions.
