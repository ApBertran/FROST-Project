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
import dbus
import smbus
#import gattlib # for notifications, currently useless
import struct
import json
import math
import random

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
left_pressed = False
right_pressed = False
okay_pressed = False
back_pressed = False

# Bluetooth configuration
bus = None
device_address = open('MAC.txt', 'r').readline().strip() # INSERT BLUETOOTH MAC ADDRESS IN MAC.TXT
obj_path = None
media_player = None
iface = None
properties_iface = None
bluetooth_connection = None

# Accelerometer / Magnetometer configuration
imu_bus = smbus.SMBus(1)
MAG_ADDRESS = 0x1E  # Magnetometer I2C address
ACC_ADDRESS = 0x6A  # Accelerometer I2C address
SCREEN_SIZE = 240
CIRCLE_RADIUS = 119  # Radius of the circle (239px max size - 1px border)
CENTER = SCREEN_SIZE // 2  # Center of the circle

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

colors_2048 = {
    0: (0, 0, 0),        # Empty cell color (black)
    2: (179, 229, 252),  # Light Blue
    4: (129, 212, 250),  # Brighter Sky Blue
    8: (79, 195, 247),   # Sky Blue
    16: (41, 182, 246),  # Mid-tone Blue
    32: (3, 169, 244),   # Vivid Blue
    64: (3, 155, 229),   # Intense Blue
    128: (2, 136, 209),  # Deep Blue
    256: (2, 119, 189),  # Strong Blue
    512: (1, 87, 155),    # Dark Blue
    1024: (1, 73, 124),   # Deep Ocean Blue
    2048: (1, 58, 100)    # Dark Teal-Blue
}

# Prepare display
disp = LCD_1inch28.LCD_1inch28()

# Pages
home_page = Image.new("RGB", (disp.width, disp.height), BLACK)
stopwatch_page = Image.new("RGB", (disp.width, disp.height), BLACK)
music_page = Image.new("RGB", (disp.width, disp.height), BLACK)
compass_page = Image.new("RGB", (disp.width, disp.height), BLACK)
game_2048_page = Image.new("RGB", (disp.width, disp.height), BLACK)

# Page Logic Variables
current_page = 'home'

stopwatch_initial_time = localtime()
stopwatch_elapsed_time = 0
stopwatch_state = 'inactive'
stopwatch_paused_time = 0
stopwatch_output = '0:00:00'
stopwatch_selection = 'none'

music_selection = ['none', 'previous', 'toggle', 'next', 'decrease', 'increase']
music_index = 0

game_2048_selection = 'none'
score_2048 = 0
game_2048_active = False
grid_2048 = None

def startup():
    global disp

    # Initiate display
    disp.Init()
    disp.clear()
    disp.bl_DutyCycle(50)

    start_bluetooth()
    get_bluetooth_properties()

    print("main running")

def start_bluetooth():
    global bus, obj_path, media_player, properties_iface, iface

    try:
        bus = dbus.SystemBus()
        obj_path = f"/org/bluez/hci0/dev_{device_address.replace(':', '_')}/player0"
        media_player = bus.get_object("org.bluez", obj_path)
        iface = dbus.Interface(media_player, "org.bluez.MediaPlayer1")
        properties_iface = dbus.Interface(media_player, "org.freedesktop.DBus.Properties")

    except Exception as e:
        print(f"Error initializing Bluetooth connection: {e}\nRetry bluetooth connection in the Audio Control page")

def get_bluetooth_properties():
    try:
        # get all properties to verify bluetooth works
        all_properties = properties_iface.GetAll("org.bluez.MediaPlayer1")
        print("All available properties:")
        for key, value in all_properties.items():
            print(f"{key}: {value}")

    except dbus.DBusException as e:
        print(f"Error getting all properties: {e}")

def draw_default_page():
    # Initialize default page
    page = Image.new("RGB", (disp.width, disp.height), BLACK)
    draw = ImageDraw.Draw(page)

    # Draw outer circle
    draw.ellipse((1,1,239,239), fill =DARK_GRAY, outline =DARK_GRAY)
    draw.ellipse((3,3,237,237), fill =BLACK, outline =DARK_GRAY)
    
    return page

