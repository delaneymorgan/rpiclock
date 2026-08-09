import os
import signal
import sys

from constants import resource_path


def signal_handler(raised_signal, frame):
    """Handle SIGINT or other quit signals."""
    _ = frame
    if raised_signal == signal.SIGINT:
        import state
        state.running_flag = False
        sys.exit(0)
    return


def is_rpi():
    """Return True only for actual Raspberry Pi hardware."""
    model_paths = ["/proc/device-tree/model", "/sys/firmware/devicetree/base/model"]
    for path in model_paths:
        if os.path.exists(path):
            try:
                with open(path, "rb") as f:
                    model = f.read().decode("utf-8", errors="ignore").lower()
                return "raspberry pi" in model or "raspberry" in model
            except OSError:
                pass
    if os.path.exists("/proc/cpuinfo"):
        try:
            with open("/proc/cpuinfo", "r", encoding="utf-8", errors="ignore") as f:
                cpuinfo = f.read().lower()
            return "raspberry pi" in cpuinfo or "bcm" in cpuinfo
        except OSError:
            pass
    return False


def log(args, text):
    if getattr(args, "verbose", False):
        print(text)
    return


def suffix_num(num):
    def func(n):
        return repr(n) + 'tsnrhtdd'[n % 5 * (n % 100 ^ 15 > 4 > n % 10)::4]

    return func(num)
