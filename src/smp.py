"""Lazy SMP — parallel search with shared transposition table."""

import multiprocessing
import os
import sys
import time

from bulletchess import Board, Move

from search import Search
from shared_tt import SharedTranspositionTable

TT_SIZE = 10_000_000
MIN_SMP_TIME = 0.3  # don't bother spawning workers for very short searches


def _worker(fen: str, deadline: float, shared_tt):
    """Helper process: searches the position, writing to shared TT."""
    # silence worker output — only main thread prints info
    sys.stdout = open(os.devnull, 'w')
    board = Board.from_fen(fen)
    search = Search(tt=shared_tt)
    search.find_best_move(board, deadline - time.time())


class LazySMP:
    def __init__(self, num_threads: int = 4):
        self.num_threads = num_threads
        self.shared_tt = SharedTranspositionTable(TT_SIZE)

    def find_best_move(self, board: Board, move_time: float) -> Move:
        use_smp = self.num_threads > 1 and move_time >= MIN_SMP_TIME
        deadline = time.time() + move_time
        main_search = Search(tt=self.shared_tt)

        workers = []
        if use_smp:
            fen = board.fen()
            ctx = multiprocessing.get_context('fork')
            for _ in range(self.num_threads - 1):
                p = ctx.Process(target=_worker, args=(fen, deadline, self.shared_tt))
                p.daemon = True
                p.start()
                workers.append(p)

        best_move = main_search.find_best_move(board, move_time)

        for p in workers:
            p.join(timeout=0.5)
            if p.is_alive():
                p.terminate()

        return best_move

    def clear(self):
        self.shared_tt.clear()
