"""The two CC scans: loading, orientation, framing and light.

Every scan is brought into one frame: z up, the sitter facing -y, the whole
scan one unit tall with its base at z = 0. Cameras and lights are then given
as azimuth/elevation about a point on the head, so a preset reads the same way
for either sitter.

Washington (CC0) is welded and Loop-subdivided once, which steadies the
curvature the crease lines are read from. Lee Perry-Smith (CC BY 3.0) has
17,684 triangles, so it is Loop-subdivided twice before drawing; his colour map supplies local tone (eyebrows, stubble, lips),
since a scan of living skin, unlike marble, is not one colour.
"""
from dataclasses import dataclass, field
import gzip
import hashlib
import io
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image

import subdivide

ROOT = Path(__file__).resolve().parent
MODELS = ROOT / 'models'


@dataclass
class Scan:
    key: str
    V: np.ndarray                 # welded positions, canonical frame
    F: np.ndarray                 # triangles into V
    raw_records: int              # vertex records in the source file
    source_triangles: int
    Fu: np.ndarray = None         # the same triangles into UV (seam-split records)
    UV: np.ndarray = None
    albedo: np.ndarray = None     # relative albedo image, skin median = 1
    subdivisions: int = 0


@dataclass
class Subject:
    key: str
    title: str
    credit: str
    licence: str
    files: dict                   # file -> sha256 of the committed copy
    upstream: dict                # where each file came from, pinned
    head: tuple                   # look-at point on the head, canonical frame
    head_height: float            # crown to chin, scene units (sets the plate scale)
    views: dict = field(default_factory=dict)
    light: dict = field(default_factory=dict)
    subdivide: int = 0
    albedo: str = None
    tone: dict = field(default_factory=dict)
    fade: dict = field(default_factory=dict)
    ground: dict = field(default_factory=dict)


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _weld(v, f):
    """Merge vertex records that share an exact position; geometry is unchanged."""
    _, first, inverse = np.unique(v, axis=0, return_index=True, return_inverse=True)
    return v[first].copy(), inverse.reshape(-1)[f]


def _normalise(v, rotation):
    """Rotate into the canonical frame, then scale to unit height, base at z = 0."""
    v = v @ np.asarray(rotation, float).T
    lo, hi = v.min(0), v.max(0)
    v = (v - [(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]]) / (hi[2] - lo[2])
    return v


# Washington: OBJ is z up with the sitter facing +y; a half turn about z faces him to -y.
WASHINGTON_ROTATION = [[-1, 0, 0], [0, -1, 0], [0, 0, 1]]
# Lee Perry-Smith: glTF is y up facing +z; a quarter turn about x gives z up facing -y.
LPS_ROTATION = [[1, 0, 0], [0, 0, -1], [0, 1, 0]]


def load_washington(levels=0):
    path = MODELS / 'washington-bust' / 'washington_bust.obj.gz'
    with gzip.open(path, 'rb') as fh:
        data = fh.read()
    mesh = trimesh.load(file_obj=io.BytesIO(data), file_type='obj', process=False, maintain_order=True)
    raw = np.asarray(mesh.vertices, float)
    faces = np.asarray(mesh.faces)
    V, F = _weld(raw, faces)
    V = _normalise(V, WASHINGTON_ROTATION)
    if levels:
        V, F, _, _ = subdivide.loop(V, F, levels)
    return Scan('washington', V, F, len(raw), len(faces), subdivisions=levels)


def load_lps(levels=2):
    path = MODELS / 'lee-perry-smith' / 'LeePerrySmith.glb'
    mesh = trimesh.load(path, process=False)
    mesh = mesh.to_geometry() if hasattr(mesh, 'to_geometry') else mesh
    raw = np.asarray(mesh.vertices, float)
    Fu = np.asarray(mesh.faces)
    UV = np.asarray(mesh.visual.uv, float)
    V, F = _weld(raw, Fu)
    V = _normalise(V, LPS_ROTATION)
    if levels:
        V, F, Fu, UV = subdivide.loop(V, F, levels, Fu, UV)
    albedo = relative_albedo(MODELS / 'lee-perry-smith' / 'Map-COL.jpg', UV[Fu].reshape(-1, 2))
    return Scan('lps', V, F, len(raw), len(mesh.faces), Fu, UV, albedo, levels)


