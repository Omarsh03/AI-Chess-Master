import pygame
import chess
import time
from ai_agent import AIAgent

class UserInterface:
    def __init__(self, surface, board):
        self.surface = surface
        self.board = board
        self.square_size = surface.get_width() // 8  # Calculate square size from surface
        self.selected_square = None
        self.last_move = None
        self.valid_moves = []  # Store valid moves for selected piece
        self.playerColor = chess.WHITE  # Used for board orientation
        self.allow_both_colors = True   # Allow playing both colors
        self.white_time = 300  # 5 minutes in seconds
        self.black_time = 300  # 5 minutes in seconds
        self.restart_prompt_shown = False  # Track if restart prompt has been shown
        
        # Colors
        self.LIGHT_SQUARE = (240, 217, 181)
        self.DARK_SQUARE = (181, 136, 99)
        self.SELECTED_COLOR = (130, 151, 105)
        self.VALID_MOVE_COLOR = (186, 202, 43)
        self.LAST_MOVE_COLOR = (205, 210, 106)
        self.TEXT_COLOR = (0, 0, 0)
        self.TIME_WARNING_COLOR = (255, 0, 0)  # Red for low time warning
        
        # Load piece images
        self.piece_images = {}
        self._load_piece_images()
        
        # Initialize font
        pygame.font.init()
        self.font = pygame.font.Font(None, 36)
        
    def _load_piece_images(self):
        """Load chess piece images."""
        try:
            # Load pawn images
            self.piece_images['wp'] = pygame.image.load("white_pawn.png")
            self.piece_images['bp'] = pygame.image.load("black_pawn.png")
            
            # Scale images to fit squares
            square_size = self.surface.get_width() // 8
            for key in self.piece_images:
                self.piece_images[key] = pygame.transform.scale(
                    self.piece_images[key], 
                    (square_size - 10, square_size - 10)  # Slightly smaller than square
                )
        except Exception as e:
            print(f"Error loading piece images: {e}")
            # Fallback to colored rectangles if images can't be loaded
            square_size = self.surface.get_width() // 8
            fallback_size = (square_size - 20, square_size - 20)
            
            # Create fallback surfaces
            wp_surface = pygame.Surface(fallback_size)
            wp_surface.fill((255, 255, 255))  # White
            pygame.draw.circle(wp_surface, (0, 0, 0), 
                             (fallback_size[0]//2, fallback_size[1]//2), 
                             min(fallback_size)//2, 2)  # Black border
            
            bp_surface = pygame.Surface(fallback_size)
            bp_surface.fill((0, 0, 0))  # Black
            
            self.piece_images['wp'] = wp_surface
            self.piece_images['bp'] = bp_surface
            
    def get_piece_image(self, piece_type, color):
        """Get the image for a chess piece."""
        key = color + piece_type  # e.g., 'wp' for white pawn
        return self.piece_images.get(key)
        
    def show_restart_prompt(self):
        """Show restart game prompt window."""
        # Create a small window in the center of the board
        window_width = 300
        window_height = 150
        x = (self.surface.get_width() - window_width) // 2
        y = (self.surface.get_height() - window_height) // 2
        
        # Draw semi-transparent background
        overlay = pygame.Surface((self.surface.get_width(), self.surface.get_height()))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(128)
        self.surface.blit(overlay, (0, 0))
        
        # Draw prompt window
        window = pygame.Surface((window_width, window_height))
        window.fill((240, 240, 240))  # Light gray background
        pygame.draw.rect(window, (100, 100, 100), window.get_rect(), 2)  # Border
        
        # Draw prompt text
        prompt_font = pygame.font.Font(None, 36)
        prompt_text = prompt_font.render("Restart Game?", True, (0, 0, 0))
        text_rect = prompt_text.get_rect(centerx=window_width//2, y=20)
        window.blit(prompt_text, text_rect)
        
        # Draw buttons
        button_width = 100
        button_height = 40
        yes_button = pygame.Surface((button_width, button_height))
        no_button = pygame.Surface((button_width, button_height))
        yes_button.fill((130, 200, 130))  # Green
        no_button.fill((200, 130, 130))   # Red
        
        # Add button text
        yes_text = prompt_font.render("Yes", True, (255, 255, 255))
        no_text = prompt_font.render("No", True, (255, 255, 255))
        yes_text_rect = yes_text.get_rect(center=(button_width//2, button_height//2))
        no_text_rect = no_text.get_rect(center=(button_width//2, button_height//2))
        yes_button.blit(yes_text, yes_text_rect)
        no_button.blit(no_text, no_text_rect)
        
        # Position buttons
        yes_pos = (window_width//4 - button_width//2, 80)
        no_pos = (3*window_width//4 - button_width//2, 80)
        window.blit(yes_button, yes_pos)
        window.blit(no_button, no_pos)
        
        # Blit window to screen
        self.surface.blit(window, (x, y))
        pygame.display.flip()
        
        # Store button rectangles for click detection
        yes_rect = pygame.Rect(x + yes_pos[0], y + yes_pos[1], button_width, button_height)
        no_rect = pygame.Rect(x + no_pos[0], y + no_pos[1], button_width, button_height)
        
        # Wait for user input
        waiting = True
        while waiting:
            for event in pygame.event.get():
                if event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_pos = event.pos
                    if yes_rect.collidepoint(mouse_pos):
                        return True
                    elif no_rect.collidepoint(mouse_pos):
                        return False
                elif event.type == pygame.QUIT:
                    return False
        return False
        
    def show_game_over_message(self, winner):
        """Show game over message with winner."""
        # Create a window in the center of the board
        window_width = 300
        window_height = 100
        x = (self.surface.get_width() - window_width) // 2
        y = (self.surface.get_height() - window_height) // 2
        
        # Draw semi-transparent background
        overlay = pygame.Surface((self.surface.get_width(), self.surface.get_height()))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(128)
        self.surface.blit(overlay, (0, 0))
        
        # Draw message window
        window = pygame.Surface((window_width, window_height))
        window.fill((240, 240, 240))  # Light gray background
        pygame.draw.rect(window, (100, 100, 100), window.get_rect(), 2)  # Border
        
        # Draw game over text
        game_font = pygame.font.Font(None, 36)
        winner_text = f"{'White' if winner == chess.WHITE else 'Black'} Wins!"
        text_surface = game_font.render(winner_text, True, (0, 0, 0))
        text_rect = text_surface.get_rect(center=(window_width//2, window_height//2))
        window.blit(text_surface, text_rect)
        
        # Blit window to screen
        self.surface.blit(window, (x, y))
        pygame.display.flip()
        
        # Wait for a moment to show the message
        pygame.time.wait(2000)  # Wait for 2 seconds

    def drawComponent(self):
        """Draw the complete game state."""
        self.surface.fill((255, 255, 255))
        
        # Draw squares and pieces
        for row in range(8):
            for col in range(8):
                x = col * self.square_size
                # Flip board view based on player color
                y = (7 - row) * self.square_size if self.playerColor == chess.WHITE else row * self.square_size
                square = chess.square(col, row)  # Use actual board coordinates
                color = self.LIGHT_SQUARE if (row + col) % 2 == 0 else self.DARK_SQUARE
                
                # Highlight selected square
                if square == self.selected_square:
                    color = self.SELECTED_COLOR
                # Highlight last move
                elif self.last_move and (chess.square_name(square) == self.last_move[:2] or 
                                       chess.square_name(square) == self.last_move[2:]):
                    color = self.LAST_MOVE_COLOR
                # Highlight valid moves
                elif self.selected_square is not None and any(
                    chess.square_name(square) == move[2:] for move in self.valid_moves):
                    color = self.VALID_MOVE_COLOR
                
                pygame.draw.rect(self.surface, color, (x, y, self.square_size, self.square_size))
                
                # Draw piece
                piece = self.board.board.piece_at(square)
                if piece:
                    piece_symbol = piece.symbol().lower()  # Always use lowercase for key
                    color_prefix = "w" if piece.color else "b"
                    piece_key = color_prefix + piece_symbol
                    piece_image = self.piece_images.get(piece_key)
                    if piece_image:
                        piece_x = x + (self.square_size - piece_image.get_width()) // 2
                        piece_y = y + (self.square_size - piece_image.get_height()) // 2
                        self.surface.blit(piece_image, (piece_x, piece_y))
        
        # Draw time and game info
        # Create a semi-transparent overlay for the info area
        info_overlay = pygame.Surface((self.surface.get_width(), 40))
        info_overlay.fill((240, 240, 240))
        info_overlay.set_alpha(200)
        self.surface.blit(info_overlay, (0, 0))
        
        # Create bottom info overlay
        bottom_overlay = pygame.Surface((self.surface.get_width(), 40))
        bottom_overlay.fill((240, 240, 240))
        bottom_overlay.set_alpha(200)
        bottom_y = self.surface.get_height() - 40
        self.surface.blit(bottom_overlay, (0, bottom_y))
        
        # Format times
        white_minutes = int(self.white_time // 60)
        white_seconds = int(self.white_time % 60)
        black_minutes = int(self.black_time // 60)
        black_seconds = int(self.black_time % 60)
        
        # Determine which color is at the bottom
        bottom_color = chess.BLACK if self.playerColor == chess.BLACK else chess.WHITE
        
        # Draw times based on board orientation
        if bottom_color == chess.WHITE:
            # White at bottom, Black at top
            # Top timer (Black)
            black_time_color = self.TIME_WARNING_COLOR if self.black_time < 60 else self.TEXT_COLOR
            black_time_text = f"Black: {black_minutes:02d}:{black_seconds:02d}"
            black_time_surface = self.font.render(black_time_text, True, black_time_color)
            self.surface.blit(black_time_surface, (10, 10))
            
            # Bottom timer (White)
            white_time_color = self.TIME_WARNING_COLOR if self.white_time < 60 else self.TEXT_COLOR
            white_time_text = f"White: {white_minutes:02d}:{white_seconds:02d}"
            white_time_surface = self.font.render(white_time_text, True, white_time_color)
            self.surface.blit(white_time_surface, (10, bottom_y + 10))
        else:
            # Black at bottom, White at top
            # Top timer (White)
            white_time_color = self.TIME_WARNING_COLOR if self.white_time < 60 else self.TEXT_COLOR
            white_time_text = f"White: {white_minutes:02d}:{white_seconds:02d}"
            white_time_surface = self.font.render(white_time_text, True, white_time_color)
            self.surface.blit(white_time_surface, (10, 10))
            
            # Bottom timer (Black)
            black_time_color = self.TIME_WARNING_COLOR if self.black_time < 60 else self.TEXT_COLOR
            black_time_text = f"Black: {black_minutes:02d}:{black_seconds:02d}"
            black_time_surface = self.font.render(black_time_text, True, black_time_color)
            self.surface.blit(black_time_surface, (10, bottom_y + 10))
        
        # Current turn (top center)
        turn_text = "Current Turn: White" if self.board.board.turn else "Current Turn: Black"
        turn_surface = self.font.render(turn_text, True, self.TEXT_COLOR)
        turn_rect = turn_surface.get_rect(centerx=self.surface.get_width() // 2, top=10)
        self.surface.blit(turn_surface, turn_rect)
        
        # If game is over, show winner
        if self.board.is_game_over():
            winner = self.board.get_winner()
            if winner is not None:
                self.show_game_over_message(winner)
        
        pygame.display.flip()
        
    def get_square_from_pos(self, pos):
        """Convert screen position to chess square."""
        x, y = pos
        if not (0 <= x < self.surface.get_width() and 0 <= y < self.surface.get_height()):
            return None
            
        col = x // self.square_size
        # Adjust row calculation based on board orientation
        if self.playerColor == chess.WHITE:
            row = 7 - (y // self.square_size)
        else:
            row = y // self.square_size
        
        if 0 <= col < 8 and 0 <= row < 8:
            return chess.square(col, row)
        return None

    def initialize_ai(self):
        """Initialize AI agent with current game state."""
        opponent_color = chess.BLACK if self.playerColor == chess.WHITE else chess.WHITE
        self.ai_agent = AIAgent(self.board.board, opponent_color, self.time)

    def drawPieces(self):
        """Draw all pawns on the board."""
        for square in chess.SQUARES:
            piece = self.board.board.piece_at(square)
            if piece is not None and piece.piece_type == chess.PAWN:
                col = chess.square_file(square)
                row = 7 - chess.square_rank(square)  # Flip for display
                x = col * self.square_size
                y = row * self.square_size
                
                if piece.color == chess.WHITE:
                    self.surface.blit(self.piece_images['wp'], (x, y))
                else:
                    self.surface.blit(self.piece_images['bp'], (x, y))

    def drawGameInfo(self):
        """Draw game information (time, current turn, etc.)."""
        info_surface = pygame.Surface((self.square_size * 8, 100))
        info_surface.fill((240, 240, 240))  # Light gray background
        
        # Draw time
        minutes = int(self.time / 60)
        seconds = int(self.time % 60)
        time_text = f"Time: {minutes:02d}:{seconds:02d}"
        time_surface = self.font.render(time_text, True, self.TEXT_COLOR)
        info_surface.blit(time_surface, (10, 10))
        
        # Draw current turn
        turn_text = "Current Turn: White" if self.board.board.turn else "Current Turn: Black"
        turn_surface = self.font.render(turn_text, True, self.TEXT_COLOR)
        info_surface.blit(turn_surface, (200, 10))
        
        # Draw player color
        if self.playerColor is not None:
            color_text = f"You are: {'White' if self.playerColor else 'Black'}"
            color_surface = self.font.render(color_text, True, self.TEXT_COLOR)
            info_surface.blit(color_surface, (10, 50))
        
        # Draw game state if game is over
        if self.board.is_game_over():
            winner = self.board.get_winner()
            if winner is not None:
                state_text = f"Game Over - {'White' if winner else 'Black'} wins!"
            else:
                state_text = "Game Over - Draw!"
            state_surface = self.font.render(state_text, True, (255, 0, 0))  # Red text
            info_surface.blit(state_surface, (200, 50))
        
        # Draw the info surface below the board
        self.surface.blit(info_surface, (0, self.square_size * 8))

    def handle_click(self, pos):
        """Handle mouse click events and return move if valid."""
        # If game is over, ignore all clicks
        if self.board.is_game_over():
            return None
            
        square = self.get_square_from_pos(pos)
        if square is None:
            return None

        # Get current turn
        current_turn = self.board.board.turn
        
        # In Human vs AI mode, only allow moves for the player's color
        if not self.allow_both_colors and current_turn != self.playerColor:
            return None
        
        # If no square is selected, select a square with a piece of the current turn
        if self.selected_square is None:
            piece = self.board.board.piece_at(square)
            if piece and piece.color == current_turn:  # Check if piece belongs to current player
                self.selected_square = square
                # Get valid moves for the selected piece
                self.valid_moves = [move for move in self.board.get_legal_moves() 
                                  if chess.square_name(square) == move[:2]]
                self.drawComponent()
            return None

        # If a square is already selected
        else:
            # Create the move string
            move = chess.square_name(self.selected_square) + chess.square_name(square)
            
            # Clear selection
            self.selected_square = None
            self.valid_moves = []
            self.drawComponent()

            # Check if move is legal
            if move[:4] in self.board.get_legal_moves():
                # Check for promotion
                target_rank = chess.square_rank(chess.parse_square(move[2:]))
                if ((current_turn == chess.WHITE and target_rank == 7) or
                    (current_turn == chess.BLACK and target_rank == 0)):
                    return "Win"  # Signal a win if pawn reaches the opposite end
                return move[:4]  # Return basic move
            
            return None

    def handle_restart(self):
        """Handle game restart."""
        if not self.restart_prompt_shown:
            self.restart_prompt_shown = True
            restart = self.show_restart_prompt()
            self.restart_prompt_shown = False
            return restart
        return False 