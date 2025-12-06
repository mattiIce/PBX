# Voice Quality Comparison Guide

This guide compares different voice generation options for your PBX system, from basic to professional quality.

## Quick Recommendation

**For the BEST quality on your production system:**
```bash
pip install gTTS pydub
python3 scripts/generate_tts_prompts.py --company "Aluminum Blanking Company"
```

This uses Google's Text-to-Speech API - **completely free, no API key needed**, just requires internet connection. The voices are very natural and human-sounding.

---

## Voice Quality Ranking (Best to Basic)

### 🥇 1. Google TTS (gTTS) - HIGHLY RECOMMENDED
**Quality:** ⭐⭐⭐⭐⭐ Excellent - Very natural, sounds almost human

**Pros:**
- ✅ FREE - No cost, no API key needed
- ✅ Very natural-sounding voices
- ✅ Multiple languages and accents available
- ✅ Easy to use
- ✅ High-quality audio

**Cons:**
- ❌ Requires internet connection
- ❌ Depends on Google's service availability

**Installation:**
```bash
pip install gTTS pydub
sudo apt-get install ffmpeg  # If not already installed
```

**Usage:**
```bash
# Generate all prompts
python3 scripts/generate_tts_prompts.py

# Custom company name
python3 scripts/generate_tts_prompts.py --company "Your Company Name"

# Only auto attendant
python3 scripts/generate_tts_prompts.py --aa-only
```

**Sample Output:**
- Very clear pronunciation
- Natural intonation and rhythm
- Sounds like a professional voice actor
- Suitable for production use

**Cost:** FREE ✅

---

### 🥈 2. Festival TTS - Good Offline Option
**Quality:** ⭐⭐⭐⭐☆ Good - More natural than basic eSpeak

**Pros:**
- ✅ Works completely offline
- ✅ Better voice quality than eSpeak
- ✅ Free and open source
- ✅ More natural intonation

**Cons:**
- ❌ Still somewhat robotic
- ❌ Limited voice options
- ❌ Larger installation size

**Installation:**
```bash
sudo apt-get install festival festvox-us-slt-hts ffmpeg
```

**Usage:**
```bash
python3 scripts/generate_natural_voices.py --engine festival
```

**Sample Output:**
- Smoother than eSpeak
- Better word transitions
- More natural rhythm
- Good for testing and basic production

**Cost:** FREE ✅

---

### 🥉 3. eSpeak Enhanced - Basic Offline Option
**Quality:** ⭐⭐⭐☆☆ Fair - Robotic but clear

**Pros:**
- ✅ Works completely offline
- ✅ Very small installation
- ✅ Clear pronunciation
- ✅ Fast generation
- ✅ Multiple accents (en-us, en-gb, etc.)

**Cons:**
- ❌ Robotic sound
- ❌ Less natural intonation

**Installation:**
```bash
sudo apt-get install espeak ffmpeg
```

**Usage:**
```bash
# American accent
python3 scripts/generate_natural_voices.py

# British accent
python3 scripts/generate_natural_voices.py --voice en-gb
```

**Sample Output:**
- Clear but robotic
- Understandable
- Suitable for testing
- May work for basic production

**Cost:** FREE ✅

---

### 🏆 4. Cloud TTS Services - Professional Quality
**Quality:** ⭐⭐⭐⭐⭐ Excellent - Very natural, multiple voices

#### Google Cloud TTS
- Very natural voices
- Multiple accents and genders
- Neural voices available
- **Cost:** $4 per 1 million characters (~50¢ for all prompts)

#### Amazon Polly
- Highly natural voices
- Multiple languages
- Neural engine available
- **Cost:** $4 per 1 million characters (~50¢ for all prompts)

#### Azure Speech Services
- Neural voices
- Custom voice training available
- Very natural
- **Cost:** $4 per 1 million characters (~50¢ for all prompts)

**Note:** See VOICE_PROMPTS_GUIDE.md for setup instructions

---

### 👤 5. Professional Voice Actor - Best Quality
**Quality:** ⭐⭐⭐⭐⭐ Excellent - Human voice, fully customizable

**Pros:**
- ✅ Actual human voice
- ✅ Fully customizable tone and style
- ✅ Can match your brand
- ✅ Unique to your company
- ✅ One-time purchase

**Cons:**
- ❌ Costs money ($50-$500)
- ❌ Requires coordination
- ❌ Not easily updatable

**Where to Find:**
- Fiverr: $5-$50 per project
- Voices.com: Professional actors
- Upwork: Freelancers
- Local recording studios

**Cost:** $50-$500 one-time

---

## Comparison Table

| Method | Quality | Cost | Internet | Setup | Production Ready |
|--------|---------|------|----------|-------|------------------|
| **gTTS (Google)** | ⭐⭐⭐⭐⭐ | FREE | Required | Easy | ✅ YES |
| **Festival** | ⭐⭐⭐⭐☆ | FREE | No | Easy | ✅ YES |
| **eSpeak Enhanced** | ⭐⭐⭐☆☆ | FREE | No | Easy | ⚠️ Basic Use |
| **Cloud TTS** | ⭐⭐⭐⭐⭐ | ~$0.50 | Required | Medium | ✅ YES |
| **Voice Actor** | ⭐⭐⭐⭐⭐ | $50-500 | No | Complex | ✅ YES |

