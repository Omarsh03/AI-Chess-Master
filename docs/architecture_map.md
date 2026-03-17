# Current Architecture Map

This document maps the original project before the full-chess refactor.

## Legacy Flow

1. `server.py` creates `ChessBoard` and optional `AIAgent`.
2. `client.py` receives setup/time/mode from server and drives `UserInterface`.
3. `UserInterface.py` builds move strings and sends them via `client.py`.
4. `board.py` wraps `python-chess` but filters legal moves to pawns only.
5. `game.py` tracks move history and uses `ChessBoard` as the state holder.
6. `timer_manager.py` tracks white/black clocks and exposes timeout checks.

## Legacy Constraints (Pawn-Only)

- `board.py` includes explicit `piece_type == chess.PAWN` filtering.
- Promotion is treated as an immediate win signal (`Win`) in UI/network flow.
- Images and rendering assets only contain white/black pawn sprites.
- Server/client protocol assumes pawn-only win/loss semantics.

## Refactor Targets

- Move rules/state handling into a generic `engine` package.
- Keep socket and timer infrastructure with minimal adaptation.
- Replace UI/game flow to consume full chess status events.
- Keep the project executable via existing entry points (`server.py`, `client.py`, `local_game.py`).
