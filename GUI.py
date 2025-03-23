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
from kivy.properties import ListProperty
from kivy.clock import Clock
from datetime import datetime
import logging

# Set up logging
class GuiLogHandler(logging.Handler):
    """Custom log handler that forwards log messages to the GUI."""
    def __init__(self, callback):
        super().__init__()
        self.callback = callback
        
    def emit(self, record):
        log_message = self.format(record)
        # Schedule on main thread to avoid threading issues
        Clock.schedule_once(lambda dt: self.callback(log_message), 0)

# Configure basic logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger()

# Set window size and background color
Window.size = (500, 700)  # Increased height for banned players list
Window.clearcolor = (0.12, 0.12, 0.14, 1)  # Dark mode background

class ModernRoundedButton(Button):
    """Enhanced button with modern styling and high visibility."""
    border_radius = ListProperty([12])  # Slightly less rounded for modern look

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''  # Remove default background
        self.background_color = (0, 0, 0, 0)  # Transparent background
        self.font_size = 16  # Larger font size
        self.bold = True  # Bold text for visibility
        self.height = 40  # Reduced height from 50 to 40 for smaller buttons
        self.bind(pos=self.update_canvas, size=self.update_canvas)
        
    def update_canvas(self, *args):
        """Update the canvas to draw rounded corners with shadow effect."""
        self.canvas.before.clear()
        with self.canvas.before:
            # Button shadow (subtle)
            Color(0, 0, 0, 0.2)
            RoundedRectangle(pos=(self.pos[0] + 2, self.pos[1] - 2), 
                             size=self.size, radius=self.border_radius)
            # Button color
            Color(*self.background_color)
            RoundedRectangle(pos=self.pos, size=self.size, radius=self.border_radius)

