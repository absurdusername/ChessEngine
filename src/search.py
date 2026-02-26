# Done is better than perfect

import bulletchess
import time

from bulletchess import Board, Move, CHECKMATE, DRAW
from bulletchess.utils import evaluate
from evaluation import evaluate_board
from pst import piece_value

# Constants
MATE_SCORE = 1e6
MATE_THRESHOLD = 1e5
TT_SIZE = 10_000_000


# Le Transposition Table | hash -> (hash, depth, best_move, score)
class TranspositionTable:
    def __init__(self, size: int):
        self.size = size
        self.table: list[tuple | None] = [None] * size

    def store(self, board: Board, depth: int, move: Move | None, score: float):
        board_hash, index, entry = self._lookup(board)
        if entry is None or depth >= entry[1]:
            self.table[index] = (board_hash, depth, move, score)

    def get_cached_result(self, board: Board, depth: int) -> tuple[Move, int] | None:
        """Returns (move, score) if the cached result was computed at a sufficient depth."""
        board_hash, _, entry = self._lookup(board)
        if entry and entry[0] == board_hash and entry[1] >= depth:
            return entry[2], entry[3]
        return None

    def get_move_hint(self, board: Board) -> Move | None:
        """Returns ANY cached move for the given position, regardless of depth."""
        board_hash, _, entry = self._lookup(board)
        if entry and entry[0] == board_hash:
            return entry[2]
        return None

    def clear(self):
        self.table = [None] * self.size

    def _lookup(self, board: Board) -> tuple[int, int, tuple | None]:
        """Returns (board_hash, index, entry) for the given board position."""
        board_hash = hash(board)
        index = board_hash % self.size
        return board_hash, index, self.table[index]


# TO-DO: should probably toss this global into SearchContext
TT = TranspositionTable(TT_SIZE)


class SearchContext:
    def __init__(self, deadline: float):
        # keeping track of time
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


def _move_score(move: Move, board: Board, tt_move: Move | None) -> int:
    if move == tt_move:
        return 1_000_000

    # MVV-LVA
    if move.is_capture(board):
        victim = board[move.destination]
        attacker = board[move.origin]

        # if victim is absent, it's a pawn (en passant)
        victim_value = piece_value[victim.piece_type] if victim else piece_value[bulletchess.PAWN]
        attacker_value = piece_value[attacker.piece_type]

        # attacker_value is divided by 100 because we want victim_value to always take preference in ranking
        return victim_value - attacker_value // 100

    return 0


def _get_ordered_moves(board: Board, captures_only: bool = False) -> list[Move]:
    tt_move = TT.get_move_hint(board)  # the best move from a previous shallower search
    moves = board.legal_moves()

    if captures_only:
        moves = [move for move in moves if move.is_capture(board)]

    moves.sort(
        key=lambda m: _move_score(m, board, tt_move),
        reverse=True
    )
    return moves


def _decay_mate_score(score: float) -> float:
    if score < -MATE_THRESHOLD:
        return score + 1

    if score > MATE_THRESHOLD:
        return score - 1

    return score


def negamax(
        board: Board,
        depth: int,
        alpha: float,
        beta: float,
        context: SearchContext,
        fast_eval: bool = True
) -> tuple[Move | None, float]:
    """
    Reference: https://www.dogeystamp.com/chess4/

    Every negamax call is essentially a bounded search-request.
    * Score within [alpha, beta] -> useful result
    * Score < alpha -> all moves were bad, caller ignores it
    * Score > beta -> cutoff, caller ignores it
    """

    if context.is_expired:
        return None, 0.0

    context.nodes_searched += 1

    # around a 6% overhead
    if board in DRAW:
        return None, 0.0

    if board in CHECKMATE:
        return None, -MATE_SCORE
    # minus sign because position is evaluated from current player's perspective

    result = TT.get_cached_result(board, depth)
    if result is not None:
        context.cache_hits += 1
        return result[0], result[1]

    if depth == 0:
        return None, quiescence(board, alpha, beta, context, fast_eval)

    possible_moves = _get_ordered_moves(board)
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

    TT.store(board, depth, best_move, best_score)
    return best_move, best_score


def quiescence(
        board: Board,
        alpha: float,
        beta: float,
        context: SearchContext,
        fast_eval: bool = True
) -> float:
    """
    Reference: https://www.chessprogramming.org/Quiescence_Search#Pseudo_Code
    """
    if context.is_expired:
        return 0.0

    context.nodes_searched += 1

    if board in DRAW:
        return 0.0

    if board in CHECKMATE:
        return -MATE_SCORE

    # Shannon's eval is 7x faster, but decisively worse in SPRT.
    # Might use in the future when balancing evaluation speed and search depth.
    if fast_eval:
        evaluation = evaluate(board)
    else:
        evaluation = evaluate_board(board)
    standing_pat = evaluation if board.turn == bulletchess.WHITE else -evaluation

    if standing_pat >= beta:
        return standing_pat

    possible_moves = _get_ordered_moves(board, captures_only=True)
    alpha = max(alpha, standing_pat)

    for move in possible_moves:
        if not move.is_capture(board):
            continue

        board.apply(move)
        score = -quiescence(board, -beta, -alpha, context, fast_eval)
        board.undo()

        if score >= beta:
            return score

        alpha = max(alpha, score)

    return alpha


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
