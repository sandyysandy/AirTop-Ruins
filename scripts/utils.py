import os
import pygame

BASE_IMAGE_PATH = 'assets/images/'
BASE_PATH = 'assets/'

def load_image(path):
    img = pygame.image.load(BASE_IMAGE_PATH + path + '.png').convert()
    img.set_colorkey((0,0,0))
    return img

def load_image_transparent(path):
    return pygame.image.load(BASE_IMAGE_PATH + path + '.png').convert_alpha()

def load_images(path):
    images = []
    for img_name in os.listdir(BASE_IMAGE_PATH + path):
        images.append(load_image(path + '/' + img_name.split('.')[0]))
    return images

def load_tile_atlas_transparent(path, num_tiles, tile_size=16,):
    atlas_img = load_image_transparent(f"tiles/{path}")
    images = []
    
    for i in range(num_tiles):
        row = i % 5    # Slices downward (0, 1, 2, 3, 4)
        col = i // 5   # Shifts to the next column every 5 tiles
        
        x = col * tile_size
        y = row * tile_size
        
        # Carve out the sub-surface for this tile variant
        tile_surf = atlas_img.subsurface(pygame.Rect(x, y, tile_size, tile_size))
        images.append(tile_surf)
        
    return images

def load_tile_atlas(path, num_tiles, tile_size=16,):
    atlas_img = load_image(f"tiles/{path}")
    images = []
    
    for i in range(num_tiles):
        row = i % 5    # Slices downward (0, 1, 2, 3, 4)
        col = i // 5   # Shifts to the next column every 5 tiles
        
        x = col * tile_size
        y = row * tile_size
        
        # Carve out the sub-surface for this tile variant
        tile_surf = atlas_img.subsurface(pygame.Rect(x, y, tile_size, tile_size))
        images.append(tile_surf)
        
    return images

def load_images_sorted(path):
    images = []
    # Get the list of filenames
    file_list = os.listdir(BASE_IMAGE_PATH + path)
    
    # Sort the files numerically by converting the filename (minus extension) into an integer
    file_list.sort(key=lambda x: int(x.split('.')[0]))
    
    for img_name in file_list:
        images.append(load_image(path + '/' + img_name.split('.')[0]))
    return images

def load_font(path, size):
    return pygame.font.Font(BASE_PATH + path, size)

class Object:
    def __init__(self, scene, o_type, pos, size):
        self.scene = scene
        self.type = o_type
        self.pos = pos
        self.size = size

    def rect(self):
        return pygame.Rect(self.pos[0], self.pos[1], self.size[0], self.size[1])