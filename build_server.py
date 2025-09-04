import PyInstaller.__main__
import os
import sys

print("=== Chess Server Build Script ===")
print("Checking dependencies...")

# Ensure all required files exist
required_files = [
    'server.py',
    'white_pawn.png',
    'black_pawn.png',
    'client.py',
    'local_game.py',
    'board.py',
    'ai_agent.py',
    'timer_manager.py',
    'UserInterface.py',
    'network.py',
    'game.py'
]

missing_files = [f for f in required_files if not os.path.exists(f)]
if missing_files:
    print("Error: The following required files are missing:")
    for f in missing_files:
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
        '--add-data=white_pawn.png;.',
        '--add-data=black_pawn.png;.',
        '--add-data=client.py;.',
        '--add-data=local_game.py;.',
        '--add-data=board.py;.',
        '--add-data=ai_agent.py;.',
        '--add-data=timer_manager.py;.',
        '--add-data=UserInterface.py;.',
        '--add-data=network.py;.',
        '--add-data=game.py;.',
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