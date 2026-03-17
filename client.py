import socket
import pygame
from UserInterface import UserInterface
import chess
import time
from network import NetworkHandler
from game import GameState

class ChessClient:
    def __init__(self):
        self.network = NetworkHandler()
        self.game = GameState()
        self.running = True
        self.connected_mode = None
        
        # Initialize UI
        pygame.init()
        self.surface = pygame.display.set_mode([600, 600])
        pygame.display.set_caption('Full Chess')
        self.UI = UserInterface(self.surface, self.game.board)
        
        # Timer variables
        self.last_move_time = None
        self.current_player_time = None

    def update_timers(self):
        """Update the time remaining for the current player."""
        if self.last_move_time is None:
            self.last_move_time = time.time()
            return

        current_time = time.time()
        elapsed = current_time - self.last_move_time
        
        if self.game.board.board.turn == chess.WHITE:
            self.UI.white_time = max(0, self.UI.white_time - elapsed)
        else:
            self.UI.black_time = max(0, self.UI.black_time - elapsed)
            
        self.last_move_time = current_time

    def switch_timer(self):
        """Switch the active timer after a move."""
        self.last_move_time = time.time()

    def handle_server_messages(self):
        """Handle initial server setup messages."""
        # Initial connection handshake
        data = self.network.receive_message()
        print(f"Server: {data}")
        self.network.send_message("OK")

        # Handle setup command
        data = self.network.receive_message()
        print(f"Server: {data}")
        if data.startswith("Setup"):
            self.game.board.setup_board(data)
            self.UI.drawComponent()
            self.network.send_message("OK")

        # Handle time limit
        data = self.network.receive_message()
        print(f"Server: {data}")
        if data.startswith("Time"):
            minutes = float(data.split()[1])  # Get the actual minutes value
            self.game.time_limit = int(minutes * 60)  # Convert to seconds
            self.UI.white_time = self.game.time_limit
            self.UI.black_time = self.game.time_limit
            self.network.send_message("OK")
            
        # Handle game mode
        data = self.network.receive_message()
        print(f"Server: {data}")
        self.connected_mode = data
        if data == "HUMAN_HUMAN":
            self.game.game_mode = "HUMAN_HUMAN"
            self.UI.playerColor = chess.WHITE  # Always show White at bottom
            self.UI.allow_both_colors = True
            self.network.send_message("OK")
        elif data in ["White", "Black", "Spectator"]:
            if data == "White":
                self.UI.playerColor = chess.WHITE
                self.UI.allow_both_colors = False  # Only allow White moves
            elif data == "Black":
                self.UI.playerColor = chess.BLACK
                self.UI.allow_both_colors = False  # Only allow Black moves
            else:  # Spectator
                self.UI.playerColor = None
                self.UI.allow_both_colors = False  # No moves allowed
            self.network.send_message("OK")

    def handle_move(self, move_str):
        """Handle move execution and network communication."""
        if not move_str:
            return False

        self.network.send_message(move_str, blocking=True)
        response = self.network.receive_message()
        if response == "OK":
            self.game.make_move(move_str)
            self.UI.last_move = move_str
            self.switch_timer()
            if self.game.board.is_game_over():
                result = self.game.get_result()
                self.UI.show_game_over_message(
                    f"Result {result['result']} ({result.get('termination', 'UNKNOWN')})"
                )
            self.UI.drawComponent()
        elif response == "exit":
            return False
        return True

    def run(self):
        """Main game loop."""
        if not self.network.connect_to_server():
            print("Could not connect to server. Please make sure the server is running.")
            return

        self.handle_server_messages()
        print(f"Successfully connected to server! Game mode: {self.game.game_mode}")

        clock = pygame.time.Clock()
        while self.running:
            # Update timers
            self.update_timers()
            
            # Check for time loss
            if self.UI.white_time <= 0:
                print("Black wins on time!")
                self.network.send_message("Lost", blocking=True)
                break
            elif self.UI.black_time <= 0:
                print("White wins on time!")
                self.network.send_message("Lost", blocking=True)
                break

            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    self.network.send_message("exit", blocking=True)
                    break
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if not self.game.board.is_game_over():
                        move = self.UI.handle_click(event.pos)
                        if move and not self.handle_move(move):
                            self.running = False
                            break

            # Check for server messages
            try:
                data = self.network.receive_message(blocking=False)
                if data:
                    print(f"Server: {data}")
                    if data == "Begin":
                        self.last_move_time = time.time()  # Start timing
                    elif data == "exit":
                        self.running = False
                        break
                    elif data.startswith("Result "):
                        self.UI.show_game_over_message(data)
                        self.running = False
                        break
                    elif len(data) >= 4:  # Move format
                        move_str = data.strip()
                        self.game.make_move(move_str)
                        self.UI.last_move = move_str
                        self.switch_timer()  # Switch timer after opponent's move
                        self.UI.drawComponent()
                        self.network.send_message("OK")
                        
                        # Check if this move ended the game
                        if self.game.board.is_game_over():
                            result = self.game.get_result()
                            self.UI.show_game_over_message(
                                f"Result {result['result']} ({result.get('termination', 'UNKNOWN')})"
                            )
                            self.network.send_message(
                                f"Result {result['result']} {result.get('termination', 'UNKNOWN')}",
                                blocking=True,
                            )
                            break
            except Exception as e:
                print(f"Error: {e}")
                self.running = False
                break

            self.UI.drawComponent()
            clock.tick(30)

        pygame.quit()
        self.network.close()

if __name__ == "__main__":
    client = ChessClient()
    client.run()
