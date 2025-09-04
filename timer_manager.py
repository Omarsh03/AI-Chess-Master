import time
import chess

class TimerManager:
    def __init__(self, initial_time_seconds=300):
        self.time_limit = initial_time_seconds
        self.white_time = self.time_limit
        self.black_time = self.time_limit
        self.current_player_time_started = time.time()
        self.is_paused = False
        self.last_update = time.time()

    def start(self):
        """Start or resume the timer."""
        self.is_paused = False
        self.current_player_time_started = time.time()
        self.last_update = time.time()

    def pause(self):
        """Pause the timer."""
        self.is_paused = True
        self.update()  # Update times before pausing

    def reset(self, new_time_limit=None):
        """Reset the timer with optionally new time limit."""
        if new_time_limit is not None:
            self.time_limit = new_time_limit
        self.white_time = self.time_limit
        self.black_time = self.time_limit
        self.current_player_time_started = time.time()
        self.last_update = time.time()
        self.is_paused = False

    def update(self, current_turn=chess.WHITE):
        """Update the time remaining for the current player."""
        if self.is_paused:
            return

        current_time = time.time()
        elapsed = current_time - self.last_update
        
        if current_turn == chess.WHITE:
            self.white_time = max(0, self.white_time - elapsed)
        else:
            self.black_time = max(0, self.black_time - elapsed)
            
        self.last_update = current_time

    def switch_turn(self):
        """Switch the active timer to the other player."""
        self.update()  # Update current player's time before switching
        self.current_player_time_started = time.time()
        self.last_update = time.time()

    def get_time_remaining(self, color):
        """Get the remaining time for a specific color."""
        return self.white_time if color == chess.WHITE else self.black_time

    def format_time(self, seconds):
        """Format time in seconds to MM:SS format."""
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"

    def get_formatted_time(self, color):
        """Get formatted time string for a specific color."""
        time_left = self.get_time_remaining(color)
        return self.format_time(time_left)

    def check_time_loss(self):
        """Check if either player has lost on time."""
        if self.white_time <= 0:
            return chess.BLACK  # Black wins (White lost on time)
        elif self.black_time <= 0:
            return chess.WHITE  # White wins (Black lost on time)
        return None  # No time loss

    def log_move(self, move_str, color):
        """Log move to terminal with remaining time."""
        time_left = self.get_time_remaining(color)
        formatted_time = self.format_time(time_left)
        print(f"{'White' if color == chess.WHITE else 'Black'} moves: {move_str} ({formatted_time} remaining)") 