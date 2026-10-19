"""12 键 74HC165 MIDI 原型（无矩阵、无二极管，可扩 64 键）。

接线（2 片 74HC165 菊花链，16 输入用 12 个）：
  GP9  → PL̅ (pin 1, SH/LD̅)   两片并接
  GP10 → CP (pin 2, 时钟)     两片并接
  GP11 ← Q7 (pin 9)           第 1 片
  第1片 DS (pin 10) ← 第2片 Q7 (pin 9)
  第1片 D0..D7 = K0..K7，第2片 D0..D3 = K8..K11（D4..D7 留空）
  每个输入脚：3V3 ──[10k 上拉]──┬── 输入脚；轴体从输入脚到 GND
  CE̅ (pin 15) 接 GND；每片 VCC-GND 加 100nF 退耦
  按下 = 低电平，软件里取反

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

NUM_CHIPS = 2
NUM_KEYS = 12
BASE_NOTE = 60
VELOCITY = 80
DEBOUNCE_S = 0.005

# 串行读出顺序：第1片 D7..D0，然后第2片 D7..D0 → 对应的键号
READ_TO_KEY = (7, 6, 5, 4, 3, 2, 1, 0, 15, 14, 13, 12, 11, 10, 9, 8)

midi = adafruit_midi.MIDI(midi_out=usb_midi.ports[1], out_channel=0)

load = digitalio.DigitalInOut(board.GP9)
load.direction = digitalio.Direction.OUTPUT
load.value = True

clk = digitalio.DigitalInOut(board.GP10)
clk.direction = digitalio.Direction.OUTPUT
clk.value = False

data = digitalio.DigitalInOut(board.GP11)
data.direction = digitalio.Direction.INPUT

state = [False] * NUM_KEYS
raw_prev = [False] * NUM_KEYS
last_change = [0.0] * NUM_KEYS


def read_keys():
    """并行锁存所有键，再串行移出；返回 NUM_KEYS 个布尔值。"""
    load.value = False   # 锁存快照
    load.value = True
    result = [False] * NUM_KEYS
    for r in range(NUM_CHIPS * 8):
        key = READ_TO_KEY[r]
        if key < NUM_KEYS and not data.value:  # 按下 = 低电平
            result[key] = True
        clk.value = True
        clk.value = False
    return result


print("hc165 12key ready, notes", BASE_NOTE, "-", BASE_NOTE + NUM_KEYS - 1)

while True:
    raw = read_keys()
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
