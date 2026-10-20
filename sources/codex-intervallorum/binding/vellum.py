"""Content-aware, deterministic paper finishing for reading PDFs.

    python binding/vellum.py INPUT.pdf OUTPUT.pdf [--seed 17] [--profile light|full]

Low-frequency mottling, fine grain and short fibres are carried by a transparent
image. Rendered ink strokes and source images have zero opacity. Rare ink spots
are also kept clear of complete text spans and restricted to empty outer margins.
No source page is flattened. The illustrated binder runs this after pen finishing.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
from pathlib import Path

import fitz
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

VERSION = 'vellum-1'
STAMP = 'CodexIntervallorum:' + VERSION
LEGACY_STAMP = 'LibrumQuinque:' + VERSION
DPI = 96
SCALE = DPI / 72
PADDING_PT = 3
GRAIN_PADDING_PT = 1
PIGMENT = (104, 72, 39)
TEXT_FLAGS = fitz.TEXTFLAGS_RAWDICT & ~fitz.TEXT_PRESERVE_IMAGES
PROFILES = ('light', 'full')


def seed_for(identity, seed=0):
    key = f'{VERSION}/{seed}/{identity}'.encode()
    return int.from_bytes(hashlib.sha256(key).digest()[:8], 'big')


def text_record(page):
    return page.get_text('rawdict', flags=TEXT_FLAGS)


def text_boxes(page):
    return [fitz.Rect(s['bbox']) for b in text_record(page)['blocks']
            for line in b.get('lines', []) for s in line['spans']]


def protection(page, *, whole_spans=False):
    """Protect pale as well as dark strokes, including vector-only ciphers.

    Grain is excluded from strokes and their immediate surroundings. Blotches
    use a wider mask including entire text spans so they cannot become apparent
    punctuation. Complete raster-art rectangles are always excluded.
    """
    pix = page.get_pixmap(matrix=fitz.Matrix(SCALE, SCALE),
                          colorspace=fitz.csRGB, alpha=False)
    rgb = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, 3)
    light = np.asarray(Image.fromarray(rgb).convert('L'), dtype=np.int16)
    # A flat cream substrate is paper; ink and even light, abrupt rules are not.
    marked = light < 215
    dx = np.abs(np.diff(light, axis=1)) > 7
    dy = np.abs(np.diff(light, axis=0)) > 7
    marked[:, 1:] |= dx
    marked[:, :-1] |= dx
    marked[1:, :] |= dy
    marked[:-1, :] |= dy
    mask = Image.fromarray(marked.astype(np.uint8) * 255)
    padding = PADDING_PT if whole_spans else GRAIN_PADDING_PT
    radius = math.ceil(padding * SCALE)
    mask = mask.filter(ImageFilter.MaxFilter(2 * radius + 1))
    draw = ImageDraw.Draw(mask)
    for rect in [*(text_boxes(page) if whole_spans else []),
                 *(fitz.Rect(i['bbox']) for i in page.get_image_info())]:
        r = (rect + (-PADDING_PT, -PADDING_PT, PADDING_PT, PADDING_PT)) * SCALE
        draw.rectangle(tuple(r), fill=255)
    return np.asarray(mask) == 255, rgb


def field(rng, shape, cells):
    """Smooth random field, without tiling a repeating paper photograph."""
    h, w = shape
    a = rng.integers(0, 256, (cells, max(2, round(cells * w / h))), dtype=np.uint8)
    return np.asarray(Image.fromarray(a).resize((w, h), Image.Resampling.BICUBIC),
                      dtype=np.float32) / 255


def make_texture(page, identity, seed=0, *, profile='light'):
    if profile not in PROFILES:
        raise ValueError(f'Unknown vellum profile: {profile}')
    protected, _ = protection(page)
    h, w = protected.shape
    rng = np.random.default_rng(seed_for(identity, seed))
    # A non-paper page receives no finish. Images and dark fields remain intact.
    if (~protected).mean() < .12:
        return None
    coarse = field(rng, (h, w), 5)
    medium = field(rng, (h, w), 19)
    fine = field(rng, (h, w), 73)
    yy, xx = np.mgrid[:h, :w]
    edge = np.minimum.reduce([xx / SCALE, (w - 1 - xx) / SCALE,
                              yy / SCALE, (h - 1 - yy) / SCALE])
    # The full profile retains the original independent pixel noise. Smooth
    # fields compress far better without it; light also halves the pigment.
    micrograin = rng.normal(0, .35, (h, w))
    tone = (.3 + 2.7 * coarse + 1.4 * medium + .6 * fine
            + (micrograin if profile == 'full' else 0)
            + 1.3 * np.exp(-edge / 23))
    # Small, discontinuous fibres; no continuous lines or invented letters.
    fibres = Image.new('L', (w, h))
    draw = ImageDraw.Draw(fibres)
    for _ in range(round(page.rect.width * page.rect.height / 15000)):
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        length = rng.uniform(.8, 3.2) * SCALE
        angle = rng.uniform(0, 2 * math.pi)
        draw.line([(x, y), (x + length * math.cos(angle),
                           y + length * math.sin(angle))], fill=2, width=1)
    tone += np.asarray(fibres)
    # Ease into the protected zones rather than cutting visible rectangular holes.
    safe = Image.fromarray((~protected).astype(np.uint8) * 255)
    fade = np.asarray(safe.filter(ImageFilter.GaussianBlur(.6 * SCALE))) / 255
    strength = .5 if profile == 'light' else 1
    opacity = np.rint(np.clip(tone * fade * strength, 0, 11)).astype(np.uint8)
    opacity[protected] = 0
    spots = []
    if rng.random() < .14:
        spot_protected, _ = protection(page, whole_spans=True)
        for _ in range(50):
            # Confine recognisable ink marks to the outermost 25 points.
            side = int(rng.integers(0, 4))
            if side < 2:
                x = rng.uniform(8, 22)
                if side == 1:
                    x = page.rect.width - x
                y = rng.uniform(12, page.rect.height - 12)
            else:
                x = rng.uniform(12, page.rect.width - 12)
                y = rng.uniform(8, 22)
                if side == 3:
                    y = page.rect.height - y
            # Check the whole cluster and a second generous separation zone.
            r = fitz.Rect(x - 4, y - 4, x + 4, y + 4)
            x0, y0, x1, y1 = (r * SCALE).irect
            if spot_protected[y0:y1, x0:x1].any():
                continue
            spot = Image.new('L', (w, h))
            pen = ImageDraw.Draw(spot)
            for j in range(int(rng.integers(2, 5))):
                cx = (x + (0 if j == 0 else rng.uniform(-1.8, 1.8))) * SCALE
                cy = (y + (0 if j == 0 else rng.uniform(-1.8, 1.8))) * SCALE
                radius = rng.uniform(.3, .85) * SCALE
                pen.ellipse((cx - radius, cy - radius * .8,
                             cx + radius, cy + radius * .8),
                            fill=int(rng.integers(32, 75)))
            spot_opacity = np.rint(np.asarray(spot) * strength).astype(np.uint8)
            opacity = np.maximum(opacity, spot_opacity)
            spots.append([round(v, 3) for v in r])
            break
    opacity[protected] = 0
    assert not opacity[protected].any()
    # Near-white pixels are useful in tests as well as cream-paper documents.
    return opacity, dict(identity=identity, ink_spots=spots,
                         protected_pixels=int(protected.sum()),
                         paper_pixels=int((~protected).sum()),
                         max_opacity=int(opacity.max()))


def png(array):
    buf = io.BytesIO()
    Image.fromarray(array).save(buf, format='PNG', optimize=True)
    return buf.getvalue()


def add_texture(page, opacity):
    # A constant pigment image compresses tightly; the varying soft mask holds
    # the grain. Original source pages remain vectors, text and original images.
    pigment = np.empty((*opacity.shape, 4), np.uint8)
    pigment[:, :, :3] = PIGMENT
    pigment[:, :, 3] = opacity
    # Put alpha in the PNG stream: PyMuPDF's image cache hashes that stream,
    # whereas a separately supplied mask can collide on constant pigment bytes.
    xref = page.insert_image(page.rect, stream=png(pigment),
                             overlay=True, keep_proportion=False)
    page.parent.xref_set_key(xref, 'LQVellum', '(' + VERSION + ')')


def is_texture(page, xref):
    return bool(xref and page.parent.xref_get_key(xref, 'LQVellum') == ('string', VERSION))


def source_images(page):
    """Keep binding illustration checks independent of tagged background images."""
    return [i for i in page.get_images() if not is_texture(page, i[0])]


def source_image_info(page):
    return [i for i in page.get_image_info(hashes=True, xrefs=True)
            if not is_texture(page, i['xref'])]


def identities(doc, log_path=None):
    result = {}
    if log_path and Path(log_path).exists():
        for title, entry in json.loads(Path(log_path).read_text()).items():
            if isinstance(entry, dict) and 'source' in entry:
                for local, physical in entry.get('body_page_map', {}).items():
                    result[physical - 1] = f'{title}/{local}'
    for i, page in enumerate(doc):
        if i not in result:
            # Other leaves use their content, so moving them does not change it.
            fingerprint = page.get_contents()
            data = b''.join(doc.xref_stream(x) for x in fingerprint)
            result[i] = 'leaf/' + hashlib.sha256(data).hexdigest()
    return result


def paths(page):
    return [{k: v for k, v in d.items() if k != 'seqno'}
            for d in page.get_drawings()]


def images(page):
    return [{k: v for k, v in i.items() if k in
             ('bbox', 'width', 'height', 'transform', 'digest', 'colorspace', 'bpc')}
            for i in page.get_image_info(hashes=True)]


def links(page):
    return [{k: v for k, v in i.items() if k not in ('xref', 'id')}
            for i in page.get_links()]


def verify_page(before, after, texture_added=False):
    """Keep source geometry and enforce exact rendered pixels in the mask."""
    if (before.rect != after.rect or before.rotation != after.rotation
            or before.mediabox != after.mediabox or before.cropbox != after.cropbox
            or text_record(before) != text_record(after)):
        raise ValueError(f'Text or page geometry changed on page {before.number + 1}')
    if paths(before) != paths(after) or links(before) != links(after):
        raise ValueError(f'Source paths or links changed on page {before.number + 1}')
    bi, ai = images(before), images(after)
    if ai[:len(bi)] != bi or len(ai) != len(bi) + texture_added:
        raise ValueError(f'Source image changed on page {before.number + 1}')
    protected, rgb = protection(before)
    pix = after.get_pixmap(matrix=fitz.Matrix(SCALE, SCALE),
                           colorspace=fitz.csRGB, alpha=False)
    finished = np.frombuffer(pix.samples, np.uint8).reshape(rgb.shape)
    # Render-level proof covers vector ciphers and raster illustrations too.
    if np.any(rgb[protected] != finished[protected]):
        raise ValueError(f'Protected pixels changed on page {before.number + 1}')
    if not texture_added and not np.array_equal(rgb, finished):
        raise ValueError(f'Skipped page changed on page {before.number + 1}')
    return int(np.any(rgb != finished, axis=2).sum())


def apply(pdf, output=None, *, seed=0, log_path=None, profile='light'):
    if profile not in PROFILES:
        raise ValueError(f'Unknown vellum profile: {profile}')
    pdf = Path(pdf)
    output = Path(output or pdf)
    output.parent.mkdir(parents=True, exist_ok=True)
    original = fitz.open(pdf)
    keywords = original.metadata.get('keywords') or ''
    if STAMP in keywords or LEGACY_STAMP in keywords:
        original.close()
        raise ValueError('This PDF already has vellum finishing; use the original binding')
    if any(p.rotation or p.rect.x0 or p.rect.y0 for p in original):
        original.close()
        raise ValueError('Vellum finishing requires unrotated, zero-origin reading pages')
    identity = identities(original, log_path or pdf.with_name('binding-log.json'))
    doc = fitz.open(pdf)
    records = []
    tmp = output.with_name(output.name + '.vellum-tmp')
    try:
        for i, page in enumerate(doc):
            result = make_texture(original[i], identity[i], seed, profile=profile)
            if result is not None:
                opacity, record = result
                add_texture(page, opacity)
                records.append(dict(page=i + 1, **record))
            if (i + 1) % 50 == 0:
                print(f'Vellum: prepared {i + 1}/{len(doc)} pages', flush=True)
        metadata = doc.metadata
        metadata['keywords'] = ((metadata.get('keywords') or '') + '; ' + STAMP).lstrip('; ')
        doc.set_metadata(metadata)
        doc.save(tmp, garbage=3, deflate=True, no_new_id=True)
        doc.close()
        # Verify independently reopened files, without planning-pass render caches.
        original.close()
        original = fitz.open(pdf)
        changed = 0
        with fitz.open(tmp) as finished:
            if len(original) != len(finished) or original.get_toc() != finished.get_toc():
                raise ValueError('Page count or outline changed')
            added = {r['page'] for r in records}
            for i, (before, after) in enumerate(zip(original, finished)):
                # No need to retain hundreds of mask arrays in memory.
                changed += verify_page(before, after, i + 1 in added)
                if (i + 1) % 50 == 0:
                    print(f'Vellum: verified {i + 1}/{len(original)} pages', flush=True)
        original.close()
        tmp.replace(output)
    except Exception:
        if not doc.is_closed:
            doc.close()
        if not original.is_closed:
            original.close()
        tmp.unlink(missing_ok=True)
        raise
    report = dict(version=VERSION, profile=profile, seed=seed, dpi=DPI, textured_pages=len(records),
                  ink_spot_pages=sum(bool(r['ink_spots']) for r in records),
                  verification=dict(text_exact=True, original_vector_paths_exact=True,
                                    original_images_exact=True, links_and_outline_exact=True,
                                    protected_pixels_exact=True, changed_pixels=changed),
                  pages=records)
    output.with_name('vellum-log.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'pages'}), flush=True)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path, nargs='?')
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--profile', choices=PROFILES, default='light')
    args = parser.parse_args()
    apply(args.input, args.output, seed=args.seed, profile=args.profile)

