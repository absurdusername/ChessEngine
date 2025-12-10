import chess
from pst import piece_square_table, piece_value


"""https://www.chessprogramming.org/Simplified_Evaluation_Function"""

def evaluate_board(board: chess.Board) -> float:
    total = 0
    end_game = _check_end_game(board)

    for square in chess.SQUARES:
        piece = board.piece_at(square)

        if not piece:
            continue

        value = piece_value[piece.piece_type] + _evaluate_piece(piece, square, end_game)
        total += value if piece.color == chess.WHITE else -value

    return total


def _evaluate_piece(piece: chess.Piece, square: int, end_game: bool) -> float:
    if piece.piece_type == chess.KING:
        mapping = piece_square_table[(piece.piece_type, end_game)]
    else:
        mapping = piece_square_table[piece.piece_type]

    return mapping[-square] if piece.color == chess.WHITE else mapping[square]


def _check_end_game(board: chess.Board) -> bool:
    # TO-DO: use the actual rule, this is a simpler subset.
    queens = 0

    for square in chess.SQUARES:
        piece = board.piece_at(square)

        if piece and piece.piece_type == chess.QUEEN:
            queens += 1

    return queens == 0