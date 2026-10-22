"""Compare a plate with and without face patterns: preview sheet and record.

Reads output/<case>/ and output/<case>-face-patterns/ (both built by run.py,
the second with --face-patterns) and writes output/face-patterns-preview.jpg
and output/face-patterns-validation.json. Refuses failed checks, dry runs and
mismatched scene records: the two plates must differ only in the engraving.
"""
from pathlib import Path
import hashlib, json, os, re
import numpy as np
from PIL import Image, ImageDraw, ImageFont

R = Path(__file__).resolve().parent
CASE = os.environ.get('INFERNAL_CASE', 'recorded_route'); VIEW = os.environ.get('TERRAIN_VIEW', 'main')
DIRS = dict(current=R / 'output' / CASE, patterns=R / 'output' / (CASE + '-face-patterns'))
PX_PER_MM, W, H = 20, 3120, 2340
INK, PAPER = '#242820', '#ede6d4'


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def layers(svg_text):
    out = {}
    for chunk in re.split(r'(?=<g inkscape:groupmode="layer")', svg_text)[1:]:
        label = re.search(r'inkscape:label="([^"]+)"', chunk).group(1); length = 0.; n = 0
        for d in re.findall(r' d="([^"]+)"', chunk):
            p = np.array([[float(v) for v in xy.split(',')] for xy in re.findall(r'[-\d.]+,[-\d.]+', d)])
            length += np.linalg.norm(np.diff(p, axis=0), axis=1).sum(); n += 1
        out[label] = dict(paths=n, pen_down_m=round(length / PX_PER_MM / 1000, 3))
    return out


class Camera:
    def __init__(self, cam):
        self.eye = np.array(cam['eye']); t = np.array(cam['target'])
        self.fwd = (t - self.eye) / np.linalg.norm(t - self.eye)
        r = np.cross(self.fwd, [0, 0, 1]); self.right = r / np.linalg.norm(r); self.up = np.cross(self.right, self.fwd)
        self.f = cam['focal_px']; self.cx, self.cy = cam['principal_point']

    def __call__(self, P):
        q = np.asarray(P, float) - self.eye; z = q @ self.fwd
        return np.column_stack([self.cx + self.f * (q @ self.right) / z, self.cy - self.f * (q @ self.up) / z])


