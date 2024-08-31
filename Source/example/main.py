#!/usr/bin/python
# -*- coding: UTF-8 -*-
#import chardet
import os
import sys 
from time import time, strftime, localtime
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
current_page = 'stopwatch'
stopwatch_running = True
stopwatch_initial_time = localtime()

def startup():
    global disp

    disp.Init()
    disp.clear()
    disp.bl_DutyCycle(50)
    
def default_page():
    # Initialize default page
    page = Image.new("RGB", (240, 240), BLACK)
    draw = ImageDraw.Draw(page)

    # Draw outer circle
    draw.arc((1,1,239,239),0, 360, fill =DARK_GRAY)
    draw.arc((2,2,238,238),0, 360, fill =DARK_GRAY)
    draw.arc((3,3,237,237),0, 360, fill =DARK_GRAY)

    return page

def draw_home_page():
    global home_page

    # Prepare default image
    home_page = default_page()
    draw = ImageDraw.Draw(home_page)

    # Draw text
    _, _, w, h = draw.textbbox((0, 0), strftime("%H:%M", localtime()), font=HUGE_FONT)
    draw.text(((240-w)/2, (228-h)/2), strftime("%H:%M", localtime()), font=HUGE_FONT, fill=WHITE)

def draw_stopwatch_page():
    global stopwatch_page

    # Prepare default image
    stopwatch_page = default_page()
    draw = ImageDraw.Draw(stopwatch_page)

    # Draw header
    _, _, w, h = draw.textbbox((0, 0), "Stopwatch", font=SMALL_FONT)
    draw.text(((240-w)/2, (50-h)/2), "Stopwatch", font=SMALL_FONT, fill=WHITE)

    # Run stopwatch data
    stopwatch_logic(draw)

def stopwatch_logic(draw):
    global current_page, stopwatch_running, stopwatch_initial_time

    if current_page == 'stopwatch':
        if stopwatch_running == True:
            # Calculate elapsed time
            elapsed_time = (localtime().tm_hour - stopwatch_initial_time.tm_hour) * 3600 + (localtime().tm_min - stopwatch_initial_time.tm_min) * 60 + (localtime().tm_sec - stopwatch_initial_time.tm_sec)
            
            # Calculate hours
            hours = str(elapsed_time // 3600)

            # Calculate minutes
            minutes = str((elapsed_time - (elapsed_time // 3600) * 3600) // 60)
            if int(minutes) < 10:
                minutes = '0' + minutes
            
            # Calculate seconds
            seconds = str(elapsed_time - ((elapsed_time // 3600) * 3600) - ((((elapsed_time // 3600) * 3600) // 60) * 60) // 60)
            if int(seconds) < 10:
                seconds = '0' + seconds
            
            stopwatch_output = hours + ':' + minutes + ":" + seconds
           
            # Draw Stopwatch
            _, _, w, h = draw.textbbox((0, 0), stopwatch_output, font=LARGE_FONT)
            draw.text(((240-w)/2, (180-h)/2), stopwatch_output, font=LARGE_FONT, fill=WHITE)

def display_image():
    global home_page, stopwatch_page
    if current_page == 'home':
        draw_home_page()
        disp.ShowImage(home_page)
    elif current_page == 'stopwatch':
        draw_stopwatch_page()
        disp.ShowImage(stopwatch_page)

def main():
    # Initializations
    startup()
    
    # Display current page
    while True:
        display_image()

if __name__ == "__main__":
    main()