# Voicemail Transcription with Vosk (FREE, Offline)

The PBX system now supports **FREE, offline voicemail transcription** using Vosk speech recognition. No API keys, no subscriptions, no cloud dependencies!

## Features

- ✅ **Completely FREE** - No API costs
- ✅ **Works OFFLINE** - No internet required for transcription
- ✅ **No API Keys** - No sign-ups or subscriptions needed
- ✅ **Privacy-Focused** - Audio never leaves your server
- ✅ **Easy to Setup** - Just download a model and configure

## Quick Start

### 1. Install Vosk

```bash
pip install vosk
```

### 2. Download a Speech Model

Vosk requires a language model. Choose one based on your needs:

#### English Models (Recommended)

**Small Model (40 MB) - Fast, Good for Most Uses:**
```bash
mkdir -p models
cd models
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
rm vosk-model-small-en-us-0.15.zip
cd ..
```

**Large Model (1.8 GB) - More Accurate:**
```bash
mkdir -p models
cd models
wget https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip
unzip vosk-model-en-us-0.22.zip
rm vosk-model-en-us-0.22.zip
cd ..
```

#### Other Languages

Visit https://alphacephei.com/vosk/models to download models for:
- Spanish
- French
- German
- Russian
- Chinese
- And many more!

### 3. Configure PBX

Edit `config.yml`:

```yaml
features:
  voicemail_transcription:
    enabled: true
    provider: vosk
    vosk_model_path: models/vosk-model-small-en-us-0.15
```

### 4. Restart PBX

```bash
python main.py
```

That's it! Voicemail transcriptions will now work offline for FREE!

## Switching Between Providers

You can easily switch between transcription providers:

### Vosk (FREE, Offline)
```yaml
voicemail_transcription:
  enabled: true
  provider: vosk
  vosk_model_path: models/vosk-model-small-en-us-0.15
```

### Google Cloud Speech (Requires API Key and Setup)
```yaml
voicemail_transcription:
  enabled: true
  provider: google
  # Set GOOGLE_APPLICATION_CREDENTIALS environment variable
```

## Model Selection Guide

| Model | Size | Speed | Accuracy | Use Case |
|-------|------|-------|----------|----------|
| Small (0.15) | 40 MB | Fast | Good | Most business voicemail |
| Large (0.22) | 1.8 GB | Slower | Better | High accuracy needed |

**Recommendation:** Start with the small model. It's fast and accurate enough for most voicemail transcription needs.

## Audio Requirements

Vosk works best with:
- **Sample Rate:** 8000 Hz (phone quality) or 16000 Hz
- **Channels:** Mono (single channel)
- **Format:** WAV (PCM)

The PBX system automatically records voicemail in the correct format.

## Troubleshooting

### "Vosk model not found"

Make sure you've downloaded and extracted the model to the correct path specified in `config.yml`.

### "Audio must be mono channel"

The audio file has multiple channels. The PBX records in mono by default, but if you're testing with custom audio files, convert them first:
```bash
ffmpeg -i input.wav -ac 1 output.wav
```

### "Unsupported sample rate"

Convert your audio to a supported sample rate:
```bash
ffmpeg -i input.wav -ar 16000 output.wav
```

## Performance Notes

- **Small Model:** Transcribes in real-time or faster on most modern CPUs
- **Large Model:** May take 2-3x real-time on older CPUs
- **Memory:** Small model uses ~100 MB RAM, large model uses ~1 GB RAM

## Comparison with Cloud Providers

| Feature | Vosk | Google Cloud Speech |
|---------|------|---------------------|
| Cost | FREE | ~$0.006/minute |
| Internet Required | No | Yes |
| API Key Required | No | Yes |
| Privacy | Full (local) | Data sent to cloud |
| Setup Complexity | Download model | Get API key + credentials |
| Accuracy | Good | Excellent |

## Why Vosk?

- **No recurring costs** - Perfect for businesses wanting to avoid subscription fees
- **Privacy** - Audio never leaves your server
- **Reliable** - No dependency on internet connectivity or API availability
- **Simple** - No API keys, OAuth flows, or complex authentication
- **Fast enough** - Real-time transcription on modern hardware

## Learn More

- Vosk Project: https://alphacephei.com/vosk/
- Model Downloads: https://alphacephei.com/vosk/models
- Vosk Documentation: https://alphacephei.com/vosk/lm
- GitHub: https://github.com/alphacep/vosk-api
