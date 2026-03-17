import chess
import random
import time

PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,
}


class AIAgent:
    """Generic full-chess AI with iterative deepening alpha-beta."""

    def __init__(self, board, color, time_limit):
        self.board = board
        self.color = color
        self.time_limit = max(1, int(time_limit))
        self.max_depth = 4

    def evaluate_position(self, board):
        if board.is_game_over():
            outcome = board.board.outcome(claim_draw=True)
            if outcome is None or outcome.winner is None:
                return 0
            return 100000 if outcome.winner == self.color else -100000

        score = 0
        for piece_type, value in PIECE_VALUES.items():
            score += len(board.board.pieces(piece_type, self.color)) * value
            score -= len(board.board.pieces(piece_type, not self.color)) * value

        # Mobility and king safety proxy.
        side_to_move = board.get_current_player()
        mobility = len(board.get_legal_moves())
        score += mobility if side_to_move == self.color else -mobility
        if board.board.is_check():
            score -= 25 if side_to_move == self.color else -25
        return score

    def _ordered_moves(self, board):
        def move_key(move):
            score = 0
            if board.board.is_capture(move):
                score += 50
            if move.promotion:
                score += 80
            if board.board.gives_check(move):
                score += 40
            return -score

        moves = list(board.board.legal_moves)
        moves.sort(key=move_key)
        return moves

    def _alpha_beta(self, board, depth, alpha, beta, maximizing, cutoff_time):
        if time.time() >= cutoff_time:
            raise TimeoutError

        if depth == 0 or board.is_game_over():
            return self.evaluate_position(board), None

        best_move = None
        moves = self._ordered_moves(board)
        if not moves:
            return self.evaluate_position(board), None

        if maximizing:
            best_eval = -float("inf")
            for move in moves:
                board_copy = board.copy()
                board_copy.make_move(move.uci())
                eval_score, _ = self._alpha_beta(
                    board_copy, depth - 1, alpha, beta, False, cutoff_time
                )
                if eval_score > best_eval:
                    best_eval = eval_score
                    best_move = move
                alpha = max(alpha, best_eval)
                if beta <= alpha:
                    break
            return best_eval, best_move

        best_eval = float("inf")
        for move in moves:
            board_copy = board.copy()
            board_copy.make_move(move.uci())
            eval_score, _ = self._alpha_beta(
                board_copy, depth - 1, alpha, beta, True, cutoff_time
            )
            if eval_score < best_eval:
                best_eval = eval_score
                best_move = move
            beta = min(beta, best_eval)
            if beta <= alpha:
                break
        return best_eval, best_move

    def get_best_move(self):
        legal = list(self.board.board.legal_moves)
        if not legal:
            return None

        # Soft cutoff to avoid flagging.
        cutoff_time = time.time() + (self.time_limit * 0.2)
        best_move = random.choice(legal)
        maximizing = self.board.get_current_player() == self.color

        for depth in range(1, self.max_depth + 1):
            try:
                _, candidate = self._alpha_beta(
                    self.board.copy(),
                    depth,
                    -float("inf"),
                    float("inf"),
                    maximizing,
                    cutoff_time,
                )
                if candidate is not None:
                    best_move = candidate
            except TimeoutError:
                break
        return best_move