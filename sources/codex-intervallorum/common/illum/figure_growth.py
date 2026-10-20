"""Progressive image-guided Physarum masks for the illustrated figures.

The three-sensor/deposit/diffuse rule follows the vocabulary of Book V, but
this is a separate, image-fed decorative run. Rendered hatches are integrated
curves of a direction field, not recorded agent trajectories. Cornmeal is
sampled along those same curves. No alphabet or semantic diagram enters here.
"""
import hashlib
import json
import math
import os
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

VERSION = "figure-growth-1"
OUTPUT_DPI = 360
ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "build" / "figure-growth"
CODE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
SPEC = dict(grid=[144, 216], agents=1500, steps=220, sensor_offset=5.5,
            sensor_angle_deg=40, rotation_angle_deg=32, deposit=3.0,
            evaporation=0.075, food_gain=5.0, tensor_alignment=0.15)

# Source-pixel rectangles, expressed as fractions of the unchanged canvas.
# These supplement the broad, feathered upper-figure guard and red-pixel guard.
# They protect recognisable objects and maintain a tonal bridge into the body.
ANCHORS = {
    "foras": [(0.29, .29, .72, .57), (.70, .57, .84, .69)],
    "gremory": [(.34, .13, .65, .40), (.18, .34, .36, .49), (.69, .34, .88, .50)],
    "bune": [(.36, .12, .63, .36), (.12, .33, .37, .52), (.70, .31, .91, .53)],
    "vassago": [(.33, .13, .66, .42), (.25, .37, .75, .56)],
    "orobas": [(.36, .13, .80, .42)],
    "paimon": [(.21, .15, .72, .45)],
    "keeper-wearing-dial": [(.35, .24, .60, .43), (.51, .44, .70, .63)],
    "measurer-of-absences-original": [(.58, .25, .80, .51)],
    "hora-and-tempus": [(.08, .12, .42, .47), (.56, .12, .88, .47)],
    "figure-beneath-cord": [(.24, .12, .65, .45)],
    "decision-demon": [(.27, .14, .79, .43)],
}


