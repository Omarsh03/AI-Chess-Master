import random
import time
import threading
import pygame
import chess

from ai_agent import AIAgent
from game import GameState
from UserInterface import UserInterface


WINDOW_WIDTH = 1040
WINDOW_HEIGHT = 700
FPS = 60

MODE_LABELS = {
    "HUMAN_AI": "Human vs AI",
    "AI_AI": "AI vs AI",
    "HUMAN_HUMAN": "Human vs Human",
}

TIME_CONTROL_GROUPS = [
    ("Bullet", [("1 min", 60, 0), ("1|1", 60, 1), ("2|1", 120, 1)]),
    ("Blitz", [("3 min", 180, 0), ("3|2", 180, 2), ("5 min", 300, 0)]),
    ("Rapid", [("10 min", 600, 0), ("15|10", 900, 10), ("30 min", 1800, 0)]),
]


class UnifiedChessApp:
    def __init__(self):
        pygame.init()
        self.surface = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Full Chess")
        self.clock = pygame.time.Clock()
        self.running = True

        self.state = "MENU"
        self.game = None
        self.ui = None
        self.mode = None
        self.pending_mode = None
        self.mode_label = ""
        self.starting_fen = None
        self.game_over = False

        self.dragging_piece_symbol = None
        self.drag_from_square = None
        self.drag_pos = None
        self.left_down_pos = None
        self.left_drag_started = False
        self.drag_start_threshold = 8

        self.arrow_start_square = None
        self.arrows = []
        self.marked_squares = set()

        self.white_time = 300
        self.black_time = 300
        self.base_time_seconds = 300
        self.increment_seconds = 0
        self.last_timer_tick = time.time()
        self.time_loss_text = ""

        self.human_color = None
        self.ai_white = None
        self.ai_black = None
        self.last_ai_move_ms = 0
        self.ai_move_interval_ms = 350
        self.redo_stack = []
        self.ai_state_lock = threading.Lock()
        self.ai_thinking = False
        self.ai_thinking_color = None
        self.ai_pending_move = None
        self.position_token = 0

        self.menu_buttons = []
        self.color_buttons = []
        self.time_buttons = []
        self.time_back_button = None
        self.game_buttons = {}
        self._build_menu_buttons()
        self._build_color_buttons()
        self._build_time_buttons()

    def _build_menu_buttons(self):
        center_x = WINDOW_WIDTH // 2
        top = 250
        button_w = 320
        button_h = 56
        gap = 18
        entries = [
            ("HUMAN_AI", "Human vs AI"),
            ("AI_AI", "AI vs AI"),
            ("HUMAN_HUMAN", "Human vs Human"),
        ]
        self.menu_buttons = []
        for idx, (mode_key, label) in enumerate(entries):
            rect = pygame.Rect(
                center_x - (button_w // 2),
                top + idx * (button_h + gap),
                button_w,
                button_h,
            )
            self.menu_buttons.append((mode_key, label, rect))

    def _build_color_buttons(self):
        center_x = WINDOW_WIDTH // 2
        top = 280
        button_w = 320
        button_h = 52
        gap = 14
        entries = [
            ("WHITE", "Play as White"),
            ("BLACK", "Play as Black"),
            ("RANDOM", "Random Color"),
            ("BACK", "Back"),
        ]
        self.color_buttons = []
        for idx, (key, label) in enumerate(entries):
            rect = pygame.Rect(
                center_x - (button_w // 2),
                top + idx * (button_h + gap),
                button_w,
                button_h,
            )
            self.color_buttons.append((key, label, rect))

    def _build_time_buttons(self):
        self.time_buttons = []
        top = 150
        left = (WINDOW_WIDTH // 2) - 260
        button_w = 160
        button_h = 50
        col_gap = 16
        row_gap = 18
        section_gap = 66

        y = top
        for category, options in TIME_CONTROL_GROUPS:
            self.time_buttons.append(("HEADER", category, None))
            y += 34
            for col, (label, base_seconds, increment_seconds) in enumerate(options):
                x = left + col * (button_w + col_gap)
                rect = pygame.Rect(x, y, button_w, button_h)
                self.time_buttons.append(
                    ("OPTION", label, rect, base_seconds, increment_seconds, category)
                )
            y += button_h + row_gap + section_gap

        back_w = 180
        back_h = 48
        self.time_back_button = pygame.Rect(
            (WINDOW_WIDTH // 2) - (back_w // 2),
            WINDOW_HEIGHT - 80,
            back_w,
            back_h,
        )

    def _format_time_control(self, base_seconds, increment_seconds):
        base_minutes = int(base_seconds // 60)
        if increment_seconds > 0:
            return f"{base_minutes}+{int(increment_seconds)}"
        return f"{base_minutes}+0"

    def _build_game_buttons(self):
        if not self.ui:
            return
        panel_x = self.ui.sidebar_x + 16
        button_w = max(120, self.surface.get_width() - panel_x - 28)
        button_h = 38
        top = self.surface.get_height() - self.ui.margin - 166
        self.game_buttons = {
            "undo": pygame.Rect(panel_x, top, button_w, button_h),
            "redo": pygame.Rect(panel_x, top + 46, button_w, button_h),
            "menu": pygame.Rect(panel_x, top + 92, button_w, button_h),
        }

    def start_game(self, mode, human_color=None):
        self.mode = mode
        tc_label = self._format_time_control(self.base_time_seconds, self.increment_seconds)
        self.mode_label = f"{MODE_LABELS.get(mode, mode)} | {tc_label}"
        self.state = "GAME"
        self.game_over = False
        self.time_loss_text = ""
        self.dragging_piece_symbol = None
        self.drag_from_square = None
        self.drag_pos = None
        self.left_down_pos = None
        self.left_drag_started = False
        self.arrow_start_square = None
        self.arrows = []
        self.marked_squares = set()
        self.redo_stack = []
        self.ai_pending_move = None
        self.ai_thinking = False
        self.ai_thinking_color = None
        self.position_token += 1

        self.game = GameState()
        self.game.setup_new_game(game_mode=mode, setup_cmd="Setup STANDARD")
        self.starting_fen = self.game.board.board.fen()

        self.ui = UserInterface(self.surface, self.game.board)
        self.ui.playerColor = chess.WHITE
        self.ui.allow_both_colors = True
        self.ui.game_result_text = ""

        self.white_time = float(self.base_time_seconds)
        self.black_time = float(self.base_time_seconds)
        self.last_timer_tick = time.time()

        self.human_color = None
        self.ai_white = None
        self.ai_black = None
        if mode == "HUMAN_AI":
            if human_color is None:
                self.human_color = random.choice([chess.WHITE, chess.BLACK])
            else:
                self.human_color = human_color
            chosen = "White" if self.human_color == chess.WHITE else "Black"
            self.mode_label = (
                f"{MODE_LABELS['HUMAN_AI']} (You: {chosen}) | "
                f"{self._format_time_control(self.base_time_seconds, self.increment_seconds)}"
            )
            self.ai_white = None if self.human_color == chess.WHITE else AIAgent(self.game.board, chess.WHITE, 5)
            self.ai_black = None if self.human_color == chess.BLACK else AIAgent(self.game.board, chess.BLACK, 5)
        elif mode == "AI_AI":
            self.ai_white = AIAgent(self.game.board, chess.WHITE, 5)
            self.ai_black = AIAgent(self.game.board, chess.BLACK, 5)

        self._build_game_buttons()
        self.last_ai_move_ms = pygame.time.get_ticks()

    def go_to_menu(self):
        self.state = "MENU"
        self.game = None
        self.ui = None
        self.mode = None
        self.pending_mode = None
        self.mode_label = ""
        with self.ai_state_lock:
            self.ai_pending_move = None
            self.ai_thinking = False
            self.ai_thinking_color = None
        self.position_token += 1

    def _human_can_move_now(self):
        if self.state != "GAME" or self.game_over or self.mode == "AI_AI":
            return False
        current_turn = self.game.board.board.turn
        if self.mode == "HUMAN_HUMAN":
            return True
        if self.mode == "HUMAN_AI":
            return current_turn == self.human_color
        return False

    def _update_timers(self):
        if self.state != "GAME" or self.game_over:
            return
        now = time.time()
        elapsed = now - self.last_timer_tick
        self.last_timer_tick = now
        if self.game.board.board.turn == chess.WHITE:
            self.white_time = max(0, self.white_time - elapsed)
            if self.white_time <= 0:
                self.time_loss_text = "Black wins on time"
        else:
            self.black_time = max(0, self.black_time - elapsed)
            if self.black_time <= 0:
                self.time_loss_text = "White wins on time"
        self.ui.white_time = self.white_time
        self.ui.black_time = self.black_time
        if self.time_loss_text and not self.game_over:
            self.game_over = True
            winner_color = chess.BLACK if self.white_time <= 0 else chess.WHITE
            self.ui.set_game_result(
                winner_color=winner_color,
                termination="TIME",
                message=self.time_loss_text,
            )

    def _update_game_result_text(self):
        result = self.game.get_result()
        if result.get("status") == "finished":
            winner = result.get("winner")
            termination = result.get("termination", "UNKNOWN")
            if winner == "white":
                winner_color = chess.WHITE
            elif winner == "black":
                winner_color = chess.BLACK
            else:
                winner_color = None
            self.ui.set_game_result(winner_color=winner_color, termination=termination)
            self.game_over = True

    def _apply_move(self, move_uci):
        if not move_uci:
            return False
        mover = self.game.board.board.turn
        if self.game.make_move(move_uci):
            if self.increment_seconds > 0:
                if mover == chess.WHITE:
                    self.white_time += self.increment_seconds
                else:
                    self.black_time += self.increment_seconds
            self.ui.last_move = move_uci
            self.last_timer_tick = time.time()
            self.redo_stack.clear()
            self.position_token += 1
            with self.ai_state_lock:
                self.ai_pending_move = None
            if self.game.is_game_over():
                self._update_game_result_text()
            return True
        return False

    def _undo_move(self):
        if self.state != "GAME" or not self.game:
            return
        board = self.game.board.board
        if not board.move_stack:
            return
        last_move = board.pop()
        self.redo_stack.append(last_move)
        mover = board.turn
        if self.increment_seconds > 0:
            if mover == chess.WHITE:
                self.white_time = max(0, self.white_time - self.increment_seconds)
            else:
                self.black_time = max(0, self.black_time - self.increment_seconds)
        self.game.board.cached_legal_moves = None
        if self.game.moves_history:
            self.game.moves_history.pop()
        self.game.current_turn = board.turn
        self.ui.last_move = board.move_stack[-1].uci() if board.move_stack else None
        self.ui.selected_square = None
        self.ui.valid_moves = []
        self.ui.clear_game_result()
        self.game_over = False
        self.time_loss_text = ""
        self.last_timer_tick = time.time()
        self.position_token += 1
        with self.ai_state_lock:
            self.ai_pending_move = None

    def _redo_move(self):
        if self.state != "GAME" or not self.game:
            return
        if not self.redo_stack:
            return
        board = self.game.board.board
        move = self.redo_stack.pop()
        if move not in board.legal_moves:
            self.redo_stack.clear()
            return
        mover = board.turn
        board.push(move)
        if self.increment_seconds > 0:
            if mover == chess.WHITE:
                self.white_time += self.increment_seconds
            else:
                self.black_time += self.increment_seconds
        self.game.board.cached_legal_moves = None
        self.game.moves_history.append(move.uci())
        self.game.current_turn = board.turn
        self.ui.last_move = move.uci()
        self.ui.selected_square = None
        self.ui.valid_moves = []
        self.ui.clear_game_result()
        self.game_over = False
        self.time_loss_text = ""
        self.last_timer_tick = time.time()
        self.position_token += 1
        with self.ai_state_lock:
            self.ai_pending_move = None
        if self.game.is_game_over():
            self._update_game_result_text()

    def _toggle_arrow(self, from_square, to_square):
        if from_square is None or to_square is None or from_square == to_square:
            return
        arrow = (from_square, to_square)
        if arrow in self.arrows:
            self.arrows.remove(arrow)
        else:
            self.arrows.append(arrow)

    def _maybe_make_ai_move(self):
        if self.state != "GAME" or self.game_over:
            return
        now_ms = pygame.time.get_ticks()
        if now_ms - self.last_ai_move_ms < self.ai_move_interval_ms:
            return

        current_turn = self.game.board.board.turn
        ai_color = None
        if self.mode == "AI_AI":
            ai_color = current_turn
        elif self.mode == "HUMAN_AI" and current_turn != self.human_color:
            ai_color = current_turn

        if ai_color is None:
            return

        pending = None
        with self.ai_state_lock:
            if self.ai_pending_move is not None:
                pending = self.ai_pending_move
                self.ai_pending_move = None

        if pending is not None:
            pending_token, pending_color, pending_move = pending
            if (
                pending_token == self.position_token
                and pending_color == current_turn
                and pending_move
            ):
                self._apply_move(pending_move)
                self.last_ai_move_ms = now_ms
            elif pending_token == self.position_token and pending_move is None:
                self._update_game_result_text()
            return

        with self.ai_state_lock:
            if self.ai_thinking:
                return
            self.ai_thinking = True
            self.ai_thinking_color = ai_color
            token = self.position_token

        board_snapshot = self.game.board.copy()
        think_seconds = max(1, int(self.base_time_seconds // 60))

        def worker(snapshot, color, pos_token, think_time):
            move_uci = None
            try:
                thinker = AIAgent(snapshot, color, think_time)
                move = thinker.get_best_move()
                move_uci = move.uci() if move else None
            except Exception:
                move_uci = None
            finally:
                with self.ai_state_lock:
                    self.ai_pending_move = (pos_token, color, move_uci)
                    self.ai_thinking = False
                    self.ai_thinking_color = None

        threading.Thread(
            target=worker,
            args=(board_snapshot, ai_color, token, think_seconds),
            daemon=True,
        ).start()

    def _draw_menu(self):
        self.surface.fill((36, 40, 50))
        title_font = pygame.font.Font(None, 64)
        subtitle_font = pygame.font.Font(None, 32)
        button_font = pygame.font.Font(None, 36)
        section_font = pygame.font.Font(None, 34)

        title = title_font.render("Full Chess", True, (245, 245, 245))
        self.surface.blit(title, title.get_rect(center=(WINDOW_WIDTH // 2, 130)))

        mouse_pos = pygame.mouse.get_pos()
        if self.state == "MENU":
            subtitle = subtitle_font.render("Choose a game mode", True, (210, 210, 210))
            self.surface.blit(subtitle, subtitle.get_rect(center=(WINDOW_WIDTH // 2, 190)))
            for mode, label, rect in self.menu_buttons:
                hovered = rect.collidepoint(mouse_pos)
                color = (79, 153, 247) if hovered else (58, 112, 184)
                pygame.draw.rect(self.surface, color, rect, border_radius=8)
                text = button_font.render(label, True, (255, 255, 255))
                self.surface.blit(text, text.get_rect(center=rect.center))
        elif self.state == "MENU_COLOR":
            subtitle = subtitle_font.render("Choose your color", True, (210, 210, 210))
            self.surface.blit(subtitle, subtitle.get_rect(center=(WINDOW_WIDTH // 2, 190)))
            for key, label, rect in self.color_buttons:
                hovered = rect.collidepoint(mouse_pos)
                if key == "BACK":
                    color = (130, 90, 90) if hovered else (108, 76, 76)
                else:
                    color = (79, 153, 247) if hovered else (58, 112, 184)
                pygame.draw.rect(self.surface, color, rect, border_radius=8)
                text = button_font.render(label, True, (255, 255, 255))
                self.surface.blit(text, text.get_rect(center=rect.center))
        else:
            subtitle = subtitle_font.render("Choose time control", True, (210, 210, 210))
            self.surface.blit(subtitle, subtitle.get_rect(center=(WINDOW_WIDTH // 2, 112)))

            for item in self.time_buttons:
                if item[0] == "HEADER":
                    category = item[1]
                    header = section_font.render(category, True, (240, 240, 240))
                    if category == "Bullet":
                        y = 150
                    elif category == "Blitz":
                        y = 318
                    else:
                        y = 486
                    self.surface.blit(header, ((WINDOW_WIDTH // 2) - 255, y))
                    continue

                _type, label, rect, base_seconds, inc_seconds, _category = item
                hovered = rect.collidepoint(mouse_pos)
                selected = (
                    self.base_time_seconds == base_seconds
                    and self.increment_seconds == inc_seconds
                )
                if selected:
                    color = (101, 170, 82) if hovered else (86, 146, 70)
                else:
                    color = (79, 153, 247) if hovered else (58, 112, 184)
                pygame.draw.rect(self.surface, color, rect, border_radius=8)
                text = button_font.render(label, True, (255, 255, 255))
                self.surface.blit(text, text.get_rect(center=rect.center))

            hovered_back = self.time_back_button.collidepoint(mouse_pos)
            back_color = (130, 90, 90) if hovered_back else (108, 76, 76)
            pygame.draw.rect(self.surface, back_color, self.time_back_button, border_radius=8)
            back_text = button_font.render("Back", True, (255, 255, 255))
            self.surface.blit(back_text, back_text.get_rect(center=self.time_back_button.center))

        pygame.display.flip()

    def _draw_game(self):
        self.ui.white_time = self.white_time
        self.ui.black_time = self.black_time
        self.ui.drawComponent(
            dragging_piece_symbol=self.dragging_piece_symbol,
            drag_pos=self.drag_pos,
            drag_from_square=self.drag_from_square,
            arrows=self.arrows,
            marked_squares=list(self.marked_squares),
            mode_label=self.mode_label,
            starting_fen=self.starting_fen,
            do_flip=False,
        )

        button_font = pygame.font.Font(None, 28)
        for key, rect in self.game_buttons.items():
            pygame.draw.rect(self.surface, (68, 68, 68), rect, border_radius=6)
            if key == "undo":
                label = "Undo (U)"
            elif key == "redo":
                label = "Redo (R)"
            else:
                label = "Menu (M)"
            text = button_font.render(label, True, (255, 255, 255))
            self.surface.blit(text, text.get_rect(center=rect.center))
        pygame.display.flip()

    def _handle_menu_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.state == "MENU":
                for mode, _label, rect in self.menu_buttons:
                    if rect.collidepoint(event.pos):
                        self.pending_mode = mode
                        self.state = "MENU_TIME"
                        return
            elif self.state == "MENU_TIME":
                if self.time_back_button.collidepoint(event.pos):
                    self.pending_mode = None
                    self.state = "MENU"
                    return
                for item in self.time_buttons:
                    if item[0] != "OPTION":
                        continue
                    _type, _label, rect, base_seconds, inc_seconds, _category = item
                    if not rect.collidepoint(event.pos):
                        continue
                    self.base_time_seconds = base_seconds
                    self.increment_seconds = inc_seconds
                    if self.pending_mode == "HUMAN_AI":
                        self.state = "MENU_COLOR"
                    elif self.pending_mode:
                        self.start_game(self.pending_mode)
                    return
            elif self.state == "MENU_COLOR":
                for key, _label, rect in self.color_buttons:
                    if not rect.collidepoint(event.pos):
                        continue
                    if key == "WHITE":
                        self.start_game("HUMAN_AI", human_color=chess.WHITE)
                    elif key == "BLACK":
                        self.start_game("HUMAN_AI", human_color=chess.BLACK)
                    elif key == "RANDOM":
                        self.start_game("HUMAN_AI", human_color=None)
                    elif key == "BACK":
                        self.state = "MENU_TIME"
                    return

    def _handle_game_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_u:
                self._undo_move()
            elif event.key == pygame.K_r:
                self._redo_move()
            elif event.key == pygame.K_m:
                self.go_to_menu()
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for key, rect in self.game_buttons.items():
                if rect.collidepoint(event.pos):
                    if key == "undo":
                        self._undo_move()
                    elif key == "redo":
                        self._redo_move()
                    elif key == "menu":
                        self.go_to_menu()
                    return
            self.left_down_pos = event.pos
            self.left_drag_started = False
            if not self._human_can_move_now():
                return
            square = self.ui.get_square_from_pos(event.pos)
            if square is None:
                return
            piece = self.game.board.board.piece_at(square)
            if piece is None:
                return
            if piece.color != self.game.board.board.turn:
                return
            self.dragging_piece_symbol = piece.symbol()
            self.drag_from_square = square
            self.drag_pos = event.pos
            return

        if event.type == pygame.MOUSEMOTION and self.dragging_piece_symbol:
            if self.left_down_pos:
                dx = event.pos[0] - self.left_down_pos[0]
                dy = event.pos[1] - self.left_down_pos[1]
                if (dx * dx + dy * dy) >= (self.drag_start_threshold ** 2):
                    self.left_drag_started = True
            self.drag_pos = event.pos
            return

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            # If we actually dragged, resolve drag-and-drop move.
            if (
                self.dragging_piece_symbol
                and self.drag_from_square is not None
                and self.left_drag_started
            ):
                target_square = self.ui.get_square_from_pos(event.pos)
                move = self.ui.build_move_from_squares(self.drag_from_square, target_square)
                if move:
                    self._apply_move(move)
                self.dragging_piece_symbol = None
                self.drag_from_square = None
                self.drag_pos = None
                self.left_down_pos = None
                self.left_drag_started = False
                return

            # Otherwise treat as click-to-select / click-to-move.
            if self._human_can_move_now():
                move = self.ui.handle_click(event.pos)
                if move:
                    self._apply_move(move)

            self.dragging_piece_symbol = None
            self.drag_from_square = None
            self.drag_pos = None
            self.left_down_pos = None
            self.left_drag_started = False
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            square = self.ui.get_square_from_pos(event.pos)
            if square is not None:
                self.arrow_start_square = square
            return

        if event.type == pygame.MOUSEBUTTONUP and event.button == 3:
            if self.arrow_start_square is not None:
                end_square = self.ui.get_square_from_pos(event.pos)
                if end_square == self.arrow_start_square:
                    if end_square in self.marked_squares:
                        self.marked_squares.remove(end_square)
                    else:
                        self.marked_squares.add(end_square)
                else:
                    self._toggle_arrow(self.arrow_start_square, end_square)
            self.arrow_start_square = None

    def run(self):
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    break
                if self.state in ("MENU", "MENU_COLOR", "MENU_TIME"):
                    self._handle_menu_event(event)
                elif self.state == "GAME":
                    self._handle_game_event(event)

            if self.state in ("MENU", "MENU_COLOR", "MENU_TIME"):
                self._draw_menu()
            elif self.state == "GAME":
                self._update_timers()
                self._maybe_make_ai_move()
                self._draw_game()

            self.clock.tick(FPS)

        pygame.quit()


if __name__ == "__main__":
    UnifiedChessApp().run()
