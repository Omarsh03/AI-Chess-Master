import socket
import tkinter as tk
from tkinter import ttk, messagebox
import threading
from ai_agent import AIAgent
import chess
import time
import random
from board import ChessBoard
import subprocess
import sys
import os
from timer_manager import TimerManager

class CustomBoardSetup:
    def __init__(self, parent, callback):
        self.window = tk.Toplevel(parent)
        self.window.title("Custom Board Setup")
        self.callback = callback
        
        # Initialize empty board
        self.board = [[None for _ in range(8)] for _ in range(8)]
        
        # Current piece to place (White/Black/None)
        self.current_piece = None
        
        self.setup_gui()
        
    def setup_gui(self):
        """Setup the custom board GUI."""
        # Control frame
        control_frame = ttk.Frame(self.window, padding="5")
        control_frame.grid(row=0, column=0, sticky="ew")
        
        # Radio buttons for piece selection
        self.piece_var = tk.StringVar(value="none")
        ttk.Radiobutton(control_frame, text="White Pawn", variable=self.piece_var, 
                       value="white").grid(row=0, column=0, padx=5)
        ttk.Radiobutton(control_frame, text="Black Pawn", variable=self.piece_var, 
                       value="black").grid(row=0, column=1, padx=5)
        ttk.Radiobutton(control_frame, text="Remove", variable=self.piece_var, 
                       value="none").grid(row=0, column=2, padx=5)
        
        # Setup command text input
        text_frame = ttk.Frame(self.window, padding="5")
        text_frame.grid(row=1, column=0, sticky="ew")
        ttk.Label(text_frame, text="Setup Command:").pack(side=tk.LEFT, padx=5)
        self.setup_text = ttk.Entry(text_frame, width=50)
        self.setup_text.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(text_frame, text="Parse", command=self.parse_setup_text).pack(side=tk.LEFT, padx=5)
        
        # Board frame
        board_frame = ttk.Frame(self.window, padding="10")
        board_frame.grid(row=2, column=0)
        
        # Create 8x8 grid of buttons
        self.squares = []
        for row in range(8):
            row_squares = []
            for col in range(8):
                btn = ttk.Button(board_frame, width=3, 
                               command=lambda r=row, c=col: self.square_click(r, c))
                btn.grid(row=row, column=col, padx=1, pady=1)
                row_squares.append(btn)
            self.squares.append(row_squares)
        
        # Control buttons
        btn_frame = ttk.Frame(self.window, padding="5")
        btn_frame.grid(row=3, column=0, sticky="ew")
        
        ttk.Button(btn_frame, text="Clear Board", 
                  command=self.clear_board).grid(row=0, column=0, padx=5)
        ttk.Button(btn_frame, text="Default Setup", 
                  command=self.default_setup).grid(row=0, column=1, padx=5)
        ttk.Button(btn_frame, text="Apply", 
                  command=self.apply_setup).grid(row=0, column=2, padx=5)
        
        # Add labels for columns (a-h) and rows (1-8)
        for col in range(8):
            lbl = ttk.Label(board_frame, text=chr(97 + col))  # a-h
            lbl.grid(row=8, column=col)
        for row in range(8):
            lbl = ttk.Label(board_frame, text=str(8 - row))  # 8-1
            lbl.grid(row=row, column=8)
            
    def parse_setup_text(self):
        """Parse setup command from text input and update board."""
        setup_text = self.setup_text.get().strip()
        if not setup_text.startswith("Setup"):
            setup_text = "Setup " + setup_text
            
        # Clear current board
        self.clear_board()
        
        # Parse pieces
        pieces = setup_text.split()[1:]  # Skip "Setup"
        for piece in pieces:
            if len(piece) == 3 and piece[0] in ['W', 'B'] and piece[1] in 'abcdefgh' and piece[2] in '12345678':
                color = piece[0]
                col = ord(piece[1]) - ord('a')  # Convert file to column (0-7)
                row = 8 - int(piece[2])  # Convert rank to row (0-7)
                
                if 0 <= row < 8 and 0 <= col < 8:
                    self.board[row][col] = color
                    self.squares[row][col].configure(text=color)
            
    def square_click(self, row, col):
        """Handle clicking on a square."""
        piece = self.piece_var.get()
        if piece == "white":
            self.board[row][col] = "W"
            self.squares[row][col].configure(text="W")
        elif piece == "black":
            self.board[row][col] = "B"
            self.squares[row][col].configure(text="B")
        else:  # remove
            self.board[row][col] = None
            self.squares[row][col].configure(text="")
        
        # Update text input to match board state
        self.update_setup_text()
            
    def clear_board(self):
        """Clear all pieces from the board."""
        for row in range(8):
            for col in range(8):
                self.board[row][col] = None
                self.squares[row][col].configure(text="")
        self.setup_text.delete(0, tk.END)
        self.setup_text.insert(0, "Setup")
                
    def default_setup(self):
        """Set up the default starting position."""
        self.clear_board()
        # Place white pawns on rank 2
        for col in range(8):
            self.board[6][col] = "W"
            self.squares[6][col].configure(text="W")
        # Place black pawns on rank 7
        for col in range(8):
            self.board[1][col] = "B"
            self.squares[1][col].configure(text="B")
        self.update_setup_text()
            
    def update_setup_text(self):
        """Update the setup text input to match the current board state."""
        setup_parts = ["Setup"]
        for row in range(8):
            for col in range(8):
                if self.board[row][col]:
                    # Convert to chess notation (e.g., "a2" for (6,0))
                    square = chr(97 + col) + str(8 - row)
                    setup_parts.append(self.board[row][col] + square)
        
        setup_cmd = " ".join(setup_parts)
        self.setup_text.delete(0, tk.END)
        self.setup_text.insert(0, setup_cmd)
            
    def apply_setup(self):
        """Generate setup command and send it back."""
        setup_cmd = self.setup_text.get().strip()
        if not setup_cmd.startswith("Setup"):
            setup_cmd = "Setup " + setup_cmd
            
        # Check if there are any pieces on the board
        pieces = setup_cmd.split()[1:]  # Skip "Setup"
        if not pieces:
            # If no pieces in command, generate from board state
            setup_parts = ["Setup"]
            for row in range(8):
                for col in range(8):
                    if self.board[row][col]:
                        # Convert to chess notation (e.g., "a2" for (6,0))
                        square = chr(97 + col) + str(8 - row)
                        setup_parts.append(self.board[row][col] + square)
            setup_cmd = " ".join(setup_parts)
            
        # Only apply if there are pieces
        if len(setup_cmd.split()) > 1:  # More than just "Setup"
            self.callback(setup_cmd)
            self.window.destroy()
        else:
            # Show error message if no pieces
            messagebox.showerror("Error", "Cannot apply empty board setup. Please place some pieces first.")

