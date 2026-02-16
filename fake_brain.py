"""
Fake Brain — EEG Simulator
===========================
Simulates a 4-channel BioSemi EEG headset using pylsl.
Toggles between "Relaxed" (Alpha waves) and "Stressed" (Random noise)
every 10 seconds.
"""

import time
import math
import random
from pylsl import StreamInfo, StreamOutlet

# ──────────────────────────────────────────────
#  CONFIGURATION
# ──────────────────────────────────────────────
CHANNEL_COUNT = 4
NOMINAL_SRATE = 256
CHANNEL_FORMAT = 'float32'
STREAM_NAME = 'BioSemi'
STREAM_TYPE = 'EEG'
SOURCE_ID = 'fake_brain_001'

TOGGLE_INTERVAL = 10.0  # Seconds to stay in each state


def main():
    # 1. Create StreamInfo
    info = StreamInfo(
        name=STREAM_NAME,
        type=STREAM_TYPE,
        channel_count=CHANNEL_COUNT,
        nominal_srate=NOMINAL_SRATE,
        channel_format=CHANNEL_FORMAT,
        source_id=SOURCE_ID
    )

    # 2. Create Outlet
    outlet = StreamOutlet(info)
    print(f"✅ LSL Outlet created: {STREAM_NAME} ({STREAM_TYPE})")
    print(f"   channels={CHANNEL_COUNT}, srate={NOMINAL_SRATE}Hz")
    print("   Broadcasting now... Press Ctrl+C to stop.\n")

    start_time = time.time()
    last_print_time = 0
    
    # State tracking
    is_relaxed = True
    next_toggle = time.time() + TOGGLE_INTERVAL

    print(f"[{time.strftime('%H:%M:%S')}] Broadcasting: RELAXED (Alpha waves)")

    while True:
        now = time.time()

        # Toggle state every 10 seconds
        if now >= next_toggle:
            is_relaxed = not is_relaxed
            next_toggle = now + TOGGLE_INTERVAL
            state_name = "RELAXED (Alpha waves)" if is_relaxed else "STRESSED (Noise)"
            print(f"[{time.strftime('%H:%M:%S')}] Broadcasting: {state_name}")

        # Generate sample based on state
        sample = []
        if is_relaxed:
            # RELAXED: Smooth sine waves ~10Hz (Alpha) + slight jitter
            # We use 'now' to drive the sine wave
            base_val = math.sin(now * 10.0 * 2 * math.pi) 
            for _ in range(CHANNEL_COUNT):
                # Add small variation per channel so they aren't identical
                variation = random.uniform(-0.1, 0.1)
                sample.append(base_val + variation)
        else:
            # STRESSED: High-frequency random noise (Beta/Gamma simulation)
            for _ in range(CHANNEL_COUNT):
                sample.append(random.uniform(-2.0, 2.0))

        # Push sample
        outlet.push_sample(sample)

        # Sleep to maintain sampling rate
        # 1/256 is approx 0.0039 seconds
        time.sleep(1.0 / NOMINAL_SRATE)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopping fake brain...")
