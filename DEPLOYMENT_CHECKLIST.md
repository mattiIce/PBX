# Auto Attendant Deployment Checklist

Use this checklist when deploying the PBX with auto attendant to your server.

## ✅ Pre-Deployment

- [ ] Server has Python 3 installed
- [ ] Server has internet connection (for best voice quality)
- [ ] You have sudo/root access (for installing packages)
- [ ] PBX code is on the server

## ✅ Voice Generation (Required - Takes 2-3 minutes)

Voice files are **NOT** included in the repository. You MUST generate them.

### Option A: Google TTS (RECOMMENDED - Best Quality)

```bash
# 1. Install dependencies
pip3 install gTTS pydub
sudo apt-get install ffmpeg  # if not already installed

# 2. Generate voices
cd /path/to/PBX
python3 scripts/generate_tts_prompts.py --company "Aluminum Blanking Company"

# 3. Verify files were created
ls -lh auto_attendant/*.wav voicemail_prompts/*.wav
```

**Expected:** 17 voice files created (5 auto attendant + 12 voicemail)

### Option B: Festival (Good Quality, Offline)

If no internet or gTTS fails:

```bash
sudo apt-get install festival festvox-us-slt-hts ffmpeg
python3 scripts/generate_espeak_voices.py --engine festival
```

### Option C: eSpeak (Basic Quality, Offline)

Last resort if others fail:

```bash
sudo apt-get install espeak ffmpeg
python3 scripts/generate_espeak_voices.py
```

## ✅ Configuration

- [ ] Review `config.yml` auto attendant section
- [ ] Verify menu options point to correct destinations
- [ ] Verify operator extension is correct
- [ ] Update company name in voice files if needed

```yaml
auto_attendant:
  enabled: true
  extension: '0'
  timeout: 10
  max_retries: 3
  operator_extension: '1001'  # ← Verify this exists!
  menu_options:
    - digit: '1'
      destination: '8001'  # ← Verify destinations exist
      description: 'Sales Queue'
    # ... etc
```

## ✅ Testing

- [ ] Start PBX: `python3 main.py` or `sudo systemctl start pbx`
- [ ] Call PBX from a phone
- [ ] Dial `0` to access auto attendant
- [ ] Listen to welcome message
- [ ] Press `1` - verify transfers to sales queue
- [ ] Press `2` - verify transfers to support queue
- [ ] Press invalid digit - verify error handling
- [ ] Wait for timeout - verify timeout handling
- [ ] Press `0` - verify transfers to operator

## ✅ Post-Deployment

- [ ] Voice quality is acceptable
- [ ] All menu options work correctly
- [ ] Timeouts work correctly
- [ ] Invalid inputs work correctly
- [ ] Operator fallback works
- [ ] Document for your team
- [ ] Monitor logs: `tail -f logs/pbx.log`

## 🔧 Troubleshooting

### Voice files not generated

**Problem:** `generate_tts_prompts.py` fails

**Solutions:**
1. Check internet: `ping google.com`
2. Check firewall allows HTTPS to Google
3. Try Festival instead: `python3 scripts/generate_espeak_voices.py --engine festival`

### "No module named 'gtts'"

```bash
pip3 install gTTS pydub
```

### "ffmpeg not found"

```bash
sudo apt-get install ffmpeg
```

### Auto attendant not answering

1. Check voice files exist: `ls auto_attendant/*.wav`
2. Check config: `auto_attendant.enabled: true`
3. Check logs: `tail -f logs/pbx.log`
4. Check extension 0 is not registered to a phone

### Voice sounds robotic

You're using eSpeak or Festival. Upgrade to gTTS:
```bash
pip3 install gTTS pydub
python3 scripts/generate_tts_prompts.py --company "Your Company"
sudo systemctl restart pbx
```

### Transfers not working

The auto attendant code has placeholder transfer implementation. You may need to implement actual call transfers based on your requirements.

## 📝 Quick Reference

### Regenerate voices with new company name

```bash
cd /path/to/PBX
python3 scripts/generate_tts_prompts.py --company "New Company Name"
sudo systemctl restart pbx
```

### Update menu options

1. Edit `config.yml` - add/change menu options
2. Edit `scripts/generate_tts_prompts.py` - update main_menu text
3. Regenerate: `python3 scripts/generate_tts_prompts.py`
4. Restart PBX

### Check which voice engine was used

```bash
# gTTS files are usually 50-150KB
# Festival files are usually 30-80KB  
# eSpeak files are usually 30-60KB
ls -lh auto_attendant/welcome.wav
```

## 📋 Files Generated

### Auto Attendant (5 files)
- `auto_attendant/welcome.wav`
- `auto_attendant/main_menu.wav`
- `auto_attendant/invalid.wav`
- `auto_attendant/timeout.wav`
- `auto_attendant/transferring.wav`

### Voicemail (12 files)
- `voicemail_prompts/enter_pin.wav`
- `voicemail_prompts/invalid_pin.wav`
- `voicemail_prompts/main_menu.wav`
- `voicemail_prompts/message_menu.wav`
- `voicemail_prompts/no_messages.wav`
- `voicemail_prompts/you_have_messages.wav`
- `voicemail_prompts/goodbye.wav`
- `voicemail_prompts/leave_message.wav`
- `voicemail_prompts/recording_greeting.wav`
- `voicemail_prompts/greeting_saved.wav`
- `voicemail_prompts/message_deleted.wav`
- `voicemail_prompts/end_of_messages.wav`

## ✅ Success Criteria

You're done when:
- [ ] All 17 voice files exist
- [ ] Voice quality is acceptable
- [ ] Calling and dialing 0 plays auto attendant
- [ ] All menu options work
- [ ] Team knows how to update if needed

## 🎉 You're Ready!

Your PBX now has a professional auto attendant with natural-sounding voices!

For questions, see:
- `RUN_THIS_ON_SERVER.txt` - Simple instructions
- `SETUP_GTTS_VOICES.md` - Detailed gTTS guide
- `VOICE_QUALITY_COMPARISON.md` - Compare voice options
- `AUTO_ATTENDANT_SUMMARY.md` - Complete implementation details
