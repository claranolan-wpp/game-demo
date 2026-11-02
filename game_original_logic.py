from dataclasses import dataclass
from pandas import io
import pygame
import pandas as pd
from noise import pnoise2
import random
import numpy as np
import io
import requests
import json
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from IPython.display import Audio
import base64

# ---------------------------Audio Setup ---------------------------

# Load credentials from your service account file
creds = service_account.Credentials.from_service_account_file(
    "keys/service.json",
    scopes=["https://www.googleapis.com/auth/cloud-platform"],
)

# Fetch an access token (this is what gcloud auth print-access-token returns)
creds.refresh(Request())
token = creds.token

with open('keys/keys.json', 'r') as f:
    keys = json.load(f)

def get_audio(input):

    url = "https://aiplatform.googleapis.com/v1beta1/projects/wpp-cto-smartprod-sandbox/locations/global/interactions"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
   
    payload = {
      "model": "lyria-3-clip-preview",
      "input": [
        {
          "type": "text",
          "text": f"{input}"
        }
      ]
    }
   

    response = requests.post(url, headers=headers, json=payload)
    # print(response)
    # print(response.text)
    # print(response.status_code)
    # print(response.headers)
    data = response.json()
    return data["outputs"][2]["data"]
    print(data["outputs"][2]["data"])

clip = get_audio("catchy jingle talking about adding more animals to the ecosystem simulation game, with a fun and playful tone, and a memorable melody.")

mp3_bytes = base64.b64decode(clip)
Audio(mp3_bytes)
sound_file = io.BytesIO(mp3_bytes)



# ---------------------------Start Game Setup ---------------------------
pygame.init()
pygame.mixer.init()
sound = pygame.mixer.Sound(sound_file)

# Window setup
screen = pygame.display.set_mode((1280, 720), pygame.RESIZABLE)
pygame.display.set_caption("Ecosytem Simulation")

clock = pygame.time.Clock()
running = True
dt = 0

#Core Variables
BLOCK_SIZE = 25 # how big grid cells are in pixels
WINDOW_SIZE = (1280, 720)
FPS = 60
TPS = 2.0 # ticks per second to be used for simulation updates
tick_accumulator = 0.0 # used to track time for simulation updates
paused = False 


# Terrain Variables
NOISE_SCALE = 0.075
OCTAVES = 5
GRASS_THRESHOLD = 0.53

# Cell Types
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
BUNNY_COLOR = (245, 235, 205) # used for debugging, but sprites are used for rendering animals

GRID_COLOR = (40, 40, 40)

width, height = screen.get_size()
cols = width // BLOCK_SIZE
rows = height // BLOCK_SIZE

# ---------------------------Animal Setup ---------------------------
coyote_sprite = pygame.image.load("coyote.png").convert_alpha()
bunny_sprite = pygame.image.load("bunny.png").convert_alpha()

# Resize sprites to fit the grid
SPRITE_SIZE = (BLOCK_SIZE-1, BLOCK_SIZE-1)  # how big grid cells are in pixels

COYOTE_IMAGE = pygame.transform.smoothscale(
    coyote_sprite, SPRITE_SIZE
)

BUNNY_IMAGE = pygame.transform.smoothscale(
    bunny_sprite, SPRITE_SIZE
)

# Match species names to their sprites
ANIMAL_IMAGES = {
    "coyote": COYOTE_IMAGE,
    "bunny": BUNNY_IMAGE
}

# Load in animal data from CSV
animal_df = pd.read_csv("animal_data.csv")
print("Loaded", len(animal_df), "animals!")
animal_df.head(5)

COYOTE_DATA = animal_df[animal_df["species_id"] == "coyote"]
BUNNY_DATA = animal_df[animal_df["species_id"].isin(["eastern_cottontail", "snowshoe_hare", "black_tailed_jackrabbit"])]

