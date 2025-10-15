import pygame
from os.path import join
from random import randint, uniform

# ======================
# Init / Window
# ======================
pygame.init()
WINDOW_WIDTH, WINDOW_HEIGHT = 1280, 720
display_surface = pygame.display.set_mode(
    (WINDOW_WIDTH, WINDOW_HEIGHT),
    pygame.HWSURFACE | pygame.DOUBLEBUF  # small perf boost
)
pygame.display.set_caption("Space Shooter")
clock = pygame.time.Clock()

# game states
STATE_PLAYING = "playing"
STATE_GAME_OVER = "game_over"
STATE_WIN = "win"
game_state = STATE_PLAYING
running = True

# win target (matches your score units: pygame time // 100)
SCORE_TO_WIN = 300

# ======================
# Assets
# ======================
star_surf = pygame.image.load(join("images", "star.png")).convert_alpha()
meteor_surf = pygame.image.load(join("images", "meteor.png")).convert_alpha()
laser_surf = pygame.image.load(join("images", "laser.png")).convert_alpha()
player_surf = pygame.image.load(join("images", "player.png")).convert_alpha()

font = pygame.font.Font(join("images", "Oxanium-Bold.ttf"), 40)
small_font = pygame.font.Font(join("images", "Oxanium-Bold.ttf"), 26)

explosion_frames = [
    pygame.image.load(join("images", "explosion", f"{i}.png")).convert_alpha()
    for i in range(21)
]

laser_sound = pygame.mixer.Sound(join("audio", "laser.wav"))
laser_sound.set_volume(0.3)
explosion_sound = pygame.mixer.Sound(join("audio", "explosion.wav"))
explosion_sound.set_volume(0.3)
game_music = pygame.mixer.Sound(join("audio", "game_music.wav"))
game_music.set_volume(0.2)
game_music.play(loops=-1)

# ======================
# Rotation Cache (perf)
# ======================
ROT_STEP_DEG = 5
_METEOR_CACHE = {}  # idx -> (surf, mask)

