# rpiclock
This repository contains the rpiclock application designed to run on a Raspberry Pi 2/3 with the 7" touchscreen under Python 2.7.

It should run on a standard Linux desktop.

---
### Obtain repository:
If you're reading this, chances are you already have some access to it.

&nbsp;&nbsp;&nbsp;&nbsp;`cd ~/<project-dir>/`  
&nbsp;&nbsp;&nbsp;&nbsp;`git clone --recursive https://<github-user>@github.com/delaneymorgan/rpiclock.git`

---
### 7" Touchscreen Setup:
Follow link for the definitive RPi 7" Touchscreen instructions.

&nbsp;&nbsp;&nbsp;&nbsp;`https://www.element14.com/community/docs/DOC-78156/l/raspberry-pi-7-touchscreen-display`

If you've mounted the display in one of its many cases, you might find the display upside-down with respect to the case.  Fret not.  You'll need to modify /boot/config.txt.

&nbsp;&nbsp;&nbsp;&nbsp;`sudo vim /boot/config.txt`  

Add the following line:

&nbsp;&nbsp;&nbsp;&nbsp;`lcd_rotate=2`  

Save and reboot.

Next you need to configure kivy to recognise touch events:

In ~/.kivy, edit config.ini and look for the input section.  Change it to:

&nbsp;&nbsp;&nbsp;&nbsp;`mouse = mouse`  
&nbsp;&nbsp;&nbsp;&nbsp;`mtdev_%(name)s = probesysfs,provider=mtdev`  
&nbsp;&nbsp;&nbsp;&nbsp;`hid_%(name)s = probesysfs,provider=hidinput`  

See:

&nbsp;&nbsp;&nbsp;&nbsp;`https://kivy.org/docs/installation/installation-rpi.html`

However, this only works for the current user.  If you run rpiclock as root, which you will if you auto-start or use the brightness control, you'll need to copy the working config to the root user's directory:

&nbsp;&nbsp;&nbsp;&nbsp;`cp -r ~/.kivy /root`  


---
### 7 Segment Font:
You can get an old-school 7-segment font for the time display from here:

&nbsp;&nbsp;&nbsp;&nbsp;`https://www.keshikan.net/fonts-e.html`

Install any font by copying it to the RPi's font directory.

&nbsp;&nbsp;&nbsp;&nbsp;`sudo cp <fontname> /usr/share/fonts`

Note that the blinking colon effect works best with a fixed-width font.  The 7-segment font works nicely.

NOTE: Under Ubuntu 14, kivy doesn't find the custom font in the usual locations where the system installs them.  Try placing the font in the same folder as the rpiclock app.

---
### Auto-Start:
A systemd service is provided for use with Raspbian.  Assuming you have installed rpiclock under /home/pi/project/rpiclock, this should run as is.  Modify as required.

&nbsp;&nbsp;&nbsp;&nbsp;`cd /lib/systemd/system/`  
&nbsp;&nbsp;&nbsp;&nbsp;`sudo ln -s ~/project/rpiclock/rpiclock.service rpiclock.service`  

---
### Packages required:
* cython - needed by kivy
* freeglut3-dev - needed by kivy

---
### Modules required:
* configparser - .ini file parsing module
* kivy - there's a specific RPi version
* rpi_backlight - for managing brightness on the RPi's touchscreen
* pyowm - open weather map support (you will need your own API Key)
* untangle - xml parser for pulling apart BoM readings
* pygame - ??????

&nbsp;&nbsp;&nbsp;&nbsp;`sudo pip install configparser`  
&nbsp;&nbsp;&nbsp;&nbsp;`sudo pip install kivy`  
&nbsp;&nbsp;&nbsp;&nbsp;`sudo pip install rpi_backlight`  
&nbsp;&nbsp;&nbsp;&nbsp;`sudo pip install pyowm`  
&nbsp;&nbsp;&nbsp;&nbsp;`sudo pip install untangle`  

---
### Usage:
The rpi_backlight module requires the program to be run as sudo/root.

-v option can be supplied to enable the (rather limited) console logging.

Most useful parameters can be set via the config.ini file.

---