def draw_home_icon(draw, x_offset, y_offset, highlight):
    draw.polygon([(120+x_offset, 210+y_offset), (111+x_offset, 217+y_offset), (129+x_offset, 217+y_offset)], fill =BLACK, outline=highlight)
    draw.polygon([(120+x_offset, 211+y_offset), (111+x_offset, 217+y_offset), (129+x_offset, 217+y_offset)], fill =BLACK, outline=highlight)
    draw.polygon([(120+x_offset, 212+y_offset), (111+x_offset, 218+y_offset), (129+x_offset, 218+y_offset)], fill =BLACK, outline=highlight)
    draw.rectangle(((114+x_offset, 217+y_offset), (126+x_offset, 228+y_offset)), fill=BLACK, outline=highlight)
    draw.rectangle(((115+x_offset, 218+y_offset), (125+x_offset, 227+y_offset)), fill=BLACK, outline=highlight)

def draw_stopwatch_icon(draw, x_offset, y_offset, highlight):
    draw.ellipse((111+x_offset, 210+y_offset, 129+x_offset, 228+y_offset), fill =highlight, outline =highlight)
    draw.ellipse((112+x_offset, 211+y_offset, 128+x_offset, 227+y_offset), fill =BLACK, outline =highlight)
    draw.line((119+x_offset, 219+y_offset, 124+x_offset, 219+y_offset), width=2, fill=highlight)
    draw.line((120+x_offset, 219+y_offset, 120+x_offset, 213+y_offset), width=2, fill=highlight)
    
def draw_music_icon(draw, x_offset, y_offset, highlight):
    draw.line((115+x_offset, 212+y_offset, 115+x_offset, 226+y_offset), width=2, fill=highlight)
    draw.line((127+x_offset, 212+y_offset, 127+x_offset, 226+y_offset), width=2, fill=highlight)
    draw.line((116+x_offset, 211+y_offset, 127+x_offset, 211+y_offset), width=2, fill=highlight)
    draw.line((115+x_offset, 216+y_offset, 128+x_offset, 216+y_offset), width=2, fill=highlight)
    draw.ellipse((111+x_offset, 224+y_offset, 115+x_offset, 228+y_offset), fill =highlight, outline =highlight)
    draw.ellipse((123+x_offset, 224+y_offset, 127+x_offset, 228+y_offset), fill =highlight, outline =highlight)

def draw_notifications_icon(draw, x_offset, y_offset, highlight):
    draw.arc(((113+x_offset, 211+y_offset),(127+x_offset, 224+y_offset)), start=180, end=360, fill=highlight)
    draw.arc(((113+x_offset, 212+y_offset),(127+x_offset, 225+y_offset)), start=180, end=360, fill=highlight)
    draw.line((113+x_offset, 215+y_offset, 113+x_offset, 224+y_offset), width=2, fill=highlight)
    draw.line((126+x_offset, 215+y_offset, 126+x_offset, 224+y_offset), width=2, fill=highlight)
    draw.line((111+x_offset, 225+y_offset, 129+x_offset, 225+y_offset), width=2, fill=highlight)
    draw.rectangle(((119+x_offset, 227+y_offset), (121+x_offset, 228+y_offset)), fill=highlight, outline=highlight)

def draw_home_page():
    global home_page

    # Prepare default image
    home_page = draw_default_page()
    draw = ImageDraw.Draw(home_page)

    # Draw text
    _, _, w, h = draw.textbbox((0, 0), strftime("%H:%M", localtime()), font=HUGE_FONT)
    draw.text(((240-w)/2, (228-h)/2), strftime("%H:%M", localtime()), font=HUGE_FONT, fill=WHITE)

    # Draw icon bar
    draw_home_icon(draw, 0, 5, WHITE)
    draw_music_icon(draw, 25, 0, DARK_GRAY)
    draw_notifications_icon(draw, -25, 0, DARK_GRAY)

