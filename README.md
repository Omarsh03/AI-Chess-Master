# Full Chess Game

A full chess app in Python (Pygame + python-chess) with a unified modern UI, AI modes, drag/click move input, planning annotations, clocks with increment, and enhanced game-over visuals.

## Prerequisites

- Python 3.8+
- pip
- Required packages (installed by `run_game.bat` when needed):
  - chess==1.11.1
  - pygame==2.6.1
  - python-chess==1.999
  - numpy==1.24.3

## Quick Start

1. Double-click `run_game.bat`
2. It will:
   - verify Python
   - install dependencies (if missing)
   - run the unified app (`unified_app.py`)

You can also run directly:

```bash
python unified_app.py
```

## Manual Setup

For Windows:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python unified_app.py
```

## Unified App Flow

Everything runs in a single window:

1. Choose game mode (`Human vs AI`, `AI vs AI`, `Human vs Human`)
2. Choose time control (Bullet / Blitz / Rapid presets)
3. If `Human vs AI`, choose color (`White`, `Black`, `Random`)
4. Play in the same window (no separate server/client windows)

## Game Modes

### Human vs AI
- Play against AI
- Choose your color before game start
- AI move calculation runs in a background thread for smoother UI

### AI vs AI
- Watch two AI players play automatically

### Human vs Human
- Local two-player game on one machine

## Time Controls

Chess.com-style presets are available:

- **Bullet**: `1 min`, `1|1`, `2|1`
- **Blitz**: `3 min`, `3|2`, `5 min`
- **Rapid**: `10 min`, `15|10`, `30 min`, `No limit`

Format:
- `X min` means no increment
- `X|Y` means `Y` seconds increment added after each move

## Controls

### Piece Movement
- Left-click hold and drag: move piece
- Left-click piece, then left-click destination: move piece

### Planning Annotations
- Right-drag from square to square: draw/remove arrow
- Right-click same square: toggle red square marker (full-square highlight)
- Arrows and red markers are player-owned and auto-clear after that player makes their next move

### Keyboard
- `U`: Undo
- `R`: Redo
- `M`: Return to menu
- `F11`: Toggle fullscreen/window
- `Esc`: Exit fullscreen to windowed mode

## UI and Gameplay Enhancements

- Piece sprites (image-based board rendering, not Unicode glyphs)
- Sound cues for move, check, and checkmate
- Professional UI polish (board frame, cleaner panel, improved in-game buttons)
- Board coordinates (`a-h`, `1-8`) rendered around the board
- Right sidebar now includes player cards (name/avatar/time/captures) and move history with per-move think time
- Captured-material score display for White/Black
- Persistent game-over screen (window stays open)
- Winner/loser display on game over
- Fallen-king animation for the losing side
- Undo/Redo still available after game over

## Rules Notes

- Standard full chess legality is enforced by `python-chess`
- Win on time is supported
- Claimable draw ending by **threefold repetition** is disabled in this app flow

## Important Files

- `unified_app.py`: Main single-window app flow and gameplay loop
- `UserInterface.py`: Board/panel rendering, piece sprites, annotations, game-over visuals
- `engine/chess_engine.py`: Core chess wrapper and endgame status policy
- `ai_agent.py`: AI move search/evaluation
- `run_game.bat`: Entry script for running the app
- `assets/pieces/`: Piece images used by the board renderer

## Troubleshooting

If something fails:

1. Ensure Python is installed and available in PATH
2. Run `pip install -r requirements.txt`
3. Run `python unified_app.py` from terminal to see errors
4. Make sure another game instance is not already running