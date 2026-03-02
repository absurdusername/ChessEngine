import time

import bulletchess
from bulletchess import Board, Move, CHECK, CHECKMATE, DRAW, PAWN
from bulletchess.utils import evaluate

from pst import piece_value
from tt import TranspositionTable

MATE_SCORE = 1e6
MATE_THRESHOLD = 1e5
TT_SIZE = 10_000_000  # size of the transposition table
DELTA_MARGIN = 200  # used for delta pruning in quiescence


class Search:
    def __init__(self):
        self.tt = TranspositionTable(TT_SIZE)
        self.deadline = 0.0
        self.nodes = 0
        self.cache_hits = 0
        self._t0 = time.time()

    def find_best_move(self, board: Board, move_time: float) -> Move:
        self.deadline = time.time() + move_time
        best_move = None

        for depth in range(1, 100):
            self.nodes = 0
            self.cache_hits = 0
            self._t0 = time.time()

            move, score = self.negamax(board, depth, -float("inf"), float("inf"))

            elapsed = int((time.time() - self._t0) * 1000)
            tag = "(incomplete)" if self.is_expired else ""
            print(f"info depth {depth} nodes {self.nodes} cache hits {self.cache_hits} "
                  f"time {elapsed} score cp {score} {tag}")

            if self.is_expired:
                break
            best_move = move

        return best_move

    def negamax(self, board: Board, depth: int, alpha: float, beta: float) -> tuple[Move | None, float]:
        """
        Reference: https://www.dogeystamp.com/chess4/

        Every negamax call is essentially a bounded search-request.
        * Score within [alpha, beta] -> useful result
        * Score < alpha -> all moves were bad, caller ignores it
        * Score > beta -> cutoff, caller ignores it
        """
        if self.is_expired:
            return None, 0.0

        self.nodes += 1

        # around a 6% overhead
        if board in DRAW:
            return None, 0.0

        if board in CHECKMATE:
            return None, -MATE_SCORE
        # minus sign because position is evaluated from current player's perspective

        cached = self.tt.get_cached_result(board, depth)
        if cached is not None:
            self.cache_hits += 1
            return cached[0], cached[1]

        if depth == 0:
            return None, self.quiescence(board, alpha, beta)

        # Null-move pruning: skip our turn and search shallower
        # still finding moves that are too good after skipping a turn => prune
        # search with a tiny window [beta-1, beta] to just check for a beta-cutoff
        # could've used [beta, beta], but sticking with the formulas for now
        if depth >= 3 and board not in CHECK and abs(beta) < MATE_THRESHOLD:
            board.apply(None)  # skips our turn
            _, opponent_score = self.negamax(board, depth - 3, -beta, -beta + 1)
            board.undo()

            our_score = -opponent_score
            if our_score >= beta:
                return None, our_score

        possible_moves = self.get_ordered_moves(board)
        best_score, best_move = -float("inf"), None

        for i, move in enumerate(possible_moves):
            # LMR: reduce depth for late _quiet_ moves
            reduced = (depth >= 3 and i >= 3
                       and not move.is_capture(board) and board not in CHECK)

            board.apply(move)
            _, opponent_score = self.negamax(board, depth - 2 if reduced else depth - 1, -beta, -alpha)

            # re-search at full depth if the reduced search beat alpha
            if reduced and -opponent_score > alpha:
                _, opponent_score = self.negamax(board, depth - 1, -beta, -alpha)

            board.undo()

            our_score = -opponent_score
            score = self._decay_mate_score(our_score)

            if score > best_score:
                best_score, best_move = score, move

            if score >= beta:
                break

            alpha = max(alpha, score)

        self.tt.store(board, depth, best_move, best_score)
        return best_move, best_score

    def quiescence(self, board: Board, alpha: float, beta: float) -> float:
        """
        Reference: https://www.chessprogramming.org/Quiescence_Search#Pseudo_Code
        """
        if self.is_expired:
            return 0.0

        self.nodes += 1

        if board in DRAW:
            return 0.0

        if board in CHECKMATE:
            return -MATE_SCORE

        standing_pat = evaluate(board)
        standing_pat = standing_pat if board.turn == bulletchess.WHITE else -standing_pat

        if standing_pat >= beta:
            return standing_pat

        alpha = max(alpha, standing_pat)

        for move in self.get_ordered_moves(board, captures_only=True):
            victim = board[move.destination]
            victim_value = piece_value[victim.piece_type] if victim else piece_value[PAWN]

            # delta pruning
            if standing_pat + victim_value + DELTA_MARGIN <= alpha:
                continue

            board.apply(move)
            score = -self.quiescence(board, -beta, -alpha)
            board.undo()

            if score >= beta:
                return score

            alpha = max(alpha, score)

        return alpha

    def _move_score(self, move: Move, board: Board, tt_move: Move) -> int:
        if move == tt_move:
            return 1_000_000

        # MVV-LVA
        if move.is_capture(board):
            victim = board[move.destination]
            attacker = board[move.origin]

            # if victim is absent, it's a pawn (en passant)
            victim_value = piece_value[victim.piece_type] if victim else piece_value[PAWN]
            attacker_value = piece_value[attacker.piece_type]

            # attacker_value is divided by 100 because we want victim_value to always take preference in ranking
            return victim_value - attacker_value // 100

        return 0

    def get_ordered_moves(self, board: Board, captures_only: bool = False) -> list[Move]:
        moves = board.legal_moves()
        tt_move = self.tt.get_move_hint(board)  # the best move from a previous shallower search

        if captures_only:
            moves = [move for move in moves if move.is_capture(board)]

        moves.sort(
            key=lambda m: self._move_score(m, board, tt_move),
            reverse=True
        )
        return moves

    @property
    def is_expired(self) -> bool:
        return time.time() > self.deadline

    @staticmethod
    def _decay_mate_score(score: float) -> float:
        if score > MATE_THRESHOLD:
            return score - 1
        if score < -MATE_THRESHOLD:
            return score + 1
        return score