def get_meteor_frame(base_surf: pygame.Surface, angle_deg: float):
    """Return cached (surface, mask) for quantized angle."""
    steps = 360 // ROT_STEP_DEG
    idx = int(angle_deg // ROT_STEP_DEG) % steps
    cached = _METEOR_CACHE.get(idx)
    if cached is None:
        quant_angle = idx * ROT_STEP_DEG
        rot_surf = pygame.transform.rotozoom(base_surf, quant_angle, 1)
        rot_mask = pygame.mask.from_surface(rot_surf)
        cached = (rot_surf, rot_mask)
        _METEOR_CACHE[idx] = cached
    return cached

# ======================
# Sprites
# ======================
class Player(pygame.sprite.Sprite):
    def __init__(self, groups):
        super().__init__(groups)
        self.image = player_surf
        self.rect = self.image.get_rect(center=(WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2))
        self.direction = pygame.Vector2()
        self.speed = 300
        self.can_shoot = True
        self.laser_shoot_time = 0
        self.cooldown_duration = 400  # ms
        self.mask = pygame.mask.from_surface(self.image)

        # win animation helpers
        self.win_boosting = False
        self.win_boost_speed = -1400  # pixels/sec upward

    def _laser_timer(self):
        if not self.can_shoot:
            if pygame.time.get_ticks() - self.laser_shoot_time >= self.cooldown_duration:
                self.can_shoot = True

    def update(self, dt):
        # During win animation we control the ship; ignore inputs
        if game_state == STATE_WIN:
            if not self.win_boosting:
                # move toward center smoothly
                target = pygame.Vector2(WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2)
                pos = pygame.Vector2(self.rect.center)
                to_center = target - pos
                dist = to_center.length()
                if dist > 2:
                    # ease-in speed
                    step = to_center.normalize() * 500 * dt
                    if step.length() > dist:
                        step.scale_to_length(dist)
                    pos += step
                    self.rect.center = (pos.x, pos.y)
                else:
                    # reached center -> start boost up
                    self.win_boosting = True
            else:
                # rocket upwards fast
                self.rect.centery += self.win_boost_speed * dt
            return

        # Normal play controls
        keys = pygame.key.get_pressed()
        self.direction.x = int(keys[pygame.K_RIGHT]) - int(keys[pygame.K_LEFT])
        self.direction.y = int(keys[pygame.K_DOWN]) - int(keys[pygame.K_UP])
        if self.direction.length_squared() > 0:
            self.direction = self.direction.normalize()
        self.rect.centerx += self.direction.x * self.speed * dt
        self.rect.centery += self.direction.y * self.speed * dt
        self.rect.clamp_ip(pygame.Rect(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT))

        # shooting (edge-trigger simulated with get_pressed is okay here)
        just = pygame.key.get_pressed()
        if just[pygame.K_SPACE] and self.can_shoot:
            Laser(laser_surf, self.rect.midtop, (all_sprites, laser_sprites))
            self.can_shoot = False
            self.laser_shoot_time = pygame.time.get_ticks()
            laser_sound.play()

        self._laser_timer()


class Star(pygame.sprite.Sprite):
    def __init__(self, group, surf):
        super().__init__(group)
        self.image = surf
        self.rect = self.image.get_rect(
            center=(randint(0, WINDOW_WIDTH), randint(0, WINDOW_HEIGHT))
        )


class Laser(pygame.sprite.Sprite):
    def __init__(self, surf, pos, groups):
        super().__init__(groups)
        self.image = surf
        self.rect = self.image.get_rect(midbottom=pos)
        self.speed = 500

    def update(self, dt):
        self.rect.centery -= self.speed * dt
        if self.rect.bottom < 0:
            self.kill()


class Meteor(pygame.sprite.Sprite):
    def __init__(self, surf, pos, groups):
        super().__init__(groups)
        self.base_surface = surf

        # start with a cached frame
        self.image, self.mask = get_meteor_frame(self.base_surface, 0)
        self.rect = self.image.get_rect(center=pos)

        # motion
        self.start_time = pygame.time.get_ticks()
        self.lifetime = 2000  # ms
        self.direction = pygame.Vector2(uniform(-0.5, 0.5), 1)
        if self.direction.length_squared() == 0:
            self.direction.y = 1
        self.direction = self.direction.normalize()
        self.speed = randint(400, 500)

        # rotation
        self.rotation = 0.0
        self.rotation_speed = randint(40, 80)  # deg/s

    def update(self, dt):
        # stop meteors moving during win screen (so scene freezes while ship exits)
        if game_state == STATE_WIN:
            return

        # movement
        self.rect.centerx += self.direction.x * self.speed * dt
        self.rect.centery += self.direction.y * self.speed * dt

        # lifetime
        if pygame.time.get_ticks() - self.start_time > self.lifetime:
            self.kill()
            return

        # rotation via cache
        self.rotation = (self.rotation + self.rotation_speed * dt) % 360
        new_img, new_mask = get_meteor_frame(self.base_surface, self.rotation)
        center = self.rect.center
        self.image = new_img
        self.mask = new_mask
        self.rect = self.image.get_rect(center=center)


class AnimatedExplosion(pygame.sprite.Sprite):
    def __init__(self, frames, pos, groups):
        super().__init__(groups)
        self.frames = frames
        self.frame_index = 0.0
        self.speed = 20  # fps (scaled by dt)
        self.image = self.frames[0]
        self.rect = self.image.get_rect(center=pos)

    def update(self, dt):
        self.frame_index += self.speed * dt
        if self.frame_index < len(self.frames):
            center = self.rect.center
            self.image = self.frames[int(self.frame_index)]
            self.rect = self.image.get_rect(center=center)
        else:
            self.kill()

# ======================
# Game Functions & State
# ======================
def set_game_over():
    """Switch to GAME_OVER state."""
    global game_state
    game_state = STATE_GAME_OVER

def set_win():
    """Switch to WIN state and prep player animation."""
    global game_state
    game_state = STATE_WIN
    player.win_boosting = False  # start with move-to-center

def reset_game():
    """Reset all entities and timers and return to PLAYING state."""
    global all_sprites, meteor_sprites, laser_sprites, player, game_state, game_start_ms

    # clear groups
    all_sprites.empty()
    meteor_sprites.empty()
    laser_sprites.empty()

    # rebuild stars
    for _ in range(20):
        Star(all_sprites, star_surf)

    # new player
    player = Player(all_sprites)

    # reset score timebase
    game_start_ms = pygame.time.get_ticks()

    # back to playing
    game_state = STATE_PLAYING

def collisions():
    # skip collisions once you’ve won
    if game_state != STATE_PLAYING:
        return

    # player vs meteors (mask collide)
    if pygame.sprite.spritecollide(player, meteor_sprites, True, pygame.sprite.collide_mask):
        set_game_over()

    # lasers vs meteors (rect is fine & faster)
    for laser in laser_sprites.sprites():
        hit = pygame.sprite.spritecollide(laser, meteor_sprites, True)
        if hit:
            laser.kill()
            AnimatedExplosion(explosion_frames, laser.rect.midtop, all_sprites)
            explosion_sound.play()

def get_score_value():
    """Return the integer score (time survived scaled the same way as before)."""
    return (pygame.time.get_ticks() - game_start_ms) // 100

def draw_score_top_left():
    score_val = get_score_value()
    text = small_font.render(f"Score: {score_val}", True, (240, 240, 240))
    rect = text.get_rect(topleft=(16, 14))
    # subtle box
    pygame.draw.rect(display_surface, (240, 240, 240), rect.inflate(16, 10), width=2, border_radius=8)
    display_surface.blit(text, rect)
    return score_val

def draw_death_screen(final_score):
    # dark overlay
    overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 170))
    display_surface.blit(overlay, (0, 0))

    title = font.render("YOU DIED", True, (255, 90, 90))
    score_txt = small_font.render(f"Score: {final_score}", True, (230, 230, 230))
    retry_txt = small_font.render("Press R to Retry   •   ESC to Quit", True, (220, 220, 220))

    display_surface.blit(title, title.get_rect(center=(WINDOW_WIDTH/2, WINDOW_HEIGHT/2 - 40)))
    display_surface.blit(score_txt, score_txt.get_rect(center=(WINDOW_WIDTH/2, WINDOW_HEIGHT/2 + 10)))
    display_surface.blit(retry_txt, retry_txt.get_rect(center=(WINDOW_WIDTH/2, WINDOW_HEIGHT/2 + 60)))

