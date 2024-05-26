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
Raspbian Bullseye/Bullfrog now manages this with its GUI.

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

First you'll need to discover which windowing system your system is using:

    echo $XDG_SESSION_TYPE

##### For X11

    sudo apt update
    sudo apt install unclutter

Then you'll need to edit the following:

    cd /etc/xdg/lxsession/LXDE-pi
    sudo vim autostart

Add the following line:

    unclutter -ide 0

This will permanently hide the cursor whenever it is stationary.

##### For Wayland

For Wayland you'll need to build a plugin to hide the cursor.

    sudo apt install -y interception-tools interception-tools-compat
    sudo apt install -y cmake
    cd ~
    git clone https://gitlab.com/interception/linux/plugins/hideaway.git
    cd hideaway
    cmake -B build -DCMAKE_BUILD_TYPE=Release
    cmake --build build
    sudo cp /home/<user>/hideaway/build/hideaway /usr/bin
    sudo chmod +x /usr/bin/hideaway

Next you'll need to configure Wayland to use the plugin.  Create the config as config.yaml and enter the following:

    - JOB: intercept $DEVNODE | hideaway 4 10000 10000 -512 -256 | uinput -d $DEVNODE
      DEVICE:
        EVENTS:
          EV_REL: [REL_X, REL_Y]

Now copy the config to the following directory:

    sudo cp /home/$USER/config.yaml /etc/interception/udevmon.d/config.yaml
    sudo systemctl restart udevmon

#### Disable Screen Saver

Fortunately Bullseye also provides a simple GUI to manage the screen saver/blanking.

* Preferences
  * Raspberry Pi Configuration
    * Select the Display tab
      * Disable Screen Blanking

#### Hide Taskbar
For this to work, you may need to first run:

	sudo rpi-update	

This is not to be taken lightly.
Check elsewhere for how to do this safely.

Then, in file .config/wf-panel-pi.ini ADD the following:

	autohide=true
	autohide_duration=500

Reboot and the program should now run without a visible taskbar,
and more importantly will use correct drawing coordinates.

---
### 7 Segment Font:
You can get an old-school 7-segment font
(anything else just looks weird, but you have fun you) for the time display from [here](https://www.keshikan.net/fonts-e.html).

Install any font by copying it to the RPi's font directory.

    sudo cp <fontname> /usr/share/fonts

Note that the blinking colon effect works best with a fixed-width font.
The Classic 7-segment font works nicely.

---
### Kivy Touch Support:
The configuration for Kivy, Wayland, and touch screen support isn't widely known AFAIK.  However, this procedure worked for me.  Run the application as a user for now.

    cd ~/<project-dir>/rpiclock
    source .venv/bin/activate
    ./rpiclock.py

Now use the mouse to click (or finger to touch) on the main time area.  This should exit the application.  You should find a default Kivy configuration in ~/.kivy/config.ini

Now edit this file and replace the input section with:

    [input]
    mouse = mouse
    hid_%(name)s = probesysfs,provider=hidinput

Remember this config only applies to the current user.  If you want to autostart rpiclock, or support the backlight you'll need to supply the same config for the root user.

    sudo cp ~/.kivy/config.ini /home/root/.kivy

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
