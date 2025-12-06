# Voice Prompt Generation Scripts

This directory contains scripts to generate voice prompts for the PBX system.

## Recommended Script (Works Offline!)

### `generate_espeak_voices.py` ⭐ RECOMMENDED

Generates **REAL VOICE** prompts using eSpeak (offline TTS).

**Advantages:**
- ✅ Works completely offline (no internet required)
- ✅ Generates actual voice speech (not tones)
- ✅ Free and open source
- ✅ No API keys needed
- ✅ Clear and intelligible voice
- ✅ Already installed on most Linux systems

**Usage:**
```bash
# Generate all prompts with default company name
python3 scripts/generate_espeak_voices.py

# Custom company name
python3 scripts/generate_espeak_voices.py --company "Your Company Name"

# Only auto attendant
python3 scripts/generate_espeak_voices.py --aa-only

# Only voicemail
python3 scripts/generate_espeak_voices.py --vm-only
```

**Requirements:**
```bash
sudo apt-get install espeak ffmpeg
```

**Voice Quality:** Robotic but clear. Suitable for testing and basic production use.

---

## Alternative Scripts (For Reference)

### `generate_tts_prompts.py`

Generates prompts using Google Cloud TTS (requires internet).

**Advantages:**
- High quality natural voices
- Multiple languages and accents

**Disadvantages:**
- ❌ Requires internet connection
- ❌ May have API limits

**Usage:**
```bash
pip install gTTS pydub
python3 scripts/generate_tts_prompts.py
```

### `generate_offline_tts.py`

Generates prompts using pyttsx3 (offline).

**Advantages:**
- Works offline
- Python-based

**Disadvantages:**
- ❌ May have compatibility issues
- ❌ More complex setup

**Usage:**
```bash
pip install pyttsx3
sudo apt-get install espeak ffmpeg
python3 scripts/generate_offline_tts.py
```

---

## Which Script Should I Use?

**For most users:** Use `generate_espeak_voices.py` ⭐

It's the simplest, most reliable, and works completely offline.

**For production with budget:** Consider professional voice actor or cloud TTS:
- Google Cloud TTS ($4 per 1M characters)
- Amazon Polly ($4 per 1M characters)
- Azure TTS ($4 per 1M characters)
- Professional voice actor ($50-$500)

See [VOICE_PROMPTS_GUIDE.md](../VOICE_PROMPTS_GUIDE.md) for detailed instructions.

---

## Generated Files

All scripts generate files in these directories:
- `auto_attendant/` - Auto attendant prompts (5 files)
- `voicemail_prompts/` - Voicemail system prompts (12 files)

All files are in telephony format:
- Format: WAV
- Sample Rate: 8000 Hz
- Bit Depth: 16-bit
- Channels: Mono

---

## Customizing Voice Prompts

### Option 1: Edit and Regenerate (Quick)

Edit the script to change the text, then regenerate:

```python
# In generate_espeak_voices.py, find:
prompts = {
    'welcome.wav': {
        'text': f'Thank you for calling {company_name}.',
        'description': 'Welcome greeting'
    },
    # ... edit the text here
}
```

Then run:
```bash
python3 scripts/generate_espeak_voices.py
```

### Option 2: Replace Files (Best Quality)

Record your own professional prompts and save them as:
- `auto_attendant/welcome.wav`
- `auto_attendant/main_menu.wav`
- etc.

Make sure they're in the correct format (8000 Hz, 16-bit, mono).

---

## Troubleshooting

### "espeak: command not found"
```bash
sudo apt-get install espeak
```

### "ffmpeg: command not found"
```bash
sudo apt-get install ffmpeg
```

### "Failed to connect" (gTTS)
- Check internet connection
- Try espeak script instead (works offline)

### Voice quality too robotic
- Use cloud TTS (Google, Amazon, Azure)
- Hire professional voice actor
- See VOICE_PROMPTS_GUIDE.md for instructions
