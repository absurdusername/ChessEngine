"""Shared-memory transposition table for Lazy SMP."""

import ctypes
import multiprocessing
from bulletchess import Move

from tt import ScoreFlag

# Pack each TT entry into a fixed-size struct (18 bytes)
class _RawEntry(ctypes.Structure):
    _fields_ = [
        ('hash', ctypes.c_uint64),
        ('depth', ctypes.c_int16),
        ('score', ctypes.c_int32),
        ('flag', ctypes.c_uint8),
        ('move_uci', ctypes.c_char * 6),  # e.g. "e7e8q\0"
    ]

ENTRY_SIZE = ctypes.sizeof(_RawEntry)  # ~21 bytes


class SharedTranspositionTable:
    """Lock-free shared TT backed by a multiprocessing RawArray."""

    def __init__(self, size: int):
        self.size = size
        self._buf = multiprocessing.RawArray(ctypes.c_char, size * ENTRY_SIZE)

    def _entry_at(self, index: int) -> _RawEntry:
        offset = index * ENTRY_SIZE
        return _RawEntry.from_buffer(self._buf, offset)

    def store(self, board, depth: int, move: Move | None, score: int, flag: ScoreFlag):
        h = hash(board)
        index = h % self.size
        entry = self._entry_at(index)
        if depth >= entry.depth or entry.hash == 0:
            entry.hash = h & 0xFFFFFFFFFFFFFFFF
            entry.depth = depth
            entry.score = score
            entry.flag = flag.value
            entry.move_uci = (str(move) if move else b'').encode()[:6]

    def get_cached_entry(self, board, depth: int):
        h = hash(board)
        index = h % self.size
        entry = self._entry_at(index)
        stored_hash = h & 0xFFFFFFFFFFFFFFFF
        if entry.hash == stored_hash and entry.depth >= depth:
            move = self._parse_move(entry.move_uci)
            return _TTResult(entry.depth, move, entry.score, ScoreFlag(entry.flag))
        return None

    def get_move_hint(self, board) -> Move | None:
        h = hash(board)
        index = h % self.size
        entry = self._entry_at(index)
        if entry.hash == (h & 0xFFFFFFFFFFFFFFFF):
            return self._parse_move(entry.move_uci)
        return None

    def clear(self):
        ctypes.memset(ctypes.addressof(self._buf), 0, self.size * ENTRY_SIZE)

    @staticmethod
    def _parse_move(uci_bytes: bytes) -> Move | None:
        uci = uci_bytes.rstrip(b'\x00').decode()
        return Move.from_uci(uci) if uci else None


class _TTResult:
    __slots__ = ('depth', 'best_move', 'score', 'score_flag')

    def __init__(self, depth, best_move, score, score_flag):
        self.depth = depth
        self.best_move = best_move
        self.score = score
        self.score_flag = score_flag
