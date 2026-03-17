import chess
from game import GameState


class GameController:
    """Application service that owns one game session lifecycle."""

    def __init__(self, game_mode="HUMAN_HUMAN", setup_command="Setup STANDARD"):
        self.state = GameState()
        self.state.setup_new_game(game_mode=game_mode, setup_cmd=setup_command)

    @property
    def board(self):
        return self.state.board

    def legal_moves(self):
        return self.state.get_legal_moves()

    def submit_move(self, move_uci):
        if not self.state.make_move(move_uci):
            return {"ok": False, "error": "illegal_move"}
        return {"ok": True, "result": self.state.get_result()}

    def current_turn_name(self):
        return "white" if self.board.get_current_player() == chess.WHITE else "black"
