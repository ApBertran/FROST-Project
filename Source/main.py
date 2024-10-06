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
import gattlib
import struct
import json

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
notification_address = open('DEVICE_NAME.txt', 'r').readline().strip() # INSERT BLUETOOTH DEVICE IN DEVICE_NAME.TXT
obj_path = None
media_player = None
iface = None
properties_iface = None
bluetooth_connection = None

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
home_page = Image.new("RGB", (disp.width, disp.height), BLACK)
stopwatch_page = Image.new("RGB", (disp.width, disp.height), BLACK)
music_page = Image.new("RGB", (disp.width, disp.height), BLACK)
notifications_page = Image.new("RGB", (disp.width, disp.height), BLACK)

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

notification_history = []

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
    draw.ellipse((47.5,145,82.5,180), fill =sel_prev, outline =sel_prev)
    draw.ellipse((48.5,146,81.5,179), fill =BLACK, outline =sel_prev)

    draw.polygon([(52.5,162.5), (64, 156), (64,169)], fill =sel_prev)
    draw.polygon([(62,162.5), (74.5, 156), (74.5,169)], fill =sel_prev)

    # Toggle
    draw.ellipse((102.5,145,137.5,180), fill =sel_toggle, outline =sel_toggle)
    draw.ellipse((103.5,146,136.5,179), fill =BLACK, outline =sel_toggle)

    if music_playback_status() == 'playing':
        draw.rectangle(((112.5, 154), (117.5, 171)), fill=sel_toggle)
        draw.rectangle(((122.5, 154), (127.5, 171)), fill=sel_toggle)
    else:
        draw.polygon([(130.5,162.5), (112.5, 154), (112.5,171)], fill =sel_toggle)
    
    # Next
    draw.ellipse((157.5,145,192.5,180), fill =sel_next, outline =sel_next)
    draw.ellipse((158.5,146,191.5,179), fill =BLACK, outline =sel_next)

    draw.polygon([(179,162.5), (165.5, 156), (165.5,169)], fill =sel_next)
    draw.polygon([(187.5,162.5), (176, 156), (176,169)], fill =sel_next)

    # Decrease Volume
    # draw.ellipse((75,185,110,220), fill =sel_dec, outline =sel_dec)
    # draw.ellipse((76,186,109,219), fill =BLACK, outline =sel_dec)

    # draw.rectangle(((82, 200), (103, 205)), fill=sel_dec)

    # Increase Volume
    # draw.ellipse((130,185,165,220), fill =sel_inc, outline =sel_inc)
    # draw.ellipse((131,186,164,219), fill =BLACK, outline =sel_inc)

    # draw.rectangle(((137, 200), (158, 205)), fill=sel_inc)
    # draw.rectangle(((145, 192), (150, 213)), fill=sel_inc)

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
            draw.text(((240-w)/2, (140-h)/2), title, font=MEDIUM_FONT, fill=WHITE)

            # Draw artist
            _, _, w, h = draw.textbbox((0, 0), artist, font=SMALL_FONT)
            draw.text(((240-w)/2, (190-h)/2), artist, font=SMALL_FONT, fill=WHITE)

            # Draw time
            _, _, w, h = draw.textbbox((0, 0), f"{position_min}:{position_sec:02d}/{duration_min}:{duration_sec:02d}", font=SMALL_FONT)
            draw.text(((240-w)/2, (240-h)/2), f"{position_min}:{position_sec:02d}/{duration_min}:{duration_sec:02d}", font=SMALL_FONT, fill=WHITE)
            
            if bluetooth_connection == False:
                bluetooth_connection = True
        else:
            _, _, w, h = draw.textbbox((0, 0), "No song detected", font=MEDIUM_FONT)
            draw.text(((240-w)/2, (170-h)/2), "No song detected", font=MEDIUM_FONT, fill=WHITE)

    except Exception as e:
        _, _, w, h = draw.textbbox((0, 0), "Press PLAY to connect", font=MEDIUM_FONT)
        draw.text(((240-w)/2, (170-h)/2), "Press PLAY to connect", font=MEDIUM_FONT, fill=WHITE)
        bluetooth_connection = False

def draw_notifications_page():
    global notifications_page

    # Prepare default image
    notifications_page = draw_default_page()
    draw = ImageDraw.Draw(notifications_page)

    # Draw header
    _, _, w, h = draw.textbbox((0, 0), "Notifications", font=SMALL_FONT)
    draw.text(((240-w)/2, (50-h)/2), "Notifications", font=SMALL_FONT, fill=WHITE)

    # Draw music selection buttons
    # music_selection_buttons(draw)

    # Draw icon bar
    draw_home_icon(draw, 25, 0, DARK_GRAY)
    draw_notifications_icon(draw, 0, 5, WHITE)

    # Draw notification info
    display_notifications(draw)


