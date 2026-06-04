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

        self.mouse_pos = (0, 0)    
    
    def load_level(self, map_id):
        self.tilemap.load(f'assets/maps/{map_id}.json')

    def reset(self):
        pass

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
            if event.key == pygame.K_LEFT:
                self.movement[0] = True
            if event.key == pygame.K_RIGHT:
                self.movement[1] = True
            if event.key == pygame.K_SPACE or event.key == pygame.K_UP:
                self.player.jump()
            if event.key == pygame.K_LSHIFT:
                self.player.sprint()
            if event.key == pygame.K_z:
                self.player.use()
            if event.key == pygame.K_x:
                self.player.dash()
            if event.key == pygame.K_r:
                self.player.death()
        if event.type == pygame.KEYUP:
            if event.key == pygame.K_LEFT:
                self.movement[0] = False
            if event.key == pygame.K_RIGHT:
                self.movement[1] = False
                
    def load_level(self, map_id):
        super().load_level(map_id)
        if self.level == 0:
            self.start_time = pygame.time.get_ticks()
        self.transition = -30
        self.player_spawn_pos = self.tilemap.find_spawn_point() or [100, 100]
        self.player.velocity = [0, 0]
        self.reset()

    def reset(self):
        # Move the player back to the saved spawn position whenever you reset
        self.player.pos = self.player_spawn_pos.copy()
        self.player.velocity = [0, 0]
            
        self.movement = [False, False]
        self.init_items()
        self.init_interactables()
    
    def next_level(self):
        self.level += 1
        if self.level >= self.game.level_count:
            self.level = 0
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
        self.scroll[0] += (player_rect.centerx - self.display.get_width() / 2 - self.scroll[0]) // 30
        self.scroll[1] += (player_rect.centery - self.display.get_height() / 2 - self.scroll[1]) // 30
        
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
        text_surf = font.render(f"Level: {self.level+1}", False, (0, 0, 0))
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
        self.render_hud()
        self.render_transition()
        return self.display

class EditorScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.movement = [False, False, False, False]

        self.tile_list = list(self.assets['tiles'])
        self.tile_sprites = self.assets['tiles']
        self.tile_group = 0
        self.tile_variant = 0

        self.clicking = False
        self.right_clicking = False
        self.shift = False
        self.ctrl = False
        self.alt = False
        self.ongrid = True

        self.current_tile_img = self.tile_sprites[self.tile_list[self.tile_group]][self.tile_variant].copy()
        self.tile_pos = (0, 0)

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
                    self.movement[0] = True
                if event.key == pygame.K_d:
                    self.movement[1] = True
                if event.key == pygame.K_w:
                    self.movement[2] = True
                if event.key == pygame.K_s:
                    self.movement[3] = True
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
                self.movement[0] = False
            if event.key == pygame.K_d:
                self.movement[1] = False
            if event.key == pygame.K_w:
                self.movement[2] = False
            if event.key == pygame.K_s:
                self.movement[3] = False
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


    def reset(self):
        self.movement = [False, False, False, False]


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
    
        # Scroll movement
        if self.shift:
            self.scroll[0] += (self.movement[1] - self.movement[0]) * 8
            self.scroll[1] += (self.movement[3] - self.movement[2]) * 8
        elif self.alt:
            self.scroll[0] += (self.tile_pos[0] * self.tilemap.tile_size - self.display.get_width() / 2 - self.scroll[0]) / 30
            self.scroll[1] += (self.tile_pos[1] * self.tilemap.tile_size - self.display.get_height() / 2 - self.scroll[1]) / 30
        else:
            self.scroll[0] += (self.movement[1] - self.movement[0]) * 5
            self.scroll[1] += (self.movement[3] - self.movement[2]) * 5


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
        text_surf = font.render(f"Level: {self.level+1}", False, (0, 0, 0))
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
            'play': pygame.Rect(220, 170, 200, 50),
            'editor': pygame.Rect(220, 240, 200, 50)
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

    def reset(self):
        pass

    def update(self):
        super().update()

    def renderButtonText(self):
        for action, rect in self.buttons.items():
            text_surf = self.getFont().render(action.capitalize(), False, (255, 255, 255))
            
            text_rect = text_surf.get_rect(center=rect.center)
            
            self.display.blit(text_surf, text_rect)

    def getFont(self):
        return self.assets['font']

    def render(self):
        self.display.fill(self.background_color)
        title_surf = self.assets['title_font'].render("airTop Ruins", False, (255, 255, 255))
        title_rect = title_surf.get_rect(center=(self.display.get_width() // 2, 110))
        self.display.blit(title_surf, title_rect)
        pygame.draw.rect(self.display, (255, 0, 0), self.buttons['play'])
        pygame.draw.rect(self.display, (0, 255, 0), self.buttons['editor'])
        self.renderButtonText()
        return self.display
    
class EndScene(Scene):
    def __init__(self, game):
        super().__init__(game)
    
    def handle_event(self, event):
        if event.type == pygame.KEYUP:
            if event.key == pygame.K_ESCAPE:
                self.game.switch_scene('main_menu')

    def reset(self):
        pass

    def update(self):
        super().update()

    def render(self):
        self.display.fill((0, 0, 0))
        font = self.assets['font']
        text_surf = font.render(f"Thanks for playing! Final Time: {self.game.timer}s", False, (255, 255, 255))
        text_rect = text_surf.get_rect(center=(self.display.get_width() // 2, self.display.get_height() // 2))
        self.display.blit(text_surf, text_rect)
        return self.display