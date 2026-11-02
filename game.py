from dataclasses import dataclass
import pygame
import pandas as pd
from noise import pnoise2
import random
import numpy as np

pygame.init()

# Window setup
screen = pygame.display.set_mode((1280, 720), pygame.RESIZABLE)
pygame.display.set_caption("Ecosytem Simulation")

clock = pygame.time.Clock()
running = True
dt = 0

#Core Variables
BLOCK_SIZE = 25
WINDOW_SIZE = (1280, 720)
FPS = 60
TPS = 2.0 #ticks per second


# Terrain Variables
NOISE_SCALE = 0.075
OCTAVES = 5
GRASS_THRESHOLD = 0.53

# Cell types
DIRT = 0
RIVER = 1
GRASS = 2

# Colors
COLORS = {
    DIRT: (125, 82, 48),
    RIVER: (45, 130, 210),
    GRASS: (65, 160, 65),
    
}

COYOTE_COLOR = (225, 105, 45)
BUNNY_COLOR = (245, 235, 205)
TEXT_COLOR = (245, 245, 245)
PANEL_COLOR = (25, 28, 32)

GRID_COLOR = (40, 40, 40)

width, height = screen.get_size()
cols = width // BLOCK_SIZE
rows = height // BLOCK_SIZE

# ---------------------------Animal Setup ---------------------------


# Load in animal data from CSV
animal_df = pd.read_csv("animal_data.csv")
print("Loaded", len(animal_df), "animals!")
animal_df.head(5)

COYOTE_DATA = animal_df[animal_df["species_id"] == "coyote"]
BUNNY_DATA = animal_df[animal_df["species_id"].isin(["eastern_cottontail", "snowshoe_hare", "black_tailed_jackrabbit"])]

class Animal:
    species: str
    x: int
    y: int
    age: int
    health: float
    hunger: float = 0.0
    alive: bool = True
    reproduction_rate: float
    mortality_rate: float
    
    @property
    def color(self):
        return COYOTE_COLOR if self.species == "coyote" else BUNNY_COLOR

    
    def __init__(self, name):
        self.name = name

    def info(self):
        print("Animal name:", self.name)

    def move_animal(animal, grid):
        # Short random movement; rivers are impassable to land animals.
        steps = [(0, 0), (1, 0), (-1, 0), (0, 1), (0, -1),
                (1, 1), (-1, 1), (1, -1), (-1, -1)]
        random.shuffle(steps)
        for dx, dy in steps:
            nx = max(0, min(cols - 1, animal.x + dx))
            ny = max(0, min(rows - 1, animal.y + dy))
            if grid[nx][ny] != RIVER:
                animal.x, animal.y = nx, ny
                return
    
    def find_food(animal):
        # For simplicity, assume bunnies eat grass and coyotes eat bunnies.
        if animal.species == "coyote":
            candidates = [bunny for bunny in bunnies if bunny.alive and abs(bunny.x - animal.x) <= 1 and abs(bunny.y - animal.y) <= 1]
        else:  # bunny
            candidates = [(animal.x + dx, animal.y + dy) for dx in range(-1, 2) for dy in range(-1, 2)
                          if 0 <= animal.x + dx < cols and 0 <= animal.y + dy < rows and grid[animal.x + dx][animal.y + dy] == GRASS]
        return random.choice(candidates) if candidates else None

    def update_animal(animal, grid):
        if not animal.alive:
            return

        # Move the animal
        Animal.move_animal(animal, grid)

        # Find food
        food = Animal.find_food(animal)
        if food:
            if animal.species == "coyote":
                # If a coyote finds a bunny, it eats it.
                for bunny in bunnies:
                    if bunny.x == food.x and bunny.y == food.y and bunny.alive:
                        bunny.alive = False
                        animal.hunger = max(0, animal.hunger - 0.5)  # Reduce hunger
                        break
            else:  # bunny
                # If a bunny finds grass, it eats it.
                animal.hunger = max(0, animal.hunger - 0.3)  # Reduce hunger

        # Increase hunger over time
        animal.hunger += 0.01

        # Check mortality based on hunger and age
        if animal.hunger > 1.0 or random.random() < animal.mortality_rate:
            animal.alive = False



player_pos = pygame.Vector2(width / 2, height / 2)


def create_grid(cols, rows):
    return [[DIRT for _ in range(rows)] for _ in range(cols)]


grid = create_grid(cols, rows)
elevation_map = np.zeros((cols, rows), dtype=float)


def generate_elevation(cols, rows, seed=None):
   
    if seed is None:
        seed = random.randint(0, 100000)

    elevation = np.zeros((cols, rows), dtype=float)

    for x in range(cols):
        for y in range(rows):
            noise_value = pnoise2(
                x * NOISE_SCALE,
                y * NOISE_SCALE,
                octaves=OCTAVES,
                persistence=0.5,
                lacunarity=2.0,
                base=seed,
            )

            # Convert noise to an approximate 0-1 elevation.
            elevation[x, y] = np.clip(
                (noise_value + 1.0) / 2.0,
                0.0,
                1.0,
            )

    return elevation


def generate_terrain(grid, elevation):
    #Fill the grid based on elevation thresholds.

    cols = len(grid)
    rows = len(grid[0])

    for x in range(cols):
        for y in range(rows):
            if elevation[x, y] >= GRASS_THRESHOLD:
                grid[x][y] = GRASS
            else:
                grid[x][y] = DIRT


