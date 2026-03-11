import time

import bulletchess
from bulletchess import Board, Move, CHECK, CHECKMATE, DRAW, PAWN
from evaluation import evaluate_board

from pst import piece_value, piece_square_table
from tt import TranspositionTable, TTEntry

MATE_SCORE = 1_000_000
MATE_THRESHOLD = 900_000
INF = 2_000_000

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

            move, score = self.negamax(board, depth, -INF, INF)

            elapsed = int((time.time() - self._t0) * 1000)
            tag = "(incomplete)" if self.is_expired else ""
            print(f"info depth {depth:<2} nodes {self.nodes:<7} cache hits {self.cache_hits:<6} "
                  f"time {elapsed:<5} score cp {score:<3} {tag}")

            if self.is_expired:
                break
            best_move = move

        return best_move

    def negamax(self, board: Board, depth: int, alpha: int, beta: int) -> tuple[Move | None, int]:
        """
        Reference: https://www.dogeystamp.com/chess4/

        Every negamax call is essentially a bounded search-request.
        * Score within [alpha, beta] -> useful result
        * Score < alpha -> all moves were bad, caller ignores it
        * Score > beta -> cutoff, caller ignores it
        """
        if self.is_expired: return None, 0
        self.nodes += 1  # increment node counter

        if board in DRAW: return None, 0

        if board in CHECKMATE: return None, -MATE_SCORE
        # minus sign because position is evaluated from current player's perspective

        # query the transposition table for a precomputed result
        cached = self.tt.get_cached_entry(board, depth)
        if cached is not None:
            self.cache_hits += 1
            if cached.can_use_score(alpha, beta):
                return cached.best_move, cached.score

        # depth exhausted => start quiescence search
        if depth == 0: return None, self.quiescence(board, alpha, beta)

        # used repeatedly later
        in_check = board in CHECK

        # Null-move pruning: skip our turn and search shallower
        # still finding moves that are too good after skipping a turn => prune
        if depth >= 3 and not in_check and abs(beta) < MATE_THRESHOLD:
            board.apply(None)  # skips our turn
            our_score = -self.negamax(board, depth - 3, -beta, -beta + 1)[1]
            board.undo()

            if our_score >= beta:
                return None, our_score

        possible_moves = self.get_ordered_moves(board)
        best_score, best_move = -INF, None
        alpha_orig = alpha  # saving original value for TT-related stuff later

        for i, move in enumerate(possible_moves):
            board.apply(move)
            new_depth = depth - 1

            # LMR: reduce depth for late quiet moves
            if i >= 3 and depth >= 3 and not move.is_capture(board) and not in_check:
                new_depth -= 1

            # PVS: search PV-node with a full window, other moves with a zero window
            if i == 0:
                our_score = -self.negamax(board, depth - 1, -beta, -alpha)[1]
            else:
                # PVS: scout with a zero window to test if move beats alpha
                our_score = -self.negamax(board, new_depth, -alpha - 1, -alpha)[1]

                # PVS: re-search with full window if scout found something useful
                if alpha < our_score < beta:
                    our_score = -self.negamax(board, new_depth, -beta, -alpha)[1]

            board.undo()

            # standard negamax bookkeeping
            score = self._decay_mate_score(our_score)
            if score > best_score:
                best_score, best_move = score, move
            if score >= beta:
                break
            alpha = max(alpha, score)

        if not self.is_expired:
            flag = TTEntry.flag_for(best_score, alpha_orig, beta)
            self.tt.store(board, depth, best_move, best_score, flag)

        return best_move, best_score

    def quiescence(self, board: Board, alpha: int, beta: int) -> int:
        """
        Reference: https://www.chessprogramming.org/Quiescence_Search#Pseudo_Code
        """
        if self.is_expired:
            return 0

        self.nodes += 1

        if board in DRAW:
            return 0

        if board in CHECKMATE:
            return -MATE_SCORE

        standing_pat = evaluate_board(board)
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

    @staticmethod
    def _move_score(move: Move, board: Board, tt_move: Move | None) -> int:
        if move == tt_move:
            return 1_000_000

        attacker = board[move.origin]
        attacker_value = piece_value[attacker.piece_type]

        # MVV-LVA
        if move.is_capture(board):
            victim = board[move.destination]

            # if victim is absent, it's a pawn (en passant)
            victim_value = piece_value[victim.piece_type] if victim else piece_value[PAWN]

            # attacker_value is divided by 100 because we want victim_value to always take preference in ranking
            return victim_value - attacker_value // 100

        # pieces flow along the PST gradient toward higher-potential squares
        table = piece_square_table[attacker.piece_type]
        origin_index, dest_index = move.origin.index(), move.destination.index()

        if attacker.color == bulletchess.WHITE:
            return table[-dest_index] - table[-origin_index]
        return table[dest_index] - table[origin_index]

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
    def _decay_mate_score(score: int) -> int:
        if score > MATE_THRESHOLD:
            return score - 1
        if score < -MATE_THRESHOLD:
            return score + 1
        return score
