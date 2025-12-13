# Make it work then make it better
# Code first, refactor second

import sys
import chess

from search import negamax


def io_loop():
    board = chess.Board()

    while True:
        command = input()
        execute(command, board)


def execute(command: str, board: chess.Board):
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
            arrange_board(command, board)

        case ["go", *args]:
            start_search(command, board)

        case ["quit"]:
            sys.exit(0)

        case ["stop"]:
            # TO-DO: stop the search ASAP and print the bestmove
            pass


def arrange_board(command: str, board: chess.Board):
    tokens = command.split()

    if tokens[1] == "startpos":
        board.reset()
    else:
        fen = " ".join(tokens[2:8])
        board.set_board_fen(fen)

    if "moves" in tokens:
        i = tokens.index("moves")
        moves_list = tokens[i+1:]

        for move in moves_list:
            board.push_uci(move)


def start_search(command: str, board: chess.Board):
    tokens = command.split()

    time_identifier = "wtime" if board.turn == chess.WHITE else "btime"
    inc_identifier = "winc" if board.turn == chess.WHITE else "binc"

    if time_identifier in tokens:
        time = int(tokens[tokens.index(time_identifier) + 1])
    else:
        time = 10

    if inc_identifier in tokens:
        inc = int(tokens[tokens.index(inc_identifier) + 1])
    else:
        inc = 0

    depth = 4 if (time / 10 + inc) >= 6 else 3
    move = negamax(board, depth)[0]
    print(f"bestmove {move}")

if __name__ == "__main__":
    io_loop()