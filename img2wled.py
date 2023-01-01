#!/bin/python3

import json
import sys

from PIL import Image, ImageSequence


ROWS = 16
COLS = 16
IP = "192.168.1.33"
MAX_PIXELS = 8*16


def gen_str_from_img(frame):
    frame = frame.convert("RGB")
    frame = frame.resize((ROWS, COLS), resample=Image.NEAREST)
    lastpx = None
    pixels = frame.load()
    commands = [1]
    # frame.show()

    pxn = 0
    runl = 0
    lpxn = 0
    for c in range(COLS):
        for r in range(ROWS):
            lpxn += 1
            pxn += 1
            px = pixels[r, c]
            commands.append(px)
        if pxn >= MAX_PIXELS:
            pxn = 0
            yield {
                "on": True,
                "seg": {
                    "i": commands
                }
            }
            commands = [lpxn+1]

    yield {
        "on": True,
        "seg": {
            "i": commands
        }
    }


def gen_str(image):
    img = Image.open(image).convert("RGB")

    if image.endswith(".gif"):
        for n, frame in enumerate(ImageSequence.Iterator(img)):
            yield from gen_str_from_img(frame)
    else:
        yield from gen_str_from_img(img)


def main():
    if sys.argv[1:]:
        img = sys.argv[1]
    else:
        img = IMG
    for segment in gen_str(img):
        print(
            f"curl -X POST 'http://{IP}/json/state' -H 'Content-Type: application/json' -d '{json.dumps(segment)}'")


if __name__ == '__main__':
    main()
