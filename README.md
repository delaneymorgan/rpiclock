# rpiclock
This repository contains the rpiclock application designed to run on a Raspberry Pi 4 running Bullfrog with the 7" touchscreen under Python 3.11.

It should run on a standard Linux desktop - without the backlight control of course.

---
### Obtain repository:
If you're reading this, chances are you already have some access to it.

    cd ~/<project-dir>/
    git clone --recursive https://github.com/delaneymorgan/rpiclock.git

If you absolutely need python 2 (but I don't recommend it unless you're running Raspbian pre-Buster), look for the "Python_2.7_Compatible" tag.

### Virtual Environment:

rpiclock runs under a virtual environment.  It isn't dockerised because AFAIK Kivy and the backlight module defies that.

    cd ~/project/rpiclock
    python3 -m venv .venv

If the .venv/bin/activate script doesn't appear, just do...

    python3 -m venv .venv

...again.

There is a requirements.txt, but I've found it rarely works.  Try it, otherwise install the packages manually.

---
### 7" Touchscreen Setup:
Follow link for the definitive [RPi 7" touchscreen instructions](https://www.element14.com/community/docs/DOC-78156/l/raspberry-pi-7-touchscreen-display)

#### Screen Orientation

If you've mounted the display in one of its many cases, you might find the display upside-down with respect to the case.
Fret not.
Raspbian Bullseye now manages this with its GUI.

Select:
* Preferences
  * Screen Configuration
    * You'll see the 7" display as an icon labelled "DSI-1"
    * Right-click the display icon
      * Select Orientation -> inverted
    * Press Apply

This should invert not just the display,
but importantly also the touch-screen coordinates.

#### Hide Cursor

    sudo apt update
    sudo apt install unclutter

Then you'll need to edit the following:

    cd /etc/xdg/lxsession/LXDE-pi
    sudo vim autostart

Add the following line:

    unclutter -ide 0

This will permanently hide the cursor whenever it is stationary.

#### Disable Screen Saver

Fortunately Bullseye also provides a simple GUI to manage the screen saver/blanking.

* Preferences
  * Raspberry Pi Configuration
    * Select the Display tab
      * Disable Screen Blanking

---
### 7 Segment Font:
You can get an old-school 7-segment font
(anything else just looks weird, but you have fun you) for the time display from [here](https://www.keshikan.net/fonts-e.html).

Install any font by copying it to the RPi's font directory.

    sudo cp <fontname> /usr/share/fonts

Note that the blinking colon effect works best with a fixed-width font.
The 7-segment font works nicely.

NOTE: Under Ubuntu 14, kivy doesn't find the custom font in the usual locations where the system installs them.
Try placing the font in the same folder as the rpiclock app.
Also, you will _definitely_ need the python 2 version of rpiclock.

---
### Auto-Start:
A systemd service is provided for use with Raspbian.  Assuming you have installed rpiclock under /home/pi/project/rpiclock, this should run as is.  Modify as required.

    cd /lib/systemd/system/
    sudo ln -s ~/project/rpiclock/rpiclock.service rpiclock.service
    sudo systemctl enable rpiclock.service
    sudo reboot

---
### Modules required:
See requirements.txt

    source ~/project/rpiclock/.venv/bin/activate
    pip3 install argparse configparser kivy pyowm python-dateutil rpi_backlight untangle

---
### Usage:
The rpi_backlight module requires the program to be run as sudo/root.

-v option can be supplied to enable the (rather limited) console logging.

Most useful parameters can be set via the config.ini file.

---