def draw_stopwatch_page():
    global stopwatch_page

    # Prepare default image
    stopwatch_page = draw_default_page()
    draw = ImageDraw.Draw(stopwatch_page)

    # Draw header
    _, _, w, h = draw.textbbox((0, 0), "Stopwatch", font=SMALL_FONT)
    draw.text(((240-w)/2, (50-h)/2), "Stopwatch", font=SMALL_FONT, fill=WHITE)

    # Draw stopwatch selection buttons
    stopwatch_selection_buttons(draw)

    # Draw icon bar
    draw_music_icon(draw, -25, 0, DARK_GRAY)
    draw_stopwatch_icon(draw, 0, 5, WHITE)

    # Run stopwatch timer
    stopwatch_time_logic(draw)

def stopwatch_selection_buttons(draw):
    sel_toggle = DARK_GRAY
    sel_reset = DARK_GRAY

    # Highlight chosen button
    if stopwatch_selection == 'reset':
        sel_reset = WHITE
    elif stopwatch_selection == 'toggle':
        sel_toggle = WHITE

    # Draw selection buttons
    if stopwatch_state == 'inactive':
        draw.ellipse((45,140,105,200), fill =sel_toggle, outline =sel_toggle)
        draw.ellipse((46,141,104,199), fill = 'green', outline =sel_toggle)
        _, _, w, h = draw.textbbox((0, 0), 'START', font=SMALL_FONT)
        draw.text(((75-w/2), (170-h/2)), 'START', font=SMALL_FONT, fill=sel_toggle)
    elif stopwatch_state == 'active':
        draw.ellipse((45,140,105,200), fill =sel_toggle, outline =sel_toggle)
        draw.ellipse((46,141,104,199), fill = 'red', outline =sel_toggle)
        _, _, w, h = draw.textbbox((0, 0), 'STOP', font=SMALL_FONT)
        draw.text(((75-w/2), (170-h/2)), 'STOP', font=SMALL_FONT, fill=sel_toggle)

    draw.ellipse((135,140,195,200), fill =sel_reset, outline =sel_reset)
    draw.ellipse((136,141,194,199), fill =GRAY, outline =sel_reset)
    _, _, w, h = draw.textbbox((0, 0), 'RESET', font=SMALL_FONT)
    draw.text(((165-w/2), (170-h/2)), 'RESET', font=SMALL_FONT, fill=sel_reset)

def stopwatch_time_logic(draw):
    global stopwatch_elapsed_time, stopwatch_output

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
        
        stopwatch_output = hours + ':' + minutes + ':' + seconds
    
    # Draw stopwatch time
    _, _, w, h = draw.textbbox((0, 0), stopwatch_output, font=LARGE_FONT)
    draw.text(((240-w)/2, (180-h)/2), stopwatch_output, font=LARGE_FONT, fill=WHITE)

def stopwatch_toggle():
    global stopwatch_state, stopwatch_paused_time, stopwatch_initial_time

    if stopwatch_state == 'inactive':
        stopwatch_state = 'active'
        stopwatch_initial_time = localtime()
    else:
        stopwatch_state = 'inactive'
        stopwatch_paused_time = stopwatch_elapsed_time

def stopwatch_reset():
    global stopwatch_elapsed_time, stopwatch_paused_time, stopwatch_state, stopwatch_output

    stopwatch_state = 'inactive'
    stopwatch_elapsed_time = 0
    stopwatch_paused_time = 0
    stopwatch_output = '0:00:00'

def draw_music_page():
    global music_page

    # Prepare default image
    music_page = draw_default_page()
    draw = ImageDraw.Draw(music_page)

    # Draw header
    _, _, w, h = draw.textbbox((0, 0), "Audio Control", font=SMALL_FONT)
    draw.text(((240-w)/2, (50-h)/2), "Audio Control", font=SMALL_FONT, fill=WHITE)

    # Draw music selection buttons
    music_selection_buttons(draw)

    # Draw icon bar
    draw_home_icon(draw, -25, 0, DARK_GRAY)
    draw_stopwatch_icon(draw, 25, 0, DARK_GRAY)
    draw_music_icon(draw, 0, 5, WHITE)

    # Draw music info
    music_display_info(draw)

