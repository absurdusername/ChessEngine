# Done is better than perfect

import math
import chess
from evaluation import evaluate_board

MATE_SCORE = 1e6
MATE_THRESHOLD = 1e5

def _negate_and_decay_score(score: float) -> float:
    if abs(score) >= MATE_THRESHOLD:
        return -math.copysign(abs(score) - 1, score)
    return -score


def negamax(board: chess.Board, depth: int) -> tuple[chess.Move | None, float]:
    if board.is_checkmate():
        value = -MATE_SCORE if board.turn == chess.WHITE else MATE_SCORE
        return None, value

    if depth == 0:
        return None, evaluate_board(board)

    possible_moves = board.legal_moves
    best_score, best_move = -float("inf"), None

    for move in possible_moves:
        board.push(move)
        _, opponent_score = negamax(board, depth - 1)
        move_score = _negate_and_decay_score(opponent_score)

        if move_score > best_score:
            best_score, best_move = move_score, move

        board.pop()

    return best_move, best_score