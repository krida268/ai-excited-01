"""The Breach — an original procedural painting for ai-excited-01.

A colossal whale breaches out of the sea at sunset, silhouetted against a
huge low sun, spray exploding around it, while a tiny sailboat rides a wave
far below for scale. One look, one jolt: scale, light, momentum.

Drawn pixel by pixel with the Python standard library only. No network, no
files read, fully deterministic: the same bytes every run.
"""

import math
import os
import random
import struct
import zlib

W = 1024
H = 1024
HORIZON = 640

# --- palette -------------------------------------------------------------
SKY_TOP = (14, 20, 64)
SKY_MID = (59, 42, 107)
SKY_LOW = (184, 58, 94)
SKY_HOR = (255, 122, 77)
SKY_GOLD = (255, 196, 107)
SEA_TOP = (14, 58, 92)
SEA_BOT = (7, 38, 63)
WHALE = (27, 42, 82)
WHALE_TOP = (44, 62, 110)
BELLY = (126, 147, 184)
SUN_CORE = (255, 233, 168)
SUN_MID = (255, 179, 71)
SUN_EDGE = (255, 140, 66)
FOAM = (235, 246, 250)
INK = (20, 38, 77)

_rng = random.Random(20261116)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


class Canvas:
    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.px = bytearray(w * h * 3)

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i], self.px[i + 1], self.px[i + 2] = color

    def blend(self, x, y, color, alpha):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            for c in range(3):
                base = self.px[i + c]
                self.px[i + c] = int(base + (color[c] - base) * alpha)

    def disc(self, cx, cy, r, color, alpha=1.0):
        r = int(r)
        for dy in range(-r, r + 1):
            dx = int(math.sqrt(max(0, r * r - dy * dy)))
            for x in range(cx - dx, cx + dx + 1):
                if alpha >= 1.0:
                    self.set(x, cy + dy, color)
                else:
                    self.blend(x, cy + dy, color, alpha)

    def ellipse(self, cx, cy, rx, ry, color, alpha=1.0):
        for dy in range(-ry, ry + 1):
            t = 1.0 - (dy * dy) / float(ry * ry)
            dx = int(rx * math.sqrt(max(0.0, t)))
            for x in range(cx - dx, cx + dx + 1):
                if alpha >= 1.0:
                    self.set(x, cy + dy, color)
                else:
                    self.blend(x, cy + dy, color, alpha)

    def hline(self, x0, x1, y, color, alpha=1.0):
        for x in range(max(0, x0), min(self.w, x1 + 1)):
            if alpha >= 1.0:
                self.set(x, y, color)
            else:
                self.blend(x, y, color, alpha)

    def vline(self, x, y0, y1, color, alpha=1.0):
        for y in range(max(0, y0), min(self.h, y1 + 1)):
            if alpha >= 1.0:
                self.set(x, y, color)
            else:
                self.blend(x, y, color, alpha)

    def line(self, x0, y0, x1, y1, color, width=1):
        steps = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        for s in range(steps + 1):
            t = s / float(steps)
            x = int(x0 + (x1 - x0) * t)
            y = int(y0 + (y1 - y0) * t)
            self.disc(x, y, width // 2, color)

    def polygon(self, points, color):
        pts = [(int(x), int(y)) for x, y in points]
        ys = [p[1] for p in pts]
        for y in range(max(0, min(ys)), min(self.h - 1, max(ys)) + 1):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    t = (y - y0) / float(y1 - y0)
                    xs.append(x0 + t * (x1 - x0))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                self.hline(int(xs[k]), int(xs[k + 1]), y, color)


def sky(c):
    stops = [(0.0, SKY_TOP), (0.30, SKY_MID), (0.55, SKY_LOW),
             (0.78, SKY_HOR), (1.0, SKY_GOLD)]
    for y in range(HORIZON + 1):
        t = y / float(HORIZON)
        for i in range(len(stops) - 1):
            t0, c0 = stops[i]
            t1, c1 = stops[i + 1]
            if t0 <= t <= t1:
                col = lerp(c0, c1, (t - t0) / (t1 - t0))
                break
        else:
            col = SKY_GOLD
        c.hline(0, W - 1, y, col)


def stars(c):
    for _ in range(150):
        x = _rng.randrange(0, W)
        y = _rng.randrange(0, 330)
        bright = 140 + _rng.randrange(0, 115)
        fade = 1.0 - y / 380.0
        base = int(bright * fade)
        col = (min(255, base + 60), min(255, base + 60),
               min(255, base + 80))
        s = 1 if _rng.random() < 0.8 else 2
        for dx in range(s):
            for dy in range(s):
                c.set(x + dx, y + dy, col)


def sun(c):
    cx, cy = 700, 520
    for r, a in ((230, 0.10), (205, 0.14), (180, 0.18), (155, 0.24)):
        c.disc(cx, cy, r, SUN_EDGE, a)
    c.disc(cx, cy, 122, SUN_EDGE)
    c.disc(cx, cy, 100, SUN_MID)
    c.disc(cx, cy, 72, SUN_CORE)
    # soft halo ring instead of stick rays: the glow already carries it
    c.disc(cx, cy, 140, SUN_EDGE, 0.12)


def clouds(c):
    for cx, cy, rx, ry, col, a in (
            (200, 300, 190, 26, (255, 158, 125), 0.45),
            (820, 250, 230, 30, (232, 139, 176), 0.40),
            (450, 170, 150, 20, (255, 178, 122), 0.35),
            (120, 470, 160, 22, (255, 140, 110), 0.30)):
        c.ellipse(cx, cy, rx, ry, col, a)
        # a smaller puff on top so the cloud reads as a cloud, not a disc
        c.ellipse(cx - rx // 3, cy - ry // 2, rx // 2, ry, col, a)


def sea(c):
    for y in range(HORIZON, H):
        t = (y - HORIZON) / float(H - HORIZON)
        c.hline(0, W - 1, y, lerp(SEA_TOP, SEA_BOT, t))
    # sun glitter path on the water
    for y in range(HORIZON + 6, H, 6):
        depth = (y - HORIZON) / float(H - HORIZON)
        half = int(120 * (1.0 - depth) + 18)
        xc = 700 + int(34 * math.sin(y / 37.0))
        c.hline(xc - half, xc + half, y, (255, 190, 110), 0.22)
        c.hline(xc - half // 2, xc + half // 2, y + 2, (255, 220, 150), 0.18)
    # rolling wave crests, brighter near the surface
    for k in range(7):
        y0 = HORIZON + 18 + k * 52
        crest = lerp((200, 235, 245), (120, 180, 205), k / 6.0)
        for x in range(0, W, 2):
            y = y0 + int(13 * math.sin(x / 110.0 + k * 1.7))
            c.set(x, y, crest)
            c.set(x, y + 1, crest)


def whale_spine(t):
    p0 = (170.0, 780.0)
    p1 = (300.0, 520.0)
    p2 = (580.0, 300.0)
    x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0]
    y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]
    dx = 2 * (1 - t) * (p1[0] - p0[0]) + 2 * t * (p2[0] - p1[0])
    dy = 2 * (1 - t) * (p1[1] - p0[1]) + 2 * t * (p2[1] - p1[1])
    n = math.hypot(dx, dy) or 1.0
    return (x, y), (-dy / n, dx / n)


def whale_width(t):
    # wide through the mid-body, still broad and blunt at the head (t=1),
    # narrow at the tail (t=0): a whale, not a worm
    if t <= 0.7:
        s = math.sin(math.pi * (t ** 0.8))
    else:
        s = math.sin(math.pi * (0.7 ** 0.8)) * (1.0 - 0.45 * (t - 0.7) / 0.3)
    return 10.0 + 105.0 * (s ** 0.8)


def whale(c):
    left, right = [], []
    for i in range(41):
        t = i / 40.0
        (x, y), (nx, ny) = whale_spine(t)
        w = whale_width(t)
        left.append((x + nx * w, y + ny * w))
        right.append((x - nx * w, y - ny * w))
    # body, darker on top edge: draw whole body, then a top sheen
    c.polygon(left + right[::-1], WHALE)
    head, _ = whale_spine(1.0)
    c.disc(int(head[0]), int(head[1]), 52, WHALE)
    # pale belly band along the lower (sea-facing) edge, as one smooth
    # strip: pre-blended BELLY over WHALE so it stays soft
    belly_col = (96, 115, 153)
    inner, outer = [], []
    for i in range(41):
        t = i / 40.0
        (x, y), (nx, ny) = whale_spine(t)
        w = whale_width(t)
        inner.append((x + nx * w * 0.15, y + ny * w * 0.15))
        outer.append((x + nx * w * 0.85, y + ny * w * 0.85))
    c.polygon(inner + outer[::-1], belly_col)
    # subtle sheen along the upper edge
    sheen_col = (37, 54, 99)
    inner2, outer2 = [], []
    for i in range(41):
        t = i / 40.0
        (x, y), (nx, ny) = whale_spine(t)
        w = whale_width(t)
        inner2.append((x - nx * w * 0.15, y - ny * w * 0.15))
        outer2.append((x - nx * w * 0.75, y - ny * w * 0.75))
    c.polygon(inner2 + outer2[::-1], sheen_col)
    # tail flukes, swept back from the tail base, a touch lighter so they
    # read against the dark sea
    c.polygon([(175, 775), (70, 690), (140, 800)], WHALE_TOP)
    c.polygon([(175, 775), (292, 705), (215, 802)], WHALE_TOP)
    # pectoral fin
    c.polygon([(320, 610), (402, 692), (278, 652)], WHALE)
    # eye
    c.disc(540, 308, 8, (240, 244, 250))
    c.disc(542, 309, 4, (10, 14, 30))
    # mouth line, kept inside the head
    c.line(528, 338, 560, 330, (10, 16, 36), width=3)


def spray(c):
    # bursting crown where the tail leaves the water
    for k in range(46):
        ang = math.pi * (0.05 + 0.9 * _rng.random())
        r = 30 + _rng.random() * 150
        x = int(180 + r * math.cos(ang) * 1.15)
        y = int(790 - r * math.sin(ang) * 0.75)
        s = 2 + int(_rng.random() * 5)
        c.disc(x, y, s, FOAM, 0.85)
    # droplets trailing the body
    for k in range(90):
        t = _rng.random()
        (x, y), (nx, ny) = whale_spine(t)
        w = whale_width(t)
        side = 1 if _rng.random() < 0.5 else -1
        d = w + _rng.random() * 55
        px = int(x + nx * d * side)
        py = int(y + ny * d * side - _rng.random() * 30)
        c.disc(px, py, 1 + int(_rng.random() * 3), FOAM, 0.8)
    # foam ring on the water at the breach
    for k in range(60):
        ang = _rng.random() * 2 * math.pi
        r = 55 + _rng.random() * 85
        x = int(185 + r * math.cos(ang))
        y = int(800 + r * math.sin(ang) * 0.28)
        c.disc(x, y, 2 + int(_rng.random() * 4), FOAM, 0.75)


def gulls(c):
    # small distant gulls wheeling in the sunset sky
    for cx, cy, s in ((250, 210, 16), (310, 180, 12), (880, 330, 14),
                      (930, 300, 10), (160, 250, 11)):
        c.line(cx - s, cy, cx, cy - s // 2, (30, 34, 60), width=3)
        c.line(cx, cy - s // 2, cx + s, cy, (30, 34, 60), width=3)


def sailboat(c):
    # the tiny boat, for scale against the whale
    c.polygon([(800, 716), (866, 716), (850, 733), (816, 733)], (24, 28, 52))
    c.line(832, 716, 832, 656, (240, 244, 250), width=3)
    c.polygon([(835, 660), (835, 712), (876, 712)], (250, 250, 248))
    c.polygon([(829, 664), (829, 712), (806, 712)], (255, 196, 110))


# tiny 5x7 block font, drawn by hand so the bubble text stays crisp
FONT = {
    "W": ["10001", "10001", "10001", "10101", "10101", "01010", "01010"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "!": ["00100", "00100", "00100", "00100", "00100", "00000", "00100"],
}


def bubble(c):
    # a speech bubble from the whale, speaking to the judge
    x0, y0, x1, y1 = 612, 128, 892, 238
    c.polygon([(x0 + 18, y0), (x1 - 18, y0), (x1, y0 + 18), (x1, y1 - 18),
               (x1 - 18, y1), (x0 + 18, y1), (x0, y1 - 18), (x0, y0 + 18)],
              (252, 252, 250))
    c.polygon([(700, y1 - 4), (640, y1 + 52), (742, y1 - 4)], (252, 252, 250))
    text = "WOW!"
    scale = 9
    cw = 5 * scale + 12
    total = len(text) * cw - 12
    tx = (x0 + x1 - total) // 2
    ty = y0 + 22
    for ch in text:
        glyph = FONT[ch]
        for r, row in enumerate(glyph):
            for col, bit in enumerate(row):
                if bit == "1":
                    for dx in range(scale):
                        for dy in range(scale):
                            c.set(tx + col * scale + dx, ty + r * scale + dy,
                                  INK)
        tx += cw


def draw():
    c = Canvas(W, H)
    sky(c)
    stars(c)
    sun(c)
    clouds(c)
    gulls(c)
    sea(c)
    whale(c)
    spray(c)
    sailboat(c)
    bubble(c)
    return c


def write_png(path, canvas):
    raw = bytearray()
    for y in range(canvas.h):
        raw.append(0)
        raw += canvas.px[y * canvas.w * 3:(y + 1) * canvas.w * 3]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data +
                struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    png = (b"\x89PNG\r\n\x1a\n" +
           chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)) +
           chunk(b"IDAT", comp) +
           chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    canvas = draw()
    write_png(os.path.join(out_dir, "entry.png"), canvas)


if __name__ == "__main__":
    main()
