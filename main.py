"""
NeuroSwarmBird — Real-time Boids Flocking Simulation
=====================================================
Implements Craig Reynolds' Boids algorithm with three steering rules:
separation, alignment, and cohesion.  Uses pygame for rendering.
Integrates LSL (Lab Streaming Layer) for real-time EEG control.
"""

import math
import random
import collections
import pygame
import numpy as np  # For FFT
from pygame.math import Vector2

# ──────────────────────────────────────────────
#  LSL IMPORTS
# ──────────────────────────────────────────────
try:
    from pylsl import StreamInlet, resolve_byprop
    LSL_AVAILABLE = True
except ImportError as e:
    LSL_AVAILABLE = False
    print(f"⚠️ pylsl import failed: {e}")
    print("⚠️ LSL integration disabled.")


# ──────────────────────────────────────────────
#  TUNABLE PARAMETERS — tweak these to taste
# ──────────────────────────────────────────────
WIDTH, HEIGHT = 1200, 800          # Window dimensions
NUM_BOIDS = 50                     # Number of boids in the flock
PERCEPTION_RADIUS = 50.0           # How far a boid can "see"

# FLOCKING WEIGHTS (Modified by LSL)
SEPARATION_WEIGHT = 1.5            # Avoid crowding neighbours
ALIGNMENT_WEIGHT = 1.0             # Steer toward average heading
COHESION_WEIGHT = 1.0              # Steer toward centre of mass

# PHYSICS LIMITS (Modified by LSL)
MAX_SPEED = 4.0                    # Maximum velocity magnitude
MAX_FORCE = 0.1                    # Maximum steering force

FPS = 60                           # Target frames per second
BOID_SIZE = 8                      # Triangle size in pixels
BOID_COLOR = (0, 255, 255)         # Cyan (default: RELAXED)
BG_COLOR = (0, 0, 0)              # Black
DASHBOARD_FONT = None             # Initialized in main()


# ──────────────────────────────────────────────
#  DASHBOARD
# ──────────────────────────────────────────────
def draw_dashboard(screen, buffer, metrics):
    """Draws a semi-transparent dashboard with signal and FFT data."""
    if not metrics:
        return

    # 1. Panel Background
    panel_w, panel_h = 300, 200
    panel_x, panel_y = 20, HEIGHT - panel_h - 20
    
    s = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    s.fill((30, 30, 30, 180))  # Dark grey, semi-transparent

    # 2. Raw Signal Graph (Top)
    # Scale raw buffer (-2 to 2 typically) to fit in top 60px
    # Center is at y=30
    if len(buffer) > 1:
        points = []
        for i, val in enumerate(buffer):
            x = (i / 256) * panel_w
            # Scale factor: 1.0 amplitude -> 20px height
            y = 30 - (val * 10) 
            points.append((x, y))
        pygame.draw.lines(s, (255, 255, 255), False, points, 1)
    
    # Label
    # font = pygame.font.SysFont("monospace", 14) # MOVED TO GLOBAL
    label = DASHBOARD_FONT.render("Raw Signal (EEG)", True, (200, 200, 200))
    s.blit(label, (5, 5))

    # 3. FFT Bars (Middle)
    # Alpha (Blue), Beta (Red)
    # Max power for scaling ~ 2000 (heuristic)
    bar_width = 80
    max_h = 80
    scale = 0.05
    
    alpha_h = min(metrics['alpha_power'] * scale, max_h)
    beta_h = min(metrics['beta_power'] * scale, max_h)
    
    # Alpha Bar
    pygame.draw.rect(s, (0, 150, 255), (20, 140 - alpha_h, bar_width, alpha_h))
    s.blit(DASHBOARD_FONT.render("Alpha", True, (0, 150, 255)), (20, 145))
    
    # Beta Bar
    pygame.draw.rect(s, (255, 50, 50), (120, 140 - beta_h, bar_width, beta_h))
    s.blit(DASHBOARD_FONT.render("Beta", True, (255, 50, 50)), (120, 145))

    # 4. State Text (Bottom)
    state_color = (0, 255, 0) if metrics['state'] == "RELAXED" else (255, 0, 0)
    state_text = DASHBOARD_FONT.render(f"State: {metrics['state']}", True, state_color)
    ratio_text = DASHBOARD_FONT.render(f"Ratio: {metrics['ratio']:.2f}", True, (200, 200, 200))
    
    s.blit(state_text, (10, 170))
    s.blit(ratio_text, (160, 170))

    screen.blit(s, (panel_x, panel_y))


