#!/usr/bin/env python3
"""Tuesday 24 November 2026 — the world in one image.

A pure-Python-stdlib program that draws a newspaper front page summing up
Tuesday 24 November 2026 and writes it to /output/entry.png (1024x1024,
under 1 MiB, deterministic: the same bytes on every run).

Every story on the page happened on, or was first reported on, Tuesday
24 November 2026 (press time 00:30 UTC); Monday-evening stories are tagged
MON EVE, Sunday events SUN EVE, and older stories are named in the DATE
CHECK box instead of being shown as today's news.

Typography: Liberation Serif (headlines) and DejaVu Sans (body), rasterized
from the system fonts by tools/make_atlas.py into atlas.bin, which ships in
this repository. main.py only reads that data file; it never touches the
network, the clock, or anything outside the repository and the output dir.
If atlas.bin is ever unreadable, a small built-in 3x5 bitmap font takes
over so the page still renders.
"""
import base64
import json
import os
import struct
import sys
import zlib

# ---------------------------------------------------------------- palette
PAPER = (247, 241, 227)      # newsprint cream
INK = (20, 20, 20)
NAVY = (14, 42, 74)
NAVY_DK = (10, 30, 54)
RED = (180, 35, 24)
MUTED = (90, 83, 72)         # warm grey for captions
HAIR = (201, 191, 169)       # hairline rules
TEAL = (15, 118, 110)
GOLD = (176, 128, 28)
GREEN = (21, 128, 61)
PURPLE = (109, 40, 217)
SLATE = (71, 85, 105)
SKY = (205, 226, 238)
SEA = (27, 58, 92)
NIGHT = (16, 32, 58)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

W = 1024
H = 1024
MX = 28                       # side margin
CW = W - 2 * MX               # content width
PRESS_TIME = "00:30 UTC"

# ---------------------------------------------------------------- atlas
# atlas.bin: magic "ATL2" + u32 length + zlib JSON:
# {"fonts": {name: {"sizes": {px: {"chars": {ch: {adv,w,h,top,left,data}}}}}}}
# char record: adv (px), w/h (px), top (px above baseline of row 0),
# left (px), data (base64 rows, 8-bit coverage per pixel, row-major).


def load_atlas():
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "atlas.bin")
    try:
        with open(path, "rb") as f:
            if f.read(4) != b"ATL2":
                return None
            n = struct.unpack(">I", f.read(4))[0]
            blob = f.read(n)
        data = json.loads(zlib.decompress(blob))
        if "serif_bold" not in data.get("fonts", {}):
            return None
        return data
    except (OSError, ValueError, KeyError, zlib.error):
        return None


ATLAS = load_atlas()

# ------------------------------------------------- emergency bitmap font
# 3x5, each glyph is 5 rows of 3 bits (LSB = left column). Only used when
# atlas.bin cannot be read.
_BITMAP = {
    "A": (0b010, 0b101, 0b111, 0b101, 0b101), "B": (0b110, 0b101, 0b110, 0b101, 0b110),
    "C": (0b011, 0b100, 0b100, 0b100, 0b011), "D": (0b110, 0b101, 0b101, 0b101, 0b110),
    "E": (0b111, 0b100, 0b110, 0b100, 0b111), "F": (0b111, 0b100, 0b110, 0b100, 0b100),
    "G": (0b011, 0b100, 0b101, 0b101, 0b011), "H": (0b101, 0b101, 0b111, 0b101, 0b101),
    "I": (0b111, 0b010, 0b010, 0b010, 0b111), "J": (0b001, 0b001, 0b001, 0b101, 0b010),
    "K": (0b101, 0b101, 0b110, 0b101, 0b101), "L": (0b100, 0b100, 0b100, 0b100, 0b111),
    "M": (0b101, 0b111, 0b111, 0b101, 0b101), "N": (0b101, 0b111, 0b111, 0b111, 0b101),
    "O": (0b010, 0b101, 0b101, 0b101, 0b010), "P": (0b110, 0b101, 0b110, 0b100, 0b100),
    "Q": (0b010, 0b101, 0b101, 0b010, 0b001), "R": (0b110, 0b101, 0b110, 0b101, 0b101),
    "S": (0b011, 0b100, 0b010, 0b001, 0b110), "T": (0b111, 0b010, 0b010, 0b010, 0b010),
    "U": (0b101, 0b101, 0b101, 0b101, 0b111), "V": (0b101, 0b101, 0b101, 0b101, 0b010),
    "W": (0b101, 0b101, 0b111, 0b111, 0b101), "X": (0b101, 0b101, 0b010, 0b101, 0b101),
    "Y": (0b101, 0b101, 0b010, 0b010, 0b010), "Z": (0b111, 0b001, 0b010, 0b100, 0b111),
    "0": (0b010, 0b101, 0b101, 0b101, 0b010), "1": (0b010, 0b110, 0b010, 0b010, 0b111),
    "2": (0b011, 0b101, 0b010, 0b100, 0b111), "3": (0b111, 0b001, 0b011, 0b001, 0b110),
    "4": (0b101, 0b101, 0b111, 0b001, 0b001), "5": (0b111, 0b100, 0b110, 0b001, 0b110),
    "6": (0b011, 0b100, 0b110, 0b101, 0b010), "7": (0b111, 0b001, 0b010, 0b010, 0b010),
    "8": (0b010, 0b101, 0b010, 0b101, 0b010), "9": (0b010, 0b101, 0b011, 0b001, 0b110),
    " ": (0, 0, 0, 0, 0), ".": (0, 0, 0, 0, 0b010), ",": (0, 0, 0, 0b010, 0b100),
    ":": (0, 0b010, 0, 0b010, 0), ";": (0, 0b010, 0, 0b010, 0b100),
    "!": (0b010, 0b010, 0b010, 0, 0b010), "?": (0b011, 0b101, 0b010, 0, 0b010),
    "-": (0, 0, 0b111, 0, 0), "'": (0b010, 0b010, 0, 0, 0),
    "(": (0b001, 0b010, 0b010, 0b010, 0b001), ")": (0b100, 0b010, 0b010, 0b010, 0b100),
    "/": (0b001, 0b001, 0b010, 0b100, 0b100), "%": (0b101, 0b001, 0b010, 0b100, 0b101),
    "&": (0b010, 0b101, 0b010, 0b101, 0b101), "+": (0, 0b010, 0b111, 0b010, 0),
    "=": (0, 0b111, 0, 0b111, 0), "$": (0b010, 0b111, 0b010, 0b111, 0b010),
}


