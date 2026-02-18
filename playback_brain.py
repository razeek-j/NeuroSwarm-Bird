"""
playback_brain.py
-----------------
Streams pre-recorded EEG data from a CSV file over LSL.
Simulates a live BioSemi EEG device.

Input: EEG_recordings.csv
Output: LSL Stream "BioSemi" (EEG, 4 channels, 256Hz)
"""

import time
import pandas as pd
import numpy as np
from pylsl import StreamInfo, StreamOutlet

# Configuration
CSV_FILE = "EEG_recording.csv"
STREAM_NAME = "BioSemi"
STREAM_TYPE = "EEG"
CHANNEL_COUNT = 4
NOMINAL_SRATE = 256
SLEEP_INTERVAL = 1.0 / NOMINAL_SRATE  # ~0.0039s

def main():
    print(f"🎬 Initializing Playback Brain...")
    
    # 1. Load Data
    try:
        print(f"📂 Loading {CSV_FILE}...")
        df = pd.read_csv(CSV_FILE)
        # Extract first 4 columns (assuming they are the EEG channels)
        # If your CSV has headers, pandas handles them. 
        # If there are timestamps, ensure they are NOT in the first 4 columns 
        # or adjust the iloc range.
        data = df.iloc[:, :4].values
        
        n_samples = len(data)
        print(f"✅ Loaded {n_samples} samples.")
        
        if n_samples == 0:
            print("❌ Error: CSV file is empty.")
            return

    except FileNotFoundError:
        print(f"❌ Error: File '{CSV_FILE}' not found.")
        print("   Please ensure the file is in the same directory.")
        return
    except Exception as e:
        print(f"❌ Error loading CSV: {e}")
        return

    # 2. Setup LSL
    info = StreamInfo(STREAM_NAME, STREAM_TYPE, CHANNEL_COUNT, NOMINAL_SRATE, 'float32', 'playback123')
    outlet = StreamOutlet(info)
    
    print(f"✅ LSL Outlet created: {STREAM_NAME} ({STREAM_TYPE})")
    print(f"   channels={CHANNEL_COUNT}, srate={NOMINAL_SRATE}Hz")
    print("   Broadcasting now... Press Ctrl+C to stop.\n")

    # 3. Playback Loop
    row_idx = 0
    start_time = time.time()
    
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
            # Note: time.sleep is not perfectly precise, but good enough for simulation
            time.sleep(SLEEP_INTERVAL)
            
            # Periodic status (every 10 seconds worth of data)
            if row_idx % (NOMINAL_SRATE * 10) == 0:
                 print(f"[{time.strftime('%H:%M:%S')}] ▶️  Streaming sample {row_idx}/{n_samples}", flush=True)

    except KeyboardInterrupt:
        print("\n🛑 Playback stopped by user.")

if __name__ == "__main__":
    main()
