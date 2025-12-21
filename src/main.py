# Make it work then make it better
# Code first, refactor second

import bulletchess
import sys

from bulletchess import Board, Move
from search import find_best_move


def io_loop():
    while True:
        command = input()
        execute(command)


def execute(command: str):
    match command.split():
        case ["uci"]:
            print("id name DumbChessEngine")
            print("id author lazy")
            print("uciok")

        case ["isready"]:
            print("readyok")

        case ["ucinewgame"]:
            # TO-DO: reset state for a new game
            pass

        case ["position", *args]:
            # position [fen <fenstring> | startpos ] moves <move1> .... <movei>
            arrange_board(command)

        case ["go", *args]:
            start_search(command)

        case ["quit"]:
            sys.exit(0)

        case ["stop"]:
            # TO-DO: stop the search ASAP and print the bestmove
            pass


def arrange_board(command: str):
    tokens = command.split()

    global board
    if tokens[1] == "startpos":
        board = Board()
    else:
        fen = " ".join(tokens[2:8])
        board = Board.from_fen(fen)

    if "moves" in tokens:
        i = tokens.index("moves")
        moves_list = tokens[i+1:]

        for move in moves_list:
            board.apply(Move.from_uci(move))


def start_search(command: str):
    tokens = command.split()

    time_identifier = "wtime" if board.turn == bulletchess.WHITE else "btime"
    inc_identifier = "winc" if board.turn == bulletchess.WHITE else "binc"

    if time_identifier in tokens:
        time = int(tokens[tokens.index(time_identifier) + 1])
    else:
        time = 10_000

    if inc_identifier in tokens:
        inc = int(tokens[tokens.index(inc_identifier) + 1])
    else:
        inc = 0

    move_time = (time / 10 + inc)
    depth = 5 if move_time >= 15_000 else 4 if move_time >= 4_000 else 3

    move = find_best_move(board, depth)
    print(f"bestmove {move}")

if __name__ == "__main__":
    board = Board()
    io_loop()