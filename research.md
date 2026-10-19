# DIY 机械轴 MIDI 琴 调研报告（2026-10）

调研结论：**方案可行，链路成熟，25 键版实价调研后 ¥85~250**。最大变数是长条 PCB 超嘉立创免费尺寸（拆小板规避），最大决策点是力度感应做到哪一步。

## 已确定的产品决策（2026-10-13 更新）

- **25 键，单排半音阶布局**（回归最初设想；宽约 48cm，PCB 需分段小板或付费整板）
- **固件：裸 CircuitPython + `adafruit_midi`**，不用 QMK——免工具链，code.py 直接编辑；单排直连无矩阵，二极管也可省
- **力度：第一版固定力度 + 旋钮**；PCB 预留第二触点焊盘，日后可加轻触开关升级为双触点测速
- **焊接：能免则免（鳄鱼夹原型 + 嘉立创 SMT 贴片），不行再买烙铁**（黄花 907 ~¥30）
- **路线：先原型验证链路 → 画正式 PCB**

## 1. 固件选型：QMK

| 方案 | 结论 |
|---|---|
| 裸 CircuitPython + `adafruit_midi` | ✅ 选用。免工具链，刷 UF2 后改 code.py 即可，单排直连 30 行代码搞定，绕开 KMK 停更风险 |
| QMK | 备选。原生支持 RP2040（`MIDI_ENABLE = yes` + `MIDI_ADVANCED` 有八度移位/力度档/延音踏板键码），功能强但需装 QMK 工具链，本项目规模用不上；日后要加功能可切换。文档：https://docs.qmk.fm/features/midi |

注意：不要选 ESP32/合宙主控——QMK 不支持 ESP32 的 USB。

## 2. 可参考的开源项目

