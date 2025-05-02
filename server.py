import socket
import threading
import json
import time
from network_entity import NetworkEntity
from game import Game

class Server(NetworkEntity):
    def __init__(self, host='0.0.0.0', port=9999):
        super().__init__()
        self.host = host
        self.port = port
        self.server_socket = None
        self.clients = {}  # Maps client_id to (socket, address) tuple
        self.client_lock = threading.Lock()
        self.game = Game()
        self.next_player_id = 1
        self.running = False
        
    def start(self):
        """Start the server and wait for connections"""
        # Initialize server socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.server_socket.settimeout(0.1)  # Short timeout for non-blocking operation
        
        print(f"Server started on {self.host}:{self.port}")
        self.running = True
        
        # Start game update thread
        game_thread = threading.Thread(target=self.game_loop)
        game_thread.daemon = True
        game_thread.start()
        
        # Main server loop - accept connections
        try:
            while self.running:
                try:
                    client_socket, addr = self.server_socket.accept()
                    # Assign client id and start handler thread
                    client_id = self.next_player_id
                    self.next_player_id += 1
                    
                    with self.client_lock:
                        self.clients[client_id] = (client_socket, addr)
                    
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, client_id)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                    
                    print(f"New connection from {addr}. Assigned ID: {client_id}")
                except socket.timeout:
                    # No new connections, just continue
                    pass
                except Exception as e:
                    print(f"Error accepting connection: {e}")
                    
                time.sleep(0.01)  # Small delay to prevent 100% CPU usage
        except KeyboardInterrupt:
            print("Server shutting down...")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the server and close all connections"""
        self.running = False
        
        # Close all client connections
        with self.client_lock:
            for client_id, (client_socket, _) in list(self.clients.items()):
                try:
                    client_socket.close()
                except:
                    pass
            self.clients.clear()
        
        # Close server socket
        if self.server_socket:
            self.server_socket.close()
            self.server_socket = None
    
    def handle_client(self, client_socket, client_id):
        """Handle communication with a client"""
        client_socket.settimeout(0.1)  # Short timeout for non-blocking operations
        
        try:
            while self.running:
                try:
                    # Try to receive data from client
                    data = client_socket.recv(1024)
                    if not data:
                        # Client disconnected
                        break
                    
                    # Process the received data
                    message = json.loads(data.decode('utf-8'))
                    self.on_message_received(client_id, message)
                    
                except socket.timeout:
                    # No data available, just continue
                    pass
                except json.JSONDecodeError:
                    print(f"Invalid JSON from client {client_id}")
                except Exception as e:
                    print(f"Error handling client {client_id}: {e}")
                    break
                
                time.sleep(0.01)  # Small delay
        finally:
            # Clean up when client disconnects
            with self.client_lock:
                if client_id in self.clients:
                    del self.clients[client_id]
            
            self.game.remove_player(client_id)
            print(f"Client {client_id} disconnected")
            
            # Broadcast player disconnect to other clients
            self.broadcast({
                "type": "player_disconnect",
                "player_id": client_id
            })
            
            try:
                client_socket.close()
            except:
                pass
    
    def on_message_received(self, client_id, message):
        """Process a message received from a client"""
        msg_type = message.get("type")
        msg_data = message.get("data", {})
        
        # Process game-related messages
        self.process_game_message(client_id, msg_type, msg_data)
    
    def process_game_message(self, client_id, message_type, message_data):
        """Process game-related messages from clients"""
        if message_type == "register":
            # New player registration
            player_name = message_data.get("player_name", f"Player{client_id}")
            self.game.add_player(client_id, player_name)
            
            # Send welcome message
            self.send_to_client(client_id, {
                "type": "welcome",
                "player_id": client_id,
                "player_name": player_name
            })
            
            print(f"Registered new player: {player_name} (ID: {client_id})")
            
        elif message_type == "hit_report":
            # A player reported being hit
            shooter_id = message_data.get("shooter_id")
            target_id = message_data.get("target_id")
            
            if shooter_id and target_id:
                # Process the hit in the game logic
                hit_success = self.game.process_hit(shooter_id, target_id)
                
                if hit_success:
                    # Get updated target player state
                    target_player = self.game.players.get(target_id)
                    if target_player:
                        # Notify target they were hit
                        self.send_to_client(target_id, {
                            "type": "hit",
                            "shooter_id": shooter_id,
                            "health": target_player.health,
                            "is_alive": target_player.is_alive
                        })
                        
                        # Notify shooter they scored a hit
                        self.send_to_client(shooter_id, {
                            "type": "hit_confirmed",
                            "target_id": target_id,
                            "score": self.game.players[shooter_id].score if shooter_id in self.game.players else 0
                        })
        
        elif message_type == "start_game_request":
            # Request to start the game
            if self.game.state == "WAITING" and len(self.game.players) >= 2:
                self.start_game()
                
        elif message_type == "shot_fired":
            # Player fired a shot (for stats tracking)
            if client_id in self.game.players:
                self.game.players[client_id].record_shot()
    
    def start_game(self):
        """Start a new game"""
        if self.game.start_game():
            # Broadcast game start to all clients
            self.broadcast({
                "type": "game_start",
                "players": {
                    str(p_id): {"name": p.name, "team": p.team}
                    for p_id, p in self.game.players.items()
                },
                "settings": self.game.game_settings
            })
            
            print("Game started!")
    
    def end_game(self):
        """End the current game"""
        result = self.game.end_game()
        
        # Broadcast game end to all clients
        self.broadcast({
            "type": "game_end",
            "winner": result["winner"],
            "winner_name": result["winner_name"],
            "scores": result["scores"]
        })
        
        print(f"Game ended! Winner: {result['winner_name']}")
    
    def send_to_client(self, client_id, message):
        """Send a message to a specific client"""
        try:
            with self.client_lock:
                if client_id in self.clients:
                    client_socket, _ = self.clients[client_id]
                    # Format message as JSON if it's not already a string
                    if not isinstance(message, str):
                        message = json.dumps(message)
                    client_socket.send(message.encode('utf-8') + b'\n')
                    return True
        except Exception as e:
            print(f"Error sending to client {client_id}: {e}")
        return False
    
    def broadcast(self, message):
        """Send a message to all connected clients"""
        with self.client_lock:
            # Format message as JSON if it's not already a string
            if not isinstance(message, str):
                message = json.dumps(message)
                
            for client_id, (client_socket, _) in list(self.clients.items()):
                try:
                    client_socket.send(message.encode('utf-8') + b'\n')
                except Exception as e:
                    print(f"Error broadcasting to client {client_id}: {e}")
    
    def game_loop(self):
        """Main game update loop"""
        while self.running:
            # Update game state
            if self.game.state == "ACTIVE":
                # Check for game end
                result = self.game.update()
                if result:  # Game has ended
                    self.end_game()
                
                # Update GUI if needed
                if hasattr(self, 'gui') and self.gui:
                    self.update_gui()
            
            time.sleep(0.1)  # Small delay
    
    def update_gui(self):
        """Update the GUI with latest game state"""
        if hasattr(self, 'gui') and self.gui:
            self.gui.update_game_state(self.game.get_game_state())
