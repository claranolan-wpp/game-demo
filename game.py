# Example file showing a circle moving on screen
import pygame

# pygame setup
pygame.init()
screen = pygame.display.set_mode((1280, 720))
clock = pygame.time.Clock()
running = True
dt = 0

player_pos = pygame.Vector2(screen.get_width() / 2, screen.get_height() / 2)

# def draw_grid():
#     blockSize = 20  # Set the size of the grid block
#     for x in range(0, screen.get_width(), blockSize):
#         for y in range(0, screen.get_height(), blockSize):
#             rect = pygame.Rect(x, y, blockSize, blockSize)
#             pygame.draw.rect(screen, "black", rect, 1)

def draw_grid():
    width = screen.get_width()
    height = screen.get_height()
    grid = [[None for _ in range(height)] for _ in range(width)]

    blockSize = 20  # Set the size of the grid block
    for x in range(0, width, blockSize):
        for y in range(0, height, blockSize):
            grid[x][y] = pygame.Rect(x, y, blockSize, blockSize)
            pygame.draw.rect(screen, "black", grid[x][y], 1)
    return grid


while running:

    # poll for events
    # pygame.QUIT event means the user clicked X to close your window
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # fill the screen with a color to wipe away anything from last frame
    screen.fill("purple")

    grid = draw_grid()
    print(grid)
    pygame.draw.circle(screen, "red", player_pos, 40)

    keys = pygame.key.get_pressed()
    if keys[pygame.K_w]:
        player_pos.y -= 300 * dt
    if keys[pygame.K_s]:
        player_pos.y += 300 * dt
    if keys[pygame.K_a]:
        player_pos.x -= 300 * dt
    if keys[pygame.K_d]:
        player_pos.x += 300 * dt

    # flip() the display to put your work on screen
    pygame.display.flip()

    # limits FPS to 60
    # dt is delta time in seconds since last frame, used for framerate-
    # independent physics.
    dt = clock.tick(60) / 1000
