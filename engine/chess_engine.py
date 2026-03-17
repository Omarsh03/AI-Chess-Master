import chess
import copy


PIECE_CODE_MAP = {
    "K": chess.KING,
    "Q": chess.QUEEN,
    "R": chess.ROOK,
    "B": chess.BISHOP,
    "N": chess.KNIGHT,
    "P": chess.PAWN,
}


class ChessEngine:
    """Generic full-chess engine wrapper around python-chess."""

    def __init__(self, board=None):
        self.board = board if board is not None else chess.Board()
        self.cached_legal_moves = None

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        result.board = chess.Board(self.board.fen())
        result.cached_legal_moves = None
        return result

    def copy(self):
        return ChessEngine(chess.Board(self.board.fen()))

    def reset_to_standard(self):
        self.board = chess.Board()
        self.cached_legal_moves = None

    def setup_board(self, setup_command):
        """
        Supported setup forms:
        - "Setup STANDARD"
        - "Setup FEN <full fen>"
        - "Setup Wa2 Bb7 WQd1 BKe8" (piece type optional; defaults to pawn)
        """
        if not setup_command:
            self.reset_to_standard()
            return

        command = setup_command.strip()
        if not command.startswith("Setup"):
            raise ValueError("Setup command must start with 'Setup'")

        parts = command.split()
        if len(parts) >= 2 and parts[1].upper() == "STANDARD":
            self.reset_to_standard()
            return

        if len(parts) >= 3 and parts[1].upper() == "FEN":
            fen = command.split(" ", 2)[2]
            self.board = chess.Board(fen)
            self.cached_legal_moves = None
            return

        self.board.clear_board()
        for token in parts[1:]:
            # Legacy format: Wa2 / Bb7
            if len(token) == 3:
                color_char, square_text = token[0], token[1:]
                piece_type = chess.PAWN
            # Extended format: WQa1 / BKe8 / WNd4
            elif len(token) == 4:
                color_char, piece_char, square_text = token[0], token[1], token[2:]
                piece_type = PIECE_CODE_MAP.get(piece_char.upper())
                if piece_type is None:
                    raise ValueError(f"Unknown piece code in token: {token}")
            else:
                raise ValueError(f"Invalid setup token: {token}")

            color = chess.WHITE if color_char.upper() == "W" else chess.BLACK
            square = chess.parse_square(square_text.lower())
            self.board.set_piece_at(square, chess.Piece(piece_type, color))

        self.cached_legal_moves = None

    def get_legal_moves(self):
        if self.cached_legal_moves is None:
            self.cached_legal_moves = [move.uci() for move in self.board.legal_moves]
        return self.cached_legal_moves

    def make_move(self, move_str):
        """Apply a UCI move (supports promotions, e.g. e7e8q)."""
        if not move_str:
            return False

        try:
            move_text = move_str.strip().lower()
            candidate = chess.Move.from_uci(move_text)
        except ValueError:
            return False

        if candidate in self.board.legal_moves:
            self.board.push(candidate)
            self.cached_legal_moves = None
            return True

        # Support 4-char promotion shorthand by auto-queening when applicable.
        if len(move_text) == 4:
            matches = [
                m for m in self.board.legal_moves if m.uci().startswith(move_text)
            ]
            if len(matches) == 1:
                self.board.push(matches[0])
                self.cached_legal_moves = None
                return True
        return False

    def is_game_over(self):
        return self.board.is_game_over(claim_draw=True)

    def get_winner(self):
        if not self.is_game_over():
            return None
        result = self.board.result(claim_draw=True)
        if result == "1-0":
            return chess.WHITE
        if result == "0-1":
            return chess.BLACK
        return None

    def get_game_result(self):
        if not self.is_game_over():
            return {"status": "ongoing", "winner": None, "result": None}

        winner = self.get_winner()
        if winner == chess.WHITE:
            winner_name = "white"
        elif winner == chess.BLACK:
            winner_name = "black"
        else:
            winner_name = None

        outcome = self.board.outcome(claim_draw=True)
        reason = outcome.termination.name if outcome else "UNKNOWN"
        return {
            "status": "finished",
            "winner": winner_name,
            "result": self.board.result(claim_draw=True),
            "termination": reason,
        }

    def get_current_player(self):
        return self.board.turn

    def get_board_state(self):
        return str(self.board)

    def get_fen(self):
        return self.board.fen()
