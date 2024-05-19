import pygame
from os.path import join
from random import randint

# general setup
pygame.init()
WINDOW_WIDTH, WINDOW_HEIGHT = 1280, 720
diplay_surface = pygame.display.set_mode((WINDOW_WIDTH,WINDOW_HEIGHT))
pygame.display.set_caption('Space Shooter')
running = True
clock = pygame.time.Clock()

# surface
surf = pygame.Surface((100,200))
surf.fill('orange')
x = 100

# imports
player_surf = pygame.image.load(join('images', 'player.png')).convert_alpha()
player_rect = player_surf.get_frect(center = (WINDOW_WIDTH/2, WINDOW_HEIGHT/2))
player_direction = pygame.math.Vector2(0,0)
player_speed = 300

star_surf = pygame.image.load(join('images', 'star.png')).convert_alpha()
star_postitions = [(randint(0, WINDOW_WIDTH),randint(0, WINDOW_HEIGHT)) for i in range(20)]

meteor_surf = pygame.image.load(join('images', 'meteor.png')).convert_alpha()
meteor_rect = meteor_surf.get_frect(center =  (WINDOW_WIDTH/2, WINDOW_HEIGHT/2))

laser_surf = pygame.image.load(join('images', 'laser.png')).convert_alpha()
laser_rect = laser_surf.get_frect(bottomleft =  (20, WINDOW_HEIGHT - 20))



while running:
    # frame rate using dt -- delta time. converted to milliseconds
    dt = clock.tick()/ 1000
    # event loop
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        # if event.type == pygame.KEYDOWN and event.key == pygame.K_1:
        #     print(1)
        # if event.type == pygame.MOUSEMOTION:
        #     player_rect.center = event.pos
            
            
    # input
    keys = pygame.key.get_pressed()
    player_direction.x = int(keys[pygame.K_RIGHT]) - int(keys[pygame.K_LEFT])
    player_direction.y = int(keys[pygame.K_DOWN]) - int(keys[pygame.K_UP])

    # normalize player vector for equal movement speed when multiple direction keys are pressed. 
    player_direction = player_direction.normalize() if player_direction else player_direction
    player_rect.center += player_direction * player_speed * dt
        
    # draw game
    diplay_surface.fill('darkgray')
    for pos in star_postitions:
        diplay_surface.blit(star_surf,pos )  
        
        
    # attaches surf to display_surface at (x,y). 
    diplay_surface.blit(meteor_surf, meteor_rect)
    diplay_surface.blit(laser_surf,laser_rect)
        
    # player movement

    diplay_surface.blit(player_surf, player_rect)
        
    pygame.display.update()
    
pygame.quit()