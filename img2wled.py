#!/bin/python3

from dataclasses import dataclass
import json
import argparse
import time
from typing import Generator
import requests

from PIL import Image, ImageSequence


MAX_PIXELS_PER_POST = 8 * 16
args = None


def gen_str_from_img(frame: Image.Image) -> Generator[dict, None, None]:
    """
    To all image can be sent in one go, so it needs to be split into multiple segments.
    This function returns a generator that yields one segment at a time.
    Each segment is a dict with the following keys:
    - on: boolean, true if the segment is on
    - tt: integer, transition time in milliseconds
    - bri: integer, brightness of the segment
    - seg: dict with the following keys:
      - frz: boolean, true if the segment is frozen
      - i: list of integers, pixel values
      The i list is a list of integers, each integer is a pixel value.
      The pixel value is a tuple of three integers, each integer is a color value.
      The color value is a integer between 0 and 255.
      The pixel value is a tuple of three integers, each integer is a color value.
    """
    frame = frame.convert("RGB")
    rows = int(args.rows)
    cols = int(args.cols)
    tt = int(args.transition_time)
    frame = frame.resize((rows, cols), resample=Image.NEAREST)
    pixels = frame.load()
    commands = [0]
    # frame.show()
    brightness = int(args.brightness)
    frz = True  # should be True, if not effects takes over.

    pxn = 0  # pixel number in this segment
    lpxn = 0  # total pixel number in this frame
    for c in range(cols):
        for r in range(rows):
            px = pixels[r, c]
            # if pxn == 0:
            #     commands.append(px)  # double?
            lpxn += 1
            pxn += 1
            commands.append(px)
        if pxn >= MAX_PIXELS_PER_POST:
            pxn = 0
            yield {
                "on": True,
                "tt": tt,
                "bri": brightness,
                "seg": {"frz": frz, "i": commands},
            }
            commands = [lpxn]

    yield {
        "on": True,
        "tt": tt,
        "bri": brightness,
        "seg": {
            "frz": frz,
            "i": commands,
        },
    }


def gen_str(image):
    img = Image.open(image).convert("RGB")

    if image.endswith(".gif"):
        for n, frame in enumerate(ImageSequence.Iterator(img)):
            yield from gen_str_from_img(frame)
    else:
        yield from gen_str_from_img(img)


def setup():
    global args
    parser = argparse.ArgumentParser(
        prog="img2wled",
        description="Convert any image to curl commands",
        epilog="To be used to print images a WLED matrixes.",
    )

    parser.add_argument("filename", nargs="*")
    parser.add_argument("-c", "--cols", help="Column count", default=16)
    parser.add_argument("-r", "--rows", help="Row count", default=16)
    parser.add_argument("--ip", help="IP to send to.", default="wled.local")
    parser.add_argument(
        "--sleep", help="ms to sleep between images, if several given.", default="3000"
    )
    parser.add_argument(
        "--curl",
        help="Print curl commands, instead of directly executing the request",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--test-color",
        help="Send solid white color to entire panel for testing",
        default=None,
        nargs="?",
    )
    parser.add_argument(
        "--brightness",
        help="Brightness of the color, 0-255",
        default=10,  # higher brightness gives me a
        type=int,
    )
    parser.add_argument(
        "--transition-time",
        help="Transition time in milliseconds -- mayeb does not work?",
        default=0,
        type=int,
    )
    parser.add_argument(
        "--loop",
        help="Loop the images",
        action="store_true",
        default=False,
    )
    args = parser.parse_args()


def show_images(images):
    while True:
        for img in images:
            if not img:
                print("Required image file name")
                return
            # img = sys.argv[1]
            for segment in gen_str(img):
                show_segment(segment)
            if len(args.filename) > 1:
                time.sleep(int(args.sleep) / 1000)
        if not args.loop:
            break


def show_segment(segment):
    if args.curl:
        print(
            f"curl -X POST 'http://{args.ip}/json/state' -H 'Content-Type: application/json' -d '{json.dumps(segment)}'"
        )
    else:
        requests.post(
            f"http://{args.ip}/json/śtate",
            data=json.dumps(segment),
            headers={"Content-Type": "application/json"},
        )


def show_solid_color(color: tuple[int, int, int]):
    frame = Image.new("RGB", (int(args.rows), int(args.cols)), color)
    for image in gen_str_from_img(frame):
        show_segment(image)


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    if len(hex_color) == 4:  # #rgb
        return tuple(int(hex_color[i] * 2, 16) for i in (1, 2, 3))
    elif len(hex_color) == 7:  # #rrggbb
        return tuple(int(hex_color[i : i + 2], 16) for i in (1, 3, 5))
    raise ValueError(f"Invalid hex color: {hex_color}")


def main():
    setup()

    if args.test_color:
        color = hex_to_rgb(args.test_color)
        show_solid_color(color)
        return

    show_images(args.filename)


if __name__ == "__main__":
    main()
