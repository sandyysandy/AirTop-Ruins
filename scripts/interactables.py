import pygame
import math

from scripts.utils import Object

class Interactable(Object):
    def __init__(self, scene, variant, pos, size=(16, 16)): 
        super().__init__(scene, 'interactables', pos, size)
        self.variant = variant
        self.interacted = False

    def update(self):
        pass

    def interact(self, player):
        pass

    def should_collide(self, player):
        return True
    
    def should_render(self):
        return True
    
    def interaction_prompt(self):
        return "Interact"

    def render(self, surf, offset=(0, 0)):
        render_pos = (int(self.pos[0] - offset[0]), int(self.pos[1] - offset[1]))
        if not self.should_render():
            return
        img = self.scene.assets['tiles']['interactables'][self.variant]
        surf.blit(img, render_pos)
    


class SilverLock(Interactable):
    def interaction_prompt(self):
        return "Silver Lock"

    def should_collide(self, player):
        return not self.interacted
    
    def should_render(self):
        return not self.interacted

    def interact(self, player):
        if player.useItem('silver_keys', 1):
            self.interacted = True

class CopperLock(Interactable):
    def interaction_prompt(self):
        return "Copper Lock"

    def should_collide(self, player):
        return not self.interacted

    def should_render(self):
        return not self.interacted

    def interact(self, player):
        if player.useItem('copper_keys', 1):
            self.interacted = True

class GoldLock(Interactable):
    def interaction_prompt(self):
        return "Gold Lock - Requires 2 Gold Keys"

    def should_collide(self, player):
        return not self.interacted

    def should_render(self):
        return not self.interacted

    def interact(self, player):
        if player.useItem('gold_keys', 2):
            self.interacted = True
        

class Portal(Interactable):
    def interaction_prompt(self):
        return "Portal"

    def should_collide(self, player):
        return False

    def interact(self, player):
        if not self.interacted:
            self.scene.next_level()
            self.interacted = True




INTERACTABLE_TYPES = {
    0: SilverLock,
    1: CopperLock,
    2: GoldLock,
    3: Portal,
}