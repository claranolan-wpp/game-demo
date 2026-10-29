import pygame
import random
import random
import numpy as np

pygame.init()

# Create a resizable window.
screen = pygame.display.set_mode(
    (1280, 720),
    pygame.RESIZABLE
)
pygame.display.set_caption("River Generator")

clock = pygame.time.Clock()
running = True
dt = 0

blockSize = 40

# Initialize dimensions from the actual window.
width, height = screen.get_size()
cols = width // blockSize
rows = height // blockSize

def create_grid(cols, rows):
    return [[0 for _ in range(rows)] for _ in range(cols)]

grid = create_grid(cols, rows)

player_pos = pygame.Vector2(width / 2, height / 2)


def update_dimensions():
    global width, height, cols, rows, grid

    width, height = screen.get_size()

    new_cols = width // blockSize
    new_rows = height // blockSize

    # Only rebuild the grid if the number of cells changes.
    if new_cols != cols or new_rows != rows:
        old_grid = grid
        old_cols = cols
        old_rows = rows

        cols = new_cols
        rows = new_rows
        grid = create_grid(cols, rows)

        # Preserve existing cells that still fit.
        for x in range(min(old_cols, cols)):
            for y in range(min(old_rows, rows)):
                grid[x][y] = old_grid[x][y]


def draw_grid():
    screen.fill("brown")
    for x in range(cols):
        for y in range(rows):
            rect = pygame.Rect(
                x * blockSize,
                y * blockSize,
                blockSize,
                blockSize
            )
        
            if grid[x][y] == 2:
                pygame.draw.rect(screen, "green", rect)
            if grid[x][y] == 1:
                pygame.draw.rect(screen, "blue", rect)

            pygame.draw.rect(screen, "black", rect, 1)


def draw_map(grid):
    cols = len(grid)
    rows = len(grid[0])
    grass = np.random.choice(['grass', 'dirt'], p=[1 / 3, 2 / 3])
    
    for x in range(3):
        start_pts = random.choice([
                (0, 0), #top left
                (0, rows - 1), #bottom left
                (cols - 1, 0), #top right
                (cols - 1, rows - 1), #bottom right
                (cols // 2, 0), #top center
            ])
        x, y = start_pts
        grid[x][y] = 1

        while y < rows - 1:
            direction = random.choice([
                (0, 1),
                (0, 1),
                (0, 1),
                (-1, 0),
                (1, 0),
            ])

            dx, dy = direction
            next_x = x + dx
            next_y = y + dy

            if 0 <= next_x < cols and 0 <= next_y < rows:
                x, y = next_x, next_y
                grid[x][y] = 1
            elif grass == 'grass':
                break  # Stop if we hit the edge and the terrain is grass


while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.VIDEORESIZE:
            # Update the display surface and grid dimensions.
            screen = pygame.display.set_mode(
                (event.w, event.h),
                pygame.RESIZABLE
            )
            update_dimensions()

        elif event.type == pygame.MOUSEBUTTONDOWN:
            mouse_x, mouse_y = event.pos

            if 0 <= mouse_x < width and 0 <= mouse_y < height:
                col = mouse_x // blockSize
                row = mouse_y // blockSize

                if col < cols and row < rows:
                    grid[col][row] = 1

    draw_grid()

    # Keep the player inside the visible window.
    player_pos.x = max(20, min(player_pos.x, width - 20))
    player_pos.y = max(20, min(player_pos.y, height - 20))

    pygame.draw.circle(screen, "red", player_pos, 20)

    keys = pygame.key.get_pressed()

    if keys[pygame.K_w]:
        player_pos.y -= 300 * dt
    if keys[pygame.K_s]:
        player_pos.y += 300 * dt
    if keys[pygame.K_a]:
        player_pos.x -= 300 * dt
    if keys[pygame.K_d]:
        player_pos.x += 300 * dt

    pygame.display.flip()
    dt = clock.tick(60) / 1000

pygame.quit()