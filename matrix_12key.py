"""12 键 3x4 矩阵 MIDI 原型（二极管 COL2ROW 方向）。

接线：
  行 GP1 GP2 GP3        输出，轮流拉低，空闲时高阻
  列 GP4 GP5 GP6 GP7    输入 + 内部上拉
  每个键：行 ──|>|── 轴体 ── 列   或   行 ── 轴体 ──|>|── 列
  （串联顺序无所谓，方向必须统一：二极管色环端/阴极朝行线）

键位 K0..K11 → MIDI 音符 60..71（C4..B4），固定力度 80。
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

ROW_PINS = (board.GP1, board.GP2, board.GP3)
COL_PINS = (board.GP4, board.GP5, board.GP6, board.GP7)
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


print("matrix 12key ready, notes", BASE_NOTE, "-", BASE_NOTE + NUM_KEYS - 1)

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
