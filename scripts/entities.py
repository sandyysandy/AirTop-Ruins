import pygame

from scripts.utils import Object

class PhysicsEntity(Object):
    def __init__(self, scene, e_type, pos, size):
        super().__init__(scene, e_type, pos, size)
        self.velocity = [0, 0]
        self.collisions = {'up': False, 'down': False, 'right': False, 'left': False}

        self.flip = False
        self.dashing = False
        self.speed = 1.5
        self.inventory = {}
        self.inventory_last_level = {}
        self.last_movement = [0, 0]

        self.current_interactable = None


    def update(self, tilemap, movement=(0,0)):
        self.collisions = {'up': False, 'down': False, 'right': False, 'left': False}

        # Check if the entity is currently executing a quick-burst dash sequence
        is_dashing = getattr(self, 'dash_timer', 0) > 0

        if is_dashing:
            # Maintain explicit dash velocity vectors, bypassing walking rules
            frame_movement = (self.velocity[0], self.velocity[1])
        else:
            # 1. IMPROVED MOVEMENT: Horizontal Acceleration and Friction (Inertia)
            if movement[0] != 0:
                self.velocity[0] += movement[0] * 0.2  # Smoothly build up speed
                if movement[0] > 0:
                    self.velocity[0] = min(self.velocity[0], self.speed)
                else:
                    self.velocity[0] = max(self.velocity[0], -self.speed)
            else:
                self.velocity[0] += (0 - self.velocity[0]) * 0.2  # Smoothly slide to a halt
                if abs(self.velocity[0]) < 0.1:
                    self.velocity[0] = 0

            frame_movement = (self.velocity[0], self.velocity[1])

        # --- X AXIS COLLISION (Tiles) ---
        self.pos[0] += frame_movement[0]
        entity_rect = self.rect()
        for rect in tilemap.physical_rect_around(self.pos):
            if entity_rect.colliderect(rect):
                if frame_movement[0] > 0:
                    entity_rect.right = rect.left
                    self.collisions['right'] = True
                elif frame_movement[0] < 0:
                    entity_rect.left = rect.right
                    self.collisions['left'] = True
                self.pos[0] = entity_rect.x

        # --- X AXIS COLLISION (Interactables) ---
        for interactable in self.scene.interactables:
            if interactable.should_collide(self) and entity_rect.colliderect(interactable.rect()):
                if frame_movement[0] > 0:
                    entity_rect.right = interactable.rect().left
                    self.collisions['right'] = True
                elif frame_movement[0] < 0:
                    entity_rect.left = interactable.rect().right
                    self.collisions['left'] = True
                self.pos[0] = entity_rect.x


        # --- Y AXIS COLLISION (Tiles) ---
        self.pos[1] += frame_movement[1]
        entity_rect = self.rect()
        for rect in tilemap.physical_rect_around(self.pos):
            if entity_rect.colliderect(rect):
                if frame_movement[1] > 0:
                    entity_rect.bottom = rect.top
                    self.collisions['down'] = True
                elif frame_movement[1] < 0:
                    entity_rect.top = rect.bottom
                    self.collisions['up'] = True
                self.pos[1] = entity_rect.y
                self.velocity[1] = 0

        # --- Y AXIS COLLISION (Interactables) ---
        for interactable in self.scene.interactables:
            if interactable.should_collide(self) and entity_rect.colliderect(interactable.rect()):
                if frame_movement[1] > 0:
                    entity_rect.bottom = interactable.rect().top
                    self.collisions['down'] = True
                elif frame_movement[1] < 0:
                    entity_rect.top = interactable.rect().bottom
                    self.collisions['up'] = True
                self.pos[1] = entity_rect.y
                self.velocity[1] = 0

        if not is_dashing:
            if movement[0] > 0:
                self.flip = False
            if movement[0] < 0:
                self.flip = True
        
        self.last_movement = movement

        if not is_dashing:
            self.velocity[1] = min(5, self.velocity[1] + 0.1)

        if self.collisions['down']:
            self.landedOnGround()
        
        self.current_interactable = None
        tile_size = 8 

        if self.flip:
            interaction_rect = pygame.Rect(self.pos[0] - tile_size, self.pos[1], tile_size, self.size[1])
        else:
            interaction_rect = pygame.Rect(self.rect().right, self.pos[1], tile_size, self.size[1])
            
        for interactable in self.scene.interactables:
            if not interactable.interacted and interaction_rect.colliderect(interactable.rect()):
                self.current_interactable = interactable
                break
        
    def useItem(self, item, amount):
        if item in self.inventory and self.inventory[item] >= amount:
            self.inventory[item] -= amount
            if self.inventory[item] <= 0:
                del self.inventory[item]
            return True
        return False

    def use(self):
        if self.current_interactable:
            self.current_interactable.interact(self)

    def death(self):
        self.inventory = self.inventory_last_level.copy() # Reset inventory to what it was at the start of the level
        self.scene.start_transition()

    def landedOnGround(self):
        self.velocity[1] = 0

    def render(self, surf, offset=(0,0)):
        surf.blit(pygame.transform.flip(self.scene.assets[self.type], self.flip, False), (int(self.pos[0] - offset[0]), int(self.pos[1] - offset[1])))

