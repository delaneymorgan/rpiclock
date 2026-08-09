#!/usr/bin/env python
# coding=utf-8

import argparse
import signal
import sys

import state

from app import ConsoleClock, RPiClockApp
from config import Config
from constants import __version__
from monitors import BOMWeatherMonitor, OWMWeatherMonitor
from utils import is_rpi, log, signal_handler


def arg_parser():
    """Parse arguments."""
    parser = argparse.ArgumentParser(description='rpiclock - time/date/weather display appliance.')
    parser.add_argument("-v", "--verbose", help="verbose mode", action="store_true")
    parser.add_argument("-d", "--diagnostic", help="diagnostic mode (includes verbose)", action="store_true")
    parser.add_argument("--console", help="run in console mode for desktop testing", action="store_true")
    parser.add_argument("--version", action="version", version='%(prog)s {version}'.format(version=__version__))
    return parser.parse_args()


def main():
    args = arg_parser()
    log(args, "rpiclock start")
    signal.signal(signal.SIGINT, signal_handler)
    state.running_flag = True
    config = Config()
    weather_monitor = None
    if config.get()["weather"]["api"] == "owm":
        weather_monitor = OWMWeatherMonitor(args, config)
    elif config.get()["weather"]["api"] == "bom":
        weather_monitor = BOMWeatherMonitor(args, config)

    if args.console:
        console_clock = ConsoleClock(args, config, weather_monitor)
        console_clock.run()
    else:
        clock_app = RPiClockApp(args, config)
        if is_rpi():
            from kivy_compat import Window
            Window.fullscreen = True
        clock_app.run()
    log(args, "rpiclock end")


if __name__ == "__main__":
    main()
