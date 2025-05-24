from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle
from kivy.properties import ListProperty, StringProperty
from kivy.clock import Clock
from datetime import datetime
import logging
import socket
import threading
import json
import time
import sqlite3
from encryptions import encrypt_message, decrypt_message

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# -------------------- Modern Rounded Button --------------------
class ModernRoundedButton(Button):
    border_radius = ListProperty([12])
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_color = (0, 0, 0, 0)
        self.font_size = 16
        self.bold = True
        self.height = 40
        self.bind(pos=self.update_canvas, size=self.update_canvas)

    def update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(0, 0, 0, 0.2)
            RoundedRectangle(pos=(self.pos[0]+2, self.pos[1]-2), size=self.size, radius=self.border_radius)
            Color(*self.background_color)
            RoundedRectangle(pos=self.pos, size=self.size, radius=self.border_radius)

# -------------------- Complete Game Server --------------------
class GameServer:
    def __init__(self, gui_callback, host='0.0.0.0', port=9999):
        self.gui_callback = gui_callback
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False
        self.clients = {}  # {client_id: (socket, addr)}
        self.player_names = {}  # {client_id: player_name}
        self.lock = threading.Lock()
        self.game_state = {
            'max_players': 4,
            'game_duration': 300,
            'active_players': [],
            'is_running': False,
            'is_paused': False,
            'remaining_time': 300,
            'start_time': None,
            'pause_time': None,
            'elapsed_before_pause': 0
        }
        
        # ADD THIS - Game mechanics state
        self.player_health = {}  # {player_name: health}
        self.player_scores = {}  # {player_name: score}
        self.player_status = {}  # {player_name: 'alive', 'dead', 'respawning'}
        self.max_health = 3  # Players start with 3 health
        
        self.timer_thread = None
        self.connection_thread = None
        # Database setup
        self.init_database()
        self.log("Database initialized")
        

    def init_database(self):
        """Initialize the SQLite database and create tables"""
        try:
            self.db_connection = sqlite3.connect('lasertag.db', check_same_thread=False)
            self.db_connection.execute('''
                CREATE TABLE IF NOT EXISTS games (
                    game_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date_time TEXT NOT NULL,
                    duration INTEGER NOT NULL,
                    player_count INTEGER NOT NULL,
                    player_names TEXT NOT NULL
                )
            ''')
            self.db_connection.commit()
        except Exception as e:
            self.log(f"Database initialization error: {str(e)}", 'error')

    def save_game_to_database(self):
        """Save the completed game to the database"""
        try:
            # Get current date and time
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Calculate actual game duration
            if self.game_state['start_time']:
                actual_duration = int(time.time() - self.game_state['start_time'] - self.game_state.get('elapsed_before_pause', 0))
            else:
                actual_duration = 0
            
            # Get player count and names
            player_count = len(self.game_state['active_players'])
            player_names = ",".join(self.game_state['active_players'])
            
            # Insert into database
            self.db_connection.execute('''
                INSERT INTO games (date_time, duration, player_count, player_names)
                VALUES (?, ?, ?, ?)
            ''', (now, actual_duration, player_count, player_names))
            
            self.db_connection.commit()
            self.log(f"Game saved to database: {player_count} players, {actual_duration}s duration")
            
        except Exception as e:
            self.log(f"Database save error: {str(e)}", 'error')
        
    def log(self, message, level='info'):
        getattr(logging, level)(message)
        try:
            # Use Clock to ensure this runs in the main thread
            Clock.schedule_once(lambda dt: self.gui_callback(f"[SERVER] {message}"), 0)
        except Exception as e:
            logging.error(f"Error in log callback: {str(e)}")

    def start_server(self):
        try:
            if self.running:
                self.log("Server already running", 'warning')
                return

            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True
            self.connection_thread = threading.Thread(target=self.accept_connections, daemon=True)
            self.connection_thread.start()
            self.log(f"Server started on {self.host}:{self.port}")
            return True
        except Exception as e:
            self.log(f"Server start failed: {str(e)}", 'error')
            return False

    def accept_connections(self):
        self.server_socket.settimeout(1)
        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                client_id = f"{addr[0]}:{addr[1]}"
                with self.lock:
                    if len(self.game_state['active_players']) >= self.game_state['max_players']:
                        client_socket.send(json.dumps({
                            "type": "error",
                            "message": "Server full"
                        }).encode())
                        client_socket.close()
                        self.log(f"Rejected connection (max players reached): {client_id}", 'warning')
                        continue
                    
                    # Add to clients with temporary name
                self.clients[client_id] = (client_socket, addr)
                # Don't add display clients to player list yet
                temp_name = f"Player_{client_id[-4:]}"
                self.player_names[client_id] = temp_name
