import pygame
import chess
from board import ChessBoard
from UserInterface import UserInterface
from timer_manager import TimerManager
import time

class LocalGame:
    def __init__(self):
        self.board = ChessBoard()
        self.running = True
        
        # Initialize UI
        pygame.init()
        self.surface = pygame.display.set_mode([600, 600])
        pygame.display.set_caption('Pawn Game - Local Mode')
        self.UI = UserInterface(self.surface, self.board)
        self.UI.playerColor = chess.WHITE  # Keep White at bottom for board orientation
        self.UI.allow_both_colors = True   # Allow playing both colors
        
        # Get time control from server's GUI value
        try:
            # Try to read the time value from server's GUI
            with open("time_settings.txt", "r") as f:
                self.time_limit = int(float(f.read()) * 60)  # Convert minutes to seconds
        except:
            # Default to 5 minutes if can't read from server
            self.time_limit = 300  # 5 minutes in seconds
        
        # Setup initial board state
        setup_cmd = "Setup Wa2 Wb2 Wc2 Wd2 We2 Wf2 Wg2 Wh2 Ba7 Bb7 Bc7 Bd7 Be7 Bf7 Bg7 Bh7"
        self.board.setup_board(setup_cmd)
        
        # Initialize timer manager
        self.timer = TimerManager(self.time_limit)
        self.UI.white_time = self.timer.white_time
        self.UI.black_time = self.timer.black_time
        
        print("\n=== Local Game Started ===")
        print("Initial board setup complete")
        print(f"Time control: {self.time_limit//60} minutes per player")

    def update_timers(self):
        """Update the time remaining for the current player."""
        self.timer.update(self.board.board.turn)
        self.UI.white_time = self.timer.white_time
        self.UI.black_time = self.timer.black_time

    def check_time_loss(self):
        """Check if either player has lost on time."""
        winner = self.timer.check_time_loss()
        if winner == chess.WHITE:
            print("\n=== Game Over ===")
            print("White wins on time! Black's time has expired.")
            return True
        elif winner == chess.BLACK:
            print("\n=== Game Over ===")
            print("Black wins on time! White's time has expired.")
            return True
        return False

    def log_move(self, move_str, color):
        """Log move to terminal with color information."""
        self.timer.log_move(move_str, color)

    def is_valid_move(self, move_str, current_turn):
        """Validate move based on current turn."""
        try:
            move = chess.Move.from_uci(move_str)
            piece = self.board.board.piece_at(move.from_square)
            return piece and piece.color == current_turn
        except:
            return False

    def handle_piece_selection(self, pos):
        """Handle piece selection and return valid moves."""
        square = self.UI.get_square_from_pos(pos)
        if square is None:
            return None

        piece = self.board.board.piece_at(square)
        if piece and piece.color == self.board.board.turn:
            # Get valid moves for the selected piece
            valid_moves = [move for move in self.board.get_legal_moves() 
                         if chess.square_name(square) == move[:2]]
            print(f"Available moves: {valid_moves}")
            return square, valid_moves
        return None

    def run(self):
        """Main game loop."""
        clock = pygame.time.Clock()
        selected_square = None
        valid_moves = []
        self.timer.start()  # Start the timer
        
        while self.running:
            # Update timers
            self.update_timers()
            
            # Check for time-based loss
            if self.check_time_loss():
                self.UI.drawComponent()
                pygame.time.wait(2000)
                self.running = False
                break
            
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    print("Game ended by user")
                    self.running = False
                    break
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if not self.board.is_game_over():
                        # If no piece is selected, try to select one
                        if selected_square is None:
                            result = self.handle_piece_selection(event.pos)
                            if result:
                                selected_square, valid_moves = result
                                self.UI.selected_square = selected_square
                                self.UI.valid_moves = valid_moves
                        else:
                            # Try to make a move with the selected piece
                            target_square = self.UI.get_square_from_pos(event.pos)
                            if target_square is not None:
                                move = chess.square_name(selected_square) + chess.square_name(target_square)
                                if move[:4] in valid_moves:
                                    if self.board.move_piece(move):
                                        self.UI.last_move = move
                                        # Log the move and update timers
                                        current_color = not self.board.board.turn  # Color that just moved
                                        self.log_move(move, current_color)
                                        self.timer.switch_turn()  # Switch active timer
                                        
                                        # Check for promotion/win
                                        target_rank = chess.square_rank(target_square)
                                        piece = self.board.board.piece_at(target_square)
                                        if piece and ((piece.color == chess.WHITE and target_rank == 7) or
                                                    (piece.color == chess.BLACK and target_rank == 0)):
                                            winner = "White" if piece.color == chess.WHITE else "Black"
                                            print(f"\n=== Game Over ===")
                                            print(f"{winner} wins by reaching the opposite end!")
                                            self.UI.drawComponent()
                                            pygame.time.wait(2000)
                                            self.running = False
                                            break
                            
                            # Clear selection after move attempt
                            selected_square = None
                            valid_moves = []
                            self.UI.selected_square = None
                            self.UI.valid_moves = []

            # Check if game is over
            if self.board.is_game_over():
                winner = self.board.get_winner()
                winner_str = "White" if winner == chess.WHITE else "Black"
                print(f"\n=== Game Over ===")
                print(f"{winner_str} wins!")
                self.UI.drawComponent()  # This will show the winner message
                pygame.time.wait(2000)  # Wait for 2 seconds to show the message
                self.running = False
                break

            self.UI.drawComponent()
            clock.tick(30)

        pygame.quit()

if __name__ == "__main__":
    game = LocalGame()
    game.run() 