def notification_add_to_history(sender, message):
    global notification_history

    # Store notification as a tuple: (sender, message, timestamp)
    notification_history.append((sender, message, time.time()))

    # Limit history to the last 10 notifications (if desired)
    if len(notification_history) > 10:
        notification_history.pop(0)

# Function to check and remove notifications older than 1.5 hours (90 minutes)
def delete_old_notifications():
    global notification_history

    # Filter out notifications older than 90 minutes (5400 seconds)
    notification_history = [
        (sender, message, timestamp) for sender, message, timestamp in notification_history
        if time.time() - timestamp < 5400
    ]

# Text wrapping function for multiline text rendering
def wrap_text(text, font, max_width):
    lines = []
    words = text.split()
    while words:
        line = ''
        while words and font.getsize(line + words[0])[0] <= max_width:
            line += (words.pop(0) + ' ')
        lines.append(line.strip())
    return lines

# Function to display all notifications in history
def display_notification_history(draw, font, max_width, line_height, position):
    # Start drawing from the specified position
    x, y = position
    for notification in notification_history:
        sender, message, timestamp = notification
        wrapped_message = wrap_text(f"{sender}: {message}", font, max_width)
        print(sender + ':' + message)
        for line in wrapped_message:
            draw.text((x, y), line, font=font, fill=(255, 255, 255))
            y += line_height
        y += line_height  # Add extra spacing between notifications

# Example function to display the notifications on the screen
def display_notifications(draw):
    
    # Position to start drawing the history (top-left corner)
    position = (10, 10)
    max_width = 220
    line_height = 20
    
    # Before displaying, delete old notifications
    delete_old_notifications()
    
    # Display notification history
    display_notification_history(draw, SMALL_FONT, max_width, line_height, position)

# Function to read notifications via Bluetooth using gattlib
def read_notifications(draw):
    try:
        adapter = gattlib.DiscoveryService('hci0')
        devices = adapter.discover(2)  # Discover for 2 seconds
        for address, name in devices.items():
            if name == notification_address:  # Assuming iPhone Bluetooth connection
                # Connect and read notifications
                with gattlib.Device(address) as device:
                    # Assuming a notification GATT service UUID (replace with actual)
                    notification_uuid = "00002a46-0000-1000-8000-00805f9b34fb"
                    value = device.char_read(notification_uuid)
                    
                    # Extract notification content (this is typically structured)
                    notification_data = struct.unpack("<H", value)
                    # Deserialize or decode as needed (assuming it's JSON encoded)
                    notification = json.loads(notification_data)
                    
                    # Parse notification and add it to history
                    sender = notification.get('sender', 'Unknown')
                    message = notification.get('message', '')
                    notification_add_to_history(sender, message)
                    
                    # Show on display
                    display_notifications(draw)
                    
    except Exception as e:
        print(f"Error reading notifications: {e}")

# Example of how to trigger when a new notification is received
# def on_notification_received(sender, message):
#     notification_add_to_history(sender, message)
#     print(f"New Notification from {sender}: {message}")
    
#     # Optionally, delete old notifications right after adding a new one
#     delete_old_notifications()

# Simulate receiving notifications (for testing purposes)
# on_notification_received("Friend", "Hello")
# on_notification_received("Work", "Meeting at 3PM")
# time.sleep(5)  # Simulate a short delay
# on_notification_received("Mom", "Call me when you're free")

def button_logic():
    global left_pressed, right_pressed, okay_pressed, back_pressed, current_page, stopwatch_selection, stopwatch_state, music_index

    # Handle LEFT inputs
    if GPIO.input(LEFT) and left_pressed == False:
        left_pressed = True

        # Home Page
        if current_page == 'home':
            current_page = 'notifications'

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

        # Notifications Page
        if current_page == 'notifications':
            current_page = 'home'

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
        if current_page == 'stopwatch':
            if stopwatch_selection == 'none':
                stopwatch_selection = 'toggle'
            elif stopwatch_selection == 'toggle':
                stopwatch_toggle()
            elif stopwatch_selection == 'reset':
                stopwatch_reset()

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
        if current_page == 'stopwatch':
            stopwatch_selection = 'none'
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
    elif current_page == 'notifications':
        draw_notifications_page()
        disp.ShowImage(notifications_page)

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