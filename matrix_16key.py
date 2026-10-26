"""16 键 4x4 矩阵 MIDI 固件（midi_matrix_4x4 PCB 专用，二极管 COL2ROW 方向）。

接线（PCB 左侧 J1 竖排针，8 根杜邦线直连 RP2040-Zero，一一对应）：
  J1 pin1..4 = ROW1..4 → GP1 GP2 GP3 GP4   输出，轮流拉低，空闲时高阻
  J1 pin5..8 = COL1..4 → GP5 GP6 GP7 GP8   输入 + 内部上拉
  矩阵不需要共地，无需接 GND；RP2040-Zero 由 USB 供电即可。

键位 K0..K15（从左到右）→ MIDI 音符 60..75（C4..D#5），固定力度 80。
键 i = ROW(i//4) + COL(i%4)，即 K0-3 在 ROW1、K4-7 在 ROW2，COL1..4 循环。
串口打印 note on / note off，兼容 keydash.py。
复制到 CIRCUITPY 盘并改名 code.py 即可运行。
"""
import board
import digitalio
import time
import usb_midi
import adafruit_midi
from adafruit_midi.note_on import NoteOn
from adafruit_midi.note_off import NoteOff

ROW_PINS = (board.GP1, board.GP2, board.GP3, board.GP4)
COL_PINS = (board.GP5, board.GP6, board.GP7, board.GP8)
BASE_NOTE = 60
VELOCITY = 80
DEBOUNCE_S = 0.005

midi = adafruit_midi.MIDI(midi_out=usb_midi.ports[1], out_channel=0)

rows = []
for pin in ROW_PINS:
    r = digitalio.DigitalInOut(pin)
    r.direction = digitalio.Direction.INPUT  # 空闲高阻，避免行间互顶
    rows.append(r)

cols = []
for pin in COL_PINS:
    c = digitalio.DigitalInOut(pin)
    c.direction = digitalio.Direction.INPUT
    c.pull = digitalio.Pull.UP
    cols.append(c)

NUM_KEYS = len(ROW_PINS) * len(COL_PINS)
state = [False] * NUM_KEYS
raw_prev = [False] * NUM_KEYS
last_change = [0.0] * NUM_KEYS


def scan_matrix():
    """返回 NUM_KEYS 个布尔值，True = 按下。"""
    result = [False] * NUM_KEYS
    for ri, row in enumerate(rows):
        row.direction = digitalio.Direction.OUTPUT
        row.value = False
        for ci, col in enumerate(cols):
            if not col.value:
                result[ri * len(COL_PINS) + ci] = True
        row.direction = digitalio.Direction.INPUT
    return result


print("matrix 16key ready, notes", BASE_NOTE, "-", BASE_NOTE + NUM_KEYS - 1)

while True:
    raw = scan_matrix()
    now = time.monotonic()
    for i in range(NUM_KEYS):
        if raw[i] != raw_prev[i]:
            raw_prev[i] = raw[i]
            last_change[i] = now
        elif raw[i] != state[i] and now - last_change[i] > DEBOUNCE_S:
            state[i] = raw[i]
            note = BASE_NOTE + i
            if state[i]:
                midi.send(NoteOn(note, VELOCITY))
                print("note on", note)
            else:
                midi.send(NoteOff(note, 0))
                print("note off", note)
    time.sleep(0.001)
