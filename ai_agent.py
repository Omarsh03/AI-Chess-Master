import chess
import random
import time

MATE_SCORE = 100000
INF = 10**9

PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,
}

TT_EXACT = 0
TT_LOWER = 1
TT_UPPER = 2

OPENING_BOOK_LINES = [
    # Open games / Italian / Ruy Lopez
    ("e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "f8c5", "c2c3", "g8f6", "d2d3"),
    ("e2e4", "e7e5", "g1f3", "b8c6", "f1b5", "a7a6", "b5a4", "g8f6", "e1g1"),
    ("e2e4", "e7e5", "g1f3", "b8c6", "d2d4", "e5d4", "f3d4", "f8c5"),
    # Sicilian
    ("e2e4", "c7c5", "g1f3", "d7d6", "d2d4", "c5d4", "f3d4", "g8f6", "b1c3"),
    ("e2e4", "c7c5", "b1c3", "b8c6", "g2g3", "g7g6", "f1g2"),
    # French
    ("e2e4", "e7e6", "d2d4", "d7d5", "b1c3", "g8f6", "e4e5", "f6d7"),
    # Caro-Kann
    ("e2e4", "c7c6", "d2d4", "d7d5", "b1c3", "d5e4", "c3e4", "c8f5"),
    # Queen's Gambit / Declined / Slav
    ("d2d4", "d7d5", "c2c4", "e7e6", "b1c3", "g8f6", "c1g5"),
    ("d2d4", "d7d5", "c2c4", "c7c6", "g1f3", "g8f6", "b1c3"),
    # Indian defenses
    ("d2d4", "g8f6", "c2c4", "g7g6", "b1c3", "f8g7", "e2e4", "d7d6"),
    ("d2d4", "g8f6", "c2c4", "e7e6", "g1f3", "b7b6", "g2g3"),
    # English / Réti setups
    ("c2c4", "e7e5", "b1c3", "g8f6", "g2g3", "d7d5"),
    ("g1f3", "d7d5", "c2c4", "e7e6", "g2g3", "g8f6"),
]


def _mk_pst(values):
    return values


PAWN_PST = _mk_pst(
    [
        0, 0, 0, 0, 0, 0, 0, 0,
        60, 60, 60, 70, 70, 60, 60, 60,
        24, 24, 34, 46, 46, 34, 24, 24,
        8, 8, 18, 28, 28, 18, 8, 8,
        0, 0, 8, 20, 20, 8, 0, 0,
        4, -2, -6, 0, 0, -6, -2, 4,
        6, 8, 8, -18, -18, 8, 8, 6,
        0, 0, 0, 0, 0, 0, 0, 0,
    ]
)
KNIGHT_PST = _mk_pst(
    [
        -50, -40, -30, -30, -30, -30, -40, -50,
        -40, -20, 0, 0, 0, 0, -20, -40,
        -30, 0, 10, 15, 15, 10, 0, -30,
        -30, 5, 15, 20, 20, 15, 5, -30,
        -30, 0, 15, 20, 20, 15, 0, -30,
        -30, 5, 10, 15, 15, 10, 5, -30,
        -40, -20, 0, 5, 5, 0, -20, -40,
        -50, -40, -30, -30, -30, -30, -40, -50,
    ]
)
BISHOP_PST = _mk_pst(
    [
        -20, -10, -10, -10, -10, -10, -10, -20,
        -10, 5, 0, 0, 0, 0, 5, -10,
        -10, 10, 10, 10, 10, 10, 10, -10,
        -10, 0, 10, 10, 10, 10, 0, -10,
        -10, 5, 5, 10, 10, 5, 5, -10,
        -10, 0, 5, 10, 10, 5, 0, -10,
        -10, 0, 0, 0, 0, 0, 0, -10,
        -20, -10, -10, -10, -10, -10, -10, -20,
    ]
)
ROOK_PST = _mk_pst(
    [
        0, 0, 5, 10, 10, 5, 0, 0,
        -5, 0, 0, 0, 0, 0, 0, -5,
        -5, 0, 0, 0, 0, 0, 0, -5,
        -5, 0, 0, 0, 0, 0, 0, -5,
        -5, 0, 0, 0, 0, 0, 0, -5,
        -5, 0, 0, 0, 0, 0, 0, -5,
        5, 10, 10, 10, 10, 10, 10, 5,
        0, 0, 0, 0, 0, 0, 0, 0,
    ]
)
QUEEN_PST = _mk_pst(
    [
        -20, -10, -10, -5, -5, -10, -10, -20,
        -10, 0, 0, 0, 0, 0, 0, -10,
        -10, 0, 5, 5, 5, 5, 0, -10,
        -5, 0, 5, 5, 5, 5, 0, -5,
        0, 0, 5, 5, 5, 5, 0, -5,
        -10, 5, 5, 5, 5, 5, 0, -10,
        -10, 0, 5, 0, 0, 0, 0, -10,
        -20, -10, -10, -5, -5, -10, -10, -20,
    ]
)
KING_MID_PST = _mk_pst(
    [
        -30, -40, -40, -50, -50, -40, -40, -30,
        -30, -40, -40, -50, -50, -40, -40, -30,
        -30, -40, -40, -50, -50, -40, -40, -30,
        -30, -40, -40, -50, -50, -40, -40, -30,
        -20, -30, -30, -40, -40, -30, -30, -20,
        -10, -20, -20, -20, -20, -20, -20, -10,
        20, 20, -5, -5, -5, -5, 20, 20,
        20, 30, 10, 0, 0, 10, 30, 20,
    ]
)
KING_END_PST = _mk_pst(
    [
        -50, -40, -30, -20, -20, -30, -40, -50,
        -30, -20, -10, 0, 0, -10, -20, -30,
        -30, -10, 20, 30, 30, 20, -10, -30,
        -30, -10, 30, 40, 40, 30, -10, -30,
        -30, -10, 30, 40, 40, 30, -10, -30,
        -30, -10, 20, 30, 30, 20, -10, -30,
        -30, -30, 0, 0, 0, 0, -30, -30,
        -50, -30, -30, -30, -30, -30, -30, -50,
    ]
)


PST_MAP = {
    chess.PAWN: PAWN_PST,
    chess.KNIGHT: KNIGHT_PST,
    chess.BISHOP: BISHOP_PST,
    chess.ROOK: ROOK_PST,
    chess.QUEEN: QUEEN_PST,
}


class AIAgent:
    """Stronger chess AI: negamax, TT, quiescence, better eval."""

    def __init__(self, board, color, time_limit):
        self.board = board
        self.color = color
        self.time_limit = max(1, int(time_limit))
        self.tt = {}
        self.killers = {}
        self.nodes = 0
        self.cutoff_time = 0.0

    def _is_endgame(self, board):
        queens = len(board.pieces(chess.QUEEN, chess.WHITE)) + len(board.pieces(chess.QUEEN, chess.BLACK))
        minors_majors = 0
        for pt in (chess.KNIGHT, chess.BISHOP, chess.ROOK):
            minors_majors += len(board.pieces(pt, chess.WHITE))
            minors_majors += len(board.pieces(pt, chess.BLACK))
        return queens == 0 or minors_majors <= 4

    def _max_search_depth(self, board):
        n = len(board.piece_map())
        if n <= 6:
            return 15
        if n <= 10:
            return 12
        if n <= 16:
            return 9
        if n <= 24:
            return 8
        return 7

    def _check_timeout(self):
        self.nodes += 1
        if (self.nodes & 1023) == 0 and time.time() >= self.cutoff_time:
            raise TimeoutError

    def _board_key(self, board):
        return (
            board.board_fen(),
            board.turn,
            board.castling_rights,
            board.ep_square,
            board.halfmove_clock,
        )

    def _material_score(self, board):
        score = 0
        for piece_type, value in PIECE_VALUES.items():
            score += len(board.pieces(piece_type, self.color)) * value
            score -= len(board.pieces(piece_type, not self.color)) * value
        return score

    def _hanging_penalty(self, board, side):
        penalty = 0
        enemy = not side
        for piece_type, value in PIECE_VALUES.items():
            if piece_type == chess.KING:
                continue
            for sq in board.pieces(piece_type, side):
                attackers = len(board.attackers(enemy, sq))
                if attackers == 0:
                    continue
                defenders = len(board.attackers(side, sq))
                if defenders == 0:
                    penalty += int(value * 0.48)
                elif attackers > defenders and value >= PIECE_VALUES[chess.BISHOP]:
                    penalty += int(value * 0.18)
        return penalty

    def _pst_score(self, board):
        score = 0
        endgame = self._is_endgame(board)
        for piece_type, table in PST_MAP.items():
            for sq in board.pieces(piece_type, self.color):
                score += table[sq]
            for sq in board.pieces(piece_type, not self.color):
                score -= table[chess.square_mirror(sq)]

        my_king = board.king(self.color)
        opp_king = board.king(not self.color)
        if my_king is not None:
            score += (KING_END_PST if endgame else KING_MID_PST)[my_king]
        if opp_king is not None:
            table = KING_END_PST if endgame else KING_MID_PST
            score -= table[chess.square_mirror(opp_king)]
        return score

    def _evaluate(self, board):
        if board.is_game_over(claim_draw=True):
            outcome = board.outcome(claim_draw=True)
            if outcome is None or outcome.winner is None:
                return 0
            root_score = MATE_SCORE if outcome.winner == self.color else -MATE_SCORE
            return root_score if board.turn == self.color else -root_score

        score = self._material_score(board)
        score += self._pst_score(board)
        score -= self._hanging_penalty(board, self.color)
        score += self._hanging_penalty(board, not self.color)

        mobility = board.legal_moves.count()
        score += mobility * 2 if board.turn == self.color else -mobility * 2

        if board.is_check():
            score += -28 if board.turn == self.color else 28

        if board.can_claim_threefold_repetition() or board.can_claim_fifty_moves():
            if score > 140:
                score -= 420
            elif score < -140:
                score += 120
        elif board.is_repetition(2):
            if score > 120:
                score -= 120

        # Negamax expects score from side-to-move perspective.
        return score if board.turn == self.color else -score

    def _capture_order_score(self, board, move):
        if not board.is_capture(move):
            return 0
        if board.is_en_passant(move):
            victim_value = PIECE_VALUES[chess.PAWN]
        else:
            victim = board.piece_at(move.to_square)
            victim_value = PIECE_VALUES[victim.piece_type] if victim else 0
        attacker = board.piece_at(move.from_square)
        attacker_value = PIECE_VALUES[attacker.piece_type] if attacker else 0
        return victim_value * 10 - attacker_value

    def _order_moves(self, board, moves, ply, tt_move=None):
        killers = self.killers.get(ply, ())

        def move_score(move):
            score = 0
            if tt_move is not None and move == tt_move:
                score += 1_000_000
            if move in killers:
                score += 25_000
            if board.is_capture(move):
                score += 10_000 + self._capture_order_score(board, move)
            if move.promotion:
                score += 8_000
            if board.gives_check(move):
                score += 900
            return -score

        ordered = list(moves)
        ordered.sort(key=move_score)
        return ordered

    def _remember_killer(self, ply, move):
        current = list(self.killers.get(ply, ()))
        if move in current:
            return
        current.insert(0, move)
        self.killers[ply] = tuple(current[:2])

    def _opening_book_move(self, board):
        # Use book only in the opening phase from near-initial positions.
        history = [move.uci() for move in board.move_stack]
        if len(history) > 16:
            return None

        candidates = {}
        for line in OPENING_BOOK_LINES:
            if len(line) <= len(history):
                continue
            if tuple(history) == line[: len(history)]:
                nxt = line[len(history)]
                try:
                    move = chess.Move.from_uci(nxt)
                except ValueError:
                    continue
                if move in board.legal_moves:
                    candidates[move] = candidates.get(move, 0) + 1

        if not candidates:
            return None
        moves = list(candidates.keys())
        weights = [candidates[m] for m in moves]
        return random.choices(moves, weights=weights, k=1)[0]

    def _quiescence(self, board, alpha, beta):
        self._check_timeout()
        stand_pat = self._evaluate(board)
        if stand_pat >= beta:
            return beta
        if stand_pat > alpha:
            alpha = stand_pat

        caps = [m for m in board.legal_moves if board.is_capture(m) or m.promotion]
        if not caps:
            return alpha
        caps = self._order_moves(board, caps, ply=99)

        for move in caps:
            board.push(move)
            score = -self._quiescence(board, -beta, -alpha)
            board.pop()
            if score >= beta:
                return beta
            if score > alpha:
                alpha = score
        return alpha

    def _negamax(self, board, depth, alpha, beta, ply):
        self._check_timeout()
        alpha_orig = alpha
        key = self._board_key(board)
        tt_entry = self.tt.get(key)
        if tt_entry is not None and tt_entry["depth"] >= depth:
            tt_score = tt_entry["score"]
            tt_bound = tt_entry["bound"]
            if tt_bound == TT_EXACT:
                return tt_score, tt_entry["move"]
            if tt_bound == TT_LOWER:
                alpha = max(alpha, tt_score)
            elif tt_bound == TT_UPPER:
                beta = min(beta, tt_score)
            if alpha >= beta:
                return tt_score, tt_entry["move"]

        if board.is_game_over(claim_draw=True):
            if board.is_checkmate():
                return (-MATE_SCORE + ply), None
            outcome = board.outcome(claim_draw=True)
            if outcome is None or outcome.winner is None:
                return 0, None
            return 0, None

        if depth <= 0:
            return self._quiescence(board, alpha, beta), None

        tt_move = tt_entry["move"] if tt_entry is not None else None
        moves = self._order_moves(board, list(board.legal_moves), ply, tt_move=tt_move)
        if not moves:
            return self._evaluate(board), None

        best_move = None
        best_score = -INF
        for move in moves:
            board.push(move)
            score, _ = self._negamax(board, depth - 1, -beta, -alpha, ply + 1)
            score = -score
            board.pop()

            if score > best_score:
                best_score = score
                best_move = move
            if score > alpha:
                alpha = score
            if alpha >= beta:
                if not board.is_capture(move):
                    self._remember_killer(ply, move)
                break

        bound = TT_EXACT
        if best_score <= alpha_orig:
            bound = TT_UPPER
        elif best_score >= beta:
            bound = TT_LOWER
        self.tt[key] = {"depth": depth, "score": best_score, "bound": bound, "move": best_move}
        return best_score, best_move

    def get_best_move(self):
        legal = list(self.board.board.legal_moves)
        if not legal:
            return None

        root = self.board.board.copy()
        self.nodes = 0
        self.tt.clear()
        self.killers.clear()
        self.cutoff_time = time.time() + max(0.9, min(30.0, self.time_limit * 0.95))

        max_depth = self._max_search_depth(root)
        best_move = random.choice(legal)

        book_move = self._opening_book_move(root)
        if book_move is not None:
            return book_move

        for depth in range(1, max_depth + 1):
            try:
                score, candidate = self._negamax(root, depth, -INF, INF, 0)
                if candidate is not None:
                    best_move = candidate
                # If we can already force mate, no need deeper.
                if score >= MATE_SCORE - 40:
                    break
            except TimeoutError:
                break
        return best_move
