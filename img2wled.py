#!/bin/python3

from dataclasses import dataclass
import json
import argparse
import requests

from PIL import Image, ImageSequence


MAX_PIXELS = 8*16
args = None


def gen_str_from_img(frame):
    frame = frame.convert("RGB")
    rows = int(args.rows)
    cols = int(args.cols)
    frame = frame.resize((rows, cols), resample=Image.NEAREST)
    lastpx = None
    pixels = frame.load()
    commands = [1]
    # frame.show()

    pxn = 0
    runl = 0
    lpxn = 0
    for c in range(cols):
        for r in range(rows):
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
def setup():
    global args
    parser = argparse.ArgumentParser(
                    prog = 'img2wled',
                    description = 'Convert any image to curl commands',
                    epilog = 'To be used to print images a WLED matrixes.')    

    parser.add_argument('filename', nargs=1)          
    parser.add_argument('-c', '--cols', help="Column count", default=16)
    parser.add_argument('-r', '--rows', help="Row count", default=16)      
    parser.add_argument('--ip', help="IP to send to.", default="wled.local")      
    parser.add_argument('--curl', help="Print curl commands, instead of directly executing the request", action="store_true", default=False)      
    args = parser.parse_args()

def main():
    setup()

    img = args.filename[0]
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


if __name__ == '__main__':
    main()
