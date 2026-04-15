import PyInstaller.__main__
import os
import sys

print("=== Chess Server Build Script ===")
print("Checking dependencies...")

# Ensure all required files exist
required_files = [
    'server.py',
    'client.py',
    'local_game.py',
    'board.py',
    'engine/chess_engine.py',
    'application/game_controller.py',
    'ai_agent.py',
    'timer_manager.py',
    'UserInterface.py',
    'network.py',
    'game.py'
]

required_piece_files = [
    'assets/pieces/white_pawn.png',
    'assets/pieces/white_knight.png',
    'assets/pieces/white_bishop.png',
    'assets/pieces/white_rook.png',
    'assets/pieces/white_queen.png',
    'assets/pieces/white_king.png',
    'assets/pieces/black_pawn.png',
    'assets/pieces/black_knight.png',
    'assets/pieces/black_bishop.png',
    'assets/pieces/black_rook.png',
    'assets/pieces/black_queen.png',
    'assets/pieces/black_king.png',
]

missing_files = [f for f in required_files if not os.path.exists(f)]
if missing_files:
    print("Error: The following required files are missing:")
    for f in missing_files:
        print(f"  - {f}")
    sys.exit(1)

missing_piece_files = [f for f in required_piece_files if not os.path.exists(f)]
if missing_piece_files:
    print("Error: Missing piece image files under assets/pieces:")
    for f in missing_piece_files:
        print(f"  - {f}")
    sys.exit(1)

print("All required files found.")
print("Starting build process...")

try:
    PyInstaller.__main__.run([
        'server.py',
        '--name=game',
        '--onefile',
        '--noconsole',
        '--add-data=client.py;.',
        '--add-data=local_game.py;.',
        '--add-data=board.py;.',
        '--add-data=engine/chess_engine.py;engine',
        '--add-data=application/game_controller.py;application',
        '--add-data=ai_agent.py;.',
        '--add-data=timer_manager.py;.',
        '--add-data=UserInterface.py;.',
        '--add-data=network.py;.',
        '--add-data=game.py;.',
        '--add-data=assets/pieces;assets/pieces',
        '--hidden-import=pygame',
        '--hidden-import=chess',
        '--hidden-import=tkinter',
        '--collect-all=pygame',
        '--collect-all=chess'
    ])
    print("\nBuild completed successfully!")
    print("You can find your game.exe in the 'dist' folder.")
except Exception as e:
    print(f"\nBuild failed with error: {str(e)}")
    sys.exit(1) 