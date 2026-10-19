#!/usr/bin/env python3
"""Live key-press dashboard for the RP2040-Zero MIDI prototype.

Reads the CircuitPython serial console (/dev/ttyACM0) and renders a
realtime view of key state, hold time, press count and recent history.

Usage: python3 keydash.py [serial_port]
"""
import re
import sys
import time

import serial

PORT = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyACM0"

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]|\x1b\][^\x1b]*\x1b\\|\x1b\\")
GREEN = "\033[42m\033[30m"
GRAY = "\033[100m\033[37m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"
HOME = "\033[H"
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"


def render(pressed, hold, count, last_dur, history, uptime):
    status = f"{GREEN}{BOLD}  ● PRESSED   {RESET}" if pressed else \
             f"{GRAY}  ○ released  {RESET}"
    bar = "█" * min(int(hold * 20), 50)
    lines = [
        f"{BOLD}MIDI key dashboard{RESET}   {DIM}port {PORT}   up {uptime:5.1f}s   Ctrl+C to quit{RESET}",
        "",
        f"  {status}",
        "",
        f"  hold    : {BOLD}{hold:6.2f}s{RESET} {GREEN}{bar}{RESET}" if pressed else
        f"  hold    : {0:6.2f}s",
        f"  presses : {BOLD}{count}{RESET}",
        f"  last    : {last_dur:6.2f}s",
        "",
        f"  {BOLD}recent presses{RESET} {DIM}(1 char ≈ 50ms){RESET}",
    ]
    for d in history[-12:]:
        lines.append(f"  {d:5.2f}s │{'█' * max(1, int(d * 20))}")
    if not history:
        lines.append(f"  {DIM}(none yet — press the key){RESET}")
    return "\n".join(lines) + "\n"


def main():
    ser = serial.Serial(PORT, 115200, timeout=0.05)
    t0 = time.monotonic()
    pressed = False
    press_start = 0.0
    count = 0
    last_dur = 0.0
    history = []
    buf = b""

    print("\033[2J" + HIDE_CURSOR, end="", flush=True)
    try:
        while True:
            buf += ser.read(256)
            while b"\n" in buf:
                raw, buf = buf.split(b"\n", 1)
                line = ANSI_RE.sub("", raw.decode("utf-8", "replace"))
                now = time.monotonic()
                if "note on" in line and not pressed:
                    pressed = True
                    press_start = now
                elif "note off" in line and pressed:
                    pressed = False
                    count += 1
                    last_dur = now - press_start
                    history.append(last_dur)
            hold = time.monotonic() - press_start if pressed else 0.0
            print(HOME + render(pressed, hold, count, last_dur, history,
                                time.monotonic() - t0), end="", flush=True)
            time.sleep(0.03)
    except KeyboardInterrupt:
        pass
    finally:
        print(SHOW_CURSOR)
        ser.close()


if __name__ == "__main__":
    try:
        main()
    except serial.SerialException as e:
        sys.exit(f"cannot open {PORT}: {e}")
    except BrokenPipeError:
        pass