def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class ChessServer:
    def __init__(self):
        self.server_socket = socket.socket()
        self.ip = "127.0.0.1"
        self.port = 9999
        # Add socket reuse option
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.clients = []
        self.game_mode = None
        self.board = None  # Initialize board later when game mode is selected
        self.default_time = 5  # Default time in minutes
        self.time_limit = None  # Will be set when game starts
        self.white_time = None  # Will be set when game starts
        self.black_time = None  # Will be set when game starts
        self.last_move_time = None
        self.timer = None  # Initialize timer when game starts
        self.ai_white = None
        self.ai_black = None
        self.server_running = False
        self.current_game_state = []  # Store moves for reconnection
        self.custom_board_setup = "Setup Wa2 Wb2 Wc2 Wd2 We2 Wf2 Wg2 Wh2 Ba7 Bb7 Bc7 Bd7 Be7 Bf7 Bg7 Bh7"
        
        # Initialize GUI
        self.root = tk.Tk()
        self.root.title("Chess Server")
        self.setup_gui()
        
        # Handle window closing
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_gui(self):
        """Setup server GUI with game mode selection and time control."""
        frame = ttk.Frame(self.root, padding="10")
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Game mode selection
        ttk.Label(frame, text="Select Game Mode:").grid(row=0, column=0, pady=5)
        
        self.mode_var = tk.StringVar(value="HUMAN_AI")  # Default selection
        modes = [("Human vs AI", "HUMAN_AI"), 
                ("AI vs AI", "AI_AI"),
                ("Human vs Human", "HUMAN_HUMAN")]
                
        for i, (text, mode) in enumerate(modes):
            ttk.Radiobutton(frame, text=text, variable=self.mode_var, 
                          value=mode).grid(row=i+1, column=0, pady=2)

        # Time control input
        time_frame = ttk.Frame(frame)
        time_frame.grid(row=len(modes)+1, column=0, pady=10)
        
        ttk.Label(time_frame, text="Time Control (minutes):").pack(side=tk.LEFT, padx=5)
        self.time_var = tk.StringVar(value=str(self.default_time))
        time_entry = ttk.Entry(time_frame, textvariable=self.time_var, width=5)
        time_entry.pack(side=tk.LEFT)

        # Custom board setup button
        ttk.Button(frame, text="Custom Board Setup", 
                  command=self.open_board_setup).grid(row=len(modes)+2, column=0, pady=5)

        # Start button
        ttk.Button(frame, text="Start Game", 
                  command=self.start_game).grid(row=len(modes)+3, column=0, pady=5)
        
        # Status label
        self.status_label = ttk.Label(frame, text="Server Status: Not Running")
        self.status_label.grid(row=len(modes)+4, column=0, pady=5)

    def open_board_setup(self):
        """Open the custom board setup window."""
        CustomBoardSetup(self.root, self.update_board_setup)
        
    def update_board_setup(self, setup_cmd):
        """Update the board setup command."""
        self.custom_board_setup = setup_cmd
        print(f"New board setup: {setup_cmd}")
        # If board exists, update it with new setup
        if self.board:
            self.board.setup_board(setup_cmd)
            print("Updated existing board with new setup")
        print(f"Custom board setup updated: {setup_cmd}")

    def start_client(self):
        """Start a new client process."""
        try:
            # Use the resource path function
            client_path = get_resource_path('client.py')
            
            # Start client process
            if sys.platform == 'win32':
                subprocess.Popen(['python', client_path], creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:
                # For macOS and Linux
                subprocess.Popen(['python3', client_path])
                
            print("Started new client process")
        except Exception as e:
            print(f"Error starting client: {e}")

    def setup_board_state(self):
        """Setup initial board state and AIs based on game mode."""
        print(f"Setting up board for game mode: {self.game_mode}")
        self.board = ChessBoard()  # Use our custom ChessBoard class
        
        # Setup the board with the custom position
        if self.custom_board_setup:
            print(f"Initializing board with custom setup: {self.custom_board_setup}")
            self.board.setup_board(self.custom_board_setup)
        else:
            # Use default setup if no custom setup is provided
            default_setup = "Setup Wa2 Wb2 Wc2 Wd2 We2 Wf2 Wg2 Wh2 Ba7 Bb7 Bc7 Bd7 Be7 Bf7 Bg7 Bh7"
            print(f"Using default setup: {default_setup}")
            self.board.setup_board(default_setup)
        
        print("Board initialized with setup")
        
        # Initialize timer with the time from GUI
        self.timer = TimerManager(self.time_limit)
        print(f"Timer initialized with {self.time_limit//60} minutes")
        
        # Initialize AIs if needed
        if self.game_mode in ["HUMAN_AI", "AI_AI"]:
            print("Initializing AIs")
            self.ai_white = AIAgent(self.board, chess.WHITE, self.time_limit)
            self.ai_black = AIAgent(self.board, chess.BLACK, self.time_limit)
        
        # Print initial board state
        print("Initial board state:")
        print(self.board.get_board_state())

    def on_closing(self):
        """Handle window closing event."""
        self.server_running = False
        try:
            self.server_socket.close()
            for client in self.clients:
                try:
                    client.close()
                except:
                    pass
        except:
            pass
        self.root.quit()
        self.root.destroy()

    def start_game(self):
        """Start either a networked game or local game based on mode."""
        self.game_mode = self.mode_var.get()
        if not self.game_mode:
            self.status_label.config(text="Please select a game mode!")
            return

        # Validate and set time control
        try:
            time_minutes = float(self.time_var.get())
            if time_minutes <= 0:
                self.status_label.config(text="Time must be greater than 0!")
                return
            self.time_limit = int(time_minutes * 60)  # Convert to seconds
            self.white_time = self.time_limit
            self.black_time = self.time_limit
        except ValueError:
            self.status_label.config(text="Invalid time format!")
            return

        if self.game_mode == "HUMAN_HUMAN":
            self.start_local_game()
        else:
            self.start_server()

    def start_server(self):
        """Start the chess server for networked games."""
        # If server is already running, clean up and restart
        if self.server_running:
            # Clean up existing connections and state
            self.cleanup_server()
            # Close and recreate the server socket
            try:
                self.server_socket.close()
            except:
                pass
            self.server_socket = socket.socket()
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            self.current_game_state = []  # Reset game state
            self.board = None  # Reset board
            self.ai_white = None  # Reset AI instances
            self.ai_black = None
            # Keep the game mode from the GUI selection
            self.game_mode = self.mode_var.get()  # Ensure game mode is set before setup
            self.setup_board_state()  # This will create new board and AI instances
            self.server_running = True

            # Start server in a separate thread
            server_thread = threading.Thread(target=self.run_server)
            server_thread.daemon = True
            server_thread.start()
            
            self.status_label.config(text=f"Server Running - Mode: {self.game_mode}")
            
            # Start client for networked games
            self.start_client()
            
        except Exception as e:
            self.status_label.config(text=f"Error: {str(e)}")
            print(f"Error starting server: {e}")

    def run_server(self):
        """Run the chess server."""
        try:
            self.server_socket.bind((self.ip, self.port))
            self.server_socket.listen(2)  # Listen for 2 clients max
            print(f"Server listening on {self.ip}:{self.port}")

            # For all modes, wait for one client
            while self.server_running:
                try:
                    client_socket, address = self.server_socket.accept()
                    self.clients.append(client_socket)
                    print(f"New connection from {address}")
                    
                    # Start client handler in a new thread
                    client_thread = threading.Thread(target=self.handle_client, 
                                                args=(client_socket, address))
                    client_thread.daemon = True
                    client_thread.start()
                    
                    # For Human vs Human, we only need one client
                    if self.game_mode == "HUMAN_HUMAN":
                        break
                except Exception as e:
                    if self.server_running:
                        print(f"Error accepting client: {e}")
                        break

        except Exception as e:
            print(f"Server error: {e}")
        finally:
            self.cleanup_server()

    def handle_client(self, client_socket, address):
        """Handle individual client connections."""
        try:
            # Send initial connection confirmation
            client_socket.send("Connected to the server".encode())
            response = client_socket.recv(1024).decode()
            print(f"Client {address} connected and responded: {response}")

            # Send initial setup using custom board setup
            client_socket.send(self.custom_board_setup.encode())
            response = client_socket.recv(1024).decode()
            print(f"Setup sent, client responded: {response}")

            # Send time limit in minutes (use the actual time from GUI)
            time_minutes = float(self.time_var.get())
            client_socket.send(f"Time {time_minutes}".encode())
            response = client_socket.recv(1024).decode()
            print(f"Time {time_minutes} minutes sent, client responded: {response}")

            # Send game mode and handle accordingly
            if self.game_mode == "HUMAN_AI":
                self.handle_human_ai_game(client_socket)
            elif self.game_mode == "AI_AI":
                self.handle_ai_ai_game(client_socket)
            else:  # HUMAN_HUMAN
                self.handle_human_human_game(client_socket)

        except Exception as e:
            print(f"Error handling client {address}: {e}")
        finally:
            if client_socket in self.clients:
                self.clients.remove(client_socket)
            try:
                client_socket.close()
            except:
                pass
            print(f"Connection closed with {address}")

    def update_timers(self):
        """Update the time remaining for the current player."""
        if self.last_move_time is None:
            self.last_move_time = time.time()
            return

        current_time = time.time()
        elapsed = current_time - self.last_move_time
        
        if self.board.board.turn == chess.WHITE:
            self.white_time -= elapsed
        else:
            self.black_time -= elapsed
            
        self.last_move_time = current_time

    def check_time_loss(self):
        """Check if either player has lost on time."""
        if self.white_time <= 0:
            print("\n=== Game Over ===")
            print("Black wins on time! White's time has expired.")
            return True
        elif self.black_time <= 0:
            print("\n=== Game Over ===")
            print("White wins on time! Black's time has expired.")
            return True
        return False

    def log_move(self, move_str, color):
        """Log move to terminal with color information."""
        time_left = self.white_time if color else self.black_time
        minutes = int(time_left // 60)
        seconds = int(time_left % 60)
        print(f"{'White' if color else 'Black'} moves: {move_str} ({minutes:02d}:{seconds:02d} remaining)")

    def handle_human_ai_game(self, client_socket):
        """Handle Human vs AI game."""
        try:
            # Randomly assign colors
            human_is_white = random.choice([True, False])
            color_msg = "White" if human_is_white else "Black"
            client_socket.send(color_msg.encode())
            print(f"Assigned {color_msg} to human player")
            
            # Wait for acknowledgment
            response = client_socket.recv(1024).decode()
            print(f"Client acknowledged color assignment: {response}")
            
            # Send time information to client
            client_socket.send(f"Time {self.timer.time_limit//60}".encode())
            response = client_socket.recv(1024).decode()
            
            # Start timer
            self.timer.start()
            
            # Replay moves if reconnecting
            if self.current_game_state:
                for move in self.current_game_state:
                    self.board.move_piece(move)
            
            # Send Begin signal before making AI move
            time.sleep(0.1)  # Small delay to ensure proper message separation
            client_socket.send("Begin".encode())
            print("Sent Begin signal")
            
            # If AI is White (human is Black), AI makes first move
            if not human_is_white and not self.current_game_state:
                print("AI is White, making first move...")
                self.timer.update(chess.WHITE)  # Update White's time
                ai = self.ai_white
                print("Getting legal moves for AI...")
                legal_moves = self.board.get_legal_moves()
                print(f"Available moves: {legal_moves}")
                if legal_moves:
                    ai_move = ai.get_best_move()
                    if ai_move:
                        move_uci = ai_move.uci()
                        if self.board.move_piece(move_uci):  # Verify move is valid
                            self.current_game_state.append(move_uci)
                            self.timer.log_move(move_uci, True)  # Log White's move
                            self.timer.switch_turn()  # Switch to Black's time
                            time.sleep(0.1)
                            client_socket.send(move_uci.encode())
                            print("AI move sent to client")
                            
                            # Check for time loss
                            if self.timer.check_time_loss():
                                client_socket.send("exit".encode())
                                return
                                
                            # Wait for acknowledgment
                            response = client_socket.recv(1024).decode()
                            print(f"Client acknowledged AI move: {response}")
                        else:
                            print("Invalid AI move!")
                            client_socket.send("exit".encode())
                            return
                    else:
                        print("AI couldn't generate a move!")
                        client_socket.send("exit".encode())
                        return
                else:
                    print("No legal moves available for AI!")
                    client_socket.send("exit".encode())
                    return
            
            while self.server_running:
                # Update timers
                self.timer.update(self.board.board.turn)
                
                # Check for time-based loss
                if self.timer.check_time_loss():
                    client_socket.send("exit".encode())
                    break
                
                # Receive human move
                move = client_socket.recv(1024).decode()
                print(f"Received move from human: {move}")
                
                if move == "Win":
                    print("Human has won!")
                    client_socket.send("exit".encode())
                    break
                    
                if move in ["Lost", "exit"]:
                    print(f"Game ended: {move}")
                    client_socket.send("exit".encode())
                    break

                # Make the move on the board
                if not self.board.move_piece(move):
                    print(f"Invalid move: {move}")
                    client_socket.send("exit".encode())
                    break

                self.current_game_state.append(move)
                self.timer.log_move(move, human_is_white)  # Log human's move
                self.timer.switch_turn()  # Switch to AI's time
                
                # Send acknowledgment of human move
                client_socket.send("OK".encode())
                print("Acknowledged human move")

                # Update timers before AI move
                self.timer.update(self.board.board.turn)
                
                # Check for time-based loss
                if self.timer.check_time_loss():
                    client_socket.send("exit".encode())
                    break

                # Make AI move
                ai = self.ai_white if not human_is_white else self.ai_black
                print(f"AI ({'White' if not human_is_white else 'Black'}) thinking...")
                legal_moves = self.board.get_legal_moves()
                print(f"Available moves: {legal_moves}")
                if legal_moves:
                    ai_move = ai.get_best_move()
                    if ai_move:
                        move_uci = ai_move.uci()
                        if self.board.move_piece(move_uci):
                            self.current_game_state.append(move_uci)
                            self.timer.log_move(move_uci, not human_is_white)  # Log AI's move
                            self.timer.switch_turn()  # Switch back to human's time
                            time.sleep(0.1)
                            client_socket.send(move_uci.encode())
                            print("AI move sent to client")
                            
                            # Check for time-based loss
                            if self.timer.check_time_loss():
                                client_socket.send("exit".encode())
                                break
                                
                            # Wait for acknowledgment
                            response = client_socket.recv(1024).decode()
                            print(f"Client acknowledged AI move: {response}")
                        else:
                            print("Invalid AI move!")
                            client_socket.send("exit".encode())
                            break
                    else:
                        print("AI couldn't generate a move!")
                        client_socket.send("exit".encode())
                        break
                else:
                    print("No legal moves available for AI!")
                    client_socket.send("exit".encode())
                    break

        except Exception as e:
            print(f"Error in human vs AI game: {e}")
            try:
                client_socket.send("exit".encode())
            except:
                pass

    def handle_ai_ai_game(self, client_socket):
        """Handle AI vs AI game."""
        try:
            client_socket.send("Spectator".encode())
            print("Starting AI vs AI game")
            
            # Send time information to client
            client_socket.send(f"Time {self.timer.time_limit//60}".encode())
            response = client_socket.recv(1024).decode()
            
            # Start timer
            self.timer.start()
            client_socket.send("Begin".encode())
            
            while self.server_running:
                # Update timers before White's move
                self.timer.update(chess.WHITE)
                
                # Check for time-based loss
                if self.timer.check_time_loss():
                    client_socket.send("exit".encode())
                    break
                
                # White AI move
                white_move = self.ai_white.get_best_move()
                if not white_move:
                    print("White AI has no moves")
                    client_socket.send("exit".encode())
                    break
                    
                if self.board.move_piece(white_move.uci()):
                    self.timer.log_move(white_move.uci(), True)  # Log White's move
                    self.timer.switch_turn()  # Switch to Black's time
                    client_socket.send(white_move.uci().encode())
                    time.sleep(1)  # Add delay between moves for visualization
                
                # Update timers before Black's move
                self.timer.update(chess.BLACK)
                
                # Check for time-based loss
                if self.timer.check_time_loss():
                    client_socket.send("exit".encode())
                    break
                
                # Black AI move
                black_move = self.ai_black.get_best_move()
                if not black_move:
                    print("Black AI has no moves")
                    client_socket.send("exit".encode())
                    break
                    
                if self.board.move_piece(black_move.uci()):
                    self.timer.log_move(black_move.uci(), False)  # Log Black's move
                    self.timer.switch_turn()  # Switch back to White's time
                    client_socket.send(black_move.uci().encode())
                    time.sleep(1)  # Add delay between moves
                
                if self.board.is_game_over():
                    client_socket.send("exit".encode())
                    break

        except Exception as e:
            print(f"Error in AI vs AI game: {e}")
            try:
                client_socket.send("exit".encode())
            except:
                pass

    def handle_human_human_game(self, client_socket):
        """Handle Human vs Human game."""
        try:
            # Send game mode
            client_socket.send("HUMAN_HUMAN".encode())
            response = client_socket.recv(1024).decode()
            print(f"Sent game mode: HUMAN_HUMAN")
            
            # Send initial game state
            time.sleep(0.1)
            client_socket.send("Begin".encode())
            print("Sent Begin signal")
            
            # Main game loop
            while self.server_running:
                # Wait for move
                move = client_socket.recv(1024).decode()
                print(f"Received move: {move}")
                
                if not move:
                    break
                    
                if move == "Win":
                    print("Win condition detected!")
                    client_socket.send("exit".encode())
                    break
                    
                if move in ["Lost", "exit"]:
                    print(f"Game ended: {move}")
                    client_socket.send("exit".encode())
                    break

                # Validate move
                if not self.board.move_piece(move):
                    print(f"Invalid move: {move}")
                    client_socket.send("exit".encode())
                    break

                # Store move in game state
                self.current_game_state.append(move)
                
                # Acknowledge move
                client_socket.send("OK".encode())
                print(f"Move {move} acknowledged")

                # Check for game over
                if self.board.is_game_over():
                    print("Game is over!")
                    client_socket.send("exit".encode())
                    break

        except ConnectionError:
            print("Client disconnected")
        except Exception as e:
            print(f"Error in human vs human game: {e}")
        finally:
            if client_socket in self.clients:
                self.clients.remove(client_socket)
            try:
                client_socket.close()
            except:
                pass

    def cleanup_server(self):
        """Clean up resources after server stops."""
        self.server_running = False
        # Send exit signal to all clients
        for client in self.clients:
            try:
                client.send("exit".encode())
                time.sleep(0.1)  # Small delay to ensure message is sent
            except:
                pass
        # Close all client connections
        for client in self.clients:
            try:
                client.close()
            except:
                pass
        self.clients = []
        
        # Close server socket
        try:
            self.server_socket.close()
        except:
            pass
        
        # Reset game state but preserve game mode
        self.board = None
        self.ai_white = None
        self.ai_black = None
        self.current_game_state = []
        
        # Update UI
        self.status_label.config(text="Server Status: Not Running")

    def start_local_game(self):
        """Start a local two-player game."""
        try:
            # Save current time setting for local game
            with open("time_settings.txt", "w") as f:
                f.write(self.time_var.get())
            
            # Use the resource path function
            game_path = get_resource_path('local_game.py')
            
            # Start local game process
            if sys.platform == 'win32':
                subprocess.Popen(['python', game_path], creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:
                # For macOS and Linux
                subprocess.Popen(['python3', game_path])
            
            print("Started local game")
            self.status_label.config(text="Local game started")
        except Exception as e:
            print(f"Error starting local game: {e}")
            self.status_label.config(text=f"Error starting local game: {str(e)}")

    def run(self):
        """Run the server application."""
        self.root.mainloop()

if __name__ == "__main__":
    server = ChessServer()
    server.run()