# Done is better than perfect

import chess
import math

from chess.polyglot import zobrist_hash
from evaluation import evaluate_board

# Constants
MATE_SCORE = 1e6
MATE_THRESHOLD = 1e5
TT_SIZE = 1000_000

# Le Transposition Table | hash -> (hash, depth, evaluation)
TT: list[tuple | None] = [None] * TT_SIZE
# Probably should make this optional, because it contributes a decrease in perf for now

def _decay_mate_score(score: float) -> float:
    if abs(score) >= MATE_THRESHOLD:
        return math.copysign(abs(score) - 1, score)
    return score


def find_best_move(board: chess.Board, depth: int) -> chess.Move:
    possible_moves = board.legal_moves
    best_move, best_score = None, float("-inf")

    for move in possible_moves:
        board.push(move)
        score = -negamax(board, depth - 1, -float("inf"), float("inf"))
        board.pop()

        if score > best_score:
            best_move, best_score = move, score

    return best_move


def negamax(board: chess.Board, depth: int, alpha: float, beta: float) -> float:
    board_hash = zobrist_hash(board)
    tt_index = board_hash % TT_SIZE

    entry = TT[tt_index]
    if entry and entry[0] == board_hash and entry[1] >= depth:
        return entry[2]

    if board.is_checkmate():
        # position must be evaluated from current player's perspective
        return -MATE_SCORE

    if depth == 0:
        evaluation = evaluate_board(board)
        value = evaluation if board.turn == chess.WHITE else -evaluation
        return value

    possible_moves = board.legal_moves
    best_score = -float("inf")

    for move in possible_moves:
        board.push(move)
        move_score = -negamax(board, depth - 1, -beta, -alpha)
        board.pop()

        move_score = _decay_mate_score(move_score)

        if move_score > best_score:
            best_score = move_score

        alpha = max(alpha, move_score)
        if move_score >= beta:
            break

    TT[tt_index] = (board_hash, depth, best_score)
    return best_score
