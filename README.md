# rpiclock
This repository contains the rpiclock application designed to run on a Raspberry Pi 2/3 with the 7" touchscreen.

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

---
### Modules required:
* configparser - .ini file parsing module
* kivy - there's a specific RPi version
* rpi_backlight - for managing brightness on the RPi's touchscreen
* pyowm - open weather map support (you will need your own API Key)
* untangle - xml parser for pulling apart BoM readings
---
### Usage:
The rpi_backlight module requires the program to be run as sudo/root.

Most useful parameters can be set via the config.ini file.

An upstart script is provided, although Raspbian doesn't use upstart.

---
