# Done is better than perfect

import bulletchess
import math
import time

from bulletchess import Board, Move, CHECKMATE
# from bulletchess.utils import evaluate
from evaluation import evaluate_board

# Constants
MATE_SCORE = 1e6
MATE_THRESHOLD = 1e5
TT_SIZE = 10_000_000

# Le Transposition Table | hash -> (hash, depth, evaluation)
TT: list[tuple | None] = [None] * TT_SIZE
# Probably should make this optional, because it contributes a decrease in perf for now

# Metrics
nodes = cache_hits = 0

def _decay_mate_score(score: float) -> float:
    if abs(score) >= MATE_THRESHOLD:
        return math.copysign(abs(score) - 1, score)
    return score


def find_best_move(board: Board, depth: int) -> Move:
    global nodes, cache_hits
    t0 = time.time()
    nodes = cache_hits = 0

    possible_moves = board.legal_moves()
    best_move, best_score = None, float("-inf")

    for move in possible_moves:
        board.apply(move)
        score = -negamax(board, depth - 1, -float("inf"), float("inf"))
        board.undo()

        if score > best_score:
            best_move, best_score = move, score

    delta = round(time.time() - t0, 2)
    print(f"info depth {depth} nodes {nodes} cache hits {cache_hits} time {delta} score cp {best_score}")
    return best_move


def negamax(board: Board, depth: int, alpha: float, beta: float) -> float:
    global nodes, cache_hits
    nodes += 1

    board_hash = hash(board)
    tt_index = board_hash % TT_SIZE

    entry = TT[tt_index]
    if entry and entry[0] == board_hash and entry[1] >= depth:
        cache_hits += 1
        return entry[2]

    if board in CHECKMATE:
        # position must be evaluated from current player's perspective
        return -MATE_SCORE

    if depth == 0:
        # evaluation = evaluate(board)
        evaluation = evaluate_board(board)
        value = evaluation if board.turn == bulletchess.WHITE else -evaluation
        return value

    possible_moves = board.legal_moves()
    best_score = -float("inf")

    for move in possible_moves:
        board.apply(move)
        move_score = -negamax(board, depth - 1, -beta, -alpha)
        board.undo()

        move_score = _decay_mate_score(move_score)

        if move_score > best_score:
            best_score = move_score

        alpha = max(alpha, move_score)
        if move_score >= beta:
            break

    TT[tt_index] = (board_hash, depth, best_score)
    return best_score
