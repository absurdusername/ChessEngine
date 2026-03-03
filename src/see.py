"""Static Exchange Evaluation — simulate capture chains to evaluate trades."""

import bulletchess
from bulletchess import Board, Move, WHITE, BLACK, PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING
from bulletchess.utils import piece_bitboard, white_bitboard, black_bitboard

from pst import piece_value

PIECE_ORDER = [PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING]

# Precomputed attack tables for leaper pieces
def _leaper_table(offsets):
    table = [0] * 64
    for sq in range(64):
        r, f = divmod(sq, 8)
        for dr, df in offsets:
            nr, nf = r + dr, f + df
            if 0 <= nr < 8 and 0 <= nf < 8:
                table[sq] |= 1 << (nr * 8 + nf)
    return table

KNIGHT_ATTACKS = _leaper_table([(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)])
KING_ATTACKS = _leaper_table([(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)])

# Pawn attackers: squares from which a pawn of `color` attacks `sq`
PAWN_ATTACKERS = [[0] * 64, [0] * 64]  # [white=0, black=1]
for _sq in range(64):
    _r, _f = divmod(_sq, 8)
    if _r > 0:
        if _f > 0: PAWN_ATTACKERS[0][_sq] |= 1 << ((_r - 1) * 8 + _f - 1)
        if _f < 7: PAWN_ATTACKERS[0][_sq] |= 1 << ((_r - 1) * 8 + _f + 1)
    if _r < 7:
        if _f > 0: PAWN_ATTACKERS[1][_sq] |= 1 << ((_r + 1) * 8 + _f - 1)
        if _f < 7: PAWN_ATTACKERS[1][_sq] |= 1 << ((_r + 1) * 8 + _f + 1)

BISHOP_DIRS = [(-1,-1),(-1,1),(1,-1),(1,1)]
ROOK_DIRS = [(-1,0),(1,0),(0,-1),(0,1)]


def _slider_attacks(sq, directions, occupied):
    bb = 0
    r, f = divmod(sq, 8)
    for dr, df in directions:
        nr, nf = r + dr, f + df
        while 0 <= nr < 8 and 0 <= nf < 8:
            bit = 1 << (nr * 8 + nf)
            bb |= bit
            if occupied & bit:
                break
            nr, nf = nr + dr, nf + df
    return bb


def _all_attackers(sq, occupied, piece_bbs, color_bbs):
    """Bitboard of all pieces attacking `sq`, masked by `occupied`."""
    att = (KNIGHT_ATTACKS[sq] & piece_bbs[KNIGHT]
         | KING_ATTACKS[sq] & piece_bbs[KING]
         | PAWN_ATTACKERS[0][sq] & piece_bbs[PAWN] & color_bbs[0]
         | PAWN_ATTACKERS[1][sq] & piece_bbs[PAWN] & color_bbs[1])
    diag = _slider_attacks(sq, BISHOP_DIRS, occupied)
    orth = _slider_attacks(sq, ROOK_DIRS, occupied)
    att |= diag & (piece_bbs[BISHOP] | piece_bbs[QUEEN])
    att |= orth & (piece_bbs[ROOK] | piece_bbs[QUEEN])
    return att & occupied


def _cache_bitboards(board):
    piece_bbs = {}
    for pt in PIECE_ORDER:
        wp = bulletchess.Piece(WHITE, pt)
        bp = bulletchess.Piece(BLACK, pt)
        piece_bbs[pt] = int(piece_bitboard(board, wp)) | int(piece_bitboard(board, bp))
    color_bbs = [int(white_bitboard(board)), int(black_bitboard(board))]
    return piece_bbs, color_bbs


def see(board: Board, move: Move) -> int:
    """Returns the material gain/loss of the capture sequence starting with `move`."""
    target = move.destination.index()
    origin = move.origin.index()

    victim = board[move.destination]
    attacker = board[move.origin]

    piece_bbs, color_bbs = _cache_bitboards(board)
    occupied = color_bbs[0] | color_bbs[1]

    # swap list: gain[d] = what side-to-move stands to gain at depth d
    gain = [0] * 33
    gain[0] = piece_value[victim.piece_type] if victim else piece_value[PAWN]

    current_value = piece_value[attacker.piece_type]
    side = 1 if attacker.color == WHITE else 0  # opponent color index
    occupied ^= 1 << origin  # remove attacker from occupied

    # recalculate attackers (x-ray: removing a piece may reveal sliders)
    d = 1
    while True:
        attackers = _all_attackers(target, occupied, piece_bbs, color_bbs)
        side_attackers = attackers & color_bbs[side]

        if not side_attackers:
            break

        gain[d] = current_value - gain[d - 1]

        # find least valuable attacker
        for pt in PIECE_ORDER:
            lva = side_attackers & piece_bbs[pt]
            if lva:
                # pick lowest bit
                lva_sq = lva & -lva
                occupied ^= lva_sq
                current_value = piece_value[pt]
                break

        side ^= 1
        d += 1
        if d >= 33:
            break

    # negamax the gain list
    while d > 1:
        d -= 1
        gain[d - 1] = -max(-gain[d - 1], gain[d])

    return gain[0]
