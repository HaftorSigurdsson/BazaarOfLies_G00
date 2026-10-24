#!/usr/bin/env python3
"""Bazaar of Lies — plate ingestion (setup/make_plates.py).

Turns raw AI-generated motif art into uniform Herald plates:

    uv run setup/make_plates.py                # process docs/assets/plates/
    uv run setup/make_plates.py --dir <dir>   # any other folder

For every *.jpg / *.jpeg in the plates directory:
  1. grayscale conversion (plates print as gray ink, never color);
  2. gentle autocontrast (keeps gray midtones — no hard threshold);
  3. trim near-white margins left by the image generator;
  4. pad with paper-white to a uniform 3:1 band (the press column plate);
  5. save as <name>.png next to the edition-pressing code's assets.

The raw jpgs are moved into <dir>/raw/ so the plates folder holds only
finished *.png plates. Idempotent: run again any time new art arrives.
"""
import argparse
import glob
import os
import shutil
import sys

from PIL import Image, ImageOps

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DIR = os.path.join(REPO_ROOT, "docs", "assets", "plates")

WHITE_LIMIT = 245          # pixels >= this count as paper-white
PAD_FRACTION = 0.06        # white breathing room kept around the art
TARGET_ASPECT = 3.0        # plate band aspect (width : height)


def trim_white(im):
    """Crop near-white margins, keeping a small padding."""
    mask = im.point(lambda p: 255 if p < WHITE_LIMIT else 0)
    bbox = mask.getbbox()
    if bbox is None:                       # a blank sheet — nothing to keep
        return im
    w, h = im.size
    px = int(max(w, h) * PAD_FRACTION)
    left = max(0, bbox[0] - px)
    top = max(0, bbox[1] - px)
    right = min(w, bbox[2] + px)
    bottom = min(h, bbox[3] + px)
    return im.crop((left, top, right, bottom))


def pad_to_band(im):
    """Pad with paper-white to the target wide aspect, art centred."""
    w, h = im.size
    band_w = max(w, int(round(h * TARGET_ASPECT)))
    band_h = int(round(band_w / TARGET_ASPECT))
    canvas = Image.new("L", (band_w, band_h), 255)
    canvas.paste(im, ((band_w - w) // 2, (band_h - h) // 2))
    return canvas


def process(path, out_path):
    with Image.open(path) as im:
        gray = im.convert("L")
    gray = trim_white(gray)
    if gray.size[0] < 16 or gray.size[1] < 16:
        return None                       # effectively empty image
    gray = ImageOps.autocontrast(gray, cutoff=1)
    plate = pad_to_band(gray)
    plate.save(out_path, optimize=True)
    return plate.size


def main():
    ap = argparse.ArgumentParser(description="Ingest Herald plate art")
    ap.add_argument("--dir", default=DEFAULT_DIR,
                    help="Plates directory (default docs/assets/plates)")
    args = ap.parse_args()
    plates_dir = args.dir
    raw_dir = os.path.join(plates_dir, "raw")
    os.makedirs(raw_dir, exist_ok=True)

    jpgs = sorted(glob.glob(os.path.join(plates_dir, "*.jpg"))
                  + glob.glob(os.path.join(plates_dir, "*.jpeg")))
    if not jpgs:
        print("no raw art found (expecting *.jpg in", plates_dir + ")")
        return 0

    for path in jpgs:
        name = os.path.splitext(os.path.basename(path))[0]
        out_path = os.path.join(plates_dir, name + ".png")
        try:
            size = process(path, out_path)
        except Exception as e:
            print(f"FAIL  {name}: {type(e).__name__}: {e}")
            continue
        if size is None:
            print(f"SKIP  {name}: image appears blank")
            continue
        shutil.move(path, os.path.join(raw_dir, os.path.basename(path)))
        print(f"OK    {name}.png  {size[0]}x{size[1]}  "
              f"(grayscale, trimmed, 3:1 band)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
