# Voicemail System Voice Prompts

This directory contains voice prompt files for the voicemail system.

## Generate Voice Files

Voice files are **not included** in the repository. Generate them using gTTS (Google Text-to-Speech):

```bash
uv pip install gTTS pydub
python3 scripts/generate_espeak_voices.py --company "Your Company Name"

# Or generate only voicemail prompts
python3 scripts/generate_espeak_voices.py --vm-only
```

See [scripts/README_VOICE_GENERATION.md](../scripts/README_VOICE_GENERATION.md) for full voice generation documentation.

## Required Files

This directory needs these 13 voice files:

- `enter_pin.wav` - PIN entry prompt
- `invalid_pin.wav` - Invalid PIN message
- `main_menu.wav` - Voicemail main menu
- `options_menu.wav` - Options menu
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
- **Format:** WAV
- **Sample Rate:** 8000 Hz
- **Bit Depth:** 16-bit
- **Channels:** Mono