class Player(PhysicsEntity):
    def __init__(self, game, pos, size):
        super().__init__(game, 'player', pos, size)
        self.jumps = 0
        self.max_jumps = 2
        self.sprinting = False
        
        # Dash State
        self.dash_timer = 0
        self.dash_cooldown = 0
        self.dash_direction = 0
        self.dashes = 2
        self.max_dashes = 2

        self.wall_slide = False

    def landedOnGround(self):
        super().landedOnGround()
        self.jumps = self.max_jumps
        self.dashes = self.max_dashes
    
    def update(self, tilemap, movement=(0,0)):
        if self.dash_timer > 0:
            self.dash_timer -= 1
            if self.dash_timer == 0:
                self.velocity[0] *= 0.5
        
        if self.dash_cooldown > 0:
            self.dash_cooldown -= 1

        self.dashing = (self.dash_timer > 0)

        if self.dash_timer <= 0:
            if self.sprinting:
                self.speed = 2.2  # Given a bit more juice than standard walking
            else:
                self.speed = 1.5
        else:
            self.velocity[0] = self.dash_direction * 4.5
            self.velocity[1] = 0

        if self.collisions['right'] or self.collisions['left'] and not self.collisions['down'] and self.velocity[1] > 0:
            self.wall_slide = True
            self.velocity[1] = min(self.velocity[1], 0.5)  # Limit falling speed while wall sliding
            if self.collisions['right']:
                self.flip = False
            else:                
                self.flip = True
        else:
            self.wall_slide = False

        if self.velocity[0] > 0:
            self.velocity[0] = max(self.velocity[0] - 0.1, 0)
        else:
            self.velocity[0] = min(self.velocity[0] + 0.1, 0)
        super().update(tilemap, movement=movement)
    
    def reset(self):
        super().reset()
        self.jumps = self.max_jumps
        self.dash_timer = 0
        self.dash_cooldown = 0
        self.dashes = self.max_dashes

    def jump(self):
        if self.wall_slide:
            # If a wall is physically touching the player's left side
            if self.collisions['left']:
                self.velocity[0] = 3.5   # Push right (away from wall)
                self.velocity[1] = -2.5  # Push up
                self.jumps = max(0, self.max_jumps - 1)
            
            # If a wall is physically touching the player's right side
            elif self.collisions['right']:
                self.velocity[0] = -3.5  # Push left (away from wall)
                self.velocity[1] = -2.5  # Push up
                self.jumps = max(0, self.max_jumps - 1)
                
        elif self.jumps:
            self.velocity[1] = -3
            self.jumps -= 1

    def sprint(self):
        self.sprinting = not self.sprinting
    
    def dash(self):
        if self.dash_timer <= 0 and self.dash_cooldown <= 0 and self.dashes > 0:
            self.dash_timer = 12    # Active dash burst length in frames
            self.dash_cooldown = 30 # Cooldown period before allowing another dash sequence
            self.dashes -= 1       # Consume the dash charge

            # Check keyboard states directly for intuitive directional aiming
            keys = pygame.key.get_pressed()
            if keys[pygame.K_LEFT]:
                self.dash_direction = -1
            elif keys[pygame.K_RIGHT]:
                self.dash_direction = 1
            else:
                # If no movement direction keys are held, default to the way the player is facing
                self.dash_direction = -1 if self.flip else 1