def smooth(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def resize(a, size):
    return np.asarray(Image.fromarray(np.asarray(a, np.float32), "F").resize(size, Image.Resampling.BILINEAR))


def blur(a, radius):
    return np.asarray(Image.fromarray(np.uint8(np.clip(a, 0, 1) * 255)).filter(
        ImageFilter.GaussianBlur(radius)), dtype=float) / 255


def subject(meta):
    return Path(meta["source"]).name.split("-raster-reference")[0]


def configure(canvas, section, index, total):
    """A fixed, monotone reading-order schedule; geometry/keying never use it."""
    if os.environ.get("GRIMOIRE_FIGURE_GROWTH", "1") == "0":
        amount = 0.0
    elif section == "III":
        amount = .38 * index / max(1, total - 1)
    elif section == "IV":
        amount = .43 + .43 * index / max(1, total - 1)
    else:
        amount = 0.0
    canvas._figure_growth = dict(section=section, index=index, total=total,
                                 amount=round(float(amount), 5))
    if not hasattr(canvas, "_figure_growth_records"):
        canvas._figure_growth_records = []
    return canvas._figure_growth


def protection(rgb, name, bbox):
    """Exact protected cores, with broad shoulders instead of sharp islands."""
    h, w = rgb.shape[:2]
    yy, xx = np.mgrid[:h, :w]
    x0, y0, x1, y1 = bbox
    # Upper anatomy remains continuous into the shoulders, not a cut-out face.
    guard = 1 - smooth((yy - y0 - .28 * (y1 - y0)) / max(1, .16 * (y1 - y0)))
    cores = np.zeros((h, w), np.uint8)
    for a, b, c, d in ANCHORS.get(name, []):
        cores[int(b*h):int(d*h)+1, int(a*w):int(c*w)+1] = 255
    r, g, b = rgb.transpose(2, 0, 1).astype(float)
    cores[(r - np.maximum(g, b) > 30) & (r > 80)] = 255
    core_img = Image.fromarray(cores).filter(ImageFilter.MaxFilter(9))
    core = np.asarray(core_img) > 0
    shoulder = np.asarray(core_img.filter(ImageFilter.GaussianBlur(w * .019)), float) / 255
    guard = np.maximum(guard, smooth(shoulder * 1.8))
    guard[core] = 1
    return guard, core


def simulate(food, seed):
    """One population; image food, three sensors, deposition, diffusion, decay.

    The arena is bounded, not toroidal. Collision exclusion and biological
    fidelity are not claimed. Source structure guides heading, not anatomy.
    """
    w, h = SPEC["grid"]
    food = resize(food, (w, h))
    food = blur(food, 1.0)
    gy, gx = np.gradient(blur(food, 2))
    tangent = np.arctan2(gy, gx) + np.pi / 2
    rng = np.random.default_rng(seed)
    probabilities = (food + .018).ravel()
    initial = rng.choice(w*h, SPEC["agents"], p=probabilities/probabilities.sum())
    x = (initial % w).astype(float) + rng.random(len(initial))
    y = (initial // w).astype(float) + rng.random(len(initial))
    heading = rng.uniform(-np.pi, np.pi, len(x))
    field = np.zeros((h, w))
    sa, ra = np.radians([SPEC["sensor_angle_deg"], SPEC["rotation_angle_deg"]])
    def sample(a, px, py):
        return a[np.clip(py.astype(int), 0, h-1), np.clip(px.astype(int), 0, w-1)]
    for _ in range(SPEC["steps"]):
        sensed = field + food * SPEC["food_gain"]
        values = [sample(sensed, x+SPEC["sensor_offset"]*np.cos(heading+a),
                         y+SPEC["sensor_offset"]*np.sin(heading+a)) for a in (-sa, 0, sa)]
        left, front, right = values
        turn = np.where(left > right, -ra, ra)
        turn = np.where((left > front) & (right > front), rng.choice([-ra, ra], len(x)), turn)
        heading += np.where(np.maximum(left, right) > front, turn, 0)
        angle = sample(tangent, x, y)
        heading += SPEC["tensor_alignment"] * .5 * np.sin(2*(angle-heading))
        nx, ny = x + np.cos(heading), y + np.sin(heading)
        ok = (nx > 1) & (nx < w-2) & (ny > 1) & (ny < h-2)
        x, y = np.where(ok, nx, x), np.where(ok, ny, y)
        heading = np.where(ok, heading, rng.uniform(-np.pi, np.pi, len(x)))
        np.add.at(field, (y.astype(int), x.astype(int)), SPEC["deposit"])
        pad = np.pad(field, 1)
        field = sum(pad[j:j+h, i:i+w] for j in range(3) for i in range(3))/9
        field *= 1-SPEC["evaporation"]
    field /= max(float(np.quantile(field, .985)), 1e-9)
    return np.clip(field, 0, 1)


def masks(rgb, meta, field, amount):
    h, w = rgb.shape[:2]
    guard, core = protection(rgb, subject(meta), meta["figure_bbox_px"])
    f = resize(field, (w, h))
    _, y0, _, y1 = meta["figure_bbox_px"]
    yy = np.arange(h)[:, None]
    height = np.clip((yy-y0)/max(1, y1-y0), 0, 1)
    # A persistent spatial front: increasing amount never unmasks a region.
    priority = .53*(1-f) + .30*(1-height)
    mask = smooth((amount*1.06-priority)/.19)*(1-guard)
    ink = np.uint8((rgb.mean(axis=2) < 244)*255)
    support = np.asarray(Image.fromarray(ink).filter(ImageFilter.MaxFilter(31)).filter(
        ImageFilter.GaussianBlur(3)), float)/255
    mask *= support
    return mask, core


def edge_masks(rgb, meta, field, amount, display_width=240):
    """A narrow physical fringe, with the existing anatomy/object guards.

    This explicitly selected mode leaves the figure's interior alone. The
    sampling image has a faint shoulder so strokes can become grain just
    outside the old contour, inside the unchanged source canvas.
    """
    h,w=rgb.shape[:2]
    radius=max(2,min(23,round(w/max(10,display_width)*1.3)))
    ink=Image.fromarray(np.uint8(rgb.mean(2)<237)*255)
    outer=ink.filter(ImageFilter.MaxFilter(2*radius+1))
    inner=ink.filter(ImageFilter.MinFilter(2*radius+1))
    band=np.clip((np.asarray(outer,float)-np.asarray(inner,float))/255,0,1)
    guard,core=protection(rgb,subject(meta),meta['figure_bbox_px'])
    f=resize(field,(w,h))
    mask=band*(.25+.55*f)*min(.8,amount)*(1-guard)
    shoulder=np.asarray(outer.filter(ImageFilter.GaussianBlur(max(1,radius*.5))),float)/255
    sampling=np.uint8(np.minimum(rgb.astype(float),255*(1-.30*shoulder[...,None])))
    return mask,core,sampling


def contours(field, level):
    """Marching squares, with a fixed centre rule at saddle cells."""
    h,w = field.shape
    a,b,c,d = field[:-1,:-1],field[:-1,1:],field[1:,1:],field[1:,:-1]
    active = (np.minimum.reduce([a,b,c,d]) < level) & (np.maximum.reduce([a,b,c,d]) >= level)
    segments=[]
    for y,x in zip(*np.nonzero(active)):
        values=[field[y,x],field[y,x+1],field[y+1,x+1],field[y+1,x]]
        points=[(x,y),(x+1,y),(x+1,y+1),(x,y+1)];cross=[]
        for i in range(4):
            j=(i+1)%4
            if (values[i]<level) != (values[j]<level):
                t=(level-values[i])/(values[j]-values[i])
                cross.append((points[i][0]+t*(points[j][0]-points[i][0]),
                              points[i][1]+t*(points[j][1]-points[i][1])))
        if len(cross)==2: segments.append(cross)
        elif len(cross)==4:
            if sum(values)/4 < level: cross=cross[1:]+cross[:1]
            segments.extend([cross[:2],cross[2:]])
    key=lambda p:(round(p[0],4),round(p[1],4))
    adj={}
    for i,pair in enumerate(segments):
        for p in pair: adj.setdefault(key(p),[]).append(i)
    used=set()
    for i,pair in enumerate(segments):
        if i in used: continue
        line=list(pair);used.add(i)
        for end in (1,0):
            while True:
                p=line[-1] if end else line[0]
                choices=[j for j in adj[key(p)] if j not in used]
                if not choices: break
                j=choices[0];used.add(j);a,b=segments[j]
                other=b if key(a)==key(p) else a
                if end: line.append(other)
                else: line.insert(0,other)
        if len(line)>=8: yield line


def render_material(rgb, field, mask, seed, cornmeal, display_width=None):
    """Spaced, tone-gated flow strokes become interrupted lines and grains."""
    h, w = rgb.shape[:2]
    display_width = max(10, display_width or 240)
    fw = max(48, min(240, round(display_width*2)))
    fh = max(48, round(fw*h/w))
    small = np.asarray(Image.fromarray(rgb).resize((fw, fh)), float)/255
    tone = np.clip(1-small.mean(axis=2), 0, 1)
    tone = blur(tone, .8)
    f = resize(field, (fw, fh))
    m = resize(mask, (fw, fh))
    gy, gx = np.gradient(blur(tone, 1.8))
    # Smoothed structure tensor: a stable tangent through small gaps.
    # Preserve signed off-diagonal terms; uint8 blur is unsuitable for them.
    def box_smooth(a):
        p=np.pad(a,3,mode="edge")
        return sum(p[y:y+fh,x:x+fw] for y in range(7) for x in range(7))/49
    jxx,jyy,jxy = [box_smooth(a) for a in (gx*gx,gy*gy,gx*gy)]
    theta = .5*np.arctan2(2*jxy, jxx-jyy) + np.pi/2
    fgy, fgx = np.gradient(blur(f, 1.2))
    field_angle = np.arctan2(fgy, fgx) + np.pi/2
    # Blend in doubled-angle space so opposite directions do not cancel.
    theta = .5*np.arctan2(.7*np.sin(2*theta)+.3*np.sin(2*field_angle),
                         .7*np.cos(2*theta)+.3*np.cos(2*field_angle))
    rng = np.random.default_rng(seed ^ 1917)
    ink = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(ink)
    occupied = np.zeros((fh, fw), bool)
    weights = (tone * (.22+.78*f) * m).ravel()
    if weights.sum() == 0:
        return np.asarray(ink), dict(curves=0, grains=0)
    candidates = rng.choice(fw*fh, min(10000, fw*fh), replace=False,
                            p=(weights+1e-10)/(weights+1e-10).sum())
    curves = grains = 0
    sx, sy = w/fw, h/fh
    for idx in candidates:
        cy, cx = divmod(int(idx), fw)
        if occupied[cy, cx] or m[cy, cx] < .035 or tone[cy, cx] < .025:
            continue
        paths = []
        for sign in (-1, 1):
            x, y, previous = cx+.5, cy+.5, None
            pts = []
            for step in range(22):
                ix, iy = int(x), int(y)
                if not (2 <= ix < fw-2 and 2 <= iy < fh-2): break
                if m[iy, ix] < .025 or tone[iy, ix] < .018: break
                if step > 3 and occupied[iy, ix]: break
                a = theta[iy, ix]
                vx, vy = math.cos(a)*sign, math.sin(a)*sign
                if previous is not None and vx*previous[0]+vy*previous[1] < 0:
                    vx, vy = -vx, -vy
                if previous is not None:
                    vx, vy = .72*previous[0]+.28*vx, .72*previous[1]+.28*vy
                norm = math.hypot(vx, vy) or 1
                vx, vy = vx/norm, vy/norm
                pts.append((x*sx, y*sy))
                x, y = x+vx*.85, y+vy*.85
                previous = vx, vy
            paths.append(pts)
        pts = list(reversed(paths[0])) + paths[1][1:]
        if len(pts) < 4: continue
        curves += 1
        col = tuple(np.uint8(np.clip(small[cy,cx]*30 + np.array([39,34,25]), 15, 95)))
        granular = cornmeal * (.30+.70*f[cy,cx])
        # The same ordered samples supply line segments and grains.
        width = max(1, round(sx*(.25+.62*tone[cy,cx])), round(w/display_width*.22))
        for j,(a,b) in enumerate(zip(pts, pts[1:])):
            if rng.random() > granular:
                d.line([a,b], fill=col, width=width)
            else:
                dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy) or 1
                spread = rng.normal(0, sx*.22)
                px,py=a[0]-dy/length*spread,a[1]+dx/length*spread
                radius = max(sx*rng.uniform(.16,.39), w/display_width*.11)
                grain_col = tuple(int(v) for v in (.70*np.array(col)+.30*np.array([158,131,82])))
                d.ellipse((px-radius,py-radius*.7,px+radius,py+radius*.7),fill=grain_col)
                grains += 1
        for x,y in pts:
            ix,iy=int(x/sx),int(y/sy)
            occupied[max(0,iy-1):min(fh,iy+2),max(0,ix-1):min(fw,ix+2)] = True
        if curves >= 2200: break
    # Iso-lines make the actual colony structure visible at a second scale.
    # They use the same mask, ink budget and interrupted-stroke/grain grammar.
    for level in (.045,.095,.18,.32,.52):
        for line in contours(field,level):
            for a,b in zip(line,line[1:]):
                x,y=a[0]/SPEC['grid'][0]*w,a[1]/SPEC['grid'][1]*h
                ix,iy=min(fw-1,int(x/sx)),min(fh-1,int(y/sy))
                if m[iy,ix]<.04 or tone[iy,ix]<.025: continue
                end=(b[0]/SPEC['grid'][0]*w,b[1]/SPEC['grid'][1]*h)
                if rng.random()>cornmeal*.72:
                    d.line([(x,y),end],fill=(88,74,48),width=max(1,round(w/750),round(w/display_width*.20)))
                else:
                    r=max(rng.uniform(.8,1.8)*w/1024,w/display_width*.10)
                    d.ellipse((x-r,y-r*.7,x+r,y+r*.7),fill=(148,122,75));grains+=1
    return np.asarray(ink), dict(curves=curves, grains=grains)


def appearance(canvas, keyed_path, meta, display_size=None):
    stage = getattr(canvas, "_figure_growth", None)
    if stage and stage["section"] == "III":
        # Advance only at a visible placement, never at a geometry/avoidance query.
        configure(canvas, "III", stage["index"]+1, stage["total"])
    if not stage or stage["amount"] <= 0:
        details = {"version": VERSION, "amount": 0, "unchanged": True,
                   "source": meta["source"], "stage": stage}
        if stage: canvas._figure_growth_records.append(details)
        return keyed_path, details
    # This seed is independent of amount and of the source's absolute path.
    seed = int(hashlib.sha256((subject(meta)+meta["source_sha256"]).encode()).hexdigest()[:8], 16)
    edge_mode=subject(meta) in getattr(canvas,'_figure_edge_subjects',())
    inputs = dict(version=VERSION, code_sha256=CODE_SHA256, stage=stage,
                  source_sha256=meta["source_sha256"], keyed_sha256=hashlib.sha256(Path(keyed_path).read_bytes()).hexdigest(),
                  seed=seed, spec=SPEC, anchors=ANCHORS.get(subject(meta), []),
                  display_size_pt=[round(abs(v),3) for v in display_size] if display_size else None,
                  treatment='contour fringe' if edge_mode else 'progressive body')
    key = hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()[:20]
    CACHE.mkdir(parents=True, exist_ok=True)
    out = CACHE / f"{subject(meta)}-{key}.png"
    record = out.with_suffix(".json")
    if not out.exists() or not record.exists():
        rgb = np.asarray(Image.open(keyed_path).convert("RGB"))
        tone = 1-rgb.mean(axis=2)/255
        field = simulate(tone, seed)
        mask, core = masks(rgb, meta, field, stage["amount"])
        sampling=rgb
        if edge_mode:
            mask,core,sampling=edge_masks(rgb,meta,field,stage['amount'],
                                          abs(display_size[0]) if display_size else 240)
        cornmeal = .15 + .65*stage["amount"]
        material, counts = render_material(sampling, field, mask, seed, cornmeal,
                                           abs(display_size[0]) if display_size else None)
        # A continuous tonal bridge remains through the transition. This is
        # replacement within a mask, never a second full-opacity drawing.
        replacement = .16*rgb.astype(float)+.84*material.astype(float)
        result = np.uint8(np.clip(np.rint(rgb*(1-mask[...,None])+replacement*mask[...,None]),0,255))
        result[core] = rgb[core]
        output = Image.fromarray(result)
        if display_size:
            scale=min(1,abs(display_size[0])*OUTPUT_DPI/72/output.width,
                        abs(display_size[1])*OUTPUT_DPI/72/output.height)
            if scale < 1:
                output=output.resize((max(1,round(output.width*scale)),max(1,round(output.height*scale))),Image.Resampling.LANCZOS)
        output.save(out, optimize=True)
        inputs.update(amount=stage["amount"], cornmeal=cornmeal, **counts,
                      field_sha256=hashlib.sha256(np.round(field,6).tobytes()).hexdigest(),
                      mask_sha256=hashlib.sha256(np.uint8(mask*255).tobytes()).hexdigest(),
                      mean_mask=round(float(mask.mean()),6), protected_pixels=int(core.sum()),
                      protected_pixels_equal=bool(np.array_equal(result[core],rgb[core])),
                      outside_mask_equal=bool(np.array_equal(result[mask==0],rgb[mask==0])),
                      protected_check_stage="source grid, before output resampling and ground palette",
                      output_size_px=list(output.size),output_dpi_cap=OUTPUT_DPI,
                      output_sha256=hashlib.sha256(out.read_bytes()).hexdigest())
        record.write_text(json.dumps(inputs,indent=2)+"\n")
    details = json.loads(record.read_text())
    canvas._figure_growth_records.append(details)
    if getattr(canvas, "_figure_ground", "light") == "dark":
        night = out.with_name(out.stem+"-night.png")
        if not night.exists():
            a=np.asarray(Image.open(out).convert("RGB"),float)/255
            density=1-a.mean(axis=2)
            # Black is transparent in Screen. Pale cornmeal and chalk replace
            # the page's dark inks; the red intervention keeps its own hue.
            n=density[...,None]*np.array([235,225,200])
            red=np.clip((a[...,0]-np.maximum(a[...,1],a[...,2])-.08)/.25,0,1)
            n=n*(1-red[...,None])+density[...,None]*np.array([242,116,83])*red[...,None]
            Image.fromarray(np.uint8(np.clip(n,0,255))).save(night,optimize=True)
        details=dict(details,ground="dark",display_sha256=hashlib.sha256(night.read_bytes()).hexdigest())
        canvas._figure_growth_records[-1]=details
        return str(night), details
    return str(out), details


def cornmeal_path(canvas, pts, color=(90,67,49), seed=0, weight=.3):
    """Tangent-jitter grains around an explicitly selected nonsemantic path.

    The uninterrupted original centerline is drawn by the caller. This shares
    the old Matricis grain hand's perpendicular displacement grammar.
    """
    rng = np.random.default_rng(seed)
    canvas.saveState()
    canvas.setFillColorRGB(*(v/255 for v in color))
    grains=0
    for a,b in zip(pts,pts[1:]):
        dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
        if length < .01: continue
        for t in np.arange(.3,length,.8):
            off=rng.normal(0,.23)
            x=a[0]+dx*t/length-dy/length*off
            y=a[1]+dy*t/length+dx/length*off
            r=rng.uniform(.11,.25)*max(.8,weight/.3)
            canvas.circle(x,y,r,fill=1,stroke=0);grains+=1
    canvas.restoreState()
    return grains


def flowing_rule(hand,x0,x1,y,color='umber',seed=0):
    """A selected decorative scallop, with its original strokes retained.

    A small image-fed field modulates sparse grain along the recorded paths.
    Call only for illustration furniture; no semantic or plotted paths enter.
    """
    import furniture as fu
    paths=[]
    def stroke(pts,*args,**kwargs):
        paths.append(list(pts))
        return hand.stroke(pts,*args,**kwargs)
    fu.wave_rule(SimpleNamespace(stroke=stroke),x0,x1,y,color=color,seed=seed)
    width=144;height=32
    food=Image.new('L',(width,height),0)
    draw=ImageDraw.Draw(food)
    def grid(p):return ((p[0]-x0)/max(1,x1-x0)*(width-1),(y+5-p[1])/10*(height-1))
    for pts in paths:draw.line([grid(p) for p in pts],fill=255,width=2)
    field_seed=int(hashlib.sha256(('wave-grain-'+str(seed)).encode()).hexdigest()[:8],16)
    field=resize(simulate(np.asarray(food,float)/255,field_seed),(width,height))
    rng=np.random.default_rng(field_seed)
    c=hand.c;c.saveState();c.setFillColorRGB(148/255,122/255,75/255)
    grains=0
    for pts in paths:
        for a,b in zip(pts,pts[1:]):
            dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
            if length<.01:continue
            gx,gy=grid(a)
            f=field[min(height-1,max(0,round(gy))),min(width-1,max(0,round(gx)))]
            if rng.random()>.12+.40*f:continue
            t=rng.random();off=rng.normal(0,.35+.35*f)
            x=a[0]+dx*t-dy/length*off;yy=a[1]+dy*t+dx/length*off
            r=rng.uniform(.12,.23)
            c.circle(x,yy,r,fill=1,stroke=0);grains+=1
    c.restoreState()
    if not hasattr(c,'_flow_material_records'):c._flow_material_records=[]
    c._flow_material_records.append(dict(kind='decorative footer wave',seed=field_seed,
        grains=grains,field_sha256=hashlib.sha256(np.round(field,6).tobytes()).hexdigest(),
        original_paths_retained=True))
    return grains
