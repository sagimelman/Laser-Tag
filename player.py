import time

class Player:
    def __init__(self, player_id, name, team=None):
        self.player_id = player_id
        self.name = name
        self.team = team
        self.health = 100
        self.max_health = 100
        self.score = 0
        self.is_alive = True
        self.respawn_time = None  # When player should respawn
        self.last_shot_time = 0   # To prevent rapid fire
        self.shots_fired = 0
        self.hits_landed = 0
    
    def reset(self, max_health=100):
        """Reset player for a new game"""
        self.max_health = max_health
        self.health = max_health
        self.score = 0
        self.is_alive = True
        self.respawn_time = None
        self.shots_fired = 0
        self.hits_landed = 0
    
    def take_damage(self, damage):
        """Take damage and check if player dies"""
        if not self.is_alive:
            return False
            
        self.health -= damage
        if self.health <= 0:
            self.health = 0
            self.is_alive = False
            return True  # Player died
        return False  # Player still alive
    
    def start_respawn_timer(self, respawn_seconds):
        """Start respawn timer"""
        self.respawn_time = time.time() + respawn_seconds
    
    def update(self, current_time):
        """Update player state, handle respawn"""
        if not self.is_alive and self.respawn_time and current_time >= self.respawn_time:
            self.respawn()
    
    def respawn(self):
        """Respawn the player"""
        self.health = self.max_health
        self.is_alive = True
        self.respawn_time = None
    
    def record_shot(self):
        """Record that player fired a shot"""
        current_time = time.time()
        
        # Implement cooldown if needed (e.g., 1 shot per second)
        if current_time - self.last_shot_time < 1.0:
            return False
            
        self.last_shot_time = current_time
        self.shots_fired += 1
        return True
    
    def record_hit(self):
        """Record that player landed a hit"""
        self.hits_landed += 1
    
    def get_state(self):
        """Return player state for GUI/network"""
        return {
            "id": self.player_id,
            "name": self.name,
            "team": self.team,
            "health": self.health,
            "max_health": self.max_health,
            "score": self.score,
            "is_alive": self.is_alive,
            "respawning_in": round(self.respawn_time - time.time()) if self.respawn_time else None,
            "accuracy": round((self.hits_landed / self.shots_fired) * 100) if self.shots_fired > 0 else 0
        }
