"""Preview sheet and record for the plate studies (PLATES.md).

Reads output/<case>-plates/ (built by run.py --plates) and writes
output/plates-preview.jpg and output/plates-validation.json. Refuses dry runs
and failed checks: the sheet shows the delivered Blender build only.
"""
from pathlib import Path
import hashlib, json, os, re
import numpy as np
from PIL import Image, ImageDraw, ImageFont

R = Path(__file__).resolve().parent
CASE = os.environ.get('INFERNAL_CASE', 'recorded_route')
OUT = R / 'output' / (CASE + '-plates')
VIEWS = ('tower', 'barn', 'main')
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
        q = np.atleast_2d(np.asarray(P, float)) - self.eye; z = q @ self.fwd
        return np.column_stack([self.cx + self.f * (q @ self.right) / z, self.cy - self.f * (q @ self.up) / z])


def square(centre, half):
    """A square crop box about `centre`, moved (not cut) to stay on the page."""
    c = np.asarray(centre, float).ravel()
    lo = np.clip(c - half, 0, (W - 2 * half, H - 2 * half))
    return tuple(int(round(v)) for v in (*lo, *(lo + 2 * half)))


def main():
    checks = {v: json.loads((OUT / f'checks-{v}.json').read_text()) for v in VIEWS}
    for v, c in checks.items():
        if c['backend'] != 'blender': raise SystemExit('Refusing a dry run: preview the Blender build')
        if not c['all_passed']: raise SystemExit(f'Refusing: the {v} checks failed')
    scene = json.loads((OUT / 'scene.json').read_text())
    manifests = {v: json.loads((OUT / f'manifest-{v}.json').read_text()) for v in VIEWS}
    farm = json.loads((OUT / 'plates-farmstead.json').read_text())
    name = lambda v: f'Infernal_{CASE}_{v}'
    svgs = {v: (OUT / f'{name(v)}.svg').read_text() for v in VIEWS}
    record = dict(case=CASE, backend='blender', scene_sha256=sha(OUT / 'scene.json'),
                  svg_sha256={v: hashlib.sha256(t.encode()).hexdigest() for v, t in svgs.items()},
                  all_passed={v: c['all_passed'] for v, c in checks.items()},
                  checks={v: len(c['checks']) for v, c in checks.items()},
                  zones_mean_ink={v: {z: s['mean_ink'] for z, s in c['measured']['zones'].items()} for v, c in checks.items()},
                  layers={v: layers(t) for v, t in svgs.items()},
                  cameras={v: scene['cameras'][v] for v in VIEWS}, farmstead=farm,
                  face_patterns={v: manifests[v]['face_patterns'] for v in VIEWS},
                  flora={v: manifests[v]['plates']['flora'] for v in VIEWS},
                  terrain_domain={v: manifests[v]['plates']['terrain_domain'] for v in VIEWS})
    (R / 'output' / 'plates-validation.json').write_text(json.dumps(record, indent=2))

    im = {v: Image.open(OUT / f'{name(v)}.png').convert('RGB') for v in VIEWS}
    V = np.array(scene['vertices'])
    tower, barn = Camera(scene['cameras']['tower']), Camera(scene['cameras']['barn'])
    seal = manifests['tower']['face_patterns']['seal']
    seal_px = tower(seal['centre_world'])[0]
    seal_r = np.ptp(tower(np.array(seal['centre_world']) + np.array([[-seal['radius'], 0, 0], [seal['radius'], 0, 0]]))[:, 0])
    board = np.vstack([V[f] for f, n in zip(scene['faces'], scene['names']) if n.startswith('Barn quilt board')])
    board_px = barn(board); quilt_c = board_px.mean(0); quilt_half = .62 * np.ptp(board_px, axis=0).max()
    # Flora where the Poisson sample is densest: along the farmyard's fence,
    # and in the tower meadow against the approval tower's east wall.
    crops = [(im['tower'].crop(square(seal_px, 1.9 * seal_r)), 'Seal (lib/sdf2d) and strata, tower'),
             (im['barn'].crop(square(quilt_c, quilt_half)), 'Barn quilt painted with lib/fuzz'),
             (im['barn'].crop(square(barn([11.97, 3.67, .46])[0], 260)), 'Flora (lib/flora) at the farmyard fence'),
             (im['tower'].crop(square(tower([-2.34, 11.45, .67])[0], 260)), 'Tower meadow: flora, field marks, route')]
    font_path = R / 'vendor/fonts/IBMPlexMono-Regular.ttf'
    font = lambda size: ImageFont.truetype(str(font_path), size) if font_path.exists() else ImageFont.load_default(size=size)
    big = []
    for v in ('tower', 'barn'):
        t = im[v].copy(); t.thumbnail((1060, 795), Image.LANCZOS); big.append((t, v))
    tile = 380
    crops = [(c.resize((tile, int(tile * c.height / max(c.width, 1))), Image.LANCZOS), label) for c, label in crops]
    overview = im['main'].copy(); overview.thumbnail((tile * 1.33, tile), Image.LANCZOS)
    width = 20 + sum(t.width + 20 for t, _ in big)
    top = 70; row2 = top + max(t.height for t, _ in big) + 50
    height = row2 + max(c.height for c, _ in crops) + 110
    sheet = Image.new('RGB', (width, height), PAPER); d = ImageDraw.Draw(sheet)
    d.text((20, 20), f'Infernal Engine 0.2 / {CASE.replace("_", " ")} / plate studies: tower and farmstead cameras',
           fill=INK, font=font(26))
    x = 20
    for t, v in big:
        sheet.paste(t, (x, top))
        d.text((x, top + t.height + 10), f'{v} camera, 156 x 117 mm plate', fill=INK, font=font(17)); x += t.width + 20
    x = 20
    for c, label in crops + [(overview, 'main camera: where the farmstead stands')]:
        sheet.paste(c, (x, row2)); d.text((x, row2 + c.height + 8), label, fill=INK, font=font(15)); x += c.width + 20
    paths = {v: sum(l['paths'] for l in record['layers'][v].values()) for v in VIEWS}
    d.text((20, height - 36), f'Detail crops at the 3120 px master (20 px/mm). Checks: {record["checks"]["tower"]} tower, '
           f'{record["checks"]["barn"]} barn, {record["checks"]["main"]} main, all passed. Paths: {paths["tower"]:,} tower, '
           f'{paths["barn"]:,} barn. Flora instances: {record["flora"]["barn"]["instances"]}.', fill=INK, font=font(16))
    sheet.save(R / 'output' / 'plates-preview.jpg', quality=88)
    print(json.dumps(dict(preview=str(R / 'output' / 'plates-preview.jpg'), size=sheet.size, paths=paths), indent=1))


if __name__ == '__main__':
    main()
