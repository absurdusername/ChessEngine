"""
Main driver script. Handles user I/O and displays the current GameState object.
"""
import sys
import pygame
from Chess import ChessEngine

WIDTH = HEIGHT = 512
SQ_SIZE = HEIGHT // 8
MAX_FPS = 15
IMAGES = {}  # piece name to piece image


def load_images():
    """Initialize the global directory of images. Called exactly once."""
    pieces = ['wp', 'wR', 'wN', 'wB', 'wQ', 'wK',
              'bp', 'bR', 'bN', 'bB', 'bQ', 'bK']

    for piece in pieces:
        IMAGES[piece] = pygame.transform.scale(pygame.image.load('images/' + piece + '.png'), (SQ_SIZE, SQ_SIZE))


def main():
    """Main function, handles user input and updates the graphics."""
    load_images()
    gs = ChessEngine.GameState()

    pygame.init()

    screen = pygame.display.set_mode((WIDTH, HEIGHT))  # create a window of WIDTH x HEIGHT
    pygame.display.set_caption('Chess')
    screen.fill('white')

    clock = pygame.time.Clock()

    while True:
        # poll for events
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        draw_game_state(screen, gs)

        clock.tick(MAX_FPS)
        pygame.display.update()


def draw_game_state(screen, gs):
    """Render the current game state."""
    draw_board(screen)  # draw squares
    draw_pieces(screen, gs.board)  # draw pieces on those squares


def draw_board(screen):
    """Draw the 8x8 chess board."""
    colors = [pygame.Color('white'), pygame.Color('dark grey')]

    for r in range(8):
        for c in range(8):
            color = colors[(r + c) % 2]
            pygame.draw.rect(screen, color, pygame.Rect(c * SQ_SIZE, r * SQ_SIZE, SQ_SIZE, SQ_SIZE))


def draw_pieces(screen, board):
    """Draw the pieces on the squares using the current GameState.board object."""
    for r in range(8):
        for c in range(8):
            piece = board[r][c]
            if piece != '--':
                screen.blit(IMAGES[piece], (c * SQ_SIZE, r * SQ_SIZE))


if __name__ == '__main__':
    main()