---

## Recommended Approach by Use Case

### For Production Deployment (Recommended)

1. **First Choice: Use gTTS**
   ```bash
   pip install gTTS pydub
   python3 scripts/generate_tts_prompts.py --company "Your Company"
   ```
   - Best free option
   - Very natural voices
   - Easy to regenerate if text changes

2. **Backup: Use Festival if no internet**
   ```bash
   sudo apt-get install festival festvox-us-slt-hts
   python3 scripts/generate_natural_voices.py --engine festival
   ```
   - Good quality
   - Works offline

### For Testing/Development

Use the included Festival voices (already generated):
- Good enough for testing
- No setup needed
- Can be replaced later

### For High-End Production

1. Use gTTS initially
2. Later upgrade to professional voice actor if budget allows
3. Or use cloud TTS with neural voices

---

## Side-by-Side Quality Examples

### Phrase: "Thank you for calling Aluminum Blanking Company"

**eSpeak Basic:**
- Sounds like: "THANK-you-for-CALL-ing-A-LU-MI-NUM-BLANK-ing-COM-pa-ny"
- Robotic, mechanical, choppy

**Festival:**
- Sounds like: "Thank you for calling Aluminum Blanking Company"
- Smoother, more natural rhythm, still computer-generated

**gTTS (Google):**
- Sounds like: A real person saying it naturally
- Natural intonation, smooth transitions, professional

**Voice Actor:**
- Sounds like: A professional receptionist
- Perfect pronunciation, custom tone, branded

---

## How to Upgrade Voice Quality

### Step 1: Current State (Festival)
Your prompts currently use Festival voices - good offline quality.

### Step 2: Upgrade to gTTS (Best Free Option)

On your production system with internet:

```bash
# Install gTTS
pip install gTTS pydub

# Generate with gTTS
cd /path/to/pbx
python3 scripts/generate_tts_prompts.py --company "Aluminum Blanking Company"

# Listen to samples
aplay auto_attendant/welcome.wav

# If happy, restart PBX
sudo systemctl restart pbx
# or
python main.py
```

### Step 3: Optional - Professional Voice Actor

If you want the absolute best:

1. Write out all your prompt scripts (provided in VOICE_PROMPTS_GUIDE.md)
2. Find voice actor on Fiverr ($20-50 for all prompts)
3. Provide them the text and format requirements (8000 Hz, 16-bit, mono WAV)
4. They record and send you the files
5. Replace the files in `auto_attendant/` and `voicemail_prompts/`
6. Restart PBX

---

## Listen Before You Deploy

Always test the voices before deploying:

```bash
# Play a sample
aplay auto_attendant/welcome.wav

# Or with ffplay
ffplay -nodisp -autoexit auto_attendant/welcome.wav
```

Call your PBX and dial `0` to hear the auto attendant with real voices!

---

## FAQ

### Q: Can I use gTTS without internet?
**A:** No, gTTS requires internet to connect to Google's servers. Use Festival for offline.

### Q: Does gTTS cost money?
**A:** No! gTTS is completely free. No API key, no credit card, no limits for reasonable use.

### Q: Which is better, gTTS or Festival?
**A:** gTTS sounds much more natural (almost human). Festival is good but more robotic. Use gTTS if you have internet.

### Q: Can I use different voices?
**A:** 
- gTTS: Limited voice options, but you can try `lang='en-gb'` for British accent
- Festival: Only a few voices available
- Cloud TTS: Many voices, accents, and genders available
- Voice Actor: Any voice you want!

### Q: How do I change the company name?
**A:** Use the `--company` parameter:
```bash
python3 scripts/generate_tts_prompts.py --company "Your Company Name"
```

### Q: Can I mix methods (some gTTS, some Festival)?
**A:** Yes! All scripts save to the same directories. You can regenerate individual files using any method.

### Q: What about other languages?
**A:** 
- gTTS: Supports 100+ languages! Use `lang='es'` for Spanish, `lang='fr'` for French, etc.
- Festival: Limited to English
- eSpeak: Supports many languages

### Q: How do I know which I'm currently using?
**A:** Check the file size and listen:
- eSpeak: Smaller files (30-60KB), very robotic
- Festival: Medium files (40-80KB), smoother but still robotic
- gTTS: Larger files (50-150KB), very natural sound

---

## Conclusion

**For best results on your production system:**

1. ✅ Use **gTTS** (Google Text-to-Speech) - FREE and very natural
2. ✅ Keep **Festival** files as backup for offline situations
3. ✅ Consider **professional voice actor** if you want the absolute best

**Current setup:** Festival voices are included and work great offline!

**Recommended upgrade:** gTTS when you deploy to production system with internet.

---

**Bottom Line:** The voices you have now (Festival) are good quality and production-ready. To make them sound more human, use gTTS on your production server (requires internet, but FREE and MUCH better quality).
