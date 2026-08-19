import json
import pygame

from scripts.interactables import INTERACTABLE_TYPES, Interactable
from scripts.items import Item

AUTOTILE_MAP = {
    # Cardinal Rules
    tuple(sorted([(1, 0), (0, 1)])): 0,
    tuple(sorted([(1, 0), (0, 1), (-1, 0)])): 1,
    tuple(sorted([(-1, 0), (0, 1)])): 2, 
    tuple(sorted([(-1, 0), (0, -1), (0, 1)])): 3,
    tuple(sorted([(-1, 0), (0, -1)])): 4,
    tuple(sorted([(-1, 0), (0, -1), (1, 0)])): 5,
    tuple(sorted([(1, 0), (0, -1)])): 6,
    tuple(sorted([(1, 0), (0, -1), (0, 1)])): 7,
    tuple(sorted([(1, 0), (-1, 0), (0, 1), (0, -1)])): 8,
}

NEIGHBOR_OFFSETS = [(-1, 0), (-1, -1), (0, -1), (1, -1), (1, 0), (0, 0), (-1, 1), (0, 1), (1, 1)]
PHYSICS_TILES = {'stone', 'grass'}
AUTOTILE_TYPES = {'stone', 'grass'}

class TileMap:
    def __init__(self, sprites, tile_size=16):
        self.sprites = sprites
        self.tile_size = tile_size
        self.tilemap = {}
        self.offgrid_tiles = []

    def find_items(self, scene):
        items = []

        for tile in self.offgrid_tiles.copy():
            if tile['type'] == 'items':
                pos = [tile['pos'][0], tile['pos'][1]]
                items.append(Item(scene, tile['variant'], pos))
                self.offgrid_tiles.remove(tile)

        for loc in list(self.tilemap.keys()):
            tile = self.tilemap[loc]

            if tile['type'] == 'items':
                pos = [tile['pos'][0] * self.tile_size, tile['pos'][1] * self.tile_size]
                items.append(Item(scene, tile['variant'], pos))
                del self.tilemap[loc]
        
        return items

    def find_interactables(self, scene):
        interactables = []

        for tile in self.offgrid_tiles.copy():
            if tile['type'] == 'interactables':
                pos = [tile['pos'][0], tile['pos'][1]]
                variant = tile['variant']
                interactable_class = INTERACTABLE_TYPES.get(variant, Interactable)
                interactables.append(interactable_class(scene, variant, pos))
                self.offgrid_tiles.remove(tile)

        for loc in list(self.tilemap.keys()):
            tile = self.tilemap[loc]

            if tile['type'] == 'interactables':
                pos = [tile['pos'][0] * self.tile_size, tile['pos'][1] * self.tile_size]
                variant = tile['variant']
                interactable_class = INTERACTABLE_TYPES.get(variant, Interactable)
                interactables.append(interactable_class(scene, variant, pos))
                del self.tilemap[loc]
        
        return interactables

    def find_spawn_point(self):

        for tile in self.offgrid_tiles.copy():
            if tile['type'] == 'spawn' and tile['variant'] == 0:
                spawn_pos = tile['pos'].copy()
                self.offgrid_tiles.remove(tile) # Delete it right away
                return spawn_pos
                
        for loc in list(self.tilemap.keys()):
            tile = self.tilemap[loc]
            if tile['type'] == 'spawn' and tile['variant'] == 0:
                spawn_pos = [
                    tile['pos'][0] * self.tile_size,
                    tile['pos'][1] * self.tile_size
                ]
                del self.tilemap[loc]
                return spawn_pos
            
        return None
    
    def tiles_around(self, pos):
        tiles = []
        tile_loc = (int(pos[0] // self.tile_size), int(pos[1] // self.tile_size))
        for offset in NEIGHBOR_OFFSETS:
            check_loc = str(tile_loc[0] + offset[0]) + ';' + str(tile_loc[1] + offset[1])
            if check_loc in self.tilemap:             
                tiles.append(self.tilemap[check_loc])
        return tiles
    
    def save(self, path):
        f = open(path, 'w')
        json.dump({'tilemap': self.tilemap, 'tile_size': self.tile_size, 'offgrid_tiles': self.offgrid_tiles}, f)
        f.close()

    def load(self, path):
        f = open(path, 'r')
        data = json.load(f)
        f.close()

        self.tilemap = data['tilemap']
        self.tile_size = data['tile_size']
        self.offgrid_tiles = data['offgrid_tiles']

    def is_solid_tile(self, pos):
        tile_loc = (int(pos[0] // self.tile_size), int(pos[1] // self.tile_size))
        check_loc = str(tile_loc[0]) + ';' + str(tile_loc[1])
        if check_loc in self.tilemap:
            return self.tilemap[check_loc]['type'] in PHYSICS_TILES
        return False

    def autotile(self, start_pos=None):
        tiles_to_update = set()
        
        if start_pos is None:
            # FallBack when no start position is specified, update everything
            tiles_to_update = set(self.tilemap)
        else:
            start_loc = f"{start_pos[0]};{start_pos[1]}"
            if start_loc in self.tilemap:
                target_type = self.tilemap[start_loc]['type']
                
                # Flood fill (BFS) to discover the connected group/island of the same tile type
                queue = [start_pos]
                visited = {start_loc}
                
                while queue:
                    curr_pos = queue.pop(0)
                    curr_loc = f"{curr_pos[0]};{curr_pos[1]}"
                    tiles_to_update.add(curr_loc)
                    
                    # Check all 8 neighboring directions to trace the island boundaries
                    for offset in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, -1), (-1, 1), (1, 1)]:
                        next_pos = (curr_pos[0] + offset[0], curr_pos[1] + offset[1])
                        next_loc = f"{next_pos[0]};{next_pos[1]}"
                        
                        if next_loc in self.tilemap and next_loc not in visited:
                            if self.tilemap[next_loc]['type'] == target_type:
                                visited.add(next_loc)
                                queue.append(next_pos)
            else:
                print("Autotile start position is not a valid tile.")
                return

        # Process autotiling ONLY for the filtered subset of tiles
        for loc in tiles_to_update:
            tile = self.tilemap[loc]
            neighbors = set()
            for shift in [(1, 0), (-1, 0), (0, -1), (0, 1)]:
                check_loc = str(tile['pos'][0] + shift[0]) + ';' + str(tile['pos'][1] + shift[1])
                if check_loc in self.tilemap:
                    if self.tilemap[check_loc]['type'] == tile['type']:
                        neighbors.add(shift)
            neighbors = tuple(sorted(neighbors))
            
            if (tile['type'] in AUTOTILE_TYPES) and (neighbors in AUTOTILE_MAP):
                tile['variant'] = AUTOTILE_MAP[neighbors]
                
                # Check for internal corners if surrounded on all 4 cardinal directions
                if neighbors == ((-1, 0), (0, -1), (0, 1), (1, 0)):
                    tl_loc = f"{tile['pos'][0] - 1};{tile['pos'][1] - 1}"
                    tr_loc = f"{tile['pos'][0] + 1};{tile['pos'][1] - 1}"
                    
                    tl_exists = tl_loc in self.tilemap and self.tilemap[tl_loc]['type'] == tile['type']
                    tr_exists = tr_loc in self.tilemap and self.tilemap[tr_loc]['type'] == tile['type']
                    
                    # Look up how many loaded variant images exist for this specific tile type
                    available_variants = len(self.sprites[tile['type']])
                    
                    # Safely apply variant 9 or 10 only if they are within bounds of your sprite list
                    if not tl_exists and tr_exists and available_variants > 9:
                        tile['variant'] = 9
                    elif not tr_exists and tl_exists and available_variants > 10:
                        tile['variant'] = 10

    def physical_rect_around(self, pos):
        rects = []
        for tile in self.tiles_around(pos):
            if tile['type'] in PHYSICS_TILES:
                rects.append(pygame.Rect(tile['pos'][0] * self.tile_size, tile['pos'][1] * self.tile_size, self.tile_size, self.tile_size))
        return rects

    def render(self, surf, offset=(0,0)):

        for tile in self.offgrid_tiles:
            tile_type = tile['type']
            tile_variant = tile['variant']
            tile_pos = tile['pos']
            try:
                surf.blit(self.sprites[tile_type][tile_variant], (int(tile_pos[0] - offset[0]), int(tile_pos[1] - offset[1])))
            except IndexError:
                print(f"CRASH: Trying to load '{tile_type}' variant {tile_variant}.")
                print(f"You only have {len(self.sprites[tile_type])} sprites loaded for '{tile_type}'.")
            
        for x in range(int(offset[0]) // self.tile_size, (int(offset[0]) + surf.get_width()) // self.tile_size + 1):
            for y in range(int(offset[1]) // self.tile_size - 1, (int(offset[1]) + surf.get_height()) // self.tile_size + 1):
                tile_loc = str(x) + ';' + str(y)
                if tile_loc in self.tilemap:
                    tile = self.tilemap[tile_loc]
                    tile_type = tile['type']
                    tile_variant = tile['variant']
                    tile_pos = tile['pos']

                    surf.blit(self.sprites[tile_type][tile_variant], (int(tile_pos[0] * self.tile_size - offset[0]), int(tile_pos[1] * self.tile_size - offset[1])))