def music_selection_buttons(draw):
    # Unfortunately direct assignment is computationally the fastest way to process this logic.
    # The endless conditionals look ugly, but they're better for this use-case where performance is important.
    
    sel_prev = DARK_GRAY
    sel_toggle = DARK_GRAY
    sel_next = DARK_GRAY
    sel_dec = DARK_GRAY
    sel_inc = DARK_GRAY

    # Highlight chosen button
    if music_selection[music_index] == 'previous':
        sel_prev = WHITE
    elif music_selection[music_index] == 'toggle':
        sel_toggle = WHITE
    elif music_selection[music_index] == 'next':
        sel_next = WHITE
    elif music_selection[music_index] == 'decrease':
        sel_dec = WHITE
    elif music_selection[music_index] == 'increase':
        sel_inc = WHITE

    # Previous
    draw.ellipse((47.5,165,102.5,180), fill =sel_prev, outline =sel_prev)
    draw.ellipse((48.5,166,101.5,179), fill =BLACK, outline =sel_prev)

    draw.polygon([(52.5,182.5), (64, 176), (64,189)], fill =sel_prev)
    draw.polygon([(62,182.5), (74.5, 176), (74.5,189)], fill =sel_prev)

    # Toggle
    draw.ellipse((102.5,165,137.5,200), fill =sel_toggle, outline =sel_toggle)
    draw.ellipse((103.5,166,136.5,199), fill =BLACK, outline =sel_toggle)

    if music_playback_status() == 'playing':
        draw.rectangle(((112.5, 174), (117.5, 191)), fill=sel_toggle)
        draw.rectangle(((122.5, 174), (127.5, 191)), fill=sel_toggle)
    else:
        draw.polygon([(130.5,182.5), (112.5, 174), (112.5,191)], fill =sel_toggle)
    
    # Next
    draw.ellipse((157.5,165,192.5,200), fill =sel_next, outline =sel_next)
    draw.ellipse((158.5,166,191.5,199), fill =BLACK, outline =sel_next)

    draw.polygon([(179,182.5), (165.5, 176), (165.5,189)], fill =sel_next)
    draw.polygon([(187.5,182.5), (176, 176), (176,189)], fill =sel_next)

def music_send_command(command):
    # Separate function to more cleanly handle errors in order to run without bluetooth functionality
    try:
        if command == "play":
            iface.Play()
        elif command == "pause":
            iface.Pause()
        elif command == "next":
            iface.Next()
        elif command == "previous":
            iface.Previous()
        elif command == "increase" and get_volume() != None:
            set_volume(get_volume() + 10)
        elif command == "decrease" and get_volume() != None:
            set_volume(get_volume() - 10)

    except Exception as e:
        print(f"Error sending Bluetooth command: {e}")

def music_playback_status():
    try:
        status = properties_iface.Get("org.bluez.MediaPlayer1", "Status")
        return status

    except Exception as e:
        print(f"Error getting playback status: {e}")
        return None

def get_volume():
    try:
        volume = properties_iface.Get("org.bluez.MediaTransport1", "Volume")
        return volume
    
    except dbus.DBusException as e:
        print(f"Error getting volume: {e}")
        return None

def set_volume(new_volume):
    try:
        new_volume = max(0, min(new_volume, 127)) # Volume is standard 7-bit, so clamp 0-127
        properties_iface.Set("org.bluez.MediaTransport1", "Volume", dbus.UInt16(new_volume))
    except dbus.DBusException as e:
        print(f"Error setting volume: {e}")

