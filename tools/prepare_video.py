"""Extract timestamped reference frames without changing the source video.

Run: uv run python tools/prepare_video.py INPUT --output OUTPUT --times 0.5,2,4
HLG previews use an explicit approximate SDR transform, not calibrated albedo.
"""
import argparse
import hashlib
import json
import math
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
    if not raw:
        raise ValueError(f'No decoded frame at {time:.3f}s; choose an earlier timestamp')
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
    parser.add_argument('--times', help='Explicit seconds, separated by commas; otherwise sample the clip evenly')
    parser.add_argument('--count', type=int, default=12, help='Automatic overview sample count')
    parser.add_argument('--height', type=int, default=480, help='Working image height; use 1440 or native detail only for selected views')
    args = parser.parse_args()
    if args.height < 64 or args.count < 1:
        parser.error('height must be at least 64 and count must be positive')
    stream, data = probe(args.input)
    duration = float(stream.get('duration') or data['format']['duration'])
    if not math.isfinite(duration) or duration <= 0:
        parser.error('Video duration must be finite and positive')
    try:
        if args.times is not None:
            times = [float(t) for t in args.times.split(',')]
        else:
            count = min(args.count, max(1, int(duration*100)))
            if stream.get('nb_frames', '').isdigit():
                count = min(count, max(1, int(stream['nb_frames'])))
            times = [i*duration/count for i in range(count)]
        if any(not math.isfinite(t) or not 0 <= t < duration for t in times):
            raise ValueError('Every timestamp must be finite and inside the video duration')
        names = [f'frame-{t:06.2f}s.png' for t in times]
        if len(names) != len(set(names)):
            raise ValueError('Timestamps must have distinct filenames at 0.01 second precision')
    except ValueError as error:
        parser.error(str(error))
    args.output.mkdir(parents=True, exist_ok=True)
    records = []
    thumbs = []
    for time in times:
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
              'duration': duration, 'codec': stream['codec_name'],
              'sampling': 'explicit' if args.times is not None else 'uniform',
              'requested_height': args.height,
              'color_transfer': stream.get('color_transfer'), 'color_primaries': stream.get('color_primaries'),
              'preview_transform': ('approximate HLG -> BT.709 filmic SDR; not calibrated albedo'
                                    if is_hlg else 'decoded RGB preview; no dedicated transfer or gamut mapping'),
              'frames': records}
    (args.output / 'manifest.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
