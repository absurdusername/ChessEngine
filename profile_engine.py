import profiling.tracing
import pstats
from io import StringIO

import sys, os

# Add src to sys.path, idk how but this fixes the imports
sys.path.append(os.path.join(os.getcwd(), 'src'))

from bulletchess import Board
from src.search import Search

def benchmark():
    move_time = 15
    fen_string = "r2q1rk1/p1p2ppp/4bn2/3p4/1b6/2NB4/PPPB1PPP/R2Q1RK1 w - - 4 11"

    board = Board.from_fen(fen_string)
    search = Search()

    search.find_best_move(board, move_time)

if __name__ == "__main__":
    pr = profiling.tracing.Profile()
    pr.enable()
    benchmark()
    pr.disable()

    s = StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats(pstats.SortKey.CUMULATIVE)
    ps.print_stats()
    print(s.getvalue())