def music_display_info(draw):
    global bluetooth_connection

    try:
        properties = properties_iface.GetAll("org.bluez.MediaPlayer1")

        if "Track" in properties:
            track = properties["Track"]
            title = track.get("Title", "Unknown")
            artist = track.get("Artist", "Unknown")
            duration_ms = track.get("Duration", 0)  # Duration in milliseconds
            position_ms = properties.get("Position", 0)  # Elapsed time in milliseconds

            # Convert milliseconds to minutes and seconds
            duration_min, duration_sec = divmod(duration_ms // 1000, 60)
            position_min, position_sec = divmod(position_ms // 1000, 60)

            # Draw title
            _, _, w, h = draw.textbbox((0, 0), title, font=MEDIUM_FONT)
            draw.text(((240-w)/2, (180-h)/2), title, font=MEDIUM_FONT, fill=WHITE)

            # Draw artist
            _, _, w, h = draw.textbbox((0, 0), artist, font=SMALL_FONT)
            draw.text(((240-w)/2, (230-h)/2), artist, font=SMALL_FONT, fill=WHITE)

            # Draw time
            _, _, w, h = draw.textbbox((0, 0), f"{position_min}:{position_sec:02d}/{duration_min}:{duration_sec:02d}", font=SMALL_FONT)
            draw.text(((240-w)/2, (280-h)/2), f"{position_min}:{position_sec:02d}/{duration_min}:{duration_sec:02d}", font=SMALL_FONT, fill=WHITE)
            
            if bluetooth_connection == False:
                bluetooth_connection = True
        else:
            _, _, w, h = draw.textbbox((0, 0), "No song detected", font=MEDIUM_FONT)
            draw.text(((240-w)/2, (210-h)/2), "No song detected", font=MEDIUM_FONT, fill=WHITE)

    except Exception as e:
        _, _, w, h = draw.textbbox((0, 0), "Retry Connection", font=MEDIUM_FONT)
        draw.text(((240-w)/2, (210-h)/2), "Retry Connection", font=MEDIUM_FONT, fill=WHITE)
        bluetooth_connection = False

def draw_2048_page():
    global game_2048_page

    # Prepare default image
    game_2048_page = draw_default_page()
    draw = ImageDraw.Draw(game_2048_page)

    # Draw header
    _, _, w, h = draw.textbbox((0, 0), "2048", font=SMALL_FONT)
    draw.text(((240-w)/2, (50-h)/2), "2048", font=SMALL_FONT, fill=WHITE)

    create_image_2048(draw)

    if game_2048_selection == 'play':
        game_play_2048(draw)
    elif game_2048_selection == 'over':
        game_over_2048(draw)
    else:
        game_menu_2048(draw)

def game_menu_2048(draw):
    if game_2048_selection == 'menu':
        fill_color = WHITE
    else:
        fill_color = DARK_GRAY

    # Display High Score
    _, _, w, h = draw.textbbox((0, 0), 'HIGH SCORE', font=MEDIUM_FONT)
    draw.text(((240-w)/2, (120-h)/2), 'HIGH SCORE', font=MEDIUM_FONT, fill=fill_color)

    # Play Button
    _, _, w, h = draw.textbbox((0, 0), 'PLAY', font=LARGE_FONT)
    draw.text(((240-w)/2, (240-h)/2), 'PLAY', font=LARGE_FONT, fill=fill_color)

def game_play_2048(draw):
    global game_2048_active, score_2048, grid_2048, game_2048_selection
    if not game_2048_active:
        grid_2048 = initialize_grid_2048()
        score_2048 = 0
        game_2048_active = True

    # Display
    create_image_2048(draw, score_2048)

    # Exit Game
    if GPIO.input(LEFT) + GPIO.input(RIGHT) + GPIO.input(BACK) + GPIO.input(OKAY) > 1:
        game_2048_selection = 'none'
    



def game_over_2048(draw):

def initialize_grid_2048(size=4):
    global grid_2048

    grid_2048 = [[0] * size for _ in range(size)]
    add_new_tile_2048(grid_2048)
    add_new_tile_2048(grid_2048)
    return grid_2048

def add_new_tile_2048():
    global grid_2048

    empty_tiles = [(i, j) for i in range(len(grid_2048)) for j in range(len(grid_2048[i])) if grid_2048[i][j] == 0]
    if empty_tiles:
        i, j = random.choice(empty_tiles)
        grid_2048[i][j] = random.choice([2, 4])

def create_image_2048(draw):
    global grid_2048, score_2048

    cell_size = 45  # Size of each cell
    border_size = 5  # Size of the border
    play_area_size = cell_size * 4  # 4 columns
    width = play_area_size + 2 * border_size  # Include border
    height = play_area_size + 2 * border_size  # Include border

    top_left_x = (disp.width - width) / 2
    top_left_y = (disp.height - height) / 2

    # Draw border around the play area
    draw.rectangle([top_left_x, top_left_y, top_left_x + width, top_left_y + height], outline=WHITE, width=border_size, fill=BLACK) 

    # Fill the grid area with black
    # draw.rectangle(
    #     [border_size * 2, border_size * 2, width, height], 
    #     fill=(0, 0, 0)
    # )

    # Draw grid
    for i in range(len(grid_2048)):
        for j in range(len(grid_2048[i])):
            value = grid_2048[i][j]
            fill_color = colors_2048.get(value, (1, 58, 100)) # Default to 2048 color if not found in case someone goes past 2048
            
            cell_x1 = top_left_x + border_size + j * cell_size
            cell_y1 = top_left_y + border_size + i * cell_size
            cell_x2 = cell_x1 + cell_size
            cell_y2 = cell_y1 + cell_size
            draw.rectangle([cell_x1, cell_y1, cell_x2, cell_y2], fill=fill_color)

            if value != 0:
                text = str(value)
                _, _, w, h = draw.textbbox((0, 0), text, font=SMALL_FONT)  # Get text bounding box
                text_x = cell_x1 + (cell_size - w) / 2
                text_y = cell_y1 + (cell_size - h) / 2
                draw.text((text_x, text_y), text, fill=(255, 255, 255), font=SMALL_FONT)

    # Display the score outside the border
    draw.text((border_size + 5, height + border_size), f"Score: {score_2048}", fill=WHITE, font=SMALL_FONT)

def game_2048_slide_and_merge(row):
    new_row = [num for num in row if num != 0]
    score = 0
    i = 0
    while i < len(new_row) - 1:
        if new_row[i] == new_row[i + 1]:
            new_row[i] *= 2
            score += new_row[i]
            del new_row[i + 1]
        i += 1
    return new_row + [0] * (len(row) - len(new_row)), score

def game_2048_move_left():
    global grid_2048, score_2048

    total_score = 0
    for i in range(len(grid_2048)):
        grid_2048[i], score = game_2048_slide_and_merge(grid_2048[i])
        total_score += score
    score_2048 += total_score

def game_2048_move_right():
    global grid_2048, score_2048

    total_score = 0
    for i in range(len(grid_2048)):
        grid_2048[i].reverse()
        grid_2048[i], score = game_2048_slide_and_merge(grid_2048[i])
        grid_2048[i].reverse()
        total_score += score
    score_2048 += total_score

def game_2048_move_up():
    global grid_2048, score_2048

    total_score = 0
    for j in range(len(grid_2048)):
        column = [grid_2048[i][j] for i in range(len(grid_2048))]
        new_column, score = game_2048_slide_and_merge(column)
        total_score += score
        for i in range(len(grid_2048)):
            grid_2048[i][j] = new_column[i]
    score_2048 += total_score

def game_2048_move_down():
    global grid_2048, score_2048

    total_score = 0
    for j in range(len(grid_2048)):
        column = [grid_2048[i][j] for i in range(len(grid_2048))]
        column.reverse()
        new_column, score = game_2048_slide_and_merge(column)
        total_score += score
        for i in range(len(grid_2048)):
            grid_2048[i][j] = new_column[len(grid_2048) - 1 - i]
    score_2048 += total_score

def game_2048_is_game_over():
    global grid_2048

    if any(0 in row for row in grid_2048):
        return False
    for i in range(len(grid_2048)):
        for j in range(len(grid_2048[i])):
            if (j + 1 < len(grid_2048[i]) and grid_2048[i][j] == grid_2048[i][j + 1]) or (i + 1 < len(grid_2048) and grid_2048[i][j] == grid_2048[i + 1][j]):
                return False
    return True

def button_logic():
    global left_pressed, right_pressed, okay_pressed, back_pressed, current_page, stopwatch_selection, stopwatch_state, music_index, game_2048_selection

    # Handle LEFT inputs
    if GPIO.input(LEFT) and left_pressed == False:
        left_pressed = True

        # 2048 Page
        if current_page == '2048':
            if game_2048_selection == 'play':
                game_2048_move_left()

        # Home Page
        elif current_page == 'home':
            current_page = '2048'

        # Music Page
        elif current_page == 'music':
            if music_index == 0: # if == none
                current_page = 'home'
            else:
                music_index = max(music_index - 1, 1)

        # Stopwatch Page
        elif current_page == 'stopwatch':
            if stopwatch_selection == 'none':
                current_page = 'music'
            elif stopwatch_selection == 'reset':
                stopwatch_selection = 'toggle'

    elif not GPIO.input(LEFT) and left_pressed == True:
        left_pressed = False
    
    # Handle RIGHT inputs
    if GPIO.input(RIGHT) and right_pressed == False:
        right_pressed = True

        # 2048 Page
        if current_page == '2048':
            if game_2048_selection == 'none':
                current_page = 'home'
            elif game_2048_selection == 'play':
                game_2048_move_right()

        # Home Page
        elif current_page == 'home':
            current_page = 'music'

        # Music Page
        elif current_page == 'music':
            if music_index == 0: # if == none
                current_page = 'stopwatch'
            else:
                music_index = min(music_index + 1, 5)

        # Stopwatch Page
        elif current_page == 'stopwatch':
            if stopwatch_selection == 'none':
                pass # NEXT PAGE
            elif stopwatch_selection == 'toggle':
                stopwatch_selection = 'reset'
    
    elif not GPIO.input(RIGHT) and right_pressed == True:
        right_pressed = False

    # Handle OKAY inputs
    if GPIO.input(OKAY) and okay_pressed == False:
        okay_pressed = True

        # 2048 Page
        if current_page == '2048':
            if game_2048_selection == 'none':
                game_2048_selection = 'menu'
            elif game_2048_selection == 'menu':
                game_2048_selection = 'play'
            elif game_2048_selection == 'play':
                game_2048_move_up()

        # Stopwatch Page
        elif current_page == 'stopwatch':
            if stopwatch_selection == 'none':
                stopwatch_selection = 'toggle'
            elif stopwatch_selection == 'toggle':
                stopwatch_toggle()
            elif stopwatch_selection == 'reset':
                stopwatch_reset()

        # Music Page
        elif current_page == 'music':
            if music_index == 0: # if == none
                music_index += 2
            elif music_index == 2: # if == toggle
                if bluetooth_connection == False:
                    start_bluetooth()
                elif music_playback_status() == 'playing':
                    music_send_command('pause')
                elif music_playback_status() == 'paused' or music_playback_status() == 'stopped':
                    music_send_command('play')
            else:
                music_send_command(music_selection[music_index])
    
    elif not GPIO.input(OKAY) and okay_pressed == True:
        okay_pressed = False

    # Handle BACK inputs
    if GPIO.input(BACK) and back_pressed == False:
        back_pressed = True

        # 2048 Page
        if current_page == '2048':
            if game_2048_selection == 'menu':
                game_2048_selection = 'none'
            elif game_2048_selection == 'play':
                game_2048_move_down()

        # Stopwatch Page
        if current_page == 'stopwatch':
            stopwatch_selection = 'none'

        # Music Page
        elif current_page == 'music':
            music_index = 0 # none
    
    elif not GPIO.input(BACK) and back_pressed == True:
        back_pressed = False

def display_image():
    #global home_page, stopwatch_page
    if current_page == 'home':
        draw_home_page()
        disp.ShowImage(home_page)
    elif current_page == 'stopwatch':
        draw_stopwatch_page()
        disp.ShowImage(stopwatch_page)
    elif current_page == 'music':
        draw_music_page()
        disp.ShowImage(music_page)
    elif current_page == '2048':
        draw_2048_page()
        disp.ShowImage(game_2048_page)

def main():
    global disp

    # Initializations
    startup()
    
    # Run primary loop
    while True:
        button_logic()
        display_image()

if __name__ == "__main__":
    main()