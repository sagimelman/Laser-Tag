import socket
import threading
import json
import time
from NetworkEntity import NetworkEntity

class LaserTagServer(NetworkEntity):
    def __init__(self, host='0.0.0.0', port=9999):
        """
        Initialize a simplified Laser Tag Server that just handles button presses.
        
        Args:
            host: Host address to bind to (default: all interfaces)
            port: Port number to bind to (default: 9999)
        """
        # Initialize with NetworkEntity parameters
        super().__init__(
            entity_type="server",
            device_name="LaserTagServer",
            ip_address=host,
            port=port,
            connected=False
        )
        
        # Server properties
        self.server_socket = None
        self.running = False
        self.clients = {}  # Dict of {client_id: (socket, address, player_name)}
        self.client_threads = {}  # Dict of {client_id: thread_object}
        self.next_client_id = 1
        
        # Lock for thread safety
        self.lock = threading.Lock()
    
    def start(self):
        """Start the server and begin accepting connections."""
        try:
            # Create server socket
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.ip_address, self.port))
            self.server_socket.listen(5)
            self.connected = True
            self.running = True
            
            print(f"Server started on {self.ip_address}:{self.port}")
            
            # Begin accepting connections
            self.accept_connections()
            
        except Exception as e:
            print(f"Error starting server: {e}")
            self.shutdown()
    
    def accept_connections(self):
        """Accept incoming client connections."""
        print("Waiting for client connections...")
        self.server_socket.settimeout(1.0)  # 1 second timeout for checking self.running
        
        while self.running:
            try:
                client_socket, client_address = self.server_socket.accept()
                # Create a new thread to handle this client
                client_id = self.next_client_id
                self.next_client_id += 1
                
                print(f"New connection from {client_address}, assigned ID: {client_id}")
                
                # Store client info (socket, address, no name yet)
                with self.lock:
                    self.clients[client_id] = (client_socket, client_address, None)
                
                # Start client handler thread
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, client_id)
                )
                client_thread.daemon = True
                client_thread.start()
                
                with self.lock:
                    self.client_threads[client_id] = client_thread
                    
            except socket.timeout:
                # This is expected due to the socket timeout
                continue
            except Exception as e:
                if self.running:  # Only print if we didn't initiate shutdown
                    print(f"Error accepting connection: {e}")
    
    def handle_client(self, client_socket, client_id):
        """
        Handle communication with a connected client.
        
        Args:
            client_socket: Socket connected to the client
            client_id: ID assigned to this client
        """
        try:
            # Set a timeout for receiving data
            client_socket.settimeout(0.5)
            
            buffer = b''
            last_active_time = time.time()
            
            while self.running:
                try:
                    # Try to receive data
                    data = client_socket.recv(1024)
                    
                    # If no data, client probably disconnected
                    if not data:
                        print(f"Empty data received from client {client_id}, assuming disconnected")
                        break
                    
                    # Client is active
                    last_active_time = time.time()
                    
                    # Add to buffer and process complete messages
                    buffer += data
                    
                    # Process complete lines (messages end with newline)
                    lines = buffer.split(b'\n')
                    
                    # Keep the last incomplete line in the buffer
                    buffer = lines.pop(-1) if not data.endswith(b'\n') else b''
                    
                    # Process complete messages
                    for line in lines:
                        if line:  # Skip empty lines
                            try:
                                print(f"Processing line: {line}")
                                message = json.loads(line.decode('utf-8'))
                                self.process_message(message, client_id)
                            except json.JSONDecodeError as e:
                                print(f"JSON decode error from client {client_id}: {e}, data: {line}")
                    
                except socket.timeout:
                    # This is expected due to the socket timeout
                    # Check if client has been inactive for too long (30 seconds)
                    if time.time() - last_active_time > 30:
                        print(f"Client {client_id} inactive for 30 seconds, checking connection")
                        # Send a ping message to check if client is still there
                        try:
                            ping_msg = {"type": "ping"}
                            self.send_message(client_socket, ping_msg)
                            last_active_time = time.time()  # Reset the timer
                        except Exception:
                            print(f"Failed to send ping to client {client_id}, assuming disconnected")
                            break
                    continue
                except ConnectionResetError:
                    print(f"Connection reset by client {client_id}")
                    break
                except Exception as e:
                    print(f"Error handling client {client_id}: {e}")
                    break
        finally:
            # Client disconnected or error occurred
            self.disconnect_client(client_socket, client_id)
    
    def process_message(self, message, client_id):
        """
        Process a message received from a client.
        
        Args:
            message: The parsed JSON message
            client_id: ID of the client that sent the message
        """
        msg_type = message.get("type")
        
        print(f"Received message from client {client_id}: {message}")
        
        if msg_type == "register":
            # Player is registering with the server
            player_name = message.get("player_name", f"Player{client_id}")
            
            # Update client info with player name
            with self.lock:
                socket_obj, address, _ = self.clients[client_id]
                self.clients[client_id] = (socket_obj, address, player_name)
            
            print(f"Client {client_id} registered as {player_name}")
            
            # Send welcome message with assigned ID
            welcome_msg = {
                "type": "welcome",
                "player_id": client_id,
                "player_name": player_name
            }
            success = self.send_message(self.clients[client_id][0], welcome_msg)
            print(f"Welcome message {'sent successfully' if success else 'FAILED to send'}")
            
            # Send an additional acknowledgment message
            ack_msg = {
                "type": "ack",
                "message": "Registration successful"
            }
            self.send_message(self.clients[client_id][0], ack_msg)
            
        elif msg_type == "heartbeat":
            # Client heartbeat - send an acknowledgment
            print(f"Heartbeat from client {client_id}")
            
            # Send back an acknowledgment for heartbeats
            with self.lock:
                if client_id in self.clients:
                    ack_msg = {
                        "type": "heartbeat_ack",
                        "timestamp": time.time()
                    }
                    self.send_message(self.clients[client_id][0], ack_msg)
            
        elif msg_type == "button_press":
            # Button press notification
            button_pin = message.get("button_pin")
            player_name = message.get("player_name", f"Player{client_id}")
            
            print(f"BUTTON PRESS on pin {button_pin} from player {player_name} (ID: {client_id})!")
            
            # Send acknowledgment back to the client
            with self.lock:
                if client_id in self.clients:
                    button_ack = {
                        "type": "button_ack",
                        "button_pin": button_pin,
                        "received": True
                    }
                    self.send_message(self.clients[client_id][0], button_ack)
            
            # You could broadcast this to all clients if needed
            # self.broadcast_message({
            #     "type": "player_action",
            #     "player_id": client_id,
            #     "player_name": player_name,
            #     "action": "button_press",
            #     "button_pin": button_pin
            # })
    
    def send_message(self, client_socket, message):
        """
        Send a message to a specific client.
        
        Args:
            client_socket: Socket to send to
            message: Message to send (will be converted to JSON)
        """
        try:
            json_data = json.dumps(message).encode('utf-8') + b'\n'
            client_socket.send(json_data)
            return True
        except Exception as e:
            print(f"Error sending message: {e}")
            return False
    
    def broadcast_message(self, message):
        """
        Send a message to all connected clients.
        
        Args:
            message: Message to broadcast (will be converted to JSON)
        """
        with self.lock:
            for client_id, (client_socket, _, _) in list(self.clients.items()):
                self.send_message(client_socket, message)
    
    def disconnect_client(self, client_socket, client_id=None):
        """
        Disconnect a client and clean up resources.
        
        Args:
            client_socket: Socket to disconnect
            client_id: ID of client to disconnect (if known)
        """
        try:
            # Try to close the socket
            client_socket.close()
        except:
            pass
        
        # If we have the client ID, remove from lists
        if client_id:
            with self.lock:
                if client_id in self.clients:
                    player_name = self.clients[client_id][2] or f"Player{client_id}"
                    print(f"Client {client_id} ({player_name}) disconnected")
                    del self.clients[client_id]
                if client_id in self.client_threads:
                    del self.client_threads[client_id]
    
    def shutdown(self):
        """Shut down the server and clean up resources."""
        self.running = False
        
        # Close all client connections
        with self.lock:
            for client_id, (client_socket, _, _) in list(self.clients.items()):
                try:
                    client_socket.close()
                except:
                    pass
            
            self.clients.clear()
            self.client_threads.clear()
        
        # Close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
            
        print("Server has been shut down.")


if __name__ == "__main__":
    # Start the server on the default port
    server = LaserTagServer(host='0.0.0.0', port=9999)
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.shutdown()
