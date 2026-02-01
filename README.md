# NonStopTV
VLC Video Looper Script for Raspberry Pi

## Features
A Python-Script that autostarts VLC Player (in Fullscreen) and plays videos (randomly) from usb stick.

- Automatically Mounts USB Stick on Bootup
- Detects Folders on USB Containing Videos
- Creates Memory File to Remember Current Folder and Video
- GPIO-Buttons for
  - Switch to next Folder on USB
  - Next Video
  - Swap Language
  - Pause Video
  - Skip 10 Seconds
  - Rewind 10 Seconds
- LED Driver Support

## Setup
As the script is built for a Raspberry Pi 2 with Buster, this setup may be different for newer systems. Good luck.

### 1. Craft Hardware
1. Get old Raspberry Pi
2. Connect screen (preferably with RF modulator to 80s kitchen tube tv)
3. Solder wanted buttons and 7-Segment display to GPIO

### 2. Enchant Software
1. Format sd card (exFAT)
2. Install linux (easyest via Raspberry Pi Imager)
3. Install `vlc`, `xdotool` and `spidev`

### 3. Bag Scripts
1. Copy `nonstoptv.py` to `/boot`
2. Copy `nonstoptv.desktop` to `/home/pi/.config/autostart`

### 4. Automount USB Stick
1. Find out UUID of stick: `sudo blkid /dev/sda1`
2. Edit `/etc/fstab` with `UUID=[1234-5678]  /media/pi/USB  [format]  defaults,nofail  0  0`
3. Create mounting point
  ```
  sudo mkdir -p /media/pi/USB
  sudo chown pi:pi /media/pi/USB
  sudo mount -a
  ```
Troubleshooting: Note that you need to create a new mounting point if you change your usb stick or format it!

### 5. Gather Videos
1. Format usb stick (exFAT)
2. Fill with videos (with subfolders)
  ```
  USB/
  ├── Simpsons/
  │   ├── ep01.mkv
  │   └── ep02.mkv
  ├── Pokemon/
  │   ├── ep01.mkv
  │   └── ep02.mkv
  ...
  ```

### 6. Enjoy
Reboot and you should be ready to go.
(After first Launch you will find an .ini and a .log file in `/home/pi/` where you can view and tweak details).