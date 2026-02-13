# Auto Attendant Voice Prompts

This directory contains voice prompt files for the auto attendant system.

## Generate Voice Files

Voice files are **not included** in the repository. Generate them using gTTS (Google Text-to-Speech):

```bash
uv pip install gTTS pydub
python3 scripts/generate_espeak_voices.py --company "Your Company Name"

# Or generate only auto attendant prompts
python3 scripts/generate_espeak_voices.py --aa-only
```

You can also regenerate prompts directly from the **Admin Panel** under the Auto Attendant tab > Voice Prompts Configuration.

See [scripts/README_VOICE_GENERATION.md](../scripts/README_VOICE_GENERATION.md) for full voice generation documentation.

## Required Files

This directory needs these 5 voice files:

- `welcome.wav` - Welcome greeting
- `main_menu.wav` - Main menu options
- `invalid.wav` - Invalid option message
- `timeout.wav` - Timeout message
- `transferring.wav` - Transfer message

## File Format

All files must be:
- **Format:** WAV
- **Sample Rate:** 8000 Hz
- **Bit Depth:** 16-bit
- **Channels:** Mono
