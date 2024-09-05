#!/usr/bin/python
# -*- coding: UTF-8 -*-
import os
import sys 
from time import strftime, localtime
import time
import spidev as SPI
sys.path.append("..")
from lib import LCD_1inch28
import RPi.GPIO as GPIO
from PIL import Image,ImageDraw,ImageFont

# Raspberry Pi pin configuration:
GPIO.setmode(GPIO.BCM)

RST = 27
DC = 25
BL = 18
bus = 0 
device = 0
OKAY = 12
BACK = 13
RIGHT = 16
LEFT = 26

channel_list = [OKAY, BACK, RIGHT, LEFT]
GPIO.setup(channel_list, GPIO.IN, GPIO.PUD_DOWN)

# Fonts
HUGE_FONT = ImageFont.truetype("Font/Font02.ttf",80)
LARGE_FONT = ImageFont.truetype("Font/Font02.ttf",55)
MEDIUM_FONT = ImageFont.truetype("Font/Font02.ttf",30)
SMALL_FONT = ImageFont.truetype("Font/Font02.ttf",20)

# Color Palette
BLACK = (0, 0, 0)               # Background
DARK_BLUE = (0, 0, 139)         # Primary
WHITE = (255, 255, 255)         # Text + Highlights
LIGHT_BLUE = (173, 216, 230)    # Accent
GRAY = (128, 128, 128)          # Neutral Background
DARK_GRAY = (47, 79, 79)        # Contrast

# Prepare display
disp = LCD_1inch28.LCD_1inch28()

# Pages
template_page = Image.new("RGB", (disp.width, disp.height), BLACK)
home_page = Image.new("RGB", (disp.width, disp.height), BLACK)
stopwatch_page = Image.new("RGB", (disp.width, disp.height), BLACK)

# Page Logic Variables
current_page = 'home'

stopwatch_initial_time = localtime()
stopwatch_elapsed_time = 0
stopwatch_state = 'inactive'
stopwatch_paused_time = 0
stopwatch_output = '0:00:00'
stopwatch_selection = 'none'

def startup():
    global disp, template_page

    # Initiate display
    disp.Init()
    disp.clear()
    disp.bl_DutyCycle(50)

    # Prepare template image
    draw = ImageDraw.Draw(template_page)

    draw.ellipse((1,1,239,239), fill =DARK_GRAY, outline =DARK_GRAY)
    draw.ellipse((3,3,237,237), fill =BLACK, outline =DARK_GRAY)

    print("main running")

def draw_home_page():
    global home_page

    # Prepare default image
    home_page = template_page
    draw = ImageDraw.Draw(home_page)

    # Draw text
    _, _, w, h = draw.textbbox((0, 0), strftime("%H:%M", localtime()), font=HUGE_FONT)
    draw.text(((240-w)/2, (228-h)/2), strftime("%H:%M", localtime()), font=HUGE_FONT, fill=WHITE)

def draw_stopwatch_page():
    global stopwatch_page

    # Prepare default image
    stopwatch_page = template_page
    draw = ImageDraw.Draw(stopwatch_page)

    # Draw header
    _, _, w, h = draw.textbbox((0, 0), "Stopwatch", font=SMALL_FONT)
    draw.text(((240-w)/2, (50-h)/2), "Stopwatch", font=SMALL_FONT, fill=WHITE)

    # Draw stopwatch selection buttons
    stopwatch_selection_buttons(draw)

    # Run stopwatch timer
    stopwatch_time_logic(draw)

def stopwatch_selection_buttons(draw):
    #global stopwatch_state, stopwatch_selection
    sel_1 = DARK_GRAY
    sel_2 = DARK_GRAY

    # Highlight chosen button
    if stopwatch_selection == 'reset':
        sel_2 = WHITE
    else:
        sel_1 = WHITE

    # Draw selection buttons
    if stopwatch_state == 'inactive':
        draw.ellipse((45,140,105,200), fill =sel_1, outline =sel_1)
        draw.ellipse((46,141,104,199), fill = 'green', outline =sel_1)
        _, _, w, h = draw.textbbox((0, 0), 'START', font=SMALL_FONT)
        draw.text(((75-w/2), (170-h/2)), 'START', font=SMALL_FONT, fill=sel_1)
    elif stopwatch_state == 'active':
        draw.ellipse((45,140,105,200), fill =sel_1, outline =sel_1)
        draw.ellipse((46,141,104,199), fill = 'red', outline =sel_1)
        _, _, w, h = draw.textbbox((0, 0), 'STOP', font=SMALL_FONT)
        draw.text(((75-w/2), (170-h/2)), 'STOP', font=SMALL_FONT, fill=sel_1)

    draw.ellipse((135,140,195,200), fill =sel_2, outline =sel_2)
    draw.ellipse((136,141,194,199), fill = 'gray', outline =sel_2)
    _, _, w, h = draw.textbbox((0, 0), 'RESET', font=SMALL_FONT)
    draw.text(((165-w/2), (170-h/2)), 'RESET', font=SMALL_FONT, fill=sel_2)