# Only add to active players after we know it's not a display
                
                self.log(f"New connection: {client_id}")
                # Notify UI to update player list
                Clock.schedule_once(lambda dt: self.gui_callback(f"PLAYER_JOINED:{temp_name}"), 0)
                
                threading.Thread(target=self.handle_client, args=(client_socket, client_id), daemon=True).start()
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    self.log(f"Connection error: {str(e)}", 'error')

    def handle_client(self, client_socket, client_id):
        try:
            while self.running:
                data = client_socket.recv(1024)
                if not data:
                    break
                
                try:
                    decrypted_data = decrypt_message(data)
                    message = json.loads(decrypted_data.decode('utf-8'))
                    self.process_message(message, client_id, client_socket)
                except json.JSONDecodeError:
                    self.log(f"Invalid message from {client_id}", 'warning')
        except Exception as e:
            self.log(f"Client error {client_id}: {str(e)}", 'warning')
        finally:
            self.disconnect_client(client_id)

    def process_message(self, message, client_id, client_socket):
        msg_type = message.get('type')
        if msg_type == 'register':
            # Existing code for handling 'register' messages
            player_name = message.get('player_name', f"Player_{client_id[-4:]}")
            with self.lock:
                if len(self.game_state['active_players']) >= self.game_state['max_players']:
                    response = {"type": "registration_failed", "reason": "server_full"}
                    self.send_encrypted_message(client_socket, response)

                    self.log(f"{player_name} tried to join but server is full", 'warning')
                else:
                    # Update player name
                    old_name = self.player_names.get(client_id, "")
                    if old_name in self.game_state['active_players']:
                        self.game_state['active_players'].remove(old_name)
                    
                    self.player_names[client_id] = player_name
                    self.game_state['active_players'].append(player_name)
                    
                    # ADD THIS - Initialize player game state
                    self.player_health[player_name] = self.max_health
                    self.player_scores[player_name] = 0
                    self.player_status[player_name] = 'alive'
                    
                    response = {"type": "welcome", "player_id": client_id}
                    client_socket.send(json.dumps(response).encode())
                    self.log(f"{player_name} joined the game (Health: {self.max_health})")
                    
                    # Notify UI to update player list
                    if old_name:
                        Clock.schedule_once(lambda dt: self.gui_callback(f"PLAYER_LEFT:{old_name}"), 0)
                    Clock.schedule_once(lambda dt: self.gui_callback(f"PLAYER_JOINED:{player_name}"), 0)
        
        elif msg_type == 'shoot':
            player_name = self.player_names.get(client_id, f"Player_{client_id[-4:]}")
            player_id = message.get('player_id', 'unknown')
            self.log(f"SHOOT: {player_name} (ID: {player_id}) fired their weapon!")

        # ADD THIS - New hit detection processing
        elif msg_type == 'hit_detected':
            victim_name = message.get('victim_name', 'Unknown')
            shooter_id = message.get('shooter_id', 0)
            
            # Find shooter name by ID
            shooter_name = self.find_player_by_id(shooter_id)
            
            if shooter_name:
                self.process_hit(shooter_name, victim_name)
            else:
                self.log(f"Hit detected but unknown shooter ID: {shooter_id}", 'warning')

    # ADD THIS - New method to find player by ID
    def find_player_by_id(self, player_id):
        """Find player name by their player ID"""
        # This assumes player IDs match the order they joined
        # You might need to adjust this based on your ID system
        try:
            player_list = list(self.game_state['active_players'])
            if 1 <= player_id <= len(player_list):
                return player_list[player_id - 1]
        except:
            pass
        return None

    # ADD THIS - Core hit processing logic
    def process_hit(self, shooter_name, victim_name):
        """Process a hit between two players"""
        with self.lock:
            # Validate both players exist and are alive
            if (victim_name not in self.player_status or 
                shooter_name not in self.player_status or
                self.player_status[victim_name] != 'alive' or
                self.player_status[shooter_name] != 'alive'):
                return
            
            # Process the hit
            old_health = self.player_health[victim_name]
            self.player_health[victim_name] -= 1
            new_health = self.player_health[victim_name]
            
            # Update shooter's score
            self.player_scores[shooter_name] += 10
            
            self.log(f"HIT! {shooter_name} shot {victim_name} (Health: {old_health} → {new_health})")
            
            # Check if player is eliminated
            if new_health <= 0:
                self.player_status[victim_name] = 'dead'
                self.log(f"ELIMINATED! {victim_name} has been eliminated by {shooter_name}!")
                
                # Broadcast elimination
                elimination_event = {
                    "type": "player_eliminated",
                    "victim": victim_name,
                    "shooter": shooter_name,
                    "shooter_score": self.player_scores[shooter_name]
                }
                self.broadcast_to_all_clients(elimination_event)
            else:
                # Broadcast hit event
                hit_event = {
                    "type": "player_hit",
                    "victim": victim_name,
                    "shooter": shooter_name,
                    "victim_health": new_health,
                    "shooter_score": self.player_scores[shooter_name]
                }
                self.broadcast_to_all_clients(hit_event)
            
            # Check win condition
            alive_players = [p for p, status in self.player_status.items() if status == 'alive']
            if len(alive_players) <= 1 and len(self.game_state['active_players']) > 1:
                winner = alive_players[0] if alive_players else "No one"
                self.log(f"GAME OVER! Winner: {winner}")
                
                # Broadcast game over
                game_over_event = {
                    "type": "game_over",
                    "winner": winner,
                    "final_scores": self.player_scores
                }
                self.broadcast_to_all_clients(game_over_event)
                
                # Stop the game
                self.stop_game()

    # ADD THIS - Broadcast messages to all connected clients
    def broadcast_to_all_clients(self, message):
        """Send a message to all connected clients"""
        for client_id, (client_socket, addr) in list(self.clients.items()):
            try:
                self.send_encrypted_message(client_socket, message)
            except Exception as e:
                self.log(f"Broadcast error to {client_id}: {str(e)}", 'warning')

    def start_game(self):
        with self.lock:
            if not self.game_state['is_running']:
                self.game_state['is_running'] = True
                self.game_state['is_paused'] = False
                self.game_state['remaining_time'] = self.game_state['game_duration']
                self.game_state['start_time'] = time.time()
                self.game_state['elapsed_before_pause'] = 0
                
                # ADD THIS - Reset all players for new game
                for player_name in self.game_state['active_players']:
                    self.player_health[player_name] = self.max_health
                    self.player_scores[player_name] = 0
                    self.player_status[player_name] = 'alive'
                
                self.log("Game started! All players reset to full health.")
                
                # Start timer in a separate thread
                if self.timer_thread is None or not self.timer_thread.is_alive():
                    self.timer_thread = threading.Thread(target=self._run_timer, daemon=True)
                    self.timer_thread.start()
                    
                game_event = {
                    "type": "game_event",
                    "event": "game_started",
                    "remaining_time": self.game_state['remaining_time'],
                    "is_running": True
                }
                self.broadcast_to_all_clients(game_event)
                return True
            return False

    def stop_game(self):
        with self.lock:
            was_running = self.game_state['is_running']
            self.game_state['is_running'] = False
            self.game_state['is_paused'] = False
            self.game_state['remaining_time'] = 0
            self.game_state['elapsed_before_pause'] = 0
            
            if was_running:
                self.log("Game stopped")
                self.save_game_to_database()
                
                stop_event = {
                    "type": "game_event",
                    "event": "game_stopped", 
                    "remaining_time": 0,
                    "is_running": False,
                    "final_scores": self.player_scores
                }
                self.broadcast_to_all_clients(stop_event)
                return True
            return False

    def pause_game(self):
        with self.lock:
            if not self.game_state['is_running']:
                return False
                
            if not self.game_state['is_paused']:
                # Pausing
                self.game_state['is_paused'] = True
                self.game_state['pause_time'] = time.time()
                # Calculate elapsed time before pause
                elapsed = int(time.time() - self.game_state['start_time'])
                self.game_state['elapsed_before_pause'] = elapsed
                self.log("Game paused")
                
                # Broadcast pause to displays
                pause_event = {
                    "type": "game_event", 
                    "event": "game_paused",
                    "remaining_time": self.game_state['remaining_time'],
                    "is_running": self.game_state['is_running'],
                    "is_paused": self.game_state['is_paused']
                }
                self.broadcast_to_all_clients(pause_event)
                
                return True
            else:
                # Resuming
                self.game_state['is_paused'] = False
                # Set a new start time that accounts for the paused duration
                current_time = time.time()
                self.game_state['start_time'] = current_time - self.game_state['elapsed_before_pause']
                self.log("Game resumed")
                
                # Broadcast resume to displays
                resume_event = {
                    "type": "game_event", 
                    "event": "game_resumed",
                    "remaining_time": self.game_state['remaining_time'],
                    "is_running": self.game_state['is_running'],
                    "is_paused": self.game_state['is_paused']
                }
                self.broadcast_to_all_clients(resume_event)
                
                return True

    def _run_timer(self):
        last_update = time.time()
        
        while self.game_state['is_running'] and self.game_state['remaining_time'] > 0:
            now = time.time()
            if now - last_update >= 1:
                last_update = now
                
                with self.lock:
                    if not self.game_state['is_paused']:
                        elapsed = int(now - self.game_state['start_time'])
                        self.game_state['remaining_time'] = max(0, self.game_state['game_duration'] - elapsed)

                        if self.game_state['remaining_time'] % 5 == 0:
                            timer_update = {
                                "type": "game_update", 
                                "remaining_time": self.game_state['remaining_time'],
                                "is_running": self.game_state['is_running']
                            }
                            self.broadcast_to_all_clients(timer_update)
            
            time.sleep(0.1)  # Small delay to prevent CPU hogging
        
        # Game ended
        with self.lock:
            if self.game_state['is_running']:
                self.game_state['is_running'] = False
                self.game_state['is_paused'] = False
                self.log("Game over - time's up!")

    def kick_player(self, player_name):
        """Kick a player from the server"""
        try:
            logging.info(f"GameServer attempting to kick player: {player_name}")
            with self.lock:
                if player_name in self.game_state['active_players']:
                    # Find the client ID
                    client_id_to_kick = None
                    for client_id, name in list(self.player_names.items()):
                        if name == player_name:
                            client_id_to_kick = client_id
                            break
                    
                    if client_id_to_kick and client_id_to_kick in self.clients:
                        try:
                            # We'll use our own method to log
                            self.log(f"Kicking player {player_name}")
                            self.disconnect_client(client_id_to_kick)
                            return True
                        except Exception as e:
                            self.log(f"Error disconnecting client: {str(e)}", 'error')
                            return False
                    else:
                        self.log(f"Player {player_name} not found in clients list", 'warning')
                        # Clean up anyway
                        if player_name in self.game_state['active_players']:
                            self.game_state['active_players'].remove(player_name)
                        return True
                else:
                    self.log(f"Player {player_name} not found in active players", 'warning')
                    return False
        except Exception as e:
            logging.error(f"Error in GameServer kick_player: {str(e)}")
            try:
                self.log(f"Error kicking player: {str(e)}", 'error')
            except:
                logging.error("Failed to log after kick error")
            return False

    def disconnect_client(self, client_id):
        try:
            with self.lock:
                if client_id in self.clients:
                    player_name = self.player_names.get(client_id)
                    
                    try:
                        client_socket, _ = self.clients[client_id]
                        client_socket.close()
                    except Exception as e:
                        self.log(f"Error closing client socket: {str(e)}", 'error')
                    
                    # Remove from active players list if present
                    if player_name and player_name in self.game_state['active_players']:
                        try:
                            self.game_state['active_players'].remove(player_name)
                        except Exception as e:
                            self.log(f"Error removing player from active list: {str(e)}", 'error')
                    
                    # ADD THIS - Clean up game state
                    if player_name:
                        self.player_health.pop(player_name, None)
                        self.player_scores.pop(player_name, None)
                        self.player_status.pop(player_name, None)
                    
                    # Remove from clients and player_names dictionaries
                    try:
                        del self.clients[client_id]
                    except Exception as e:
                        self.log(f"Error removing client: {str(e)}", 'error')
                        
                    try:
                        if client_id in self.player_names:
                            del self.player_names[client_id]
                    except Exception as e:
                        self.log(f"Error removing player name: {str(e)}", 'error')
                    
                    if player_name:
                        self.log(f"Client disconnected: {player_name}")
                        # Notify UI through Clock to ensure it runs on the main thread
                        Clock.schedule_once(lambda dt: self.gui_callback(f"PLAYER_LEFT:{player_name}"), 0)
        except Exception as e:
            self.log(f"Disconnect client error: {str(e)}", 'error')

    def shutdown(self):
        if self.running:
            self.running = False
            if self.game_state['is_running']:
                self.stop_game()
                
            # Close all client connections
            with self.lock:
                for client_id, (sock, _) in list(self.clients.items()):
                    try:
                        sock.close()
                    except:
                        pass
                self.clients.clear()
                self.player_names.clear()
                
            # Close server socket
            if self.server_socket:
                try:
                    self.server_socket.close()
                except:
                    pass
            self.log("Server shutdown complete")
            return True
        return False

    def get_active_players(self):
        """Return a list of currently active players"""
        with self.lock:
            return list(self.game_state['active_players'])
        

    def send_encrypted_message(self, client_socket, message):
        """Send encrypted message to client"""
        try:
            json_str = json.dumps(message)
            encrypted_data = encrypt_message(json_str)
            client_socket.send(encrypted_data)
            return True
        except Exception as e:
            self.log(f"Send error: {e}", 'error')
            return False