@dataclass
class Animal:
    species: str
    x: int
    y: int
    age: int = 0
    health: float = 100.0
    hunger: float = 0.0
    alive: bool = True
    reproduction_rate: float = 0.0 # from csv
    mortality_rate: float = 0.0 # from csv

    @property
    def color(self):
        return COYOTE_COLOR if self.species == "coyote" else BUNNY_COLOR

    def move_animal(self, grid):
        grid_cols = len(grid)
        grid_rows = len(grid[0])

        # define possible movement steps (including diagonals)
        steps = [
            (0, 0), (1, 0), (-1, 0),
            (0, 1), (0, -1),
            (1, 1), (-1, 1),
            (1, -1), (-1, -1)
        ]

        random.shuffle(steps)

        for dx, dy in steps:
            # calculate new position and ensure it's within grid bounds
            nx = max(0, min(grid_cols - 1, self.x + dx))
            ny = max(0, min(grid_rows - 1, self.y + dy))
            # animals cant move into river cells
            if grid[nx][ny] != RIVER:
                self.x, self.y = nx, ny
            return
        
    def update(self, grid, animals):
        if not self.alive:
            return

        self.move_animal(grid)
        self.age += 1
        self.hunger += 0.001

        if self.species == "bunny":
            if grid[self.x][self.y] == GRASS:
                self.hunger = max(0, self.hunger - 0.2)
                self.health = min(100, self.health + 0.15)

        elif self.species == "coyote":
            prey = [
                animal for animal in animals
                if animal.alive
                and animal.species == "bunny"
                # if bunny is close enough to the coyote, it can be eaten
                and abs(animal.x - self.x) <= 1
                and abs(animal.y - self.y) <= 1
            ]

            if prey:
                target = random.choice(prey)
                target.alive = False
                self.hunger = max(0, self.hunger - 0.5)
                self.health = min(100, self.health + 2)

        # Defining death cases
        # Hunger damages health
        if self.hunger > 1:
            self.health -= self.hunger * 0.5

        # Disease event
        if random.random() < 0.004:
            self.health -= random.uniform(10, 30)

        # Old age
        max_age = 150 if self.species == "bunny" else 250

        if self.age > max_age:
            self.health -= 2

        # Natural mortality rate check
        if random.random() < self.mortality_rate:
            self.alive = False

        if self.health <= 0:
            self.alive = False

# Used to store all animals in the simulation
animals = []

def spawn_animals(species, count, reproduction_rate, mortality_rate):
    for cell in range(count):
        x = random.randrange(cols)
        y = random.randrange(rows)

        while grid[x][y] == RIVER:
            x = random.randrange(cols)
            y = random.randrange(rows)

        animals.append(
            Animal(
                species=species,
                x=x,
                y=y,
                reproduction_rate=reproduction_rate,
                mortality_rate=mortality_rate
            )
        )


def update_ecosystem(grid):
    # Update all animals in the ecosystem
    for animal in animals[:]:
        animal.update(grid, animals)
    # Remove dead animals from the list
    animals[:] = [
        animal for animal in animals
        if animal.alive
    ]

def draw_animals():
    for animal in animals:

        # Get the correct sprite for this species
        animal_image = ANIMAL_IMAGES.get(animal.species)

        # Calculate pixel position from grid coordinates
        px = animal.x * BLOCK_SIZE + BLOCK_SIZE // 2
        py = animal.y * BLOCK_SIZE + BLOCK_SIZE // 2

        # Center the image on the animal's grid cell
        image_rect = animal_image.get_rect(
            center=(px, py)
        )

        screen.blit(animal_image, image_rect)
# ---------------------------UI Setup ---------------------------
# UI Setup
TEXT_COLOR = (245, 245, 245)
PANEL_COLOR = (25, 28, 32)

UI_FONT = pygame.font.SysFont("Papyrus", 20, bold=True)
HUD_FONT = pygame.font.SysFont("Papyrus", 22, bold=True)

BUTTON_WIDTH = 165
BUTTON_HEIGHT = 36

BUNNY_BUTTON = pygame.Rect(10, 10, BUTTON_WIDTH, BUTTON_HEIGHT)
COYOTE_BUTTON = pygame.Rect(10, 54, BUTTON_WIDTH, BUTTON_HEIGHT)

ADD_ANIMAL_COUNT = 5