def stopwatch_time_logic(draw):
    global stopwatch_elapsed_time, stopwatch_output
    # stopwatch_state, stopwatch_initial_time, stopwatch_paused_time

    if stopwatch_state == 'active':
        # Calculate elapsed time
        stopwatch_elapsed_time = stopwatch_paused_time + (localtime().tm_hour - stopwatch_initial_time.tm_hour) * 3600 + (localtime().tm_min - stopwatch_initial_time.tm_min) * 60 + (localtime().tm_sec - stopwatch_initial_time.tm_sec)
        
        # Calculate hours
        hours = str(stopwatch_elapsed_time // 3600)

        # Calculate minutes
        minutes = str((stopwatch_elapsed_time - int(hours) * 3600) // 60)
        if int(minutes) < 10:
            minutes = '0' + minutes
        
        # Calculate seconds
        seconds = str(stopwatch_elapsed_time - (int(hours) * 3600) - (int(minutes) * 60))
        if int(seconds) < 10:
            seconds = '0' + seconds
        
        stopwatch_output = hours + ':' + minutes + ":" + seconds
    
    # Draw stopwatch time
    _, _, w, h = draw.textbbox((0, 0), stopwatch_output, font=LARGE_FONT)
    draw.text(((240-w)/2, (180-h)/2), stopwatch_output, font=LARGE_FONT, fill=WHITE)

def stopwatch_toggle():
    global stopwatch_state, stopwatch_paused_time, stopwatch_initial_time
    # stopwatch_elapsed_time

    if stopwatch_state == 'inactive':
        stopwatch_state = 'active'
        stopwatch_initial_time = localtime()
    else:
        stopwatch_state = 'inactive'
        stopwatch_paused_time = stopwatch_elapsed_time

def stopwatch_reset():
    global stopwatch_elapsed_time, stopwatch_paused_time, stopwatch_state

    stopwatch_elapsed_time = 0
    stopwatch_paused_time = 0
    stopwatch_state = 'inactive'

def button_logic():
    global current_page, stopwatch_selection, stopwatch_state

    # Handle LEFT inputs
    if GPIO.input(LEFT):
        if current_page == 'stopwatch':
            if stopwatch_selection == 'none':
                current_page = 'home'
            elif stopwatch_selection == 'reset':
                stopwatch_selection = 'toggle'
    
    # Handle RIGHT inputs
    if GPIO.input(RIGHT):
        if current_page == 'home':
            current_page = 'stopwatch'
        elif current_page == 'stopwatch':
            if stopwatch_selection == 'toggle':
                stopwatch_selection = 'reset'

    # Handle OKAY inputs
    if GPIO.input(OKAY):
        if current_page == 'stopwatch':
            if stopwatch_selection == 'none':
                stopwatch_selection = 'toggle'
            elif stopwatch_selection == 'toggle':
                stopwatch_toggle()
            elif stopwatch_selection == 'reset':
                stopwatch_reset()

    # Handle BACK inputs
    if GPIO.input(BACK):
        if current_page == 'stopwatch' and stopwatch_selection != 'none':
            stopwatch_selection = 'none'

def display_image():
    #global home_page, stopwatch_page
    if current_page == 'home':
        draw_home_page()
        disp.ShowImage(home_page)
    elif current_page == 'stopwatch':
        draw_stopwatch_page()
        disp.ShowImage(stopwatch_page)

def main():
    global disp

    # Initializations
    startup()
    
    # Run primary loop
    while True:
        disp.clear() # might break stuff, remove if display not working
        button_logic()
        display_image()

if __name__ == "__main__":
    main()