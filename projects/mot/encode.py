"""Validate all 480 frames and encode a 20-second, 24 fps MP4 using FFmpeg."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

PROJECT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT.parents[1]))
from projects.mot.frames import valid_png


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--frames', type=Path, default=PROJECT / 'output/frames')
    parser.add_argument('--output', type=Path, default=PROJECT / 'output/mot-24fps.mp4')
    args = parser.parse_args()
    directory = args.frames.resolve()
    settings = json.loads((directory / 'settings.json').read_text())
    width, height = settings['resolution']
    if settings['fps'] != 24 or settings['frames'] != 480:
        parser.error('Expected 480 frames at 24 fps')
    missing = [frame for frame in range(1, 481)
               if not valid_png(directory / f'frame-{frame:04d}.png', width, height)]
    if missing:
        parser.error(f'{len(missing)} missing or invalid frames; first: {missing[:10]}')
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        parser.error(f'Output already exists: {output}; choose another --output')
    subprocess.run([
        'ffmpeg', '-hide_banner', '-loglevel', 'error', '-n', '-framerate', '24',
        '-start_number', '1', '-i', str(directory / 'frame-%04d.png'), '-frames:v', '480',
        '-vf', 'scale=out_color_matrix=bt709', '-c:v', 'libx264', '-crf', '17',
        '-preset', 'medium', '-pix_fmt', 'yuv420p', '-colorspace', 'bt709',
        '-color_primaries', 'bt709', '-color_trc', 'bt709', '-movflags', '+faststart', str(output),
    ], check=True)
    probe = subprocess.run([
        'ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
        'stream=width,height,nb_frames,r_frame_rate:format=duration', '-of', 'json', str(output),
    ], capture_output=True, text=True, check=True)
    result = json.loads(probe.stdout)
    video = result['streams'][0]
    if ((video['width'], video['height']) != (width, height)
            or video['r_frame_rate'] != '24/1' or video['nb_frames'] != '480'
            or abs(float(result['format']['duration']) - 20) >= 0.01):
        raise RuntimeError(f'Encoded video failed validation: {result}')
    output.with_suffix('.validation.json').write_text(json.dumps(result, indent=2) + '\n')
    print(f'PASS: {output} — {width}x{height}, 480 frames, 24 fps, 20 seconds')


if __name__ == '__main__':
    main()
