import time
from player import Player

class Game:
    def __init__(self):
        self.players = {}  # Dictionary of Player objects, keyed by player_id
        self.state = "WAITING"  # WAITING, ACTIVE, ENDED
        self.game_settings = {
            "game_duration_seconds": 300,  # 5 minutes
            "max_health": 100,
            "respawn_time_seconds": 5,
            "teams_enabled": False
        }
        self.start_time = None
        self.end_time = None
    
    def add_player(self, player_id, name):
        """Add a new player to the game"""
        if player_id not in self.players:
            self.players[player_id] = Player(player_id, name)
            return True
        return False
    
    def remove_player(self, player_id):
        """Remove a player from the game"""
        if player_id in self.players:
            del self.players[player_id]
            return True
        return False
    
    def start_game(self):
        """Start the game"""
        if len(self.players) >= 2:  # Need at least 2 players
            self.state = "ACTIVE"
            self.start_time = time.time()
            self.end_time = self.start_time + self.game_settings["game_duration_seconds"]
            # Reset all players for new game
            for player in self.players.values():
                player.reset(self.game_settings["max_health"])
            return True
        return False
    
    def end_game(self):
        """End the game and determine winner"""
        self.state = "ENDED"
        # Find player with highest score
        highest_score = -1
        winner = None
        
        for player in self.players.values():
            if player.score > highest_score:
                highest_score = player.score
                winner = player
        
        return {
            "winner": winner.player_id if winner else None,
            "winner_name": winner.name if winner else None,
            "scores": {p_id: p.score for p_id, p in self.players.items()}
        }
    
    def process_hit(self, shooter_id, target_id):
        """Process a hit from shooter to target"""
        if self.state != "ACTIVE":
            return False
            
        if shooter_id not in self.players or target_id not in self.players:
            return False
            
        shooter = self.players[shooter_id]
        target = self.players[target_id]
        
        # Can't shoot yourself
        if shooter_id == target_id:
            return False
            
        # Can't shoot teammates if teams enabled
        if self.game_settings["teams_enabled"] and shooter.team == target.team:
            return False
            
        # Can't hit dead players
        if not target.is_alive:
            return False
            
        # Process the hit
        damage = 10  # Standard damage
        target.take_damage(damage)
        shooter.record_hit()  # Record successful hit for shooter
        
        # Award point if target dies
        if not target.is_alive:
            shooter.score += 1
            # Start respawn timer for target
            target.start_respawn_timer(self.game_settings["respawn_time_seconds"])
            
        return True
    
    def update(self):
        """Update game state, check for game end, respawn players"""
        current_time = time.time()
        
        if self.state == "ACTIVE":
            # Check if game time is up
            if current_time >= self.end_time:
                return self.end_game()
                
            # Update all players (handle respawns, etc)
            for player in self.players.values():
                player.update(current_time)
                
        return None  # No game end yet
        
    def get_game_state(self):
        """Return current game state for GUI display"""
        return {
            "state": self.state,
            "players": {p_id: p.get_state() for p_id, p in self.players.items()},
            "settings": self.game_settings,
            "time_remaining": round(self.end_time - time.time()) if self.state == "ACTIVE" and self.end_time else None
        }
