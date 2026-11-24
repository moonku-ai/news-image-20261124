#!/usr/bin/env python3
"""Rasterize TrueType glyphs into a compact atlas for main.py.

Dev-time tool only (runs on THIS machine; main.py never calls it). Reads
system TTFs, parses cmap/glyf with pure stdlib, rasterizes outlines with
3x3 supersampling + non-zero winding, and writes atlas.bin: magic "ATL2"
followed by a zlib-compressed JSON document of glyph bitmaps.

Usage: python3 make_atlas.py --out atlas.bin
"""
import argparse
import base64
import json
import struct
import sys
import zlib

FONTS = {
    "serif_bold": "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
    "serif_italic": "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf",
    "sans_bold": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "sans": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
}

SPECS = [
    ("serif_bold", 56), ("serif_bold", 40), ("serif_bold", 22),
    ("serif_bold", 16), ("serif_bold", 15),
    ("serif_italic", 19),
    ("sans_bold", 13), ("sans_bold", 12), ("sans_bold", 11), ("sans_bold", 10),
    ("sans_bold", 9),
    ("sans", 13), ("sans", 12), ("sans", 11), ("sans", 10), ("sans", 9),
]

CHARSET = "".join(chr(c) for c in range(32, 127))
CHARSET += "".join(chr(c) for c in range(0xA0, 0x100))
CHARSET += "\u2013\u2014\u2018\u2019\u201c\u201d\u2022\u20ac\u2192"


def u16(b, o):
    return struct.unpack_from(">H", b, o)[0]


def i16(b, o):
    return struct.unpack_from(">h", b, o)[0]


def u32(b, o):
    return struct.unpack_from(">I", b, o)[0]


