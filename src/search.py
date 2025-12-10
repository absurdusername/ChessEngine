import time
import chess
from evaluation import evaluate_board

MATE_SCORE = 1e9

class AlphaBetaSearch:
    def __init__(self, board: chess.Board):
        self.board = board
        self.nodes_explored = 0


    def search(self, clock: int, inc: int) -> chess.Move:
        t0 = time.time()

        depth = 4 if (inc + clock / 10) >= 6 else 3

        maximize = (self.board.turn == chess.WHITE)
        best_value = float('-inf') if maximize else float('inf')
        best_move = None

        moves = self._get_ordered_moves()
        for move in moves:
            self.board.push(move)

            if self.board.can_claim_draw():
                best_value = 0
            else:
                value = self._ab_search(float("-inf"), float("inf"), depth - 1, not maximize)

                if (maximize and value > best_value) or (not maximize and value < best_value):
                    best_value = value
                    best_move = move

            self.board.pop()

        print(f"info time {time.time() - t0}")
        print(f"info nodes {self.nodes_explored}")

        return best_move

    
    def _ab_search(self, alpha: float, beta: float, depth: int, maximize: bool) -> float:
        self.nodes_explored += 1
        
        if self.board.is_checkmate():
            return -MATE_SCORE if maximize else MATE_SCORE
        
        if depth == 0:
            return evaluate_board(self.board)

        value = float("-inf") if maximize else float("inf")
        moves = self._get_ordered_moves()

        if maximize:
            for move in moves:
                self.board.push(move)
                value = max(value, self._ab_search(alpha, beta, depth - 1, False))
                self.board.pop()

                if value >= beta:
                    break
                alpha = max(alpha, value)
        else:
            for move in moves:
                self.board.push(move)
                value = min(value, self._ab_search(alpha, beta, depth - 1, True))
                self.board.pop()

                if value <= alpha:
                    break
                beta = min(beta, value)

        return value

    def _get_ordered_moves(self) -> list[chess.Move]:
        return list(self.board.legal_moves)