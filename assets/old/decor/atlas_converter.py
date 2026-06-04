import os
import pygame

def create_tile_atlas():
    # Initialize pygame display modules
    pygame.display.init()
    
    # Open a hidden 1x1 window to establish a pixel format context for .convert_alpha()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    
    # Get the directory where this script is saved
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Supported image formats
    valid_extensions = ('.png', '.jpg', '.jpeg', '.bmp')
    
    # Scan directory for images, ignoring any existing 'output.png'
    all_files = os.listdir(current_dir)
    image_files = [f for f in all_files if f.lower().endswith(valid_extensions) and f.lower() != 'output.png']
    
    if not image_files:
        print("No tile images found in this folder!")
        return

    # Sort files numerically by their number name (e.g., '10.png' comes after '9.png')
    try:
        image_files.sort(key=lambda x: int(os.path.splitext(x)[0]))
        print("Successfully sorted files numerically.")
    except ValueError:
        # Fallback to normal alphabetical sorting if filenames are not strictly integers
        image_files.sort()
        print("Filenames are not pure numbers; sorted alphabetically instead.")

    # Load the first image to automatically detect tile size (handles 16x16, 32x32, etc.)
    first_image_path = os.path.join(current_dir, image_files[0])
    first_tile = pygame.image.load(first_image_path)
    tile_w, tile_h = first_tile.get_size()
    print(f"Auto-detected tile dimensions: {tile_w}x{tile_h} pixels.")

    num_tiles = len(image_files)
    max_rows_vertical = 5
    
    # Math to figure out how many columns are needed
    cols = (num_tiles + max_rows_vertical - 1) // max_rows_vertical
    
    # Set final atlas dimensions
    atlas_width = cols * tile_w
    atlas_height = max_rows_vertical * tile_h if num_tiles >= max_rows_vertical else num_tiles * tile_h

    # Create the base atlas sheet surface and paint it pure black
    atlas_surface = pygame.Surface((atlas_width, atlas_height))
    atlas_surface.fill((0, 0, 0))

    print(f"Building atlas canvas: {cols} columns x {min(num_tiles, max_rows_vertical)} rows maximum...")

    # Blit each tile onto the sheet
    for index, filename in enumerate(image_files):
        row = index % max_rows_vertical   # Moves down down down (0, 1, 2, 3, 4)
        col = index // max_rows_vertical  # Jumps to the next column every 5th tile
        
        x_pos = col * tile_w
        y_pos = row * tile_h
        
        filepath = os.path.join(current_dir, filename)
        try:
            # .convert_alpha() will now work perfectly thanks to the hidden display context
            tile_surface = pygame.image.load(filepath).convert_alpha()
            atlas_surface.blit(tile_surface, (x_pos, y_pos))
            print(f" -> Positioned {filename} at Col: {col}, Row: {row}")
        except Exception as e:
            print(f"Error processing {filename}: {e}")

    # Export the completed sheet
    output_path = os.path.join(current_dir, 'output.png')
    pygame.image.save(atlas_surface, output_path)
    
    print("\n=============================================")
    print(f"Success! Processed {num_tiles} total images.")
    print(f"Generated Sheet Size: {atlas_width}x{atlas_height}")
    print(f"Saved atlas as: {output_path}")
    print("=============================================")

if __name__ == '__main__':
    create_tile_atlas()