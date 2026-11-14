"""Compare manually selected subject crops, without claiming solved camera alignment."""
import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--reference', type=Path, required=True)
parser.add_argument('--render', type=Path, required=True)
parser.add_argument('--reference-crop', help='left,top,right,bottom in input pixels')
parser.add_argument('--render-crop', help='left,top,right,bottom in input pixels')
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()


def panel(path, crop):
    im = Image.open(path).convert('RGB')
    if crop:
        box = tuple(map(int, crop.split(',')))
        if len(box) != 4 or not (0 <= box[0] < box[2] <= im.width and 0 <= box[1] < box[3] <= im.height):
            raise ValueError(f'Invalid crop for {path}: {box}')
        im = im.crop(box)
    return ImageOps.contain(im, (480, 960), Image.Resampling.LANCZOS)


images = [panel(args.reference, args.reference_crop), panel(args.render, args.render_crop)]
canvas = Image.new('RGB', (1040, 1040), '#20252b')
draw = ImageDraw.Draw(canvas)
for i, (im, title) in enumerate(zip(images, ['VIDEO REFERENCE', 'BLENDER v001'])):
    x = 20+i*520
    draw.text((x, 15), title, fill='white')
    canvas.paste(im, (x+(480-im.width)//2, 50+(960-im.height)//2))
draw.text((20, 1020), 'Manual crop comparison. Estimated scale / camera. Different lighting; no pixel-error claim.', fill='#b7c0ca')
args.output.parent.mkdir(parents=True, exist_ok=True)
canvas.save(args.output)
print(args.output)