def get_brain_state(data_buffer, rate=256):
    """
    Analyze buffer (256 samples) using FFT.
    Returns dictionary with state and power metrics.
    """
    if len(data_buffer) < rate:
        return None  # Not enough data yet

    # Convert to numpy array for FFT
    data = np.array(data_buffer)
    
    # Compute FFT
    fft_vals = np.fft.rfft(data)
    freqs = np.fft.rfftfreq(len(data), 1/rate)
    psd = np.abs(fft_vals)**2

    # Extract Band Power
    # Alpha: 8-12 Hz
    alpha_mask = (freqs >= 8) & (freqs <= 12)
    alpha_power = np.sum(psd[alpha_mask])

    # Beta/Noise: 13-30 Hz
    beta_mask = (freqs >= 13) & (freqs <= 30)
    beta_power = np.sum(psd[beta_mask])

    # Avoid division by zero
    ratio = 0.0
    if alpha_power > 0:
        ratio = beta_power / alpha_power
    
    # Threshold: If Beta/Noise is 2x stronger than Alpha, trigger Stress
    state = "STRESSED" if ratio > 2.0 else "RELAXED"
    
    return {
        "state": state,
        "alpha_power": alpha_power,
        "beta_power": beta_power,
        "ratio": ratio
    }



# ──────────────────────────────────────────────
#  BOID CLASS
# ──────────────────────────────────────────────

class Boid:
    """A single boid with position, velocity, and acceleration."""

    def __init__(self):
        self.position = Vector2(random.uniform(0, WIDTH), random.uniform(0, HEIGHT))
        # Random initial velocity with random direction and speed
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(1, MAX_SPEED)
        self.velocity = Vector2(math.cos(angle) * speed, math.sin(angle) * speed)
        self.acceleration = Vector2(0, 0)
        
        # Trail history (stores tuples of (x, y))
        self.trail = collections.deque(maxlen=20)

    # ── Flocking rules ────────────────────────

    def _steer_towards(self, target_vec):
        """Return a steering force: desired direction clamped to MAX_FORCE."""
        if target_vec.length_squared() == 0:
            return Vector2(0, 0)
        desired = target_vec.normalize() * MAX_SPEED
        steer = desired - self.velocity
        if steer.length() > MAX_FORCE:
            steer.scale_to_length(MAX_FORCE)
        return steer

    def separation(self, boids):
        """Steer to avoid crowding local flockmates."""
        steer = Vector2(0, 0)
        total = 0

        for other in boids:
            diff = self.position - other.position
            d = diff.length()
            if other is not self and d < PERCEPTION_RADIUS and d > 0:
                steer += diff / d          # Away from neighbour, weighted by 1/d
                total += 1

        if total > 0:
            steer /= total
            return self._steer_towards(steer)
        return steer

    def alignment(self, boids):
        """Steer towards the average heading of local flockmates."""
        avg_vel = Vector2(0, 0)
        total = 0

        for other in boids:
            d = self.position.distance_to(other.position)
            if other is not self and d < PERCEPTION_RADIUS:
                avg_vel += other.velocity
                total += 1

        if total > 0:
            avg_vel /= total
            return self._steer_towards(avg_vel)
        return Vector2(0, 0)

    def cohesion(self, boids):
        """Steer to move toward the average position of local flockmates."""
        centre = Vector2(0, 0)
        total = 0

        for other in boids:
            d = self.position.distance_to(other.position)
            if other is not self and d < PERCEPTION_RADIUS:
                centre += other.position
                total += 1

        if total > 0:
            centre /= total
            desired = centre - self.position
            return self._steer_towards(desired)
        return Vector2(0, 0)

    # ── Lifecycle ─────────────────────────────

    def flock(self, boids):
        """Compute combined steering from all three rules."""
        sep = self.separation(boids) * SEPARATION_WEIGHT
        ali = self.alignment(boids) * ALIGNMENT_WEIGHT
        coh = self.cohesion(boids) * COHESION_WEIGHT

        self.acceleration = sep + ali + coh

    def update(self):
        """Integrate acceleration → velocity → position, then reset."""
        # Update trail BEFORE moving (stores previous position)
        self.trail.append((self.position.x, self.position.y))
        
        self.velocity += self.acceleration
        if self.velocity.length() > MAX_SPEED:
            self.velocity.scale_to_length(MAX_SPEED)
        self.position += self.velocity
        self.acceleration = Vector2(0, 0)

    def edges(self):
        """Toroidal wrap — boid reappears on the opposite side."""
        wrapped = False
        if self.position.x > WIDTH:
            self.position.x = 0
            wrapped = True
        elif self.position.x < 0:
            self.position.x = WIDTH
            wrapped = True
        if self.position.y > HEIGHT:
            self.position.y = 0
            wrapped = True
        elif self.position.y < 0:
            self.position.y = HEIGHT
            wrapped = True
        
        if wrapped:
            self.trail.clear()

    def draw(self, screen):
        """Render the boid as a small triangle pointing in the direction of travel."""
        # Draw Trail
        if len(self.trail) > 1:
            pygame.draw.lines(screen, BOID_COLOR, False, list(self.trail), 1)

        angle = math.atan2(self.velocity.y, self.velocity.x)

        # Triangle vertices: tip in front, two wings behind
        tip = self.position + Vector2(math.cos(angle), math.sin(angle)) * BOID_SIZE
        left = self.position + Vector2(math.cos(angle + 2.5), math.sin(angle + 2.5)) * (BOID_SIZE * 0.6)
        right = self.position + Vector2(math.cos(angle - 2.5), math.sin(angle - 2.5)) * (BOID_SIZE * 0.6)

        pygame.draw.polygon(screen, BOID_COLOR, [tip, left, right])