# -------------------- GUI Implementation (Same as before) --------------------
class ServerGUI(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.padding = 20
        self.spacing = 15
        Window.clearcolor = (0.12, 0.12, 0.14, 1)
        
        # UI Components
        self.add_widget(Label(text="LASER TAG SERVER", font_size=24, bold=True, color=(0.9, 0.9, 0.9, 1)))
        self.setup_server_controls()
        self.setup_game_controls()
        self.setup_player_list()
        self.setup_console()
        
        # Initialize server - MOVED AFTER UI SETUP!
        self.server = GameServer(self.handle_server_message)
        
        # Timer updates
        Clock.schedule_interval(self.update_timer_display, 0.5)

    def handle_server_message(self, message):
        """Process messages from the server thread"""
        try:
            if message.startswith("PLAYER_JOINED:"):
                player_name = message.split(":", 1)[1]
                # Use Clock to ensure UI operations happen on the main thread
                Clock.schedule_once(lambda dt: self.add_player_to_list(player_name), 0)
                self.update_status(f"Player {player_name} joined")
            elif message.startswith("PLAYER_LEFT:"):
                player_name = message.split(":", 1)[1]
                # Use Clock to ensure UI operations happen on the main thread
                Clock.schedule_once(lambda dt: self.remove_player_from_list(player_name), 0)
                self.update_status(f"Player {player_name} left")
            else:
                self.update_status(message)
        except Exception as e:
            logging.error(f"Error handling server message: {str(e)}")

    def setup_server_controls(self):
        controls = BoxLayout(size_hint_y=None, height=50)
        self.start_btn = ModernRoundedButton(
            text="START SERVER", 
            background_color=(0, 0.8, 0, 1)
        )
        self.start_btn.bind(on_press=self.start_server)
        
        self.stop_btn = ModernRoundedButton(
            text="STOP SERVER", 
            background_color=(0.9, 0, 0, 1),
            disabled=True
        )
        self.stop_btn.bind(on_press=self.stop_server)
        
        controls.add_widget(self.start_btn)
        controls.add_widget(self.stop_btn)
        self.add_widget(controls)

    def start_server(self, instance):
        if not self.server.running:
            success = self.server.start_server()
            if success:
                self.start_btn.disabled = True
                self.stop_btn.disabled = False
                self.update_status("Server started successfully")
                self.enable_game_controls(True)

    def stop_server(self, instance):
        if self.server.running:
            success = self.server.shutdown()
            if success:
                self.start_btn.disabled = False
                self.stop_btn.disabled = True
                self.update_status("Server stopped")
                self.enable_game_controls(False)
                # Clear player list
                self.player_list_container.clear_widgets()

    def enable_game_controls(self, enabled):
        """Enable or disable game controls"""
        self.game_start_btn.disabled = not enabled
        self.pause_btn.disabled = not enabled or not self.server.game_state['is_running']
        self.game_stop_btn.disabled = not enabled or not self.server.game_state['is_running']

    def setup_game_controls(self):
        # Game configuration
        config_grid = GridLayout(cols=2, spacing=10, size_hint_y=None, height=80)
        
        # Max Players
        config_grid.add_widget(Label(text="Max Players:", color=(0.9, 0.9, 0.9, 1)))
        self.max_players = Spinner(
            text="4", 
            values=["2", "4", "6", "8"],
            background_color=(0.25, 0.25, 0.3, 1)
        )
        self.max_players.bind(text=self.update_max_players)
        config_grid.add_widget(self.max_players)

        # Game Duration
        config_grid.add_widget(Label(text="Game Time (s):", color=(0.9, 0.9, 0.9, 1)))
        self.game_duration = TextInput(
            text="300",
            input_filter='int',
            background_color=(0.25, 0.25, 0.3, 1)
        )
        self.game_duration.bind(text=self.update_game_duration)
        config_grid.add_widget(self.game_duration)

        self.add_widget(config_grid)

        # Game controls
        game_btns = GridLayout(cols=3, spacing=10, size_hint_y=None, height=50)
        
        self.game_start_btn = ModernRoundedButton(
            text="START GAME", 
            background_color=(0, 0.8, 0, 1),
            disabled=True
        )
        self.game_start_btn.bind(on_press=self.start_game)
        
        self.pause_btn = ModernRoundedButton(
            text="PAUSE", 
            background_color=(0.9, 0.6, 0, 1),
            disabled=True
        )
        self.pause_btn.bind(on_press=self.toggle_pause)
        
        self.game_stop_btn = ModernRoundedButton(
            text="STOP GAME", 
            background_color=(0.9, 0, 0, 1),
            disabled=True
        )
        self.game_stop_btn.bind(on_press=self.stop_game)
        
        game_btns.add_widget(self.game_start_btn)
        game_btns.add_widget(self.pause_btn)
        game_btns.add_widget(self.game_stop_btn)
        self.add_widget(game_btns)

        # Timer display
        timer_box = BoxLayout(size_hint_y=None, height=50)
        timer_box.add_widget(Label(text="TIME LEFT:", color=(0.9, 0.9, 0.9, 1)))
        self.timer_text = Label(
            text="00:00", 
            font_size=24, 
            color=(0.2, 0.8, 0.2, 1),
            size_hint_x=0.7
        )
        timer_box.add_widget(self.timer_text)
        self.add_widget(timer_box)
        
    def setup_player_list(self):
        # Player list section
        player_section = BoxLayout(orientation='vertical', size_hint_y=0.3)
        player_section.add_widget(Label(text="CONNECTED PLAYERS", font_size=18, bold=True))
        
        # Scrollable container for player list
        player_scroll = ScrollView()
        self.player_list_container = GridLayout(cols=1, spacing=2, size_hint_y=None)
        self.player_list_container.bind(minimum_height=self.player_list_container.setter('height'))
        player_scroll.add_widget(self.player_list_container)
        player_section.add_widget(player_scroll)
        
        self.add_widget(player_section)

    def setup_console(self):
        console_box = BoxLayout(orientation='vertical', size_hint_y=0.3)
        console_box.add_widget(Label(text="SERVER CONSOLE", font_size=18, bold=True))
        
        self.console = ScrollView()
        self.console_text = TextInput(
            readonly=True,
            background_color=(0.05, 0.05, 0.1, 1),
            foreground_color=(0, 0.9, 0, 1),
            size_hint_y=None,
            height=200,  # Set a fixed initial height
            multiline=True,
            font_size=14
        )
        self.console_text.bind(minimum_height=self.console_text.setter('height'))
        self.console.add_widget(self.console_text)
        console_box.add_widget(self.console)
        
        self.add_widget(console_box)

    def add_player_to_list(self, player_name):
        """Add a player to the UI list"""
        try:
            player_item = BoxLayout(size_hint_y=None, height=30)
            
            # Player name
            player_item.add_widget(Label(text=player_name, color=(0.9, 0.9, 0.9, 1), size_hint_x=0.7))
            
            # Kick button
            kick_btn = Button(
                text="Kick", 
                size_hint_x=0.3,
                background_color=(0.8, 0.3, 0.1, 1)
            )
            kick_btn.player_name = player_name  # Store player name as a property
            kick_btn.bind(on_release=self.kick_button_pressed)
            player_item.add_widget(kick_btn)
            
            self.player_list_container.add_widget(player_item)
            logging.info(f"Added player {player_name} to UI list")
        except Exception as e:
            logging.error(f"Error adding player to list: {str(e)}")

    def remove_player_from_list(self, player_name):
        try:
            children_to_remove = []
            for child in list(self.player_list_container.children):
                try:
                    if isinstance(child, BoxLayout):
                        for widget in child.children:
                            if isinstance(widget, Label) and widget.text == player_name:
                                children_to_remove.append(child)
                                break
                except Exception as e:
                    logging.error(f"Error checking player widget: {str(e)}")
            
            for child in children_to_remove:
                try:
                    self.player_list_container.remove_widget(child)
                except Exception as e:
                    logging.error(f"Error removing player widget: {str(e)}")
        except Exception as e:
            logging.error(f"Error in remove_player_from_list: {str(e)}")

    def kick_player(self, player_name):
        """Kick a player when kick button is clicked"""
        if self.server.kick_player(player_name):
            self.update_status(f"Player {player_name} has been kicked")
        else:
            self.update_status(f"Failed to kick player {player_name}")

    def kick_button_pressed(self, instance):
        """Handle kick button press with safe access to player name"""
        try:
            player_name = getattr(instance, 'player_name', None)
            if player_name:
                logging.info(f"Kick button pressed for player: {player_name}")
                # Create a delay to ensure UI remains responsive
                Clock.schedule_once(lambda dt: self.kick_player(player_name), 0.1)
        except Exception as e:
            logging.error(f"Error in kick button handler: {str(e)}")
            self.update_status(f"Error in kick button: {str(e)}")

    def update_max_players(self, instance, value):
        try:
            max_players = int(value)
            self.server.game_state['max_players'] = max_players
            self.update_status(f"Max players set to {max_players}")
        except ValueError:
            self.update_status("Invalid max players value", 'warning')

    def update_game_duration(self, instance, value):
        try:
            if value.strip():
                duration = int(value)
                self.server.game_state['game_duration'] = duration
                if not self.server.game_state['is_running']:
                    self.server.game_state['remaining_time'] = duration
                self.update_status(f"Game duration set to {duration}s")
        except ValueError:
            self.update_status("Invalid game duration", 'warning')

    def start_game(self, instance):
        """Start the game"""
        if self.server.start_game():
            self.pause_btn.disabled = False
            self.game_stop_btn.disabled = False
            self.update_status("Game started")

    def toggle_pause(self, instance):
        """Toggle game pause state"""
        if self.server.pause_game():
            if self.server.game_state['is_paused']:
                self.pause_btn.text = "RESUME"
                self.pause_btn.background_color = (0, 0.7, 0.3, 1)
            else:
                self.pause_btn.text = "PAUSE"
                self.pause_btn.background_color = (0.9, 0.6, 0, 1)

    def stop_game(self, instance):
        """Stop the game"""
        if self.server.stop_game():
            self.pause_btn.text = "PAUSE"
            self.pause_btn.background_color = (0.9, 0.6, 0, 1)
            self.pause_btn.disabled = True
            self.game_stop_btn.disabled = True
            self.update_status("Game stopped")

    def update_timer_display(self, dt):
        """Update the timer display"""
        try:
            minutes = self.server.game_state['remaining_time'] // 60
            seconds = self.server.game_state['remaining_time'] % 60
            self.timer_text.text = f"{minutes:02d}:{seconds:02d}"
            
            # Update timer color based on remaining time
            if self.server.game_state['remaining_time'] <= 30:
                self.timer_text.color = (0.9, 0.2, 0.2, 1)
            elif self.server.game_state['remaining_time'] <= 60:
                self.timer_text.color = (0.9, 0.7, 0.2, 1)
            else:
                self.timer_text.color = (0.2, 0.8, 0.2, 1)
                
            # Add blinking effect when paused
            if self.server.game_state['is_paused']:
                if int(time.time()) % 2 == 0:  # Blink every second
                    self.timer_text.opacity = 0.5
                else:
                    self.timer_text.opacity = 1.0
            else:
                self.timer_text.opacity = 1.0
                
            # Update game control buttons based on game state
            if not self.server.running:
                self.game_start_btn.disabled = True
                self.pause_btn.disabled = True
                self.game_stop_btn.disabled = True
            else:
                self.game_start_btn.disabled = self.server.game_state['is_running']
                self.pause_btn.disabled = not self.server.game_state['is_running']
                self.game_stop_btn.disabled = not self.server.game_state['is_running']
        except Exception as e:
            logging.error(f"Error updating timer: {str(e)}")

    def update_status(self, message, level='info'):
        """Update the console with a new status message"""
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Format the message with timestamp and level
            level_prefix = ""
            if level == 'warning':
                level_prefix = "[WARNING] "
            elif level == 'error':
                level_prefix = "[ERROR] "
                
            # Add the message to the console
            formatted_msg = f"[{timestamp}] {level_prefix}{message}\n"
            self.console_text.text += formatted_msg
            
            # Auto-scroll to the bottom
            self.console_text.cursor = (len(self.console_text.text), 0)
        except Exception as e:
            logging.error(f"Error updating console: {str(e)}")

# -------------------- Main App Class --------------------
class LaserTagServerApp(App):
    def build(self):
        return ServerGUI()

# -------------------- Run the Application --------------------
if __name__ == "__main__":
    try:
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        LaserTagServerApp().run()
    except Exception as e:
        logging.error(f"Application error: {str(e)}")