================================================================================
HOW TO GENERATE NATURAL VOICE PROMPTS WITH GOOGLE TTS
================================================================================

SIMPLE 3-STEP PROCESS:

Step 1: Install Dependencies (one-time setup)
----------------------------------------------
pip3 install gTTS pydub


Step 2: Generate Voice Prompts
-------------------------------
cd /path/to/PBX
python3 scripts/generate_tts_prompts.py --company "Aluminum Blanking Company"


Step 3: Restart PBX
-------------------
sudo systemctl restart pbx
OR
python3 main.py


THAT'S IT!
==========

The script will generate 17 high-quality voice files:
- 5 auto attendant prompts in auto_attendant/
- 12 voicemail prompts in voicemail_prompts/

These voices will sound MUCH more human and natural than the current ones.


QUICK REFERENCE:
================

# Generate all prompts with custom company name:
python3 scripts/generate_tts_prompts.py --company "Your Company Name"

# Generate only auto attendant:
python3 scripts/generate_tts_prompts.py --aa-only

# Generate only voicemail:
python3 scripts/generate_tts_prompts.py --vm-only

# Test the voice:
aplay auto_attendant/welcome.wav


TROUBLESHOOTING:
================

If you get "No module named 'gtts'":
  pip3 install gTTS pydub

If you get "ffmpeg not found":
  sudo apt-get install ffmpeg

If you get "Failed to connect":
  - Check internet: ping google.com
  - Check firewall allows HTTPS to Google
  - Try again in a few minutes


THAT'S ALL YOU NEED!
====================
The voices will sound like a professional human receptionist.
Much better than the robotic Festival voices currently included.

Total time: 2-3 minutes
Cost: FREE
Quality: Excellent (sounds human)
