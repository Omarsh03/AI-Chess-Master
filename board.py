import chess
import copy

class ChessBoard:
    def __init__(self, board=None):
        # Initialize standard chess board
        if board is None:
            self.board = chess.Board()
            self.board.clear_board()
        else:
            self.board = board
        self.cached_legal_moves = None  # Cache for legal moves

    def __deepcopy__(self, memo):
        """Support for deepcopy."""
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        result.board = chess.Board(self.board.fen())
        result.cached_legal_moves = None
        return result

    def setup_board(self, setup_command):
        """
        Setup board from command like: "Setup Wa2 Wb2 Wc2 Wd2 We2 Wf2 Wg2 Wh2 Ba7 Bb7 Bc7 Bd7 Be7 Bf7 Bg7 Bh7"
        W = White pawn, B = Black pawn, followed by position
        """
        # Clear any existing pieces
        self.board.clear_board()
        
        # Parse the setup command
        pieces = setup_command.split()[1:]  # Skip the "Setup" word
        for piece in pieces:
            color = chess.WHITE if piece[0] == 'W' else chess.BLACK
            position = chess.parse_square(piece[1:])  # Convert algebraic notation to square number
            # Place pawn at the position
            self.board.set_piece_at(position, chess.Piece(chess.PAWN, color))

    def move_piece(self, move_str):
        """Make a move on the board using chess library's move validation."""
        try:
            # Ensure move string is just the basic move (4 characters)
            basic_move_str = move_str[:4]
            from_square = chess.parse_square(basic_move_str[:2])
            to_square = chess.parse_square(basic_move_str[2:])
            
            # Create a basic move
            move = chess.Move(from_square, to_square)
            
            # Check if it's a valid pawn move
            piece = self.board.piece_at(from_square)
            if piece and piece.piece_type == chess.PAWN:
                # Get all legal moves for this piece
                legal_moves = [m for m in self.board.legal_moves 
                             if m.from_square == from_square and m.to_square == to_square]
                
                if legal_moves:
                    # Use the first legal move (which might be an en passant)
                    legal_move = legal_moves[0]
                    # Make the move using chess library's move application
                    self.board.push(legal_move)
                    # Since we don't want promotions, revert any promotion
                    if legal_move.promotion:
                        # Get the last moved piece and replace it with a pawn
                        self.board.pop()  # Undo the promotion move
                        # Remove the piece from the source square
                        self.board.remove_piece_at(from_square)
                        # Place a pawn on the target square
                        self.board.set_piece_at(to_square, piece)
                        # Update the turn
                        self.board.turn = not self.board.turn
                    self.cached_legal_moves = None  # Invalidate cache
                    return True
            return False
        except ValueError:
            return False

    def get_legal_moves(self):
        """Get all legal moves using chess library."""
        if self.cached_legal_moves is None:
            # Filter moves to only include pawn moves without promotion
            legal_moves = []
            for move in self.board.legal_moves:
                piece = self.board.piece_at(move.from_square)
                if piece and piece.piece_type == chess.PAWN:
                    # Just use the basic move notation without promotion
                    move_str = move.uci()[:4]  # Only take the first 4 characters (from-to squares)
                    if move_str not in legal_moves:  # Avoid duplicates
                        legal_moves.append(move_str)
            self.cached_legal_moves = legal_moves
        return self.cached_legal_moves

    def is_game_over(self):
        """Check if the game is over using chess library and pawn-specific rules."""
        # Check for pawns reaching the opposite end - immediate win condition
        for square in chess.SQUARES:
            piece = self.board.piece_at(square)
            if piece and piece.piece_type == chess.PAWN:
                rank = chess.square_rank(square)
                if (piece.color == chess.WHITE and rank == 7) or \
                   (piece.color == chess.BLACK and rank == 0):
                    return True
        
        # Check for no legal moves for pawns
        has_legal_pawn_moves = False
        for move in self.board.legal_moves:
            piece = self.board.piece_at(move.from_square)
            if piece and piece.piece_type == chess.PAWN:
                has_legal_pawn_moves = True
                break
        if not has_legal_pawn_moves:
            return True
        
        # Check if all pawns of one side are captured
        white_pawns = list(self.board.pieces(chess.PAWN, chess.WHITE))
        black_pawns = list(self.board.pieces(chess.PAWN, chess.BLACK))
        if not white_pawns or not black_pawns:
            return True
            
        return False

    def get_winner(self):
        """Determine the winner if the game is over."""
        if not self.is_game_over():
            return None
            
        # Check for pawns reaching the opposite end - highest priority win condition
        for square in chess.SQUARES:
            piece = self.board.piece_at(square)
            if piece and piece.piece_type == chess.PAWN:
                rank = chess.square_rank(square)
                if piece.color == chess.WHITE and rank == 7:
                    return chess.WHITE
                if piece.color == chess.BLACK and rank == 0:
                    return chess.BLACK
        
        # Check for all pawns captured
        white_pawns = list(self.board.pieces(chess.PAWN, chess.WHITE))
        black_pawns = list(self.board.pieces(chess.PAWN, chess.BLACK))
        if not white_pawns:
            return chess.BLACK
        if not black_pawns:
            return chess.WHITE
        
        # If no moves available, current player loses
        if not list(self.board.legal_moves):
            return not self.board.turn
            
        return None

    def get_current_player(self):
        """Get the current player's color."""
        return self.board.turn

    def get_board_state(self):
        """Get a string representation of the board."""
        return str(self.board)

    def copy(self):
        """Create a copy of the board."""
        return ChessBoard(chess.Board(self.board.fen())) 