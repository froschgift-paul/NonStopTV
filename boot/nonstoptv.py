#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time
import os
import subprocess
from pathlib import Path
from luma.led_matrix.device import max7219
from luma.core.interface.serial import spi, noop
from luma.core.virtual import sevensegment, viewport

# https://wiki.ubuntuusers.de/xdotool/
# https://wiki.ubuntuusers.de/VLC/
# https://linuxcommandlibrary.com/man/vlc


####################
##### SETTINGS #####
####################

# Paths
USB_PATH = Path("/media/pi/USB/")
STATE_FILE = USB_PATH / "nonstoptv-config.ini"
LOG_FILE = USB_PATH / "nonstoptv-report.log"

# Config
VIDEO_EXTENSIONS = [".avi", ".mov", ".mkv", ".mp3", ".mp4"]

# GPIO
GPIO.setmode(GPIO.BCM)
BUTTON_NEXTFOLDER = 21
BUTTON_NEXTVIDEO = 26
BUTTON_PAUSE = 20
BUTTON_LANGUAGE = 19
BUTTON_SKP10 = 13
BUTTON_REW10 = 16
GPIO.setup(BUTTON_NEXTFOLDER, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BUTTON_NEXTVIDEO, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BUTTON_PAUSE, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BUTTON_LANGUAGE, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BUTTON_SKP10, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BUTTON_REW10, GPIO.IN, pull_up_down=GPIO.PUD_UP)


#####################
##### FUNCTIONS #####
#####################