def main():
    checks = {k: json.loads((d / f'checks-{VIEW}.json').read_text()) for k, d in DIRS.items()}
    for k, c in checks.items():
        if not c['all_passed']: raise SystemExit(f'Refusing: {k} checks failed')
        if c['backend'] != 'blender': raise SystemExit('Refusing a dry run: compare Blender builds')
    if sha(DIRS['current'] / 'scene.json') != sha(DIRS['patterns'] / 'scene.json'):
        raise SystemExit('Refusing: the two plates were built from different scene records')
    scene = json.loads((DIRS['current'] / 'scene.json').read_text()); cam = Camera(scene['cameras'][VIEW])
    record = json.loads((DIRS['patterns'] / f'manifest-{VIEW}.json').read_text())['face_patterns']
    V = np.array(scene['vertices']); N = np.array(scene['normals']); mats = scene['materials']
    name = f'Infernal_{CASE}_{VIEW}'
    plates = {k: np.asarray(Image.open(d / f'{name}.png').convert('RGB')) for k, d in DIRS.items()}

    def mask(pred):
        m = Image.new('L', (W, H), 0); dr = ImageDraw.Draw(m)
        for i, (face, n) in enumerate(zip(scene['faces'], scene['names'])):
            if pred(i, n): dr.polygon([tuple(p) for p in cam(V[face])], fill=255)
        return np.asarray(m) > 0
    tower, staff = record['strata']['node'], record['quilt']['node']
    c = np.array(record['quilt']['centre_world']); s = record['quilt']['size_world'] / 2
    quilt_px = cam([c + (-s, 0, -s), c + (s, 0, -s), c + (s, 0, s), c + (-s, 0, s)])
    qm = Image.new('L', (W, H), 0); ImageDraw.Draw(qm).polygon([tuple(p) for p in quilt_px], fill=255)
    regions = {'strata walls, lit': mask(lambda i, n: n.startswith(tower + ' | duration bays') and mats[i] == 1 and np.allclose(N[i], (0, -1, 0))),
               'strata walls, shaded': mask(lambda i, n: n.startswith(tower + ' | duration bays') and mats[i] == 1 and np.allclose(N[i], (1, 0, 0))),
               'quilt square': np.asarray(qm) > 0}
    coverage = {}
    for k, im in plates.items():
        grey = np.asarray(Image.fromarray(im).convert('L'), float); paper = np.median(grey[:200, :200])
        ink = np.clip((paper - grey) / (paper - 36), 0, 1)   # 36: the black ink's grey value
        coverage[k] = {r: round(float(ink[m].mean()), 3) for r, m in regions.items()}
    svgs = {k: (d / f'{name}.svg').read_text() for k, d in DIRS.items()}
    result = dict(case=CASE, view=VIEW, backend='blender', scene_sha256=sha(DIRS['current'] / 'scene.json'),
                  svg_sha256={k: hashlib.sha256(t.encode()).hexdigest() for k, t in svgs.items()},
                  all_passed={k: c['all_passed'] for k, c in checks.items()},
                  zones_mean_ink={k: {z: v['mean_ink'] for z, v in c['measured']['zones'].items()} for k, c in checks.items()},
                  layers={k: layers(t) for k, t in svgs.items()}, coverage=coverage,
                  region_px={r: int(m.sum()) for r, m in regions.items()}, face_patterns=record)
    (R / 'output' / 'face-patterns-validation.json').write_text(json.dumps(result, indent=2))

    def box(pred, pad):
        pts = np.vstack([cam(V[f]) for i, (f, n) in enumerate(zip(scene['faces'], scene['names'])) if pred(i, n)])
        lo, hi = pts.min(0) - pad, pts.max(0) + pad
        return tuple(int(v) for v in (*np.maximum(lo, 0), *np.minimum(hi, (W, H))))
    tb = box(lambda i, n: n.startswith(tower + ' | duration bays') or n.startswith(tower + ' roof'), 18)
    sb = box(lambda i, n: n.startswith(staff + ' | duration bays') or n.startswith(staff + ' roof'), 18)
    qc = quilt_px.mean(0); half = .75 * np.ptp(quilt_px, axis=0).max()
    qb = tuple(int(v) for v in (qc[0] - half, qc[1] - half, qc[0] + half, qc[1] + half))
    font_path = R / 'vendor/fonts/IBMPlexMono-Regular.ttf'
    font = lambda size: ImageFont.truetype(str(font_path), size) if font_path.exists() else ImageFont.load_default(size=size)
    crop = lambda k, b, z=1.: Image.fromarray(plates[k]).crop(b).resize((int((b[2] - b[0]) * z), int((b[3] - b[1]) * z)), Image.LANCZOS)
    tiles = [(crop(k, tb), f'{"Current" if k == "current" else "Face patterns"}: strata, {tower}') for k in DIRS] + \
            [(crop(k, sb), f'{"Current" if k == "current" else "Face patterns"}: quilt, {staff}') for k in DIRS]
    zoom = 380 / (qb[2] - qb[0])
    quilts = [(crop(k, qb, zoom), f'{"Current" if k == "current" else "Face patterns"}, x{zoom:.1f}') for k in DIRS]
    full = Image.fromarray(plates['patterns']); full.thumbnail((820, 615))
    top_h = max(t.height for t, _ in tiles); width = sum(t.width for t, _ in tiles) + 20 * (len(tiles) + 1)
    sheet = Image.new('RGB', (max(width, 1640), 70 + top_h + 60 + max(full.height, 380) + 90), PAPER); d = ImageDraw.Draw(sheet)
    d.text((20, 18), f'Infernal Engine 0.2 / {CASE.replace("_", " ")}, {VIEW} camera / 2D generators on flat walls', fill=INK, font=font(24))
    x = 20
    for t, label in tiles:
        sheet.paste(t, (x, 70)); d.text((x, 70 + top_h + 8), label, fill=INK, font=font(16)); x += t.width + 20
    y = 70 + top_h + 60; x = 20
    for t, label in quilts:
        sheet.paste(t, (x, y)); d.text((x, y + t.height + 8), label, fill=INK, font=font(16)); x += t.width + 20
    sheet.paste(full, (x + 20, y)); d.text((x + 20, y + full.height + 8), 'Face patterns, whole plate (156 x 117 mm)', fill=INK, font=font(16))
    cov = coverage
    d.text((20, sheet.height - 34), f'Crops at the 3120 px master (20 px/mm). Ink on the strata walls {cov["current"]["strata walls, lit"]:.2f} -> '
           f'{cov["patterns"]["strata walls, lit"]:.2f} (lit), {cov["current"]["strata walls, shaded"]:.2f} -> {cov["patterns"]["strata walls, shaded"]:.2f} (shade).',
           fill=INK, font=font(16))
    sheet.save(R / 'output' / 'face-patterns-preview.jpg', quality=90)
    print(json.dumps(dict(preview=str(R / 'output' / 'face-patterns-preview.jpg'), size=sheet.size, coverage=coverage), indent=1))


if __name__ == '__main__':
    main()
