#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time
import os
import subprocess
import socket
import urllib.parse
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
VIDEO_EXTENSIONS = [".avi", ".mov", ".mkv", ".mp3", ".mp4", ".m4a"]
VLC_RC_HOST = "127.0.0.1"
VLC_RC_PORT = 4212

# LED Display
LED_SCROLL_DELAY = 0.15
led_scroll_text = ""
led_scroll_index = 0
led_scroll_next_time = 0
led_current_message = ""
led_temp_message_until = 0
LED_TEMP_MESSAGE_SECONDS = 2.0

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
        log_message(f"State File is a Directory: {STATE_FILE}")
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
    vlc_command = ["vlc", "--loop", "--fullscreen", "--audio-visual=visual", "--no-video-title-show"]
    if RANDOM:
        vlc_command.append("--random")
    vlc_command.extend(["--extraintf", "rc", "--rc-host", f"{VLC_RC_HOST}:{VLC_RC_PORT}", str(video_path)])

    try:
        log_message(f"Playing Videos in Folder: {dir}")
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

# VLC RC Communication
def vlc_rc_send(command, expect_response=False):
    try:
        with socket.create_connection((VLC_RC_HOST, VLC_RC_PORT), timeout=0.25) as handle:
            handle.sendall(f"{command}\n".encode("utf-8", errors="ignore"))

            if not expect_response:
                return ""

            handle.settimeout(0.15)
            chunks = []
            while True:
                try:
                    chunk = handle.recv(4096)
                    if not chunk:
                        break
                    chunks.append(chunk)
                except (socket.timeout, TimeoutError):
                    break

            return b"".join(chunks).decode("utf-8", errors="ignore")
    except Exception:
        return ""

def vlc_extract_file_name(value):
    if not value:
        return ""

    cleaned = str(value).strip().strip('"').strip("'")
    if not cleaned:
        return ""

    if cleaned.startswith("file://"):
        cleaned = cleaned[7:]

    cleaned = urllib.parse.unquote(cleaned)
    cleaned = cleaned.replace("\\", "/")
    return Path(cleaned).name

def vlc_get_current_file_name_from_status():
    response = vlc_rc_send("status", expect_response=True)
    if not response:
        return ""

    for line in response.splitlines():
        cleaned = line.strip()
        lower = cleaned.lower()

        if "new input:" in lower:
            value = cleaned.split(":", 1)[1].strip()
            file_name = vlc_extract_file_name(value)
            if file_name:
                return file_name

        if lower.startswith("input:"):
            value = cleaned.split(":", 1)[1].strip()
            file_name = vlc_extract_file_name(value)
            if file_name:
                return file_name

        if lower.startswith("filename:"):
            value = cleaned.split(":", 1)[1].strip()
            file_name = vlc_extract_file_name(value)
            if file_name:
                return file_name

    return ""

def vlc_get_current_file_name_from_info():
    response = vlc_rc_send("info", expect_response=True)
    if not response:
        return ""

    for line in response.splitlines():
        cleaned = line.strip()
        lower = cleaned.lower()

        if lower.startswith("filename:"):
            value = cleaned.split(":", 1)[1].strip()
            file_name = vlc_extract_file_name(value)
            if file_name:
                return file_name

        if lower.startswith("location:"):
            value = cleaned.split(":", 1)[1].strip()
            file_name = vlc_extract_file_name(value)
            if file_name:
                return file_name

    return ""

