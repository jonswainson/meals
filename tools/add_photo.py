#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Attach a photo to a recipe, breakfast or snack.

Written 21 October 2026. The photo is turned the right way up, shrunk to
1200px on its long side and saved as a JPEG of about 150KB in photos/,
named after the meal, then named in recipes.json: a recipe's own `photo`,
or `fixedPhotos` for the breakfasts and snacks that live in plan.html.

    python3 tools/add_photo.py <meal id> <image file> [alt text]
    python3 tools/add_photo.py crispy-prawn-tacos ~/Downloads/IMG_1234.HEIC

Use your own photos: images from recipe accounts belong to them.
"""
import io, json, os, re, sys
from PIL import Image, ImageOps

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
if len(sys.argv) < 3:
    raise SystemExit(__doc__)
mid, src = sys.argv[1], os.path.expanduser(sys.argv[2])
alt = sys.argv[3] if len(sys.argv) > 3 else None

data = json.load(io.open(os.path.join(BASE, "recipes.json"), encoding="utf-8"))
plan = io.open(os.path.join(BASE, "plan.html"), encoding="utf-8").read()
rec = next((r for r in data["recipes"] if r["id"] == mid), None)
fixed = re.search(r'^\s*"%s":\s*\{name:"([^"]+)"' % re.escape(mid), plan, re.M)
if not rec and not fixed:
    raise SystemExit("no recipe, breakfast or snack called %r" % mid)
name = rec["name"] if rec else fixed.group(1)

try:
    img = Image.open(src)
except Exception as e:
    raise SystemExit("can't open %s: %s (HEIC from an iPhone: export it as JPEG first)" % (src, e))
img = ImageOps.exif_transpose(img).convert("RGB")
img.thumbnail((1200, 1200))
os.makedirs(os.path.join(BASE, "photos"), exist_ok=True)
rel = "photos/%s.jpg" % mid
out = os.path.join(BASE, rel)
img.save(out, "JPEG", quality=80, optimize=True, progressive=True)

entry = {"src": rel, "alt": alt or name}
if rec:
    rec["photo"] = entry
else:
    data.setdefault("fixedPhotos", {})[mid] = entry
io.open(os.path.join(BASE, "recipes.json"), "w", encoding="utf-8").write(
    json.dumps(data, indent=2, ensure_ascii=False) + "\n")
print("%s: %s, %dx%d, %dKB" % (name, rel, img.width, img.height, os.path.getsize(out) // 1024))
