import pygame
import chess
from board import ChessBoard
from UserInterface import UserInterface
from timer_manager import TimerManager

class LocalGame:
    def __init__(self):
        self.board = ChessBoard()
        self.running = True
        
        # Initialize UI
        pygame.init()
        self.surface = pygame.display.set_mode([600, 600])
        pygame.display.set_caption('Full Chess - Local Mode')
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
        setup_cmd = "Setup STANDARD"
        self.board.setup_board(setup_cmd)
        
        # Initialize timer manager
        self.timer = TimerManager(self.time_limit)
        self.UI.white_time = self.timer.white_time
        self.UI.black_time = self.timer.black_time
        
        print("\n=== Local Game Started ===")
        print("Initial standard board setup complete")
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

    def run(self):
        """Main game loop."""
        clock = pygame.time.Clock()
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
                        move = self.UI.handle_click(event.pos)
                        if move and self.board.make_move(move):
                            self.UI.last_move = move
                            current_color = not self.board.board.turn
                            self.log_move(move, current_color)
                            self.timer.switch_turn()

            # Check if game is over
            if self.board.is_game_over():
                result = self.board.get_game_result()
                print(f"\n=== Game Over ===")
                print(f"Result: {result['result']} ({result.get('termination', 'UNKNOWN')})")
                self.UI.show_game_over_message(
                    f"Result {result['result']} ({result.get('termination', 'UNKNOWN')})"
                )
                pygame.time.wait(2500)
                self.running = False
                break

            self.UI.drawComponent()
            clock.tick(30)

        pygame.quit()

if __name__ == "__main__":
    game = LocalGame()
    game.run() 