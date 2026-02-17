"""
NeuroSwarmBird — Real-time Boids Flocking Simulation
=====================================================
Implements Craig Reynolds' Boids algorithm with three steering rules:
separation, alignment, and cohesion.  Uses pygame for rendering.
Integrates LSL (Lab Streaming Layer) for real-time EEG control.
"""

import math
import random
import pygame
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
        self.velocity += self.acceleration
        if self.velocity.length() > MAX_SPEED:
            self.velocity.scale_to_length(MAX_SPEED)
        self.position += self.velocity
        self.acceleration = Vector2(0, 0)

    def edges(self):
        """Toroidal wrap — boid reappears on the opposite side."""
        if self.position.x > WIDTH:
            self.position.x = 0
        elif self.position.x < 0:
            self.position.x = WIDTH
        if self.position.y > HEIGHT:
            self.position.y = 0
        elif self.position.y < 0:
            self.position.y = HEIGHT

    def draw(self, screen):
        """Render the boid as a small triangle pointing in the direction of travel."""
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

    import collections  # Local import for buffer

    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("NeuroSwarmBird — Boids Flocking Simulation (LSL Enabled)")
    clock = pygame.time.Clock()

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
    current_state = "RELAXED"

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
                signal_buffer.append(abs(sample[0]))

            # Compute moving average if we have data
            if len(signal_buffer) > 0:
                avg_val = sum(signal_buffer) / len(signal_buffer)

                # Hysteresis Thresholding (Prevents edge flickering)
                # > 0.9  => Trigger STRESSED (since mean moves from ~0.6 to 1.0)
                # < 0.8  => Trigger RELAXED
                if current_state == "RELAXED" and avg_val > 0.9:
                    current_state = "STRESSED"
                    print(f"🧠 State → STRESSED (avg={avg_val:.2f})", flush=True)
                elif current_state == "STRESSED" and avg_val < 0.8:
                    current_state = "RELAXED"
                    print(f"🧠 State → RELAXED  (avg={avg_val:.2f})", flush=True)

                if current_state == "STRESSED":
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

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()

