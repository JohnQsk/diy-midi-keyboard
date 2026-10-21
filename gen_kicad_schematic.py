"""生成 KiCad 原理图 midi_matrix.kicad_sch（12 键 3x4 矩阵，COL2ROW）。

从系统符号库提取 Device:D / Switch:SW_Push / Connector_Generic:Conn_01x07
并内嵌进图纸，无需配置库表即可打开。运行：
    python3 gen_kicad_schematic.py
渲染验证：
    kicad-cli sch export pdf -o midi_matrix.pdf midi_matrix.kicad_sch
"""
import re
import uuid

PROJ = "midi_matrix"

SYM_SOURCES = [
    ("/usr/share/kicad/symbols/Device.kicad_sym", "D", "Device"),
    ("/usr/share/kicad/symbols/Switch.kicad_sym", "SW_Push", "Switch"),
    ("/usr/share/kicad/symbols/Connector_Generic.kicad_sym", "Conn_01x07", "Connector_Generic"),
]


def extract_symbol(path, name):
    txt = open(path).read()
    i = txt.find(f'(symbol "{name}"')
    assert i >= 0, f"{name} not in {path}"
    depth = 0
    for j in range(i, len(txt)):
        if txt[j] == "(":
            depth += 1
        elif txt[j] == ")":
            depth -= 1
            if depth == 0:
                return txt[i:j + 1]
    raise ValueError(name)


def lib_symbol(lib_name, sym_name, path):
    body = extract_symbol(path, sym_name)
    # 内嵌符号名必须是 "库名:符号名"
    return body.replace(f'(symbol "{sym_name}"', f'(symbol "{lib_name}:{sym_name}"', 1)


def u():
    return str(uuid.uuid4())


def fmt(v):
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return s if s else "0"


def wire(x1, y1, x2, y2):
    return (f'  (wire (pts (xy {fmt(x1)} {fmt(y1)}) (xy {fmt(x2)} {fmt(y2)})) '
            f'(stroke (width 0) (type default)) (uuid "{u()}"))')


def label(name, x, y, justify):
    return (f'  (label "{name}" (at {fmt(x)} {fmt(y)} 0) (fields_autoplaced) '
            f'(effects (font (size 1.27 1.27)) (justify {justify} bottom)) '
            f'(uuid "{u()}"))')


def text(content, x, y, size=1.8, bold=False):
    b = " (bold yes)" if bold else ""
    return (f'  (text "{content}" (at {fmt(x)} {fmt(y)} 0) '
            f'(effects (font (size {size} {size}){b}) (justify left bottom)) (uuid "{u()}"))')


def symbol(lib_id, ref, value, x, y, ref_off, val_off, pins):
    props = []
    for pname, pval, (ox, oy), hide in [
        ("Reference", ref, ref_off, False),
        ("Value", value, val_off, False),
        ("Footprint", "", (0, 0), True),
        ("Datasheet", "~", (0, 0), True),
    ]:
        h = " hide" if hide else ""
        props.append(f'    (property "{pname}" "{pval}" (at {fmt(x + ox)} {fmt(y + oy)} 0) '
                     f'(effects (font (size 1.27 1.27)){h}))')
    pin_uuids = "".join(f'    (pin "{p}" (uuid "{u()}"))\n' for p in pins)
    return (f'  (symbol (lib_id "{lib_id}") (at {fmt(x)} {fmt(y)} 0) (unit 1)\n'
            f'    (in_bom yes) (on_board yes) (dnp no) (fields_autoplaced)\n'
            f'    (uuid "{u()}")\n' + "\n".join(props) + "\n" + pin_uuids +
            f'    (instances (project "{PROJ}" (path "/" (reference "{ref}") (unit 1))))\n'
            f'  )')


parts = []

