import subprocess
import time
import sys
import os

def run_demo(producer_script):
    """Launches the selected data producer and the main Boids simulation."""
    cwd = os.getcwd()
    producer_process = None
    sim_process = None

    try:
        # Start the LSL Producer
        print(f"\n🧠 Launching LSL Producer: {producer_script}...")
        producer_process = subprocess.Popen([sys.executable, producer_script], cwd=cwd)
        
        # Wait a moment for the LSL stream to initialize and start broadcasting
        print("⏳ Waiting for stream to initialize...")
        time.sleep(2)
        
        # Start the Boids simulation
        print("🐦 Launching NeuroSwarm Simulation (LSL Consumer)...")
        print("-----------------------------------------------------------------")
        print("💡 HINT: To record, bring the PyGame window to the foreground.")
        print("        To stop, close the PyGame window or press ESC.")
        print("-----------------------------------------------------------------\n")
        sim_process = subprocess.Popen([sys.executable, "main.py"], cwd=cwd)
        
        # Wait for the simulation to close (User clicks 'X' or hits ESC)
        sim_process.wait()

    except KeyboardInterrupt:
        print("\n🛑 Demo interrupted by user.")
    except Exception as e:
        print(f"\n❌ Error running demo: {e}")
    finally:
        print("\n🧹 Cleaning up background processes...")
        if sim_process and sim_process.poll() is None:
            sim_process.terminate()
        if producer_process and producer_process.poll() is None:
            producer_process.terminate()
        print("✅ Demo finished gracefully. Ready for next take!\n")

def main():
    while True:
        print("========================================")
        print(" 🎬 NeuroSwarm Video Recording Hub 🎬")
        print("========================================")
        print("Select a data source to showcase:")
        print("  1. Simulated Brain (Dramatic Alpha/Beta shifts - Best for video demo)")
        print("  2. Authentic PhysioNet Data (Real human EEG playback)")
        print("  3. Raw CSV Playback (Generic file)")
        print("  4. Exit")
        print("========================================")
        
        choice = input("\nEnter choice (1/2/3/4): ").strip()
        
        if choice == '1':
            run_demo("fake_brain.py")
        elif choice == '2':
            run_demo("playback_physionet.py")
        elif choice == '3':
            run_demo("playback_brain.py")
        elif choice == '4':
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please select 1, 2, 3, or 4.\n")

if __name__ == "__main__":
    main()