class TTF:
    def __init__(self, path):
        with open(path, "rb") as f:
            self.data = f.read()
        d = self.data
        ntab = u16(d, 4)
        self.tables = {}
        for i in range(ntab):
            o = 12 + 16 * i
            tag = d[o:o + 4].decode("latin-1")
            self.tables[tag] = (u32(d, o + 8), u32(d, o + 12))
        head = self._table("head")
        self.upem = u16(head, 18)
        self.loc_fmt = i16(head, 50)
        maxp = self._table("maxp")
        self.nglyphs = u16(maxp, 4)
        hhea = self._table("hhea")
        self.nhmetrics = u16(hhea, 34)
        self.hmtx = self._table("hmtx")
        self.cmap = self._build_cmap()
        loca = self._table("loca")
        self.loca = []
        if self.loc_fmt == 0:
            for i in range(self.nglyphs + 1):
                self.loca.append(2 * u16(loca, 2 * i))
        else:
            for i in range(self.nglyphs + 1):
                self.loca.append(u32(loca, 4 * i))
        self.glyf = self._table("glyf")

    def _table(self, tag):
        off, ln = self.tables[tag]
        return self.data[off:off + ln]

    def _build_cmap(self):
        c = self._table("cmap")
        nsub = u16(c, 2)
        best = None
        for i in range(nsub):
            plat, enc, off = u16(c, 4 + 8 * i), u16(c, 6 + 8 * i), u32(c, 8 + 8 * i)
            if plat == 3 and enc == 1:
                best = off
                break
            if best is None and plat == 0:
                best = off
        sub = c[best:]
        fmt = u16(sub, 0)
        if fmt != 4:
            raise ValueError("unsupported cmap format %d" % fmt)
        seg = u16(sub, 6) // 2
        ends = [u16(sub, 14 + 2 * i) for i in range(seg)]
        starts = [u16(sub, 16 + 2 * seg + 2 * i) for i in range(seg)]
        deltas = [i16(sub, 16 + 4 * seg + 2 * i) for i in range(seg)]
        roff_base = 16 + 6 * seg
        roffs = [u16(sub, roff_base + 2 * i) for i in range(seg)]
        glyphs = {}
        for s in range(seg):
            for code in range(starts[s], ends[s] + 1):
                if code == 0xFFFF:
                    continue
                if roffs[s] == 0:
                    g = (code + deltas[s]) % 65536
                else:
                    gi = roff_base + 2 * s + roffs[s] + 2 * (code - starts[s])
                    g = u16(sub, gi)
                    if g:
                        g = (g + deltas[s]) % 65536
                glyphs[code] = g
        return glyphs

    def advance(self, gid):
        if gid < self.nhmetrics:
            return u16(self.hmtx, 4 * gid)
        return u16(self.hmtx, 4 * (self.nhmetrics - 1))

    def outline(self, gid, depth=0):
        """Return list of contours; each contour is a list of (x, y, oncurve)."""
        if gid >= self.nglyphs or depth > 3:
            return []
        a, b = self.loca[gid], self.loca[gid + 1]
        if b <= a:
            return []
        g = self.glyf[a:b]
        ncont = i16(g, 0)
        if ncont < 0:
            # composite: recurse into components
            out = []
            o = 10
            while True:
                flags = u16(g, o)
                comp = u16(g, o + 2)
                o += 4
                if flags & 1:
                    a1, a2 = i16(g, o), i16(g, o + 2)
                    o += 4
                else:
                    a1, a2 = g[o], g[o + 1]
                    o += 2
                sx = sy = 1.0
                if flags & 8:
                    sx = i16(g, o) / 16384.0
                    sy = sx
                    o += 2
                elif flags & 0x40:
                    sx = i16(g, o) / 16384.0
                    o += 2
                    sy = i16(g, o) / 16384.0
                    o += 2
                elif flags & 0x80:
                    sx = i16(g, o) / 16384.0
                    o += 2
                    sy = i16(g, o + 2) / 16384.0
                    o += 4
                dx = dy = 0.0
                if flags & 2:
                    dx, dy = a1, a2
                for cnt in self.outline(comp, depth + 1):
                    out.append([(x * sx + dx, y * sy + dy, on) for (x, y, on) in cnt])
                if not (flags & 0x20):
                    break
            return out
        if ncont == 0:
            return []
        ends = [u16(g, 10 + 2 * i) for i in range(ncont)]
        npts = ends[-1] + 1
        ilen = u16(g, 10 + 2 * ncont)
        o = 10 + 2 * ncont + 2 + ilen
        flags = []
        while len(flags) < npts:
            f = g[o]
            o += 1
            flags.append(f)
            if f & 8:
                for _ in range(g[o]):
                    flags.append(f)
                o += 1
        xs = []
        x = 0
        for f in flags:
            if f & 2:
                d = g[o]
                o += 1
                x += d if (f & 16) else -d
            elif not (f & 16):
                x += i16(g, o)
                o += 2
            xs.append(x)
        ys = []
        y = 0
        for f in flags:
            if f & 4:
                d = g[o]
                o += 1
                y += d if (f & 32) else -d
            elif not (f & 32):
                y += i16(g, o)
                o += 2
            ys.append(y)
        contours = []
        start = 0
        for end in ends:
            pts = [(xs[i], ys[i], bool(flags[i] & 1)) for i in range(start, end + 1)]
            contours.append(pts)
            start = end + 1
        return contours


def flatten(contours):
    """Quadratic outlines -> list of edges (x0, y0, x1, y1) in font units."""
    edges = []
    for pts in contours:
        if not pts:
            continue
        # expand off-curve runs into on-curve endpoints
        seq = []
        n = len(pts)
        for i, p in enumerate(pts):
            if p[2]:
                seq.append((p[0], p[1]))
            else:
                nxt = pts[(i + 1) % n]
                if nxt[2]:
                    seq.append((p[0], p[1]))
                else:
                    seq.append(((p[0] + nxt[0]) / 2.0, (p[1] + nxt[1]) / 2.0))
        # walk: start at last on-curve point, each segment is quad or line
        # rebuild with explicit control points
        expanded = []
        m = len(pts)
        # build ordered list of (point, is_on) starting at an on-curve point
        start = 0
        while start < m and not pts[start][2]:
            start += 1
        if start == m:
            continue
        ordered = [pts[(start + i) % m] for i in range(m)]
        # first point is on-curve; iterate segments
        cur = (ordered[0][0], ordered[0][1])
        i = 1
        while i < len(ordered):
            p = ordered[i]
            if p[2]:
                edges.append((cur[0], cur[1], p[0], p[1]))
                cur = (p[0], p[1])
                i += 1
            else:
                nxt = ordered[i + 1] if i + 1 < len(ordered) else ordered[0]
                end = (nxt[0], nxt[1]) if nxt[2] else ((p[0] + nxt[0]) / 2.0, (p[1] + nxt[1]) / 2.0)
                # subdivide quadratic
                steps = 8
                px, py = cur
                for s in range(1, steps + 1):
                    t = s / steps
                    mt = 1 - t
                    qx = mt * mt * cur[0] + 2 * mt * t * p[0] + t * t * end[0]
                    qy = mt * mt * cur[1] + 2 * mt * t * p[1] + t * t * end[1]
                    edges.append((px, py, qx, qy))
                    px, py = qx, qy
                cur = end
                i += 2 if (i + 1 < len(ordered) and not ordered[i + 1][2]) else 1
                if i >= len(ordered):
                    break
        # close contour
        first = (ordered[0][0], ordered[0][1])
        if cur != first:
            edges.append((cur[0], cur[1], first[0], first[1]))
    return edges


