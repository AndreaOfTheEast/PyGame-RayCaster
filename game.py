import pygame
import math

DEBUG_SIZE = 32
DEBUG = False

class Map:
    def __init__(self, map: list[int], size: int):
        self.map =      map
        self.size =     size

    def debug_draw(self, surface: pygame.Surface):
        for y in range(self.size):
            for x in range(self.size):
                colour = pygame.Color(30, 30, 30, 255)
                if self.map[x + y * self.size] == 1:
                    colour = pygame.Color(255, 255, 255, 255)

                pygame.draw.rect(surface, colour, pygame.Rect(
                    x * DEBUG_SIZE, y * DEBUG_SIZE, 
                    DEBUG_SIZE - 1, DEBUG_SIZE - 1)
                    )

    def index_in_bounds(self, p: int) -> bool:
        if (p >= 0 or p < self.size * self.size):
            return True
        return False

    def check_collide(self, x: int, y: int) -> bool:
        p = round(x + y * self.size)
        if (p < 0 or p >= self.size * self.size):
            raise(ValueError(f"{p} is outside of map range."))
        return (self.map[round(x + y * self.size)] != 0)

class Ray:
    def __init__(self):
        self.distance = 0.0
        self.side = 0
        self.tex_x = 0

class RayCaster:
    def __init__(self, map: Map):
        self.map = map

    def cast_ray(self, surface, position: pygame.Vector2, angle: float) -> Ray:
        start = position.copy()
        end = position.copy()

        max_length = 10
        ray_direction = (pygame.Vector2(math.cos(angle) * max_length, math.sin(angle) * max_length)).normalize()
        ray_unit_step_size = pygame.Vector2(
            math.sqrt(1 + (ray_direction.y / ray_direction.x) * (ray_direction.y / ray_direction.x)),
            math.sqrt(1 + (ray_direction.x / ray_direction.y) * (ray_direction.x / ray_direction.y))
        )

        ray_length = pygame.Vector2(0, 0)
        map_check = start.copy()
        map_check.x = math.floor(map_check.x)
        map_check.y = math.floor(map_check.y)
                
        step = pygame.Vector2()

        if (ray_direction.x < 0):
            step.x = -1
            ray_length.x = (start.x - map_check.x) * ray_unit_step_size.x
        else:
            step.x = 1
            ray_length.x = ((map_check.x + 1) - start.x) * ray_unit_step_size.x

        if (ray_direction.y < 0):
            step.y = -1
            ray_length.y = (start.y - map_check.y) * ray_unit_step_size.y
        else:
            step.y = 1  
            ray_length.y = ((map_check.y + 1) - start.y) * ray_unit_step_size.y  

        found_tile = False 
        max_distance = 1000
        distance = 0.0
        side = 0

        while (not found_tile and distance < max_distance):
            if ray_length.x < ray_length.y:
                map_check.x += step.x 
                distance = ray_length.x
                ray_length.x += ray_unit_step_size.x
                side = 0
            else:
                map_check.y += step.y 
                distance = ray_length.y
                ray_length.y += ray_unit_step_size.y
                side = 1

            tile = map_check.x + map_check.y * self.map.size

            if self.map.index_in_bounds(tile):
                if self.map.check_collide(map_check.x, map_check.y) != 0:
                    found_tile = True

        end = start + ray_direction * distance

        if DEBUG:
            pygame.draw.line(
                surface, (0, 255, 255, 255), 
                (start * DEBUG_SIZE), 
                (end * DEBUG_SIZE),
                2
                )

        ray = Ray()
        ray.distance = start.distance_to(end)
        ray.side = side
        if side == 0:
            ray.tex_x = end.y - int(end.y)
        else:
            ray.tex_x = end.x - int(end.x)
        return ray