def relative_albedo(path, used_uv):
    """Linear luminance of an sRGB colour map, divided by its median over the
    texels the mesh actually uses, so typical skin reads 1.0 and darker local
    colour (brows, stubble, lips) reads below it."""
    rgb = np.asarray(Image.open(path).convert('RGB'), float) / 255
    lin = np.where(rgb <= .04045, rgb / 12.92, ((rgb + .055) / 1.055) ** 2.4)
    lum = lin @ [.2126, .7152, .0722]
    h, w = lum.shape
    px = np.clip((used_uv[:, 0] * w).astype(int), 0, w - 1)
    py = np.clip((used_uv[:, 1] * h).astype(int), 0, h - 1)
    return lum / np.median(lum[py, px])


def sample_albedo(img, uv):
    """Bilinear lookup; v runs down the image, as the glTF stores it."""
    h, w = img.shape
    x = np.clip(uv[:, 0] * w - .5, 0, w - 1.001); y = np.clip(uv[:, 1] * h - .5, 0, h - 1.001)
    x0 = x.astype(int); y0 = y.astype(int); fx = x - x0; fy = y - y0
    return (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x0 + 1] * fx * (1 - fy)
            + img[y0 + 1, x0] * (1 - fx) * fy + img[y0 + 1, x0 + 1] * fx * fy)


SUBJECTS = {
    'washington': Subject(
        key='washington',
        title='George Washington, after Ceracchi',
        credit=('Bust of George Washington, marble, ca. 1819, after Giuseppe Ceracchi (1792). '
                'Smithsonian National Portrait Gallery, NPG.70.4. 3D scan released by the Smithsonian under CC0.'),
        licence='CC0-1.0',
        files={'washington_bust.obj.gz': None, 'LICENSE': None},
        upstream={
            'washington_bust.obj': dict(
                url='https://github.com/pyvista/data/raw/5a3de12d34c24aa5dd5e5db1cbc2defebc0d4da3/Data/washington_bust/washington_bust.obj',
                sha256='b97b76991d612158ee1945a74cb9dd86c0d65e001c7912d862041f36b0850893',
                note='stored gzip-compressed (gzip -9 -n); decompresses to these bytes'),
            'LICENSE': dict(
                url='https://github.com/pyvista/data/raw/5a3de12d34c24aa5dd5e5db1cbc2defebc0d4da3/Data/washington_bust/LICENSE',
                sha256='470cd25f1f1620d1733c9870f96aa058292b557148a5e93cbe8b4df22f5b76d3'),
            'smithsonian': 'https://3d.si.edu/',
        },
        head=(-.03, .01, .80),
        head_height=.40,
        subdivide=1,
    ),
    'lps': Subject(
        key='lps',
        title='Lee Perry-Smith',
        credit=('Infinite, 3D Head Scan by Lee Perry-Smith (Infinite-Realities), licensed under CC BY 3.0 '
                '(https://creativecommons.org/licenses/by/3.0/), as distributed with three.js r150. '
                'Changed: Loop-subdivided twice and drawn as a line engraving.'),
        licence='CC-BY-3.0',
        files={'LeePerrySmith.glb': None, 'Map-COL.jpg': None, 'LeePerrySmith_License.txt': None},
        upstream={
            name: dict(url=f'https://github.com/mrdoob/three.js/raw/a2e9b10cb814d441202c8e5e5c3c4975e37e59a3/examples/models/gltf/LeePerrySmith/{name}',
                       sha256=sha)
            for name, sha in (('LeePerrySmith.glb', '402b8a8ac9f03232e6d64b5962929703a069daf99d3c49ac8eb0e48bedc9c576'),
                              ('Map-COL.jpg', 'e976d73b31407f8d0967412bf468019ed26a5d5a32cf5811aabff7e816458a65'),
                              ('LeePerrySmith_License.txt', '7cf4da43a6ae6d32f7f7d063fe129a19468af6f4fe7c53b937f83959709fcb50'))
        },
        head=(-.01, -.10, .74),
        head_height=.46,
        subdivide=2,
        albedo='Map-COL.jpg',
    ),
}

