#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time
import os
import subprocess
from pathlib import Path

# https://wiki.ubuntuusers.de/xdotool/
# https://wiki.ubuntuusers.de/VLC/
# https://linuxcommandlibrary.com/man/vlc


####################
##### SETTINGS #####
####################

# Paths
USB_PATH = Path("/media/pi/USB")
STATE_DIR = Path("/home/pi/")
STATE_FILE = STATE_DIR / "nonstoptv.ini"
LOG_FILE = STATE_DIR / "nonstoptv_vlc.log"

# Config
VIDEO_EXTENSIONS = [".avi", ".mov", ".mkv", ".mp4"]
RANDOM = True
VOLUME = 100

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
def list_video_folders():
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

# Read INI State
def ini_get(key, default_value = ""):
    if not STATE_FILE.exists():
        return default_value

    try:
        lines = STATE_FILE.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return default_value

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if stripped.startswith("#"):
            continue

        if "=" not in stripped:
            continue

        stored_key, stored_value = stripped.split("=", 1)
        if stored_key.strip() != key:
            continue

        return stored_value.strip()

    return default_value

# Write INI State
def ini_set(key, value):
    if STATE_FILE.exists() and STATE_FILE.is_dir():
        print(f"State file path is a directory: {STATE_FILE}")
        return False

    value_text = str(value).replace("\r", "").replace("\n", " ")
    lines = []
    try:
        if STATE_FILE.exists():
            lines = STATE_FILE.read_text(encoding="utf-8", errors="ignore").splitlines(True)
    except Exception:
        lines = []

    replaced = False
    output_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            output_lines.append(line)
            continue

        if stripped.startswith("#"):
            output_lines.append(line)
            continue

        if "=" not in stripped:
            output_lines.append(line)
            continue

        stored_key = stripped.split("=", 1)[0].strip()
        if stored_key != key:
            output_lines.append(line)
            continue

        output_lines.append(f"{key}={value_text}\n")
        replaced = True

    if not replaced:
        if output_lines and not output_lines[-1].endswith("\n"):
            output_lines[-1] = f"{output_lines[-1]}\n"
        output_lines.append(f"{key}={value_text}\n")

    temp_file = STATE_FILE.with_suffix(f"{STATE_FILE.suffix}.tmp")
    try:
        try:
            STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        with temp_file.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write("".join(output_lines))
        os.replace(temp_file, STATE_FILE)
        return True
    except Exception as error:
        print(f"Could not write state file: {STATE_FILE} ({error})")
        try:
            with LOG_FILE.open("ab") as log:
                log.write(f"\n--- {time.strftime('%Y-%m-%d %H:%M:%S')} STATE WRITE FAILED: {STATE_FILE} ({error}) ---\n".encode("utf-8", errors="ignore"))
        except Exception:
            pass
        try:
            if temp_file.exists():
                temp_file.unlink()
        except Exception:
            pass

    return False

# Load State
def load_state(dirs):
    selected_folder = ini_get("folder", "")
    if selected_folder in dirs:
        return dirs.index(selected_folder)
    return 0

def save_state(index, dirs):
    if index < 0 or index >= len(dirs):
        ini_set("folder", "")
        return

    ini_set("folder", dirs[index])

# (Re)Start VLC Player
def start_vlc_player(dir, restart =False):
    if restart:
        subprocess.run(["pkill", "vlc"])
        time.sleep(1)
    video_path = USB_PATH / dir
    vlc_command = [
        "vlc",
        "--loop",
        "--fullscreen",
        "--no-video-title-show",
        str(video_path),
    ]

    if RANDOM:
        vlc_command.insert(4, "--random")

    try:
        with LOG_FILE.open("ab") as log:
            header = f"\n--- {time.strftime('%Y-%m-%d %H:%M:%S')} START VLC: {' '.join(vlc_command)} ---\n"
            log.write(header.encode("utf-8", errors="ignore"))
            process = subprocess.Popen(vlc_command, stdout=log, stderr=log)
        print(f"VLC started (pid={process.pid})")
    except Exception as error:
        print(f"Could not start VLC: {error}")


##########################
##### INITIALISATION #####
##########################

# Wait for USB Stick to be Mounted
while not is_usb_ready():
    print("Waiting for Stick...")
    time.sleep(1)

# Get Video Directories
dirs = list_video_folders()
while not dirs:
    print("Searching for Folders...")
    time.sleep(2)
    dirs = list_video_folders()

# Delete Old Log File
if LOG_FILE.exists():
    try:
        LOG_FILE.unlink()
    except OSError:
        pass

# Wait For X11 Session
display_value = os.environ.get("DISPLAY", "")
if display_value.startswith(":"):
    display_number_text = display_value[1:].split(".", 1)[0]
    if display_number_text.isdigit():
        x11_socket = Path(f"/tmp/.X11-unix/X{display_number_text}")
        display_wait_seconds = 0
        while not x11_socket.exists() and display_wait_seconds < 20:
            time.sleep(1)
            display_wait_seconds += 1

# Initially Start VLC Player
subprocess.run(["amixer", "set", "PCM", f"{VOLUME}%"])
current_index = load_state(dirs)
save_state(current_index, dirs)
start_vlc_player(dirs[current_index])


##########################
##### BUTTON CONTROL #####
##########################

try:
    while True:
        try:
            # Button: Next Folder
            if GPIO.input(BUTTON_NEXTFOLDER) == GPIO.LOW:
                current_index = (current_index + 1) % len(dirs)
                print(f"Switch Folder to: {dirs[current_index]}")
                save_state(current_index, dirs)
                start_vlc_player(dirs[current_index], restart=True)

                time.sleep(1)
                while GPIO.input(BUTTON_NEXTFOLDER) == GPIO.LOW:
                    time.sleep(0.1)

            time.sleep(0.1)
        except Exception as error:
            print(f"ERROR: {error}")
            time.sleep(1)

finally:
    GPIO.cleanup()
