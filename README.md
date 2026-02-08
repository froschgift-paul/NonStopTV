# NonStopTV
VLC Video Looper Script for Raspberry Pi

## Features
A python script that autostarts VLC player (in Fullscreen) and plays videos (randomly) from usb stick.

- Automatically mounts usb stick on bootup
- Detects folders on usb containing videos
- Creates memory file to remember current folder
- GPIO buttons for
  - Switch to next folder on usb
  - Next video
  - Swap language
  - Pause video
  - Skip 10 seconds
  - Rewind 10 seconds
- LED driver support
- Options for LED light and volume

## Setup
As the script is built for a Raspberry Pi 2 with Buster, this setup may be different for newer systems. Good luck.
Note that this guide was written while the system was invented, tested and debugged. So there may be some minor issues I am happy to fix if you report inconsistencies.

### 1. Craft Hardware
1. Get old Raspberry Pi
2. Connect screen (preferably with RF modulator to 80s kitchen tube tv)
3. Solder wanted buttons and 7-Segment display to GPIO

### 2. Enchant Software
1. Format sd card (exFAT)
2. Install linux (easyest via Raspberry Pi Imager)
3. Install `vlc`, `xdotool`,  `spidev` and `luma.led-matrix`
Note that older Raspberry Pis are not secure enough to be left connected to the internet and should be run offline.

### 3. Bag Scripts
1. Copy `nonstoptv.py` to `/boot`
2. Copy `nonstoptv.desktop` to `/home/pi/.config/autostart`

### 4. Automount USB Stick
1. Format usb stick (exFAT)
2. Find out UUID of stick: `sudo blkid /dev/sda1`
3. Edit `/etc/fstab` with `UUID=[1234-5678]  /media/pi/USB  [format]  defaults,nofail  0  0`
4. Create mounting point
  ```
  sudo mkdir -p /media/pi/USB
  sudo chown pi:pi /media/pi/USB
  sudo mount -a
  ```
Troubleshooting: Note that you need to create a new mounting point if you change your usb stick or format it!

### 5. Gather Videos
Fill usb stick with videos (use subfolders)
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
(After first launch you will find an .ini and a .log file in your usb drive where you can view and tweak details).