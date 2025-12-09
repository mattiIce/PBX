# Setup Guide: Google TTS Voices (BEST QUALITY)

Since your server has internet access, you can use **Google Text-to-Speech (gTTS)** to generate very natural, human-sounding voice prompts. This is **completely FREE** and produces much better quality than Festival or eSpeak.

## Why Use gTTS?

**Quality Comparison:**
- **gTTS (Google TTS):** ⭐⭐⭐⭐⭐ - Sounds like a real person, very natural
- **Festival:** ⭐⭐⭐⭐☆ - Better than eSpeak but still robotic
- **eSpeak:** ⭐⭐⭐☆☆ - Robotic and mechanical

**Cost:** FREE - No API key needed, no account required, no limits

**Listen to Samples:** Google TTS is used by Google Translate, Google Assistant, and many professional services.

---

## Quick Setup (2 minutes)

### Step 1: Install Dependencies

```bash
cd /path/to/PBX
pip3 install gTTS pydub
```

### Step 2: Generate Voice Prompts

```bash
python3 scripts/generate_tts_prompts.py --company "Aluminum Blanking Company"
```

That's it! All 17 voice prompts will be generated with high-quality Google voices.

### Step 3: Restart PBX

```bash
# If using systemd
sudo systemctl restart pbx

# Or run manually
python3 main.py
```

### Step 4: Test

Call your PBX and dial `0` to hear the auto attendant with beautiful, natural voices!

---

## Detailed Instructions

### Installation

```bash
# Navigate to PBX directory
cd /home/user/PBX  # Adjust path as needed

# Install Python packages
pip3 install gTTS pydub

# Verify installation
python3 -c "from gtts import gTTS; print('gTTS installed successfully!')"
```

### Generate All Prompts

```bash
# Generate with your company name
python3 scripts/generate_tts_prompts.py --company "Aluminum Blanking Company"

# This will generate:
# - 5 auto attendant prompts (auto_attendant/)
# - 12 voicemail prompts (voicemail_prompts/)
```

**Output:**
```
✓ welcome.wav          (XXXXX bytes) - Welcome greeting
✓ main_menu.wav        (XXXXX bytes) - Main menu options
✓ invalid.wav          (XXXXX bytes) - Invalid option message
...
Generated 17/17 voice prompts successfully
```

### Generate Only Specific Prompts

```bash
# Only auto attendant
python3 scripts/generate_tts_prompts.py --aa-only --company "Your Company"

# Only voicemail
python3 scripts/generate_tts_prompts.py --vm-only

# Custom output directories
python3 scripts/generate_tts_prompts.py --aa-dir /custom/path/aa --vm-dir /custom/path/vm
```

---

## Advanced Options

### Different Languages

gTTS supports 100+ languages!

```bash
# Spanish
python3 scripts/generate_tts_prompts.py --company "Tu Empresa" --language es

# French
python3 scripts/generate_tts_prompts.py --company "Votre Entreprise" --language fr

# German
python3 scripts/generate_tts_prompts.py --company "Ihr Unternehmen" --language de
```

**Supported languages:** en (English), es (Spanish), fr (French), de (German), it (Italian), pt (Portuguese), ru (Russian), ja (Japanese), zh (Chinese), and 100+ more!

### British English Accent

```bash
python3 scripts/generate_tts_prompts.py --company "Your Company" --language en-gb
```

### Slow Speed for Clarity

Edit `scripts/generate_tts_prompts.py` and change:
```python
tts = gTTS(text=text, lang=language, slow=True)  # Add slow=True
```

---

## Customizing the Prompts

### Edit the Script Text

Open `scripts/generate_tts_prompts.py` in a text editor:

```python
# Around line 100, find the prompts dictionary:
prompts = {
    'welcome.wav': {
        'text': f'Thank you for calling {company_name}.',  # Edit this
        'description': 'Welcome greeting'
    },
    'main_menu.wav': {
        'text': 'For Sales, press 1. For Support, press 2...',  # Edit this
        'description': 'Main menu options'
    },
    # ... edit any prompt text
}
```

After editing, regenerate:
```bash
python3 scripts/generate_tts_prompts.py --company "Your Company"
```

---

## Troubleshooting

### "Failed to connect" Error

**Problem:** Cannot reach Google's TTS servers

**Solutions:**
1. Check internet connection:
   ```bash
   ping google.com
   ```

2. Check firewall rules (allow outbound HTTPS to Google)

3. If behind proxy, set proxy:
   ```bash
   export http_proxy="http://proxy:port"
   export https_proxy="http://proxy:port"
   python3 scripts/generate_tts_prompts.py
   ```

4. Temporary network issue - try again in a few minutes

### "No module named 'gtts'" Error

**Problem:** gTTS not installed

