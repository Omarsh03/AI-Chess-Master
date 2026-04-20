import os
import math
import random
import time
import threading
import subprocess
import pygame
import chess
import numpy as np

from ai_agent import AIAgent
from game import GameState
from learning import LearningBook
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
        global WINDOW_WIDTH, WINDOW_HEIGHT
        pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
        pygame.init()
        self.windowed_size = (1040, 700)
        display_info = pygame.display.Info()
        WINDOW_WIDTH = max(self.windowed_size[0], display_info.current_w)
        WINDOW_HEIGHT = max(self.windowed_size[1], display_info.current_h)
        WINDOW_WIDTH, WINDOW_HEIGHT = self.windowed_size
        self.surface = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("@Chess")
        self.clock = pygame.time.Clock()
        self.running = True
        self.is_fullscreen = False
        self.sound_enabled = False
        self.sounds = {}
        self.sound_error = None
        self.last_check_announce_ms = 0
        self._init_audio()
        self.menu_pieces = self._load_menu_pieces()
        self.menu_logo = self._load_menu_logo()
        self.bg_particles = []
        self._init_menu_background_particles()

        # Persistent learning book: loads accumulated experience from
        # previous runs and is updated after every completed game.
        self.learning_book = LearningBook()
        # Remembers whether the current game was already ingested so we
        # don't double-record on repeated result-text updates.
        self._game_recorded = False
        # Post-game auto-play (review): steps one ply forward every
        # `auto_play_interval_ms`, watchable like a replay video.
        self.auto_play_active = False
        self.auto_play_interval_ms = 1800
        self.auto_play_last_step_ms = 0

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
        self.marked_squares = []

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
        self.turn_started_at = time.time()
        self.move_log = []
        self.white_label = "White"
        self.black_label = "Black"
        self.white_is_bot = False
        self.black_is_bot = False

        self.menu_buttons = []
        self.color_buttons = []
        self.time_buttons = []
        self.time_back_button = None
        self.game_buttons = {}
        self._build_menu_buttons()
        self._build_color_buttons()
        self._build_time_buttons()

    def _shape_audio_for_mixer(self, mono_pcm):
        mixer_cfg = pygame.mixer.get_init()
        if mixer_cfg is None:
            return mono_pcm
        channels = mixer_cfg[2]
        if channels <= 1:
            return mono_pcm
        return np.repeat(mono_pcm[:, np.newaxis], channels, axis=1)

    def _make_tone(self, frequency_hz, duration_seconds, volume=0.35):
        sample_rate = 44100
        samples = max(1, int(sample_rate * duration_seconds))
        t = np.linspace(0, duration_seconds, samples, endpoint=False)
        wave = np.sin(2 * np.pi * frequency_hz * t)
        # Simple decay envelope to avoid click/pop at tone end.
        envelope = np.linspace(1.0, 0.0, samples)
        audio = wave * envelope * volume
        pcm = np.int16(audio * 32767)
        pcm = self._shape_audio_for_mixer(pcm)
        return pygame.sndarray.make_sound(pcm)

    def _make_tone_sequence(self, notes, volume=0.35):
        sample_rate = 44100
        chunks = []
        for frequency_hz, duration_seconds in notes:
            samples = max(1, int(sample_rate * duration_seconds))
            t = np.linspace(0, duration_seconds, samples, endpoint=False)
            wave = np.sin(2 * np.pi * frequency_hz * t)
            envelope = np.linspace(1.0, 0.0, samples)
            chunks.append(wave * envelope)
        audio = np.concatenate(chunks) * volume
        pcm = np.int16(audio * 32767)
        pcm = self._shape_audio_for_mixer(pcm)
        return pygame.sndarray.make_sound(pcm)

    def _make_move_click_sound(self, volume=0.42):
        """
        Create a short "wooden piece move" click:
        a soft transient + warm body tone + tiny high-frequency tick.
        """
        sample_rate = 44100
        duration_seconds = 0.11
        samples = max(1, int(sample_rate * duration_seconds))
        t = np.linspace(0, duration_seconds, samples, endpoint=False)

        # Warm body resonance.
        body = (
            0.68 * np.sin(2 * np.pi * 190 * t)
            + 0.36 * np.sin(2 * np.pi * 320 * t)
            + 0.18 * np.sin(2 * np.pi * 510 * t)
        )
        body_envelope = np.exp(-30.0 * t)

        # Fast percussive attack.
        rng = np.random.default_rng(7)
        noise = rng.normal(0.0, 1.0, samples)
        noise_envelope = np.exp(-180.0 * t)
        attack = noise * noise_envelope * 0.20

        # Small bright tick to improve clarity on laptop speakers.
        tick = np.sin(2 * np.pi * 1500 * t) * np.exp(-85.0 * t) * 0.08

        audio = (body * body_envelope) + attack + tick
        peak = np.max(np.abs(audio))
        if peak > 0:
            audio = audio / peak
        audio = audio * volume

        pcm = np.int16(audio * 32767)
        pcm = self._shape_audio_for_mixer(pcm)
        return pygame.sndarray.make_sound(pcm)

    def _init_audio(self):
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self.sounds = {
                "move": self._make_move_click_sound(volume=0.42),
                "check": self._make_tone_sequence(
                    [(740, 0.07), (988, 0.09)], volume=0.35
                ),
                "checkmate": self._make_tone_sequence(
                    [(880, 0.08), (740, 0.08), (523, 0.16)], volume=0.4
                ),
            }
            self.sound_enabled = True
            self.sound_error = None
        except Exception as exc:
            self.sound_enabled = False
            self.sounds = {}
            self.sound_error = str(exc)

    def _play_sound(self, sound_name):
        if not self.sound_enabled:
            return
        sound = self.sounds.get(sound_name)
        if sound is None:
            return
        try:
            sound.play()
        except Exception:
            pass

    def _speak_check_async(self):
        now_ms = pygame.time.get_ticks()
        # Avoid repeated voice spam on near-consecutive check positions.
        if now_ms - self.last_check_announce_ms < 1200:
            return
        self.last_check_announce_ms = now_ms
        threading.Thread(target=self._speak_check, daemon=True).start()

    def _speak_check(self):
        # Windows TTS via PowerShell / SAPI.
        command = (
            "Add-Type -AssemblyName System.Speech;"
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer;"
            '$s.Rate = 0; $s.Volume = 100; $s.Speak("Check");'
        )
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", command],
                check=False,
                capture_output=True,
            )
        except Exception:
            pass

    def _rebuild_ui_for_current_surface(self):
        if not self.ui or not self.game:
            return
        previous_ui = self.ui
        rebuilt = UserInterface(self.surface, self.game.board)
        rebuilt.selected_square = previous_ui.selected_square
        rebuilt.last_move = previous_ui.last_move
        rebuilt.valid_moves = list(previous_ui.valid_moves)
        rebuilt.playerColor = previous_ui.playerColor
        rebuilt.allow_both_colors = previous_ui.allow_both_colors
        rebuilt.white_time = previous_ui.white_time
        rebuilt.black_time = previous_ui.black_time
        rebuilt.show_clock = previous_ui.show_clock
        rebuilt.game_result_text = previous_ui.game_result_text
        rebuilt.game_winner_color = previous_ui.game_winner_color
        rebuilt.game_termination = previous_ui.game_termination
        rebuilt.fallen_loser_color = previous_ui.fallen_loser_color
        rebuilt.fall_anim_start_ms = previous_ui.fall_anim_start_ms
        self.ui = rebuilt
        self._build_game_buttons()

    def _set_fullscreen(self, fullscreen):
        global WINDOW_WIDTH, WINDOW_HEIGHT
        if fullscreen:
            display_info = pygame.display.Info()
            WINDOW_WIDTH = max(self.windowed_size[0], display_info.current_w)
            WINDOW_HEIGHT = max(self.windowed_size[1], display_info.current_h)
            self.surface = pygame.display.set_mode(
                (WINDOW_WIDTH, WINDOW_HEIGHT), pygame.FULLSCREEN
            )
            self.is_fullscreen = True
        else:
            WINDOW_WIDTH, WINDOW_HEIGHT = self.windowed_size
            self.surface = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
            self.is_fullscreen = False

        self._build_menu_buttons()
        self._build_color_buttons()
        self._build_time_buttons()
        self._rebuild_ui_for_current_surface()

    def _handle_display_shortcuts(self, event):
        if event.type != pygame.KEYDOWN:
            return False
        if event.key == pygame.K_F11:
            self._set_fullscreen(not self.is_fullscreen)
            return True
        if event.key == pygame.K_ESCAPE and self.is_fullscreen:
            self._set_fullscreen(False)
            return True
        return False

    def _load_menu_pieces(self):
        base = os.path.dirname(os.path.abspath(__file__))
        order = ['king', 'queen', 'knight', 'bishop', 'rook', 'pawn']
        result = {'white': [], 'black': []}
        for k in order:
            for color in ('white', 'black'):
                path = os.path.join(base, "assets", "pieces", f"{color}_{k}.png")
                try:
                    img = pygame.image.load(path).convert_alpha()
                    result[color].append(img)
                except Exception:
                    result[color].append(None)
        return result

    def _load_menu_logo(self):
        """
        Load ``assets/logo.png`` as a transparent-background surface so it
        sits naturally on the dark menu. Returns ``None`` if the file is
        missing, in which case we fall back to the legacy knight + title.

        White / near-white pixels in the source are softly faded out with
        a smooth threshold curve, which keeps anti-aliased edges crisp
        instead of producing jagged holes.
        """
        base = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base, "assets", "logo.png")
        if not os.path.isfile(path):
            return None
        try:
            raw = pygame.image.load(path).convert_alpha()
        except Exception:
            return None

        # Copy into an independent surface we can freely edit.
        surf = raw.copy()
        try:
            rgb = pygame.surfarray.pixels3d(surf)
            alpha = pygame.surfarray.pixels_alpha(surf)
        except Exception:
            # Some locked/indexed surfaces can't expose pixel arrays —
            # fall back to the raw image.
            return raw

        # How "white" each pixel is == min(R, G, B). Pure white → 255.
        min_channel = np.minimum(np.minimum(rgb[:, :, 0], rgb[:, :, 1]), rgb[:, :, 2])

        # Soft threshold: anything under 200 stays fully opaque; anything
        # over 238 is erased; in between we interpolate for clean edges.
        lower, upper = 200, 238
        m = min_channel.astype(np.int16)
        opaque_mask = m <= lower
        transparent_mask = m >= upper
        fade = ((upper - m) * 255 // (upper - lower)).clip(0, 255)
        new_alpha = fade.astype(np.uint8)
        new_alpha[opaque_mask] = 255
        new_alpha[transparent_mask] = 0
        # Preserve any original transparency the file may already have.
        alpha[:] = np.minimum(alpha, new_alpha)

        del rgb, alpha
        return surf

    def _init_menu_background_particles(self):
        """
        Build a small set of slowly-drifting, semi-transparent chess pieces
        that float across the menu background, evoking pieces in space.
        Images are pre-rotated and alpha-baked once for a cheap per-frame blit.
        """
        self.bg_particles = []
        rng = random.Random(20251997)
        piece_indices = [0, 1, 2, 3, 4, 5]
        count = 16
        attempts = 0
        while len(self.bg_particles) < count and attempts < count * 4:
            attempts += 1
            color = rng.choice(['white', 'black'])
            idx = rng.choice(piece_indices)
            img = self.menu_pieces[color][idx]
            if img is None:
                continue
            size = rng.choice([56, 72, 96, 128, 160])
            rotation = rng.uniform(-24.0, 24.0)
            # Heavier pieces stay more transparent so they never fight the UI.
            alpha = rng.randint(26, 62) if size >= 96 else rng.randint(34, 78)
            try:
                scaled = pygame.transform.smoothscale(img, (size, size))
                rotated = pygame.transform.rotate(scaled, rotation)
            except Exception:
                continue
            rotated.set_alpha(alpha)
            self.bg_particles.append({
                'img': rotated,
                'cx_frac': rng.uniform(-0.05, 1.05),
                'cy_frac': rng.uniform(-0.05, 1.05),
                'amp_x': rng.uniform(30.0, 95.0),
                'amp_y': rng.uniform(22.0, 70.0),
                'speed_x': rng.uniform(0.00007, 0.00022) * rng.choice([-1, 1]),
                'speed_y': rng.uniform(0.00006, 0.00018) * rng.choice([-1, 1]),
                'phase_x': rng.uniform(0.0, math.tau),
                'phase_y': rng.uniform(0.0, math.tau),
                'drift_x': rng.uniform(-0.000035, 0.000035),
                'drift_y': rng.uniform(-0.000028, 0.000028),
            })

    def _draw_menu_background(self, t):
        """
        Paint the elegant deep-space menu backdrop: dark base, a soft radial
        glow, and slowly drifting chess pieces rendered behind the UI.
        """
        W, H = WINDOW_WIDTH, WINDOW_HEIGHT
        self.surface.fill((22, 21, 18))

        # Soft vignette glow behind the title area for cinematic depth.
        glow_radius = max(220, min(W, H) // 2)
        glow = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
        for r in range(glow_radius, 0, -18):
            intensity = max(0, 36 - int(36 * (r / glow_radius)))
            if intensity <= 0:
                continue
            pygame.draw.circle(
                glow,
                (129, 182, 76, intensity),
                (glow_radius, glow_radius),
                r,
            )
        self.surface.blit(
            glow,
            glow.get_rect(center=(W // 2, int(H * 0.28))),
        )

        # Drifting pieces.
        for p in self.bg_particles:
            fx = (p['cx_frac'] + p['drift_x'] * t) % 1.2 - 0.1
            fy = (p['cy_frac'] + p['drift_y'] * t) % 1.2 - 0.1
            px = fx * W + p['amp_x'] * math.sin(t * p['speed_x'] + p['phase_x'])
            py = fy * H + p['amp_y'] * math.cos(t * p['speed_y'] + p['phase_y'])
            rect = p['img'].get_rect(center=(int(px), int(py)))
            self.surface.blit(p['img'], rect)

        # Top accent bar on top of the background.
        pygame.draw.rect(self.surface, (129, 182, 76), pygame.Rect(0, 0, W, 3))

    def _build_menu_buttons(self):
        center_x = WINDOW_WIDTH // 2
        button_w = 320
        button_h = 56
        gap = 18
        entries = [
            ("HUMAN_AI", "Human vs AI"),
            ("AI_AI", "AI vs AI"),
            ("HUMAN_HUMAN", "Human vs Human"),
        ]
        # Anchor the button stack below the title/divider block and leave
        # comfortable breathing room at the bottom of the menu.
        top = max(300, int(WINDOW_HEIGHT * 0.46))
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
        cx = WINDOW_WIDTH // 2
        card_w, card_h = 210, 230
        gap = 24
        card_top = 195
        self.color_buttons = [
            ("WHITE", "White",  pygame.Rect(cx - gap//2 - card_w, card_top, card_w, card_h)),
            ("BLACK", "Black",  pygame.Rect(cx + gap//2,           card_top, card_w, card_h)),
            ("RANDOM", "Random Color", pygame.Rect(cx - 140, card_top + card_h + 22, 280, 50)),
            # Back sits in the top-left corner as a compact LED pill so it
            # doesn't collide with the shared footer at the bottom.
            ("BACK",   "Back",         pygame.Rect(24, 22, 128, 42)),
        ]

    def _build_time_buttons(self):
        self.time_buttons = []
        top = 138
        left = (WINDOW_WIDTH // 2) - 260
        button_w = 160
        button_h = 46
        col_gap = 16
        row_gap = 12
        section_gap = 40

        y = top
        for category, options in TIME_CONTROL_GROUPS:
            header_y = y
            self.time_buttons.append(("HEADER", category, header_y))
            y += 36
            for col, (label, base_seconds, increment_seconds) in enumerate(options):
                x = left + col * (button_w + col_gap)
                rect = pygame.Rect(x, y, button_w, button_h)
                self.time_buttons.append(
                    ("OPTION", label, rect, base_seconds, increment_seconds, category)
                )
            y += button_h + row_gap + section_gap

        # No Limit as its own animated category row
        nolimit_w = button_w * 3 + col_gap * 2
        nolimit_rect = pygame.Rect(left, y, nolimit_w, button_h)
        self.time_buttons.append(("NOLIMIT", "No Limit", nolimit_rect, -1, 0))

        # Compact LED-style Back button anchored in the top-left so the
        # footer at the bottom stays clean on every menu screen.
        self.time_back_button = pygame.Rect(24, 22, 128, 42)

    def _format_time_control(self, base_seconds, increment_seconds):
        if base_seconds < 0:
            return "No Limit"
        base_minutes = int(base_seconds // 60)
        if increment_seconds > 0:
            return f"{base_minutes}+{int(increment_seconds)}"
        return f"{base_minutes}+0"

    def _build_game_buttons(self):
        if not self.ui:
            return
        panel_x   = self.ui.sidebar_x + 12
        panel_w   = self.surface.get_width() - panel_x - self.ui.margin - 8
        arrow_sz  = 42
        gap       = 8
        row_h     = 42
        bottom_y  = self.surface.get_height() - self.ui.margin - 12
        row_y     = bottom_y - row_h

        undo_rect = pygame.Rect(panel_x, row_y, arrow_sz, arrow_sz)
        redo_rect = pygame.Rect(
            panel_x + arrow_sz + gap, row_y, arrow_sz, arrow_sz
        )
        menu_x = panel_x + (arrow_sz + gap) * 2 + gap
        menu_w = max(80, panel_x + panel_w - menu_x)
        menu_rect = pygame.Rect(menu_x, row_y, menu_w, arrow_sz)

        # Wide replay/pause button sits just above the arrow row. It's
        # only drawn when the game is over, but we always reserve the
        # rect so layout/click geometry is stable.
        play_h = 42
        play_rect = pygame.Rect(
            panel_x, row_y - play_h - 10, panel_w, play_h
        )

        self.game_buttons = {
            "undo": undo_rect,
            "redo": redo_rect,
            "menu": menu_rect,
            "play": play_rect,
        }

    def _record_finished_game_if_needed(self, winner_color):
        """
        Ingest a just-finished game into the persistent learning book,
        exactly once per game. Runs in a background thread so a slow
        disk write never stalls the UI. Safe to call from any end-of-
        game path (time loss, checkmate, stalemate, resignation, ...).
        """
        if self._game_recorded:
            return
        if self.learning_book is None or not self.move_log:
            return
        self._game_recorded = True
        move_log_snapshot = list(self.move_log)

        def worker():
            try:
                self.learning_book.record_game(move_log_snapshot, winner_color)
                self.learning_book.save()
            except Exception:
                # Never let a learning-book bug crash the app.
                pass

        threading.Thread(target=worker, daemon=True).start()

    def start_game(self, mode, human_color=None):
        self.mode = mode
        tc_label = self._format_time_control(self.base_time_seconds, self.increment_seconds)
        self.mode_label = f"{MODE_LABELS.get(mode, mode)} | {tc_label}"
        self.state = "GAME"
        self.game_over = False
        self._game_recorded = False
        self.auto_play_active = False
        self.auto_play_last_step_ms = 0
        self.time_loss_text = ""
        self.dragging_piece_symbol = None
        self.drag_from_square = None
        self.drag_pos = None
        self.left_down_pos = None
        self.left_drag_started = False
        self.arrow_start_square = None
        self.arrows = []
        self.marked_squares = []
        self.redo_stack = []
        self.move_log = []
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
        self.ui.show_clock = self.base_time_seconds >= 0

        if self.base_time_seconds >= 0:
            self.white_time = float(self.base_time_seconds)
            self.black_time = float(self.base_time_seconds)
        else:
            self.white_time = 0.0
            self.black_time = 0.0
        self.last_timer_tick = time.time()

        self.human_color = None
        self.ai_white = None
        self.ai_black = None
        self.white_label = "White Player"
        self.black_label = "Black Player"
        self.white_is_bot = False
        self.black_is_bot = False
        if mode == "HUMAN_AI":
            if human_color is None:
                self.human_color = random.choice([chess.WHITE, chess.BLACK])
            else:
                self.human_color = human_color
            # Flip the board so the human's pieces are always at the bottom.
            self.ui.playerColor = self.human_color
            chosen = "White" if self.human_color == chess.WHITE else "Black"
            self.mode_label = (
                f"{MODE_LABELS['HUMAN_AI']} (You: {chosen}) | "
                f"{self._format_time_control(self.base_time_seconds, self.increment_seconds)}"
            )
            self.ai_white = None if self.human_color == chess.WHITE else AIAgent(
                self.game.board, chess.WHITE, 5, learning_book=self.learning_book
            )
            self.ai_black = None if self.human_color == chess.BLACK else AIAgent(
                self.game.board, chess.BLACK, 5, learning_book=self.learning_book
            )
            if self.human_color == chess.WHITE:
                self.white_label = "You"
                self.black_label = "AI Bot"
                self.white_is_bot = False
                self.black_is_bot = True
            else:
                self.white_label = "AI Bot"
                self.black_label = "You"
                self.white_is_bot = True
                self.black_is_bot = False
        elif mode == "AI_AI":
            self.ai_white = AIAgent(
                self.game.board, chess.WHITE, 5, learning_book=self.learning_book
            )
            self.ai_black = AIAgent(
                self.game.board, chess.BLACK, 5, learning_book=self.learning_book
            )
            self.white_label = "AI White"
            self.black_label = "AI Black"
            self.white_is_bot = True
            self.black_is_bot = True

        self._build_game_buttons()
        self.last_ai_move_ms = pygame.time.get_ticks()
        self.turn_started_at = time.time()

    def go_to_menu(self):
        self.state = "MENU"
        self.game = None
        self.ui = None
        self.mode = None
        self.pending_mode = None
        self.mode_label = ""
        self.move_log = []
        self.auto_play_active = False
        with self.ai_state_lock:
            self.ai_pending_move = None
            self.ai_thinking = False
            self.ai_thinking_color = None
        self.position_token += 1

    # ------------------------------------------------------------------ #
    # Post-game auto-play (replay the finished game one ply at a time)
    # ------------------------------------------------------------------ #
    def _toggle_auto_play(self):
        """Play/Stop toggle for the post-game replay."""
        if self.state != "GAME" or not self.game_over or not self.move_log:
            return
        if self.auto_play_active:
            self.auto_play_active = False
            return
        # If we're already at the end, jump to the start so PLAY starts
        # the replay from move 1. Otherwise resume from the current ply.
        current_ply = len(self.game.board.board.move_stack)
        if current_ply >= len(self.move_log):
            self._go_to_review_position(0)
        self.auto_play_active = True
        # Schedule the first step a touch earlier so the user feels
        # immediate feedback when they press Play.
        now_ms = pygame.time.get_ticks()
        self.auto_play_last_step_ms = now_ms - (self.auto_play_interval_ms - 400)

    def _tick_auto_play(self):
        """Advance one ply if enough time passed; stop at the end."""
        if not self.auto_play_active or not self.game_over or not self.game:
            return
        now_ms = pygame.time.get_ticks()
        if now_ms - self.auto_play_last_step_ms < self.auto_play_interval_ms:
            return
        current_ply = len(self.game.board.board.move_stack)
        if current_ply >= len(self.move_log):
            self.auto_play_active = False
            return
        self._go_to_review_position(current_ply + 1)
        # Keep the latest played move visible in the scrolling list.
        if self.ui is not None:
            self.ui.ensure_ply_visible(current_ply + 1)
        self.auto_play_last_step_ms = now_ms

    def _human_can_move_now(self):
        if self.state != "GAME" or self.game_over or self.mode == "AI_AI":
            return False
        # HUMAN_AI peek-mode: player is looking at an earlier position and
        # must Redo back to the latest before they can play again.
        if self._is_in_peek_mode():
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
        if self.base_time_seconds < 0:
            self.last_timer_tick = time.time()
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
            self._record_finished_game_if_needed(winner_color)

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
            self._record_finished_game_if_needed(winner_color)

    def _apply_move(self, move_uci):
        if not move_uci:
            return False
        think_seconds = max(0.0, time.time() - self.turn_started_at)
        san = move_uci
        try:
            san = self.game.board.board.san(chess.Move.from_uci(move_uci))
        except Exception:
            san = move_uci
        mover = self.game.board.board.turn
        if self.game.make_move(move_uci):
            board_state = self.game.board.board
            if board_state.is_checkmate():
                self._play_sound("checkmate")
            elif board_state.is_check():
                self._play_sound("check")
                self._speak_check_async()
            else:
                self._play_sound("move")
            # Every move wipes the shared annotations so both players start
            # the next turn with a clean board.
            self.arrows = []
            self.marked_squares = []
            if self.increment_seconds > 0:
                if mover == chess.WHITE:
                    self.white_time += self.increment_seconds
                else:
                    self.black_time += self.increment_seconds
            self.ui.last_move = move_uci
            self.ui.selected_square = None
            self.ui.valid_moves = []
            self.move_log.append(
                {
                    "side": mover,
                    "san": san,
                    "uci": move_uci,
                    "think_seconds": think_seconds,
                }
            )
            self.last_timer_tick = time.time()
            self.turn_started_at = time.time()
            self.redo_stack.clear()
            self.position_token += 1
            with self.ai_state_lock:
                self.ai_pending_move = None
            if self.game.is_game_over():
                self._update_game_result_text()
            return True
        return False

    def _go_to_review_position(self, target_ply):
        """
        Step the displayed position forward/backward without touching
        game_over state or move_log — used for reviewing the game after
        it has already finished.
        """
        if not self.game or self.ui is None:
            return
        board = self.game.board.board
        target_ply = max(0, min(target_ply, len(self.move_log)))

        # Rewind.
        while len(board.move_stack) > target_ply:
            self.redo_stack.append(board.pop())
        # Fast-forward.
        while len(board.move_stack) < target_ply and self.redo_stack:
            nxt = self.redo_stack.pop()
            if nxt not in board.legal_moves:
                self.redo_stack.clear()
                break
            board.push(nxt)

        self.game.board.cached_legal_moves = None
        self.game.current_turn = board.turn
        self.ui.last_move = (
            board.move_stack[-1].uci() if board.move_stack else None
        )
        self.ui.selected_square = None
        self.ui.valid_moves = []
        self.arrows = []
        self.marked_squares = []
        # Victory/defeat ornaments only belong on the true final
        # position — hide them while the user is peeking at earlier
        # plies and re-show them when they scrub back to the end.
        if self.game_over and self.ui is not None:
            at_final = len(board.move_stack) == len(self.move_log)
            if self.ui.show_end_effects != at_final:
                self.ui.show_end_effects = at_final
                if at_final:
                    self.ui.end_anim_start_ms = pygame.time.get_ticks()
        self.position_token += 1
        with self.ai_state_lock:
            self.ai_pending_move = None

    def _undo_single_ply(self):
        """Pop one move off the live board — returns True if it popped."""
        if not self.game:
            return False
        board = self.game.board.board
        if not board.move_stack:
            return False
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
        if self.move_log:
            self.move_log.pop()
        return True

    def _redo_single_ply(self):
        """Re-apply the most recently undone move. Returns True on success."""
        if not self.game or not self.redo_stack:
            return False
        board = self.game.board.board
        move = self.redo_stack[-1]
        if move not in board.legal_moves:
            self.redo_stack.clear()
            return False
        self.redo_stack.pop()
        mover = board.turn
        san = move.uci()
        try:
            san = board.san(move)
        except Exception:
            san = move.uci()
        board.push(move)
        if self.increment_seconds > 0:
            if mover == chess.WHITE:
                self.white_time += self.increment_seconds
            else:
                self.black_time += self.increment_seconds
        self.game.board.cached_legal_moves = None
        self.game.moves_history.append(move.uci())
        self.game.current_turn = board.turn
        self.move_log.append(
            {
                "side": mover,
                "san": san,
                "uci": move.uci(),
                "think_seconds": 0.0,
            }
        )
        return True

    def _is_in_peek_mode(self):
        """
        Live HUMAN_AI 'peek' mode: the player rewound the position with
        Undo but hasn't returned to the latest position yet. We keep
        move_log intact, so this is simply whether the live board is
        behind the recorded history.
        """
        if not self.game:
            return False
        return (
            self.mode == "HUMAN_AI"
            and not self.game_over
            and len(self.game.board.board.move_stack) < len(self.move_log)
        )

    def _undo_move(self):
        if self.state != "GAME" or not self.game:
            return
        board = self.game.board.board
        if not board.move_stack:
            return

        # Game-over review: navigate through history without touching state.
        if self.game_over:
            self._go_to_review_position(len(board.move_stack) - 1)
            return

        # HUMAN_AI: peek-only navigation. The move_log is preserved so
        # the player cannot drop a move, pick a different piece, and
        # cheat the engine. They can only Redo back to the latest
        # position to keep playing.
        if self.mode == "HUMAN_AI" and self.human_color is not None:
            current_ply = len(board.move_stack)
            target = current_ply - 1
            # Land on the human's turn when possible so peeking at the
            # position "right before you played" is one click away.
            if target > 0:
                target_turn = chess.WHITE if target % 2 == 0 else chess.BLACK
                if target_turn != self.human_color:
                    target = max(0, target - 1)
            self._go_to_review_position(target)
            return

        # HUMAN_HUMAN / AI_AI: traditional undo that rewrites move_log.
        if not self._undo_single_ply():
            return
        self.ui.last_move = (
            board.move_stack[-1].uci() if board.move_stack else None
        )
        self.ui.selected_square = None
        self.ui.valid_moves = []
        self.arrows = []
        self.marked_squares = []
        self.ui.clear_game_result()
        self.game_over = False
        self.time_loss_text = ""
        self.last_timer_tick = time.time()
        self.turn_started_at = time.time()
        self.position_token += 1
        with self.ai_state_lock:
            self.ai_pending_move = None

    def _redo_move(self):
        if self.state != "GAME" or not self.game:
            return
        board = self.game.board.board

        # Review mode: navigate forward through the already-recorded game.
        if self.game_over:
            self._go_to_review_position(len(board.move_stack) + 1)
            return

        # HUMAN_AI peek-forward: step forward in the recorded game.
        if self.mode == "HUMAN_AI" and self.human_color is not None:
            current_ply = len(board.move_stack)
            max_ply = len(self.move_log)
            if current_ply >= max_ply:
                return
            target = current_ply + 1
            if target < max_ply:
                target_turn = chess.WHITE if target % 2 == 0 else chess.BLACK
                if target_turn != self.human_color:
                    target = min(max_ply, target + 1)
            self._go_to_review_position(target)
            return

        if not self.redo_stack:
            return
        if not self._redo_single_ply():
            return
        self.ui.last_move = (
            board.move_stack[-1].uci() if board.move_stack else None
        )
        self.ui.selected_square = None
        self.ui.valid_moves = []
        self.arrows = []
        self.marked_squares = []
        self.ui.clear_game_result()
        self.game_over = False
        self.time_loss_text = ""
        self.last_timer_tick = time.time()
        self.turn_started_at = time.time()
        self.position_token += 1
        with self.ai_state_lock:
            self.ai_pending_move = None
        if self.game.is_game_over():
            self._update_game_result_text()

    def _clear_arrows_for_color(self, color):
        self.arrows = [
            arrow
            for arrow in self.arrows
            if arrow["owner"] != color
        ]

    def _clear_markers_for_color(self, color):
        self.marked_squares = [
            marker
            for marker in self.marked_squares
            if marker["owner"] != color
        ]

    def _toggle_arrow(self, from_square, to_square):
        if from_square is None or to_square is None or from_square == to_square:
            return
        piece = self.game.board.board.piece_at(from_square) if self.game else None
        owner = piece.color if piece else (self.game.board.board.turn if self.game else None)
        existing = next(
            (a for a in self.arrows if a["from"] == from_square and a["to"] == to_square and a["owner"] == owner),
            None,
        )
        if existing:
            self.arrows.remove(existing)
            # re-number remaining arrows
            for i, a in enumerate(self.arrows):
                a["number"] = i + 1
        else:
            self.arrows.append({"from": from_square, "to": to_square, "owner": owner, "number": len(self.arrows) + 1})

    def _get_visible_arrows(self):
        return list(self.arrows)

    def _toggle_marker(self, square):
        if square is None:
            return
        owner = self.game.board.board.turn if self.game else None
        marker = {"square": square, "owner": owner}
        if marker in self.marked_squares:
            self.marked_squares.remove(marker)
        else:
            self.marked_squares.append(marker)

    def _get_visible_marked_squares(self):
        return [marker["square"] for marker in self.marked_squares]

    def _maybe_make_ai_move(self):
        if self.state != "GAME" or self.game_over:
            return
        # Freeze the AI while the player is peeking at a past position —
        # it only resumes once Redo brings them back to the latest ply.
        if self._is_in_peek_mode():
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
        if self.base_time_seconds < 0:
            think_seconds = 6
        else:
            think_seconds = max(2, min(25, int(self.base_time_seconds // 30)))

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
        W, H = WINDOW_WIDTH, WINDOW_HEIGHT
        BG        = (22, 21, 18)
        ACCENT    = (129, 182, 76)
        BTN_DARK  = (42, 40, 36)
        BTN_BORD  = (66, 63, 58)
        TEXT_PRI  = (212, 210, 202)
        TEXT_MUT  = (110, 107, 100)
        RED_BG    = (48, 28, 28)
        RED_BORD  = (105, 55, 55)
        RED_FG    = (210, 170, 170)

        t = pygame.time.get_ticks()
        self._draw_menu_background(t)

        btn_font  = pygame.font.Font(None, 34)
        cat_font  = pygame.font.Font(None, 24)
        mouse_pos = pygame.mouse.get_pos()

        # ── helpers ──────────────────────────────────────────────────────
        def draw_btn(rect, label, hovered, selected=False, danger=False, font=None):
            f = font or btn_font
            if danger:
                bg   = (65, 35, 35) if hovered else RED_BG
                bord = RED_BORD
                fg   = RED_FG
            elif selected:
                bg   = (55, 82, 30) if hovered else (44, 65, 22)
                bord = ACCENT
                fg   = (195, 230, 150)
            elif hovered:
                bg, bord, fg = ACCENT, ACCENT, BG
            else:
                bg, bord, fg = BTN_DARK, BTN_BORD, TEXT_PRI
            pygame.draw.rect(self.surface, bg,   rect, border_radius=8)
            pygame.draw.rect(self.surface, bord, rect, 1, border_radius=8)
            surf = f.render(label, True, fg)
            self.surface.blit(surf, surf.get_rect(center=rect.center))

        def draw_primary_btn(
            rect,
            label,
            hovered,
            selected=False,
            danger=False,
            font=None,
            label_offset=(0, 0),
            accent_bar=True,
        ):
            """
            Premium button style used across all menu screens: drop shadow,
            subtle vertical gradient, inset top highlight, left accent bar,
            and an outer glow for hover / selected / danger states.
            """
            radius = 12
            f = font or btn_font

            # Soft drop shadow behind the button (kept subtle so the
            # floating background pieces still read through the button).
            shadow = pygame.Surface(
                (rect.width + 16, rect.height + 16), pygame.SRCALPHA
            )
            pygame.draw.rect(
                shadow,
                (0, 0, 0, 70),
                shadow.get_rect().inflate(-6, -6),
                border_radius=radius + 2,
            )
            self.surface.blit(shadow, (rect.x - 8, rect.y - 2))

            if danger:
                if hovered:
                    top_color    = (96, 44, 44)
                    bot_color    = (58, 24, 24)
                    border_color = (190, 110, 110)
                    bar_color    = (210, 130, 130)
                    fg           = (240, 200, 200)
                else:
                    top_color    = (72, 36, 36)
                    bot_color    = RED_BG
                    border_color = RED_BORD
                    bar_color    = (165, 90, 90)
                    fg           = RED_FG
                glow_color = (180, 80, 80)
            elif selected:
                top_color    = (88, 122, 50)
                bot_color    = (44, 65, 22)
                border_color = ACCENT
                bar_color    = (220, 240, 170)
                fg           = (220, 240, 170)
                glow_color   = ACCENT
            elif hovered:
                top_color    = (74, 104, 44)
                bot_color    = (44, 62, 22)
                border_color = ACCENT
                bar_color    = ACCENT
                fg           = (224, 244, 184)
                glow_color   = ACCENT
            else:
                top_color    = (54, 52, 46)
                bot_color    = (34, 32, 28)
                border_color = (78, 74, 68)
                bar_color    = (98, 138, 58)
                fg           = TEXT_PRI
                glow_color   = None

            # Outer glow: hover (static) + selected (pulse).
            if glow_color is not None and (hovered or selected or danger):
                if selected:
                    pulse_a = 46 + int(20 * math.sin(t / 380))
                else:
                    pulse_a = 42 if hovered else 30
                glow = pygame.Surface(
                    (rect.width + 28, rect.height + 28), pygame.SRCALPHA
                )
                pygame.draw.rect(
                    glow,
                    (*glow_color, max(10, pulse_a)),
                    glow.get_rect(),
                    border_radius=radius + 8,
                )
                self.surface.blit(glow, (rect.x - 14, rect.y - 14))

            # Build a rounded vertical gradient into its own surface.
            # Semi-transparent fill so the drifting pieces remain visible
            # through the button while keeping the label clearly legible.
            fill_alpha = 215 if (hovered or selected or danger) else 180
            grad = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            for y in range(rect.height):
                k = y / max(1, rect.height - 1)
                r = int(top_color[0] + (bot_color[0] - top_color[0]) * k)
                g = int(top_color[1] + (bot_color[1] - top_color[1]) * k)
                b = int(top_color[2] + (bot_color[2] - top_color[2]) * k)
                pygame.draw.line(grad, (r, g, b, fill_alpha), (0, y), (rect.width, y))
            mask = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            pygame.draw.rect(
                mask, (255, 255, 255, 255), mask.get_rect(), border_radius=radius
            )
            grad.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            self.surface.blit(grad, rect.topleft)

            # Inset top highlight for a subtle "lit from above" feel.
            highlight = pygame.Surface(
                (max(1, rect.width - 14), 2), pygame.SRCALPHA
            )
            highlight.fill((255, 255, 255, 40 if (hovered or selected) else 28))
            self.surface.blit(highlight, (rect.x + 7, rect.y + 3))

            # Crisp 1px border.
            pygame.draw.rect(
                self.surface, border_color, rect, 1, border_radius=radius
            )

            # Left accent bar (vertical strip, chess-inspired signal stripe).
            if accent_bar:
                bar_w = 4 if (hovered or selected) else 3
                bar_h = max(14, rect.height - 18)
                bar_rect = pygame.Rect(
                    rect.x + 10, rect.centery - bar_h // 2, bar_w, bar_h
                )
                pygame.draw.rect(
                    self.surface, bar_color, bar_rect, border_radius=2
                )

            # Label (centered by default; optional offset for icons).
            surf = f.render(label, True, fg)
            lrect = surf.get_rect(center=rect.center)
            lrect.x += label_offset[0]
            lrect.y += label_offset[1]
            self.surface.blit(surf, lrect)

        def draw_led_back_btn(rect, hovered):
            """
            Compact corner "Back" pill with a pulsing red LED dot — acts as
            a clean alternative to a bottom-centred Back button so the
            shared footer can breathe.
            """
            radius = rect.height // 2

            # Soft shadow beneath the pill (kept light so the background
            # drift shows through the button).
            shadow = pygame.Surface(
                (rect.width + 12, rect.height + 12), pygame.SRCALPHA
            )
            pygame.draw.rect(
                shadow,
                (0, 0, 0, 70),
                shadow.get_rect().inflate(-4, -4),
                border_radius=radius + 2,
            )
            self.surface.blit(shadow, (rect.x - 6, rect.y - 2))

            if hovered:
                bg_color  = (84, 38, 38)
                bord      = (214, 128, 128)
                fg        = (246, 222, 222)
                led_core  = (255, 130, 130)
                led_glow  = (255, 80, 80)
                bg_alpha  = 215
            else:
                bg_color  = (44, 26, 26)
                bord      = (142, 78, 78)
                fg        = (222, 174, 174)
                led_core  = (230, 90, 90)
                led_glow  = (220, 60, 60)
                bg_alpha  = 180

            # Semi-transparent pill body so the floating pieces pass behind.
            pill_body = pygame.Surface(
                (rect.width, rect.height), pygame.SRCALPHA
            )
            pygame.draw.rect(
                pill_body,
                (*bg_color, bg_alpha),
                pill_body.get_rect(),
                border_radius=radius,
            )
            self.surface.blit(pill_body, rect.topleft)
            pygame.draw.rect(self.surface, bord, rect, 1, border_radius=radius)

            # Pulsing red LED dot on the left side of the pill.
            pulse = 0.5 + 0.5 * math.sin(t / 260)
            led_cx = rect.x + 18
            led_cy = rect.centery
            glow_alpha = int(80 + 120 * pulse)
            glow_surf = pygame.Surface((24, 24), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (*led_glow, glow_alpha), (12, 12), 12)
            pygame.draw.circle(glow_surf, (*led_glow, min(255, glow_alpha + 50)), (12, 12), 7)
            self.surface.blit(glow_surf, (led_cx - 12, led_cy - 12))
            pygame.draw.circle(self.surface, led_core, (led_cx, led_cy), 4)
            pygame.draw.circle(self.surface, (255, 220, 220), (led_cx, led_cy), 2)

            # Back arrow.
            ax = rect.x + 42
            pygame.draw.line(self.surface, fg, (ax, led_cy), (ax - 9, led_cy), 2)
            pygame.draw.line(self.surface, fg, (ax - 9, led_cy), (ax - 4, led_cy - 5), 2)
            pygame.draw.line(self.surface, fg, (ax - 9, led_cy), (ax - 4, led_cy + 5), 2)

            # "Back" label.
            bfont = pygame.font.Font(None, 26)
            bsurf = bfont.render("Back", True, fg)
            self.surface.blit(
                bsurf, bsurf.get_rect(midleft=(rect.x + 52, led_cy))
            )

        def draw_elegant_divider(div_y, half_width=200):
            pygame.draw.line(self.surface, (52, 50, 46),
                             (W // 2 - half_width, div_y), (W // 2 - 10, div_y), 1)
            pygame.draw.line(self.surface, (52, 50, 46),
                             (W // 2 + 10, div_y), (W // 2 + half_width, div_y), 1)
            diamond = [
                (W // 2,     div_y - 5),
                (W // 2 + 5, div_y),
                (W // 2,     div_y + 5),
                (W // 2 - 5, div_y),
            ]
            pygame.draw.polygon(self.surface, ACCENT, diamond)

        def draw_back_arrow(rect, color):
            bx = rect.left + 20
            by = rect.centery
            pygame.draw.line(self.surface, color, (bx, by), (bx - 8, by), 2)
            pygame.draw.line(self.surface, color, (bx - 8, by), (bx - 4, by - 4), 2)
            pygame.draw.line(self.surface, color, (bx - 8, by), (bx - 4, by + 4), 2)

        def icon_badge(surface, cx, cy, w, h, color):
            badge = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.rect(badge, (*color, 38), (0, 0, w, h), border_radius=6)
            surface.blit(badge, (cx - w // 2, cy - h // 2))

        def draw_category_icon(surface, category, cx, cy, size, color):
            icon_badge(surface, cx, cy, size + 10, size + 10, color)
            if category == "Bullet":
                # Bullet projectile: rounded body + pointed nose + animated speed lines
                bw, bh = int(size * 0.42), int(size * 0.28)
                # Animated x-offset: bullet slides right across icon then resets
                phase = (t % 520) / 520
                ox = int((phase - 0.3) * size * 0.7)  # -0.3..0.7 range
                bx = cx + ox
                # Speed lines (left of bullet)
                for i, (dy2, llen) in enumerate([(- bh//2 + 1, int(size*0.28)),
                                                  (0,            int(size*0.36)),
                                                  (bh//2 - 1,   int(size*0.22))]):
                    a_line = max(0, min(255, int(255 * (0.35 - phase) / 0.35))) if phase < 0.35 else 0
                    a_line = max(0, 200 - i * 50) if phase > 0.1 else int(200 * phase / 0.1)
                    ls = pygame.Surface((llen, 2), pygame.SRCALPHA)
                    ls.fill((*color, a_line))
                    surface.blit(ls, (bx - bw // 2 - llen - 2, cy + dy2 - 1))
                # Bullet body
                body_rect = pygame.Rect(bx - bw // 2, cy - bh // 2, bw, bh)
                pygame.draw.rect(surface, color, body_rect, border_radius=3)
                # Pointed nose (triangle to the right)
                tip = int(size * 0.18)
                pygame.draw.polygon(surface, color, [
                    (bx + bw // 2, cy - bh // 2),
                    (bx + bw // 2 + tip, cy),
                    (bx + bw // 2, cy + bh // 2),
                ])
                # Base rim (darker bottom band)
                rim = pygame.Rect(bx - bw // 2, cy + bh // 2 - 4, bw, 4)
                rim_surf = pygame.Surface((bw, 4), pygame.SRCALPHA)
                rim_surf.fill((*color, 140))
                surface.blit(rim_surf, rim.topleft)

            elif category == "Blitz":
                # Bright flickering lightning bolt
                flicker = 0.55 + 0.45 * abs(math.sin(t * math.pi / 70))
                al = int(255 * flicker)
                s = size
                bolt = pygame.Surface((s + 6, s + 6), pygame.SRCALPHA)
                bw2 = s + 6
                pts = [
                    (bw2 * 0.62, 0),
                    (bw2 * 0.18, bw2 * 0.50),
                    (bw2 * 0.48, bw2 * 0.50),
                    (bw2 * 0.10, bw2 * 1.00),
                    (bw2 * 0.78, bw2 * 0.46),
                    (bw2 * 0.50, bw2 * 0.46),
                ]
                pygame.draw.polygon(bolt, (*color, al), pts)
                # Bright core at high flicker
                if flicker > 0.85:
                    inner_pts = [(p[0] * 0.75 + bw2*0.12, p[1] * 0.75 + bw2*0.12) for p in pts]
                    pygame.draw.polygon(bolt, (255, 255, 200, int(al * 0.5)), inner_pts)
                surface.blit(bolt, (int(cx - bw2 // 2), int(cy - bw2 // 2)))

            elif category == "Rapid":
                # Professional ticking clock face
                r = int(size * 0.46)
                cx2, cy2 = int(cx), int(cy)
                # Clock face (filled dark center)
                face = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
                pygame.draw.circle(face, (*color, 25), (r + 2, r + 2), r)
                surface.blit(face, (cx2 - r - 2, cy2 - r - 2))
                pygame.draw.circle(surface, color, (cx2, cy2), r, 2)
                # 12 tick marks
                for i in range(12):
                    ang = i * math.pi / 6 - math.pi / 2
                    tlen = 4 if i % 3 == 0 else 2
                    tw   = 2 if i % 3 == 0 else 1
                    x1 = cx2 + int(r * math.cos(ang))
                    y1 = cy2 + int(r * math.sin(ang))
                    x2 = cx2 + int((r - tlen) * math.cos(ang))
                    y2 = cy2 + int((r - tlen) * math.sin(ang))
                    pygame.draw.line(surface, color, (x1, y1), (x2, y2), tw)
                # Minute hand (1 rotation per 30s — visibly moving)
                min_ang = (t / 30000) * 2 * math.pi - math.pi / 2
                mx = cx2 + int(r * 0.60 * math.cos(min_ang))
                my = cy2 + int(r * 0.60 * math.sin(min_ang))
                pygame.draw.line(surface, color, (cx2, cy2), (mx, my), 2)
                # Second hand (1 rotation per 2s — fast sweep)
                sec_ang = (t / 2000) * 2 * math.pi - math.pi / 2
                sx = cx2 + int((r - 3) * math.cos(sec_ang))
                sy = cy2 + int((r - 3) * math.sin(sec_ang))
                pygame.draw.line(surface, (200, 80, 80), (cx2, cy2), (sx, sy), 1)
                pygame.draw.circle(surface, color, (cx2, cy2), 2)

        def draw_infinity_icon(surface, cx, cy, size, color):
            a = size * 0.54
            n = 100
            pts = []
            for i in range(n + 1):
                th = i * 2 * math.pi / n
                d = 1 + math.sin(th) ** 2
                pts.append((int(cx + a * math.cos(th) / d),
                             int(cy + a * math.sin(th) * math.cos(th) / d)))
            if len(pts) >= 2:
                pygame.draw.lines(surface, color, False, pts, 3)
            # Animated glowing tracer
            th_dot = (t / 1500) * 2 * math.pi
            d = 1 + math.sin(th_dot) ** 2
            dx = int(cx + a * math.cos(th_dot) / d)
            dy = int(cy + a * math.sin(th_dot) * math.cos(th_dot) / d)
            glow = pygame.Surface((18, 18), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*color, 90), (9, 9), 9)
            surface.blit(glow, (dx - 9, dy - 9))
            pygame.draw.circle(surface, (245, 245, 235), (dx, dy), 3)

        def piece_alpha(slot_offset=0):
            CYCLE = 2200
            FADE  = 280
            phase = (t + slot_offset * CYCLE // 2) % CYCLE
            if phase < FADE:
                return int(255 * phase / FADE), (t + slot_offset * CYCLE // 2) // CYCLE % 6
            elif phase > CYCLE - FADE:
                return int(255 * (CYCLE - phase) / FADE), (t + slot_offset * CYCLE // 2) // CYCLE % 6
            return 255, (t + slot_offset * CYCLE // 2) // CYCLE % 6

        def blit_piece(img, cx, cy, size, alpha):
            if img is None:
                return
            scaled = pygame.transform.smoothscale(img, (size, size))
            scaled.set_alpha(alpha)
            self.surface.blit(scaled, scaled.get_rect(center=(cx, cy)))

        # ── MENU ──────────────────────────────────────────────────────────
        if self.state == "MENU":
            title_font  = pygame.font.Font(None, 96)
            sub_font    = pygame.font.Font(None, 26)
            footer_font = pygame.font.Font(None, 20)

            # Layout anchors scale with the window so it looks balanced in
            # both windowed and fullscreen modes.
            logo_y   = int(H * 0.22)
            sub_y    = int(H * 0.385)
            div_y    = int(H * 0.425)
            footer_y = H - 28

            float_offset = 4 * math.sin(t / 900)

            if self.menu_logo is not None:
                # Transparent-background branding artwork. We scale it to
                # match the window while preserving aspect ratio, then
                # place a soft accent glow behind it for an elegant
                # "spotlit" feel.
                src_w, src_h = self.menu_logo.get_size()
                target_w = min(int(W * 0.58), 620)
                target_h = int(src_h * (target_w / max(1, src_w)))
                if target_h > int(H * 0.42):
                    target_h = int(H * 0.42)
                    target_w = int(src_w * (target_h / max(1, src_h)))
                logo = pygame.transform.smoothscale(
                    self.menu_logo, (target_w, target_h)
                )
                logo_rect = logo.get_rect(
                    center=(W // 2, logo_y + int(float_offset))
                )
                # Soft accent halo behind the logo.
                halo_r = max(target_w, target_h) // 2 + 40
                halo = pygame.Surface(
                    (halo_r * 2, halo_r * 2), pygame.SRCALPHA
                )
                for r in range(halo_r, 0, -18):
                    intensity = max(0, 30 - int(30 * (r / halo_r)))
                    if intensity <= 0:
                        continue
                    pygame.draw.circle(
                        halo, (*ACCENT, intensity), (halo_r, halo_r), r
                    )
                self.surface.blit(
                    halo, halo.get_rect(center=logo_rect.center)
                )
                self.surface.blit(logo, logo_rect)
            else:
                # Graceful fallback: original white-knight emblem + title
                # when the branding file isn't installed yet.
                title_y = int(H * 0.315)
                white_knight = self.menu_pieces['white'][2]
                logo_size = 100
                if white_knight:
                    sc_w = pygame.transform.smoothscale(
                        white_knight, (logo_size, logo_size)
                    )
                    self.surface.blit(
                        sc_w,
                        sc_w.get_rect(
                            center=(W // 2, int(H * 0.16) + int(float_offset))
                        ),
                    )
                title_surf = title_font.render("@Chess", True, TEXT_PRI)
                self.surface.blit(
                    title_surf,
                    title_surf.get_rect(center=(W // 2, title_y)),
                )

            sub_surf = sub_font.render("Select a game mode to begin", True, TEXT_MUT)
            self.surface.blit(sub_surf, sub_surf.get_rect(center=(W // 2, sub_y)))

            draw_elegant_divider(div_y, half_width=200)

            for _mode, label, rect in self.menu_buttons:
                hov = rect.collidepoint(mouse_pos)
                draw_primary_btn(rect, label, hov)

        # ── MENU_COLOR ────────────────────────────────────────────────────
        elif self.state == "MENU_COLOR":
            title_font = pygame.font.Font(None, 58)
            sub_font   = pygame.font.Font(None, 28)
            label_font = pygame.font.Font(None, 36)

            title_surf = title_font.render("Choose Your Side", True, TEXT_PRI)
            self.surface.blit(title_surf, title_surf.get_rect(center=(W // 2, 120)))

            sub_surf = sub_font.render("Which side do you want to play?", True, TEXT_MUT)
            self.surface.blit(sub_surf, sub_surf.get_rect(center=(W // 2, 158)))

            draw_elegant_divider(180, half_width=220)

            # Draw White and Black cards — transparent so the drifting
            # pieces from the background pass right through them.
            for key, _label, rect in self.color_buttons[:2]:
                is_white = (key == "WHITE")
                hov = rect.collidepoint(mouse_pos)

                # Contrast tint: dark panel sits behind the white piece and
                # a light panel sits behind the black piece, so each piece
                # pops against its backdrop. Very low alpha so the drifting
                # pieces in the background remain clearly visible through
                # the card.
                tint_color = (12, 10, 8) if is_white else (235, 232, 225)
                tint_alpha = 38 if is_white else 14
                tint = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                pygame.draw.rect(
                    tint,
                    (*tint_color, tint_alpha),
                    tint.get_rect(),
                    border_radius=14,
                )
                self.surface.blit(tint, rect.topleft)

                # Soft outer glow on hover.
                if hov:
                    glow = pygame.Surface(
                        (rect.width + 24, rect.height + 24), pygame.SRCALPHA
                    )
                    pygame.draw.rect(
                        glow,
                        (*ACCENT, 55),
                        glow.get_rect(),
                        border_radius=18,
                    )
                    self.surface.blit(glow, (rect.x - 12, rect.y - 12))

                card_bord = ACCENT if hov else (
                    (120, 116, 106) if is_white else (70, 66, 60)
                )
                pygame.draw.rect(
                    self.surface, card_bord, rect, 2, border_radius=14
                )

                alpha, idx = piece_alpha(slot_offset=(0 if is_white else 1))
                pieces_list = self.menu_pieces['white' if is_white else 'black']
                blit_piece(
                    pieces_list[idx], rect.centerx, rect.centery - 20, 110, alpha
                )

                side_label = "White" if is_white else "Black"
                lsurf = label_font.render(side_label, True, TEXT_PRI)
                self.surface.blit(
                    lsurf,
                    lsurf.get_rect(center=(rect.centerx, rect.bottom - 28)),
                )

            # Random button: premium style (centered under the cards).
            for key, label, rect in self.color_buttons[2:]:
                hov = rect.collidepoint(mouse_pos)
                if key == "BACK":
                    draw_led_back_btn(rect, hov)
                else:
                    draw_primary_btn(rect, label, hov)

        # ── MENU_TIME ─────────────────────────────────────────────────────
        else:
            title_font = pygame.font.Font(None, 52)
            sub_font   = pygame.font.Font(None, 28)

            title_surf = title_font.render("Time Control", True, TEXT_PRI)
            self.surface.blit(title_surf, title_surf.get_rect(center=(W // 2, 70)))

            sub_surf = sub_font.render("Select the time control for this game", True, TEXT_MUT)
            self.surface.blit(sub_surf, sub_surf.get_rect(center=(W // 2, 103)))

            draw_elegant_divider(122, half_width=240)

            left_x = (W // 2) - 260
            for item in self.time_buttons:
                if item[0] == "HEADER":
                    category, hy = item[1], item[2]
                    icon_size = 28
                    icon_cx = left_x + icon_size // 2 + 2
                    draw_category_icon(self.surface, category, icon_cx, hy + 16, icon_size, ACCENT)
                    cat_surf = cat_font.render(category.upper(), True, ACCENT)
                    self.surface.blit(cat_surf, (left_x + icon_size + 18, hy + 8))
                    pygame.draw.line(self.surface, (52, 50, 46),
                                     (left_x, hy + 30), (left_x + 518, hy + 30), 1)
                    continue
                if item[0] == "NOLIMIT":
                    _type, label, rect, base_seconds, inc_seconds = item
                    selected = (self.base_time_seconds == base_seconds
                                and self.increment_seconds == inc_seconds)
                    hov = rect.collidepoint(mouse_pos)
                    # Premium button background, but turn off the left bar
                    # so the infinity icon owns the left-side ornament.
                    draw_primary_btn(
                        rect,
                        "No Limit",
                        hov,
                        selected=selected,
                        accent_bar=False,
                        label_offset=(28, 0),
                    )
                    inf_color = (220, 240, 170) if selected else (ACCENT if hov else (160, 200, 110))
                    draw_infinity_icon(self.surface, rect.left + 40, rect.centery, 26, inf_color)
                    continue
                _type, label, rect, base_seconds, inc_seconds, _cat = item
                selected = (self.base_time_seconds == base_seconds
                            and self.increment_seconds == inc_seconds)
                draw_primary_btn(
                    rect,
                    label,
                    rect.collidepoint(mouse_pos),
                    selected=selected,
                )

            back_hov = self.time_back_button.collidepoint(mouse_pos)
            draw_led_back_btn(self.time_back_button, back_hov)

        # Shared footer across all menu screens: author credit + controls.
        footer_font_small = pygame.font.Font(None, 20)
        credit_font       = pygame.font.Font(None, 22)
        footer_y = H - 28
        credit_surf = credit_font.render(
            "Created by Omar Sheikh", True, (150, 146, 136)
        )
        self.surface.blit(
            credit_surf,
            credit_surf.get_rect(center=(W // 2, footer_y - 22)),
        )
        controls_surf = footer_font_small.render(
            "F11 Fullscreen  ·  Esc exits fullscreen",
            True,
            (92, 89, 82),
        )
        self.surface.blit(
            controls_surf, controls_surf.get_rect(center=(W // 2, footer_y))
        )

        pygame.display.flip()

    def _draw_game(self):
        self.ui.white_time = self.white_time
        self.ui.black_time = self.black_time
        # Surface a compact learning-book indicator alongside the mode
        # label so the player can watch the AI's experience grow.
        decorated_mode_label = self.mode_label
        if self.learning_book is not None:
            stats = self.learning_book.stats_summary()
            if stats["games"] > 0:
                decorated_mode_label = (
                    f"{self.mode_label}  ·  Learned: "
                    f"{stats['games']}g / {stats['positions']}p"
                )
        self.ui.drawComponent(
            dragging_piece_symbol=self.dragging_piece_symbol,
            drag_pos=self.drag_pos,
            drag_from_square=self.drag_from_square,
            arrows=self._get_visible_arrows(),
            marked_squares=self._get_visible_marked_squares(),
            mode_label=decorated_mode_label,
            starting_fen=self.starting_fen,
            white_label=self.white_label,
            black_label=self.black_label,
            white_is_bot=self.white_is_bot,
            black_is_bot=self.black_is_bot,
            move_log=self.move_log,
            do_flip=False,
        )

        button_font = pygame.font.Font(None, 26)
        mouse_pos = pygame.mouse.get_pos()

        def _gradient_body(rect, top_c, bot_c, radius):
            grad = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            for yy in range(rect.height):
                k = yy / max(1, rect.height - 1)
                rc = int(top_c[0] + (bot_c[0] - top_c[0]) * k)
                gc = int(top_c[1] + (bot_c[1] - top_c[1]) * k)
                bc = int(top_c[2] + (bot_c[2] - top_c[2]) * k)
                pygame.draw.line(grad, (rc, gc, bc, 255), (0, yy), (rect.width, yy))
            mask = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            pygame.draw.rect(
                mask,
                (255, 255, 255, 255),
                mask.get_rect(),
                border_radius=radius,
            )
            grad.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            self.surface.blit(grad, rect.topleft)

        def _render_arrow_button(rect, direction, hovered, enabled):
            """Compact square icon button with a left/right chevron."""
            radius = 10
            # Soft drop shadow.
            shadow = pygame.Surface(
                (rect.width + 12, rect.height + 12), pygame.SRCALPHA
            )
            pygame.draw.rect(
                shadow,
                (0, 0, 0, 80),
                shadow.get_rect().inflate(-4, -4),
                border_radius=radius + 2,
            )
            self.surface.blit(shadow, (rect.x - 6, rect.y - 2))

            if not enabled:
                top_c, bot_c = (42, 40, 36), (28, 26, 24)
                border_c = (60, 58, 54)
                arrow_c  = (110, 107, 100)
                glow_c   = None
            elif hovered:
                top_c, bot_c = (74, 104, 44), (44, 62, 22)
                border_c = (129, 182, 76)
                arrow_c  = (226, 244, 184)
                glow_c   = (129, 182, 76)
            else:
                top_c, bot_c = (54, 72, 34), (36, 50, 20)
                border_c = (100, 142, 58)
                arrow_c  = (210, 240, 170)
                glow_c   = None

            if glow_c is not None:
                glow = pygame.Surface(
                    (rect.width + 18, rect.height + 18), pygame.SRCALPHA
                )
                pygame.draw.rect(
                    glow,
                    (*glow_c, 55),
                    glow.get_rect(),
                    border_radius=radius + 6,
                )
                self.surface.blit(glow, (rect.x - 9, rect.y - 9))

            _gradient_body(rect, top_c, bot_c, radius)

            # Inset top highlight.
            highlight = pygame.Surface(
                (max(1, rect.width - 12), 2), pygame.SRCALPHA
            )
            highlight.fill((255, 255, 255, 38 if hovered else 22))
            self.surface.blit(highlight, (rect.x + 6, rect.y + 3))

            pygame.draw.rect(
                self.surface, border_c, rect, 1, border_radius=radius
            )

            # Chevron arrow.
            cx, cy = rect.center
            s = rect.height // 4
            if direction == "left":
                pts = [(cx + s // 2, cy - s), (cx - s // 2, cy), (cx + s // 2, cy + s)]
            else:
                pts = [(cx - s // 2, cy - s), (cx + s // 2, cy), (cx - s // 2, cy + s)]
            pygame.draw.lines(self.surface, arrow_c, False, pts, 3)

        def _render_menu_button(rect, hovered):
            radius = 10
            shadow = pygame.Surface(
                (rect.width + 12, rect.height + 12), pygame.SRCALPHA
            )
            pygame.draw.rect(
                shadow,
                (0, 0, 0, 80),
                shadow.get_rect().inflate(-4, -4),
                border_radius=radius + 2,
            )
            self.surface.blit(shadow, (rect.x - 6, rect.y - 2))

            if hovered:
                top_c, bot_c = (96, 44, 44), (58, 24, 24)
                border_c = (212, 128, 128)
                fg_c     = (248, 218, 218)
                glow_c   = (200, 90, 90)
            else:
                top_c, bot_c = (70, 34, 34), (46, 22, 22)
                border_c = (138, 78, 78)
                fg_c     = (226, 180, 180)
                glow_c   = None

            if glow_c is not None:
                glow = pygame.Surface(
                    (rect.width + 18, rect.height + 18), pygame.SRCALPHA
                )
                pygame.draw.rect(
                    glow,
                    (*glow_c, 55),
                    glow.get_rect(),
                    border_radius=radius + 6,
                )
                self.surface.blit(glow, (rect.x - 9, rect.y - 9))

            _gradient_body(rect, top_c, bot_c, radius)

            highlight = pygame.Surface(
                (max(1, rect.width - 14), 2), pygame.SRCALPHA
            )
            highlight.fill((255, 255, 255, 40 if hovered else 24))
            self.surface.blit(highlight, (rect.x + 7, rect.y + 3))

            pygame.draw.rect(
                self.surface, border_c, rect, 1, border_radius=radius
            )

            text = button_font.render("Menu  (M)", True, fg_c)
            self.surface.blit(text, text.get_rect(center=rect.center))

        # Undo / redo availability:
        #  - HUMAN_AI live play: peek mode — Undo moves you backwards in
        #    the recorded history, Redo brings you back. No takebacks.
        #  - Game-over: pure review navigation through the whole history.
        #  - HUMAN_HUMAN / AI_AI: traditional undo/redo against redo_stack.
        if self.game_over:
            can_undo = bool(
                self.game and self.game.board.board.move_stack
            )
            can_redo = bool(
                self.game
                and len(self.game.board.board.move_stack) < len(self.move_log)
            )
        elif self.mode == "HUMAN_AI":
            can_undo = bool(
                self.game and self.game.board.board.move_stack
            )
            can_redo = bool(
                self.game
                and len(self.game.board.board.move_stack) < len(self.move_log)
            )
        else:
            can_undo = bool(
                self.game and self.game.board.board.move_stack
            )
            can_redo = bool(self.redo_stack)
        undo_rect = self.game_buttons["undo"]
        redo_rect = self.game_buttons["redo"]
        menu_rect = self.game_buttons["menu"]
        play_rect = self.game_buttons.get("play")

        def _render_play_button(rect, is_playing, hovered):
            """Wide Play/Stop replay button — visible once the game ends."""
            radius = 10
            shadow = pygame.Surface(
                (rect.width + 14, rect.height + 14), pygame.SRCALPHA
            )
            pygame.draw.rect(
                shadow,
                (0, 0, 0, 90),
                shadow.get_rect().inflate(-4, -4),
                border_radius=radius + 2,
            )
            self.surface.blit(shadow, (rect.x - 7, rect.y - 2))

            if is_playing:
                # Amber/pause palette.
                top_c, bot_c = (176, 118, 38), (108, 70, 18)
                border_c = (244, 188, 96)
                fg_c     = (250, 230, 190)
                glow_c   = (236, 170, 64)
                label    = "Stop"
            else:
                # Green/play palette.
                top_c, bot_c = (84, 124, 48), (46, 70, 22)
                border_c = (160, 212, 96)
                fg_c     = (230, 250, 196)
                glow_c   = (129, 182, 76)
                label    = "Play replay"

            if hovered:
                glow = pygame.Surface(
                    (rect.width + 22, rect.height + 22), pygame.SRCALPHA
                )
                pygame.draw.rect(
                    glow,
                    (*glow_c, 65),
                    glow.get_rect(),
                    border_radius=radius + 8,
                )
                self.surface.blit(glow, (rect.x - 11, rect.y - 11))

            _gradient_body(rect, top_c, bot_c, radius)

            highlight = pygame.Surface(
                (max(1, rect.width - 14), 2), pygame.SRCALPHA
            )
            highlight.fill((255, 255, 255, 48 if hovered else 32))
            self.surface.blit(highlight, (rect.x + 7, rect.y + 3))

            pygame.draw.rect(
                self.surface, border_c, rect, 1, border_radius=radius
            )

            # Icon (triangle for Play, two bars for Stop) drawn on the left.
            icon_cx = rect.x + 22
            icon_cy = rect.centery
            if is_playing:
                bar_w = 4
                bar_h = 14
                gap_w = 4
                pygame.draw.rect(
                    self.surface,
                    fg_c,
                    (icon_cx - bar_w - gap_w // 2, icon_cy - bar_h // 2, bar_w, bar_h),
                    border_radius=1,
                )
                pygame.draw.rect(
                    self.surface,
                    fg_c,
                    (icon_cx + gap_w // 2, icon_cy - bar_h // 2, bar_w, bar_h),
                    border_radius=1,
                )
            else:
                s = 8
                pts = [
                    (icon_cx - s + 2, icon_cy - s),
                    (icon_cx + s + 2, icon_cy),
                    (icon_cx - s + 2, icon_cy + s),
                ]
                pygame.draw.polygon(self.surface, fg_c, pts)

            text = button_font.render(label, True, fg_c)
            text_rect = text.get_rect(center=rect.center)
            text_rect.x += 10  # nudge right so it doesn't overlap the icon
            self.surface.blit(text, text_rect)

        _render_arrow_button(
            undo_rect, "left",
            undo_rect.collidepoint(mouse_pos) and can_undo,
            enabled=can_undo,
        )
        _render_arrow_button(
            redo_rect, "right",
            redo_rect.collidepoint(mouse_pos) and can_redo,
            enabled=can_redo,
        )
        if self.game_over and play_rect is not None:
            _render_play_button(
                play_rect,
                self.auto_play_active,
                play_rect.collidepoint(mouse_pos),
            )
        _render_menu_button(menu_rect, menu_rect.collidepoint(mouse_pos))
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
                    if item[0] == "OPTION":
                        _type, _label, rect, base_seconds, inc_seconds, _category = item
                    elif item[0] == "NOLIMIT":
                        _type, _label, rect, base_seconds, inc_seconds = item
                    else:
                        continue
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
            elif event.key == pygame.K_SPACE and self.game_over:
                self._toggle_auto_play()
            return

        # Mouse-wheel scroll over the move-history panel pages through
        # older / newer rows. Works for both live play and review.
        if event.type == pygame.MOUSEWHEEL and self.ui is not None:
            mouse_pos = pygame.mouse.get_pos()
            if self.ui.history_view_rect.collidepoint(mouse_pos):
                # event.y > 0 means wheel up → older rows.
                self.ui.scroll_history(event.y)
                return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Play button is only interactive after the game ends.
            play_rect = self.game_buttons.get("play")
            if (
                self.game_over
                and play_rect is not None
                and play_rect.collidepoint(event.pos)
            ):
                self._toggle_auto_play()
                return

            for key, rect in self.game_buttons.items():
                if key == "play":
                    continue
                if rect.collidepoint(event.pos):
                    if key == "undo":
                        self._undo_move()
                    elif key == "redo":
                        self._redo_move()
                    elif key == "menu":
                        self.go_to_menu()
                    return

            # Review-mode: once the game is finished, clicking a move row
            # in the history jumps the board to that position without
            # resuming the game. This also pauses auto-play so the user
            # can pick a spot and then press Play to continue from there.
            if self.game_over and self.ui is not None:
                clicked_ply = self.ui.get_history_click_ply(event.pos)
                if clicked_ply is not None:
                    self.auto_play_active = False
                    self._go_to_review_position(clicked_ply)
                    self.ui.ensure_ply_visible(clicked_ply)
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
                    self._toggle_marker(end_square)
                else:
                    self._toggle_arrow(self.arrow_start_square, end_square)
            self.arrow_start_square = None

    def run(self):
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    break
                if self._handle_display_shortcuts(event):
                    continue
                if self.state in ("MENU", "MENU_COLOR", "MENU_TIME"):
                    self._handle_menu_event(event)
                elif self.state == "GAME":
                    self._handle_game_event(event)

            if self.state in ("MENU", "MENU_COLOR", "MENU_TIME"):
                self._draw_menu()
            elif self.state == "GAME":
                self._update_timers()
                self._maybe_make_ai_move()
                self._tick_auto_play()
                self._draw_game()

            self.clock.tick(FPS)

        pygame.quit()


if __name__ == "__main__":
    UnifiedChessApp().run()
