# n'oubliez pas d'installer toutes les librairies que vous n'avez pas ! pip install [nom_de_la_librairie]
import asyncio
import time
import pygame
import myAuthTwitch
from twitchio.ext import commands
import pyaudio
import numpy as np
import os
import re


ton_token = myAuthTwitch.token
nom_de_ta_chaine = myAuthTwitch.name

# Pour changer les paramètres de l'écran
length = 640
height = 360
image_per_seconds = 60
radius_censor = 15

# Configuration de la bibliothèque pyaudio
p = pyaudio.PyAudio()
volume = 0.5
sample_rate = 44100
num_channels = 1
format_audio = pyaudio.paFloat32


class Pixel:
    def __init__(self, red, green, blue, x, y):
        self.red = red
        self.green = green
        self.blue = blue
        self.x = x if x >= 0 else 0 if x > length else length
        self.y = y if y >= 0 else 0 if y > height else height


class BotTwitch(commands.Bot):
    def __init__(self, screen):
        self.screen = screen
        super().__init__(token=ton_token, prefix='!', initial_channels=[nom_de_ta_chaine])

    async def event_ready(self):
        print(f'Logged in as | {self.nick} id : {self.user_id}')

    async def event_message(self, message):
        if message.echo:
            return
        asyncio.create_task(process_messages(message.content, self.screen))
        await self.handle_commands(message)

    @commands.command()
    async def pixel(self, ctx: commands.Context):
        await ctx.send("Ex: #FFFFFF;11;17 -> couleur_hexadecimal;x position;y position"
                       " 1 message : 1 pixel ; x0 y0 = le pixel en haut à gauche")


async def get_twitch_chat_messages(bot):
    await bot.start()


def freq_from_pixel(pixel):
    color_sum = pixel.red + pixel.green + pixel.blue
    note_index = round((color_sum / 765) * 39)
    return (2 ** ((note_index+69 - 81) / 12)) * 440


async def do_music(pixel):
    duration = 0.5
    samples = (np.sin(2*np.pi*np.arange(sample_rate*duration)*freq_from_pixel(pixel)/sample_rate)).astype(np.float32)
    await asyncio.sleep(0)
    stream = p.open(format=format_audio, channels=num_channels, rate=sample_rate, output=True)
    stream.write(volume*samples)
    stream.close()
    await asyncio.sleep(0)


async def calculate_pixel_from_message(match):
    color, x, y = match.group(0).split(';')
    red, green, blue = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
    x, y = int(x), int(y)
    return Pixel(red, green, blue, x, y)


def check_text_format_pixel(message):
    pattern = r'^#[0-9A-Fa-f]{{6}};([1-9]|[1-5]\d|6[0-4]\d|65[0-4]);([1-9]|[1-2]\d|3[0-5]\d|{height})$'.format(
        height=height-1, length=length-1)
    return re.match(pattern, message)


async def process_messages(message, screen):
    match = check_text_format_pixel(message)
    if match is not None:
        pixel = await calculate_pixel_from_message(match)
        # si vous ne souhaitez pas avoir de son, mettez en commentaire la fonction juste en dessous
        asyncio.create_task(do_music(pixel))
        await show_pixel(pixel, screen)


async def show_pixel(pixel, screen):
    screen.set_at((pixel.x, pixel.y), (pixel.red, pixel.green, pixel.blue))
    pygame.display.update()
    await asyncio.sleep(0)


def check_event(screen):
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return True
        if event.type == pygame.MOUSEBUTTONDOWN:
            pygame.draw.circle(screen, (255, 255, 255), pygame.mouse.get_pos(), radius_censor)
            pygame.display.update()
    return False


async def game_loop(bot, screen):
    frame_time = 1 / image_per_seconds
    running = True
    while running:
        await asyncio.sleep(0)
        start_time = time.monotonic()
        if check_event(screen):
            running = False
        await asyncio.sleep(0)
        elapsed_time = time.monotonic() - start_time
        remaining_time = frame_time - elapsed_time
        if remaining_time > 0:
            await asyncio.sleep(remaining_time)
    await asyncio.sleep(1)
    await bot.close()


def loadsave(screen):
    image_count = 0
    if os.path.exists(f"saved_image_{image_count}.png"):
        while os.path.exists(f"saved_image_{image_count}.png"):
            image_count += 1
        image_count -= 1
        saved_image = pygame.image.load(f"saved_image_{image_count}.png")
        screen.blit(saved_image, (0, 0))
        image_count += 1
        pygame.display.flip()
    else:
        screen.fill((0, 0, 0))
    return image_count


def save_and_quit(screen, image_count):
    pygame.image.save(screen, f"saved_image_{image_count}.png")
    pygame.quit()


async def main():
    pygame.init()
    screen = pygame.display.set_mode((length, height))
    image_count = loadsave(screen)
    pygame.display.set_caption("Pixel Display")
    bot = BotTwitch(screen)
    tasks = [asyncio.create_task(get_twitch_chat_messages(bot)), asyncio.create_task(game_loop(bot, screen))]
    await asyncio.gather(*tasks)
    await asyncio.sleep(1)
    save_and_quit(screen, image_count)


asyncio.run(main())
