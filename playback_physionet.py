"""
playback_physionet.py
---------------------
Streams specific columns from a PhysioNet/Muse CSV file over LSL.
Simulates a live Muse EEG device for Boids simulation.

Input: EEG_recording.csv (Columns: TP9, AF7, AF8, TP10)
Output: LSL Stream "Muse" (EEG, 4 channels, 256Hz)
"""

import time
import pandas as pd
import numpy as np
from pylsl import StreamInfo, StreamOutlet

# Configuration
CSV_FILE = "EEG_recording.csv"
TARGET_COLS = ['TP9', 'AF7', 'AF8', 'TP10']
STREAM_NAME = "Muse"
STREAM_TYPE = "EEG"
CHANNEL_COUNT = 4
NOMINAL_SRATE = 256
SLEEP_INTERVAL = 1.0 / NOMINAL_SRATE  # ~0.0039s

def main():
    print(f"🎬 Initializing PhysioNet Playback...")
    
    # 1. Load Data
    try:
        print(f"📂 Loading {CSV_FILE}...")
        df = pd.read_csv(CSV_FILE)
        
        # Check if target columns exist
        missing_cols = [col for col in TARGET_COLS if col not in df.columns]
        if missing_cols:
            print(f"❌ Error: Missing columns in CSV: {missing_cols}")
            return

        # Filter columns
        df = df[TARGET_COLS]
        print(f"✅ Selected columns: {TARGET_COLS}")

        # Handle NaNs: Forward fill first, then fill remaining (start) with 0
        df = df.fillna(method='ffill').fillna(0)
        
        # Scale Data: Divide by 100.0 to match Boids simulation range
        # (Muse data is often in uV, e.g., 800.0 -> 8.0)
        data = df.values / 100.0
        
        n_samples = len(data)
        print(f"✅ Processed {n_samples} samples.")
        
        if n_samples == 0:
            print("❌ Error: CSV file is empty after processing.")
            return

    except FileNotFoundError:
        print(f"❌ Error: File '{CSV_FILE}' not found.")
        print("   Please ensure the file is in the same directory.")
        return
    except Exception as e:
        print(f"❌ Error loading CSV: {e}")
        return

    # 2. Setup LSL
    info = StreamInfo(STREAM_NAME, STREAM_TYPE, CHANNEL_COUNT, NOMINAL_SRATE, 'float32', 'muse_playback')
    outlet = StreamOutlet(info)
    
    print(f"✅ LSL Outlet created: {STREAM_NAME} ({STREAM_TYPE})")
    print(f"   channels={CHANNEL_COUNT}, srate={NOMINAL_SRATE}Hz")
    print("   Broadcasting now... Press Ctrl+C to stop.\n")

    # 3. Playback Loop
    row_idx = 0
    
    try:
        while True:
            # Get current sample
            sample = data[row_idx]
            
            # Push to LSL
            outlet.push_sample(sample)
            
            # Advance index
            row_idx += 1
            
            # Loop formatting
            if row_idx >= n_samples:
                row_idx = 0
                print(f"[{time.strftime('%H:%M:%S')}] 🔄 End of file. Restarting playback...", flush=True)

            # Precise timing: sleep to maintain 256Hz
            time.sleep(SLEEP_INTERVAL)
            
            # Periodic status (every 10 seconds worth of data)
            if row_idx % (NOMINAL_SRATE * 10) == 0:
                 print(f"[{time.strftime('%H:%M:%S')}] ▶️  Streaming sample {row_idx}/{n_samples}", flush=True)

    except KeyboardInterrupt:
        print("\n🛑 Playback stopped by user.")

if __name__ == "__main__":
    main()
