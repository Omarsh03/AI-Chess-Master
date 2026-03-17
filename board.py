import chess
from engine import ChessEngine


class ChessBoard(ChessEngine):
    """
    Backward-compatible adapter over the new generic engine.
    Existing callers can keep using ChessBoard while rules are now full chess.
    """

    def __init__(self, board=None):
        super().__init__(board=board if board is not None else chess.Board())

    def move_piece(self, move_str):
        return self.make_move(move_str)