"""Extract timestamped reference frames without changing the source video.

Run: uv run python tools/prepare_video.py INPUT --output OUTPUT --times 0.5,2,4
HLG previews use an explicit approximate SDR transform, not calibrated albedo.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image, ImageDraw


def probe(path):
    data = json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)
    ]))
    return next(s for s in data['streams'] if s['codec_type'] == 'video'), data


def extract(path, time, stream, max_height):
    # ffmpeg applies the container display matrix before scaling.
    raw = subprocess.check_output([
        'ffmpeg', '-v', 'error', '-ss', str(time), '-i', str(path), '-map', '0:v:0',
        '-frames:v', '1', '-vf', f'scale=-2:{max_height}', '-pix_fmt', 'rgb48le',
        '-f', 'image2pipe', '-vcodec', 'ppm', '-threads', '1', '-'
    ])
    # PPM keeps 16-bit samples and embeds the post-rotation dimensions.
    import io
    header = io.BytesIO(raw)
    assert header.readline().strip() == b'P6'
    dims = header.readline()
    while dims.startswith(b'#'):
        dims = header.readline()
    width, height = map(int, dims.split())
    maximum = int(header.readline())
    rgb = np.frombuffer(header.read(), dtype='>u2' if maximum > 255 else 'u1')
    rgb = rgb.reshape(height, width, 3).astype(np.float32) / maximum
    if stream.get('color_transfer') == 'arib-std-b67':
        # Invert HLG OETF, approximate its display OOTF, convert BT.2020 to BT.709.
        a, b, c = 0.17883277, 0.28466892, 0.55991073
        linear = np.where(rgb <= .5, rgb * rgb / 3, (np.exp((rgb-c)/a)+b)/12)
        luminance = np.maximum(linear @ np.array([.2627, .6780, .0593]), 1e-8)
        linear *= luminance[..., None] ** .2
        linear = linear @ np.array([
            [1.660491, -.587641, -.072850],
            [-.124550, 1.132900, -.008350],
            [-.018151, -.100579, 1.118730]
        ], dtype=np.float32).T
        # Fixed exposure and filmic shoulder for comparable reference previews.
        x = np.maximum(linear * 4, 0)
        rgb = np.clip((x*(2.51*x+.03))/(x*(2.43*x+.59)+.14), 0, 1)
        rgb = np.where(rgb <= .0031308, rgb*12.92, 1.055*rgb**(1/2.4)-.055)
    return Image.fromarray(np.uint8(np.clip(rgb, 0, 1)*255))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--times', default='0.5,1.5,2.5,3.5,4.5,5.5,6.5,7.5,8.5,9.5,10.5,11.2')
    parser.add_argument('--height', type=int, default=1440)
    args = parser.parse_args()
    stream, data = probe(args.input)
    args.output.mkdir(parents=True, exist_ok=True)
    records = []
    thumbs = []
    for time in map(float, args.times.split(',')):
        if not 0 <= time < float(stream['duration']):
            raise ValueError(f'Timestamp outside video: {time}')
        img = extract(args.input, time, stream, args.height)
        name = f'frame-{time:06.2f}s.png'
        img.save(args.output / name)
        gray = np.asarray(img.convert('L'), dtype=np.float32)
        edge = gray[1:-1, :-2]+gray[1:-1, 2:]+gray[:-2, 1:-1]+gray[2:, 1:-1]-4*gray[1:-1, 1:-1]
        records.append({'seconds': time, 'file': name, 'size': img.size,
                        'laplacian_variance': round(float(edge.var()), 3)})
        img.thumbnail((240, 400))
        thumb = Image.new('RGB', (260, 432), '#20252b')
        thumb.paste(img, ((260-img.width)//2, 24))
        ImageDraw.Draw(thumb).text((12, 8), f'{time:.2f}s', fill='white')
        thumbs.append(thumb)
    sheet = Image.new('RGB', (260*4, 432*((len(thumbs)+3)//4)), '#20252b')
    for i, img in enumerate(thumbs):
        sheet.paste(img, (i%4*260, i//4*432))
    sheet.save(args.output / 'contact-sheet.jpg', quality=90)
    # Do not copy location tags into the shareable report.
    with args.input.open('rb') as source:
        source_sha256 = hashlib.file_digest(source, 'sha256').hexdigest()
    is_hlg = stream.get('color_transfer') == 'arib-std-b67'
    report = {'source_name': args.input.name, 'source_sha256': source_sha256,
              'duration': stream['duration'], 'codec': stream['codec_name'],
              'color_transfer': stream.get('color_transfer'), 'color_primaries': stream.get('color_primaries'),
              'preview_transform': ('approximate HLG -> BT.709 filmic SDR; not calibrated albedo'
                                    if is_hlg else 'decoded RGB preview; no dedicated transfer or gamut mapping'),
              'frames': records}
    (args.output / 'manifest.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