def generate_river(grid, start_x=None):
  #Use drunken walk to carve a river from the top edge to the bottom edge of the grid.

    cols = len(grid)
    rows = len(grid[0])

    if cols == 0 or rows == 0:
        return

    if start_x is None:
        x = random.randrange(cols)
    else:
        x = max(0, min(start_x, cols - 1))

    y = 0
    visited = set()

    # Weighted movement options:
    # Down is most likely; sideways movement creates meanders.
    moves = [
        (0, 1, 6.0),
        (-1, 1, 1.5),
        (1, 1, 1.5),
        (-1, 0, 1.0),
        (1, 0, 1.0),
    ]

    max_steps = cols * rows * 3

    for _ in range(max_steps):
        if not (0 <= x < cols and 0 <= y < rows):
            break

        grid[x][y] = RIVER
        visited.add((x, y))

        # Optional widening: occasionally add a neighboring river cell.
        if random.random() < 0.15:
            side = random.choice([-1, 1])
            wide_x = x + side

            if 0 <= wide_x < cols:
                grid[wide_x][y] = RIVER

        # Stop once the river reaches the bottom edge.
        if y == rows - 1:
            break

        # Favor valid downward and sideways moves.
        candidates = [
            (x + dx, y + dy, weight)
            for dx, dy, weight in moves
            if 0 <= x + dx < cols
            and 0 <= y + dy < rows
        ]

        if not candidates:
            break

        # Prefer unexplored cells to reduce looping.
        fresh = [
            candidate
            for candidate in candidates
            if (candidate[0], candidate[1]) not in visited
        ]

        if fresh:
            candidates = fresh

        positions = [(cx, cy) for cx, cy, _ in candidates]
        weights = [weight for _, _, weight in candidates]

        x, y = random.choices(
            positions,
            weights=weights,
            k=1,
        )[0]


def generate_map(cols, rows, river_count=2):
   #Build map with rivers and terrain based on Perlin noise elevation.
    grid = create_grid(cols, rows)
    elevation = generate_elevation(cols, rows)

    generate_terrain(grid, elevation)

    # Start rivers at different positions along the top edge.
    # River cells overwrite grass and dirt.
    starts = []

    for _ in range(river_count):
        if cols <= 0:
            break

        start_x = random.randrange(cols)
        generate_river(grid, start_x)

    return grid, elevation


def update_dimensions():
    global width, height, cols, rows, grid, elevation_map

    width, height = screen.get_size()

    new_cols = width // BLOCK_SIZE
    new_rows = height // BLOCK_SIZE

    if new_cols != cols or new_rows != rows:
        cols = new_cols
        rows = new_rows

        if cols > 0 and rows > 0:
            grid, elevation_map = generate_map(cols, rows)
        else:
            grid = create_grid(cols, rows)
            elevation_map = np.zeros((cols, rows), dtype=float)


def draw_grid():
    screen.fill(COLORS[DIRT])

    for x in range(cols):
        for y in range(rows):
            rect = pygame.Rect(
                x * BLOCK_SIZE,
                y * BLOCK_SIZE,
                BLOCK_SIZE,
                BLOCK_SIZE,
            )

            cell_type = grid[x][y]
            pygame.draw.rect(screen, COLORS[cell_type], rect)

            # Cell outlines
            pygame.draw.rect(screen, GRID_COLOR, rect, 1)


# Generate the initial world.
if cols > 0 and rows > 0:
    grid, elevation_map = generate_map(cols, rows)


while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.VIDEORESIZE:
            screen = pygame.display.set_mode(
                (event.w, event.h),
                pygame.RESIZABLE,
            )
            update_dimensions()

        elif event.type == pygame.MOUSEBUTTONDOWN:
            mouse_x, mouse_y = event.pos

            if 0 <= mouse_x < width and 0 <= mouse_y < height:
                col = mouse_x // BLOCK_SIZE
                row = mouse_y // BLOCK_SIZE

                if col < cols and row < rows:
                    # Left click paints river.
                    if event.button == 1:
                        grid[col][row] = RIVER

                    # Right click paints grass.
                    elif event.button == 3:
                        grid[col][row] = GRASS

        elif event.type == pygame.KEYDOWN:
            # Press R to regenerate the world.
            if event.key == pygame.K_r:
                if cols > 0 and rows > 0:
                    grid, elevation_map = generate_map(cols, rows)

    draw_grid()

    # Keep player inside the window.
    player_pos.x = max(20, min(player_pos.x, width - 20))
    player_pos.y = max(20, min(player_pos.y, height - 20))

    # Player movement
    keys = pygame.key.get_pressed()

    if keys[pygame.K_w]:
        player_pos.y -= 300 * dt
    if keys[pygame.K_s]:
        player_pos.y += 300 * dt
    if keys[pygame.K_a]:
        player_pos.x -= 300 * dt
    if keys[pygame.K_d]:
        player_pos.x += 300 * dt

    pygame.draw.circle(
        screen,
        (220, 45, 45),
        (int(player_pos.x), int(player_pos.y)),
        20,
    )

    pygame.display.flip()
    dt = clock.tick(60) / 1000

pygame.quit()