def log_message(message):
    try:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with LOG_FILE.open("ab") as log:
            log.write(f"--- {timestamp} | {message}\n".encode("utf-8", errors="ignore"))
    except Exception:
        pass

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
        log_message(f"State File Is A Directory: {STATE_FILE}")
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
        log_message(f"State Write Failed: {STATE_FILE} ({error})")
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
        subprocess.run(["pkill", "vlc"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
        log_message(f"Starting With Folder: {dir}")
        with LOG_FILE.open("ab") as log:
            process = subprocess.Popen(vlc_command, stdout=log, stderr=log)
        log_message(f"VLC Started (pid={process.pid})")
    except Exception as error:
        log_message(f"VLC Start Failed: {error}")

# Kill Running Instances of This Script
def kill_other_instances():
    try:
        subprocess.run(["pkill", "vlc"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        result = subprocess.run(["pgrep", "-f", "/boot/nonstoptv.py"], capture_output=True, text=True)
        for pid_text in result.stdout.split():
            if not pid_text.isdigit():
                continue
            pid = int(pid_text)
            if pid == os.getpid():
                continue
            os.kill(pid, 15)
    except Exception:
        pass

# Show Message on LED Display
def show_message(seg, msg, delay=0.1):
    seg.text = msg
    time.sleep(delay)
    # width = device.width
    # padding = " " * width
    # msg = padding + msg + padding
    # n = len(msg)
 
    # virtual = viewport(device, width=n, height=8)
    # sevensegment(virtual).text = msg
    # for i in reversed(list(range(n - width))):
    #     virtual.set_position((i, 0))
    #     time.sleep(delay)


##########################
##### INITIALISATION #####
##########################

# Kill Other Instances
kill_other_instances()

# Reset Log File
try:
    with LOG_FILE.open("wb") as log:
        log.write(b"")
except Exception:
    pass

log_message("Script Started")

# Load Config
random_text = ini_get("random", None)
if random_text is None:
    RANDOM = True
    ini_set("random", "true")
elif random_text.lower() in ["1", "true", "yes", "on"]:
    RANDOM = True
elif random_text.lower() in ["0", "false", "no", "off"]:
    RANDOM = False
else:
    RANDOM = True
    ini_set("random", "true")

volume_text = ini_get("volume", None)
volume_value = -1
if volume_text is None:
    volume_value = 100
    ini_set("volume", "100")
elif volume_text.isdigit():
    volume_value = int(volume_text)

if volume_value < 0 or volume_value > 100:
    VOLUME = 100
    ini_set("volume", "100")
else:
    VOLUME = volume_value

ledbrightness_text = ini_get("ledbrightness", None)
ledbrightness_value = -1
if ledbrightness_text is None:
    ledbrightness_value = 100
    ini_set("ledbrightness", "100")
elif ledbrightness_text.isdigit():
    ledbrightness_value = int(ledbrightness_text)

if ledbrightness_value < 0 or ledbrightness_value > 100:
    ledbrightness = 100
    ini_set("ledbrightness", "100")
else:
    ledbrightness = int(round(ledbrightness_value * 2.55))

# Wait for USB Stick to be Mounted
while not is_usb_ready():
    log_message("Waiting For USB")
    time.sleep(1)

# Get Video Directories
dirs = list_video_folders()
while not dirs:
    log_message("Searching For Folders")
    time.sleep(2)
    dirs = list_video_folders()

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

# LED Setup
serial = spi(port=0, device=0, gpio=noop())
device = max7219(serial, cascaded=1)
seg = sevensegment(device)
seg.device.contrast(ledbrightness)
show_message(seg, f"{dirs[current_index]}".upper())


##########################
##### BUTTON CONTROL #####
##########################

try:
    while True:
        try:
            # Button: Next Folder
            if GPIO.input(BUTTON_NEXTFOLDER) == GPIO.LOW:
                current_index = (current_index + 1) % len(dirs)
                log_message(f"Switch Folder: {dirs[current_index]}")
                save_state(current_index, dirs)
                start_vlc_player(dirs[current_index], restart=True)
                show_message(seg, f"{dirs[current_index]}".upper())

                time.sleep(1)
                while GPIO.input(BUTTON_NEXTFOLDER) == GPIO.LOW:
                    time.sleep(0.1)

            # Button: Next Video
            if GPIO.input(BUTTON_NEXTVIDEO) == GPIO.LOW:
                log_message("Next Video")
                subprocess.run(["xdotool", "key", "n"])

                time.sleep(1)
                while GPIO.input(BUTTON_NEXTVIDEO) == GPIO.LOW:
                    time.sleep(0.1)
            
            # Button: Pause/Play
            if GPIO.input(BUTTON_PAUSE) == GPIO.LOW:
                log_message("Pause/Play")
                subprocess.run(["xdotool", "key", "space"])

                time.sleep(1)
                while GPIO.input(BUTTON_PAUSE) == GPIO.LOW:
                    time.sleep(0.1)
            
            # Button: Language
            if GPIO.input(BUTTON_LANGUAGE) == GPIO.LOW:
                log_message("Change Audio Track")
                subprocess.run(["xdotool", "key", "b"])

                time.sleep(1)
                while GPIO.input(BUTTON_LANGUAGE) == GPIO.LOW:
                    time.sleep(0.1)
            
            # Button: Skip 10 Seconds
            if GPIO.input(BUTTON_SKP10) == GPIO.LOW:
                log_message("Skip Forward 10 Seconds")
                subprocess.run(["xdotool", "key", "Right"])
                show_message(seg, f"PLUS 10")

                time.sleep(1)
                while GPIO.input(BUTTON_SKP10) == GPIO.LOW:
                    time.sleep(0.1)
            
            # Button: Rewind 10 Seconds
            if GPIO.input(BUTTON_REW10) == GPIO.LOW:
                log_message("Skip Backward 10 Seconds")
                subprocess.run(["xdotool", "key", "Left"])
                show_message(seg, f"MINUS 10")
                time.sleep(1)
                while GPIO.input(BUTTON_REW10) == GPIO.LOW:
                    time.sleep(0.1)

            time.sleep(0.1)
        except Exception as error:
            log_message(f"Error: {error}")
            time.sleep(1)

finally:
    log_message("Script Terminated")
    GPIO.cleanup()
