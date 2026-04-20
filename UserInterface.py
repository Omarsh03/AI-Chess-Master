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

    def _draw_app_background(self):
        self.surface.fill(self.APP_BG)

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

    def _draw_player_card(self, rect, name, is_bot, side_color, time_text, captured_symbols, is_active=False, score=0):
        pygame.draw.rect(self.surface, self.CARD_BG, rect, border_radius=8)
        pygame.draw.rect(self.surface, self.CARD_BORDER, rect, 1, border_radius=8)

        if is_active:
            bar = pygame.Rect(rect.x, rect.y + 6, 3, rect.height - 12)
            pygame.draw.rect(self.surface, self.ACCENT, bar, border_radius=2)

        avatar_size = 34
        avatar_x = rect.x + 20
        avatar_y = rect.y + 22
        self._draw_avatar(avatar_x, avatar_y, avatar_size, is_bot, side_color)

        name_text = self.subtitle_font.render(name, True, self.TEXT_COLOR)
        role_label = "BOT" if is_bot else "YOU"
        role_text = self.small_font.render(role_label, True, self.SUBTLE_TEXT)
        self.surface.blit(name_text, (avatar_x + 22, rect.y + 8))
        self.surface.blit(role_text, (avatar_x + 22, rect.y + 28))

        if self.show_clock:
            clock_w = 82
            clock_h = 34
            clock_rect = pygame.Rect(rect.right - clock_w - 10, rect.y + 8, clock_w, clock_h)
            clock_bg = self.CLOCK_ACTIVE_BG if is_active else self.CLOCK_INACTIVE_BG
            clock_fg = self.CLOCK_ACTIVE_FG if is_active else self.CLOCK_INACTIVE_FG
            pygame.draw.rect(self.surface, clock_bg, clock_rect, border_radius=6)
            if is_active:
                pygame.draw.rect(self.surface, self.ACCENT, clock_rect, 1, border_radius=6)
            clock_surf = self.info_font.render(time_text, True, clock_fg)
            self.surface.blit(clock_surf, clock_surf.get_rect(center=clock_rect.center))

        sep_y = rect.y + 50
        pygame.draw.line(self.surface, self.CARD_BORDER, (rect.x + 10, sep_y), (rect.right - 10, sep_y), 1)

        cap_x = rect.x + 12
        cap_y = sep_y + 7
        if score > 0:
            score_surf = self.small_font.render(f"+{score}", True, self.ACCENT)
            self.surface.blit(score_surf, (cap_x, cap_y))
            cap_x += score_surf.get_width() + 6
        self.draw_captured_strip(captured_symbols, cap_x, cap_y, rect.right - cap_x - 10)

    def _draw_move_history(self, rect, move_log):
        pygame.draw.rect(self.surface, self.CARD_BG, rect, border_radius=8)
        pygame.draw.rect(self.surface, self.CARD_BORDER, rect, 1, border_radius=8)

        title = self.subtitle_font.render("Moves", True, self.TEXT_COLOR)
        self.surface.blit(title, (rect.x + 12, rect.y + 8))

        header_y = rect.y + 28
        pygame.draw.line(self.surface, (65, 62, 58),
                         (rect.x + 8, header_y + 16), (rect.right - 8, header_y + 16), 1)
        no_header = self.small_font.render("#", True, self.SUBTLE_TEXT)
        w_header = self.small_font.render("White", True, self.SUBTLE_TEXT)
        b_header = self.small_font.render("Black", True, self.SUBTLE_TEXT)
        self.surface.blit(no_header, (rect.x + 10, header_y))
        self.surface.blit(w_header, (rect.x + 36, header_y))
        self.surface.blit(b_header, (rect.x + rect.width // 2 + 18, header_y))

        rows = []
        for idx, entry in enumerate(move_log):
            move_no = (idx // 2) + 1
            if idx % 2 == 0:
                rows.append({"no": move_no, "white": entry.get("san", "-"), "black": ""})
            elif rows:
                rows[-1]["black"] = entry.get("san", "-")

        row_start_y = header_y + 22
        row_h = 20
        visible_rows = max(1, (rect.height - (row_start_y - rect.y) - 6) // row_h)
        rows = rows[-visible_rows:]

        for i, row in enumerate(rows):
            y = row_start_y + i * row_h
            if i % 2 == 0:
                pygame.draw.rect(self.surface, (55, 52, 48),
                                 (rect.x + 6, y, rect.width - 12, row_h), border_radius=3)
            no_text = self.small_font.render(str(row["no"]), True, self.SUBTLE_TEXT)
            white_text = self.small_font.render(row["white"], True, self.TEXT_COLOR)
            black_text = self.small_font.render(row["black"], True, self.TEXT_COLOR)
            self.surface.blit(no_text, (rect.x + 10, y + 2))
            self.surface.blit(white_text, (rect.x + 36, y + 2))
            self.surface.blit(black_text, (rect.x + rect.width // 2 + 18, y + 2))

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
        pygame.draw.rect(self.surface, self.PANEL_BG, panel_rect, border_radius=10)
        pygame.draw.rect(self.surface, self.PANEL_BORDER, panel_rect, 1, border_radius=10)

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

        # Turn dot indicator
        turn_label = "White to move" if is_white_turn else "Black to move"
        dot_color = (220, 220, 215) if is_white_turn else (50, 50, 50)
        dot_outline = (150, 145, 138)
        dot_x = cx + 8
        dot_y = y_cur + 8
        pygame.draw.circle(self.surface, dot_outline, (dot_x, dot_y), 7)
        pygame.draw.circle(self.surface, dot_color, (dot_x, dot_y), 6)
        turn_surf = self.small_font.render(turn_label, True, self.TEXT_COLOR)
        self.surface.blit(turn_surf, (dot_x + 12, y_cur))
        y_cur += 24

        card_h = 98
        buttons_reserve = 170

        black_card = pygame.Rect(cx, y_cur, cw, card_h)
        self._draw_player_card(black_card, black_label, black_is_bot, chess.BLACK,
                               black_time_text, black_captured,
                               is_active=not is_white_turn, score=black_adv)
        y_cur += card_h + 8

        white_card_y = panel_rect.bottom - card_h - buttons_reserve
        history_rect = pygame.Rect(cx, y_cur, cw, white_card_y - y_cur - 8)
        if history_rect.height > 60:
            self._draw_move_history(history_rect, move_log)

        white_card = pygame.Rect(cx, white_card_y, cw, card_h)
        self._draw_player_card(white_card, white_label, white_is_bot, chess.WHITE,
                               white_time_text, white_captured,
                               is_active=is_white_turn, score=white_adv)

        # Game-over overlay banner
        if self.game_result_text:
            banner_h = 38
            banner_y = white_card.bottom + 10
            if banner_y + banner_h < panel_rect.bottom - buttons_reserve + 10:
                banner = pygame.Rect(cx, banner_y, cw, banner_h)
                pygame.draw.rect(self.surface, (60, 22, 22), banner, border_radius=7)
                pygame.draw.rect(self.surface, self.BAD, banner, 1, border_radius=7)
                res_surf = self.small_font.render(self.game_result_text, True, (240, 180, 180))
                self.surface.blit(res_surf, res_surf.get_rect(center=banner.center))

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