import socket
import time

class NetworkHandler:
    def __init__(self, is_server=False):
        self.socket = socket.socket()
        if is_server:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
    def connect_to_server(self, host="localhost", port=9999, max_retries=5):
        """Client method to connect to server."""
        retries = 0
        while retries < max_retries:
            try:
                print(f"Attempting to connect (attempt {retries + 1}/{max_retries})...")
                self.socket.connect((host, port))
                return True
            except ConnectionRefusedError:
                print(f"Connection attempt {retries + 1} failed. Server might not be ready...")
                retries += 1
                if retries < max_retries:
                    time.sleep(2)  # Wait before retrying
                self.socket = socket.socket()  # Create new socket for retry
            except Exception as e:
                print(f"Connection error: {e}")
                return False
        
        print("Failed to connect after maximum retries")
        return False

    def start_server(self, ip="127.0.0.1", port=9999):
        """Server method to start listening."""
        try:
            self.socket.bind((ip, port))
            self.socket.listen(2)  # Listen for 2 clients max
            print(f"Server listening on {ip}:{port}")
            return True
        except Exception as e:
            print(f"Server error: {e}")
            return False

    def send_message(self, message, blocking=True):
        """Send a message with proper error handling."""
        try:
            if blocking:
                self.socket.setblocking(True)
            self.socket.send(message.encode())
            return True
        except Exception as e:
            print(f"Error sending message: {e}")
            return False
        finally:
            if blocking:
                self.socket.setblocking(False)

    def receive_message(self, blocking=True):
        """Receive a message with proper error handling."""
        try:
            if blocking:
                self.socket.setblocking(True)
            data = self.socket.recv(1024).decode()
            return data
        except BlockingIOError:
            return None  # No data available
        except Exception as e:
            print(f"Error receiving message: {e}")
            return None
        finally:
            if blocking:
                self.socket.setblocking(False)

    def close(self):
        """Close the socket connection."""
        try:
            self.socket.close()
        except:
            pass 