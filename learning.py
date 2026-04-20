"""
learning.py — Persistent experience-replay module for the chess AI.

Overview
--------
This module implements a lightweight **reinforcement-learning-inspired
experience book** that lets the chess AI improve across games and across
application runs. After every completed game the book records, for each
position that was actually played, which move was chosen and the
final game outcome (win / loss / draw from the mover's perspective).

During live play the AI consults the book while ordering candidate
moves; moves with a strong historical win-rate at the current position
get a positive score bonus. This is a gentle, well-calibrated preference
— the core alpha-beta search still decides — but it makes the engine
demonstrably stronger on positions it has encountered before.

Key techniques
--------------
* **Zobrist Hashing** (`chess.polyglot.zobrist_hash`) — industry-standard
  64-bit position keys that are small, collision-resistant, and
  deterministic across runs.
* **Laplace (additive) smoothing** with a Bayesian prior of 0.5 —
  positions with only a handful of samples don't receive an
  overconfident bonus.
* **Confidence scaling** from sample count — the ordering bonus grows
  with sample size and saturates around ten samples.
* **Atomic JSON persistence** (write-to-temp + `os.replace`) — the book
  file never ends up half-written, even if the process is killed.
* **Thread-safe updates** — the book is protected by an `RLock` so it
  can be safely touched from the main thread and from the AI worker.
"""

from __future__ import annotations

import json
import os
import threading
from typing import Optional, Tuple

import chess
import chess.polyglot