class Player:
    def __init__(self, game: Game):
        self.position = pygame.Vector2(1.5, 1.5)
        self.speed = 3
        self.direction = 0.00001
        self.turn_speed = 1

        self.game = game
        self.ray_caster = RayCaster(game.map)
        self.fov = 45
        self.resolution = round(game.window_dimensions.x)

    def debug_draw(self, surface: pygame.Surface):
        pygame.draw.circle(surface, (25, 125, 255, 255), (self.position.x * DEBUG_SIZE, self.position.y * DEBUG_SIZE), 4)
        pygame.draw.line(
            surface, (0, 255, 0, 255), 
            (self.position * DEBUG_SIZE), 
            (pygame.Vector2(self.position.x + math.cos(self.direction), self.position.y + math.sin(self.direction)) * DEBUG_SIZE)
            )

    def draw_world(self):
        angle_start = self.direction - math.radians(self.fov / 2)
        angle_step = math.radians(self.fov) / self.resolution

        window_mid = self.game.window_dimensions.y / 2
        wall_size = self.game.window_dimensions.y * 1.5

        for i in range(self.resolution):
            ray_angle = angle_start + (angle_step * i)
            ray = self.ray_caster.cast_ray(self.game.window, self.position, ray_angle)
            length = ray.distance * math.cos(ray_angle - self.direction)

            true_size = wall_size / length

            # Avoid pathologically huge scale targets when extremely close to a wall
            max_scale_height = self.game.window_dimensions.y * 4
            scale_height = min(true_size, max_scale_height)

            screen_top = window_mid - true_size / 2
            screen_bottom = window_mid + true_size / 2

            visible_top = max(0, screen_top)
            visible_bottom = min(self.game.window_dimensions.y, screen_bottom)
            visible_height = visible_bottom - visible_top

            if visible_height <= 0:
                continue

            tex_column = self.game.image.subsurface(
                (ray.tex_x * self.game.image.width, 0, 1, self.game.image.height)
            )

            # Scale to the FULL (unclamped) height — no texture-space cropping
            scaled_column = pygame.transform.scale(tex_column, (1, round(scale_height)))

            # Crop happens here, in screen-pixel space, post-scale — precise, no rounding drift
            area_top = visible_top - screen_top
            area = pygame.Rect(0, round(area_top), 1, round(visible_height))

            self.game.window.blit(scaled_column, (i, visible_top), area=area)

    def update(self):
        keys = pygame.key.get_pressed()
        move_turn = 0
        move = 0
        if keys[pygame.K_w]:
            move = 1
        if keys[pygame.K_s]:
            move = -1
        if keys[pygame.K_a]:
            move_turn = -1
        if keys[pygame.K_d]:
            move_turn = 1

        self.direction += move_turn * self.turn_speed * self.game.dt

        move_x = move * math.cos(self.direction) * self.game.dt * self.speed * 1
        if (self.game.map.check_collide(math.floor(self.position.x + move_x), math.floor(self.position.y))):
            move_x = 0
        self.position.x += move_x

        move_y = move * math.sin(self.direction) * self.game.dt * self.speed * 1
        if (self.game.map.check_collide(math.floor(self.position.x), math.floor(self.position.y + move_y))):
            move_y = 0
        self.position.y += move_y

        if self.direction > 2 * math.pi:
            self.direction -= 2 * math.pi
        if self.direction < 0:
            self.direction += 2 * math.pi

class Game:
    def __init__(self):
        pygame.init()
        self.window_dimensions = pygame.Vector2(1280, 960) 
        self.window = pygame.display.set_mode(self.window_dimensions)
        self.clock = pygame.time.Clock()
        self.running = True

        self.fps = 60
        self.dt = 0

        self.map = Map([
            1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
            1, 0, 0, 0, 1, 0, 1, 0, 0, 1,
            1, 0, 1, 0, 1, 0, 1, 0, 0, 1,
            1, 0, 0, 0, 1, 0, 0, 0, 0, 1,
            1, 0, 0, 0, 1, 0, 0, 0, 0, 1,
            1, 1, 0, 1, 1, 1, 1, 0, 1, 1,
            1, 0, 0, 0, 1, 0, 0, 0, 0, 1,
            1, 0, 0, 0, 0, 0, 0, 0, 0, 1,
            1, 0, 0, 0, 1, 0, 0, 0, 0, 1,
            1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
        ], size=10)

        self.player = Player(self)
        self.image = pygame.image.load("assets/bricks.png").convert()

    def update(self):
        self.player.update()

    def draw(self):
        self.window.fill((255, 0, 0, 255)) 
        if DEBUG:
            self.map.debug_draw(self.window)
            self.player.debug_draw(self.window)

        self.player.draw_world()
        pygame.display.flip()

    def process(self):
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

            self.update()
            self.draw()

            self.dt = self.clock.tick(self.fps) / 1000

def main():
    game = Game()
    game.process()
    
if __name__ == "__main__":
    main()