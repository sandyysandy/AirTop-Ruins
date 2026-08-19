import os

import pygame
import sys

from scripts.scenes import EndScene, GameScene, EditorScene, HowToPlayScene, MainMenuScene
from scripts.utils import load_font, load_image , load_images, load_tile_atlas, load_images_sorted, load_tile_atlas_transparent


# TODO: Add a portal to get to the next level. and a way to activate it, Trap door, Button, Lever, etc.

# Stops window scaling. 
if os.name == 'nt': # Only run if the OS is Windows
    import ctypes
    try:
        # 2 = PROCESS_PER_MONITOR_DPI_AWARE
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass

class Game:
    def __init__(self, screen_width, screen_height):
        pygame.init()

        pygame.display.set_caption('AirTop Ruins')
        # Fixed internal game resolution
        self.game_width = 320*2
        self.game_height = 200*2
        
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.screen = pygame.display.set_mode((screen_width, screen_height), pygame.NOFRAME)
        self.clock = pygame.time.Clock()
        self.timer = 0
        self.new_game_plus = False
        self.grappling_hook_enabled = False

        self.tiles = {
            'items': load_tile_atlas_transparent('items', 5),
            'interactables': load_tile_atlas_transparent('interactables', 4),
            'grass': load_tile_atlas('grass', 11),
            'stone': load_tile_atlas('stone', 9),
            'decor': load_tile_atlas('decor', 4),
            'large_decor': load_images_sorted('tiles/large_decor'),
            'spawn': load_images('spawn')
        }

        self.assets = {
            'tiles': self.tiles,
            'player': load_image('entities/player'),
            'clouds': load_images('clouds'),
            'font': load_font('Minecraft.ttf', 16),
            'ingame_font': load_font('Pix32.ttf', 12),
            'title_font': load_font('Robot Crush.ttf', 45),
            'background_front': load_image('Background_1'),
            'background_back': load_image('Background_2')
        }

        self.scenes = {
            'main_menu': MainMenuScene(self),
            'game': GameScene(self),
            'editor': EditorScene(self),
            'end_scene': EndScene(self),
            'how_to_play': HowToPlayScene(self)
        }

        self.level_count = 5
        self.final_player_inventory = None
        self.current_scene = self.scenes['main_menu']
        self.current_time = pygame.time.get_ticks()


    def switch_scene(self, scene_key):
        if self.current_scene == self.scenes['game']:
            self.current_scene.player.death()
        else:
            self.current_scene.reset()
        self.current_scene = self.scenes[scene_key]

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                
                # Toggle between Game and Editor
                if event.type == pygame.KEYUP:
                    if event.key == pygame.K_ESCAPE and self.current_scene == self.scenes['main_menu']:
                        pygame.event.post(pygame.event.Event(pygame.QUIT))
                    elif event.key == pygame.K_ESCAPE:
                        self.switch_scene('main_menu')


                self.current_scene.handle_event(event)
            
            if not self.new_game_plus:
                self.grappling_hook_enabled = False 

            self.current_time = pygame.time.get_ticks()
            self.current_scene.update()
            
            # Render the scene to its own display surface, then scale to screen
            render_surf = self.current_scene.render()
            scaled_display = pygame.transform.scale(render_surf, (self.screen_width, self.screen_height))
            self.screen.blit(scaled_display, (0, 0))

            pygame.display.update()
            self.clock.tick(60)

Game(1920, 1200).run()