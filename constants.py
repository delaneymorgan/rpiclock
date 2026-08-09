import os
import sys


def resource_path(path):
    if os.path.isabs(path):
        return path
    if os.path.exists(path):
        return path
    meipass = getattr(sys, '_MEIPASS', None)
    if meipass:
        candidate = os.path.join(meipass, path)
        if os.path.exists(candidate):
            return candidate
    bundle_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    candidate = os.path.join(bundle_dir, path)
    if os.path.exists(candidate):
        return candidate
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidate = os.path.join(script_dir, path)
    if os.path.exists(candidate):
        return candidate
    return path


__version__ = "20240915-1"
SECONDS_IN_DAY = 24 * 60 * 60
DEGREE_SIGN = u"\u00b0"
CONFIG_FILENAME = resource_path("config.ini")
OWM_ICONS_DIR = resource_path("owm_icons")
BOM_ICONS_DIR = resource_path("bom_icons")

MEMBERS_FORMATS = dict(
    blink_colon="bool",
    blink_rate="integer",
    date='string',
    date_dom_suffix='bool',
    display='string',
    forecast_time="integer",
    large_font="string",
    large_font_size="integer",
    small_font="string",
    small_font_size="integer",
    text_color='list',
    time='string',
    weather='string',
    window_size='list'
)
MEMBERS_BRIGHTNESS = dict(
    high='float',
    high_tom_start='string',
    low='float',
    low_tom_start='string'
)
MEMBERS_WEATHER = dict(api='string', check_interval='integer')
MEMBERS_BOM_WEATHER = dict(
    forecast_path='string',
    forecast_place='string',
    ftp_host='string',
    ftp_port='integer',
    observation_url='string',
    observation_place='string'
)
MEMBERS_OWM_WEATHER = dict(
    api_key='string',
    place='string',
    temperature_scale='string'
)
BLANK_IMAGE = "blank.png"