| 项目 | 键数/布局 | 主控 | 可抄什么 |
|---|---|---|---|
| [mechmidi1](https://github.com/konsumer/mechmidi1) | 20 键网格 | RP2040-Zero + CircuitPython | EasyEDA 工程开源，同主控同规模 |
| [MIDIKeyboard-SoundEngine](https://github.com/Mikedan37/MIDIKeyboard-SoundEngine) | 25 键单排 | Pico + TinyUSB | 25 键 RP2040 先例；实现了双触点力度（但注明未打板） |
| [midi314-pcb](https://github.com/tiliosys/midi314-pcb) | 42 键 Jankó | Pro Micro | KiCad 矩阵电路完整开源，画 PCB 参考 |
| [MIDI88](https://www.printables.com/model/1168638-midi88-88-key-mx-based-midi-keyboard) | 88 键标准钢琴布局 | QMK | 黑白键错位布局参考（3D 打印，PCB/主控未确认） |
| [OMX-27](https://github.com/okyeron/OMX-27) | 27 键黑白两排 | RP2040 | 布局参考（PCB 不开源，313×65mm） |
| [Melodicade MX](https://www.koopinstruments.com/instrument-projects/melodicade-mx) | 6+ 八度 | Teensy 4.1 | **力度方案**：轴底剪掉让轴芯触底戳轻触开关，双触点时差测速，代码 GPL3 |

布局结论：**没有"钢琴黑白两排 + MX 轴 + PCB 开源"的现成设计**，电路抄 midi314/mechmidi1，布局抄 MIDI88，自己拼。

## 3. 力度感应方案对比

| 方案 | 25 键增加成本 | 复杂度 | 结论 |
|---|---|---|---|
| 固定力度 + 旋钮 | ≈¥5 | ≈0 | **第一版采用** |
| 双触点测速（Melodicade MX 式：轴下叠轻触开关，测两触点时差；重击 ~1500µs、轻触 >30000µs） | ≈¥30~50 | 中（装配精度） | 唯一被完整验证的 DIY 真力度方案，**预留焊盘，二期升级** |
| 霍尔磁轴全模拟（每键线性霍尔 + HC4067 多路复用 + 校准） | ≈¥150~200 | 高 | 最优雅（可带复音触后），留作进阶 |
| FSR/压电 | ¥150+ | 高且效果差 | 排除：测静态压力而非击键速度 |

开源验证先例：Melodicade MX（完整构建指南 + GPL3 代码）；霍尔路线见 [PJRC 论坛项目](https://forum.pjrc.com/index.php?threads/velocity-sensitive-contactless-midi-keyboard-with-polyphonic-aftertouch-for-teensy-synth.75078/) 和 Midihex。

## 4. BOM 实价（2026-10 调研）

| 物料 | 型号/规格 | 实价 | 来源 |
|---|---|---|---|
| 主控 | RP2040-Zero 兼容板 | ¥7.5~9.9 | 淘宝 |
| 主控（原型备选） | Pico 全尺寸兼容板 | ¥9.3~19.8 | 淘宝（排针好焊） |
| 轴 | 高特红轴 | ~¥1/颗（10 颗 ¥10） | 淘宝/京东 |
| 轴（升级） | 佳达隆 G 红 Pro | ¥1.2/颗 | 淘宝 |
| 键帽 | XDA 1u 无刻散装，黑/白多色自选 | ¥1~2/颗（估计）；1688 白色 108 键全套 ¥69 实价 | 淘宝/1688 |
| 热插拔轴座 | 凯华 MX 轴座 | ¥0.28/个（1688 百起批）；零售 ~¥0.5~1 | 1688/淘宝 |
| 二极管 | 1N4148（直插/贴片同价） | ~¥0.025/只；淘宝 100 只 ¥3.4 | 立创商城/淘宝 |
| USB-C 母座 | 16P 贴片 | ¥0.30 | 立创商城 |
| 外壳 | 亚克力（立创面板）/ 3D 打印 | ¥20~60 | 立创面板/嘉立创 3D |

**两档总价：**

| | 25 键 | 37 键 |
|---|---|---|
| 裸板 + 分段小板（免费券） | **¥85~120** | ¥110~160 |
| 整板 + 外壳 | ¥140~250 | ¥180~300 |

## 5. PCB 与嘉立创规则

- 免费打样（2025-26 现行）：**每月 2 张券，双层 FR-4，10×10cm 以内，5 片**
- 25 键单排整板约 480×60mm，超免费尺寸；付费 5 片估计 ¥30~80；嘉立创 V 割最大 475mm
- **37 键单排约 70cm 超 V 割上限**——所以选 25 键也规避了这个问题
- 策略：正式版按"白键排 + 黑键排"两块小板设计，都吃免费券，排针/导线互联；也降低长板翘曲风险

## 6. Linux 链路（已确认免驱）

USB MIDI 是 class 标准设备，内核 `snd-usb-audio` 即插即用。已知坑都在软件配置：

1. QSynth/FluidSynth **必须加载 SoundFont**（如 FluidR3_GM.sf2），否则无声——最常见坑
2. MIDI 连接要手动：`aconnect <键盘> <fluidsynth>`；PipeWire 系统用 `pw-link`
3. QSynth 音频后端别选 JACK（没跑 JACK 会无声），选 ALSA/PulseAudio
4. 调试利器：`aseqdump` 直接看 Note On/Off 原始消息，先排除硬件/固件问题

## 7. 原型阶段计划（12 键洞洞板，约 ¥50）

购物：RP2040-Zero（选已焊排针版）¥9~15、高特红轴 ×15 ¥15、830 孔面包板 ¥5~10、杜邦线一扎（母头可直接套 MX 轴脚）¥5、10K 电位器 ×2 ¥3、键帽可先不买（裸轴芯能按）。单排直连无矩阵，二极管可不买。烙铁非必需，要买就黄花 907（~¥30）。

接线：开发板插面包板，面包板电源轨作 GND 总线；12 键直连 12 个 GPIO（一脚杜邦线 → GND 轨，一脚杜邦线母头套轴脚 → GPIO），免焊免鳄鱼夹；电位器接 GPIO26(ADC)。零成本预验证：杜邦线短接 GPIO 与 GND 即模拟按键。面包板接触不如焊接，消抖（≥5ms）别省。

固件：CircuitPython UF2（circuitpython.org，RP2040-Zero 选 Waveshare 版）+ 拷入 `adafruit_midi` 库 + `code.py`（直连 GPIO 扫描发 NoteOn/NoteOff，~30 行）；力度先固定 100，旋钮版读 GPIO26 ADC 映射 1~127。

验收：`aconnect -l` 认出 → `aseqdump` 有消息 → QSynth 加载 SoundFont 后 `aconnect` 连上发声 → MuseScore 能录入。

原型要回答：红轴当琴键手感能否接受、延迟感知、Linux 链路是否顺畅。全绿后画正式 PCB（25 键双小板、热插拔轴座、预留双触点焊盘）。

## 未确认事项（用到时再查）

- QMK MIDI 在 RP2040 上无官方"已验证"声明（也无反面 issue）——原型验证即覆盖
- MIDI88 的主控/PCB/许可证未确认（Printables 页面抓取失败）
- 长条 PCB 在线报价、散装 XDA 单颗价，下单前各确认一次
