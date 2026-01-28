#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time
import os
import subprocess
from pathlib import Path


####################
##### SETTINGS #####
####################

# Paths
USB_PATH = Path("/media/pi/USB")
STATE_FILE = Path("/home/pi/nonstoptv.ini")

# Config
VIDEO_EXTENSIONS = [".avi", ".mov", ".mkv", ".mp4"]
RANDOM = True

# GPIO
GPIO.setmode(GPIO.BCM)
BUTTON_NEXTFOLDER = 21
BUTTON_NEXTVIDEO = 26
BUTTON_PAUSE = 20
BUTTON_LANGUAGE = 19
BUTTON_SKP10 = 16
BUTTON_REW10 = 13
GPIO.setup(BUTTON_NEXTFOLDER, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BUTTON_NEXTVIDEO, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BUTTON_PAUSE, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BUTTON_LANGUAGE, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BUTTON_SKP10, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BUTTON_REW10, GPIO.IN, pull_up_down=GPIO.PUD_UP)


#####################
##### FUNCTIONS #####
#####################

# Wait for Mounted USB
def is_usb_ready():
    if not USB_PATH.exists():
        return False

    try:
        for _ in USB_PATH.iterdir():
            return True
    except OSError:
        return False

    return False

# Get Valid Video Directories
def get_video_dirs():
    valid_dirs = []

    try:
        folders = list(USB_PATH.iterdir())
    except OSError:
        return valid_dirs

    for folder in folders:
        if not folder.is_dir():
            continue

        found = False
        try:
            for subpath in folder.rglob("*"):
                if subpath.is_file() and subpath.suffix.lower() in VIDEO_EXTENSIONS:
                    valid_dirs.append(folder.name)
                    found = True
                    break
        except OSError:
            continue

        if found:
            continue

    return sorted(valid_dirs)

# TO DO REMOVE
def load_state(dirs):
    if STATE_FILE.exists():
        folder = STATE_FILE.read_text().strip()
        if folder in dirs:
            return dirs.index(folder)
    return 0

# TO DO REMOVE
def save_state(index, dirs):
    STATE_FILE.write_text(dirs[index])

# TO DO REMOVE
def set_video_looper_path(folder_name):
    if not VIDEO_LOOPER_CONFIG.exists():
        print(f"Video Looper Config nicht gefunden: {VIDEO_LOOPER_CONFIG}")
        return

    new_path = str(USB_PATH / folder_name)
    lines = VIDEO_LOOPER_CONFIG.read_text().splitlines(True)
    replaced = False

    for index, line in enumerate(lines):
        stripped = line.lstrip()
        if not stripped.startswith("path"):
            continue

        if "=" not in stripped:
            continue

        key = stripped.split("=", 1)[0].strip()
        if key != "path":
            continue

        indentation = line[: len(line) - len(stripped)]
        lines[index] = f"{indentation}path = {new_path}\n"
        replaced = True
        break

    if not replaced:
        if lines and not lines[-1].endswith("\n"):
            lines[-1] = f"{lines[-1]}\n"
        lines.append(f"path = {new_path}\n")

    new_text = "".join(lines)
    try:
        VIDEO_LOOPER_CONFIG.write_text(new_text)
    except PermissionError:
        try:
            subprocess.run(
                ["sudo", "-n", "tee", str(VIDEO_LOOPER_CONFIG)],
                input=new_text.encode("utf-8"),
                check=True,
                timeout=5,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            print(f"Keine Berechtigung zum Schreiben: {VIDEO_LOOPER_CONFIG}")
            return

    restart_video_looper()

# Start VLC Player
def start_vlc_player():
    video_path = USB_PATH / dirs[current_index]
    vlc_command = [
        "vlc",
        "--loop",
        "--fullscreen",
        "--no-video-title-show",
        str(video_path),
    ]
    subprocess.Popen(vlc_command)

# Restart VLC Player
def restart_vlc_player():
    subprocess.run(["pkill", "vlc"])
    time.sleep(1)
    start_vlc_player()


##########################
##### INITIALISATION #####
##########################

# Wait for USB Stick to be Mounted
while not is_usb_ready():
    print("Waiting for Stick...")
    time.sleep(1)

# Get Video Directories
dirs = get_video_dirs()
while not dirs:
    print("Searching for Folders...")
    time.sleep(2)
    dirs = get_video_dirs()

# Load Current Video Directory
current_index = load_state(dirs)

# Start VLC Player
start_vlc_player()


##########################
##### BUTTON CONTROL #####
##########################

try:
    while True:
        try:

            # Button: Next Folder
            if GPIO.input(BUTTON_NEXTFOLDER) == GPIO.LOW:
                current_index = (current_index + 1) % len(dirs)
                print(f"Button pressed → Switch to: {dirs[current_index]}")
                # save_state(current_index, dirs)
                # set_video_looper_path(dirs[current_index])
                restart_vlc_player()

                time.sleep(1)
                while GPIO.input(BUTTON_NEXTFOLDER) == GPIO.LOW:
                    time.sleep(0.1)

            time.sleep(0.1)
        except Exception as error:
            print(f"ERROR: {error}")
            time.sleep(1)

finally:
    GPIO.cleanup()