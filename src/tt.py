from enum import Enum
from dataclasses import dataclass
from bulletchess import Board, Move

class ScoreFlag(Enum):
    EXACT = 0
    UNDER_ESTIMATE = 1
    OVER_ESTIMATE = 2  # beta-cutoff

@dataclass
class TTEntry:
    board_hash: int
    depth: int
    best_move: Move
    score: int
    score_flag: ScoreFlag

# Le Transposition Table | hash -> TTEntry
class TranspositionTable:
    def __init__(self, size: int):
        self.size = size
        self.table: list[TTEntry | None] = [None] * size

    def store(self, board: Board, depth: int, move: Move, score: int, flag: ScoreFlag):
        index, entry = self._lookup(board)
        if entry is None or depth >= entry.depth:
            self.table[index] = TTEntry(hash(board), depth, move, score, flag)

    def get_cached_entry(self, board: Board, depth: int) -> TTEntry | None:
        """Returns the entry if the cached entry was computed at a sufficient depth."""
        _, entry = self._lookup(board)
        if entry and entry.depth >= depth and entry.board_hash == hash(board):
            return entry
        return None

    def get_move_hint(self, board: Board) -> Move | None:
        """Returns ANY cached move for the given position, regardless of depth."""
        index, entry = self._lookup(board)
        if entry and entry.board_hash == hash(board):
            return entry.best_move
        return None

    def clear(self):
        self.table = [None] * self.size

    def _lookup(self, board: Board) -> tuple[int, TTEntry | None]:
        """Returns (index, entry) for the given board position."""
        index = hash(board) % self.size
        return index, self.table[index]
