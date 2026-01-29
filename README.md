# NonStopTV
VLC Video Looper Script for Raspberry Pi

## Features
A Python-Script that autostarts VLC Player (in Fullscreen) and plays Videos (Randomly) from USB Stick.

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
As the Script is built for a Raspberry Pi 2, this Setup is 

### Hardware
1. Get old Raspberry Pi
2. Connect Screen (preferably with RF Modulator to 80s Kitchen Tube TV)
3. Solder Wanted Buttons and 7-Segment Display to GPIO

## Prepare System
1. Format SD Card (exFAT) and Install Linux (easyest via Raspberry Pi Imager)
2. Format USB Stick (exFAT) and fill with Videos (with subfolders)
```
USB/
├── Simpsons/
│   ├── ep01.mkv
│   └── ep02.mkv
├── Pokemon/
│   └── ep01.mkv
...
```

### Automount USB Stick
1. Find out UUID of Stick: `sudo blkid /dev/sda1`
2. Edit `/etc/fstab` with `UUID=[1234-5678]  /media/pi/USB  [format]  defaults,nofail  0  0`
3. Create Mounting Point
  ```
  sudo mkdir -p /media/pi/USB
  sudo chown pi:pi /media/pi/USB
  sudo mount -a
  ```
Troubleshooting: Note that you need to create a new Mounting Point if you change your USB Stick or format it

### Autostart Script
1. Copy `nonstoptv.py` into `/boot`
2. Copy `nonstoptv.desktop` into `/home/pi/.config/autostart`
