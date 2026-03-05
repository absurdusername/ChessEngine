import bulletchess

from bulletchess import Board
from pst import piece_square_table, piece_value


"""https://www.chessprogramming.org/Simplified_Evaluation_Function"""

def evaluate_board(board: Board) -> int:
    total = 0
    end_game = _check_end_game(board)

    for square in bulletchess.SQUARES:
        piece = board[square]

        if not piece:
            continue

        value = piece_value[piece.piece_type] + _evaluate_piece(piece, square, end_game)
        total += value if piece.color == bulletchess.WHITE else -value

    return total


def _evaluate_piece(piece: bulletchess.Piece, square: bulletchess.Square, end_game: bool) -> int:
    index = square.index()

    if piece.piece_type == bulletchess.KING:
        mapping = piece_square_table[(piece.piece_type, end_game)]
    else:
        mapping = piece_square_table[piece.piece_type]

    return mapping[-index] if piece.color == bulletchess.WHITE else mapping[index]


def _check_end_game(board: Board) -> bool:
    # TO-DO: use the actual rule, this is a simpler subset.
    queens = 0

    for square in bulletchess.SQUARES:
        piece = board[square]

        if piece and piece.piece_type == bulletchess.QUEEN:
            queens += 1

    return queens == 0