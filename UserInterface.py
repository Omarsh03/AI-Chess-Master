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
        self.sidebar_width = 380
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
        self.show_clock = True
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
        self.TEXT_COLOR = (28, 30, 35)
        self.PANEL_BG = (248, 249, 252)
        self.PANEL_BORDER = (200, 206, 218)
        self.ARROW_COLOR = (30, 144, 255)
        self.MARKER_COLOR = (214, 110, 110)
        self.APP_BG = (26, 30, 38)
        self.BOARD_FRAME_DARK = (48, 54, 66)
        self.BOARD_FRAME_LIGHT = (84, 93, 112)
        self.SUBTLE_TEXT = (90, 98, 114)
        self.ACCENT = (75, 124, 211)
        self.GOOD = (30, 138, 67)
        self.BAD = (170, 45, 45)

        pygame.font.init()
        self.info_font = pygame.font.Font(None, 30)
        self.small_font = pygame.font.Font(None, 24)
        self.title_font = pygame.font.Font(None, 36)
        self.subtitle_font = pygame.font.Font(None, 27)
        self.coord_font = pygame.font.Font(None, 22)
        self.badge_font = pygame.font.Font(None, 25)
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
        file_idx = chess.square_file(square)
        rank_idx = chess.square_rank(square)
        x, y = self._screen_coords(file_idx, rank_idx)
        inset = max(6, int(self.square_size * 0.18))
        width = max(2, int(self.square_size * 0.08))
        rect = pygame.Rect(
            x + inset,
            y + inset,
            self.square_size - (inset * 2),
            self.square_size - (inset * 2),
        )
        pygame.draw.rect(self.surface, marker_color, rect, width, border_radius=4)

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

    def _draw_app_background(self):
        self.surface.fill(self.APP_BG)
        top_band = pygame.Rect(0, 0, self.surface.get_width(), 54)
        pygame.draw.rect(self.surface, (35, 40, 50), top_band)
        pygame.draw.line(
            self.surface,
            (72, 82, 103),
            (0, top_band.bottom - 1),
            (self.surface.get_width(), top_band.bottom - 1),
            1,
        )

    def _draw_board_frame(self):
        outer = pygame.Rect(
            self.board_origin_x - 16,
            self.board_origin_y - 16,
            self.board_size + 32,
            self.board_size + 32,
        )
        shadow = outer.move(5, 6)
        pygame.draw.rect(self.surface, (15, 18, 24), shadow, border_radius=14)
        pygame.draw.rect(self.surface, self.BOARD_FRAME_DARK, outer, border_radius=14)
        pygame.draw.rect(self.surface, self.BOARD_FRAME_LIGHT, outer, 2, border_radius=14)

    def _draw_board_coordinates(self):
        top_y = self.board_origin_y - 12
        bottom_y = self.board_origin_y + self.board_size + 4
        left_x = self.board_origin_x - 12
        right_x = self.board_origin_x + self.board_size + 7

        for display_file in range(8):
            board_file = display_file if self.playerColor == chess.WHITE else (7 - display_file)
            label = chr(ord("a") + board_file)
            text = self.coord_font.render(label, True, (214, 220, 232))
            center_x = self.board_origin_x + display_file * self.square_size + self.square_size // 2
            self.surface.blit(text, text.get_rect(center=(center_x, top_y)))
            self.surface.blit(text, text.get_rect(center=(center_x, bottom_y)))

        for display_rank in range(8):
            board_rank = 7 - display_rank if self.playerColor == chess.WHITE else display_rank
            label = str(board_rank + 1)
            text = self.coord_font.render(label, True, (214, 220, 232))
            center_y = self.board_origin_y + display_rank * self.square_size + self.square_size // 2
            self.surface.blit(text, text.get_rect(center=(left_x, center_y)))
            self.surface.blit(text, text.get_rect(center=(right_x, center_y)))

    def _format_think_time(self, seconds):
        if seconds is None:
            return "-"
        return f"{seconds:.1f}s"

    def _draw_avatar(self, x, y, size, is_bot, side_color):
        base = (77, 124, 205) if is_bot else (100, 108, 121)
        ring = (217, 224, 238) if is_bot else (216, 216, 216)
        pygame.draw.circle(self.surface, base, (x, y), size // 2)
        pygame.draw.circle(self.surface, ring, (x, y), size // 2, 2)

        if is_bot:
            head_w = int(size * 0.5)
            head_h = int(size * 0.35)
            head = pygame.Rect(0, 0, head_w, head_h)
            head.center = (x, y - int(size * 0.08))
            pygame.draw.rect(self.surface, (236, 241, 252), head, border_radius=4)
            eye_r = max(2, size // 18)
            pygame.draw.circle(self.surface, (51, 64, 88), (head.left + head_w // 3, head.centery), eye_r)
            pygame.draw.circle(self.surface, (51, 64, 88), (head.right - head_w // 3, head.centery), eye_r)
            mouth = pygame.Rect(head.left + head_w // 4, head.bottom - eye_r - 1, head_w // 2, 2)
            pygame.draw.rect(self.surface, (51, 64, 88), mouth)
            ant_y = head.top - 5
            pygame.draw.line(self.surface, (236, 241, 252), (x, ant_y), (x, ant_y - 6), 2)
            pygame.draw.circle(self.surface, (236, 241, 252), (x, ant_y - 7), 2)
        else:
            piece_symbol = "K" if side_color == chess.WHITE else "k"
            sprite = self.captured_piece_images.get(piece_symbol)
            if sprite is not None:
                rect = sprite.get_rect(center=(x, y))
                self.surface.blit(sprite, rect)

    def _draw_player_card(self, rect, name, is_bot, side_color, time_text, captured_symbols):
        pygame.draw.rect(self.surface, (251, 252, 255), rect, border_radius=10)
        pygame.draw.rect(self.surface, (207, 214, 226), rect, 1, border_radius=10)

        avatar_size = 38
        avatar_x = rect.x + 24
        avatar_y = rect.y + 24
        self._draw_avatar(avatar_x, avatar_y, avatar_size, is_bot, side_color)

        name_text = self.subtitle_font.render(name, True, self.TEXT_COLOR)
        role_text = self.small_font.render("BOT" if is_bot else "PLAYER", True, self.SUBTLE_TEXT)
        self.surface.blit(name_text, (avatar_x + 26, rect.y + 10))
        self.surface.blit(role_text, (avatar_x + 26, rect.y + 33))

        clock_label = self.small_font.render(time_text, True, self.ACCENT)
        self.surface.blit(clock_label, (rect.right - clock_label.get_width() - 14, rect.y + 14))

        cap_label = self.small_font.render("Captured", True, self.SUBTLE_TEXT)
        self.surface.blit(cap_label, (rect.x + 14, rect.y + 54))
        self.draw_captured_strip(captured_symbols, rect.x + 14, rect.y + 74, rect.width - 28)

    def _draw_move_history(self, rect, move_log):
        pygame.draw.rect(self.surface, (251, 252, 255), rect, border_radius=10)
        pygame.draw.rect(self.surface, (207, 214, 226), rect, 1, border_radius=10)

        title = self.subtitle_font.render("Move History", True, self.TEXT_COLOR)
        self.surface.blit(title, (rect.x + 14, rect.y + 10))

        header_y = rect.y + 38
        pygame.draw.line(
            self.surface,
            (221, 226, 235),
            (rect.x + 12, header_y + 20),
            (rect.right - 12, header_y + 20),
            1,
        )
        no_header = self.small_font.render("#", True, self.SUBTLE_TEXT)
        w_header = self.small_font.render("White", True, self.SUBTLE_TEXT)
        b_header = self.small_font.render("Black", True, self.SUBTLE_TEXT)
        self.surface.blit(no_header, (rect.x + 14, header_y))
        self.surface.blit(w_header, (rect.x + 42, header_y))
        self.surface.blit(b_header, (rect.x + rect.width // 2 + 24, header_y))

        rows = []
        for idx, entry in enumerate(move_log):
            move_no = (idx // 2) + 1
            if idx % 2 == 0:
                rows.append(
                    {
                        "no": move_no,
                        "white": f"{entry.get('san', '-')} ({self._format_think_time(entry.get('think_seconds'))})",
                        "black": "",
                    }
                )
            elif rows:
                rows[-1]["black"] = f"{entry.get('san', '-')} ({self._format_think_time(entry.get('think_seconds'))})"

        row_start_y = header_y + 26
        row_h = 22
        visible_rows = max(1, (rect.height - (row_start_y - rect.y) - 10) // row_h)
        rows = rows[-visible_rows:]

        for i, row in enumerate(rows):
            y = row_start_y + i * row_h
            if i % 2 == 0:
                pygame.draw.rect(
                    self.surface,
                    (246, 248, 252),
                    (rect.x + 10, y - 1, rect.width - 20, row_h),
                    border_radius=4,
                )
            no_text = self.small_font.render(str(row["no"]), True, self.SUBTLE_TEXT)
            white_text = self.small_font.render(row["white"], True, self.TEXT_COLOR)
            black_text = self.small_font.render(row["black"], True, self.TEXT_COLOR)
            self.surface.blit(no_text, (rect.x + 14, y))
            self.surface.blit(white_text, (rect.x + 42, y))
            self.surface.blit(black_text, (rect.x + rect.width // 2 + 24, y))

    def drawComponent(
        self,
        dragging_piece_symbol=None,
        drag_pos=None,
        drag_from_square=None,
        arrows=None,
        marked_squares=None,
        mode_label="",
        starting_fen=None,
        white_label="White",
        black_label="Black",
        white_is_bot=False,
        black_is_bot=False,
        move_log=None,
        do_flip=True,
    ):
        self._draw_app_background()
        arrows = arrows or []
        marked_squares = set(marked_squares or [])
        move_log = move_log or []
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

        self._draw_board_frame()

        panel_rect = pygame.Rect(
            self.sidebar_x,
            self.margin,
            self.surface.get_width() - self.sidebar_x - self.margin,
            self.surface.get_height() - (self.margin * 2),
        )
        panel_shadow = panel_rect.move(4, 5)
        pygame.draw.rect(self.surface, (18, 22, 30), panel_shadow, border_radius=12)
        pygame.draw.rect(self.surface, self.PANEL_BG, panel_rect, border_radius=12)
        pygame.draw.rect(self.surface, self.PANEL_BORDER, panel_rect, 2, border_radius=12)

        for rank_idx in range(8):
            for file_idx in range(8):
                square = chess.square(file_idx, rank_idx)
                x, y = self._screen_coords(file_idx, rank_idx)
                color = self.LIGHT_SQUARE if (file_idx + rank_idx) % 2 == 1 else self.DARK_SQUARE

                if square == self.selected_square:
                    color = self.SELECTED_COLOR
                elif self.last_move and (
                    chess.square_name(square) == self.last_move[:2]
                    or chess.square_name(square) == self.last_move[2:4]
                ):
                    color = self.LAST_MOVE_COLOR
                elif any(chess.square_name(square) == move[2:4] for move in self.valid_moves):
                    color = self.VALID_MOVE_COLOR
                if square in marked_squares:
                    color = self.MARKER_COLOR

                pygame.draw.rect(
                    self.surface, color, (x, y, self.square_size, self.square_size)
                )

        pygame.draw.rect(
            self.surface,
            (24, 28, 38),
            (self.board_origin_x, self.board_origin_y, self.board_size, self.board_size),
            1,
        )

        for from_square, to_square in arrows:
            self.draw_arrow(from_square, to_square)

        self._draw_board_coordinates()

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
        if self.show_clock:
            white_minutes = int(max(0, self.white_time) // 60)
            white_seconds = int(max(0, self.white_time) % 60)
            black_minutes = int(max(0, self.black_time) // 60)
            black_seconds = int(max(0, self.black_time) % 60)
            white_time_text = f"{white_minutes:02d}:{white_seconds:02d}"
            black_time_text = f"{black_minutes:02d}:{black_seconds:02d}"
        else:
            white_time_text = "--:--"
            black_time_text = "--:--"
        turn = "White" if self.board.board.turn == chess.WHITE else "Black"
        turn_color = (40, 120, 40) if self.board.board.turn == chess.WHITE else (120, 40, 40)

        header_y = self.margin + 12
        title = self.title_font.render("Full Chess", True, self.TEXT_COLOR)
        self.surface.blit(title, (self.sidebar_x + 18, header_y))
        if mode_label:
            mode_text = self.small_font.render(f"Mode: {mode_label}", True, self.SUBTLE_TEXT)
            self.surface.blit(mode_text, (self.sidebar_x + 18, header_y + 30))

        turn_badge = pygame.Rect(self.sidebar_x + 16, header_y + 56, panel_rect.width - 32, 34)
        turn_bg = (224, 244, 231) if self.board.board.turn == chess.WHITE else (246, 228, 228)
        pygame.draw.rect(self.surface, turn_bg, turn_badge, border_radius=8)
        pygame.draw.rect(self.surface, (195, 206, 214), turn_badge, 1, border_radius=8)
        turn_text = self.badge_font.render(f"Turn: {turn}", True, turn_color)
        self.surface.blit(turn_text, turn_text.get_rect(center=turn_badge.center))

        cards_top = turn_badge.bottom + 10
        card_h = 118
        top_card = pygame.Rect(self.sidebar_x + 16, cards_top, panel_rect.width - 32, card_h)
        bottom_card = pygame.Rect(
            self.sidebar_x + 16,
            panel_rect.bottom - card_h - 16,
            panel_rect.width - 32,
            card_h,
        )
        history_rect = pygame.Rect(
            self.sidebar_x + 16,
            top_card.bottom + 10,
            panel_rect.width - 32,
            bottom_card.y - (top_card.bottom + 20),
        )

        self._draw_player_card(
            top_card,
            black_label,
            black_is_bot,
            chess.BLACK,
            f"{black_time_text}   +{black_score}",
            black_captured,
        )
        self._draw_player_card(
            bottom_card,
            white_label,
            white_is_bot,
            chess.WHITE,
            f"{white_time_text}   +{white_score}",
            white_captured,
        )

        if history_rect.height > 80:
            self._draw_move_history(history_rect, move_log)

        if score_diff > 0:
            if white_lead:
                lead_text = self.small_font.render(f"White lead: +{score_diff}", True, self.GOOD)
            else:
                lead_text = self.small_font.render(f"Black lead: +{score_diff}", True, self.GOOD)
            self.surface.blit(
                lead_text,
                (self.sidebar_x + panel_rect.width - lead_text.get_width() - 18, turn_badge.y - 24),
            )

        if self.game_winner_color == chess.WHITE:
            winner_surface = self.small_font.render("Winner: White", True, self.GOOD)
            self.surface.blit(winner_surface, (bottom_card.x, bottom_card.y - 22))
        elif self.game_winner_color == chess.BLACK:
            winner_surface = self.small_font.render("Winner: Black", True, self.GOOD)
            self.surface.blit(winner_surface, (top_card.x, top_card.y - 22))

        if self.game_result_text:
            result_surface = self.small_font.render(self.game_result_text, True, self.BAD)
            self.surface.blit(
                result_surface,
                (self.sidebar_x + 18, panel_rect.bottom - 22),
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