# ──────────────────────────────────────────────
#  MAIN LOOP
# ──────────────────────────────────────────────

def main():
    global SEPARATION_WEIGHT, ALIGNMENT_WEIGHT, COHESION_WEIGHT
    global MAX_SPEED, MAX_FORCE, BOID_COLOR
    global DASHBOARD_FONT

    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("NeuroSwarmBird — Boids Flocking Simulation (LSL Enabled)")
    clock = pygame.time.Clock()
    
    DASHBOARD_FONT = pygame.font.SysFont("monospace", 14)

    # ── LSL Connection ────────────────────────
    inlet = None
    if LSL_AVAILABLE:
        print("Searching for LSL stream (type='EEG')...", flush=True)
        try:
            streams = resolve_byprop('type', 'EEG', timeout=5)
            if streams:
                inlet = StreamInlet(streams[0])
                print("✅ Connected to LSL stream!", flush=True)
            else:
                print("⚠️ No EEG stream found. Running in default mode.", flush=True)
        except Exception as e:
            print(f"⚠️ LSL error: {e}. Running in default mode.", flush=True)

    boids = [Boid() for _ in range(NUM_BOIDS)]

    # ── Signal Smoothing ──
    # Buffer last 1 second of data (~256 samples) for stable averaging
    signal_buffer = collections.deque(maxlen=256)
    
    # Default metrics to start (until buffer full)
    current_metrics = {
        "state": "RELAXED",
        "alpha_power": 0.0,
        "beta_power": 0.0,
        "ratio": 0.0
    }

    running = True
    while running:
        # ── Events ──
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        # ── LSL Update ──
        if inlet:
            # Drain ALL buffered samples this frame
            while True:
                sample, timestamp = inlet.pull_sample(timeout=0.0)
                if sample is None:
                    break
                signal_buffer.append(sample[0]) # Store raw value, FFT handles amplitude

            # Compute FFT state only when buffer is FULL
            if len(signal_buffer) == 256:
                metrics = get_brain_state(signal_buffer)
                
                if metrics:
                    # Update State if changed
                    if metrics["state"] != current_metrics["state"]:
                        print(f"🧠 State → {metrics['state']} (Ratio={metrics['ratio']:.2f})", flush=True)
                    
                    current_metrics = metrics

                if current_metrics["state"] == "STRESSED":
                    # EXPLODE!
                    BOID_COLOR = (255, 0, 0)      # Red
                    SEPARATION_WEIGHT = 10.0      # Extreme repulsion
                    ALIGNMENT_WEIGHT = 0.2        # Chaos
                    COHESION_WEIGHT = -2.0         # Repel from center
                    MAX_SPEED = 10.0              # Very fast
                    MAX_FORCE = 0.5               # Strong steering
                else:
                    # Group up
                    BOID_COLOR = (0, 255, 255)    # Cyan
                    SEPARATION_WEIGHT = 1.0       # Normal
                    ALIGNMENT_WEIGHT = 1.0        # Organized
                    COHESION_WEIGHT = 1.0         # Cohesive
                    MAX_SPEED = 4.0               # Calm
                    MAX_FORCE = 0.1               # Gentle steering

        # ── Boids Update ──
        for boid in boids:
            boid.flock(boids)

        for boid in boids:
            boid.update()
            boid.edges()

        # ── Draw ──
        screen.fill(BG_COLOR)
        for boid in boids:
            boid.draw(screen)
        
        # Draw Dashboard Overlay
        draw_dashboard(screen, signal_buffer, current_metrics)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()

