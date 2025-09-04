import chess
import random
import math
import time
from copy import deepcopy

class Node:
    def __init__(self, board, parent=None, move=None):
        self.board = board
        self.parent = parent
        self.move = move  # Move that led to this node
        self.children = []
        self.wins = 0
        self.visits = 0
        self.untried_moves = list(board.get_legal_moves())

class AIAgent:
    def __init__(self, board, color, time_limit):
        self.board = board
        self.color = color
        self.time_limit = time_limit
        self.nodes_evaluated = 0
        self.transposition_table = {}
        
        # Evaluation weights
        self.PAWN_VALUE = 100
        self.CENTER_BONUS = 20
        self.ADVANCEMENT_BONUS = 10
        self.CHAIN_BONUS = 15
        self.PASSED_PAWN_BONUS = 30
        self.ISOLATED_PAWN_PENALTY = -20
        self.BLOCKED_PAWN_PENALTY = -10
        
        # Center squares for evaluation
        self.CENTER_SQUARES = [27, 28, 35, 36]  # e4, d4, e5, d5
        self.EXTENDED_CENTER = [18, 19, 20, 21, 26, 29, 34, 37, 42, 43, 44, 45]
        
        # Position values for pawns
        self.POSITION_VALUES = [
            0,  0,  0,  0,  0,  0,  0,  0,
            50, 50, 50, 50, 50, 50, 50, 50,
            10, 10, 20, 30, 30, 20, 10, 10,
            5,  5, 10, 25, 25, 10,  5,  5,
            0,  0,  0, 20, 20,  0,  0,  0,
            5, -5,-10,  0,  0,-10, -5,  5,
            5, 10, 10,-20,-20, 10, 10,  5,
            0,  0,  0,  0,  0,  0,  0,  0
        ]

    def evaluate_position(self, board):
        """Enhanced position evaluation."""
        if board.is_game_over():
            winner = board.get_winner()
            if winner == self.color:
                return float('inf')
            elif winner is None:
                return 0
            else:
                return float('-inf')

        score = 0
        
        # Material and basic position evaluation
        for square in chess.SQUARES:
            piece = board.board.piece_at(square)
            if piece and piece.piece_type == chess.PAWN:
                value = self.PAWN_VALUE + self.POSITION_VALUES[square]
                rank = chess.square_rank(square)
                
                if piece.color == self.color:
                    score += value
                    # Strongly prioritize pawns near promotion
                    if self.color == chess.WHITE:
                        # Exponential bonus for rank advancement
                        rank_bonus = 2 ** rank * self.ADVANCEMENT_BONUS
                        # Huge bonus for pawns one step from promotion
                        if rank == 6:  # One step away from promotion
                            rank_bonus = 10000  # Very high bonus to ensure it's chosen
                        score += rank_bonus
                    else:
                        # Same for black pawns
                        rank_bonus = 2 ** (7 - rank) * self.ADVANCEMENT_BONUS
                        if rank == 1:  # One step away from promotion
                            rank_bonus = 10000
                        score += rank_bonus
                        
                    # Center control bonus
                    if square in self.CENTER_SQUARES:
                        score += self.CENTER_BONUS
                    elif square in self.EXTENDED_CENTER:
                        score += self.CENTER_BONUS // 2
                        
                    # Passed pawn bonus (increased for advanced pawns)
                    if self._is_passed_pawn(board, square, piece.color):
                        if self.color == chess.WHITE:
                            score += self.PASSED_PAWN_BONUS * (rank + 1) * 2
                        else:
                            score += self.PASSED_PAWN_BONUS * (8 - rank) * 2
                        
                    # Pawn chain bonus
                    if self._is_part_of_chain(board, square, piece.color):
                        score += self.CHAIN_BONUS
                        
                    # Isolated pawn penalty
                    if self._is_isolated_pawn(board, square, piece.color):
                        score += self.ISOLATED_PAWN_PENALTY
                        
                    # Blocked pawn penalty (reduced for advanced pawns)
                    if self._is_blocked_pawn(board, square, piece.color):
                        if (self.color == chess.WHITE and rank >= 5) or \
                           (self.color == chess.BLACK and rank <= 2):
                            score += self.BLOCKED_PAWN_PENALTY // 2  # Reduced penalty for advanced pawns
                        else:
                            score += self.BLOCKED_PAWN_PENALTY
                else:
                    score -= value
                    # Apply same evaluations for opponent
                    if self.color == chess.WHITE:
                        rank_bonus = 2 ** (7 - rank) * self.ADVANCEMENT_BONUS
                        if rank == 1:  # One step away from promotion
                            rank_bonus = 10000
                        score -= rank_bonus
                    else:
                        rank_bonus = 2 ** rank * self.ADVANCEMENT_BONUS
                        if rank == 6:  # One step away from promotion
                            rank_bonus = 10000
                        score -= rank_bonus
                        
                    if square in self.CENTER_SQUARES:
                        score -= self.CENTER_BONUS
                    elif square in self.EXTENDED_CENTER:
                        score -= self.CENTER_BONUS // 2
                        
                    if self._is_passed_pawn(board, square, piece.color):
                        if piece.color == chess.WHITE:
                            score -= self.PASSED_PAWN_BONUS * (rank + 1) * 2
                        else:
                            score -= self.PASSED_PAWN_BONUS * (8 - rank) * 2
                        
                    if self._is_part_of_chain(board, square, piece.color):
                        score -= self.CHAIN_BONUS
                        
                    if self._is_isolated_pawn(board, square, piece.color):
                        score -= self.ISOLATED_PAWN_PENALTY
                        
                    if self._is_blocked_pawn(board, square, piece.color):
                        if (piece.color == chess.WHITE and rank >= 5) or \
                           (piece.color == chess.BLACK and rank <= 2):
                            score -= self.BLOCKED_PAWN_PENALTY // 2
                        else:
                            score -= self.BLOCKED_PAWN_PENALTY

        # Mobility evaluation (reduced importance compared to promotion)
        mobility = len(board.get_legal_moves())
        if board.get_current_player() == self.color:
            score += mobility * 2  # Reduced from 5 to 2
        else:
            score -= mobility * 2

        return score

    def _is_passed_pawn(self, board, square, color):
        """Check if a pawn is passed (no enemy pawns ahead)."""
        file = chess.square_file(square)
        rank = chess.square_rank(square)
        
        if color == chess.WHITE:
            target_ranks = range(rank + 1, 8)
        else:
            target_ranks = range(rank - 1, -1, -1)
            
        for r in target_ranks:
            for f in [file - 1, file, file + 1]:
                if 0 <= f <= 7:
                    target_square = chess.square(f, r)
                    piece = board.board.piece_at(target_square)
                    if piece and piece.piece_type == chess.PAWN and piece.color != color:
                        return False
        return True

    def _is_part_of_chain(self, board, square, color):
        """Check if a pawn is part of a pawn chain."""
        file = chess.square_file(square)
        rank = chess.square_rank(square)
        
        # Check diagonally adjacent squares
        for f in [file - 1, file + 1]:
            if 0 <= f <= 7:
                if color == chess.WHITE:
                    r = rank - 1
                else:
                    r = rank + 1
                    
                if 0 <= r <= 7:
                    adj_square = chess.square(f, r)
                    piece = board.board.piece_at(adj_square)
                    if piece and piece.piece_type == chess.PAWN and piece.color == color:
                        return True
        return False

    def _is_isolated_pawn(self, board, square, color):
        """Check if a pawn is isolated (no friendly pawns on adjacent files)."""
        file = chess.square_file(square)
        
        for f in [file - 1, file + 1]:
            if 0 <= f <= 7:
                for r in range(8):
                    adj_square = chess.square(f, r)
                    piece = board.board.piece_at(adj_square)
                    if piece and piece.piece_type == chess.PAWN and piece.color == color:
                        return False
        return True

    def _is_blocked_pawn(self, board, square, color):
        """Check if a pawn is blocked by enemy pieces."""
        file = chess.square_file(square)
        rank = chess.square_rank(square)
        
        if color == chess.WHITE:
            if rank < 7:
                front_square = chess.square(file, rank + 1)
        else:
            if rank > 0:
                front_square = chess.square(file, rank - 1)
                
        piece = board.board.piece_at(front_square)
        return piece is not None

    def get_best_move(self):
        """Get the best move using alpha-beta search with iterative deepening."""
        print("AI: Starting move selection...")
        start_time = time.time()
        legal_moves = self.board.get_legal_moves()
        
        if not legal_moves:
            return None
            
        # First, check for immediate winning moves
        for move_uci in legal_moves:
            move = chess.Move.from_uci(move_uci)
            to_rank = chess.square_rank(move.to_square)
            if ((self.color == chess.WHITE and to_rank == 7) or
                (self.color == chess.BLACK and to_rank == 0)):
                print("AI: Found immediate winning move:", move_uci)
                return move
        
        # If no immediate win, proceed with normal search
        best_move = None
        max_depth = 4  # Start with reasonable depth
        
        try:
            # Iterative deepening
            for depth in range(1, max_depth + 1):
                print(f"AI: Searching at depth {depth}")
                move = self.alpha_beta_search(depth, start_time)
                if move:
                    best_move = move
                    print(f"AI: Found move at depth {depth}: {best_move}")
                
                # Check if we have enough time for next iteration
                elapsed = time.time() - start_time
                if elapsed > self.time_limit * 0.3:  # Use 30% of time limit as cutoff
                    break
                    
        except TimeoutError:
            print("AI: Search stopped due to time limit")
            
        if best_move and best_move in legal_moves:
            return chess.Move.from_uci(best_move)
        elif legal_moves:  # Fallback to random move if necessary
            return chess.Move.from_uci(random.choice(legal_moves))
            
        return None

    def alpha_beta_search(self, depth, start_time):
        """Alpha-Beta search with move ordering."""
        alpha = float('-inf')
        beta = float('inf')
        best_move = None
        
        # Get and sort moves
        moves = self.get_ordered_moves()
        
        for move in moves:
            if time.time() - start_time > self.time_limit * 0.3:
                raise TimeoutError
                
            board_copy = self.board.copy()
            board_copy.move_piece(move)
            score = -self._alpha_beta(board_copy, depth - 1, -beta, -alpha, start_time)
            
            if score > alpha:
                alpha = score
                best_move = move
                
        return best_move

    def _alpha_beta(self, board, depth, alpha, beta, start_time):
        """Alpha-Beta helper function with quiescence search."""
        if time.time() - start_time > self.time_limit * 0.3:
            raise TimeoutError
            
        if depth == 0:
            return self.quiescence_search(board, alpha, beta, start_time)
            
        if board.is_game_over():
            return self.evaluate_position(board)
            
        for move in self.get_ordered_moves_for_board(board):
            board_copy = board.copy()
            board_copy.move_piece(move)
            score = -self._alpha_beta(board_copy, depth - 1, -beta, -alpha, start_time)
            
            if score >= beta:
                return beta
            alpha = max(alpha, score)
            
        return alpha

    def quiescence_search(self, board, alpha, beta, start_time, depth=3):
        """Quiescence search to handle tactical positions."""
        if time.time() - start_time > self.time_limit * 0.3:
            raise TimeoutError
            
        stand_pat = self.evaluate_position(board)
        if depth == 0:
            return stand_pat
            
        if stand_pat >= beta:
            return beta
            
        alpha = max(alpha, stand_pat)
        
        # Only consider captures and promotions
        for move in self.get_ordered_moves_for_board(board, captures_only=True):
            board_copy = board.copy()
            board_copy.move_piece(move)
            score = -self.quiescence_search(board_copy, -beta, -alpha, start_time, depth - 1)
            
            if score >= beta:
                return beta
            alpha = max(alpha, score)
            
        return alpha

    def get_ordered_moves(self):
        """Get moves ordered by preliminary evaluation."""
        moves = []
        for move_uci in self.board.get_legal_moves():
            score = self.evaluate_move_uci(move_uci)
            moves.append((-score, move_uci))  # Negative score for descending sort
        
        # Sort moves by score in descending order
        moves.sort()  # Will sort by the first element of tuple (-score)
        return [move for _, move in moves]

    def get_ordered_moves_for_board(self, board, captures_only=False):
        """Get ordered moves for a given board position."""
        moves = []
        for move_uci in board.get_legal_moves():
            if not captures_only or self._is_capture(board, move_uci):
                score = self.evaluate_move_uci(move_uci)
                moves.append((-score, move_uci))  # Negative score for descending sort
        
        moves.sort()  # Will sort by the first element of tuple (-score)
        return [move for _, move in moves]

    def evaluate_move_uci(self, move_uci):
        """Preliminary move evaluation for move ordering using UCI string."""
        score = 0
        move = chess.Move.from_uci(move_uci)
        from_square = move.from_square
        to_square = move.to_square
        
        # Check for immediate win (pawn reaching the opposite rank)
        piece = self.board.board.piece_at(from_square)
        if piece and piece.piece_type == chess.PAWN:
            to_rank = chess.square_rank(to_square)
            if ((self.color == chess.WHITE and to_rank == 7) or
                (self.color == chess.BLACK and to_rank == 0)):
                return float('inf')  # Highest possible score for winning moves
        
        # Prioritize captures
        if self._is_capture(self.board, move_uci):
            score += 1000
            
        # Prioritize promotions and moves towards promotion
        if move.promotion:
            score += 2000
            
        # Strong bonus for advancement (especially in endgame)
        if piece and piece.color == self.color:
            if self.color == chess.WHITE:
                # Exponential bonus for rank advancement
                score += (10 ** chess.square_rank(to_square))
            else:
                score += (10 ** (7 - chess.square_rank(to_square)))
            
            # Extra bonus for passed pawns
            if self._is_passed_pawn(self.board, from_square, self.color):
                if self.color == chess.WHITE:
                    score += (10 ** chess.square_rank(to_square)) * 2
                else:
                    score += (10 ** (7 - chess.square_rank(to_square))) * 2
                
        # Bonus for center control (less important than winning)
        if to_square in self.CENTER_SQUARES:
            score += 50
        elif to_square in self.EXTENDED_CENTER:
            score += 25
                
        return score

    def _is_capture(self, board, move_uci):
        """Check if a move is a capture using UCI string."""
        move = chess.Move.from_uci(move_uci)
        return board.board.piece_at(move.to_square) is not None

    def mcts_search(self, time_limit):
        """Monte Carlo Tree Search implementation."""
        root = Node(self.board.copy())
        start_time = time.time()
        
        while time.time() - start_time < time_limit:
            node = self._select(root)
            if not node.board.is_game_over():
                node = self._expand(node)
            simulation_result = self._simulate(node)
            self._backpropagate(node, simulation_result)
            
        # Select best move
        if root.children:
            best_child = max(root.children, key=lambda c: c.visits)
            return best_child.move
        return None

    def _select(self, node):
        """Select a node to expand using UCT."""
        while node.untried_moves == [] and node.children != []:
            node = self._uct_select(node)
        return node

    def _uct_select(self, node):
        """Select child with highest UCT value."""
        exploration = 1.41  # UCT exploration parameter
        
        def uct_value(n):
            if n.visits == 0:
                return float('inf')
            return (n.wins / n.visits) + exploration * math.sqrt(math.log(n.parent.visits) / n.visits)
            
        return max(node.children, key=uct_value)

    def _expand(self, node):
        """Expand node by adding a child."""
        if node.untried_moves:
            move = random.choice(node.untried_moves)
            node.untried_moves.remove(move)
            
            new_board = node.board.copy()
            new_board.move_piece(move)
            
            child = Node(new_board, parent=node, move=move)
            node.children.append(child)
            return child
        return node

    def _simulate(self, node):
        """Simulate a random game from node."""
        board = node.board.copy()
        
        while not board.is_game_over():
            moves = board.get_legal_moves()
            if not moves:
                break
            move = random.choice(moves)
            board.move_piece(move)
            
        winner = board.get_winner()
        return 1 if winner == self.color else 0 if winner is None else -1

    def _backpropagate(self, node, result):
        """Backpropagate simulation result."""
        while node is not None:
            node.visits += 1
            node.wins += result
            node = node.parent

    def _is_forcing_move(self, move):
        """Check if move is forcing (captures or promotion)."""
        board_copy = self.board.copy()
        board_copy.board.push(move)
        is_forcing = (
            self.board.board.is_capture(move) or
            chess.square_rank(move.to_square) in [0, 7]
        )
        return is_forcing 