BUNNY_BUTTON_COLOR = BUNNY_COLOR
COYOTE_BUTTON_COLOR = COYOTE_COLOR

def draw_ui():
  # Black panel in the top-right corner
    panel_width = 650
    panel_height = 75
    panel_x = screen.get_width() - panel_width - 10
    panel_y = 5

    panel = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
    panel.fill((25, 28, 32, 220))
    screen.blit(panel, (panel_x, panel_y))

    # Direction text
    instructions = [
        "To play: Click the buttons to add animals and keep populations above zero.",
        "R to regenerate. "
        "Left-click to add water. "
        "Right-click to add grass."
    ]

    # Use this for line wrapping if needed, but for now we will just render each line separately
    for i, line in enumerate(instructions):
        direction_text = UI_FONT.render(line, True, (255, 255, 255))
        screen.blit(direction_text, (panel_x + 10, panel_y + 10 + i * 25))

    # Draw buttons
    pygame.draw.rect(
        screen, BUNNY_BUTTON_COLOR, BUNNY_BUTTON, border_radius=7
    )
    pygame.draw.rect(
        screen, COYOTE_BUTTON_COLOR, COYOTE_BUTTON, border_radius=7
    )

    bunny_button_text = UI_FONT.render(
        "+ Add 5 Bunnies", True, (255, 255, 255)
    )
    coyote_button_text = UI_FONT.render(
        "+ Add 5 Coyotes", True, (255, 255, 255)
    )

    # Count current populations
    bunny_count = sum(
        1 for animal in animals
        if animal.species == "bunny" and animal.alive
    )

    coyote_count = sum(
        1 for animal in animals
        if animal.species == "coyote" and animal.alive
    )

    # Population counters
    bunny_population = HUD_FONT.render(
        f"Bunnies: {bunny_count}", True, (190, 255, 190)
    )

    coyote_population = HUD_FONT.render(
        f"Coyotes: {coyote_count}", True, (255, 190, 145)
    )

    # Draw buttons and population counters below instructions
    screen.blit(bunny_button_text, (BUNNY_BUTTON.x + 10, BUNNY_BUTTON.y + 10))
    screen.blit(coyote_button_text, (COYOTE_BUTTON.x + 10, COYOTE_BUTTON.y + 10))

    screen.blit(bunny_population, (195, 20))
    screen.blit(coyote_population, (195, 64))

player_pos = pygame.Vector2(width / 2, height / 2)

# ---------------------------Grid/Map Setup ---------------------------

def create_grid(cols, rows):
    return [[DIRT for row in range(rows)] for col in range(cols)]


grid = create_grid(cols, rows)
elevation_map = np.zeros((cols, rows), dtype=float)


def generate_elevation(cols, rows, seed=None):
   
    if seed is None:
        seed = random.randint(0, 123445565)

    #tabula rasa
    elevation = np.zeros((cols, rows), dtype=float)

    for x in range(cols):
        for y in range(rows):
            noise_value = pnoise2(
                x * NOISE_SCALE,
                y * NOISE_SCALE,
                octaves=OCTAVES, # structure detail
                persistence=0.5,
                lacunarity=2.0, # for water formations
                base=seed,
            )

            # convert noise to an approximate 0-1 elevation
            elevation[x, y] = np.clip(
                (noise_value + 1.0) / 2.0,
                0.0,
                1.0,
            )

    return elevation


def generate_terrain(grid, elevation):
    #Fill the grid based on elevation thresholds

    cols = len(grid)
    rows = len(grid[0])

    for x in range(cols):
        for y in range(rows):
            if elevation[x, y] >= GRASS_THRESHOLD:
                grid[x][y] = GRASS
            else:
                grid[x][y] = DIRT