# Get Current Playing File Name from VLC
def vlc_get_current_file_name():
    file_name = vlc_get_current_file_name_from_status()
    if file_name:
        return file_name

    file_name = vlc_get_current_file_name_from_info()
    if file_name:
        return file_name

    response = vlc_rc_send("playlist", expect_response=True)
    if not response:
        return ""

    best_file_name = ""
    fallback_text = ""
    for line in response.splitlines():
        cleaned = line.strip()
        if "*" not in cleaned:
            continue

        if " - " not in cleaned:
            continue

        item_text = cleaned.split(" - ", 1)[1].strip()
        if not item_text:
            continue

        # Avoid playlist tree/group nodes like "Folder (played 1 times)"
        if "(played" in item_text.lower():
            fallback_text = item_text
            continue

        if item_text.startswith("file://"):
            decoded = urllib.parse.unquote(item_text[7:])
            decoded = decoded.replace("\\", "/")
            file_name = Path(decoded).name
            if file_name:
                best_file_name = file_name
            continue

        lower_item = item_text.lower()
        for extension in VIDEO_EXTENSIONS:
            if lower_item.endswith(extension):
                best_file_name = Path(item_text).name
                break

    if best_file_name:
        return best_file_name

    if fallback_text:
        return ""

    return ""

# Check if VLC is Paused
def vlc_is_paused():
    response = vlc_rc_send("status", expect_response=True)
    if not response:
        return False

    lower = response.lower()
    if "state paused" in lower:
        return True
    if "state playing" in lower:
        return False
    if "paused" in lower and "state" in lower:
        return True

    return False

# LED Display Scrolling Tick
def display_tick(seg):
    global led_scroll_index
    global led_scroll_next_time

    if not led_scroll_text:
        return

    now = time.time()
    if now < led_scroll_next_time:
        return

    width = seg.device.width
    max_start_index = len(led_scroll_text) - width
    if max_start_index < 0:
        return

    if led_scroll_index > max_start_index:
        led_scroll_index = 0

    seg.text = led_scroll_text[led_scroll_index:led_scroll_index + width]
    led_scroll_index += 1
    led_scroll_next_time = now + LED_SCROLL_DELAY

# Show Message on LED Display
def show_message(seg, msg, scroll_delay=LED_SCROLL_DELAY):
    global led_scroll_text
    global led_scroll_index
    global led_scroll_next_time
    global LED_SCROLL_DELAY
    global led_current_message

    width = seg.device.width
    message_text = str(msg).upper()
    led_current_message = message_text
    LED_SCROLL_DELAY = float(scroll_delay)

    if len(message_text) <= width:
        led_scroll_text = ""
        led_scroll_index = 0
        led_scroll_next_time = 0
        seg.text = message_text.ljust(width)
        return

    padding = " " * width
    led_scroll_text = f"{padding}{message_text}{padding}"
    led_scroll_index = 0
    led_scroll_next_time = 0
    seg.text = led_scroll_text[:width]

# Show Temporary Message on LED Display
def show_temporary_message(seg, msg, seconds=LED_TEMP_MESSAGE_SECONDS):
    global led_temp_message_until

    show_message(seg, msg)
    led_temp_message_until = time.time() + float(seconds)

def is_temporary_message_active():
    return time.time() < led_temp_message_until

def clear_temporary_message():
    global led_temp_message_until

    led_temp_message_until = 0


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
    log_message("Waiting for USB")
    time.sleep(1)

