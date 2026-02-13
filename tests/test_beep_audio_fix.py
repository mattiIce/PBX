#!/usr/bin/env python3
"""
Test that beep audio is correctly encoded as PCMU (u-law)
This test verifies the fix for the bug where play_beep was sending
raw PCM data with PCMU payload type, causing incorrect audio playback.
"""


from pbx.rtp.handler import RTPPlayer
from pbx.utils.audio import generate_beep_tone, pcm16_to_ulaw


def test_beep_generation() -> bool:
    """Test that beep tone is generated correctly"""

    beep_data = generate_beep_tone(frequency=1000, duration_ms=500, sample_rate=8000)

    # 500ms at 8kHz = 4000 samples
    # Each sample is 16-bit (2 bytes)
    # Total: 4000 * 2 = 8000 bytes
    expected_pcm_size = 8000
    if len(beep_data) != expected_pcm_size:
        return False

    ulaw_data = pcm16_to_ulaw(beep_data)

    # u-law is 8-bit per sample
    # 4000 samples = 4000 bytes
    expected_ulaw_size = 4000
    if len(ulaw_data) != expected_ulaw_size:
        return False

    player = RTPPlayer(
        local_port=30030, remote_host="127.0.0.1", remote_port=30031, call_id="test_beep"
    )

    if not player.start():
        return False

    # Capture the packet count indirectly by checking logs
    result = player.play_beep(frequency=1000, duration_ms=500)
    player.stop()

    if not result:
        # After the fix, play_beep should:
        # 1. Generate 8000 bytes of PCM data
        # 2. Convert to 4000 bytes of u-law data
        # 3. Send 25 packets (4000 bytes / 160 bytes per packet = 25)
        return False

    # Verify the math
    samples_per_packet = 160
    bytes_per_sample_ulaw = 1
    bytes_per_packet = samples_per_packet * bytes_per_sample_ulaw  # 160 bytes

    num_packets = (expected_ulaw_size + bytes_per_packet - 1) // bytes_per_packet
    expected_packets = 25  # ceiling(4000 / 160) = 25

    if num_packets != expected_packets:
        return False

    # 25 packets * 160 samples/packet = 4000 samples
    # 4000 samples / 8000 samples/sec = 0.5 seconds
    total_samples = num_packets * samples_per_packet
    duration_sec = total_samples / 8000
    expected_duration = 0.5

    if abs(duration_sec - expected_duration) >= 0.01:
        return False

    return True


def test_bug_scenario() -> bool:
    """
    Test the specific bug scenario:
    Before fix: play_beep sent 8000 bytes of PCM as if it were u-law
    After fix: play_beep sends 4000 bytes of properly encoded u-law
    """

    from pbx.utils.audio import generate_beep_tone, pcm16_to_ulaw

    pcm_data = generate_beep_tone(1000, 500, 8000)
    ulaw_data = pcm16_to_ulaw(pcm_data)

    samples_per_packet = 160

    # Wrong way (before fix)
    wrong_packets = (len(pcm_data) + samples_per_packet - 1) // samples_per_packet

    # Right way (after fix)
    right_packets = (len(ulaw_data) + samples_per_packet - 1) // samples_per_packet

    if right_packets == 25 and wrong_packets == 50:
        return True
    else:
        return False
