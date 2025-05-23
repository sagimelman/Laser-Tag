# Simple Display Client for Laser Tag
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.core.window import Window
from kivy.clock import Clock
from datetime import datetime
import socket
import threading
import json
import time

# Import encryption
from encryptions import encrypt_message, decrypt_message

# Configuration
SERVER_IP = "127.0.0.1"  # localhost (same computer)
SERVER_PORT = 9999

class DisplayClient(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.padding = 20
        self.spacing = 15
        
        # Dark theme
        Window.clearcolor = (0.1, 0.1, 0.15, 1)
        
        # Connection
        self.connected = False
        self.sock = None
        
        # Game state
        self.game_time = 300
        self.game_running = False
        self.game_paused = False
        self.players = []
        
        self.setup_ui()
        self.connect_to_server()
        
        # Update display every second
        Clock.schedule_interval(self.update_display, 1)

    def setup_ui(self):
        # Title
        title = Label(
            text="🎯 LASER TAG DISPLAY",
            font_size=32,
            bold=True,
            color=(1, 1, 1, 1),
            size_hint_y=None,
            height=60
        )
        self.add_widget(title)
        
        # Game timer
        timer_section = BoxLayout(orientation='vertical', size_hint_y=None, height=100)
        timer_section.add_widget(Label(
            text="TIME REMAINING",
            font_size=18,
            color=(0.8, 0.8, 0.8, 1),
            size_hint_y=0.3
        ))
        
        self.timer_label = Label(
            text="05:00",
            font_size=48,
            bold=True,
            color=(0.2, 1, 0.2, 1),
            size_hint_y=0.7
        )
        timer_section.add_widget(self.timer_label)
        self.add_widget(timer_section)
        
        # Game status
        self.status_label = Label(
            text="🔴 Game Not Started",
            font_size=24,
            bold=True,
            color=(1, 0.3, 0.3, 1),
            size_hint_y=None,
            height=40
        )
        self.add_widget(self.status_label)
        
        # Players list
        self.add_widget(Label(
            text="👥 CONNECTED PLAYERS",
            font_size=18,
            bold=True,
            color=(0.2, 0.8, 1, 1),
            size_hint_y=None,
            height=30
        ))
        
        self.players_label = Label(
            text="No players connected",
            font_size=16,
            color=(0.9, 0.9, 0.9, 1),
            size_hint_y=None,
            height=60
        )
        self.add_widget(self.players_label)
        
        # Live feed
        self.add_widget(Label(
            text="📡 LIVE FEED",
            font_size=16,
            bold=True,
            color=(0.2, 0.8, 1, 1),
            size_hint_y=None,
            height=30
        ))
        
        feed_scroll = ScrollView()
        self.feed_text = TextInput(
            readonly=True,
            background_color=(0.05, 0.05, 0.1, 1),
            foreground_color=(0.2, 1, 0.2, 1),
            multiline=True,
            font_size=12
        )
        feed_scroll.add_widget(self.feed_text)
        self.add_widget(feed_scroll)
        
        # Connection status
        self.connection_label = Label(
            text="🔴 Connecting...",
            font_size=14,
            color=(1, 0.5, 0.5, 1),
            size_hint_y=None,
            height=30
        )
        self.add_widget(self.connection_label)

    def add_to_feed(self, message):
        """Add message to live feed"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.feed_text.text += f"[{timestamp}] {message}\n"
        # Auto scroll to bottom
        self.feed_text.cursor = (len(self.feed_text.text), 0)

    def send_encrypted_message(self, message):
        """Send encrypted message to server"""
        try:
            json_str = json.dumps(message)
            encrypted_data = encrypt_message(json_str)
            self.sock.send(encrypted_data)
            return True
        except Exception as e:
            self.add_to_feed(f"❌ Send error: {e}")
            return False

    def connect_to_server(self):
        """Connect to server"""
        def connect():
            try:
                self.sock = socket.socket()
                self.sock.connect((SERVER_IP, SERVER_PORT))
                
                # Register as display
                registration = {
                    "type": "register_display",
                    "client_type": "display"
                }
                
                if self.send_encrypted_message(registration):
                    self.connected = True
                    Clock.schedule_once(lambda dt: self.update_connection_status(True), 0)
                    Clock.schedule_once(lambda dt: self.add_to_feed("✅ Connected to server"), 0)
                    
                    # Start listening
                    threading.Thread(target=self.listen_for_messages, daemon=True).start()
                else:
                    raise Exception("Failed to register")
                    
            except Exception as e:
                Clock.schedule_once(lambda dt: self.update_connection_status(False, str(e)), 0)
                Clock.schedule_once(lambda dt: self.add_to_feed(f"❌ Connection failed: {e}"), 0)
                # Retry in 5 seconds
                Clock.schedule_once(lambda dt: threading.Thread(target=connect, daemon=True).start(), 5)
        
        threading.Thread(target=connect, daemon=True).start()

    def update_connection_status(self, connected, error=None):
        """Update connection status in UI"""
        if connected:
            self.connection_label.text = "🟢 Connected (Encrypted)"
            self.connection_label.color = (0.3, 1, 0.3, 1)
        else:
            self.connection_label.text = f"🔴 {error or 'Disconnected'}"
            self.connection_label.color = (1, 0.3, 0.3, 1)

    def listen_for_messages(self):
        """Listen for encrypted messages from server"""
        while self.connected:
            try:
                data = self.sock.recv(1024)
                if not data:
                    break
                
                # Decrypt message
                decrypted_data = decrypt_message(data)
                message = json.loads(decrypted_data.decode('utf-8'))
                
                # Process on main thread
                Clock.schedule_once(lambda dt: self.process_message(message), 0)
                
            except Exception as e:
                Clock.schedule_once(lambda dt: self.add_to_feed(f"⚠️ Message error: {e}"), 0)
                if "too old" in str(e):
                    # Clock sync issue, continue listening
                    continue
                else:
                    # Connection lost
                    break
        
        self.connected = False
        Clock.schedule_once(lambda dt: self.update_connection_status(False, "Connection lost"), 0)

    def process_message(self, message):
        """Process received message"""
        msg_type = message.get('type', 'unknown')
        
        if msg_type == 'game_update':
            self.game_time = message.get('remaining_time', 300)
            self.game_running = message.get('is_running', False)
            self.add_to_feed(f"🎮 Timer: {self.game_time}s")
            
        elif msg_type == 'game_event':
            event_type = message.get('event', '')
            
            if event_type in ['game_started', 'game_paused', 'game_resumed', 'game_stopped']:
                # Update game state from server
                self.game_time = message.get('remaining_time', 300)
                self.game_running = message.get('is_running', False)
                self.game_paused = message.get('is_paused', False)  # ADD THIS LINE
                
                if event_type == 'game_started':
                    self.add_to_feed("🎮 Game started!")
                elif event_type == 'game_paused':
                    self.add_to_feed("⏸️ Game paused")
                elif event_type == 'game_resumed':
                    self.add_to_feed("▶️ Game resumed")
                elif event_type == 'game_stopped':
                    self.add_to_feed("🛑 Game stopped")
                    self.game_time = 300  # Reset timer display
            else:
                # Regular game events
                event_text = message.get('message', 'Unknown event')
                self.add_to_feed(f"📢 {event_text}")
            
        elif msg_type == 'player_joined':
            player_name = message.get('player_name', 'Unknown')
            self.players.append(player_name)
            self.add_to_feed(f"🟢 {player_name} joined")
            
        elif msg_type == 'player_left':
            player_name = message.get('player_name', 'Unknown')
            if player_name in self.players:
                self.players.remove(player_name)
            self.add_to_feed(f"🔴 {player_name} left")
            
        else:
            self.add_to_feed(f"❓ Unknown message: {msg_type}")

    def update_display(self, dt):
        """Update display every second"""
        if self.game_running and not self.game_paused and self.game_time > 0:
            self.game_time -= 1
            
        # Format timer
        minutes = self.game_time // 60
        seconds = self.game_time % 60
        self.timer_label.text = f"{minutes:02d}:{seconds:02d}"
        
        # Timer color
        if self.game_time <= 30:
            self.timer_label.color = (1, 0.2, 0.2, 1)  # Red
        elif self.game_time <= 60:
            self.timer_label.color = (1, 0.8, 0.2, 1)  # Orange
        else:
            self.timer_label.color = (0.2, 1, 0.2, 1)  # Green
        
        # Game status
        if self.game_running:
            self.status_label.text = "🟢 Game In Progress"
            self.status_label.color = (0.3, 1, 0.3, 1)
        else:
            self.status_label.text = "🔴 Game Not Started"
            self.status_label.color = (1, 0.3, 0.3, 1)
        
        # Players list
        if self.players:
            players_text = '\n'.join([f"• {player}" for player in self.players])
            self.players_label.text = players_text
        else:
            self.players_label.text = "No players connected"

class DisplayApp(App):
    def build(self):
        return DisplayClient()

if __name__ == "__main__":
    DisplayApp().run()