def generate_river(grid, start_x=None):
  #Use drunken walk to carve a river from the top edge to the bottom edge of the grid
    # reference: https://www.redblobgames.com/articles/drunken-walks/
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

        # Optional widening: occasionally add a neighboring river cell
        if random.random() < 0.15:
            side = random.choice([-1, 1])
            wide_x = x + side

            if 0 <= wide_x < cols:
                grid[wide_x][y] = RIVER

        # Stop once the river reaches the bottom edge
        if y == rows - 1:
            break

        # Favor valid downward and sideways moves 
        candidates = [
            (x + dx, y + dy, weight)
            for dx, dy, weight in moves
            if 0 <= x + dx < cols
            and 0 <= y + dy < rows
        ]

        if not candidates:
            break

        # Filter out already visited cells to avoid loops
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
   #Build map with rivers and terrain based on Perlin noise elevation
    grid = create_grid(cols, rows)
    elevation = generate_elevation(cols, rows)

    generate_terrain(grid, elevation)

    # Start rivers at different positions along the top edge
    # River cells overwrite grass and dirt
    starts = []

    for _ in range(river_count):
        if cols <= 0:
            break

        start_x = random.randrange(cols)
        generate_river(grid, start_x)

    return grid, elevation

# Used for screen resizing and regenerating the map when the window size changes
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
else:
    grid = create_grid(cols, rows)
    elevation_map = np.zeros((cols, rows), dtype=float)

coyote_row = COYOTE_DATA.iloc[0]
bunny_row = BUNNY_DATA.sample(n=1).iloc[0] # there is 3 rows in bunny data, so we randomly select one of them for initial population

spawn_animals(
    "coyote",
    int(coyote_row["initial_population"]),
    float(coyote_row["reproduction_rate_per_tick"]),
    float(coyote_row["natural_mortality_per_tick"])
)

spawn_animals(
    "bunny",
    int(bunny_row["initial_population"]),
    float(bunny_row["reproduction_rate_per_tick"]),
    float(bunny_row["natural_mortality_per_tick"])
)

# ---------------------------Main Gameloop ---------------------------

while running:

    dt = clock.tick(FPS) / 1000.0

    for event in pygame.event.get():

        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.VIDEORESIZE:
            screen = pygame.display.set_mode(
                (event.w, event.h),
                pygame.RESIZABLE
            )

            update_dimensions()

        elif event.type == pygame.KEYDOWN:

            if event.key == pygame.K_SPACE:
                paused = not paused

            elif event.key == pygame.K_r:
                if cols > 0 and rows > 0:
                    grid, elevation_map = generate_map(cols, rows)

                    # Move animals out of river cells after regeneration
                    for animal in animals:
                        if grid[animal.x][animal.y] == RIVER:
                            land_cells = [
                                (x, y)
                                for x in range(cols)
                                for y in range(rows)
                                if grid[x][y] != RIVER
                            ]

                            if land_cells:
                                animal.x, animal.y = random.choice(land_cells)

        elif event.type == pygame.MOUSEBUTTONDOWN:

            mouse_x, mouse_y = event.pos

            # Add bunnies
            if event.button == 1 and BUNNY_BUTTON.collidepoint(event.pos):
                spawn_animals(
                    "bunny",
                    ADD_ANIMAL_COUNT,
                    float(bunny_row["reproduction_rate_per_tick"]),
                    float(bunny_row["natural_mortality_per_tick"])
                )
                sound.play()

            # Add coyotes
            elif event.button == 1 and COYOTE_BUTTON.collidepoint(event.pos):
                spawn_animals(
                    "coyote",
                    ADD_ANIMAL_COUNT,
                    float(coyote_row["reproduction_rate_per_tick"]),
                    float(coyote_row["natural_mortality_per_tick"])
                )
                sound.play()

            # Handle painting terrain on the grid

            if 0 <= mouse_x < width and 0 <= mouse_y < height:
                col = mouse_x // BLOCK_SIZE
                row = mouse_y // BLOCK_SIZE

                if col < cols and row < rows:

                    # Left click paints river
                    if event.button == 1:
                        grid[col][row] = RIVER

                    # Right click paints grass
                    elif event.button == 3:
                        grid[col][row] = GRASS

    # Update simulation at TPS, independently of rendering
    if not paused:
        tick_accumulator += dt
        interval = 1.0 / TPS

        while tick_accumulator >= interval:
            update_ecosystem(grid)
            tick_accumulator -= interval

    # Render every frame
    draw_grid()
    draw_animals()
    draw_ui()

    pygame.display.flip()

pygame.quit()