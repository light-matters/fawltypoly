"""Run in Blender: render the committed scene as restartable Cycles frames."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

PROJECT = Path(__file__).resolve().parent
ROOT = PROJECT.parents[1]


def configure_device(bpy, requested):
    preferences = bpy.context.preferences.addons['cycles'].preferences
    backends = ['OPTIX', 'CUDA', 'HIP', 'ONEAPI'] if requested == 'auto' else [requested]
    for backend in backends:
        if backend == 'CPU':
            break
        try:
            preferences.compute_device_type = backend
            preferences.refresh_devices()
            devices = [d for d in preferences.devices if d.type == backend]
            if devices:
                for device in preferences.devices:
                    device.use = device.type == backend
                bpy.context.scene.cycles.device = 'GPU'
                return backend
        except (TypeError, RuntimeError):
            continue
    if requested not in ('auto', 'CPU'):
        raise SystemExit(f'No usable {requested} device found; choose --device CPU or auto')
    bpy.context.scene.cycles.device = 'CPU'
    return 'CPU'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=PROJECT / 'output/frames')
    parser.add_argument('--samples', type=int, default=128)
    parser.add_argument('--width', type=int, default=1280)
    parser.add_argument('--device', choices=('auto', 'CPU', 'OPTIX', 'CUDA', 'HIP', 'ONEAPI'), default='auto')
    parser.add_argument('--start', type=int, default=1)
    parser.add_argument('--end', type=int, default=480)
    parser.add_argument('--dry-run', action='store_true')
    arguments = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    args = parser.parse_args(arguments)
    if args.samples < 1 or args.width < 32 or args.width % 32 or not 1 <= args.start <= args.end <= 480:
        parser.error('Use positive samples, width divisible by 32, and frames within 1..480')
    import bpy
    sys.path.insert(0, str(ROOT))
    from projects.mot.frames import valid_png

    scene = bpy.context.scene
    if not bpy.data.filepath or scene.frame_end != 480:
        parser.error('Open the MOT .blend with its full 480-frame timeline first')
    directory = args.output.resolve()
    width, height = args.width, args.width * 9 // 16
    settings = {'engine': 'CYCLES', 'resolution': [width, height], 'fps': 24,
                'frames': 480, 'samples_max': args.samples, 'adaptive_threshold': 0.02,
                'adaptive_min_samples': min(16, args.samples), 'denoising': True,
                'scene_sha256': hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest()}
    manifest = directory / 'settings.json'
    if manifest.exists() and json.loads(manifest.read_text()) != settings:
        parser.error('Render settings or scene changed; use a different --output directory')
    scene.render.engine = 'CYCLES'
    device = configure_device(bpy, args.device)
    scene.cycles.samples = args.samples
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_min_samples = settings['adaptive_min_samples']
    scene.cycles.adaptive_threshold = 0.02
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = width, height
    scene.render.resolution_percentage = 100
    scene.render.fps, scene.render.fps_base = 24, 1
    scene.frame_start, scene.frame_end, scene.frame_step = 1, 480, 1
    scene.render.use_persistent_data = True
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.image_settings.color_depth = '8'
    scene.render.image_settings.compression = 15
    print(f'MOT: {width}x{height}, 24 fps, {args.samples} samples, device {device}', flush=True)
    if args.dry_run:
        return
    directory.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(settings, indent=2) + '\n')
    for frame in range(args.start, args.end + 1):
        output = directory / f'frame-{frame:04d}.png'
        if valid_png(output, width, height):
            print(f'MOT_SKIP {frame}', flush=True)
            continue
        started = time.monotonic()
        scene.frame_set(frame)
        partial = output.with_name(output.stem + '.partial.png')
        scene.render.filepath = str(partial)
        bpy.ops.render.render(write_still=True)
        partial.replace(output)
        print(f'MOT_FRAME {frame} {time.monotonic() - started:.2f}s', flush=True)


if __name__ == '__main__':
    main()
