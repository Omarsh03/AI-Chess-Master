import os
import sys
import pygame
import chess

PIECE_IMAGE_FILES = {
    "P": "white_pawn.png",
    "N": "white_knight.png",
    "B": "white_bishop.png",
    "R": "white_rook.png",
    "Q": "white_queen.png",
    "K": "white_king.png",
    "p": "black_pawn.png",
    "n": "black_knight.png",
    "b": "black_bishop.png",
    "r": "black_rook.png",
    "q": "black_queen.png",
    "k": "black_king.png",
}

PIECE_POINTS = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
    chess.KING: 0,
}


def get_resource_path(relative_path):
    """Resolve resource path for both dev and PyInstaller builds."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


class UserInterface:
    def __init__(self, surface, board):
        self.surface = surface
        self.board = board
        self.margin = 20
        self.sidebar_width = 240
        available_w = max(320, surface.get_width() - self.sidebar_width - (self.margin * 2))
        available_h = max(320, surface.get_height() - (self.margin * 2))
        board_pixels = min(available_w, available_h)
        self.square_size = max(32, board_pixels // 8)
        self.board_size = self.square_size * 8
        self.board_origin_x = self.margin
        self.board_origin_y = max(self.margin, (surface.get_height() - self.board_size) // 2)
        self.sidebar_x = self.board_origin_x + self.board_size + 20
        self.selected_square = None
        self.last_move = None
        self.valid_moves = []
        self.playerColor = chess.WHITE
        self.allow_both_colors = True
        self.white_time = 300
        self.black_time = 300
        self.game_result_text = ""
        self.game_winner_color = None
        self.game_termination = ""
        self.fallen_loser_color = None
        self.fall_anim_start_ms = None
        self.fall_anim_duration_ms = 700

        self.LIGHT_SQUARE = (240, 217, 181)
        self.DARK_SQUARE = (181, 136, 99)
        self.SELECTED_COLOR = (130, 151, 105)
        self.VALID_MOVE_COLOR = (186, 202, 43)
        self.LAST_MOVE_COLOR = (205, 210, 106)
        self.TEXT_COLOR = (0, 0, 0)
        self.PANEL_BG = (245, 245, 245)
        self.PANEL_BORDER = (190, 190, 190)
        self.ARROW_COLOR = (30, 144, 255)
        self.MARKER_COLOR = (40, 90, 210)

        pygame.font.init()
        self.info_font = pygame.font.Font(None, 30)
        self.small_font = pygame.font.Font(None, 24)
        self.title_font = pygame.font.Font(None, 36)
        self.piece_images = self._load_piece_images()
        self.captured_piece_images = self._build_captured_piece_images()

    def _load_piece_images(self):
        """Load and scale all 12 piece images once at startup."""
        piece_images = {}
        missing_files = []
        image_paths = {}
        target_size = int(self.square_size * 0.86)

        for symbol, filename in PIECE_IMAGE_FILES.items():
            image_path = get_resource_path(os.path.join("assets", "pieces", filename))
            image_paths[symbol] = image_path
            if not os.path.isfile(image_path):
                missing_files.append(image_path)

        if missing_files:
            missing_as_text = "\n".join(f"- {path}" for path in missing_files)
            raise FileNotFoundError(
                "Missing piece images. Add all 12 files under assets/pieces:\n"
                f"{missing_as_text}"
            )

        for symbol, image_path in image_paths.items():
            try:
                image = pygame.image.load(image_path).convert_alpha()
                piece_images[symbol] = pygame.transform.smoothscale(
                    image, (target_size, target_size)
                )
            except pygame.error as exc:
                raise RuntimeError(f"Failed to load piece image '{image_path}': {exc}") from exc

        return piece_images

    def _build_captured_piece_images(self):
        """Build smaller sprites for captured-piece display in sidebar."""
        mini_size = max(14, int(self.square_size * 0.36))
        mini_images = {}
        for symbol, sprite in self.piece_images.items():
            mini_images[symbol] = pygame.transform.smoothscale(
                sprite, (mini_size, mini_size)
            )
        return mini_images

    def _screen_coords(self, file_idx, rank_idx):
        x = self.board_origin_x + (file_idx * self.square_size)
        if self.playerColor == chess.WHITE:
            y = self.board_origin_y + ((7 - rank_idx) * self.square_size)
        else:
            y = self.board_origin_y + (rank_idx * self.square_size)
        return x, y

    def get_square_from_pos(self, pos):
        x, y = pos
        if not (
            self.board_origin_x <= x < self.board_origin_x + self.board_size
            and self.board_origin_y <= y < self.board_origin_y + self.board_size
        ):
            return None
        file_idx = (x - self.board_origin_x) // self.square_size
        if self.playerColor == chess.WHITE:
            rank_idx = 7 - ((y - self.board_origin_y) // self.square_size)
        else:
            rank_idx = (y - self.board_origin_y) // self.square_size
        if 0 <= file_idx <= 7 and 0 <= rank_idx <= 7:
            return chess.square(file_idx, rank_idx)
        return None

    def square_center(self, square):
        file_idx = chess.square_file(square)
        rank_idx = chess.square_rank(square)
        x, y = self._screen_coords(file_idx, rank_idx)
        return (x + self.square_size // 2, y + self.square_size // 2)

    def draw_arrow(self, from_square, to_square, color=None):
        start = self.square_center(from_square)
        end = self.square_center(to_square)
        arrow_color = color if color is not None else self.ARROW_COLOR
        pygame.draw.line(self.surface, arrow_color, start, end, 5)

        dx = end[0] - start[0]
        dy = end[1] - start[1]
        length = max(1, (dx * dx + dy * dy) ** 0.5)
        ux = dx / length
        uy = dy / length
        head_len = 16
        head_w = 10
        tip = (end[0], end[1])
        left = (
            end[0] - (ux * head_len) + (uy * head_w),
            end[1] - (uy * head_len) - (ux * head_w),
        )
        right = (
            end[0] - (ux * head_len) - (uy * head_w),
            end[1] - (uy * head_len) + (ux * head_w),
        )
        pygame.draw.polygon(self.surface, arrow_color, [tip, left, right])

    def draw_marker(self, square, color=None):
        marker_color = color if color is not None else self.MARKER_COLOR
        center = self.square_center(square)
        radius = max(8, int(self.square_size * 0.22))
        width = max(2, int(self.square_size * 0.08))
        pygame.draw.circle(self.surface, marker_color, center, radius, width)

    def clear_game_result(self):
        self.game_result_text = ""
        self.game_winner_color = None
        self.game_termination = ""
        self.fallen_loser_color = None
        self.fall_anim_start_ms = None

    def set_game_result(self, winner_color=None, termination="", message=None):
        self.game_winner_color = winner_color
        self.game_termination = termination or ""
        self.fall_anim_start_ms = None
        if winner_color in (chess.WHITE, chess.BLACK):
            self.fallen_loser_color = not winner_color
            self.fall_anim_start_ms = pygame.time.get_ticks()
        else:
            self.fallen_loser_color = None
        if message is not None:
            self.game_result_text = message
            return
        if winner_color == chess.WHITE:
            self.game_result_text = f"White wins - Black loses ({self.game_termination})"
        elif winner_color == chess.BLACK:
            self.game_result_text = f"Black wins - White loses ({self.game_termination})"
        else:
            base = "Draw"
            if self.game_termination:
                base = f"{base} ({self.game_termination})"
            self.game_result_text = base

    def draw_fallen_king(self, loser_color, progress=1.0):
        king_square = self.board.board.king(loser_color)
        if king_square is None:
            return
        king_symbol = "K" if loser_color == chess.WHITE else "k"
        sprite = self.piece_images.get(king_symbol)
        if sprite is None:
            return

        # Ease-out makes the fall feel more natural.
        p = max(0.0, min(1.0, float(progress)))
        eased = 1.0 - ((1.0 - p) ** 3)
        center_x, center_y = self.square_center(king_square)
        shadow_w = int(self.square_size * (0.3 + 0.32 * eased))
        shadow_h = int(self.square_size * (0.08 + 0.12 * eased))
        shadow_rect = pygame.Rect(0, 0, shadow_w, shadow_h)
        shadow_rect.center = (center_x, center_y + int(self.square_size * (0.05 + 0.25 * eased)))
        pygame.draw.ellipse(self.surface, (40, 40, 40), shadow_rect)

        target_angle = 105 if loser_color == chess.BLACK else -105
        angle = target_angle * eased
        scale = 1.0 + (0.03 * eased)
        fallen = pygame.transform.rotozoom(sprite, angle, scale)
        x_shift = int((self.square_size * 0.08) * eased * (1 if loser_color == chess.BLACK else -1))
        y_shift = int((self.square_size * 0.24) * eased)
        fallen_rect = fallen.get_rect(
            center=(center_x + x_shift, center_y + y_shift)
        )
        self.surface.blit(fallen, fallen_rect)

    def build_move_from_squares(self, from_square, to_square):
        if from_square is None or to_square is None or from_square == to_square:
            return None

        move_prefix = chess.square_name(from_square) + chess.square_name(to_square)
        legal_moves = self.board.get_legal_moves()
        if move_prefix in legal_moves:
            return move_prefix

        promo = self._promotion_suffix(move_prefix)
        if promo is None:
            return None
        return f"{move_prefix}{promo}" if promo else move_prefix

    def get_capture_scores(self, starting_fen=None):
        if starting_fen:
            replay_board = chess.Board(starting_fen)
        else:
            replay_board = chess.Board()

        white_score = 0
        black_score = 0
        for move in self.board.board.move_stack:
            mover = replay_board.turn
            if replay_board.is_capture(move):
                if replay_board.is_en_passant(move):
                    capture_square = move.to_square - 8 if mover == chess.WHITE else move.to_square + 8
                else:
                    capture_square = move.to_square
                captured = replay_board.piece_at(capture_square)
                if captured:
                    value = PIECE_POINTS.get(captured.piece_type, 0)
                    if mover == chess.WHITE:
                        white_score += value
                    else:
                        black_score += value
            replay_board.push(move)
        return white_score, black_score

    def get_captured_pieces(self, starting_fen=None):
        if starting_fen:
            replay_board = chess.Board(starting_fen)
        else:
            replay_board = chess.Board()

        white_captured = []
        black_captured = []

        for move in self.board.board.move_stack:
            mover = replay_board.turn
            if replay_board.is_capture(move):
                if replay_board.is_en_passant(move):
                    capture_square = (
                        move.to_square - 8 if mover == chess.WHITE else move.to_square + 8
                    )
                else:
                    capture_square = move.to_square
                captured = replay_board.piece_at(capture_square)
                if captured:
                    if mover == chess.WHITE:
                        white_captured.append(captured.symbol())
                    else:
                        black_captured.append(captured.symbol())
            replay_board.push(move)

        return white_captured, black_captured

    def draw_captured_strip(self, symbols, x, y, max_width):
        if not symbols:
            none_text = self.small_font.render("-", True, (90, 90, 90))
            self.surface.blit(none_text, (x, y + 2))
            return y + none_text.get_height() + 4

        cursor_x = x
        cursor_y = y
        row_h = 0
        spacing = 4
        for symbol in symbols:
            sprite = self.captured_piece_images.get(symbol)
            if sprite is None:
                continue
            sprite_w = sprite.get_width()
            sprite_h = sprite.get_height()
            if cursor_x + sprite_w > x + max_width:
                cursor_x = x
                cursor_y += row_h + spacing
                row_h = 0
            self.surface.blit(sprite, (cursor_x, cursor_y))
            cursor_x += sprite_w + spacing
            row_h = max(row_h, sprite_h)

        return cursor_y + row_h + 4

    def drawComponent(
        self,
        dragging_piece_symbol=None,
        drag_pos=None,
        drag_from_square=None,
        arrows=None,
        marked_squares=None,
        mode_label="",
        starting_fen=None,
        do_flip=True,
    ):
        self.surface.fill((232, 232, 232))
        arrows = arrows or []
        marked_squares = marked_squares or []
        fallen_loser_color = None
        fallen_king_square = None
        fall_progress = 1.0
        if self.fallen_loser_color in (chess.WHITE, chess.BLACK):
            fallen_loser_color = self.fallen_loser_color
            fallen_king_square = self.board.board.king(fallen_loser_color)
            if self.fall_anim_start_ms is not None:
                elapsed = pygame.time.get_ticks() - self.fall_anim_start_ms
                fall_progress = max(0.0, min(1.0, elapsed / self.fall_anim_duration_ms))
            else:
                fall_progress = 1.0

        panel_rect = pygame.Rect(
            self.sidebar_x,
            self.margin,
            self.surface.get_width() - self.sidebar_x - self.margin,
            self.surface.get_height() - (self.margin * 2),
        )
        pygame.draw.rect(self.surface, self.PANEL_BG, panel_rect, border_radius=8)
        pygame.draw.rect(self.surface, self.PANEL_BORDER, panel_rect, 2, border_radius=8)

        for rank_idx in range(8):
            for file_idx in range(8):
                square = chess.square(file_idx, rank_idx)
                x, y = self._screen_coords(file_idx, rank_idx)
                color = self.LIGHT_SQUARE if (file_idx + rank_idx) % 2 == 0 else self.DARK_SQUARE

                if square == self.selected_square:
                    color = self.SELECTED_COLOR
                elif self.last_move and (
                    chess.square_name(square) == self.last_move[:2]
                    or chess.square_name(square) == self.last_move[2:4]
                ):
                    color = self.LAST_MOVE_COLOR
                elif any(chess.square_name(square) == move[2:4] for move in self.valid_moves):
                    color = self.VALID_MOVE_COLOR

                pygame.draw.rect(
                    self.surface, color, (x, y, self.square_size, self.square_size)
                )

        for from_square, to_square in arrows:
            self.draw_arrow(from_square, to_square)
        for square in marked_squares:
            self.draw_marker(square)

        for rank_idx in range(8):
            for file_idx in range(8):
                square = chess.square(file_idx, rank_idx)
                x, y = self._screen_coords(file_idx, rank_idx)
                piece = self.board.board.piece_at(square)
                if piece and square != drag_from_square and square != fallen_king_square:
                    sprite = self.piece_images[piece.symbol()]
                    rect = sprite.get_rect(
                        center=(x + self.square_size // 2, y + self.square_size // 2)
                    )
                    self.surface.blit(sprite, rect)

        if dragging_piece_symbol and drag_pos:
            sprite = self.piece_images[dragging_piece_symbol]
            rect = sprite.get_rect(center=drag_pos)
            self.surface.blit(sprite, rect)
        elif fallen_loser_color is not None:
            self.draw_fallen_king(fallen_loser_color, progress=fall_progress)

        white_score, black_score = self.get_capture_scores(starting_fen=starting_fen)
        white_captured, black_captured = self.get_captured_pieces(starting_fen=starting_fen)
        score_diff = abs(white_score - black_score)
        white_lead = white_score > black_score
        black_lead = black_score > white_score
        white_minutes = int(max(0, self.white_time) // 60)
        white_seconds = int(max(0, self.white_time) % 60)
        black_minutes = int(max(0, self.black_time) // 60)
        black_seconds = int(max(0, self.black_time) % 60)
        turn = "White" if self.board.board.turn == chess.WHITE else "Black"
        turn_color = (40, 120, 40) if self.board.board.turn == chess.WHITE else (120, 40, 40)

        y = self.margin + 12
        title = self.title_font.render("Full Chess", True, self.TEXT_COLOR)
        self.surface.blit(title, (self.sidebar_x + 16, y))
        y += 42
        if mode_label:
            mode_text = self.small_font.render(f"Mode: {mode_label}", True, self.TEXT_COLOR)
            self.surface.blit(mode_text, (self.sidebar_x + 16, y))
            y += 30

        turn_text = self.info_font.render(f"Turn: {turn}", True, turn_color)
        self.surface.blit(turn_text, (self.sidebar_x + 16, y))
        y += 38

        white_text = self.small_font.render(
            f"White  {white_minutes:02d}:{white_seconds:02d}   +{white_score}",
            True,
            self.TEXT_COLOR,
        )
        self.surface.blit(white_text, (self.sidebar_x + 16, y))
        if white_lead and score_diff > 0:
            white_lead_text = self.small_font.render(
                f"Lead +{score_diff}", True, (28, 118, 43)
            )
            self.surface.blit(white_lead_text, (self.sidebar_x + 220, y))
        y += 28
        black_text = self.small_font.render(
            f"Black  {black_minutes:02d}:{black_seconds:02d}   +{black_score}",
            True,
            self.TEXT_COLOR,
        )
        self.surface.blit(black_text, (self.sidebar_x + 16, y))
        if black_lead and score_diff > 0:
            black_lead_text = self.small_font.render(
                f"Lead +{score_diff}", True, (28, 118, 43)
            )
            self.surface.blit(black_lead_text, (self.sidebar_x + 220, y))
        y += 40

        panel_content_width = self.surface.get_width() - self.sidebar_x - 32
        white_captured_title = self.small_font.render(
            "White captured:", True, self.TEXT_COLOR
        )
        self.surface.blit(white_captured_title, (self.sidebar_x + 16, y))
        y += 22
        y = self.draw_captured_strip(
            white_captured, self.sidebar_x + 16, y, panel_content_width
        )
        y += 6

        black_captured_title = self.small_font.render(
            "Black captured:", True, self.TEXT_COLOR
        )
        self.surface.blit(black_captured_title, (self.sidebar_x + 16, y))
        y += 22
        y = self.draw_captured_strip(
            black_captured, self.sidebar_x + 16, y, panel_content_width
        )
        y += 12

        controls_header = self.small_font.render("Controls", True, self.TEXT_COLOR)
        self.surface.blit(controls_header, (self.sidebar_x + 16, y))
        y += 24
        controls = [
            "Left-click hold: drag piece",
            "Left click piece -> target: move",
            "Right drag: draw planning arrow",
            "Right click same square: marker",
            "U key: undo move",
            "R key: redo move",
            "M key: return to menu",
        ]
        for line in controls:
            line_surface = self.small_font.render(line, True, (70, 70, 70))
            self.surface.blit(line_surface, (self.sidebar_x + 16, y))
            y += 20

        if self.game_winner_color == chess.WHITE:
            winner_surface = self.info_font.render("Winner: White", True, (28, 118, 43))
            loser_surface = self.small_font.render("Loser: Black", True, (170, 35, 35))
            self.surface.blit(winner_surface, (self.sidebar_x + 16, y + 6))
            self.surface.blit(loser_surface, (self.sidebar_x + 16, y + 36))
        elif self.game_winner_color == chess.BLACK:
            winner_surface = self.info_font.render("Winner: Black", True, (28, 118, 43))
            loser_surface = self.small_font.render("Loser: White", True, (170, 35, 35))
            self.surface.blit(winner_surface, (self.sidebar_x + 16, y + 6))
            self.surface.blit(loser_surface, (self.sidebar_x + 16, y + 36))

        if self.game_result_text:
            result_surface = self.small_font.render(
                self.game_result_text, True, (190, 30, 30)
            )
            self.surface.blit(
                result_surface,
                (self.sidebar_x + 16, self.surface.get_height() - self.margin - 28),
            )

        if do_flip:
            pygame.display.flip()

    def show_game_over_message(self, result_text):
        self.set_game_result(winner_color=None, termination="", message=result_text)
        self.drawComponent()

    def _promotion_suffix(self, move_prefix):
        """Prefer queen promotion, fallback to any legal promotion."""
        legal = self.board.get_legal_moves()
        candidates = [m for m in legal if m.startswith(move_prefix)]
        if not candidates:
            return None
        for suffix in ("q", "r", "b", "n"):
            if f"{move_prefix}{suffix}" in candidates:
                return suffix
        if len(candidates[0]) == 5:
            return candidates[0][4]
        return ""

    def handle_click(self, pos):
        if self.board.is_game_over():
            return None

        square = self.get_square_from_pos(pos)
        if square is None:
            return None

        current_turn = self.board.board.turn
        if not self.allow_both_colors and self.playerColor is not None and current_turn != self.playerColor:
            return None

        if self.selected_square is None:
            piece = self.board.board.piece_at(square)
            if piece and piece.color == current_turn:
                self.selected_square = square
                self.valid_moves = [
                    move
                    for move in self.board.get_legal_moves()
                    if chess.square_name(square) == move[:2]
                ]
            return None

        move_prefix = chess.square_name(self.selected_square) + chess.square_name(square)
        self.selected_square = None
        self.valid_moves = []

        legal_moves = self.board.get_legal_moves()
        if move_prefix in legal_moves:
            return move_prefix

        promo = self._promotion_suffix(move_prefix)
        if promo is None:
            return None
        return f"{move_prefix}{promo}" if promo else move_prefix