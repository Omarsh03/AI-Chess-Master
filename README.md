# Pawn Chess Game

A chess variant where only pawns are used, implemented with Python and featuring AI gameplay.

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Required Python packages (will be installed automatically):
  - chess==1.11.1
  - pygame==2.6.1
  - python-chess==1.999
  - numpy==1.24.3

## Quick Start

1. Simply double-click `run_game.bat`
2. The script will:
   - Check for Python installation
   - Install required packages if needed
   - Start the server
   - Start the client

## Manual Setup (Alternative)

1. Create and activate a virtual environment:

For Windows:
```bash
python -m venv venv
venv\Scripts\activate
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Start the server:
```bash
python server.py
```

4. The client will automatically start in a new window

## Game Modes

### Human vs AI
- You will be randomly assigned White or Black
- If you're White, you move first
- If you're Black, the AI will make the first move
- Make moves by clicking on a pawn and then clicking its destination

### AI vs AI
- Watch two AI players compete against each other
- The game will play automatically
- You can observe the moves and strategy

### Human vs Human (Local)
- Play against another person on the same computer
- White moves first
- Players take turns making moves

## Custom Board Setup

1. Click "Custom Board Setup" in the server window
2. Use the radio buttons to select piece type (White Pawn/Black Pawn)
3. Click on the board squares to place pieces
4. Click "Apply" to save the setup
5. Start the game with your custom position

## Game Rules

- Only pawns are used
- Pawns move and capture according to standard chess rules
- Win by:
  - Getting a pawn to the opposite end of the board
  - Capturing all opponent's pawns
  - Making your opponent run out of legal moves
  - Making your opponent run out of time

## Time Control

- Each player starts with the specified amount of time
- Time decreases only during your turn
- Running out of time results in losing the game

## Files Description

- `server.py`: Main server implementation and game setup
- `client.py`: Client implementation and game interface
- `board.py`: Chess board representation and game logic
- `ai_agent.py`: AI player implementation
- `UserInterface.py`: Game UI implementation
- `timer_manager.py`: Time control management
- `local_game.py`: Local two-player game implementation

## Troubleshooting

If you encounter any errors:
1. Make sure Python is installed and added to PATH
2. Try running `pip install -r requirements.txt` manually
3. Check the error messages in the server and client windows
4. Make sure no other instance of the game is running 