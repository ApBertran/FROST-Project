#!/usr/bin/python
# -*- coding: UTF-8 -*-
#import chardet
import os
import sys 
from time import time, strftime, gmtime, localtime
import datetime
import logging
import spidev as SPI
sys.path.append("..")
from lib import LCD_1inch28
from PIL import Image,ImageDraw,ImageFont

# Raspberry Pi pin configuration:
RST = 27
DC = 25
BL = 18
bus = 0 
device = 0 

# Fonts
HUGE_FONT = ImageFont.truetype("../Font/Font02.ttf",80)
LARGE_FONT = ImageFont.truetype("../Font/Font02.ttf",55)
MEDIUM_FONT = ImageFont.truetype("../Font/Font02.ttf",30)
SMALL_FONT = ImageFont.truetype("../Font/Font02.ttf",20)

# Color Palette
BLACK = (0, 0, 0)               # Background
DARK_BLUE = (0, 0, 139)         # Primary
WHITE = (255, 255, 255)         # Text + Highlights
LIGHT_BLUE = (173, 216, 230)    # Accent
GRAY = (128, 128, 128)          # Neutral Background
DARK_GRAY = (47, 79, 79)        # Contrast

disp = LCD_1inch28.LCD_1inch28()

# Pages
home_page = Image.new("RGB", (240, 240), BLACK)    # REPLACE (240, 240) WITH (disp.width, disp.height)
stopwatch_page = Image.new("RGB", (240, 240), BLACK)    # REPLACE (240, 240) WITH (disp.width, disp.height)

# Page Logic Variables
current_page = 'home'
stopwatch_running = True
stopwatch_runtime = 0
stopwatch_time_elapsed = 0
stopwatch_initial_time = localtime()



def startup():
    global disp

    disp.Init()
    disp.clear()
    disp.bl_DutyCycle(50)

    prepare_default_page(home_page)
    prepare_default_page(stopwatch_page)

def logic_loop():
    stopwatch_logic()
    
def prepare_default_page(page):
    draw = ImageDraw.Draw(page)

    # Draw outer circle
    draw.arc((1,1,239,239),0, 360, fill =DARK_GRAY)
    draw.arc((2,2,238,238),0, 360, fill =DARK_GRAY)
    draw.arc((3,3,237,237),0, 360, fill =DARK_GRAY)

def draw_home_page():
    global home_page
    draw = ImageDraw.Draw(home_page)

    # Draw text
    _, _, w, h = draw.textbbox((0, 0), strftime("%H:%M", localtime()), font=HUGE_FONT)
    draw.text(((240-w)/2, (228-h)/2), strftime("%H:%M", localtime()), font=HUGE_FONT, fill=WHITE)

def draw_stopwatch_page():
    global stopwatch_page

    draw = ImageDraw.Draw(stopwatch_page)

    # Draw header
    _, _, w, h = draw.textbbox((0, 0), "Stopwatch", font=SMALL_FONT)
    draw.text(((240-w)/2, (50-h)/2), "Stopwatch", font=SMALL_FONT, fill=WHITE)

    # Draw Stopwatch
    _, _, w, h = draw.textbbox((0, 0), "Stopwatch", font=SMALL_FONT)
    draw.text(((240-w)/2, (50-h)/2), "Stopwatch", font=SMALL_FONT, fill=WHITE)

def stopwatch_logic():
    global current_page, stopwatch_running, stopwatch_runtime, stopwatch_time_elapsed

    if current_page == 'stopwatch':
        if stopwatch_running == True:
            stopwatch_time_elapsed = localtime() - stopwatch_initial_time
            print(stopwatch_time_elapsed)


def main():
    global home_page, stopwatch_page
    startup()
    draw_home_page()
    draw_stopwatch_page()

    current_image = home_page
    disp.ShowImage(current_image)
    disp.module_exit()

if __name__ == "__main__":
    main()