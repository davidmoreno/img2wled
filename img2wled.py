#!/bin/python3

from dataclasses import dataclass
import json
import argparse
import time
import requests

from PIL import Image, ImageSequence


MAX_PIXELS = 8*16
args = None


def gen_str_from_img(frame):
    frame = frame.convert("RGB")
    rows = int(args.rows)
    cols = int(args.cols)
    frame = frame.resize((rows, cols), resample=Image.NEAREST)
    pixels = frame.load()
    commands = [0]
    # frame.show()

    pxn = 0
    lpxn = 0
    for c in range(cols):
        for r in range(rows):
            px = pixels[r, c]
            if pxn == 0:
                commands.append(px) # double?
            lpxn += 1
            pxn += 1
            commands.append(px)
        if pxn >= MAX_PIXELS:
            pxn = 0
            yield {
                "on": True,
                "tt": 0,
                "bri": 255,
                "seg": {
                "frz": True,
                    "i": commands
                }
            }
            commands = [lpxn]

    yield {
        "on": True,
        "tt": 0,
        "bri": 255,
        "seg": {
            "frz": True,
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
def setup():
    global args
    parser = argparse.ArgumentParser(
                    prog = 'img2wled',
                    description = 'Convert any image to curl commands',
                    epilog = 'To be used to print images a WLED matrixes.')    

    parser.add_argument('filename', nargs="+")          
    parser.add_argument('-c', '--cols', help="Column count", default=16)
    parser.add_argument('-r', '--rows', help="Row count", default=16)      
    parser.add_argument('--ip', help="IP to send to.", default="wled.local")      
    parser.add_argument('--sleep', help="ms to sleep between images, if several given.", default="300")      
    parser.add_argument('--curl', help="Print curl commands, instead of directly executing the request", action="store_true", default=False)      
    args = parser.parse_args()

def main():
    setup()

    for img in args.filename:
        if not img:
            print("Required image file name")
            return
        # img = sys.argv[1]
        for segment in gen_str(img):
            if args.curl:
                print(
                    f"curl -X POST 'http://{args.ip}/json/state' -H 'Content-Type: application/json' -d '{json.dumps(segment)}'")
            else:
                requests.post(f"http://{args.ip}/json/śtate", data=json.dumps(segment), headers={"Content-Type": "application/json"})
        if len(args.filename) > 1:
            time.sleep(int(args.sleep) / 1000)


if __name__ == '__main__':
    main()