class ConfiguratorGUI(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.padding = 20
        self.spacing = 15  # Increased spacing for better look

        # Game state
        self.game_running = False
        self.game_paused = False  # New game paused state
        self.remaining_time = 0
        self.active_players = []
        self.banned_players = []
        self.timer_event = None

        # Set up logging to GUI
        self.gui_handler = GuiLogHandler(self.update_status)
        self.gui_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        logger.addHandler(self.gui_handler)

        # Title and header
        header = Label(
            text="LASER TAG CONFIGURATOR", 
            font_size=24, 
            bold=True, 
            color=(0.9, 0.9, 0.9, 1),
            size_hint_y=None,
            height=50
        )
        self.add_widget(header)

        # Game Settings
        settings_header = Label(
            text="Game Settings", 
            font_size=20, 
            bold=True, 
            color=(0.9, 0.9, 0.9, 1),
            size_hint_y=None,
            height=40
        )
        self.add_widget(settings_header)

        # Settings container with background
        settings_container = BoxLayout(orientation='vertical', size_hint_y=None, height=200)
        with settings_container.canvas.before:
            Color(0.18, 0.18, 0.2, 1)  # Slightly lighter than background
            RoundedRectangle(pos=settings_container.pos, size=settings_container.size, radius=[10])
        settings_container.bind(pos=self._update_settings_bg, size=self._update_settings_bg)

        settings_layout = GridLayout(cols=2, spacing=10, padding=15, size_hint_y=None, height=180)
        settings_layout.bind(minimum_height=settings_layout.setter('height'))

        # Player Count
        settings_layout.add_widget(Label(text="Player Count:", font_size=16, color=(0.9, 0.9, 0.9, 1)))
        self.player_count = Spinner(
            text="2", 
            values=["2", "3", "4", "5"], 
            font_size=16, 
            size_hint_y=None, 
            height=40,
            background_normal='',
            background_color=(0.25, 0.25, 0.3, 1)
        )
        self.player_count.bind(text=self.update_player_management)
        settings_layout.add_widget(self.player_count)

        # Game Duration
        settings_layout.add_widget(Label(text="Game Duration (s):", font_size=16, color=(0.9, 0.9, 0.9, 1)))
        self.game_duration = TextInput(
            text="300", 
            font_size=16, 
            multiline=False, 
            size_hint_y=None, 
            height=40,
            background_color=(0.25, 0.25, 0.3, 1),
            foreground_color=(0.9, 0.9, 0.9, 1),
            cursor_color=(0.9, 0.9, 0.9, 1)
        )
        settings_layout.add_widget(self.game_duration)

        # Lives per Player
        settings_layout.add_widget(Label(text="Lives per Player:", font_size=16, color=(0.9, 0.9, 0.9, 1)))
        self.lives_per_player = TextInput(
            text="3", 
            font_size=16, 
            multiline=False, 
            size_hint_y=None, 
            height=40,
            background_color=(0.25, 0.25, 0.3, 1),
            foreground_color=(0.9, 0.9, 0.9, 1),
            cursor_color=(0.9, 0.9, 0.9, 1)
        )
        settings_layout.add_widget(self.lives_per_player)

        # Score to Win
        settings_layout.add_widget(Label(text="Score to Win:", font_size=16, color=(0.9, 0.9, 0.9, 1)))
        self.score_to_win = TextInput(
            text="10", 
            font_size=16, 
            multiline=False, 
            size_hint_y=None, 
            height=40,
            background_color=(0.25, 0.25, 0.3, 1),
            foreground_color=(0.9, 0.9, 0.9, 1),
            cursor_color=(0.9, 0.9, 0.9, 1)
        )
        settings_layout.add_widget(self.score_to_win)

        settings_container.add_widget(settings_layout)
        self.add_widget(settings_container)

        # Timer Display
        timer_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        
        timer_label = Label(
            text="Time Remaining:", 
            font_size=18, 
            bold=True, 
            color=(0.9, 0.9, 0.9, 1),
            size_hint_x=0.4
        )
        timer_layout.add_widget(timer_label)
        
        self.timer_display = Label(
            text="00:00", 
            font_size=20, 
            bold=True, 
            color=(0.2, 0.8, 0.2, 1),  # Bright green
            size_hint_x=0.6
        )
        timer_layout.add_widget(self.timer_display)
        
        self.add_widget(timer_layout)

        # Buttons - ENHANCED with bright colors as requested and now with three buttons
        buttons_layout = BoxLayout(spacing=10, size_hint_y=None, height=50, padding=[0, 5, 0, 5])
        
        # Start button - BRIGHT GREEN
        self.start_button = ModernRoundedButton(
            text="START GAME", 
            background_color=(0.0, 0.8, 0.0, 1),  # Bright green
            color=(1, 1, 1, 1)  # White text
        )
        self.start_button.bind(on_press=self.start_game)
        buttons_layout.add_widget(self.start_button)

        # Freeze button - BRIGHT BLUE - New button
        self.freeze_button = ModernRoundedButton(
            text="FREEZE GAME", 
            background_color=(0.0, 0.5, 0.9, 1),  # Bright blue
            color=(1, 1, 1, 1),  # White text
            disabled=True
        )
        self.freeze_button.bind(on_press=self.freeze_game)
        buttons_layout.add_widget(self.freeze_button)

        # Stop button - BRIGHT RED
        self.stop_button = ModernRoundedButton(
            text="STOP GAME", 
            background_color=(0.9, 0.0, 0.0, 1),  # Bright red
            color=(1, 1, 1, 1),  # White text
            disabled=True
        )
        self.stop_button.bind(on_press=self.stop_game)
        buttons_layout.add_widget(self.stop_button)

        self.add_widget(buttons_layout)

        # Player Management
        player_header = Label(
            text="Player Management", 
            font_size=20, 
            bold=True, 
            color=(0.9, 0.9, 0.9, 1),
            size_hint_y=None,
            height=40
        )
        self.add_widget(player_header)

        # Player management container with background
        player_container = BoxLayout(orientation='vertical', size_hint_y=None, height=150)
        with player_container.canvas.before:
            Color(0.18, 0.18, 0.2, 1)  # Slightly lighter than background
            RoundedRectangle(pos=player_container.pos, size=player_container.size, radius=[10])
        player_container.bind(pos=self._update_player_bg, size=self._update_player_bg)

        # Active players label
        self.active_players_label = Label(
            text="Active Players: None", 
            font_size=16, 
            color=(0.2, 0.8, 0.2, 1),  # Green
            size_hint_y=None,
            height=30,
            halign="left",
            padding=(10, 0)
        )
        self.active_players_label.bind(width=lambda *x: self.active_players_label.setter('text_size')(self.active_players_label, (self.active_players_label.width, None)))
        player_container.add_widget(self.active_players_label)

        player_management_layout = GridLayout(cols=2, spacing=10, padding=15, size_hint_y=None, height=100)
        player_management_layout.bind(minimum_height=player_management_layout.setter('height'))

        # Disconnect Player
        player_management_layout.add_widget(Label(text="Disconnect Player:", font_size=16, color=(0.9, 0.9, 0.9, 1)))
        self.disconnect_player = Spinner(
            text="Player 1", 
            values=["Player 1", "Player 2"], 
            font_size=16, 
            size_hint_y=None, 
            height=40,
            background_normal='',
            background_color=(0.25, 0.25, 0.3, 1)
        )
        self.disconnect_player.bind(on_press=self.check_player_lists)  # Update dropdown on press
        player_management_layout.add_widget(self.disconnect_player)

        # Ban Player
        player_management_layout.add_widget(Label(text="Ban Player:", font_size=16, color=(0.9, 0.9, 0.9, 1)))
        self.ban_player = Spinner(
            text="Player 1", 
            values=["Player 1", "Player 2"], 
            font_size=16, 
            size_hint_y=None, 
            height=40,
            background_normal='',
            background_color=(0.25, 0.25, 0.3, 1)
        )
        self.ban_player.bind(on_press=self.check_player_lists)  # Update dropdown on press
        player_management_layout.add_widget(self.ban_player)

        player_container.add_widget(player_management_layout)
        
        # Action buttons for disconnect and ban
        actions_layout = BoxLayout(spacing=10, padding=[15, 0, 15, 15], size_hint_y=None, height=50)
        
        # Disconnect button
        disconnect_button = Button(
            text="Disconnect", 
            background_normal='',
            background_color=(0.7, 0.3, 0.0, 1),  # Orange
            color=(1, 1, 1, 1)
        )
        disconnect_button.bind(on_press=self.disconnect_selected_player)
        actions_layout.add_widget(disconnect_button)
        
        # Ban button
        ban_button = Button(
            text="Ban", 
            background_normal='',
            background_color=(0.7, 0.0, 0.0, 1),  # Darker red
            color=(1, 1, 1, 1)
        )
        ban_button.bind(on_press=self.ban_selected_player)
        actions_layout.add_widget(ban_button)
        
        player_container.add_widget(actions_layout)
        self.add_widget(player_container)
        
        # Banned Players List
        banned_header = Label(
            text="Banned Players", 
            font_size=20, 
            bold=True, 
            color=(0.9, 0.9, 0.9, 1),
            size_hint_y=None,
            height=40
        )
        self.add_widget(banned_header)
        
        # Banned players container
        banned_container = BoxLayout(orientation='vertical', size_hint_y=None, height=100)
        with banned_container.canvas.before:
            Color(0.18, 0.18, 0.2, 1)
            RoundedRectangle(pos=banned_container.pos, size=banned_container.size, radius=[10])
        banned_container.bind(pos=self._update_banned_bg, size=self._update_banned_bg)
        
        # Scrollable view for banned players
        banned_scroll = ScrollView(size_hint=(1, None), size=(1, 80))
        self.banned_list = TextInput(
            text="No banned players", 
            font_size=14, 
            foreground_color=(0.9, 0.2, 0.2, 1),  # Red text
            background_color=(0.15, 0.15, 0.17, 1),
            readonly=True,
            size_hint_y=None,
            height=80
        )
        banned_scroll.add_widget(self.banned_list)
        banned_container.add_widget(banned_scroll)
        
        # Unban action
        unban_layout = BoxLayout(spacing=10, padding=[15, 5, 15, 15], size_hint_y=None, height=40)
        
        # Unban dropdown
        self.unban_player = Spinner(
            text="Select player to unban", 
            values=["No banned players"], 
            font_size=14,
            size_hint_x=0.7,
            background_normal='',
            background_color=(0.25, 0.25, 0.3, 1)
        )
        unban_layout.add_widget(self.unban_player)
        
        # Unban button
        unban_button = Button(
            text="Unban", 
            size_hint_x=0.3,
            background_normal='',
            background_color=(0.2, 0.5, 0.2, 1),  # Green
            color=(1, 1, 1, 1)
        )
        unban_button.bind(on_press=self.unban_selected_player)
        unban_layout.add_widget(unban_button)
        
        banned_container.add_widget(unban_layout)
        self.add_widget(banned_container)

        # Console Log (Status Display)
        console_header = Label(
            text="Console Log", 
            font_size=20, 
            bold=True, 
            color=(0.9, 0.9, 0.9, 1),
            size_hint_y=None,
            height=40
        )
        self.add_widget(console_header)

        # Console container with background
        console_container = BoxLayout(orientation='vertical', size_hint_y=1)
        with console_container.canvas.before:
            Color(0.05, 0.05, 0.1, 1)  # Very dark background for console
            RoundedRectangle(pos=console_container.pos, size=console_container.size, radius=[10])
        console_container.bind(pos=self._update_console_bg, size=self._update_console_bg)

        self.status_display = ScrollView(size_hint=(1, 1))
        self.status_text = TextInput(
            text="=== Console Output ===\n", 
            font_size=14, 
            foreground_color=(0.0, 0.9, 0.0, 1),  # Green text like a terminal
            background_color=(0.05, 0.05, 0.1, 1),  # Very dark background
            readonly=True,  # Make it read-only
            size_hint_y=None,
            height=1000  # Set a large height to make it scrollable
        )
        self.status_text.bind(minimum_height=self.status_text.setter('height'))
        self.status_display.add_widget(self.status_text)
        
        console_container.add_widget(self.status_display)
        self.add_widget(console_container)

        # Log application startup
        logging.info("Laser Tag Configurator started")

    def _update_settings_bg(self, instance, value):
        """Update the background of the settings container when it moves/resizes."""
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(0.18, 0.18, 0.2, 1)
            RoundedRectangle(pos=instance.pos, size=instance.size, radius=[10])

    def _update_player_bg(self, instance, value):
        """Update the background of the player container when it moves/resizes."""
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(0.18, 0.18, 0.2, 1)
            RoundedRectangle(pos=instance.pos, size=instance.size, radius=[10])
            
    def _update_banned_bg(self, instance, value):
        """Update the background of the banned players container when it moves/resizes."""
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(0.18, 0.18, 0.2, 1)
            RoundedRectangle(pos=instance.pos, size=instance.size, radius=[10])

    def _update_console_bg(self, instance, value):
        """Update the background of the console container when it moves/resizes."""
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(0.05, 0.05, 0.1, 1)
            RoundedRectangle(pos=instance.pos, size=instance.size, radius=[10])

    def start_game(self, instance):
        """Handle the Start Game button click."""
        # If game is paused, resume it
        if self.game_paused:
            self.game_paused = False
            self.timer_event = Clock.schedule_interval(self.update_timer, 1)
            logging.info("Game resumed")
            return
            
        # Get settings from the GUI
        player_count = self.player_count.text
        try:
            game_duration = int(self.game_duration.text)
            lives_per_player = int(self.lives_per_player.text)
            score_to_win = int(self.score_to_win.text)
        except ValueError:
            logging.error("Error: Please enter valid numeric values for game settings.")
            return
            
        # Validate inputs
        if not player_count or game_duration <= 0 or lives_per_player <= 0 or score_to_win <= 0:
            logging.error("Error: Please fill in all fields with valid positive values.")
            return

        # Disable Start Game button and enable Stop/Freeze Game buttons
        self.start_button.disabled = True
        self.stop_button.disabled = False
        self.freeze_button.disabled = False
        self.game_running = True
        
        # Initialize players list
        self.active_players = [f"Player {i+1}" for i in range(int(player_count))]
        self.update_active_players_display()
        
        # Set up and start the timer
        self.remaining_time = game_duration
        self.update_timer_display()
        self.timer_event = Clock.schedule_interval(self.update_timer, 1)

        # Log the action
        logging.info(f"Game started with {player_count} players, {game_duration}s duration, "
                   f"{lives_per_player} lives per player, and {score_to_win} points to win.")
                   
        # Update player management dropdowns with active players
        self.update_player_dropdowns()

    def freeze_game(self, instance):
        """Handle the Freeze Game button click."""
        if not self.game_running:
            return
            
        if not self.game_paused:
            # Pause the game
            self.game_paused = True
            if self.timer_event:
                self.timer_event.cancel()
                self.timer_event = None
            
            # Enable Start Game button to allow resuming
            self.start_button.disabled = False
            logging.info("Game frozen. Press START GAME to resume.")
        else:
            # Resume the game
            self.game_paused = False
            self.timer_event = Clock.schedule_interval(self.update_timer, 1)
            self.start_button.disabled = True
            logging.info("Game resumed.")

    def stop_game(self, instance):
        """Handle the Stop Game button click."""
        # Enable Start Game button and disable Stop/Freeze Game buttons
        self.start_button.disabled = False
        self.stop_button.disabled = True
        self.freeze_button.disabled = True
        self.game_running = False
        self.game_paused = False
        
        # Stop the timer if it's running
        if self.timer_event:
            self.timer_event.cancel()
            self.timer_event = None
        
        # Reset the timer display
        self.timer_display.text = "00:00"
        
        # Clear active players
        self.active_players = []
        self.update_active_players_display()

        # Log the action
        logging.info("Game stopped.")

    def update_timer(self, dt):
        """Update the game timer every second."""
        if self.remaining_time > 0:
            self.remaining_time -= 1
            self.update_timer_display()
        else:
            # Time's up
            if self.timer_event:
                self.timer_event.cancel()
                self.timer_event = None
            logging.info("Game time expired!")
            self.stop_game(None)
            
    def update_timer_display(self):
        """Update the timer display with the current remaining time."""
        minutes = self.remaining_time // 60
        seconds = self.remaining_time % 60
        self.timer_display.text = f"{minutes:02d}:{seconds:02d}"
        
        # Change color based on remaining time
        if self.remaining_time <= 30:
            self.timer_display.color = (0.9, 0.2, 0.2, 1)  # Red when < 30 seconds
        elif self.remaining_time <= 60:
            self.timer_display.color = (0.9, 0.7, 0.2, 1)  # Yellow when < 60 seconds
        else:
            self.timer_display.color = (0.2, 0.8, 0.2, 1)  # Green otherwise

    def update_player_management(self, instance, value):
        """Update the player management when player count changes."""
        player_count = int(value)
        
        # Reset active players list if the game is not running
        if not self.game_running:
            self.active_players = [f"Player {i+1}" for i in range(player_count)]
            self.update_active_players_display()
        
        # Update dropdowns
        self.update_player_dropdowns()
        
        # Log the update
        logging.info(f"Updated player count to {player_count} players.")
        
    def check_player_lists(self, instance):
        """Update player dropdowns when they're about to be opened."""
        # This ensures the dropdown only shows active players
        self.update_player_dropdowns()
        
    def update_player_dropdowns(self):
        """Update all player-related dropdowns with current data."""
        # Update disconnect and ban dropdowns to show only active players
        if self.active_players:
            self.disconnect_player.values = self.active_players
            self.ban_player.values = self.active_players
            self.disconnect_player.text = self.active_players[0]
            self.ban_player.text = self.active_players[0]
        else:
            self.disconnect_player.values = ["No active players"]
            self.ban_player.values = ["No active players"]
            self.disconnect_player.text = "No active players"
            self.ban_player.text = "No active players"
            
        # Update unban dropdown to show banned players
        if self.banned_players:
            self.unban_player.values = self.banned_players
            self.unban_player.text = self.banned_players[0]
        else:
            self.unban_player.values = ["No banned players"]
            self.unban_player.text = "No banned players"
            
    def update_active_players_display(self):
        """Update the display of active players."""
        if self.active_players:
            players_text = ", ".join(self.active_players)
            self.active_players_label.text = f"Active Players: {players_text}"
        else:
            self.active_players_label.text = "Active Players: None"
            
            # Added condition to stop game if no players remain
            if self.game_running:
                logging.warning("No active players remain. Stopping game.")
                self.stop_game(None)
            
    def update_banned_players_display(self):
        """Update the display of banned players."""
        if self.banned_players:
            self.banned_list.text = "Banned Players:\n" + "\n".join(self.banned_players)
        else:
            self.banned_list.text = "No banned players"
            
    def disconnect_selected_player(self, instance):
        """Disconnect the selected player."""
        if not self.game_running:
            logging.warning("Cannot disconnect player: No game is running")
            return
            
        player = self.disconnect_player.text
        if player in self.active_players:
            self.active_players.remove(player)
            logging.info(f"{player} has been disconnected")
            self.update_active_players_display()
            self.update_player_dropdowns()
            
            # Check if we still have players
            if not self.active_players:
                logging.warning("No active players remain. Stopping game.")
                self.stop_game(None)
        else:
            logging.warning(f"Cannot disconnect {player}: Player not active or already disconnected")
            
    def ban_selected_player(self, instance):
        """Ban the selected player."""
        if not self.game_running:
            logging.warning("Cannot ban player: No game is running")
            return
            
        player = self.ban_player.text
        if player in self.active_players:
            # Remove from active players
            self.active_players.remove(player)
            
            # Add to banned players if not already banned
            if player not in self.banned_players:
                self.banned_players.append(player)
                
            logging.info(f"{player} has been banned")
            
            # Update displays and dropdowns
            self.update_active_players_display()
            self.update_banned_players_display()
            self.update_player_dropdowns()
            
            # Check if we still have players
            if not self.active_players:
                logging.warning("No active players remain. Stopping game.")
                self.stop_game(None)
        else:
            logging.warning(f"Cannot ban {player}: Player not active or already banned")
            
    def unban_selected_player(self, instance):
        """Unban the selected player."""
        player = self.unban_player.text
        if player in self.banned_players:
            self.banned_players.remove(player)
            logging.info(f"{player} has been unbanned")
            
            # Update displays and dropdowns
            self.update_banned_players_display()
            self.update_player_dropdowns()
        else:
            logging.warning(f"Cannot unban {player}: Player not in banned list")

    def update_status(self, message: str):
        """Update the status display with a new message."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_text.text += f"[{timestamp}] {message}\n"
        
        # Auto-scroll to the bottom
        self.status_text.cursor = (0, len(self.status_text.text))
        self.status_display.scroll_y = 0  # Scroll to bottom

class LaserTagApp(App):
    def build(self):
        return ConfiguratorGUI()

if __name__ == "__main__":
    LaserTagApp().run()