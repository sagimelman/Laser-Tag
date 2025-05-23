from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle
from kivy.properties import ListProperty
from kivy.clock import Clock
from datetime import datetime
import sqlite3

# Modern Rounded Button (same as your server)
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

class GameCard(BoxLayout):
    def __init__(self, game_data, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.height = 120
        self.padding = 10
        self.spacing = 5
        
        # Create card background
        with self.canvas.before:
            Color(0.15, 0.15, 0.2, 1)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[15])
        self.bind(pos=self.update_rect, size=self.update_rect)
        
        game_id, date_time, duration, player_count, player_names = game_data
        
        # Header with game ID and emoji
        header = BoxLayout(size_hint_y=0.3)
        emoji = self.get_game_emoji(duration, player_count)
        header.add_widget(Label(
            text=f"{emoji} GAME #{game_id}", 
            font_size=18, 
            bold=True,
            color=(0.3, 0.8, 1, 1),
            halign='left',
            text_size=(None, None)
        ))
        
        # Format date
        try:
            dt = datetime.strptime(date_time, "%Y-%m-%d %H:%M:%S")
            formatted_date = dt.strftime("%b %d, %Y • %I:%M %p")
        except:
            formatted_date = date_time
            
        header.add_widget(Label(
            text=formatted_date,
            font_size=12,
            color=(0.7, 0.7, 0.7, 1),
            halign='right',
            text_size=(None, None)
        ))
        self.add_widget(header)
        
        # Game info
        info_layout = GridLayout(cols=2, size_hint_y=0.7)
        
        # Duration
        duration_str = self.format_duration(duration)
        info_layout.add_widget(Label(
            text=f"⏱️ Duration: {duration_str}",
            font_size=14,
            color=(0.9, 0.9, 0.9, 1),
            halign='left',
            text_size=(None, None)
        ))
        
        # Players
        if player_count == 0:
            player_text = "🤖 Test Run"
            player_color = (0.8, 0.6, 0.2, 1)
        else:
            player_text = f"👥 {player_count} Players"
            player_color = (0.2, 0.8, 0.2, 1)
            
        info_layout.add_widget(Label(
            text=player_text,
            font_size=14,
            color=player_color,
            halign='left',
            text_size=(None, None)
        ))
        
        # Player names (if any)
        if player_names and player_count > 0:
            names_text = f"Players: {player_names.replace(',', ', ')}"
            info_layout.add_widget(Label(
                text=names_text,
                font_size=12,
                color=(0.7, 0.9, 0.7, 1),
                halign='left',
                text_size=(None, None)
            ))
        else:
            info_layout.add_widget(Label())  # Empty space
            
        info_layout.add_widget(Label())  # Empty space
        
        self.add_widget(info_layout)
    
    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size
    
    def format_duration(self, seconds):
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes:02d}:{secs:02d}"
    
    def get_game_emoji(self, duration, player_count):
        if player_count == 0:
            return "🧪"  # Test game
        elif duration < 60:
            return "⚡"  # Quick game
        elif duration > 240:
            return "🏆"  # Long game
        else:
            return "🎯"  # Normal game

class StatCard(BoxLayout):
    def __init__(self, title, value, emoji, color=(0.2, 0.8, 0.2, 1), **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.height = 80
        self.padding = 10
        
        # Create card background
        with self.canvas.before:
            Color(0.1, 0.1, 0.15, 1)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[10])
        self.bind(pos=self.update_rect, size=self.update_rect)
        
        # Value with emoji
        self.add_widget(Label(
            text=f"{emoji} {value}",
            font_size=20,
            bold=True,
            color=color,
            size_hint_y=0.6
        ))
        
        # Title
        self.add_widget(Label(
            text=title,
            font_size=12,
            color=(0.7, 0.7, 0.7, 1),
            size_hint_y=0.4
        ))
    
    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

class DatabaseViewer(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = 20
        self.spacing = 15
        Window.clearcolor = (0.08, 0.08, 0.12, 1)
        
        # Header
        header = BoxLayout(size_hint_y=None, height=60)
        header.add_widget(Label(
            text="🎮 LASER TAG DATABASE VIEWER",
            font_size=24,
            bold=True,
            color=(0.3, 0.8, 1, 1)
        ))
        
        # Refresh button
        refresh_btn = ModernRoundedButton(
            text="🔄 REFRESH",
            size_hint_x=0.2,
            background_color=(0.2, 0.6, 0.8, 1)
        )
        refresh_btn.bind(on_press=self.refresh_data)
        header.add_widget(refresh_btn)
        
        self.add_widget(header)
        
        # Statistics section
        self.stats_container = BoxLayout(size_hint_y=None, height=100, spacing=10)
        self.add_widget(self.stats_container)
        
        # Games list
        games_label = Label(
            text="📊 GAME HISTORY",
            font_size=18,
            bold=True,
            color=(0.9, 0.9, 0.9, 1),
            size_hint_y=None,
            height=40
        )
        self.add_widget(games_label)
        
        # Scrollable games container
        scroll = ScrollView()
        self.games_container = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=10
        )
        self.games_container.bind(minimum_height=self.games_container.setter('height'))
        scroll.add_widget(self.games_container)
        self.add_widget(scroll)
        
        # Load initial data
        self.refresh_data()
        
        # Auto-refresh every 10 seconds
        Clock.schedule_interval(lambda dt: self.refresh_data(), 10)
    
    def refresh_data(self, instance=None):
        try:
            conn = sqlite3.connect('lasertag.db')
            games = conn.execute("SELECT * FROM games ORDER BY date_time DESC").fetchall()
            conn.close()
            
            # Clear existing widgets
            self.stats_container.clear_widgets()
            self.games_container.clear_widgets()
            
            if not games:
                # No data message
                self.games_container.add_widget(Label(
                    text="📭 No games found!\n💡 Start playing to see data here",
                    font_size=16,
                    color=(0.6, 0.6, 0.6, 1),
                    text_size=(400, None),
                    halign='center'
                ))
            else:
                # Calculate statistics
                total_games = len(games)
                total_duration = sum(game[2] for game in games)
                total_players = sum(game[3] for game in games)
                avg_duration = total_duration / total_games if total_games else 0
                
                # Add stat cards
                self.stats_container.add_widget(StatCard(
                    "Total Games", str(total_games), "🎯", (0.3, 0.8, 1, 1)
                ))
                self.stats_container.add_widget(StatCard(
                    "Total Playtime", self.format_duration(total_duration), "⏱️", (0.8, 0.3, 1, 1)
                ))
                self.stats_container.add_widget(StatCard(
                    "Player Sessions", str(total_players), "👥", (0.2, 0.8, 0.2, 1)
                ))
                self.stats_container.add_widget(StatCard(
                    "Avg Game Length", self.format_duration(int(avg_duration)), "📊", (0.8, 0.6, 0.2, 1)
                ))
                
                # Add game cards
                for game in games:
                    self.games_container.add_widget(GameCard(game))
                    
        except Exception as e:
            # Error message
            self.games_container.clear_widgets()
            self.games_container.add_widget(Label(
                text=f"❌ Database Error!\n{str(e)}\n💡 Make sure lasertag.db exists",
                font_size=14,
                color=(0.9, 0.3, 0.3, 1),
                text_size=(400, None),
                halign='center'
            ))
    
    def format_duration(self, seconds):
        if seconds < 60:
            return f"{seconds}s"
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes:02d}:{secs:02d}"

class DatabaseViewerApp(App):
    def build(self):
        return DatabaseViewer()

if __name__ == "__main__":
    DatabaseViewerApp().run()