# ---------- 12 个按键单元：ROWi ── SW ── D(1N4148) ── COLj ----------
# SW_Push 引脚: 1=(-5.08,0) 2=(5.08,0)；D 引脚: 1(K)=(-3.81,0) 2(A)=(3.81,0)
# 二极管阴极(K，色环端)朝左 = 朝行线（COL2ROW）
NOTES = ["C4", "C#4", "D4", "D#4", "E4", "F4", "F#4", "G4", "G#4", "A4", "A#4", "B4"]
for ri in range(3):
    for ci in range(4):
        k = ri * 4 + ci
        ox, oy = 70 + ci * 60, 60 + ri * 30
        parts.append(symbol("Switch:SW_Push", f"SW{k + 1}", f"K{k} ({NOTES[k]})",
                            ox, oy, (-2, -5.5), (2, 5.5), ["1", "2"]))
        dx = ox + 5.08 + 5.08 + 3.81  # 二极管中心
        parts.append(symbol("Device:D", f"D{k + 1}", "1N4148",
                            dx, oy, (0, -4.5), (0, 4.5), ["1", "2"]))
        parts.append(wire(ox + 5.08, oy, dx - 3.81, oy))          # SW -> D.K
        parts.append(wire(ox - 5.08, oy, ox - 10.16, oy))         # ROW stub
        parts.append(label(f"ROW{ri + 1}", ox - 10.16, oy, "right"))
        parts.append(wire(dx + 3.81, oy, dx + 8.89, oy))          # COL stub
        parts.append(label(f"COL{ci + 1}", dx + 8.89, oy, "left"))

# ---------- GPIO 连接器（代表 RP2040 / RP2040-Zero） ----------
# Conn_01x07 引脚: x=-5.08；注意符号库 y 轴向上、图纸 y 轴向下，pin1 在 y=-7.62（顶部）
cx, cy = 245, 140
parts.append(symbol("Connector_Generic:Conn_01x07", "J1", "RP2040 GPIO",
                    cx, cy, (2, -11), (2, 11), [str(i) for i in range(1, 8)]))
pin_nets = ["ROW1", "ROW2", "ROW3", "COL1", "COL2", "COL3", "COL4"]
for i, net in enumerate(pin_nets):
    py = cy - 7.62 + i * 2.54
    px = cx - 5.08
    stub = 10.16 if i % 2 == 0 else 15.24
    parts.append(wire(px - stub, py, px, py))
    parts.append(label(net, px - stub, py, "right"))
parts.append(text("J1 pin1..7 = GP1..GP7", cx - 18, cy + 17, size=1.5))

# ---------- 注释 ----------
parts.append(text("ROW1~3 = GP1~3 (output, drive LOW in turn, Hi-Z when idle)", 15, 150))
parts.append(text("COL1~4 = GP4~7 (input with internal pull-up, no external parts)", 15, 155))
parts.append(text("Each key: ROW -- SW -- 1N4148 -- COL; diode cathode (band) faces ROW (COL2ROW)", 15, 160))
parts.append(text("K0..K11 -> MIDI note 60..71; firmware: matrix_12key.py", 15, 165))

lib_syms = "\n".join(lib_symbol(lib, name, path) for path, name, lib in SYM_SOURCES)
lib_syms = "\n".join("    " + line for line in lib_syms.splitlines())

sch = f'''(kicad_sch (version 20230121) (generator "eeschema")
  (uuid "{u()}")
  (paper "A4")
  (title_block
    (title "12-key 3x4 Matrix MIDI Keyboard (COL2ROW)")
    (date "2026-10-19")
    (rev "1.0")
    (comment 1 "Diode per key, cathode to ROW. Firmware: matrix_12key.py")
  )
  (lib_symbols
{lib_syms}
  )
{chr(10).join(parts)}
  (sheet_instances
    (path "/" (page "1"))
  )
)
'''

open(f"{PROJ}.kicad_sch", "w").write(sch)

pro = {
    "meta": {"filename": f"{PROJ}.kicad_pro", "version": 1},
    "schematic": {"drawing": {"default_text_size": 1.27}},
}
import json
open(f"{PROJ}.kicad_pro", "w").write(json.dumps(pro, indent=2))
print(f"saved {PROJ}.kicad_sch / {PROJ}.kicad_pro")
