import json
from tkinter import font

import pygame
from scripts.entities import Player
from scripts.tilemap import TileMap
from scripts.clouds import Clouds
from scripts.items import Item, ITEM_TYPES


class Scene:
    def __init__(self, game):
        self.game = game
        self.display = pygame.Surface((self.game.game_width, self.game.game_height))
        self.tilemap = TileMap(game.assets['tiles'])
        self.assets = game.assets
        self.scroll = [0.0, 0.0]
        self.background_color = (61, 186, 235)
        self.level_transition = False
        self.level = 0
        self.free_movement = [False, False, False, False]
        self.shift = False
        self.ctrl = False
        self.alt = False
        self.tab = False
        self.tile_pos = (0, 0)

        self.mouse_pos = (0, 0)    
    
    def load_level(self, map_id):
        self.tilemap.load(f'assets/maps/{map_id}.json')

    def reset(self):
        self.free_movement = [False, False, False, False]


    def handle_event(self, event):
        pass

    def update(self):
        mouse_window_pos = pygame.mouse.get_pos()
        scale_x = self.game.game_width / self.game.screen_width
        scale_y = self.game.game_height / self.game.screen_height
        self.mouse_pos = (mouse_window_pos[0] * scale_x + self.scroll[0], mouse_window_pos[1] * scale_y + self.scroll[1])

    def render(self):
        self.display.blit(pygame.transform.scale(self.assets['background_back'], (self.display.get_width(), self.display.get_height())), (0, 0))
        self.display.blit(pygame.transform.scale(self.assets['background_front'], (self.display.get_width(), self.display.get_height())), (0, 0))

        return self.display
    
    def update_free_movement(self):
        # Scroll movement in free cam
        if self.shift:
            self.scroll[0] += (self.free_movement[1] - self.free_movement[0]) * 8
            self.scroll[1] += (self.free_movement[3] - self.free_movement[2]) * 8
        elif self.alt:
            self.scroll[0] += (self.tile_pos[0] * self.tilemap.tile_size - self.display.get_width() / 2 - self.scroll[0]) / 30
            self.scroll[1] += (self.tile_pos[1] * self.tilemap.tile_size - self.display.get_height() / 2 - self.scroll[1]) / 30
        else:
            self.scroll[0] += (self.free_movement[1] - self.free_movement[0]) * 5
            self.scroll[1] += (self.free_movement[3] - self.free_movement[2]) * 5

class GameScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.clouds = Clouds(self.assets['clouds'], 16)
        self.player = Player(self, [100, 100], (8, 15))
        self.movement = [False, False]
        self.items = []
        self.interactables = []
        self.player_spawn_pos = [100, 100]
        self.transition = 0
        self.player_freeze_pos = [0, 0]
        self.reset()
        self.load_level(self.level)

        self.start_time = pygame.time.get_ticks()



    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_a:
                if not self.tab: self.movement[0] = True
                self.free_movement[0] = True
            if event.key == pygame.K_d:
                if not self.tab: self.movement[1] = True
                self.free_movement[1] = True
            if event.key == pygame.K_SPACE or event.key == pygame.K_w:
                if not self.tab: self.player.jump()
                self.free_movement[2] = True
            if event.key == pygame.K_s:
                self.free_movement[3] = True
            if event.key == pygame.K_LSHIFT:
                self.player.sprint()
            if event.key == pygame.K_e:
                self.player.use()
            if event.key == pygame.K_c:
                self.player.dash()
            if event.key == pygame.K_r:
                self.player.death()
            if event.key == pygame.K_v or event.key == pygame.K_x:
                self.player.fire_grapple(self.tilemap)
        if event.type == pygame.KEYUP:
            if event.key == pygame.K_a:
                self.movement[0] = False
                self.free_movement[0] = False
            if event.key == pygame.K_d:
                self.movement[1] = False
                self.free_movement[1] = False
            if event.key == pygame.K_SPACE or event.key == pygame.K_w:
                self.free_movement[2] = False
            if event.key == pygame.K_s:
                self.free_movement[3] = False
            if event.key == pygame.K_TAB:
                self.tab = not self.tab
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left mouse button
                self.player.fire_grapple(self.tilemap)
                
    def load_level(self, map_id):
        if self.level == 0 and self.game.grappling_hook_enabled or self.level == 1 and self.game.grappling_hook_enabled:
            self.tilemap.load(f'assets/maps/{map_id}_grapple.json')
        else: 
            super().load_level(map_id)
        if self.level == 0:
            self.start_time = pygame.time.get_ticks()
            self.player.inventory = {}
            if self.game.new_game_plus:
                self.player.inventory['grappling_hook'] = 1
        self.player.inventory_last_level = self.player.inventory.copy() # Save current inventory before resetting for new level
        self.transition = -30
        self.player_spawn_pos = self.tilemap.find_spawn_point() or [100, 100]
        self.player.velocity = [0, 0]
        self.reset()

    def reset(self):
        # Move the player back to the saved spawn position whenever you reset
        self.player.pos = self.player_spawn_pos.copy()
        self.player.velocity = [0, 0]
        self.tab = False
        self.movement = [False, False]
        self.init_items()
        self.init_interactables()
    
    def next_level(self):
        self.level += 1
        if self.level >= self.game.level_count:
            self.level = 0
            self.game.new_game_plus = True
            self.game.final_player_inventory = self.player.inventory.copy()
            self.game.final_player_inventory.pop('silver_keys', None)
            self.game.final_player_inventory.pop('copper_keys', None)
            self.game.final_player_inventory.pop('gold_keys', None)
            self.game.switch_scene('end_scene')
        else:
            self.start_transition()

    def start_transition(self):
        self.player.velocity = [0, 0]
        self.player_freeze_pos = self.player.pos.copy()
        self.level_transition = True

    def init_items(self):
        self.items = self.tilemap.find_items(self)

    def init_interactables(self):
        self.interactables = self.tilemap.find_interactables(self)

    def update(self):
        super().update()
        self.game.timer = (self.game.current_time - self.start_time) // 1000
        player_rect = self.player.rect()
        if (not self.tab):
            self.scroll[0] += (player_rect.centerx - self.display.get_width() / 2 - self.scroll[0]) // 30
            self.scroll[1] += (player_rect.centery - self.display.get_height() / 2 - self.scroll[1]) // 30
        else:
            self.movement = [False, False]
            self.update_free_movement()
        
        self.clouds.update()
        self.player.update(self.tilemap, (self.movement[1] - self.movement[0], 0))
        if self.player.pos[1] > 1000:
            self.player.death()

        for item in self.items.copy():
            item.update()
            if player_rect.colliderect(item.rect()):
                if not item.collected:
                    if item.collide_with_player(self.player):
                        self.items.remove(item)

        for interactable in self.interactables:
            interactable.update()

        if self.level_transition:
            self.transition += 1
            self.player.pos = self.player_freeze_pos.copy()
            if self.transition > 30:
                self.load_level(self.level)
                self.level_transition = False

        if self.transition < 0:
            self.transition += 1


    def render_hud(self):
        start_x = 5
        start_y = 5
        spacing = 35
        font = self.assets['ingame_font']

        for variant, config in ITEM_TYPES.items():
            item_key = config['key']
            max_val = config['max']
            count = self.player.inventory.get(item_key, 0)

            try:
                icon_img = self.assets['tiles']['items'][variant].copy()
                icon_img.set_alpha(200)
                self.display.blit(pygame.transform.scale_by(icon_img, 2), (start_x, start_y))
            except (KeyError, IndexError):
                continue

            # Format item numbers depending on whether it is capped or infinite
            if max_val == float('inf'):
                text_str = f"x{count}"
            else:
                text_str = f"{count}/{max_val}"

            text_surf = font.render(text_str, False, (0, 0, 0))
            text_rect = text_surf.get_rect(midleft=(start_x + 35, start_y + 10))
            self.display.blit(text_surf, text_rect)

            start_y += spacing

        font = self.assets['font']
        text_surf = font.render(f"Level: {self.level+1}/5", False, (0, 0, 0))
        self.display.blit(text_surf, (self.display.get_width() - text_surf.get_width() - 20, 20))

        timer_text = f"Time: {self.game.timer}s"
        timer_surf = font.render(timer_text, False, (0, 0, 0))
        self.display.blit(timer_surf, (self.display.get_width() - timer_surf.get_width() - 20, 50))
        
        # Prompt to interact if player is in range of an interactable
        interactable = self.player.current_interactable
        if interactable:
            text_surf = font.render(interactable.interaction_prompt(), False, (0, 0, 0))
            self.display.blit(text_surf, ((self.display.get_width() - text_surf.get_width())//2, 20))
        

    def render_transition(self):
        if self.transition:
            transition_surf = pygame.Surface((self.display.get_size()))
            pygame.draw.circle(transition_surf, (255, 255, 255), (int(self.display.get_width() / 2), int(self.display.get_height() / 2)), (30 - abs(self.transition)) * 13)
            transition_surf.set_colorkey((255, 255, 255))
            self.display.blit(transition_surf, (0, 0))


    def render(self):
        super().render()
        
        self.clouds.render(self.display, offset=self.scroll)
        self.tilemap.render(self.display, offset=self.scroll)
        
        # Render our active extracted object class items
        for item in self.items:
            item.render(self.display, offset=self.scroll)

        for interactable in self.interactables:
            interactable.render(self.display, offset=self.scroll)
            
        self.player.render(self.display, offset=self.scroll)
        if not self.tab: self.render_hud()
        self.render_transition()
        return self.display

class EditorScene(Scene):
    def __init__(self, game):
        super().__init__(game)

        self.tile_list = list(self.assets['tiles'])
        self.tile_sprites = self.assets['tiles']
        self.tile_group = 0
        self.tile_variant = 0

        self.clicking = False
        self.right_clicking = False
        self.ongrid = True

        self.current_tile_img = self.tile_sprites[self.tile_list[self.tile_group]][self.tile_variant].copy()

        self.load_level(self.level)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: # Left mouse button
                self.clicking = True
                if not self.ongrid:
                    self.tilemap.offgrid_tiles.append({'type': self.tile_list[self.tile_group], 'variant': self.tile_variant, 'pos': (int(self.mouse_pos[0] - self.current_tile_img.get_width() / 2), int(self.mouse_pos[1] - self.current_tile_img.get_height() / 2))})
            if event.button == 3:  # Right mouse button
                self.right_clicking = True
            if self.shift:
                if event.button == 4: # Scroll up
                    self.tile_variant = (self.tile_variant - 1) % len(self.tile_sprites[self.tile_list[self.tile_group]])
                if event.button == 5: # Scroll down
                    self.tile_variant = (self.tile_variant + 1) % len(self.tile_sprites[self.tile_list[self.tile_group]])
            else:
                if event.button == 4:
                    self.tile_group = (self.tile_group - 1) % len(self.tile_list)
                    self.tile_variant = 0
                if event.button == 5:
                    self.tile_group = (self.tile_group + 1) % len(self.tile_list)
                    self.tile_variant = 0
        if event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self.clicking = False
            if event.button == 3:
                self.right_clicking = False

        if event.type == pygame.KEYDOWN:
            if not self.ctrl:
                if event.key == pygame.K_a:
                    self.free_movement[0] = True
                if event.key == pygame.K_d:
                    self.free_movement[1] = True
                if event.key == pygame.K_w:
                    self.free_movement[2] = True
                if event.key == pygame.K_s:
                    self.free_movement[3] = True
                if event.key == pygame.K_UP:
                    self.tile_group = (self.tile_group - 1) % len(self.tile_list)
                    self.tile_variant = 0
                if event.key == pygame.K_DOWN:
                    self.tile_group = (self.tile_group + 1) % len(self.tile_list)
                    self.tile_variant = 0
                if event.key == pygame.K_LEFT:
                    self.tile_variant = (self.tile_variant - 1) % len(self.tile_sprites[self.tile_list[self.tile_group]])
                if event.key == pygame.K_RIGHT:
                    self.tile_variant = (self.tile_variant + 1) % len(self.tile_sprites[self.tile_list[self.tile_group]])

            if event.key == pygame.K_SPACE:
                self.ongrid = not self.ongrid
            if event.key == pygame.K_LSHIFT:
                self.shift = True
            if event.key == pygame.K_LCTRL:
                self.ctrl = True
            if event.key == pygame.K_LALT:
                self.alt = not self.alt
            if event.key == pygame.K_r:
                self.right_clicking = True
                if not self.ongrid:
                    self.tilemap.offgrid_tiles.append({'type': self.tile_list[self.tile_group], 'variant': self.tile_variant, 'pos': (int(self.mouse_pos[0] - self.current_tile_img.get_width() / 2), int(self.mouse_pos[1] - self.current_tile_img.get_height() / 2))})
            if event.key == pygame.K_s and self.ctrl:
                try:
                    self.tilemap.save(f'assets/maps/{self.level}.json')
                    print(f'Map saved to /maps/{self.level}.json')
                except (json.JSONDecodeError):
                    print('Can\'t save map data')
        if event.type == pygame.KEYUP:
            if event.key == pygame.K_a:
                self.free_movement[0] = False
            if event.key == pygame.K_d:
                self.free_movement[1] = False
            if event.key == pygame.K_w:
                self.free_movement[2] = False
            if event.key == pygame.K_s:
                self.free_movement[3] = False
            if event.key == pygame.K_r:
                self.right_clicking = False
            if event.key == pygame.K_LSHIFT:
                self.shift = False
            if event.key == pygame.K_LCTRL:
                self.ctrl = False
            if event.key == pygame.K_f:
                self.tilemap.autotile(self.tile_pos)
            if event.key == pygame.K_q and self.ctrl:
                if self.level > 0:
                    self.level -= 1
                    self.load_level(self.level)
            if event.key == pygame.K_e and self.ctrl:
                if self.level < self.game.level_count - 1:
                    self.level += 1
                    self.load_level(self.level)

    def update(self):    
        super().update()

        self.tile_pos = (int(self.mouse_pos[0]  // self.tilemap.tile_size), int(self.mouse_pos[1] // self.tilemap.tile_size))

        if self.clicking and self.ongrid:
            self.tilemap.tilemap[str(self.tile_pos[0]) + ';' + str(self.tile_pos[1])] = {'type': self.tile_list[self.tile_group], 'variant': self.tile_variant, 'pos': self.tile_pos}
        if self.right_clicking:
            tile_loc = str(self.tile_pos[0]) + ';' + str(self.tile_pos[1])
            if tile_loc in self.tilemap.tilemap:
                del self.tilemap.tilemap[tile_loc]
            for tile in self.tilemap.offgrid_tiles.copy():
                tile_img = self.tile_sprites[tile['type']][tile['variant']]
                tile_rect = pygame.Rect(tile['pos'][0], tile['pos'][1], tile_img.get_width(), tile_img.get_height())
                if tile_rect.collidepoint(self.mouse_pos):
                    self.tilemap.offgrid_tiles.remove(tile)
        
        self.update_free_movement()
    



    def render_hud(self):
        # Render current tile preview in the top-left corner
        self.current_tile_img = self.tile_sprites[self.tile_list[self.tile_group]][self.tile_variant].copy()
        self.current_tile_img.set_alpha(200)
        self.display.blit(pygame.transform.scale_by(self.current_tile_img, 2), (20, 20))

        # Render tile preview at mouse position
        if self.ongrid:
            self.display.blit(self.current_tile_img, (self.tile_pos[0] * self.tilemap.tile_size - self.scroll[0], self.tile_pos[1] * self.tilemap.tile_size - self.scroll[1]))
        else:
            self.display.blit(self.current_tile_img, (int(self.mouse_pos[0] - self.current_tile_img.get_width() / 2 - self.scroll[0]), int(self.mouse_pos[1] - self.current_tile_img.get_height() / 2 - self.scroll[1])))

        font = self.assets['font']
        text_surf = font.render(f"Level: {self.level+1}/5", False, (0, 0, 0))
        self.display.blit(text_surf, (self.display.get_width() - text_surf.get_width() - 20, 20))

    def render(self):
        super().render()
        self.tilemap.render(self.display, offset=self.scroll)
        self.render_hud()

        return self.display
    
class MainMenuScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.buttons = {
            'play': pygame.Rect(220, 140, 200, 50),
            'editor': pygame.Rect(220, 210, 200, 50),
            'how_to_play': pygame.Rect(220, 280, 200, 50),
            'toggle_grapple': pygame.Rect(220, 350, 200, 40),
        }
    
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left mouse button
                for action, rect in self.buttons.items():
                    if rect.collidepoint(self.mouse_pos):
                        if action == 'play':
                            self.game.switch_scene('game')
                        elif action == 'editor':
                            self.game.switch_scene('editor') 
                        elif action == 'how_to_play':
                            self.game.switch_scene('how_to_play') 
                        elif action == 'toggle_grapple' and self.game.new_game_plus:
                            # Flip the boolean state back and forth
                            self.game.grappling_hook_enabled = not self.game.grappling_hook_enabled

    def reset(self):
        pass

    def update(self):
        super().update()

    def renderButtonText(self):
        for action, rect in self.buttons.items():
            if action == 'toggle_grapple':
                if not self.game.new_game_plus:
                    continue
                status = "Enabled" if self.game.grappling_hook_enabled else "Disabled"
                text = f"Grapple: {status}"
            else:
                text = action.replace("_", " ").capitalize()
            
            text_surf = self.getFont().render(text.capitalize(), False, (255, 255, 255))
            
            text_rect = text_surf.get_rect(center=rect.center)
            
            self.display.blit(text_surf, text_rect)

    def getFont(self):
        return self.assets['font']

    def render(self):
        self.display.fill(self.background_color)
        title_surf = self.assets['title_font'].render("airTop Ruins", False, (255, 255, 255))
        title_rect = title_surf.get_rect(center=(self.display.get_width() // 2, 60))
        self.display.blit(title_surf, title_rect)
        pygame.draw.rect(self.display, (255, 0, 0), self.buttons['play'])
        pygame.draw.rect(self.display, (0, 255, 0), self.buttons['editor'])
        if self.game.new_game_plus:
            pygame.draw.rect(self.display, (150, 50, 200), self.buttons['toggle_grapple'])
        pygame.draw.rect(self.display, (0, 0, 255), self.buttons['how_to_play'])
        self.renderButtonText()
        return self.display
    
class EndScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        
        # Add a button to let the player return to the menu
        self.buttons = {
            'main menu': pygame.Rect(self.display.get_width() // 2 - 75, self.display.get_height() - 50, 150, 30)
        }
        
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left mouse button
                for action, rect in self.buttons.items():
                    if rect.collidepoint(self.mouse_pos):
                        if action == 'main menu':
                            self.game.switch_scene('main_menu')

    def render(self):
        # 1. Draw Background
        self.display.fill(self.background_color)
        
        # 2. Draw a dark UI panel for the stats to sit inside
        panel_width = 240
        panel_height = self.display.get_height() - 150
        panel_rect = pygame.Rect(self.display.get_width() // 2 - (panel_width // 2), 80, panel_width, panel_height)
        
        # Inner panel (dark blue/gray) and Border (light gray)
        pygame.draw.rect(self.display, (30, 40, 60), panel_rect, border_radius=10)
        pygame.draw.rect(self.display, (200, 200, 200), panel_rect, width=2, border_radius=10) 
        
        font = self.assets['font']
        title_font = self.assets['title_font']
        
        # 3. Draw Title
        title_surf = title_font.render("You Finished The Game!", False, (255, 215, 0)) # Gold color
        title_rect = title_surf.get_rect(center=(self.display.get_width() // 2, 45))
        self.display.blit(title_surf, title_rect)
        
        # 4. Draw Stats line by line
        start_y = 110
        line_spacing = 20
        
        if getattr(self.game, 'final_player_inventory', None) is not None:
            # Subtitle
            stat_title = font.render("- STATS -", False, (150, 150, 150))
            self.display.blit(stat_title, stat_title.get_rect(center=(self.display.get_width() // 2, start_y)))
            start_y += line_spacing + 5
            
            # Loop through items and draw them individually 
            for item, count in self.game.final_player_inventory.items():
                item_name = item.replace('_', ' ').title() # Cleans up "gold_keys" into "Gold Keys"
                text_surf = font.render(f"{item_name}: {count}", False, (255, 255, 255))
                text_rect = text_surf.get_rect(center=(self.display.get_width() // 2, start_y))
                self.display.blit(text_surf, text_rect)
                start_y += line_spacing
                
            # Calculate inventory item score points
            point_total = 0
            for item, count in self.game.final_player_inventory.items():
                if item == 'gems':
                    point_total += count
                elif item == 'gold_sack':
                    point_total += count * 5
            
            # 5. Calculate and Draw Time Bonus Breakdowns
            timer = getattr(self.game, 'timer', 999)
            time_bonus = 0
            if timer < 250:
                time_bonus = 50
            elif timer < 300:
                time_bonus = 30
            elif timer < 350:
                time_bonus = 10
            
            point_total += time_bonus
            
            start_y += 10 # Extra padding gap before time info
            
            # Render clear time
            time_surf = font.render(f"Clear Time: {int(timer)}s", False, (200, 200, 200))
            time_rect = time_surf.get_rect(center=(self.display.get_width() // 2, start_y))
            self.display.blit(time_surf, time_rect)
            start_y += line_spacing
            
            # Render specific time bonus text line (soft gold text)
            bonus_surf = font.render(f"Time Bonus: +{time_bonus}", False, (255, 240, 150))
            bonus_rect = bonus_surf.get_rect(center=(self.display.get_width() // 2, start_y))
            self.display.blit(bonus_surf, bonus_rect)
            start_y += line_spacing + 5
            
            # Highlight the total combined score in green
            score_surf = font.render(f"Total Score: {point_total}", False, (100, 255, 100)) 
            score_rect = score_surf.get_rect(center=(self.display.get_width() // 2, start_y))
            self.display.blit(score_surf, score_rect)
        
        # 6. Draw Main Menu Button
        for action, rect in self.buttons.items():
            # Button background
            pygame.draw.rect(self.display, (50, 150, 200), rect, border_radius=5) 
            
            # Button text
            btn_surf = font.render(action.title(), False, (255, 255, 255))
            btn_rect = btn_surf.get_rect(center=rect.center)
            self.display.blit(btn_surf, btn_rect)

        return self.display
    
class HowToPlayScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        
        # Simple back button at the bottom of the screen
        self.buttons = {
            'back': pygame.Rect(self.display.get_width() // 2 - 50, self.display.get_height() - 50, 100, 30)
        }
        
        # Here is where you can fill in your controls! 
        # Each string in this list will be rendered on a new line.
        self.instructions = [
            "Controls:",
            "Move - [Left and Right Arrow Keys]",
            "Jump - [Space, Up Arrow]",
            "Dash - [X]",
            "Interact - [Z]",
            "Reset Level - [R]",
            "Free Cam - [Tab]",
            "",
            "You also can double jump and double dash in mid air and wall slide and jump",
            "",
            "Objective:",
            "Collect keys and find the purple portal and finish all 5 levels!"

        ]

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left mouse button
                for action, rect in self.buttons.items():
                    if rect.collidepoint(self.mouse_pos):
                        if action == 'back':
                            self.game.switch_scene('main_menu')

    def getFont(self):
        return self.assets['font']

    def render(self):
        # 1. Draw Background
        self.display.fill(self.background_color)
        
        # 2. Draw Title
        title_surf = self.assets['title_font'].render("How to Play", False, (255, 255, 255))
        title_rect = title_surf.get_rect(center=(self.display.get_width() // 2, 40))
        self.display.blit(title_surf, title_rect)

        # 3. Draw Instructions
        font = self.getFont()
        start_y = 90
        line_spacing = 20
        
        for i, text in enumerate(self.instructions):
            text_surf = font.render(text, False, (255, 255, 255))
            text_rect = text_surf.get_rect(center=(self.display.get_width() // 2, start_y + (i * line_spacing)))
            self.display.blit(text_surf, text_rect)

        # 4. Draw Back Button
        for action, rect in self.buttons.items():
            # Optional: Draw a dark box behind the button text so it looks like a button
            pygame.draw.rect(self.display, (30, 100, 150), rect, border_radius=4) 
            
            text_surf = font.render(action.capitalize(), False, (255, 255, 255))
            text_rect = text_surf.get_rect(center=rect.center)
            self.display.blit(text_surf, text_rect)
        
        return self.display

        