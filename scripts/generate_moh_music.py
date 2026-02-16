#!/usr/bin/env python3
"""
Generate Music on Hold (MOH) audio files for the PBX system.

Creates simple, pleasant musical tones suitable for hold music.
All files are in telephony format: 8000 Hz, 16-bit, mono WAV.
"""

import argparse
import math
import struct
import wave
from pathlib import Path


def generate_tone(
    frequency: float, duration: float, sample_rate: int = 8000, amplitude: float = 0.3
) -> list[int]:
    """
    Generate a sine wave tone.

    Args:
        frequency: Frequency in Hz
        duration: Duration in seconds
        sample_rate: Sample rate in Hz (default 8000 for telephony)
        amplitude: Amplitude (0.0 to 1.0, default 0.3 for pleasant listening)

    Returns:
        List of sample values
    """
    samples = []
    num_samples = int(duration * sample_rate)

    for i in range(num_samples):
        # Generate sine wave
        t = i / sample_rate
        value = amplitude * math.sin(2 * math.pi * frequency * t)
        # Convert to 16-bit integer
        sample = int(value * 32767)
        samples.append(sample)

    return samples


def generate_chord(
    frequencies: list[float], duration: float, sample_rate: int = 8000, amplitude: float = 0.2
) -> list[int]:
    """
    Generate a chord (multiple frequencies played together).

    Args:
        frequencies: List of frequencies in Hz
        duration: Duration in seconds
        sample_rate: Sample rate in Hz
        amplitude: Base amplitude per frequency

    Returns:
        List of sample values
    """
    samples = []
    num_samples = int(duration * sample_rate)

    for i in range(num_samples):
        t = i / sample_rate
        value = 0

        # Sum all frequencies
        for freq in frequencies:
            value += amplitude * math.sin(2 * math.pi * freq * t)

        # Normalize to prevent clipping
        value = value / len(frequencies)

        # Convert to 16-bit integer
        sample = int(value * 32767)
        samples.append(sample)

    return samples


def add_fade(samples: list[int], fade_duration: float = 0.1, sample_rate: int = 8000) -> list[int]:
    """
    Add fade in/out to samples to prevent clicks.

    Args:
        samples: List of sample values
        fade_duration: Fade duration in seconds
        sample_rate: Sample rate in Hz

    Returns:
        List of faded sample values
    """
    fade_samples = int(fade_duration * sample_rate)
    result = samples.copy()

    # Fade in
    for i in range(min(fade_samples, len(result))):
        factor = i / fade_samples
        result[i] = int(result[i] * factor)

    # Fade out
    for i in range(min(fade_samples, len(result))):
        factor = i / fade_samples
        idx = len(result) - 1 - i
        result[idx] = int(result[idx] * factor)

    return result


def write_wav_file(filename: str, samples: list[int], sample_rate: int = 8000) -> None:
    """
    Write samples to WAV file.

    Args:
        filename: Output filename
        samples: List of sample values
        sample_rate: Sample rate in Hz
    """
    with wave.open(filename, "w") as wav_file:
        # Set parameters: 1 channel (mono), 2 bytes per sample (16-bit), sample rate
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)

        # Convert samples to bytes
        for sample in samples:
            wav_file.writeframes(struct.pack("<h", sample))


def generate_simple_melody(output_file: str | Path, duration: int = 30) -> None:
    """
    Generate a simple, pleasant melody.

    Args:
        output_file: Output WAV file path
        duration: Total duration in seconds
    """
    print(f"Generating simple melody: {output_file}")

    # Musical notes (frequencies in Hz)
    # Using a pleasant major scale pattern
    notes = [
        523.25,  # C5
        587.33,  # D5
        659.25,  # E5
        698.46,  # F5
        783.99,  # G5
    ]

    samples = []
    note_duration = 2.0  # Each note plays for 2 seconds
    num_notes = int(duration / note_duration)

    for i in range(num_notes):
        # Alternate through notes with a pattern
        note_idx = i % len(notes)
        freq = notes[note_idx]

        # Generate note
        note_samples = generate_tone(freq, note_duration, amplitude=0.25)

        # Add fade to prevent clicks
        note_samples = add_fade(note_samples, fade_duration=0.05)

        samples.extend(note_samples)

    # Trim to exact duration
    samples = samples[: int(duration * 8000)]

    write_wav_file(output_file, samples)
    print(f"✓ Generated {output_file}")


def generate_ambient_tones(output_file: str | Path, duration: int = 30) -> None:
    """
    Generate ambient, soothing tones.

    Args:
        output_file: Output WAV file path
        duration: Total duration in seconds
    """
    print(f"Generating ambient tones: {output_file}")

    # Use harmonious frequencies
    base_freq = 220.0  # A3
    frequencies = [
        base_freq,  # Root
        base_freq * 1.25,  # Major third
        base_freq * 1.5,  # Perfect fifth
    ]

    samples = generate_chord(frequencies, duration, amplitude=0.15)
    samples = add_fade(samples, fade_duration=0.5)

    write_wav_file(output_file, samples)
    print(f"✓ Generated {output_file}")


