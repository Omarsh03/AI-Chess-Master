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
        # Horizontal strips above/below the board host the player info
        # (clock + captured pieces), matching standard chess layouts.
        self.strip_h = 56
        self.strip_gap = 8
        available_w = max(320, surface.get_width() - self.sidebar_width - (self.margin * 2))
        available_h = max(
            320,
            surface.get_height()
            - (self.margin * 2)
            - (self.strip_h * 2)
            - (self.strip_gap * 2),
        )
        board_pixels = min(available_w, available_h)
        self.square_size = max(32, board_pixels // 8)
        self.board_size = self.square_size * 8
        self.board_origin_x = self.margin
        stack_h = self.board_size + 2 * self.strip_h + 2 * self.strip_gap
        self.board_origin_y = max(
            self.margin + self.strip_h + self.strip_gap,
            (surface.get_height() - stack_h) // 2 + self.strip_h + self.strip_gap,
        )
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
        self.SELECTED_COLOR = (106, 138, 82)
        self.VALID_MOVE_COLOR = (106, 138, 82)
        self.LAST_MOVE_COLOR = (205, 210, 106)
        self.TEXT_COLOR = (212, 210, 202)
        self.PANEL_BG = (36, 34, 31)
        self.PANEL_BORDER = (58, 55, 51)
        self.CARD_BG = (48, 46, 43)
        self.CARD_BORDER = (66, 63, 59)
        self.ARROW_COLOR = (30, 144, 255)
        self.ARROW_WHITE = (255, 190, 0)
        self.ARROW_BLACK = (80, 200, 255)
        self.MARKER_COLOR = (214, 110, 110)
        self.APP_BG = (22, 21, 18)
        self.BOARD_FRAME_DARK = (28, 26, 24)
        self.BOARD_FRAME_LIGHT = (52, 50, 46)
        self.SUBTLE_TEXT = (135, 130, 122)
        self.ACCENT = (129, 182, 76)
        self.GOOD = (129, 182, 76)
        self.BAD = (200, 75, 75)
        self.CLOCK_ACTIVE_FG = (240, 240, 230)
        self.CLOCK_ACTIVE_BG = (35, 60, 18)
        self.CLOCK_INACTIVE_FG = (110, 107, 100)
        self.CLOCK_INACTIVE_BG = (42, 40, 37)

        pygame.font.init()
        self.info_font = pygame.font.Font(None, 30)
        self.small_font = pygame.font.Font(None, 24)
        self.tiny_font = pygame.font.Font(None, 19)
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

    def draw_arrow(self, from_square, to_square, color=None, owner=None, number=None):
        import chess as _chess
        if color is None:
            if owner == _chess.WHITE:
                color = self.ARROW_WHITE
            elif owner == _chess.BLACK:
                color = self.ARROW_BLACK
            else:
                color = self.ARROW_COLOR

        start = self.square_center(from_square)
        end = self.square_center(to_square)

        f1 = _chess.square_file(from_square)
        r1 = _chess.square_rank(from_square)
        f2 = _chess.square_file(to_square)
        r2 = _chess.square_rank(to_square)
        df = abs(f2 - f1)
        dr = abs(r2 - r1)
        is_knight_move = (df == 2 and dr == 1) or (df == 1 and dr == 2)

        head_len = 18
        head_w = 11

        if is_knight_move:
            # L-shaped: move horizontally first, then vertically
            corner = self.square_center(_chess.square(f2, r1))
            pygame.draw.line(self.surface, color, start, corner, 6)
            dx = end[0] - corner[0]
            dy = end[1] - corner[1]
            seg_len = max(1, (dx * dx + dy * dy) ** 0.5)
            ux = dx / seg_len
            uy = dy / seg_len
            shaft_end = (end[0] - ux * head_len, end[1] - uy * head_len)
            pygame.draw.line(self.surface, color, corner, shaft_end, 6)
            # number label at the corner of the L
            label_pos = corner
        else:
            dx = end[0] - start[0]
            dy = end[1] - start[1]
            length = max(1, (dx * dx + dy * dy) ** 0.5)
            ux = dx / length
            uy = dy / length
            shaft_end = (end[0] - ux * head_len, end[1] - uy * head_len)
            pygame.draw.line(self.surface, color, start, shaft_end, 6)
            label_pos = (int((start[0] + end[0]) / 2), int((start[1] + end[1]) / 2))

        tip = (end[0], end[1])
        left = (
            end[0] - (ux * head_len) + (uy * head_w),
            end[1] - (uy * head_len) - (ux * head_w),
        )
        right = (
            end[0] - (ux * head_len) - (uy * head_w),
            end[1] - (uy * head_len) + (ux * head_w),
        )
        pygame.draw.polygon(self.surface, color, [tip, left, right])

        if number is not None:
            font_size = max(14, self.square_size // 3)
            font = pygame.font.Font(None, font_size)
            label = str(number)
            text_surf = font.render(label, True, (255, 255, 255))
            shadow_surf = font.render(label, True, (0, 0, 0))
            rect = text_surf.get_rect(center=label_pos)
            self.surface.blit(shadow_surf, rect.move(1, 1))
            self.surface.blit(text_surf, rect)

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

    def _draw_rounded_gradient(self, rect, top_color, bot_color, radius=10, alpha=255):
        """Render a rounded rectangle with a subtle top→bottom gradient."""
        if rect.width <= 0 or rect.height <= 0:
            return
        grad = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        for y in range(rect.height):
            k = y / max(1, rect.height - 1)
            r = int(top_color[0] + (bot_color[0] - top_color[0]) * k)
            g = int(top_color[1] + (bot_color[1] - top_color[1]) * k)
            b = int(top_color[2] + (bot_color[2] - top_color[2]) * k)
            pygame.draw.line(grad, (r, g, b, alpha), (0, y), (rect.width, y))
        if radius > 0:
            mask = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            pygame.draw.rect(
                mask,
                (255, 255, 255, 255),
                mask.get_rect(),
                border_radius=radius,
            )
            grad.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        self.surface.blit(grad, rect.topleft)

    def _draw_app_background(self):
        """
        Elegant in-game backdrop: vertical gradient that matches the menu
        palette, plus a soft radial glow centred behind the board so the
        pieces feel spotlit.
        """
        W, H = self.surface.get_width(), self.surface.get_height()

        # Vertical gradient from slightly warm dark at the top to deeper
        # tones at the bottom. Cached per surface size for speed.
        cached = getattr(self, "_bg_gradient_cache", None)
        if cached is None or cached.get_size() != (W, H):
            bg = pygame.Surface((W, H))
            top = (26, 25, 22)
            bot = (14, 13, 11)
            for y in range(H):
                k = y / max(1, H - 1)
                r = int(top[0] + (bot[0] - top[0]) * k)
                g = int(top[1] + (bot[1] - top[1]) * k)
                b = int(top[2] + (bot[2] - top[2]) * k)
                pygame.draw.line(bg, (r, g, b), (0, y), (W, y))
            self._bg_gradient_cache = bg
            cached = bg
        self.surface.blit(cached, (0, 0))

        # Soft radial spotlight behind the board area.
        board_cx = self.board_origin_x + self.board_size // 2
        board_cy = self.board_origin_y + self.board_size // 2
        glow_r = max(self.board_size // 2 + 60, 220)
        glow = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
        for r in range(glow_r, 0, -30):
            intensity = max(0, 26 - int(26 * (r / glow_r)))
            if intensity <= 0:
                continue
            pygame.draw.circle(
                glow, (129, 182, 76, intensity), (glow_r, glow_r), r
            )
        self.surface.blit(
            glow, glow.get_rect(center=(board_cx, board_cy))
        )

        # Accent bar at the very top to match the menu screens.
        pygame.draw.rect(self.surface, self.ACCENT, pygame.Rect(0, 0, W, 3))

    def _draw_valid_move_overlays(self):
        if not self.valid_moves:
            return
        sz = self.square_size
        for move in self.valid_moves:
            if len(move) < 4:
                continue
            try:
                to_sq = chess.parse_square(move[2:4])
            except Exception:
                continue
            file_idx = chess.square_file(to_sq)
            rank_idx = chess.square_rank(to_sq)
            x, y = self._screen_coords(file_idx, rank_idx)
            piece_at = self.board.board.piece_at(to_sq)
            overlay = pygame.Surface((sz, sz), pygame.SRCALPHA)
            if piece_at is None:
                r = max(7, sz // 5)
                pygame.draw.circle(overlay, (0, 0, 0, 72), (sz // 2, sz // 2), r)
            else:
                ring_w = max(5, sz // 7)
                pygame.draw.circle(overlay, (0, 0, 0, 72), (sz // 2, sz // 2),
                                   sz // 2 - 2, ring_w)
            self.surface.blit(overlay, (x, y))

    def _draw_board_frame(self):
        outer = pygame.Rect(
            self.board_origin_x - 16,
            self.board_origin_y - 16,
            self.board_size + 32,
            self.board_size + 32,
        )

        # Two-tier drop shadow for real depth.
        deep_shadow = outer.move(0, 14)
        ds = pygame.Surface(
            (deep_shadow.width + 30, deep_shadow.height + 30), pygame.SRCALPHA
        )
        pygame.draw.rect(
            ds,
            (0, 0, 0, 90),
            ds.get_rect().inflate(-10, -10),
            border_radius=20,
        )
        self.surface.blit(ds, (deep_shadow.x - 15, deep_shadow.y - 15))
        close_shadow = outer.move(4, 6)
        cs = pygame.Surface(
            (close_shadow.width + 10, close_shadow.height + 10), pygame.SRCALPHA
        )
        pygame.draw.rect(
            cs,
            (0, 0, 0, 140),
            cs.get_rect().inflate(-4, -4),
            border_radius=16,
        )
        self.surface.blit(cs, (close_shadow.x - 5, close_shadow.y - 5))

        # Frame body with a subtle top→bottom gradient (wood-tinted dark).
        self._draw_rounded_gradient(
            outer, top_color=(38, 34, 30), bot_color=(22, 20, 17), radius=14
        )
        # Crisp double border: outer light + inner dark edge.
        pygame.draw.rect(
            self.surface, self.BOARD_FRAME_LIGHT, outer, 2, border_radius=14
        )
        inner_edge = outer.inflate(-10, -10)
        pygame.draw.rect(
            self.surface, (0, 0, 0), inner_edge, 1, border_radius=9
        )

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

    def _format_think_time_compact(self, seconds):
        """Very compact per-move time badge: 1.3s / 42s / 2:05."""
        if seconds is None:
            return ""
        s = max(0.0, float(seconds))
        if s < 10:
            return f"{s:.1f}s"
        if s < 60:
            return f"{int(s)}s"
        m = int(s // 60)
        sec = int(s % 60)
        return f"{m}:{sec:02d}"

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

    def _draw_side_strip(self, rect, name, is_bot, side_color, time_text,
                         captured_symbols, is_active, score):
        """
        Horizontal player strip shown above/below the board: avatar +
        name on the left, captured material with score in the middle,
        and the clock pill on the right.
        """
        # Active-side glow.
        if is_active:
            glow = pygame.Surface(
                (rect.width + 16, rect.height + 16), pygame.SRCALPHA
            )
            pulse = 0.55 + 0.45 * abs(
                (pygame.time.get_ticks() % 1800) / 900.0 - 1.0
            )
            pygame.draw.rect(
                glow,
                (*self.ACCENT, int(48 * pulse) + 26),
                glow.get_rect(),
                border_radius=14,
            )
            self.surface.blit(glow, (rect.x - 8, rect.y - 8))

        # Body gradient + border.
        if is_active:
            top_c, bot_c = (62, 74, 42), (38, 44, 24)
            border_c = self.ACCENT
        else:
            top_c, bot_c = (52, 50, 44), (32, 30, 26)
            border_c = self.CARD_BORDER
        self._draw_rounded_gradient(
            rect, top_color=top_c, bot_color=bot_c, radius=10
        )
        pygame.draw.rect(
            self.surface, border_c, rect, 1, border_radius=10
        )

        # Inset top highlight.
        hl = pygame.Surface((rect.width - 12, 2), pygame.SRCALPHA)
        hl.fill((255, 255, 255, 38 if is_active else 22))
        self.surface.blit(hl, (rect.x + 6, rect.y + 3))

        # Avatar on the far-left.
        avatar_size = 34
        avatar_x = rect.x + 22
        avatar_y = rect.centery
        self._draw_avatar(avatar_x, avatar_y, avatar_size, is_bot, side_color)

        # Name + role stacked next to the avatar.
        name_x = avatar_x + 22
        name_text = self.subtitle_font.render(name, True, self.TEXT_COLOR)
        role_label = "BOT" if is_bot else "YOU"
        role_color = (150, 200, 120) if is_active else self.SUBTLE_TEXT
        role_text = self.small_font.render(role_label, True, role_color)
        self.surface.blit(
            name_text, name_text.get_rect(midleft=(name_x, rect.centery - 10))
        )
        self.surface.blit(
            role_text, role_text.get_rect(midleft=(name_x, rect.centery + 10))
        )

        # Clock pill on the far-right.
        clock_w = 100
        clock_h = 36
        clock_rect = pygame.Rect(
            rect.right - clock_w - 12,
            rect.centery - clock_h // 2,
            clock_w,
            clock_h,
        )
        if self.show_clock:
            if is_active:
                ctop, cbot = (60, 98, 30), self.CLOCK_ACTIVE_BG
                cfg, cborder = self.CLOCK_ACTIVE_FG, self.ACCENT
            else:
                ctop, cbot = (58, 55, 50), self.CLOCK_INACTIVE_BG
                cfg, cborder = self.CLOCK_INACTIVE_FG, (70, 66, 60)
            self._draw_rounded_gradient(
                clock_rect, top_color=ctop, bot_color=cbot, radius=7
            )
            pygame.draw.rect(
                self.surface, cborder, clock_rect, 1, border_radius=7
            )
            clock_surf = self.info_font.render(time_text, True, cfg)
            self.surface.blit(
                clock_surf, clock_surf.get_rect(center=clock_rect.center)
            )

        # Captured-pieces strip between the name and the clock.
        cap_x = name_x + 120
        cap_right = clock_rect.left - 12 if self.show_clock else rect.right - 12
        cap_w = max(0, cap_right - cap_x)
        cap_y = rect.centery - 9
        if score > 0:
            score_surf = self.small_font.render(f"+{score}", True, self.ACCENT)
            self.surface.blit(
                score_surf, score_surf.get_rect(midleft=(cap_x, rect.centery))
            )
            cap_x += score_surf.get_width() + 8
            cap_w = max(0, cap_right - cap_x)
        if cap_w > 0:
            self.draw_captured_strip(captured_symbols, cap_x, cap_y, cap_w)

    def _draw_player_card(self, rect, name, is_bot, side_color, time_text, captured_symbols, is_active=False, score=0):
        # Outer glow when it's this player's turn.
        if is_active:
            glow = pygame.Surface(
                (rect.width + 16, rect.height + 16), pygame.SRCALPHA
            )
            pulse = 0.6 + 0.4 * abs(
                (pygame.time.get_ticks() % 1800) / 900.0 - 1.0
            )
            pygame.draw.rect(
                glow,
                (*self.ACCENT, int(55 * pulse) + 30),
                glow.get_rect(),
                border_radius=12,
            )
            self.surface.blit(glow, (rect.x - 8, rect.y - 8))

        # Card body: gradient + border + inset highlight.
        if is_active:
            top_c, bot_c = (62, 74, 42), (38, 44, 24)
            border_c = self.ACCENT
        else:
            top_c, bot_c = (54, 52, 46), (36, 34, 30)
            border_c = self.CARD_BORDER
        self._draw_rounded_gradient(rect, top_color=top_c, bot_color=bot_c, radius=10)
        pygame.draw.rect(self.surface, border_c, rect, 1, border_radius=10)

        inset_hl = pygame.Surface(
            (rect.width - 12, 2), pygame.SRCALPHA
        )
        inset_hl.fill((255, 255, 255, 36 if is_active else 22))
        self.surface.blit(inset_hl, (rect.x + 6, rect.y + 3))

        # Bright accent bar on the left when it's the player's turn.
        if is_active:
            bar = pygame.Rect(rect.x + 2, rect.y + 6, 4, rect.height - 12)
            pygame.draw.rect(self.surface, self.ACCENT, bar, border_radius=2)

        avatar_size = 34
        avatar_x = rect.x + 22
        avatar_y = rect.y + 22
        self._draw_avatar(avatar_x, avatar_y, avatar_size, is_bot, side_color)

        name_text = self.subtitle_font.render(name, True, self.TEXT_COLOR)
        role_label = "BOT" if is_bot else "YOU"
        role_color = (150, 200, 120) if is_active else self.SUBTLE_TEXT
        role_text = self.small_font.render(role_label, True, role_color)
        self.surface.blit(name_text, (avatar_x + 22, rect.y + 8))
        self.surface.blit(role_text, (avatar_x + 22, rect.y + 28))

        if self.show_clock:
            clock_w = 86
            clock_h = 34
            clock_rect = pygame.Rect(rect.right - clock_w - 10, rect.y + 8, clock_w, clock_h)
            if is_active:
                clock_top = (60, 98, 30)
                clock_bot = self.CLOCK_ACTIVE_BG
                clock_fg  = self.CLOCK_ACTIVE_FG
                clock_border = self.ACCENT
            else:
                clock_top = (58, 55, 50)
                clock_bot = self.CLOCK_INACTIVE_BG
                clock_fg  = self.CLOCK_INACTIVE_FG
                clock_border = (70, 66, 60)
            self._draw_rounded_gradient(
                clock_rect, top_color=clock_top, bot_color=clock_bot, radius=6
            )
            pygame.draw.rect(
                self.surface, clock_border, clock_rect, 1, border_radius=6
            )
            clock_surf = self.info_font.render(time_text, True, clock_fg)
            self.surface.blit(clock_surf, clock_surf.get_rect(center=clock_rect.center))

        # Elegant separator with an accent diamond, matching the menu.
        sep_y = rect.y + 50
        pygame.draw.line(
            self.surface,
            self.CARD_BORDER,
            (rect.x + 12, sep_y),
            (rect.centerx - 6, sep_y),
            1,
        )
        pygame.draw.line(
            self.surface,
            self.CARD_BORDER,
            (rect.centerx + 6, sep_y),
            (rect.right - 12, sep_y),
            1,
        )
        diamond_color = self.ACCENT if is_active else (90, 88, 80)
        pygame.draw.polygon(
            self.surface,
            diamond_color,
            [
                (rect.centerx,     sep_y - 3),
                (rect.centerx + 3, sep_y),
                (rect.centerx,     sep_y + 3),
                (rect.centerx - 3, sep_y),
            ],
        )

        cap_x = rect.x + 14
        cap_y = sep_y + 7
        if score > 0:
            score_surf = self.small_font.render(f"+{score}", True, self.ACCENT)
            self.surface.blit(score_surf, (cap_x, cap_y))
            cap_x += score_surf.get_width() + 6
        self.draw_captured_strip(captured_symbols, cap_x, cap_y, rect.right - cap_x - 10)

    def _draw_move_history(self, rect, move_log):
        # Reset the map of clickable cells every frame.
        self._history_cells = []

        # Gradient body + crisp border.
        self._draw_rounded_gradient(
            rect, top_color=(50, 48, 43), bot_color=(30, 28, 25), radius=8
        )
        pygame.draw.rect(
            self.surface, self.CARD_BORDER, rect, 1, border_radius=8
        )

        title = self.subtitle_font.render("Moves", True, self.TEXT_COLOR)
        self.surface.blit(title, (rect.x + 12, rect.y + 8))
        # Small accent underline under the title.
        underline = pygame.Rect(rect.x + 12, rect.y + 32, 28, 2)
        pygame.draw.rect(self.surface, self.ACCENT, underline, border_radius=1)

        header_y = rect.y + 42
        no_header = self.small_font.render("#",     True, self.SUBTLE_TEXT)
        w_header  = self.small_font.render("White", True, self.SUBTLE_TEXT)
        b_header  = self.small_font.render("Black", True, self.SUBTLE_TEXT)
        self.surface.blit(no_header, (rect.x + 10, header_y))
        self.surface.blit(w_header,  (rect.x + 36, header_y))
        self.surface.blit(b_header,  (rect.x + rect.width // 2 + 18, header_y))
        pygame.draw.line(
            self.surface,
            (65, 62, 58),
            (rect.x + 8, header_y + 18),
            (rect.right - 8, header_y + 18),
            1,
        )

        # Group move_log entries into (white, black) pairs with their ply
        # indices, so we can turn each half-move into its own click target.
        rows = []
        for ply_idx, entry in enumerate(move_log):
            move_no = (ply_idx // 2) + 1
            if ply_idx % 2 == 0:
                rows.append({
                    "no": move_no,
                    "white": entry.get("san", "-"),
                    "white_ply": ply_idx + 1,
                    "white_time": entry.get("think_seconds", 0.0),
                    "black": "",
                    "black_ply": None,
                    "black_time": None,
                })
            elif rows:
                rows[-1]["black"] = entry.get("san", "-")
                rows[-1]["black_ply"] = ply_idx + 1
                rows[-1]["black_time"] = entry.get("think_seconds", 0.0)

        row_start_y = header_y + 24
        row_h = 20
        visible_rows = max(1, (rect.height - (row_start_y - rect.y) - 6) // row_h)
        is_last_pair = len(rows) > visible_rows
        rows = rows[-visible_rows:]

        # The ply currently shown on the board (may differ from latest when
        # we're reviewing a finished game).
        current_ply = len(self.board.board.move_stack)
        mid_x = rect.x + rect.width // 2 + 8
        half_w = rect.width - 12

        for i, row in enumerate(rows):
            y = row_start_y + i * row_h

            # Row-level zebra shading so the eye can still scan easily.
            if i % 2 == 0:
                stripe = pygame.Surface((half_w, row_h), pygame.SRCALPHA)
                pygame.draw.rect(
                    stripe,
                    (255, 255, 255, 10),
                    stripe.get_rect(),
                    border_radius=4,
                )
                self.surface.blit(stripe, (rect.x + 6, y))

            # Cell rects (used for per-cell highlight and click detection).
            white_cell = pygame.Rect(rect.x + 28, y, (mid_x - rect.x - 28), row_h)
            black_cell = pygame.Rect(mid_x, y, rect.right - mid_x - 6, row_h)

            for cell_rect, ply in (
                (white_cell, row["white_ply"]),
                (black_cell, row["black_ply"]),
            ):
                if ply is None:
                    continue

                is_current = (ply == current_ply)
                if is_current:
                    hi = pygame.Surface(
                        (cell_rect.width, cell_rect.height), pygame.SRCALPHA
                    )
                    pygame.draw.rect(
                        hi,
                        (*self.ACCENT, 70),
                        hi.get_rect(),
                        border_radius=4,
                    )
                    self.surface.blit(hi, cell_rect.topleft)
                    pygame.draw.rect(
                        self.surface,
                        self.ACCENT,
                        cell_rect,
                        1,
                        border_radius=4,
                    )

                # Register the cell for click detection.
                self._history_cells.append({"rect": cell_rect.copy(), "ply": ply})

            no_color = self.ACCENT if current_ply and row["white_ply"] == current_ply else self.SUBTLE_TEXT
            no_text    = self.small_font.render(str(row["no"]), True, no_color)
            white_text = self.small_font.render(row["white"], True, self.TEXT_COLOR)
            black_text = self.small_font.render(row["black"], True, self.TEXT_COLOR)
            self.surface.blit(no_text,    (rect.x + 10, y + 2))
            self.surface.blit(white_text, (rect.x + 36, y + 2))
            self.surface.blit(black_text, (mid_x + 6, y + 2))

            # Per-move think-time label rendered in small muted text.
            if row["white_time"] is not None:
                t_surf = self.tiny_font.render(
                    self._format_think_time_compact(row["white_time"]),
                    True,
                    self.SUBTLE_TEXT,
                )
                self.surface.blit(
                    t_surf,
                    (rect.x + 36 + white_text.get_width() + 5, y + 5),
                )
            if row["black_time"] is not None:
                t_surf = self.tiny_font.render(
                    self._format_think_time_compact(row["black_time"]),
                    True,
                    self.SUBTLE_TEXT,
                )
                self.surface.blit(
                    t_surf,
                    (mid_x + 6 + black_text.get_width() + 5, y + 5),
                )

        # Small "..." overflow indicator at the top if there are truncated rows.
        if is_last_pair:
            dots = self.small_font.render("…", True, self.SUBTLE_TEXT)
            self.surface.blit(dots, (rect.centerx - 4, row_start_y - 14))

    def get_history_click_ply(self, pos):
        """Return the half-move (ply) index at `pos`, or None if not on a cell."""
        for cell in getattr(self, "_history_cells", []):
            if cell["rect"].collidepoint(pos):
                return cell["ply"]
        return None

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

        # Subtle drop shadow behind the panel to separate it from the board.
        ps = pygame.Surface(
            (panel_rect.width + 20, panel_rect.height + 20), pygame.SRCALPHA
        )
        pygame.draw.rect(
            ps,
            (0, 0, 0, 100),
            ps.get_rect().inflate(-6, -6),
            border_radius=14,
        )
        self.surface.blit(ps, (panel_rect.x - 10, panel_rect.y - 4))

        # Vertical gradient body + crisp border + top accent strip.
        self._draw_rounded_gradient(
            panel_rect,
            top_color=(44, 42, 38),
            bot_color=(26, 24, 21),
            radius=12,
        )
        pygame.draw.rect(
            self.surface, self.PANEL_BORDER, panel_rect, 1, border_radius=12
        )
        accent_cap = pygame.Rect(
            panel_rect.x + 14, panel_rect.y + 1, panel_rect.width - 28, 2
        )
        pygame.draw.rect(self.surface, self.ACCENT, accent_cap, border_radius=1)

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
                if square in marked_squares:
                    color = self.MARKER_COLOR

                pygame.draw.rect(self.surface, color, (x, y, self.square_size, self.square_size))

        pygame.draw.rect(self.surface, (0, 0, 0),
                         (self.board_origin_x, self.board_origin_y, self.board_size, self.board_size), 1)

        for arrow in arrows:
            if isinstance(arrow, dict):
                self.draw_arrow(arrow["from"], arrow["to"], owner=arrow.get("owner"), number=arrow.get("number"))
            else:
                self.draw_arrow(arrow[0], arrow[1])

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

        self._draw_valid_move_overlays()

        if dragging_piece_symbol and drag_pos:
            sprite = self.piece_images[dragging_piece_symbol]
            rect = sprite.get_rect(center=drag_pos)
            self.surface.blit(sprite, rect)
        elif fallen_loser_color is not None:
            self.draw_fallen_king(fallen_loser_color, progress=fall_progress)

        # ── Sidebar content ────────────────────────────────────────────
        white_score, black_score = self.get_capture_scores(starting_fen=starting_fen)
        white_adv = max(0, white_score - black_score)
        black_adv = max(0, black_score - white_score)
        white_captured, black_captured = self.get_captured_pieces(starting_fen=starting_fen)
        is_white_turn = self.board.board.turn == chess.WHITE

        if self.show_clock:
            white_time_text = f"{int(max(0, self.white_time) // 60):02d}:{int(max(0, self.white_time) % 60):02d}"
            black_time_text = f"{int(max(0, self.black_time) // 60):02d}:{int(max(0, self.black_time) % 60):02d}"
        else:
            white_time_text = "--:--"
            black_time_text = "--:--"

        cx = panel_rect.x + 12
        cw = panel_rect.width - 24
        y_cur = panel_rect.y + 10

        # Mode label
        if mode_label:
            mode_surf = self.small_font.render(mode_label, True, self.SUBTLE_TEXT)
            self.surface.blit(mode_surf, (cx, y_cur))
            y_cur += 22

        # Premium turn indicator: pill with pulsing side dot.
        turn_label = "White to move" if is_white_turn else "Black to move"
        pill_rect = pygame.Rect(cx, y_cur - 2, cw, 26)
        self._draw_rounded_gradient(
            pill_rect, top_color=(46, 44, 40), bot_color=(30, 28, 25), radius=13
        )
        pygame.draw.rect(
            self.surface, self.CARD_BORDER, pill_rect, 1, border_radius=13
        )

        dot_color = (235, 235, 228) if is_white_turn else (30, 30, 30)
        dot_outline = (160, 158, 150) if is_white_turn else (90, 88, 80)
        dot_x = pill_rect.x + 14
        dot_y = pill_rect.centery
        # Soft pulsing halo around the dot.
        pulse = 0.5 + 0.5 * abs(
            (pygame.time.get_ticks() % 1600) / 800.0 - 1.0
        )
        halo = pygame.Surface((22, 22), pygame.SRCALPHA)
        pygame.draw.circle(
            halo, (*self.ACCENT, int(80 * pulse) + 30), (11, 11), 11
        )
        self.surface.blit(halo, (dot_x - 11, dot_y - 11))
        pygame.draw.circle(self.surface, dot_outline, (dot_x, dot_y), 7)
        pygame.draw.circle(self.surface, dot_color, (dot_x, dot_y), 6)
        turn_surf = self.small_font.render(turn_label, True, self.TEXT_COLOR)
        self.surface.blit(
            turn_surf,
            turn_surf.get_rect(midleft=(dot_x + 14, dot_y)),
        )
        y_cur += 30

        # Compact controls reserve at the bottom of the sidebar (arrows +
        # menu button); a bit taller when the game-over banner is visible.
        controls_reserve = 62
        banner_reserve = 54 if self.game_result_text else 0

        # Keep the side panel in sync with board orientation: the player's
        # own side is always at the bottom, opponent at the top.
        if self.playerColor == chess.BLACK:
            top_color, bot_color = chess.WHITE, chess.BLACK
            top_label, bot_label = white_label, black_label
            top_is_bot, bot_is_bot = white_is_bot, black_is_bot
            top_time, bot_time = white_time_text, black_time_text
            top_captured, bot_captured = white_captured, black_captured
            top_score, bot_score = white_adv, black_adv
            top_active = is_white_turn
            bot_active = not is_white_turn
        else:
            top_color, bot_color = chess.BLACK, chess.WHITE
            top_label, bot_label = black_label, white_label
            top_is_bot, bot_is_bot = black_is_bot, white_is_bot
            top_time, bot_time = black_time_text, white_time_text
            top_captured, bot_captured = black_captured, white_captured
            top_score, bot_score = black_adv, white_adv
            top_active = not is_white_turn
            bot_active = is_white_turn

        # Player strips above and below the board (full-width of frame).
        strip_x = self.board_origin_x - 16
        strip_w = self.board_size + 32
        top_strip_rect = pygame.Rect(
            strip_x,
            self.board_origin_y - 16 - self.strip_gap - self.strip_h,
            strip_w,
            self.strip_h,
        )
        bottom_strip_rect = pygame.Rect(
            strip_x,
            self.board_origin_y + self.board_size + 16 + self.strip_gap,
            strip_w,
            self.strip_h,
        )
        self._draw_side_strip(
            top_strip_rect,
            top_label, top_is_bot, top_color, top_time, top_captured,
            is_active=top_active, score=top_score,
        )
        self._draw_side_strip(
            bottom_strip_rect,
            bot_label, bot_is_bot, bot_color, bot_time, bot_captured,
            is_active=bot_active, score=bot_score,
        )

        # Moves history now occupies the full remaining sidebar height.
        history_top = y_cur
        history_bottom = panel_rect.bottom - controls_reserve - banner_reserve - 10
        history_rect = pygame.Rect(cx, history_top, cw, history_bottom - history_top)
        if history_rect.height > 60:
            self._draw_move_history(history_rect, move_log)

        # Game-over banner sits between the history and the controls row.
        if self.game_result_text:
            banner_h = 42
            banner_y = history_bottom + 6
            banner = pygame.Rect(cx, banner_y, cw, banner_h)
            bg_glow = pygame.Surface(
                (banner.width + 14, banner.height + 14), pygame.SRCALPHA
            )
            pygame.draw.rect(
                bg_glow,
                (*self.BAD, 55),
                bg_glow.get_rect(),
                border_radius=12,
            )
            self.surface.blit(bg_glow, (banner.x - 7, banner.y - 7))
            self._draw_rounded_gradient(
                banner,
                top_color=(88, 34, 34),
                bot_color=(48, 18, 18),
                radius=8,
            )
            pygame.draw.rect(
                self.surface, self.BAD, banner, 1, border_radius=8
            )
            bar = pygame.Rect(banner.x + 4, banner.y + 6, 3, banner.height - 12)
            pygame.draw.rect(self.surface, self.BAD, bar, border_radius=2)
            res_surf = self.subtitle_font.render(
                self.game_result_text, True, (248, 212, 212)
            )
            self.surface.blit(
                res_surf, res_surf.get_rect(center=banner.center)
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