class LearningBook:
    """
    Persistent experience-replay buffer that records move statistics per
    position and serves a score bonus during AI move ordering.

    File schema (v1):
        {
            "version": 1,
            "games_recorded": <int>,
            "positions": {
                "<zobrist_hex>": {
                    "<move_uci>": { "w": <int>, "l": <int>, "d": <int> }
                }
            }
        }
    """

    FILE_NAME = "ai_memory.json"
    SCHEMA_VERSION = 1

    # Tuning constants — exposed as class attributes so they're easy to
    # tweak (and legible to a reader).
    LAPLACE_ALPHA = 2.0               # Strength of the 50/50 prior.
    CONFIDENCE_SATURATION = 10.0      # Samples needed to trust the data fully.
    MAX_ORDERING_BONUS = 1200         # Max bonus added to move-ordering score.
    DEFAULT_MIN_SAMPLES = 5           # Required samples to call a move "known".
    DEFAULT_MIN_RATE = 0.55           # Required win-rate to recommend a move.

    def __init__(self, filepath: Optional[str] = None) -> None:
        if filepath is None:
            base = os.path.dirname(os.path.abspath(__file__))
            filepath = os.path.join(base, self.FILE_NAME)
        self.filepath = filepath
        # hex(zobrist) -> move_uci -> {"w": wins, "l": losses, "d": draws}
        self.positions: dict = {}
        self.games_recorded: int = 0
        self._lock = threading.RLock()
        self.load()

    # ------------------------------------------------------------------ #
    # Position hashing
    # ------------------------------------------------------------------ #
    @staticmethod
    def _key(board: chess.Board) -> str:
        """Zobrist-hash the position into a short hex string."""
        return format(chess.polyglot.zobrist_hash(board), "x")

    # ------------------------------------------------------------------ #
    # Persistence
    # ------------------------------------------------------------------ #
    def load(self) -> None:
        with self._lock:
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except FileNotFoundError:
                return
            except (OSError, json.JSONDecodeError, ValueError):
                # Corrupted file — start fresh rather than crashing the app.
                self.positions = {}
                self.games_recorded = 0
                return

            if not isinstance(data, dict):
                return
            if data.get("version") != self.SCHEMA_VERSION:
                # Future-proofing: unknown schema → ignore rather than crash.
                return

            positions = data.get("positions", {})
            if isinstance(positions, dict):
                self.positions = positions
            try:
                self.games_recorded = int(data.get("games_recorded", 0))
            except (TypeError, ValueError):
                self.games_recorded = 0

    def save(self) -> None:
        """Atomically persist the book to disk (write-tmp + replace)."""
        with self._lock:
            data = {
                "version": self.SCHEMA_VERSION,
                "games_recorded": self.games_recorded,
                "positions": self.positions,
            }
            tmp_path = f"{self.filepath}.tmp"
            try:
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
                os.replace(tmp_path, self.filepath)
            except OSError:
                # Best effort: clean up the temp file and move on without
                # crashing the game.
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

    # ------------------------------------------------------------------ #
    # Recording
    # ------------------------------------------------------------------ #
    def record_game(self, move_log, winner_color) -> int:
        """
        Ingest a completed game into the buffer.

        Parameters
        ----------
        move_log:
            Iterable of dicts with at least the keys ``"side"`` (a
            ``chess.Color`` of the mover) and ``"uci"`` (the UCI move
            string). This matches the app's own move log format.
        winner_color:
            ``chess.WHITE``, ``chess.BLACK``, or ``None`` for a draw.

        Returns
        -------
        int
            Number of plies that were successfully recorded.
        """
        recorded = 0
        with self._lock:
            board = chess.Board()
            for entry in move_log or []:
                uci = entry.get("uci")
                mover = entry.get("side")
                if not uci or mover is None:
                    break
                try:
                    move = chess.Move.from_uci(uci)
                except ValueError:
                    break
                if move not in board.legal_moves:
                    # If the log drifted from the board, stop here rather
                    # than recording nonsense.
                    break

                key = self._key(board)
                pos_bucket = self.positions.setdefault(key, {})
                stats = pos_bucket.setdefault(uci, {"w": 0, "l": 0, "d": 0})
                if winner_color is None:
                    stats["d"] += 1
                elif winner_color == mover:
                    stats["w"] += 1
                else:
                    stats["l"] += 1

                board.push(move)
                recorded += 1

            self.games_recorded += 1
        return recorded

    # ------------------------------------------------------------------ #
    # Queries
    # ------------------------------------------------------------------ #
    def get_stats(self, board: chess.Board) -> dict:
        """All recorded move stats for the current position."""
        with self._lock:
            return self.positions.get(self._key(board), {})

    @classmethod
    def _laplace_win_rate(cls, w: int, l: int, d: int) -> float:
        """
        Laplace-smoothed win rate where draws count as half a win. The
        smoothing pulls rates towards 0.5 when there are few samples.
        """
        total = w + l + d
        alpha = cls.LAPLACE_ALPHA
        denom = total + alpha
        if denom <= 0:
            return 0.5
        return (w + 0.5 * d + 0.5 * alpha) / denom

    def ordering_bonus(self, board: chess.Board, move: chess.Move) -> int:
        """Integer score bonus used during alpha-beta move ordering."""
        data = self.get_stats(board).get(move.uci())
        if data is None:
            return 0
        total = data["w"] + data["l"] + data["d"]
        if total == 0:
            return 0
        rate = self._laplace_win_rate(data["w"], data["l"], data["d"])
        confidence = min(1.0, total / self.CONFIDENCE_SATURATION)
        # (rate - 0.5) maps win-rate to [-0.5, +0.5]; scaling by the max
        # bonus produces an integer comparable to the existing move
        # ordering heuristics (captures, killers, …).
        return int((rate - 0.5) * 2.0 * self.MAX_ORDERING_BONUS * confidence)

    def best_known_move(
        self,
        board: chess.Board,
        min_samples: int = DEFAULT_MIN_SAMPLES,
        min_rate: float = DEFAULT_MIN_RATE,
    ) -> Optional[Tuple[str, float, int]]:
        """
        Return (uci, laplace_win_rate, total_samples) for the strongest
        historically-known move in this position, or ``None`` if nothing
        clears the confidence bar.
        """
        stats = self.get_stats(board)
        best: Optional[Tuple[str, float, int]] = None
        best_rate = -1.0
        for uci, data in stats.items():
            total = data["w"] + data["l"] + data["d"]
            if total < min_samples:
                continue
            rate = self._laplace_win_rate(data["w"], data["l"], data["d"])
            if rate >= min_rate and rate > best_rate:
                best_rate = rate
                best = (uci, rate, total)
        return best

    # ------------------------------------------------------------------ #
    # Reporting
    # ------------------------------------------------------------------ #
    def stats_summary(self) -> dict:
        """High-level numbers for display in the UI."""
        with self._lock:
            total_moves = sum(len(moves) for moves in self.positions.values())
            return {
                "games": self.games_recorded,
                "positions": len(self.positions),
                "moves": total_moves,
            }
