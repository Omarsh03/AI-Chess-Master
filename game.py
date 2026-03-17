import chess
from board import ChessBoard


class GameState:
    def __init__(self):
        self.board = ChessBoard()
        self.current_turn = chess.WHITE
        self.game_mode = None
        self.time_limit = 300  # 5 minutes in seconds
        self.moves_history = []
        
    def setup_new_game(self, game_mode="HUMAN_HUMAN", setup_cmd="Setup STANDARD"):
        """Setup a new game with initial position."""
        self.game_mode = game_mode
        self.board.setup_board(setup_cmd)
        self.current_turn = chess.WHITE
        self.moves_history = []
        return setup_cmd

    def make_move(self, move_str):
        """Make a move and update game state."""
        if self.board.move_piece(move_str):
            self.moves_history.append(move_str)
            self.current_turn = not self.current_turn
            return True
        return False

    def is_valid_move(self, move_str):
        """Check if a move is valid."""
        try:
            move = chess.Move.from_uci(move_str)
            return move in self.board.board.legal_moves
        except:
            return False

    def check_win_condition(self, move_str=None):
        """Compatibility helper: True when game reaches terminal winner state."""
        _ = move_str
        if not self.board.is_game_over():
            return False
        return self.board.get_winner() is not None

    def get_legal_moves(self):
        """Get all legal moves for current position."""
        return self.board.get_legal_moves()

    def is_game_over(self):
        """Check if the game is over."""
        return self.board.is_game_over()

    def get_winner(self):
        """Get the winner if game is over."""
        return self.board.get_winner()

    def get_result(self):
        return self.board.get_game_result()

    def reset_game(self):
        """Reset the game to initial state."""
        return self.setup_new_game(self.game_mode)