import pygame
import math

from scripts.utils import Object

# Maps the sheet variant index to its inventory registration rules.
# - 'key': The dictionary string name matching player.inventory
# - 'max': Maximum carrying capacity limit (use float('inf') for infinite/uncapped)

ITEM_TYPES = {
    0: {'key': 'gems', 'max': float('inf')},
    1: {'key': 'silver_keys', 'max': 5},
    2: {'key': 'copper_keys', 'max': 5},
    3: {'key': 'gold_keys', 'max': 5}, 
    4: {'key': 'gold_sack', 'max': float('inf')}
}

class Item(Object):
    def __init__(self, scene, variant, pos, size=(16, 16)): 
        super().__init__(scene, 'items', pos, size)
        self.variant = variant
        self.collected = False
        self.animation_timer = 0
        
        # Automatically look up internal item registration tracking metadata
        config = ITEM_TYPES.get(self.variant, {'key': 'unknown', 'max': float('inf')})
        self.item_key = config['key']
        self.max_limit = config['max']

    def update(self):
        self.animation_timer += 1

    def collide_with_player(self, player):
        # Fetch current count from player inventory safely
        current_amount = player.inventory.get(self.item_key, 0)
        
        # AUTOMATIC COLLECTION: Only pick up if player is under maximum capacity limit
        if current_amount < self.max_limit:
            player.inventory[self.item_key] = current_amount + 1
            self.collected = True
            return True
            
        return False

    def render(self, surf, offset=(0, 0)):
        if self.collected:
            return
        
        # Idle bobbing floating effect
        bob_offset = math.sin(self.animation_timer * 0.1) * 3
        render_pos = (int(self.pos[0] - offset[0]), int(self.pos[1] - offset[1] + bob_offset))

        try:
            img = self.scene.assets['tiles']['items'][self.variant]
            surf.blit(img, render_pos)
        except (KeyError, IndexError):
            # Fallback debug frame rendering
            pygame.draw.rect(surf, (0, 255, 255), (render_pos[0], render_pos[1], self.size[0], self.size[1]), 1)