def draw_win_screen(final_score):
    # subtle overlay while ship exits
    overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 20, 40, 120))
    display_surface.blit(overlay, (0, 0))

    title = font.render("YOU WIN!", True, (120, 255, 160))
    score_txt = small_font.render(f"Final Score: {final_score}", True, (230, 255, 230))
    retry_txt = small_font.render("Press R to Play Again   •   ESC to Quit", True, (220, 230, 220))

    display_surface.blit(title, title.get_rect(center=(WINDOW_WIDTH/2, WINDOW_HEIGHT/2 - 40)))
    display_surface.blit(score_txt, score_txt.get_rect(center=(WINDOW_WIDTH/2, WINDOW_HEIGHT/2 + 10)))
    display_surface.blit(retry_txt, retry_txt.get_rect(center=(WINDOW_WIDTH/2, WINDOW_HEIGHT/2 + 60)))

# ======================
# Groups & Entities
# ======================
all_sprites = pygame.sprite.Group()
meteor_sprites = pygame.sprite.Group()
laser_sprites = pygame.sprite.Group()

for _ in range(20):
    Star(all_sprites, star_surf)

player = Player(all_sprites)

# custom event - meteor spawn
meteor_event = pygame.event.custom_type()
pygame.time.set_timer(meteor_event, 500)

# cap meteors to avoid runaway cost
MAX_METEORS = 30

# score base time
game_start_ms = pygame.time.get_ticks()
final_score_cache = 0  # remember score shown on end screens

# ======================
# Main Loop
# ======================
while running:
    dt = clock.tick(120) / 1000  # aim up to 120 FPS if possible

    # events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # spawn meteors only during PLAYING
        if game_state == STATE_PLAYING and event.type == meteor_event and len(meteor_sprites) < MAX_METEORS:
            x, y = randint(0, WINDOW_WIDTH), randint(-200, -100)
            Meteor(meteor_surf, (x, y), (all_sprites, meteor_sprites))

        # end-screen inputs
        if (game_state in (STATE_GAME_OVER, STATE_WIN)) and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                reset_game()
            if event.key == pygame.K_ESCAPE:
                running = False

    # update & collisions
    all_sprites.update(dt)
    collisions()

    # win check (only from active play)
    if game_state == STATE_PLAYING:
        current_score = get_score_value()
        final_score_cache = current_score
        if current_score >= SCORE_TO_WIN:
            # stop meteors from spawning further
            set_win()

    # draw
    display_surface.fill("#3a2e3f")
    all_sprites.draw(display_surface)

    # score always shown top-left during play; frozen on end screens
    if game_state == STATE_PLAYING:
        draw_score_top_left()
    elif game_state == STATE_GAME_OVER:
        # freeze scene and draw the death overlay with last score
        draw_score_top_left()  # still show score box
        draw_death_screen(final_score_cache)
    else:  # STATE_WIN
        draw_score_top_left()
        draw_win_screen(final_score_cache)

    pygame.display.update()

pygame.quit()
