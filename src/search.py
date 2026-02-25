# Done is better than perfect

import bulletchess
import time

from bulletchess import Board, Move, CHECKMATE, DRAW
from bulletchess.utils import evaluate
from evaluation import evaluate_board

# Constants
MATE_SCORE = 1e6
MATE_THRESHOLD = 1e5
TT_SIZE = 10_000_000

# Le Transposition Table | hash -> (hash, depth, best_move, score)
# Probably should make this optional, because it contributes a decrease in perf for now
TT: list[tuple | None] = [None] * TT_SIZE


class SearchContext:
    def __init__(self, deadline: float):
        self.deadline = deadline

        # stats
        self.nodes_searched = 0
        self.cache_hits = 0
        self._t0 = time.time()

    @property
    def is_expired(self) -> bool:
        """Did we overrun the deadline?"""
        return time.time() > self.deadline

    @property
    def time_elapsed(self) -> int:
        """Time elapsed since initialization in milliseconds."""
        return int((time.time() - self._t0) * 1000)


def _decay_mate_score(score: float) -> float:
    if score < -MATE_THRESHOLD:
        return score + 1

    if score > MATE_THRESHOLD:
        return score - 1

    return score


def find_best_move(board: Board, move_time: float) -> Move:
    deadline = time.time() + move_time
    best_move = None

    for depth in range(1, 100):
        context = SearchContext(deadline)

        move, score = negamax(
            board, depth, alpha=-float("inf"), beta=float("inf"), context=context
        )

        if not context.is_expired:
            best_move = move

        status = "(incomplete)" if context.is_expired else ""
        print(f"info depth {depth} nodes {context.nodes_searched} cache hits {context.cache_hits} "
              f"time {context.time_elapsed} score cp {score} {status}")

        if context.is_expired:
            break

    return best_move


def negamax(
        board: Board,
        depth: int,
        alpha: float,
        beta: float,
        context: SearchContext,
        fast_eval: bool = True
) -> tuple[Move | None, float]:
    """Reference: https://www.dogeystamp.com/chess4/"""

    if context.is_expired:
        return None, 0.0

    context.nodes_searched += 1

    # around a 6% overhead
    if board in DRAW:
        return None, 0.0

    if board in CHECKMATE:
        return None, -MATE_SCORE
    # minus sign because position is evaluated from current player's perspective

    board_hash = hash(board)
    tt_index = board_hash % TT_SIZE
    entry = TT[tt_index]
    if entry and entry[0] == board_hash and entry[1] >= depth:
        context.cache_hits += 1
        return entry[2], entry[3]

    if depth == 0:
        # Shannon's eval is 7x faster, but decisively worse in SPRT.
        # Might use in the future when balancing evaluation speed and search depth.
        if fast_eval:
            evaluation = evaluate(board)
        else:
            evaluation = evaluate_board(board)
        value = evaluation if board.turn == bulletchess.WHITE else -evaluation
        return None, value

    possible_moves = board.legal_moves()
    best_score, best_move = -float("inf"), None

    for move in possible_moves:
        board.apply(move)
        opponent_move, opponent_score = negamax(
            board, depth - 1, -beta, -alpha,
            context=context, fast_eval=fast_eval
        )
        board.undo()

        our_score = -opponent_score
        our_score = _decay_mate_score(our_score)

        if our_score > best_score:
            best_score, best_move = our_score, move

        if our_score >= beta:
            break

        alpha = max(alpha, our_score)

    TT[tt_index] = (board_hash, depth, best_move, best_score)
    return best_move, best_score