**Solution:**
```bash
pip3 install gTTS pydub
```

### "ffmpeg not found" Error

**Problem:** ffmpeg not installed

**Solution:**
```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

### Voice Sounds Choppy or Distorted

**Problem:** Audio conversion issue

**Solution:** Regenerate the prompts:
```bash
python3 scripts/generate_tts_prompts.py --company "Your Company"
```

### Want Different Voice

**Problem:** gTTS free version has limited voice options

**Solution:** For more voice options, consider:
1. Try different language variants (en-us, en-gb, en-au)
2. Use paid cloud TTS (Google Cloud TTS, Amazon Polly, Azure)
3. Hire voice actor

---

## Comparison: Before and After

### Before (Festival/eSpeak)
- **Sound:** Robotic, mechanical
- **Quality:** Clear but obviously computer-generated
- **Suitable for:** Testing, basic production

### After (gTTS)
- **Sound:** Natural, human-like
- **Quality:** Professional, like a real receptionist
- **Suitable for:** Professional production use

### Listen Test

```bash
# Play old Festival voice
aplay auto_attendant_OLD/welcome.wav

# Generate new gTTS voice
python3 scripts/generate_tts_prompts.py --company "Your Company"

# Play new gTTS voice
aplay auto_attendant/welcome.wav

# You'll hear a HUGE difference!
```

---

## Maintenance

### Updating Company Name

Just regenerate:
```bash
python3 scripts/generate_tts_prompts.py --company "New Company Name"
sudo systemctl restart pbx
```

### Adding New Menu Options

1. Edit `config.yml` to add menu option
2. Edit `scripts/generate_tts_prompts.py` to update main_menu text
3. Regenerate:
   ```bash
   python3 scripts/generate_tts_prompts.py --company "Your Company"
   ```
4. Restart PBX

### Keeping Prompts Updated

Create a cron job or script:
```bash
#!/bin/bash
# regenerate_voices.sh
cd /path/to/PBX
python3 scripts/generate_tts_prompts.py --company "Your Company"
sudo systemctl restart pbx
echo "Voices regenerated at $(date)" >> /var/log/pbx_voice_regen.log
```

---

## Cost Analysis

### gTTS (Recommended)
- **Cost:** $0 FREE
- **Quality:** ⭐⭐⭐⭐⭐ Excellent
- **Maintenance:** Easy - just regenerate
- **Total for 17 prompts:** $0

### Professional Voice Actor
- **Cost:** $50-500 one-time
- **Quality:** ⭐⭐⭐⭐⭐ Excellent
- **Maintenance:** Hard - need to re-record for changes
- **Total for 17 prompts:** $50-500

### Cloud TTS Services (Google Cloud, Amazon Polly, Azure)
- **Cost:** ~$4 per 1 million characters
- **Quality:** ⭐⭐⭐⭐⭐ Excellent (more voice options)
- **Maintenance:** Easy - API calls
- **Total for 17 prompts:** ~$0.50

**Winner: gTTS** - Same great quality as paid services, but FREE!

---

## Production Deployment Checklist

- [ ] Server has internet access
- [ ] Python 3 installed
- [ ] pip3 installed
- [ ] Install gTTS: `pip3 install gTTS pydub`
- [ ] Install ffmpeg: `sudo apt-get install ffmpeg`
- [ ] Test generation: `python3 scripts/generate_tts_prompts.py --company "Test"`
- [ ] Listen to sample: `aplay auto_attendant/welcome.wav`
- [ ] Generate final prompts with your company name
- [ ] Test by calling and dialing 0
- [ ] Document for your team
- [ ] Set up regeneration script if needed

---

## Support

If you have issues:

1. Check the troubleshooting section above
2. Review `VOICE_PROMPTS_GUIDE.md` for general voice prompt help
3. Check logs: `logs/pbx.log`
4. Test network: `ping google.com`
5. Try fallback to Festival: `python3 scripts/generate_espeak_voices.py --engine festival`

---

## Summary

**You have internet on your server, so use gTTS!**

**Commands:**
```bash
# Install
pip3 install gTTS pydub

# Generate
python3 scripts/generate_tts_prompts.py --company "Aluminum Blanking Company"

# Restart
sudo systemctl restart pbx

# Test
# Call PBX and dial 0
```

**Result:** Professional, natural-sounding voices that sound almost human. FREE. Easy to update.

**Time to implement:** 2-5 minutes

**Quality improvement:** Robotic → Natural Human Voice

---

## What Users Will Hear

### With gTTS (Recommended):
*"Thank you for calling Aluminum Blanking Company. For Sales, press 1. For Support, press 2. For Accounting, press 3. Or press 0 to speak with an operator."*

Sounds like: A professional, friendly receptionist speaking naturally and clearly.

**This is what you want for production!** 🎉