def _bitmap_width(s, scale):
    return sum((4 if ch == " " else 4) for ch in s) * scale - scale


def _bitmap_draw(cv, x, y_base, s, color, scale):
    cx = x
    for ch in s:
        g = _BITMAP.get(ch.upper(), _BITMAP["?"])
        for r in range(5):
            bits = g[r]
            for c in range(3):
                if bits & (0b100 >> c):
                    cv.rect(cx + c * scale, y_base - 5 * scale + r * scale,
                            scale, scale, color)
        cx += 4 * scale
    return cx


# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.px = bytearray(bg * (w * h))

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = bytes(c)

    def blend(self, x, y, c, a):
        if a <= 0 or not (0 <= x < self.w and 0 <= y < self.h):
            return
        if a >= 255:
            self.set(x, y, c)
            return
        i = (y * self.w + x) * 3
        b = self.px
        b[i] = (c[0] * a + b[i] * (255 - a)) // 255
        b[i + 1] = (c[1] * a + b[i + 1] * (255 - a)) // 255
        b[i + 2] = (c[2] * a + b[i + 2] * (255 - a)) // 255

    def rect(self, x, y, w, h, c):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(c) * (x1 - x0)
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            self.px[i:i + len(row)] = row

    def hline(self, x, y, w, c, t=1):
        self.rect(x, y, w, t, c)

    def vline(self, x, y, h, c, t=1):
        self.rect(x, y, t, h, c)

    def line(self, x1, y1, x2, y2, c, t=1):
        dx, dy = abs(x2 - x1), abs(y2 - y1)
        sx = 1 if x2 > x1 else -1
        sy = 1 if y2 > y1 else -1
        err = dx - dy
        x, y = x1, y1
        while True:
            self.rect(x, y, t, t, c)
            if x == x2 and y == y2:
                return
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy

    def circle(self, cx, cy, r, c):
        for yy in range(cy - r, cy + r + 1):
            dx = int((r * r - (yy - cy) ** 2) ** 0.5) if abs(yy - cy) <= r else 0
            self.hline(cx - dx, yy, 2 * dx + 1, c)

    def ring(self, cx, cy, r, c, t=1):
        for k in range(t):
            rr = r - k
            for a in range(360):
                import math
                x = cx + int(rr * math.cos(math.radians(a)))
                y = cy + int(rr * math.sin(math.radians(a)))
                self.set(x, y, c)

    def ellipse(self, cx, cy, rx, ry, c):
        for yy in range(cy - ry, cy + ry + 1):
            t = 1 - ((yy - cy) / ry) ** 2
            if t < 0:
                continue
            dx = int(rx * t ** 0.5)
            self.hline(cx - dx, yy, 2 * dx + 1, c)

    def polygon(self, pts, c):
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        for yy in range(int(min(ys)), int(max(ys)) + 1):
            xs = []
            n = len(pts)
            for i in range(n):
                x1, y1 = pts[i]
                x2, y2 = pts[(i + 1) % n]
                if (y1 <= yy < y2) or (y2 <= yy < y1):
                    t = (yy - y1) / (y2 - y1)
                    xs.append(x1 + t * (x2 - x1))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                self.hline(int(xs[k]), yy, int(xs[k + 1]) - int(xs[k]) + 1, c)

    # ------------------------------------------------------------- text
    def _glyph(self, font, size, ch):
        if ATLAS is None:
            return None
        try:
            return ATLAS["fonts"][font]["sizes"][str(size)]["chars"][ch]
        except KeyError:
            try:
                return ATLAS["fonts"][font]["sizes"][str(size)]["chars"]["?"]
            except KeyError:
                return None

    def text_width(self, font, size, s, tracking=0):
        if ATLAS is None:
            return _bitmap_width(s, max(1, size // 6))
        w = 0
        for ch in s:
            g = self._glyph(font, size, ch)
            w += (g["adv"] if g else size // 2) + tracking
        return w - tracking if s else 0

    def text(self, font, size, x, y_base, s, color, tracking=0):
        if ATLAS is None:
            _bitmap_draw(self, x, y_base, s, color, max(1, size // 6))
            return
        cx = x
        for ch in s:
            g = self._glyph(font, size, ch)
            if g is None:
                cx += size // 2 + tracking
                continue
            if g["data"]:
                raw = base64.b64decode(g["data"])
                gw, gh = g["w"], g["h"]
                ox, oy = cx + g["left"], y_base - g["top"]
                for r in range(gh):
                    row = raw[r * gw:(r + 1) * gw]
                    for cc in range(gw):
                        a = row[cc]
                        if a:
                            self.blend(ox + cc, oy + r, color, a)
            cx += g["adv"] + tracking

    def text_center(self, font, size, cx, y_base, s, color, tracking=0):
        self.text(font, size, cx - self.text_width(font, size, s, tracking) // 2,
                  y_base, s, color, tracking)

    def text_right(self, font, size, x_right, y_base, s, color, tracking=0):
        self.text(font, size, x_right - self.text_width(font, size, s, tracking),
                  y_base, s, color, tracking)

    def wrap(self, font, size, s, max_w):
        lines, cur = [], ""
        for word in s.split(" "):
            trial = (cur + " " + word).strip()
            if self.text_width(font, size, trial) <= max_w or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
        return lines

    def para(self, font, size, x, y_top, max_w, s, color, leading=None):
        y = y_top + size
        for ln in self.wrap(font, size, s, max_w):
            self.text(font, size, x, y, ln, color)
            y += leading or int(size * 1.3)
        return y

    # -------------------------------------------------------------- png
    def png_bytes(self):
        raw = bytearray()
        stride = self.w * 3
        prev = bytearray(stride)
        for yy in range(self.h):
            row = self.px[yy * stride:(yy + 1) * stride]
            raw.append(1)  # Sub filter
            for i in range(stride):
                left = row[i - 3] if i >= 3 else 0
                raw.append((row[i] - left) & 0xFF)
        comp = zlib.compress(bytes(raw), 9)

        def chunk(tag, data):
            out = struct.pack(">I", len(data)) + tag + data
            return out + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

        ihdr = struct.pack(">IIBBBBB", self.w, self.h, 8, 2, 0, 0, 0)
        return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
                + chunk(b"IDAT", comp) + chunk(b"IEND", b""))

# ---------------------------------------------------------------- stories
# Fields: num, region, kicker, headline, body, tag ("" / "MON EVE" / "SUN EVE"),
# certainty ("R" reported / "C" claim / "F" forecast), lon, lat (map pin).
LEADS = [
    {"num": 1, "region": "TECH", "kicker": "HUANG IS BACK",
     "headline": "Nvidia restores Huang as chief",
     "body": "The board votes unanimously, 11 days after his resignation over a spy scare. Shares jump about 30% as Wall Street rallies and Trump says he vouched for him.",
     "tag": "MON EVE", "cert": "R", "lon": -122.0, "lat": 37.4},
    {"num": 2, "region": "ASIA", "kicker": "JET INCURSION",
     "headline": "Russian jet enters Korean airspace",
     "body": "Seoul briefly warns Ulleung island to evacuate after the intrusion off the east coast, then stands the alert down.",
     "tag": "", "cert": "R", "lon": 130.9, "lat": 37.5},
    {"num": 3, "region": "EUROPE", "kicker": "DRONE BREACH",
     "headline": "Russian drone violates Polish airspace",
     "body": "Warsaw reports the brief incursion during an overnight attack on western Ukraine. NATO answers by sending AWACS early-warning planes.",
     "tag": "", "cert": "R", "lon": 19.0, "lat": 52.0},
]

MEDIUM = [
    {"num": 4, "region": "EUROPE", "kicker": "EU SANCTIONS",
     "headline": "Brussels proposes new Russia curbs",
     "body": "Athletes under the Russian flag banned; visas denied to ex-fighters.",
     "tag": "MON EVE", "cert": "R", "lon": 4.4, "lat": 50.9},
    {"num": 5, "region": "AFRICA", "kicker": "WAR AT SEA",
     "headline": "Ukraine sinks Russian warship",
     "body": "Sea drones hit a corvette in Benghazi port, Kyiv says.",
     "tag": "SUN EVE", "cert": "C", "lon": 20.1, "lat": 32.1},
    {"num": 6, "region": "AMERICAS", "kicker": "IOWA PAUSE",
     "headline": "Trump halts toxic blast in Iowa",
     "body": "Army must pause detonating the decaying lead-azide stockpile.",
     "tag": "MON EVE", "cert": "R", "lon": -93.6, "lat": 41.6},
    {"num": 7, "region": "MIDDLE EAST", "kicker": "SHADOW BANKS",
     "headline": "US sanctions Iran's shadow bankers",
     "body": "Dozens are hit in a crackdown on the networks moving money for Tehran.",
     "tag": "MON EVE", "cert": "R", "lon": 51.4, "lat": 35.7},
    {"num": 8, "region": "MIDDLE EAST", "kicker": "GAZA STRIKES",
     "headline": "Israeli strikes kill three in Gaza",
     "body": "An UNRWA worker is among the dead; France condemns settler attacks.",
     "tag": "MON EVE", "cert": "R", "lon": 34.5, "lat": 31.5},
    {"num": 9, "region": "SPORT", "kicker": "CHESS CROWN",
     "headline": "Gukesh begins title defence",
     "body": "Champion, 20, faces Sindarov, 20, in Geneva — the youngest match ever.",
     "tag": "", "cert": "R", "lon": 6.1, "lat": 46.2},
]

SMALL = [
    {"num": 10, "region": "ASIA", "kicker": "BORDER TALKS",
     "headline": "India, China hold military talks",
     "body": "Commanders meet in Arunachal to ease tensions.",
     "tag": "", "cert": "R", "lon": 94.0, "lat": 28.2},
    {"num": 11, "region": "ASIA", "kicker": "AI CENTRE",
     "headline": "Modi opens AI centre at IIT Patna",
     "body": "The PM launches a Rs 400-crore research park project.",
     "tag": "", "cert": "R", "lon": 85.1, "lat": 25.6},
    {"num": 12, "region": "AFRICA", "kicker": "AFCON VERDICT DUE",
     "headline": "CAS to rule on Senegal title appeal",
     "body": "Decision due this afternoon on the stripped Africa Cup crown.",
     "tag": "", "cert": "F", "lon": -17.4, "lat": 14.7},
    {"num": 13, "region": "SPORT", "kicker": "WELLINGTON DRAW",
     "headline": "India held to a draw in Wellington",
     "body": "New Zealand bat out 120 overs, 239/5, after India's 720/9.",
     "tag": "MON EVE", "cert": "R", "lon": 174.8, "lat": -41.3},
    {"num": 14, "region": "SPORT", "kicker": "91 ALL OUT",
     "headline": "South Africa rout Bangladesh",
     "body": "Visitors bowled out for 91 at Centurion; hosts reach 88/1.",
     "tag": "", "cert": "R", "lon": 28.2, "lat": -25.9},
    {"num": 15, "region": "EUROPE", "kicker": "GHETTO LAW",
     "headline": "Denmark backs 'ghetto law'",
     "body": "The top court upholds hardline immigration housing rules.",
     "tag": "MON EVE", "cert": "R", "lon": 12.6, "lat": 55.7},
]

ALSO = [
    (16, "NATO to send AWACS planes to Poland", "MON EVE"),
    (17, "Trump: court opens path to erase hush-money conviction", "MON EVE"),
    (18, "FIFA names 2031 and 2035 Women's World Cup hosts", "MON EVE"),
    (19, "Germany to use Ukraine's Delta battle tool", "MON EVE"),
    (20, "Sparta II cargo ship still burning off Finland", "MON EVE"),
    (21, "Murmansk governor held for embezzlement", "MON EVE"),
    (22, "Beijing limits drone-part sales used by Russia", "MON EVE"),
    (23, "Iran vows to fight US naval blockade; singer flogged", "MON EVE"),
    (24, "Kenya and DR Congo renew ties", "TUE"),
    (25, "Oil falls ~3% as Libya pipeline restarts", "TUE"),
    (26, "India top court grants bail in Godhra case", "TUE"),
]

DATE_CHECK = ("NOT TODAY: COP31 collapse (Mon) · Alcaraz wins the ATP Finals (Sun) · "
              "Delta outage delays 1,900 flights (Sun) · Man City beat Liverpool 2-1 (Sun) · "
              "'Chapo Isidro' arrested (Sat) · ICJ Myanmar ruling (Thu) · Shenzhen summit (Thu) · "
              "Poland missile strike (Fri) · FAA ground stop (13 Nov)")

STATS = [("26", "STORIES"), ("7", "REGIONS"), ("15", "PINS ON THE MAP"),
         ("3", "ILLUSTRATED LEADS"), ("2", "AIRSPACE INCURSIONS"), ("1", "CEO RESTORED")]

REGIONS = [("EUROPE", 3, NAVY), ("ASIA", 3, TEAL), ("MIDDLE EAST", 2, RED),
           ("AMERICAS", 1, GOLD), ("AFRICA", 2, GREEN), ("SPORT", 3, PURPLE),
           ("TECH", 1, SLATE)]

FOOTER_SOURCES = ("Sources: Reuters · CNN · AP · BBC · The Hindu · IANS · Yonhap · "
                  "press time " + PRESS_TIME + " · all stories dated Tuesday 24 November 2026 "
                  "unless tagged MON EVE / SUN EVE.")
FOOTER_LEGEND_TAIL = ("  Pins are numbered to the stories above.  ·  "
                      "THE WORLD IN ONE DAY — Tuesday 24 November 2026.")

# Manual pin offsets (dx, dy) for stories whose true positions collide on
# the small map; a leader line joins the numbered circle to its true spot.
PIN_OFFSETS = {3: (0, -16), 4: (-16, 2), 5: (14, 10), 7: (14, -12),
               8: (2, 14), 9: (-16, 12), 10: (12, -10), 11: (-14, 12),
               15: (12, -14)}

# ------------------------------------------------------------- illustrations
def draw_nvidia(cv, x, y, w, h):
    """Chip die + rising market chart on a dark board."""
    cv.rect(x, y, w, h, NIGHT)
    cv.rect(x, y, w, 3, GOLD)
    # circuit traces
    for i, yy in enumerate(range(y + 12, y + h - 8, 16)):
        cv.hline(x + 10, yy, w - 20, (38, 66, 104), 1)
        cv.vline(x + 10 + (i * 37) % (w - 24), y + 8, h - 16, (38, 66, 104), 1)
    # chip
    cx, cy = x + w // 2 - 34, y + h // 2 - 26
    cv.rect(cx - 6, cy - 6, 68, 56, (10, 22, 40))
    cv.rect(cx, cy, 56, 44, (24, 64, 38))
    cv.rect(cx + 6, cy + 6, 44, 32, (34, 94, 54))
    for k in range(5):
        cv.rect(cx - 6, cy + 4 + k * 9, 6, 4, GOLD)
        cv.rect(cx + 56, cy + 4 + k * 9, 6, 4, GOLD)
    cv.text_center("sans_bold", 12, cx + 28, cy + 28, "NVDA", WHITE)
    # rising chart arrow
    pts = [(x + 12, y + h - 14), (x + 60, y + h - 34), (x + 96, y + h - 26),
           (x + 140, y + h - 48), (x + 190, y + h - 40), (x + w - 16, y + 16)]
    for a, b in zip(pts, pts[1:]):
        cv.line(a[0], a[1], b[0], b[1], GREEN, 3)
    ex, ey = pts[-1]
    cv.polygon([(ex - 12, ey + 2), (ex - 2, ey + 10), (ex + 2, ey - 12)], GREEN)
    cv.text("sans_bold", 11, x + w - 52, y + 16, "+30%", GREEN)


def draw_korea(cv, x, y, w, h):
    """Radar rings, a jet silhouette and Ulleung island under a warning."""
    cv.rect(x, y, w, h, SKY)
    cv.rect(x, y, w, 3, RED)
    # sun + clouds
    cv.circle(x + w - 40, y + 22, 14, (240, 200, 90))
    for cx, cy in ((x + 30, y + 24), (x + 90, y + 18), (x + 160, y + 28)):
        cv.ellipse(cx, cy, 22, 7, WHITE)
        cv.ellipse(cx + 12, cy + 3, 16, 6, WHITE)
    # radar rings
    rx, ry = x + 64, y + h - 34
    for r in (30, 20, 10):
        cv.ring(rx, ry, r, TEAL, 2)
    cv.line(rx, ry, rx + 26, ry - 20, TEAL, 2)
    cv.circle(rx + 26, ry - 20, 3, RED)
    # island
    cv.polygon([(x + 30, y + h - 6), (x + 46, y + h - 30), (x + 70, y + h - 34),
                (x + 92, y + h - 22), (x + 104, y + h - 6)], (46, 110, 68))
    cv.polygon([(x + 46, y + h - 30), (x + 58, y + h - 44), (x + 70, y + h - 34)],
               (30, 84, 52))
    # jet silhouette
    jx, jy = x + w - 120, y + 52
    cv.polygon([(jx, jy), (jx + 46, jy + 6), (jx + 70, jy + 2), (jx + 46, jy + 10),
                (jx + 58, jy + 16), (jx + 40, jy + 14), (jx + 10, jy + 12),
                (jx - 6, jy + 8)], (40, 48, 60))
    cv.polygon([(jx + 18, jy + 2), (jx + 30, jy + 6), (jx + 18, jy + 8)], (40, 48, 60))
    # warning triangle
    tx, ty = x + w - 44, y + h - 40
    cv.polygon([(tx, ty), (tx + 26, ty), (tx + 13, ty - 22)], (240, 200, 90))
    cv.polygon([(tx + 3, ty - 3), (tx + 23, ty - 3), (tx + 13, ty - 20)], (180, 35, 24))
    cv.text_center("sans_bold", 11, tx + 13, ty - 6, "!", WHITE)


def draw_poland(cv, x, y, w, h):
    """Night sky, an AWACS plane with its radar dome, dotted flight path."""
    cv.rect(x, y, w, h, NIGHT)
    cv.rect(x, y, w, 3, WHITE)
    # stars
    for (sx, sy) in ((18, 14), (52, 26), (96, 12), (150, 20), (200, 10),
                     (250, 24), (290, 14), (30, 48), (120, 44), (220, 40)):
        cv.rect(x + sx, y + sy, 2, 2, WHITE)
    # moon
    cv.circle(x + w - 36, y + 24, 13, (238, 230, 210))
    cv.circle(x + w - 31, y + 20, 11, NIGHT)
    # dotted flight path
    for i in range(0, w - 30, 12):
        cv.rect(x + 14 + i, y + h - 26 - (i // 14), 4, 2, GOLD)
    # AWACS plane
    px, py = x + w // 2 - 70, y + 34
    cv.polygon([(px, py + 10), (px + 120, py + 10), (px + 140, py + 14),
                (px + 120, py + 18), (px, py + 18)], (205, 215, 225))
    cv.polygon([(px + 96, py + 10), (px + 116, py + 2), (px + 124, py + 10)],
               (205, 215, 225))
    cv.polygon([(px + 20, py + 18), (px + 34, py + 30), (px + 44, py + 18)],
               (205, 215, 225))
    # radar dome + strut
    cv.vline(px + 62, py - 6, 8, (160, 170, 180), 2)
    cv.ellipse(px + 62, py - 10, 22, 7, (225, 232, 238))
    cv.ellipse(px + 62, py - 12, 22, 5, WHITE)
    # polish flag strip
    cv.rect(x, y + h - 12, w // 2, 6, WHITE)
    cv.rect(x + w // 2, y + h - 12, w // 2, 6, RED)
    cv.text("sans_bold", 10, x + 28, y + 16, "AWACS TO POLAND", GOLD)


# ------------------------------------------------------------- world map
# Coarse continent outlines (lon, lat) drawn by hand for a stylized map.
CONTINENTS = [
    [(-168, 66), (-140, 70), (-125, 72), (-110, 68), (-95, 69), (-85, 66),
     (-80, 73), (-70, 62), (-65, 60), (-55, 52), (-60, 47), (-70, 44),
     (-75, 39), (-80, 32), (-81, 26), (-84, 30), (-90, 29), (-97, 26),
     (-105, 22), (-110, 24), (-115, 30), (-120, 34), (-125, 40), (-125, 49),
     (-130, 55), (-140, 60), (-155, 58), (-165, 60)],
    [(-58, 64), (-45, 60), (-40, 64), (-30, 68), (-20, 70), (-25, 76),
     (-40, 80), (-55, 76), (-60, 74)],
    [(-80, 9), (-75, 11), (-70, 12), (-62, 10), (-55, 6), (-50, 0),
     (-44, -3), (-35, -8), (-40, -15), (-48, -25), (-55, -35), (-65, -41),
     (-70, -50), (-73, -53), (-70, -40), (-73, -30), (-77, -20), (-80, -12),
     (-81, -5), (-80, 0)],
    [(-17, 15), (-15, 20), (-10, 25), (-5, 30), (0, 35), (10, 37),
     (20, 32), (30, 31), (35, 28), (40, 20), (43, 12), (48, 11), (51, 10),
     (44, 0), (40, -10), (35, -20), (32, -28), (28, -33), (20, -35),
     (15, -30), (12, -18), (13, -10), (9, 4), (4, 6), (-8, 5), (-13, 8), (-17, 12)],
    [(-10, 36), (-9, 43), (-2, 48), (-5, 50), (0, 51), (5, 53), (8, 57),
     (10, 59), (5, 60), (5, 62), (10, 64), (15, 68), (20, 70), (30, 70),
     (40, 68), (50, 69), (60, 69), (70, 72), (80, 73), (90, 75), (100, 76),
     (110, 74), (120, 73), (130, 72), (140, 72), (150, 70), (160, 69),
     (170, 67), (178, 65), (178, 62), (170, 60), (162, 56), (158, 52),
     (150, 59), (142, 59), (140, 54), (135, 44), (130, 42), (127, 40),
     (122, 38), (120, 32), (115, 28), (110, 20), (108, 18), (105, 10),
     (103, 7), (100, 6), (98, 10), (95, 15), (92, 21), (88, 22), (86, 20),
     (80, 15), (77, 8), (75, 12), (72, 20), (66, 25), (62, 25), (58, 26),
     (56, 27), (52, 28), (50, 29), (48, 30), (44, 29), (40, 30), (36, 36),
     (33, 36), (30, 36), (26, 38), (23, 36), (22, 37), (19, 40), (16, 38),
     (12, 44), (8, 44), (3, 43), (0, 40), (-2, 37), (-6, 36), (-9, 37)],
    [(-5, 50), (-3, 53), (-5, 56), (-3, 58), (-1, 57), (0, 53), (-1, 51)],
    [(130, 31), (132, 33), (135, 34), (137, 35), (140, 36), (141, 39),
     (142, 42), (144, 44), (142, 44), (140, 41), (139, 38), (137, 35),
     (135, 33), (132, 32)],
    [(95, 5), (98, 6), (100, 0), (104, -3), (108, -6), (112, -7), (116, -8),
     (120, -9), (122, -10), (118, -9), (114, -8), (110, -7), (106, -6),
     (102, -4), (98, 2)],
    [(109, 1), (113, 4), (117, 6), (119, 1), (117, -3), (112, -4), (109, -1)],
    [(113, -22), (114, -30), (115, -34), (118, -35), (124, -33), (129, -32),
     (132, -32), (135, -35), (138, -35), (140, -38), (145, -38), (150, -37),
     (153, -32), (153, -27), (150, -22), (146, -19), (142, -15), (142, -11),
     (140, -17), (136, -15), (135, -12), (132, -12), (130, -13), (126, -14),
     (122, -17), (118, -20)],
    [(167, -45), (170, -43), (173, -41), (175, -38), (177, -38), (176, -40),
     (174, -42), (171, -44), (168, -46)],
]


def draw_map(cv, x, y, w, h):
    """Stylized world map with numbered pins for the 15 card stories."""
    cv.rect(x, y, w, h, (216, 230, 238))
    # land
    scale = min(w / 360.0, h / 140.0)
    ox = x + (w - 360 * scale) / 2
    oy = y + (h - 140 * scale) / 2

    def proj(lon, lat):
        return (ox + (lon + 180) * scale, oy + (80 - lat) * scale)

    for cont in CONTINENTS:
        cv.polygon([proj(lon, lat) for (lon, lat) in cont], (216, 198, 158))
    # graticule
    for lon in (-120, -60, 0, 60, 120):
        px = proj(lon, 0)[0]
        cv.vline(int(px), int(y), int(h), (196, 212, 222), 1)
    for lat in (60, 30, 0, -30):
        py = proj(0, lat)[1]
        cv.hline(int(x), int(py), int(w), (196, 212, 222), 1)
    # pins: a small dot at the true spot, numbered circle offset where
    # neighbours collide, joined by a leader line
    for st in LEADS + MEDIUM + SMALL:
        px, py = proj(st["lon"], st["lat"])
        px, py = int(px), int(py)
        dx, dy = PIN_OFFSETS.get(st["num"], (0, 0))
        cx, cy = px + dx, py + dy
        cv.circle(px, py, 2, RED)
        if (dx, dy) != (0, 0):
            cv.line(px, py, cx, cy, RED, 1)
        cv.circle(cx, cy, 8, RED)
        cv.text_center("sans_bold", 9, cx, cy + 3, str(st["num"]), WHITE)
    return

# ---------------------------------------------------------------- layout
def region_color(region):
    for (name, _n, col) in REGIONS:
        if name == region:
            return col
    return NAVY


def _num_chip(cv, x, y, num):
    cv.rect(x, y, 16, 16, NAVY)
    cv.text_center("sans_bold", 10, x + 8, y + 12, str(num), WHITE)


def _cert_mark(cv, x, y, cert):
    if cert == "R":
        cv.circle(x, y, 4, INK)
    elif cert == "C":
        cv.circle(x, y, 4, GOLD)
    else:
        cv.ring(x, y, 4, INK, 2)


def _tag(cv, x_right, y_base, tag):
    if tag:
        cv.text_right("sans_bold", 9, x_right, y_base, tag, MUTED)


LEAD_DRAW = [draw_nvidia, draw_korea, draw_poland]


def draw_lead_card(cv, x, y, w, h, story, draw_fn):
    draw_fn(cv, x, y, w, 96)
    _num_chip(cv, x + 6, y + 6, story["num"])
    col = region_color(story["region"])
    cv.text("sans_bold", 10, x, y + 112, story["kicker"], col, tracking=1)
    _tag(cv, x + w, y + 112, story["tag"])
    hl = cv.wrap("serif_bold", 22, story["headline"], w)[:2]
    yy = y + 134
    for ln in hl:
        cv.text("serif_bold", 22, x, yy, ln, INK)
        yy += 22
    body = cv.wrap("sans", 10, story["body"], w)[:3]
    yy = y + 170
    for ln in body:
        cv.text("sans", 10, x, yy, ln, INK)
        yy += 12


def draw_medium_card(cv, x, y, w, h, story):
    cv.rect(x, y, w, 1, HAIR)
    _num_chip(cv, x, y + 6, story["num"])
    col = region_color(story["region"])
    cv.text("sans_bold", 10, x + 22, y + 18, story["kicker"], col, tracking=1)
    hl = cv.wrap("sans_bold", 13, story["headline"], w)[:2]
    yy = y + 36
    for ln in hl:
        cv.text("sans_bold", 13, x, yy, ln, INK)
        yy += 16
    body = cv.wrap("sans", 11, story["body"], w)[:3]
    yy = y + 70
    for ln in body:
        cv.text("sans", 11, x, yy, ln, INK)
        yy += 13
    _cert_mark(cv, x + 5, y + h - 12, story["cert"])
    _tag(cv, x + w, y + h - 8, story["tag"])


def draw_small_card(cv, x, y, w, h, story):
    cv.rect(x, y, w, 1, HAIR)
    _num_chip(cv, x, y + 6, story["num"])
    col = region_color(story["region"])
    cv.text("sans_bold", 10, x + 22, y + 18, story["kicker"], col, tracking=1)
    hl = cv.wrap("sans_bold", 12, story["headline"], w)[:2]
    yy = y + 34
    for ln in hl:
        cv.text("sans_bold", 12, x, yy, ln, INK)
        yy += 15
    body = cv.wrap("sans", 10, story["body"], w)[:2]
    yy = y + 66
    for ln in body:
        cv.text("sans", 10, x, yy, ln, INK)
        yy += 12
    _cert_mark(cv, x + 5, y + h - 10, story["cert"])
    _tag(cv, x + w, y + h - 6, story["tag"])


def build_page():
    cv = Canvas(W, H, PAPER)
    # ---- top kicker bar
    cv.rect(0, 0, W, 28, NAVY)
    cv.text("sans_bold", 13, MX, 20, "THE WORLD IN ONE DAY", WHITE, tracking=2)
    cv.text_right("sans_bold", 11, W - MX, 20,
                  "26 STORIES · 7 REGIONS · EVERY ONE DATED TUESDAY 24 NOVEMBER 2026",
                  WHITE, tracking=1)
    # ---- masthead
    cv.text_center("serif_bold", 56, W // 2, 94, "Tuesday 24 November 2026", INK)
    cv.text_center("serif_italic", 19, W // 2, 122,
                   "Nvidia restores its chief · Russian jets test two borders · "
                   "A chess crown begins in Geneva", RED)
    cv.hline(MX, 130, CW, INK, 1)
    cv.hline(MX, 133, CW, INK, 2)
    # ---- stats strip
    cell = CW // 6
    for i, (num, label) in enumerate(STATS):
        cx = MX + i * cell + cell // 2
        cv.text_center("serif_bold", 32, cx, 168, num, INK)
        cv.text_center("sans", 10, cx, 184, label, MUTED)
    cv.hline(MX, 196, CW, HAIR, 1)
    # ---- region tabs
    tab_texts = ["%s %d" % (name, n) for (name, n, _c) in REGIONS]
    widths = [cv.text_width("sans_bold", 11, t) + 18 for t in tab_texts]
    total = sum(widths)
    tx = MX
    for (name, n, col), t, tw in zip(REGIONS, tab_texts, widths):
        w = int(tw * CW / total)
        cv.rect(tx, 204, w, 20, col)
        cv.text_center("sans_bold", 11, tx + w // 2, 218, t, WHITE)
        tx += w
    # ---- ticker
    cv.rect(MX, 230, CW, 18, NAVY_DK)
    tlabel = "THE DAY IN BRIEF"
    tw = cv.text_width("sans_bold", 10, tlabel, tracking=1)
    cv.text("sans_bold", 10, MX + 8, 243, tlabel, GOLD, tracking=1)
    cv.text("sans", 10, MX + 8 + tw + 12, 243,
            "KOREA WARNS AFTER JET INCURSION   ·   POLAND: DRONE BREACH   ·   "
            "NVIDIA: HUANG IS BACK   ·   CHESS CROWN BEGINS IN GENEVA   ·   "
            "PRESS TIME " + PRESS_TIME, WHITE)
    # ---- leads
    lw = (CW - 2 * 13) // 3
    for i, story in enumerate(LEADS):
        draw_lead_card(cv, MX + i * (lw + 13), 256, lw, 194, story, LEAD_DRAW[i])
    # ---- medium
    mw = (CW - 5 * 6) // 6
    for i, story in enumerate(MEDIUM):
        draw_medium_card(cv, MX + i * (mw + 6), 458, mw, 138, story)
    # ---- small
    for i, story in enumerate(SMALL):
        draw_small_card(cv, MX + i * (mw + 6), 604, mw, 106, story)
    # ---- bottom: map + also
    by, bh = 718, 220
    cv.rect(MX, by, 300, bh, PAPER)
    cv.rect(MX, by, 300, 1, HAIR)
    cv.rect(MX, by + bh - 1, 300, 1, HAIR)
    cv.rect(MX, by, 1, bh, HAIR)
    cv.rect(MX + 299, by, 1, bh, HAIR)
    cv.text("sans_bold", 11, MX + 8, by + 16, "WHERE IT HAPPENED", INK)
    cv.text_right("sans", 9, MX + 292, by + 16, "pins = story numbers", MUTED)
    draw_map(cv, MX + 4, by + 22, 292, bh - 26)
    ax = MX + 308
    aw = W - MX - ax
    cv.rect(ax, by, aw, bh, PAPER)
    cv.rect(ax, by, aw, 1, HAIR)
    cv.rect(ax, by + bh - 1, aw, 1, HAIR)
    cv.rect(ax, by, 1, bh, HAIR)
    cv.rect(ax + aw - 1, by, 1, bh, HAIR)
    cv.text("sans_bold", 11, ax + 8, by + 16,
            "ALSO ON TUESDAY 24 NOVEMBER — 11 MORE STORIES", INK)
    colw = (aw - 16) // 2
    for j, (num, text, tag) in enumerate(ALSO):
        col = j // 6
        row = j % 6
        ix = ax + 8 + col * colw
        iy = by + 40 + row * 17
        cv.text("sans_bold", 10, ix, iy, str(num), RED)
        full = text + (" (" + tag + ")" if tag == "TUE" else "")
        maxw = colw - 26
        if cv.text_width("sans", 10, full) > maxw:
            full = text
        cv.text("sans", 10, ix + 20, iy, full, INK)
    # ---- date check
    dy = 946
    cv.rect(MX, dy, CW, 40, PAPER)
    cv.rect(MX, dy, CW, 2, RED)
    cv.rect(MX, dy + 38, CW, 2, RED)
    cv.rect(MX, dy, 2, 40, RED)
    cv.rect(MX + CW - 2, dy, 2, 40, RED)
    cv.text("sans_bold", 11, MX + 8, dy + 15, "DATE CHECK", RED)
    lx = MX + 8 + cv.text_width("sans_bold", 11, "DATE CHECK") + 10
    lines = cv.wrap("sans", 11, DATE_CHECK, W - MX - lx - 8)
    ly = dy + 15
    for ln in lines[:2]:
        cv.text("sans", 11, lx, ly, ln, INK)
        ly += 14
    # ---- footer (certainty marks drawn as shapes: the atlas has no ●◐○)
    cv.text("sans", 9, MX, 996, FOOTER_SOURCES, MUTED)
    fx = MX
    cv.text("sans", 9, fx, 1008, "Certainty:", MUTED)
    fx += cv.text_width("sans", 9, "Certainty:") + 8
    cv.circle(fx + 4, 1005, 4, INK)
    fx += 12
    cv.text("sans", 9, fx, 1008, "REPORTED", MUTED)
    fx += cv.text_width("sans", 9, "REPORTED") + 8
    cv.circle(fx + 4, 1005, 4, GOLD)
    fx += 12
    cv.text("sans", 9, fx, 1008, "CLAIM", MUTED)
    fx += cv.text_width("sans", 9, "CLAIM") + 8
    cv.ring(fx + 4, 1005, 4, INK, 2)
    fx += 12
    cv.text("sans", 9, fx, 1008, "FORECAST" + FOOTER_LEGEND_TAIL, MUTED)
    # ---- bottom bar
    cv.rect(0, 1014, W, 10, NAVY)
    return cv


def resolve_outdir():
    cands = []
    env = os.environ.get("MAKEFUN_OUTPUT_DIR")
    if env:
        cands.append(env)
    cands.append("/output")
    cands.append("output")
    for d in cands:
        try:
            os.makedirs(d, exist_ok=True)
            probe = os.path.join(d, ".write_test")
            with open(probe, "wb") as f:
                f.write(b"")
            os.remove(probe)
            return d
        except OSError:
            continue
    return "."


def render_to(path):
    """Render the page and write the PNG to an explicit path. Returns bytes."""
    data = build_page().png_bytes()
    d = os.path.dirname(os.path.abspath(path))
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)
    return data


def main():
    outdir = resolve_outdir()
    data = render_to(os.path.join(outdir, "entry.png"))
    print("wrote %s (%d bytes)" % (os.path.join(outdir, "entry.png"), len(data)))


if __name__ == "__main__":
    main()
