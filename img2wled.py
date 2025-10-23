#!/bin/python3

from dataclasses import dataclass
import json
import argparse
import time
from typing import Generator
import requests

from PIL import Image, ImageSequence


MAX_DATA_PER_POST = 16 * 16
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
      - i: list of pixel data, supporting two formats:

    Format 1 - Individual pixels:
      - First element: starting pixel index (integer)
      - Subsequent elements: RGB tuples for each pixel
      - Example: [0, (255,0,0), (0,255,0), (0,0,255)] for pixels 0,1,2 with colors red,green,blue

    Format 2 - Range optimization:
      - First element: starting pixel index (integer)
      - Second element: ending pixel index (integer)
      - Third element: RGB tuple for the entire range
      - Example: [0, 4, (255,255,255)] for pixels 0-4 all white

    The function automatically optimizes by using range format when consecutive pixels
    have the same color, reducing data transmission size.
    """
    frame = frame.convert("RGB")
    rows = int(args.rows)
    cols = int(args.cols)
    tt = int(args.transition_time)
    frame = frame.resize((rows, cols), resample=Image.Resampling.NEAREST)
    pixels = frame.load()
    brightness = int(args.brightness)
    frz = True  # should be True, if not effects takes over.

    # Collect all pixels first
    all_pixels = []
    for c in range(cols):
        for r in range(rows):
            all_pixels.append(pixels[r, c])

    # Generate all optimized commands for the entire image
    all_commands = optimize_pixel_segment(all_pixels, 0)

    # Split commands into segments respecting MAX_DATA_PER_POST
    # Each command tuple counts as its length in data items
    segment_start = 0

    while segment_start < len(all_commands):
        segment_commands = []
        data_count = 0

        # Add commands until we reach the limit
        for i in range(segment_start, len(all_commands)):
            command = all_commands[i]
            command_data_count = len(command)  # 2 for individual, 3 for range

            if data_count + command_data_count > MAX_DATA_PER_POST:
                break

            segment_commands.append(command)
            data_count += command_data_count

        # Convert command tuples to flat list format
        flat_commands = []
        for command in segment_commands:
            flat_commands.extend(command)

        # Add starting pixel index at the beginning
        if segment_commands:
            start_pixel = segment_commands[0][0]
            final_commands = [start_pixel] + flat_commands
        else:
            final_commands = [0]

        yield {
            "on": True,
            "tt": tt,
            "bri": brightness,
            "seg": {"frz": frz, "i": final_commands},
        }

        segment_start += len(segment_commands)


def optimize_pixel_segment(pixels: list, start_index: int) -> list:
    """
    Optimize a segment of pixels by using range format when consecutive pixels
    have the same color.

    Args:
        pixels: List of RGB tuples for the segment
        start_index: Starting pixel index for this segment

    Returns:
        List of complete command tuples. Each tuple represents either:
        - Individual pixel: (pixel_index, color)
        - Range: (start_index, end_index, color)
        End index is the last pixel in the range, not including the last pixel.
    """
    if not pixels:
        return []

    commands = []
    i = 0

    while i < len(pixels):
        current_color = pixels[i]
        range_start = i

        # Find consecutive pixels with the same color
        while i < len(pixels) and pixels[i] == current_color:
            i += 1

        range_length = i - range_start

        if range_length == 1:
            # Single pixel - use individual format
            pixel_index = start_index + range_start
            commands.append((pixel_index, current_color))
        else:
            # Multiple consecutive pixels with same color - use range format
            pixel_index = start_index + range_start
            end_index = pixel_index + range_length
            commands.append((pixel_index, end_index, current_color))

    return commands


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
                show_segment(img, segment)
            if len(args.filename) > 1:
                time.sleep(int(args.sleep) / 1000)
        if not args.loop:
            break


def show_segment(name, segment):
    if args.curl:
        print(
            f"curl -X POST 'http://{args.ip}/json/state' -H 'Content-Type: application/json' -d '{json.dumps(segment)}'"
        )
    else:

        ret = requests.post(
            f"http://{args.ip}/json/śtate",
            data=json.dumps(segment),
            headers={"Content-Type": "application/json"},
        )
        print(
            f"Sending image={name}, size={len(json.dumps(segment))}, status={ret.status_code}"
        )


def show_solid_color(color: tuple[int, int, int]):
    frame = Image.new("RGB", (int(args.rows), int(args.cols)), color)
    for image in gen_str_from_img(frame):
        show_segment("test", image)


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
