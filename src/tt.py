from bulletchess import Board, Move

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
