import subprocess
import time
import sys
import os

def run_auto_demo(producer_script, duration_seconds=30, title=""):
    print("\n" + "="*60)
    print(f" 🎬 NEXT SCENE: {title}")
    print("="*60)
    print(f"Starting {producer_script}...")
    
    cwd = os.getcwd()
    producer_process = None
    sim_process = None

    try:
        # Start the LSL Producer
        producer_process = subprocess.Popen([sys.executable, producer_script], cwd=cwd)
        time.sleep(2) # Give LSL socket time to bind
        
        # Start Boids Sim
        print(f"🐦 Launching Visualizer... (Running for {duration_seconds} seconds)")
        sim_process = subprocess.Popen([sys.executable, "main.py"], cwd=cwd)
        
        # Keep process alive for N seconds
        sim_process.wait(timeout=duration_seconds)
        
    except subprocess.TimeoutExpired:
        print("\n⏳ Scene Time limit reached.")
    except KeyboardInterrupt:
        print("\n🛑 Demo interrupted early by user.")
        sys.exit(0)
    finally:
        print("\n🎬 Cut! Cleaning up scene...")
        if sim_process and sim_process.poll() is None:
            sim_process.terminate()
        if producer_process and producer_process.poll() is None:
            producer_process.terminate()
        print("✅ Cleanup finished.\n")
        time.sleep(3) # Brief cinematic pause between scenes

def main():
    print("========================================")
    print(" 🎥 FULL NEUROSWARM REEL RECORDING 🎥")
    print("========================================")
    print("This script will automatically run both modes.")
    print("Please arrange your windows so both the terminal")
    print("and the PyGame window will be visible on screen.")
    print("Get your screen recorder ready!\n")
    
    for i in range(5, 0, -1):
        print(f"Starting in {i}...")
        time.sleep(1)
        
    # Scene 1: Fake Brain (Toggle from Relaxed to Stressed)
    run_auto_demo("fake_brain.py", duration_seconds=30, title="Mode 1: Simulated Cognitive Shift (Alpha -> Beta)")
    
    # Scene 2: PhysioNet Playback (Real human data)
    run_auto_demo("playback_physionet.py", duration_seconds=25, title="Mode 2: Authentic PhysioNet EEG Playback")

    print("\n========================================")
    print(" 🎉 ALL SCENES COMPLETE! 🎉")
    print(" You can stop your screen recording now.")
    print("========================================")

if __name__ == "__main__":
    main()
