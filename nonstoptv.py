#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time
from pathlib import Path


# Settings
BUTTON_PIN = 21
USB_PATH = Path("/media/pi/USB")
STATE_FILE = Path("/home/pi/videofolder")
VIDEO_EXTENSIONS = [".avi", ".mov", ".mkv", ".mp4"]

while not USB_PATH.exists() or not any(USB_PATH.iterdir()):
    print("Warte auf USB-Stick...")
    time.sleep(2)

GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)


# --- Hilfsfunktionen ---
def get_video_dirs():
    valid_dirs = []

    for folder in USB_PATH.iterdir():
        if not folder.is_dir():
            continue

        found = False
        for subpath in folder.rglob("*"):
            if subpath.is_file() and subpath.suffix.lower() in VIDEO_EXTENSIONS:
                valid_dirs.append(folder.name)
                found = True
                break

        if found:
            continue

    return sorted(valid_dirs)

def load_state(dirs):
    if STATE_FILE.exists():
        folder = STATE_FILE.read_text().strip()
        if folder in dirs:
            return dirs.index(folder)
    return 0

def save_state(index, dirs):
    STATE_FILE.write_text(dirs[index])


# Initializing
dirs = get_video_dirs()
if not dirs:
    print("Keine Ordner gefunden!")
    exit(1)

current_index = load_state(dirs)
print(f"Start mit Ordner: {dirs[current_index]}")


# Loop
try:
    while True:
        if GPIO.input(BUTTON_PIN) == GPIO.LOW:
            # nächster Ordner
            current_index = (current_index + 1) % len(dirs)
            save_state(current_index, dirs)
            print(f"Taster gedrückt → Wechsel zu: {dirs[current_index]}")

            # Entprellen + warten bis Taster losgelassen wird
            time.sleep(0.4)
            while GPIO.input(BUTTON_PIN) == GPIO.LOW:
                time.sleep(0.05)

        time.sleep(0.1)

finally:
    GPIO.cleanup()