def rasterize(ttf, gid, px, ss=3):
    """Return (adv_px, w, h, top, left, rows) with rows = list of bytes."""
    scale = px / ttf.upem
    adv = int(round(ttf.advance(gid) * scale))
    edges = flatten(ttf.outline(gid))
    if not edges:
        return adv, 0, 0, 0, 0, []
    xs = [e[0] for e in edges] + [e[2] for e in edges]
    ys = [e[1] for e in edges] + [e[3] for e in edges]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    # screen coords: x right, y down from top of glyph bbox
    left = int(xmin * scale) - 1
    top = int(ymax * scale) + 1  # px above baseline of row 0
    w = int(xmax * scale) - left + 2
    h = int(ymax * scale) - int(ymin * scale) + 2
    if w <= 0 or h <= 0:
        return adv, 0, 0, 0, 0, []
    # scale edges into subpixel space (y down, origin at bbox top-left)
    se = []
    for (x0, y0, x1, y1) in edges:
        se.append(((x0 * scale - left) * ss, (top - y0 * scale) * ss,
                   (x1 * scale - left) * ss, (top - y1 * scale) * ss))
    rows = []
    H = h * ss
    for sy in range(H):
        yc = sy + 0.5
        crosses = []
        for (x0, y0, x1, y1) in se:
            if (y0 <= yc < y1) or (y1 <= yc < y0):
                t = (yc - y0) / (y1 - y0)
                crosses.append((x0 + t * (x1 - x0), 1 if y1 > y0 else -1))
        crosses.sort()
        row = bytearray(w)
        wind = 0
        prev = 0.0
        for (cx, d) in crosses:
            if wind != 0:
                a = max(0, int(prev / ss))
                b = min(w, int(cx / ss) + 1)
                for xx in range(a, b):
                    # coverage: fraction of this pixel's sub-columns covered
                    lo = max(prev, xx * ss)
                    hi = min(cx, (xx + 1) * ss)
                    if hi > lo:
                        row[xx] = min(255, row[xx] + int(255 * (hi - lo) / ss))
            wind += d
            prev = cx
        rows.append(bytes(row))
    # downsample subpixel rows to pixel rows (average of ss rows)
    out = []
    for py in range(h):
        acc = [0] * w
        for k in range(ss):
            r = rows[py * ss + k]
            for xx in range(w):
                acc[xx] += r[xx]
        out.append(bytes(min(255, (v + ss // 2) // ss) for v in acc))
    return adv, w, h, top, left, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    doc = {"fonts": {}}
    total = 0
    for name, path in FONTS.items():
        ttf = TTF(path)
        entry = {"sizes": {}}
        for (fname, px) in SPECS:
            if fname != name:
                continue
            chars = {}
            for ch in CHARSET:
                gid = ttf.cmap.get(ord(ch), 0)
                adv, w, h, top, left, rows = rasterize(ttf, gid, px)
                chars[ch] = {
                    "adv": adv, "w": w, "h": h, "top": top, "left": left,
                    "data": base64.b64encode(b"".join(rows)).decode() if rows else "",
                }
                total += 1
            entry["sizes"][str(px)] = {"chars": chars}
        doc["fonts"][name] = entry
        print("font %s done (%d glyphs)" % (name, total), flush=True)
    blob = zlib.compress(json.dumps(doc, separators=(",", ":")).encode(), 9)
    with open(args.out, "wb") as f:
        f.write(b"ATL2")
        f.write(struct.pack(">I", len(blob)))
        f.write(blob)
    print("wrote %s (%d bytes, %d glyphs)" % (args.out, 4 + 4 + len(blob), total))


if __name__ == "__main__":
    main()