# Get Video Directories
dirs = list_video_folders()
while not dirs:
    log_message("Searching for Folders")
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
    last_video_name = ""
    last_video_query_time = 0
    is_paused_display_active = False
    last_button_skp10_state = GPIO.HIGH
    last_button_rew10_state = GPIO.HIGH
    last_button_skp10_time = 0
    last_button_rew10_time = 0
    while True:
        try:
            display_tick(seg)

            if not is_temporary_message_active() and led_temp_message_until:
                clear_temporary_message()
                if is_paused_display_active:
                    show_message(seg, "PAUSE")
                else:
                    if last_video_name:
                        show_message(seg, last_video_name)
                    else:
                        current_file_name = vlc_get_current_file_name()
                        if current_file_name:
                            last_video_name = Path(current_file_name).stem
                            show_message(seg, last_video_name)

            # Check Current Video Every Second
            now = time.time()
            if not is_paused_display_active and now - last_video_query_time >= 1.0:
                current_file_name = vlc_get_current_file_name()
                if current_file_name:
                    current_video_name = Path(current_file_name).stem
                    if current_video_name and current_video_name != last_video_name:
                        log_message(f"Playing: {current_video_name}")
                        last_video_name = current_video_name
                        if not is_temporary_message_active():
                            show_message(seg, current_video_name)
                last_video_query_time = now

            # Button: Next Folder
            if GPIO.input(BUTTON_NEXTFOLDER) == GPIO.LOW:
                current_index = (current_index + 1) % len(dirs)
                log_message(f"Switch Folder: {dirs[current_index]}")
                save_state(current_index, dirs)
                start_vlc_player(dirs[current_index], restart=True)
                show_message(seg, f"{dirs[current_index]}".upper())

                last_video_name = ""
                last_video_query_time = 0

                time.sleep(1)
                while GPIO.input(BUTTON_NEXTFOLDER) == GPIO.LOW:
                    time.sleep(0.1)

            # Button: Next Video
            if GPIO.input(BUTTON_NEXTVIDEO) == GPIO.LOW:
                log_message("Next Video")
                subprocess.run(["xdotool", "key", "n"])

                time.sleep(0.5)
                while GPIO.input(BUTTON_NEXTVIDEO) == GPIO.LOW:
                    time.sleep(0.1)
            
            # Button: Pause/Play
            if GPIO.input(BUTTON_PAUSE) == GPIO.LOW:
                log_message("Pause/Play")
                if is_paused_display_active:
                    subprocess.run(["xdotool", "key", "space"])
                    is_paused_display_active = False

                    if last_video_name:
                        show_message(seg, last_video_name)
                    else:
                        current_file_name = vlc_get_current_file_name()
                        if current_file_name:
                            last_video_name = Path(current_file_name).stem
                            show_message(seg, last_video_name)

                    last_video_query_time = time.time()
                else:
                    subprocess.run(["xdotool", "key", "space"])

                    pause_wait_seconds = 0
                    paused_now = False
                    while pause_wait_seconds < 1.0:
                        paused_now = vlc_is_paused()
                        if paused_now:
                            break
                        time.sleep(0.1)
                        pause_wait_seconds += 0.1

                    if paused_now:
                        is_paused_display_active = True
                        show_message(seg, "PAUSE")

                time.sleep(0.1)
                while GPIO.input(BUTTON_PAUSE) == GPIO.LOW:
                    time.sleep(0.1)
            
            # Button: Language
            if GPIO.input(BUTTON_LANGUAGE) == GPIO.LOW:
                log_message("Change Audio Track")
                subprocess.run(["xdotool", "key", "b"])

                time.sleep(0.1)
                while GPIO.input(BUTTON_LANGUAGE) == GPIO.LOW:
                    time.sleep(0.1)
            
            # Button: Skip 10 Seconds
            button_skp10_state = GPIO.input(BUTTON_SKP10)
            if button_skp10_state == GPIO.LOW and last_button_skp10_state == GPIO.HIGH:
                now = time.time()
                if now - last_button_skp10_time >= 0.3:
                    last_button_skp10_time = now
                    log_message("Skip Forward 10 Seconds")
                    subprocess.run(["xdotool", "key", "Right"])
                    show_temporary_message(seg, "PLUS  10")
            last_button_skp10_state = button_skp10_state
            
            # Button: Rewind 10 Seconds
            button_rew10_state = GPIO.input(BUTTON_REW10)
            if button_rew10_state == GPIO.LOW and last_button_rew10_state == GPIO.HIGH:
                now = time.time()
                if now - last_button_rew10_time >= 0.3:
                    last_button_rew10_time = now
                    log_message("Skip Backward 10 Seconds")
                    subprocess.run(["xdotool", "key", "Left"])
                    show_temporary_message(seg, "MINUS 10")
            last_button_rew10_state = button_rew10_state

            time.sleep(0.1)
        except Exception as error:
            log_message(f"Error: {error}")
            time.sleep(1)

finally:
    log_message("Script Terminated")
    GPIO.cleanup()