def generate_arpeggio(output_file: str | Path, duration: int = 30) -> None:
    """
    Generate an arpeggio pattern.

    Args:
        output_file: Output WAV file path
        duration: Total duration in seconds
    """
    print(f"Generating arpeggio: {output_file}")

    # Major chord arpeggio
    frequencies = [
        261.63,  # C4
        329.63,  # E4
        392.00,  # G4
        523.25,  # C5
    ]

    samples = []
    note_duration = 0.5  # Each note plays for 0.5 seconds
    num_cycles = int(duration / (note_duration * len(frequencies)))

    for _ in range(num_cycles):
        for freq in frequencies:
            note_samples = generate_tone(freq, note_duration, amplitude=0.25)
            note_samples = add_fade(note_samples, fade_duration=0.02)
            samples.extend(note_samples)

    # Trim to exact duration
    samples = samples[: int(duration * 8000)]

    write_wav_file(output_file, samples)
    print(f"✓ Generated {output_file}")


def generate_soft_pad(output_file: str | Path, duration: int = 30) -> None:
    """
    Generate a soft, sustained pad sound.

    Args:
        output_file: Output WAV file path
        duration: Total duration in seconds
    """
    print(f"Generating soft pad: {output_file}")

    # Rich chord with multiple harmonics
    base = 196.00  # G3
    frequencies = [
        base,  # Root
        base * 1.25,  # Major third
        base * 1.5,  # Perfect fifth
        base * 2.0,  # Octave
    ]

    samples = generate_chord(frequencies, duration, amplitude=0.12)
    samples = add_fade(samples, fade_duration=1.0)

    write_wav_file(output_file, samples)
    print(f"✓ Generated {output_file}")


def generate_gentle_chimes(output_file: str | Path, duration: int = 30) -> None:
    """
    Generate gentle chime sounds.

    Args:
        output_file: Output WAV file path
        duration: Total duration in seconds
    """
    print(f"Generating gentle chimes: {output_file}")

    # Bell-like frequencies
    chime_freqs = [
        523.25,  # C5
        659.25,  # E5
        783.99,  # G5
    ]

    samples = []
    chime_duration = 3.0  # Each chime rings for 3 seconds
    silence_duration = 1.0  # 1 second of silence between chimes

    num_chimes = int(duration / (chime_duration + silence_duration))

    for i in range(num_chimes):
        # Alternate between different chimes
        freq = chime_freqs[i % len(chime_freqs)]

        # Generate chime with natural decay
        chime_samples = generate_tone(freq, chime_duration, amplitude=0.3)

        # Add envelope for natural sound (quick fade in, slow fade out)
        fade_in = int(0.01 * 8000)
        for j in range(fade_in):
            chime_samples[j] = int(chime_samples[j] * (j / fade_in))

        fade_out = int(2.0 * 8000)
        for j in range(min(fade_out, len(chime_samples))):
            idx = len(chime_samples) - 1 - j
            chime_samples[idx] = int(chime_samples[idx] * (j / fade_out))

        samples.extend(chime_samples)

        # Add silence
        silence_samples = [0] * int(silence_duration * 8000)
        samples.extend(silence_samples)

    # Trim to exact duration
    samples = samples[: int(duration * 8000)]

    write_wav_file(output_file, samples)
    print(f"✓ Generated {output_file}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate Music on Hold (MOH) audio files for PBX system"
    )
    parser.add_argument(
        "--output-dir",
        default="moh/default",
        help="Output directory for MOH files (default: moh/default)",
    )
    parser.add_argument(
        "--duration", type=int, default=30, help="Duration of each track in seconds (default: 30)"
    )
    parser.add_argument("--all", action="store_true", help="Generate all MOH tracks (default)")
    parser.add_argument("--melody", action="store_true", help="Generate only simple melody")
    parser.add_argument("--ambient", action="store_true", help="Generate only ambient tones")
    parser.add_argument("--arpeggio", action="store_true", help="Generate only arpeggio")
    parser.add_argument("--pad", action="store_true", help="Generate only soft pad")
    parser.add_argument("--chimes", action="store_true", help="Generate only gentle chimes")

    args = parser.parse_args()

    # Create output directory
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    # Determine which tracks to generate
    generate_all = args.all or not (
        args.melody or args.ambient or args.arpeggio or args.pad or args.chimes
    )

    print("=" * 60)
    print("Music on Hold (MOH) Generator")
    print("=" * 60)
    print(f"Output directory: {args.output_dir}")
    print(f"Track duration: {args.duration} seconds")
    print("Audio format: 8000 Hz, 16-bit, mono WAV")
    print("=" * 60)
    print()

    # Generate requested tracks
    if generate_all or args.melody:
        generate_simple_melody(Path(args.output_dir) / "melody.wav", args.duration)

    if generate_all or args.ambient:
        generate_ambient_tones(Path(args.output_dir) / "ambient.wav", args.duration)

    if generate_all or args.arpeggio:
        generate_arpeggio(Path(args.output_dir) / "arpeggio.wav", args.duration)

    if generate_all or args.pad:
        generate_soft_pad(Path(args.output_dir) / "pad.wav", args.duration)

    if generate_all or args.chimes:
        generate_gentle_chimes(Path(args.output_dir) / "chimes.wav", args.duration)

    print()
    print("=" * 60)
    print("✓ MOH generation complete!")
    print("=" * 60)
    print()
    print("Generated files:")
    output_path = Path(args.output_dir)
    for filepath in sorted(output_path.iterdir()):
        if filepath.suffix == ".wav":
            size_kb = filepath.stat().st_size / 1024
            print(f"  • {filepath.name} ({size_kb:.1f} KB)")
    print()
    print("Usage:")
    print(f"  1. Files are in: {args.output_dir}/")
    print("  2. PBX will automatically load these on startup")
    print("  3. Music will play when calls are placed on hold")
    print()
    print("To regenerate with different duration:")
    print(f"  python3 {__file__} --duration 60")
    print()


if __name__ == "__main__":
    main()
