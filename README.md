# rpiclock
This repository contains the rpiclock application designed to run on a Raspberry Pi 2/3 with the 7" touchscreen under Python 3.x.

It should run on a standard Linux desktop - without the backlight control of course.

---
### Obtain repository:
If you're reading this, chances are you already have some access to it.

&nbsp;&nbsp;&nbsp;&nbsp;`cd ~/<project-dir>/`  
&nbsp;&nbsp;&nbsp;&nbsp;`git clone --recursive https://github.com/delaneymorgan/rpiclock.git`

If you absolutely need python 2 (but I don't recommend it unless you're running Raspbian pre-Buster), look for the "Python_2.7_Compatible" tag.


### Virtual Environment:

rpiclock runs under a virtual environment.  It isn't dockerised because AFAIK Kivy and the backlight module defies that.

&nbsp;&nbsp;&nbsp;&nbsp;`cd ~/project/rpiclock`
&nbsp;&nbsp;&nbsp;&nbsp;`python3 -m venv .venv`

If the .venv/bin/activate script doesn't appear, just do...

&nbsp;&nbsp;&nbsp;&nbsp;`python3 -m venv .venv`

...again.

There is a requirements.txt, but I've found it rarely works.  Try it, otherwise install the packages manually.

---
### 7" Touchscreen Setup:
Follow link for the definitive RPi 7" Touchscreen instructions.

&nbsp;&nbsp;&nbsp;&nbsp;`https://www.element14.com/community/docs/DOC-78156/l/raspberry-pi-7-touchscreen-display`

#### Screen Orientation

If you've mounted the display in one of its many cases, you might find the display upside-down with respect to the case.  Fret not.  You'll need to modify /boot/config.txt.

&nbsp;&nbsp;&nbsp;&nbsp;`sudo vim /boot/config.txt`  

Add the following line:

&nbsp;&nbsp;&nbsp;&nbsp;`lcd_rotate=2`  

Save and reboot.

#### Touch Events

Next you need to configure kivy to recognise touch events:

In ~/.kivy, edit config.ini and look for the input section.  Change it to:

&nbsp;&nbsp;&nbsp;&nbsp;`mouse = mouse`  
&nbsp;&nbsp;&nbsp;&nbsp;`mtdev_%(name)s = probesysfs,provider=mtdev`  
&nbsp;&nbsp;&nbsp;&nbsp;`hid_%(name)s = probesysfs,provider=hidinput`  

See:

&nbsp;&nbsp;&nbsp;&nbsp;`https://kivy.org/docs/installation/installation-rpi.html`

However, this only works for the current user.  If you run rpiclock as root, which you will if you auto-start or use the brightness control, you'll need to copy the working config to the root user's directory:

&nbsp;&nbsp;&nbsp;&nbsp;`cp -r ~/.kivy /root`  

#### Disable Screen Saver

You will also need to disable Raspbian's screen saver.  In:

&nbsp;&nbsp;&nbsp;&nbsp;`/etc/lightdm/lightdm.conf`

add:

&nbsp;&nbsp;&nbsp;&nbsp;`xserver-command=X -s 0 -dpms`

Reboot.

---
### 7 Segment Font:
You can get an old-school 7-segment font (anything else just looks weird, but you have fun you) for the time display from here:

&nbsp;&nbsp;&nbsp;&nbsp;`https://www.keshikan.net/fonts-e.html`

Install any font by copying it to the RPi's font directory.

&nbsp;&nbsp;&nbsp;&nbsp;`sudo cp <fontname> /usr/share/fonts`

Note that the blinking colon effect works best with a fixed-width font.  The 7-segment font works nicely.

NOTE: Under Ubuntu 14, kivy doesn't find the custom font in the usual locations where the system installs them.  Try placing the font in the same folder as the rpiclock app.  Also, you will _definitely_ need the python 2 version of rpiclock.

---
### Auto-Start:
A systemd service is provided for use with Raspbian.  Assuming you have installed rpiclock under /home/pi/project/rpiclock, this should run as is.  Modify as required.

&nbsp;&nbsp;&nbsp;&nbsp;`cd /lib/systemd/system/`  
&nbsp;&nbsp;&nbsp;&nbsp;`sudo ln -s ~/project/rpiclock/rpiclock.service rpiclock.service`  
&nbsp;&nbsp;&nbsp;&nbsp;`sudo systemctl enable rpiclock.service`  
&nbsp;&nbsp;&nbsp;&nbsp;`sudo reboot`

---
### Packages required:
* cython - needed by kivy
* freeglut3-dev - needed by kivy

---
### Modules required:
* argparse - for command line arguments
* configparser - .ini file parsing module
* kivy - there's a specific RPi version
* pyowm - open weather map support (you will need your own API Key)
* requests - for making url requests
* rpi_backlight - for managing brightness on the RPi's touchscreen
* untangle - xml parser for pulling apart BoM readings

&nbsp;&nbsp;&nbsp;&nbsp;`source ~/project/rpiclock/.venv/bin/activate`  
&nbsp;&nbsp;&nbsp;&nbsp;`pip3 install argparse`  
&nbsp;&nbsp;&nbsp;&nbsp;`pip3 install configparser`  
&nbsp;&nbsp;&nbsp;&nbsp;`pip3 install kivy`  
&nbsp;&nbsp;&nbsp;&nbsp;`pip3 install pyowm`  
&nbsp;&nbsp;&nbsp;&nbsp;`pip3 install requests`  
&nbsp;&nbsp;&nbsp;&nbsp;`pip3 install rpi_backlight`  
&nbsp;&nbsp;&nbsp;&nbsp;`pip3 install untangle`  

---
### Usage:
The rpi_backlight module requires the program to be run as sudo/root.

-v option can be supplied to enable the (rather limited) console logging.

Most useful parameters can be set via the config.ini file.

---