# Tone: darkness d = 1 - light^light_gamma, remapped so that d below `paper` stays bare;
# ink coverage = scale * d^gamma, with cross-hatching taking `cross` of it once d passes cross_from. Scanned Statue v2 used
# 1 - sqrt(light), .68 and 1.3, which leaves a lit face almost bare at portrait scale.
TONE = dict(light_gamma=1., paper=.06, gamma=1.25, scale=.85, cross=.34, cross_from=.45, cross_ramp=.30,
            cross_min_deg=30., cross_full_deg=50.,
            smooth_samples=1.5, albedo_gamma=1.0, fold_threshold=5., fold_min_pens=6,
            valley_threshold=20., ridge_threshold=70., crease_min_pens=12, crease_smooth=1,
            crease_strong=2.5, crease_light=.55)

# A rig is given about the subject's frame: azimuth 0 is in front, positive toward +x
# (the viewer's right when facing the sitter), elevation up from the horizontal.
STUDIO = dict(key_azimuth=-50., key_elevation=38., key_distance=3., key_size=1.2, key_samples=7,
              fill_azimuth=25., fill_elevation=8., ao_samples=40, ao_radius=.06,
              ambient=.12, key=.80, fill=.18, occlusion=.85)

SUBJECTS['washington'].light = dict(STUDIO)
SUBJECTS['washington'].tone = {}
# Views. Washington's head is turned to his right (toward -x): azimuth -35 sees the face full on,
# 15 a strong three-quarter, 62 the profile.
SUBJECTS['washington'].views = {
    'bust': dict(azimuth=15., elevation=6., distance=3.6, head_mm=100., center=(.5, .30),
                 fade=dict(dx=0., dy=.50, rx=1.30, ry=1.37, soft=.45, below_only=True),
                 ground=dict(dy=.35, rx=.95, ry=1.05)),
    'head': dict(azimuth=15., elevation=6., distance=3.2, head_mm=140., center=(.5, .34)),
    'front': dict(azimuth=-35., elevation=5., distance=3.2, head_mm=140., center=(.5, .34),
                  key_azimuth=-85., fill_azimuth=-10.),
    'profile': dict(azimuth=62., elevation=4., distance=3.2, head_mm=140., center=(.5, .34),
                    key_azimuth=-10., fill_azimuth=80.),
}
SUBJECTS['washington'].fade = dict(dx=0., dy=.10, rx=.62, ry=.78, soft=.30)
SUBJECTS['washington'].ground = dict(kind='oval', dx=0., dy=.04, rx=.62, ry=.74, soft=.22, halo_mm=2.5,
                                     halo_soft_mm=3., tone=.26, gradient=.30, dark_side='auto', spacing_pens=1.75,
                                     angle=0., res=.25, min_mm=1.5)

SUBJECTS['lps'].light = dict(STUDIO)
SUBJECTS['lps'].tone = {}
SUBJECTS['lps'].views = {
    'head': dict(azimuth=-30., elevation=5., distance=3., head_mm=122., center=(.5, .40),
                 key_azimuth=40., fill_azimuth=-45.),
    'bust': dict(azimuth=-30., elevation=5., distance=3.4, head_mm=92., center=(.5, .33),
                 key_azimuth=40., fill_azimuth=-45., offset=(0., .03, -.06),
                 fade=dict(dx=0., dy=.62, rx=1.45, ry=1.25, soft=.45, below_only=True),
                 ground=dict(dy=.30, rx=1.0, ry=1.05)),
    'front': dict(azimuth=0., elevation=4., distance=3., head_mm=122., center=(.5, .40)),
}
SUBJECTS['lps'].fade = dict(dx=0., dy=.10, rx=.62, ry=.78, soft=.30)
SUBJECTS['lps'].ground = dict(SUBJECTS['washington'].ground)

LOADERS = {'washington': load_washington, 'lps': load_lps}


def load(key, levels=None):
    s = SUBJECTS[key]
    return LOADERS[key](s.subdivide if levels is None else levels)


def verify(key):
    """sha256 of each committed model file against the pinned upstream copy."""
    s = SUBJECTS[key]; folder = MODELS / ('washington-bust' if key == 'washington' else 'lee-perry-smith')
    out = {}
    for name, up in s.upstream.items():
        if not isinstance(up, dict):
            continue
        path = folder / name
        if not path.exists():
            path = folder / (name + '.gz')
            data = gzip.decompress(path.read_bytes())
        else:
            data = path.read_bytes()
        out[name] = hashlib.sha256(data).hexdigest() == up['sha256']
    return out
