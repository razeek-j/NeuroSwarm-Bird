# NeuroSwarm

![Python Badge](https://img.shields.io/badge/Python-3.9%2B-blue)
![License Badge](https://img.shields.io/badge/License-MIT-green)

![NeuroSwarm Demo](neuroswarm_demo.mov)

## Abstract
Traditional Brain-Computer Interfaces (BCIs) visualize cognitive states using boring 2D line graphs or static charts. This fails to capture the fluid, dynamic, and organic nature of human emotion and thought. **NeuroSwarm** bridges affective computing and generative artificial life. It is a real-time visualization engine that translates raw brain activity into emergent swarm behavior. When biology directly drives artificial life, the simulation transcends static analysis and becomes a seamless reflection of cognitive presence.

## System Architecture

NeuroSwarm implements a robust, closed-loop visualization pipeline:

1. **Data Source** (PhysioNet CSV or Fake Simulator)
2. **LSL Stream** (Lab Streaming Layer Protocol)
3. **Real-time FFT Processing** (Algorithm/Filters)
4. **State Classification** (Relaxed vs. Stressed thresholds)
5. **Boids Physics Engine** (Translates signals to mathematically mapped vectors)
6. **PyGame Render** (System Dashboard & Flocking Engine)

## The Math (Signal Processing)
The system leverages **Fast Fourier Transform (FFT)** to decode the frequency domains of raw EEG data in real-time. By extracting signal power across specific biological bands, we mathematically determine cognitive load:

- **Alpha Power (8–12 Hz):** Signifies a state of relaxation and calmness.
- **Beta Power (13–30 Hz):** Indicates deep focus, high cognitive load, or stress.

A biological metric ratio (`Beta Power / Alpha Power`) continuously drives the engine. When the user is relaxed, the digital flock moves in tight, harmonious, cyan-colored synchronization via dominant cohesion rules. When the user experiences cognitive stress, high Beta activity commands negative cohesion and extreme separation, instantly fracturing the swarm into a chaotic, red-colored dispersion.

## Project Structure

```text
NeuroSwarmBird/
│
├── main.py                - The core Boids simulation engine and PyGame renderer with a real-time system dashboard.
├── fake_brain.py          - A simulated EEG producer that toggles between relaxed and stressed states for testing.
├── playback_physionet.py  - Streams authentic PhysioNet/Muse EEG data (target columns: TP9, AF7, AF8, TP10).
├── playback_brain.py      - A generic LSL playback script for streaming raw CSV EEG recordings.
├── requirements.txt       - Lists project dependencies (pygame, pylsl, numpy, pandas).
└── EEG_recording.csv      - (Required for Playback Mode) Valid Muse/PhysioNet EEG dataset.
```

## Installation

1. **Clone the repository:**
   ```bash
   git clone <your-repository-url>
   cd NeuroSwarmBird
   ```

2. **Set up a Python Virtual Environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows, use `.venv\Scripts\activate`
   ```

3. **Install Core Requirements:**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

NeuroSwarm operates via the Lab Streaming Layer (LSL). You must run the data producer script and the visualization consumer script concurrently.

### Mode 1: Simulated Data (No Hardware/Data Required)
This mode algorithmically toggles between Alpha waves (Sine) and Beta/Noise, pushing data for visual testing.

**Terminal 1:** Initiate the simulated brain.
```bash
source .venv/bin/activate
python fake_brain.py
```

**Terminal 2:** Launch the visualization engine.
```bash
source .venv/bin/activate
python main.py
```

### Mode 2: Authentic PhysioNet Data
This mode streams pre-recorded human EEG data. Ensure your dataset is formatted and saved as `EEG_recording.csv` in the project root.

**Terminal 1:** Stream the PhysioNet LSL data.
```bash
source .venv/bin/activate
python playback_physionet.py
```

**Terminal 2:** Launch the visualization engine.
```bash
source .venv/bin/activate
python main.py
```
