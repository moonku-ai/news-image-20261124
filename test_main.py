#!/usr/bin/env python3
"""Local tests for the news-image-20261124 entry (pure stdlib).

Run: python3 test_main.py
Checks: atlas loads, text fits its line budgets, PNG is 1024x1024 and
<= 1 MiB, two runs are byte-identical, a clean-directory run (grader
simulation) works, and the page still renders if atlas.bin is missing.
"""
import importlib
import os
import shutil
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import main

FAILURES = []


def check(name, ok, detail=""):
    print("%s %s %s" % ("PASS" if ok else "FAIL", name, detail))
    if not ok:
        FAILURES.append(name)


def png_info(path):
    with open(path, "rb") as f:
        data = f.read()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "bad PNG signature"
    w, h = struct.unpack(">II", data[16:24])
    return data, w, h


def test_atlas():
    check("atlas loads", main.ATLAS is not None)
    if main.ATLAS is not None:
        fonts = main.ATLAS["fonts"]
        check("atlas has serif_bold 56",
              "56" in fonts["serif_bold"]["sizes"])
        check("atlas has sans 9",
              "9" in fonts["sans"]["sizes"])


def test_text_fit():
    cv = main.build_page()
    bad = []
    for st in main.LEADS:
        hl = cv.wrap("serif_bold", 22, st["headline"], 314)
        bd = cv.wrap("sans", 10, st["body"], 314)
        if len(hl) > 2 or len(bd) > 3:
            bad.append(("lead", st["num"], len(hl), len(bd)))
    for st in main.MEDIUM:
        hl = cv.wrap("sans_bold", 13, st["headline"], 156)
        bd = cv.wrap("sans", 11, st["body"], 156)
        if len(hl) > 2 or len(bd) > 3:
            bad.append(("med", st["num"], len(hl), len(bd)))
    for st in main.SMALL:
        hl = cv.wrap("sans_bold", 12, st["headline"], 156)
        bd = cv.wrap("sans", 10, st["body"], 156)
        if len(hl) > 2 or len(bd) > 2:
            bad.append(("small", st["num"], len(hl), len(bd)))
    check("all headlines/bodies fit line budgets", not bad, str(bad))
    # header/footer widths
    check("masthead fits", cv.text_width("serif_bold", 56, "Tuesday 24 November 2026") <= 968)
    check("ticker fits",
          cv.text_width("sans", 10, "KOREA WARNS AFTER JET INCURSION   ·   POLAND: DRONE BREACH   ·   NVIDIA: HUANG IS BACK   ·   CHESS CROWN BEGINS IN GENEVA   ·   PRESS TIME 00:30 UTC") <= 825)
    check("date-check fits 2 lines",
          len(cv.wrap("sans", 11, main.DATE_CHECK, 800)) <= 2)


def test_render(tmp):
    p1 = os.path.join(tmp, "a.png")
    p2 = os.path.join(tmp, "b.png")
    d1 = main.render_to(p1)
    d2 = main.render_to(p2)
    check("deterministic bytes", d1 == d2)
    check("PNG <= 1 MiB", len(d1) <= 1048576, "(%d bytes)" % len(d1))
    _d, w, h = png_info(p1)
    check("PNG is 1024x1024", (w, h) == (1024, 1024), "(%dx%d)" % (w, h))
    return d1


def test_clean_dir(tmp):
    d = os.path.join(tmp, "grader")
    os.makedirs(d)
    for f in ("main.py", "atlas.bin"):
        shutil.copy(os.path.join(HERE, f), os.path.join(d, f))
    out = os.path.join(tmp, "out")
    env = dict(os.environ, MAKEFUN_OUTPUT_DIR=out)
    r = subprocess.run([sys.executable, "main.py"], cwd=d, env=env,
                       capture_output=True, text=True, timeout=120)
    check("clean-dir run exits 0", r.returncode == 0, r.stderr[-300:])
    p = os.path.join(out, "entry.png")
    check("clean-dir writes entry.png", os.path.exists(p))
    if os.path.exists(p):
        _d, w, h = png_info(p)
        check("clean-dir PNG 1024x1024", (w, h) == (1024, 1024))
        with open(p, "rb") as f:
            got = f.read()
        with open(os.path.join(tmp, "a.png"), "rb") as f:
            want = f.read()
        check("clean-dir bytes match local render", got == want)


def test_fallback(tmp):
    main.ATLAS = None
    try:
        data = main.build_page().png_bytes()
        check("fallback renders without atlas", len(data) > 10000,
              "(%d bytes)" % len(data))
    finally:
        importlib.reload(main)


def test_story_counts():
    n = len(main.LEADS) + len(main.MEDIUM) + len(main.SMALL) + len(main.ALSO)
    check("26 stories total", n == 26, "(%d)" % n)
    nums = [s["num"] for s in main.LEADS + main.MEDIUM + main.SMALL]
    check("pins 1-15 unique", sorted(nums) == list(range(1, 16)))
    check("also numbered 16-26",
          [a[0] for a in main.ALSO] == list(range(16, 27)))
    check("region tabs sum to 15",
          sum(n for _n, n, _c in main.REGIONS) == 15)


def main_test():
    test_atlas()
    test_text_fit()
    test_story_counts()
    tmp = tempfile.mkdtemp(prefix="n24-test-")
    try:
        test_render(tmp)
        test_clean_dir(tmp)
        test_fallback(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print()
    if FAILURES:
        print("FAILURES: %s" % ", ".join(FAILURES))
        return 1
    print("ALL TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main_test())
