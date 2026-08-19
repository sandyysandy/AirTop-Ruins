import math

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
        is_grappling = getattr(self, 'grapple_attached', False)

        if is_dashing or is_grappling:
            if is_grappling and movement[0] != 0:
                self.velocity[0] += movement[0] * 0.1
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
        self.grapple_attached = False
        self.grapple_pos = [0, 0]
        self.grapple_length = 0
        self.grapple_max_length = 160
        self.grapple_pull_strength = 0.25

    def landedOnGround(self):
        super().landedOnGround()
        self.jumps = self.max_jumps
        self.dashes = self.max_dashes
    
    def fire_grapple(self, tilemap):
        if not self.inventory.get('grappling_hook'):
            return
        
        if self.grapple_attached:
            self.grapple_attached = False
            return
        
        center_x = self.rect().centerx
        center_y = self.rect().centery
        
        # FIX: Use the scene's calculated world-space mouse position!
        mouse_x, mouse_y = self.scene.mouse_pos

        angle = math.atan2(mouse_y - center_y, mouse_x - center_x)

        step_size = 4
        current_dist = 0
        test_x, test_y = center_x, center_y

        while current_dist < self.grapple_max_length:
            test_x += math.cos(angle) * step_size
            test_y += math.sin(angle) * step_size
            current_dist += step_size
        
            # This will now accurately check the grid based on correct world coordinates
            if tilemap.is_solid_tile((test_x, test_y)):
                self.grapple_attached = True
                self.grapple_pos = [test_x, test_y]
                self.grapple_length = math.hypot(test_x - center_x, test_y - center_y)
                break
            
    def render(self, surf, offset=(0, 0)):
        super().render(surf, offset)
        
        if self.grapple_attached:
            start_pos = (self.rect().centerx - offset[0], self.rect().centery - offset[1])
            end_pos = (self.grapple_pos[0] - offset[0], self.grapple_pos[1] - offset[1])
            
            dist = math.hypot(end_pos[0] - start_pos[0], end_pos[1] - start_pos[1])
            
            # Calculate how much slack is in the rope[cite: 25]
            slack = max(0, self.grapple_length - dist)
            rope_color = (130, 100, 70)  # Brownish rope color[cite: 25]
            
            num_segments = 4  # Change this number to add or remove segments!
            points = []
            
            for i in range(num_segments + 1):
                # t goes from 0.0 to 1.0 representing the percentage along the rope
                t = i / num_segments 
                
                # 1. Get the straight-line position at this percentage
                line_x = start_pos[0] + (end_pos[0] - start_pos[0]) * t
                line_y = start_pos[1] + (end_pos[1] - start_pos[1]) * t
                
                # 2. Calculate the parabolic sag: 4 * t * (1 - t)
                # This creates a curve that is 0 at the ends and 1 in the exact center
                curve_multiplier = 4 * t * (1 - t)
                
                # 3. Apply the slack to the Y axis based on the curve
                point_x = line_x
                point_y = line_y + (slack * 0.75 * curve_multiplier)
                
                points.append((point_x, point_y))
                
            # Draw all the connected segments at once using pygame.draw.lines
            if len(points) >= 2:
                pygame.draw.lines(surf, rope_color, False, points, 2)  

    def update(self, tilemap, movement=(0,0)):
        if getattr(self.scene.game, 'grappling_hook_enabled', False):
            self.max_jumps = 1  # Disable double jump
            self.max_dashes = 0 # Disable dash completely
        else:
            self.max_jumps = 2
            self.max_dashes = 2

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
            
        if self.grapple_attached:
            center_x, center_y = self.rect().centerx, self.rect().centery
            dist_to_hook = math.hypot(self.grapple_pos[0] - center_x, self.grapple_pos[1] - center_y)
        
            # --- NEW: Climb up or down the rope using W and S keys ---
            keys = pygame.key.get_pressed()
            climb_speed = 1.0
            if keys[pygame.K_w] or keys[pygame.K_UP]:
                self.grapple_length = max(20, self.grapple_length - climb_speed)
            elif keys[pygame.K_s] or keys[pygame.K_DOWN]:
                self.grapple_length = min(self.grapple_max_length, self.grapple_length + climb_speed)

            # If the player falls past the length of the rope
            if dist_to_hook > self.grapple_length:
                nx = (self.grapple_pos[0] - center_x) / dist_to_hook
                ny = (self.grapple_pos[1] - center_y) / dist_to_hook
                
                outward_vel = self.velocity[0] * -nx + self.velocity[1] * -ny
                if outward_vel > 0:
                    self.velocity[0] += nx * outward_vel
                    self.velocity[1] += ny * outward_vel
                
                pull_force = (dist_to_hook - self.grapple_length) * 0.1 
                self.velocity[0] += nx * pull_force
                self.velocity[1] += ny * pull_force

            self.velocity[0] *= 0.98
            self.velocity[1] *= 0.99 
            
            max_swing_speed = 7.0
            current_speed = math.hypot(self.velocity[0], self.velocity[1])
            if current_speed > max_swing_speed:
                self.velocity[0] = (self.velocity[0] / current_speed) * max_swing_speed
                self.velocity[1] = (self.velocity[1] / current_speed) * max_swing_speed


        if not self.grapple_attached:
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
        self.grapple_attached = False
    
    def death(self):
        self.grapple_attached = False
        super().death()

    def jump(self):
        if self.grapple_attached:
            return  # Disable jumping while attached to the grapple

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