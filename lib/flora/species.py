"""Species-informed drawing grammars, not calibrated botanical growth models.

Seeds change architecture and organ placement. Stage changes are deliberately
discrete; a spring fruit head is not a universal late-summer state.
"""
import random
import numpy as np
from .model import Plant, bezier, frame, unit

SPECIES = {
    "little_bluestem": dict(common="Little bluestem", latin="Schizachyrium scoparium",
        stages=("seed", "leafy"), habitat="dry prairie"),
    "side_oats_grama": dict(common="Side-oats grama", latin="Bouteloua curtipendula",
        stages=("seed", "leafy"), habitat="dry bluff prairie"),
    "leadplant": dict(common="Leadplant", latin="Amorpha canescens",
        stages=("flowering", "leafy"), habitat="prairie / savanna"),
    "prairie_smoke": dict(common="Prairie smoke", latin="Geum triflorum",
        stages=("seed", "flowering", "leafy"), habitat="dry prairie"),
    "wild_bergamot": dict(common="Wild bergamot", latin="Monarda fistulosa",
        stages=("flowering", "seed"), habitat="prairie / open woodland"),
    "bur_oak": dict(common="Bur oak", latin="Quercus macrocarpa",
        stages=("leafy", "bare"), habitat="oak savanna"),
}


def radial(a, z=0):
    return np.array([np.cos(a), np.sin(a), z])


def axis(p, a, b, r=.001, bend=None, bark=False):
    a, b = np.asarray(a, float), np.asarray(b, float)
    c = (a+b)/2 if bend is None else np.asarray(bend)
    return p.stem(bezier(a, c, b), r, bark=bark)


def compound(p, base, direction, length, rng, pairs=9, fern=False):
    d, side = frame(direction, rng.uniform(-.35, .35))
    base = np.asarray(base)
    tip = base+d*length
    axis(p, base, tip, .00045)
    for j in range(pairs):
        t = .15+.77*j/pairs
        q = base+d*length*t
        for sign in (-1, 1):
            ll = length*(.22 if fern else .15)*((.55+.65*t) if fern else (1-.35*t))*rng.uniform(.9, 1.1)
            p.leaf(q, sign*side*.9+d*.3, ll, ll*(.52 if fern else .50),
                   shape="fern" if fern else "oval", bend=-.12,
                   roll=rng.uniform(.5, 1.15)*sign, veins=True)
    p.leaf(tip-d*length*.04, d, length*.16, length*.08,
           shape="fern" if fern else "oval", roll=.8, veins=True)
    p.organs.append({"type": "compound_leaf", "pairs": pairs, "base": base.tolist()})


def grass(p, rng, stage, sideoats=False):
    for i in range(rng.randint(12, 18)):
        a = rng.uniform(0, 2*np.pi); L = rng.uniform(.22, .49)
        p.leaf(radial(a)*rng.uniform(0, .028), radial(a, rng.uniform(.6, 2)), L,
               rng.uniform(.003, .006), shape="grass", bend=-.45,
               roll=rng.uniform(-.5, .5))
    for k in range(rng.randint(5, 8)):
        a = rng.uniform(0, 2*np.pi); h = rng.uniform(.55, .93)
        base = radial(a)*rng.uniform(.01, .04)
        tip = base+radial(a)*rng.uniform(.02, .15)+[0, 0, h]
        culm = axis(p, base, tip, .001, base+[0, 0, h*.6])
        for j, t in enumerate((.24, .43, .62)):
            q = culm[round(t*(len(culm)-1))]
            p.leaf(q, radial(a+(j%2)*np.pi, .5), rng.uniform(.16, .29), .004,
                   shape="grass", bend=-.38, roll=.15)
        if stage == "leafy":
            continue
        if sideoats:
            # All pendant short branches point to one side of each rachis.
            side = radial(a+.7)
            for t in np.linspace(.67, .98, rng.randint(12, 19)):
                q = base+(tip-base)*t
                end = q+side*.017+[0, 0, -.018]
                axis(p, q, end, .00035)
                for f in range(3):
                    pos = q+(end-q)*(.4+f*.22)
                    p.leaf(pos, side*.4+[0, 0, -1], .010, .0028,
                           role="seed", veins=False, bend=0)
            p.organs.append({"type": "one_sided_raceme", "position": tip.tolist()})
        else:
            # Slender racemes, including short lateral ones; no turkey-foot head.
            for t in (.72, .84, .94):
                q = base+(tip-base)*t; end = q+radial(a)*.025+[0, 0, .07]
                axis(p, q, end, .00045)
                for u in np.linspace(.16, 1, 8):
                    pt = q+(end-q)*u
                    for sign in (-1, 1):
                        d = radial(a+sign*.9)*.010+[0, 0, .009]
                        p.line([pt, pt+d], "seed")
                        p.line([pt+d*.3, pt+d+[0, 0, .011]], "hair", 2)


def leadplant(p, rng, stage):
    for k in range(rng.randint(3, 5)):
        a = k*2.4+rng.uniform(-.4, .4); h = rng.uniform(.40, .72)
        end = radial(a)*rng.uniform(.07, .18)+[0, 0, h]
        stem = axis(p, [0, 0, 0], end, .003, end*[.2, .2, .65])
        for j, t in enumerate(np.linspace(.23, .87, 6)):
            q = stem[round(t*(len(stem)-1))]
            phi = a+j*2.4
            compound(p, q, radial(phi, .45), rng.uniform(.10, .17), rng,
                     pairs=rng.randint(8, 12))
        if stage == "flowering":
            for j in range(rng.randint(2, 4)):
                q = end+[0, 0, -.05]; v = radial(a+j*2)*.04+[0, 0, rng.uniform(.08, .15)]
                axis(p, q, q+v, .001)
                for n in range(36):
                    t = .18+.80*n/36; phi = n*2.39996
                    pt = q+v*t
                    p.leaf(pt, radial(phi, .2), .006, .0035,
                           role="flower", veins=False, bend=.1)
            p.organs.append({"type": "terminal_spikes", "position": end.tolist()})


def prairie_smoke(p, rng, stage):
    for k in range(rng.randint(7, 11)):
        a = k*2.39996+rng.uniform(-.25, .25)
        compound(p, [0, 0, .008], radial(a, rng.uniform(.25, .65)),
                 rng.uniform(.12, .21), rng, pairs=rng.randint(4, 8), fern=True)
    if stage == "leafy":
        return
    for k in range(rng.randint(2, 3)):
        a = k*2.4+rng.uniform(-.5, .5); h = rng.uniform(.27, .39)
        fork = radial(a)*.04+[0, 0, h*.75]
        axis(p, [0, 0, 0], fork, .0015)
        for j in range(3):
            phi = a+(j-1)*1.4; side = radial(phi)
            tip = fork+side*rng.uniform(.035, .07)+[0, 0, h*.25]
            if stage == "flowering":
                hook = tip+side*.017+[0, 0, -.020]
                axis(p, fork, hook, .001, tip+[0, 0, .045])
                for b in range(5):
                    p.leaf(hook, radial(b*2*np.pi/5, -1.4), .019, .008,
                           role="flower", veins=False, bend=0)
                p.organs.append({"type": "nodding_flower", "position": hook.tolist()})
            else:
                axis(p, fork, tip, .001)
                for n in range(28):
                    phi2 = n*2.39996; r = rng.uniform(.015, .045)
                    end = tip+radial(phi2)*r+[0, 0, rng.uniform(.04, .085)]
                    line = bezier(tip, tip+(end-tip)*.6+side*.012, end, 13)
                    p.line(line, "seed")
                    for q in (5, 8, 10):
                        for sign in (-1, 1):
                            p.line([line[q], line[q]+radial(phi2+sign*1.2)*.004+[0, 0, .004]], "hair", 2)
                p.organs.append({"type": "upright_plumes", "position": tip.tolist()})


def bergamot_head(p, centre, rng, stage):
    c = np.asarray(centre)
    for j in range(8):
        p.leaf(c-[0, 0, .006], radial(j*np.pi/4, -.2), .021, .007,
               role="bract", veins=False, bend=-.1)
    for j in range(65):
        phi = j*2.39996; r = .016*np.sqrt((j+.5)/65)
        pt = c+radial(phi)*r+[0, 0, .007*np.sqrt(max(0, 1-(r/.017)**2))]
        if stage == "flowering":
            end = pt+radial(phi)*.012+[0, 0, rng.uniform(.015, .025)]
            p.line(bezier(pt, end+[0, 0, -.007], end, 7), "flower")
            p.line([end, end+radial(phi)*.003+[0, 0, .003], end+radial(phi+1)*.004], "flower")
        else:
            p.line([pt, pt+[0, 0, .006], pt+radial(phi)*.002+[0, 0, .006]], "seed")
    p.organs.append({"type": "terminal_head", "position": c.tolist()})


def wild_bergamot(p, rng, stage):
    for k in range(rng.randint(3, 5)):
        a = k*2.4; h = rng.uniform(.56, .91)
        end = radial(a)*rng.uniform(.045, .12)+[0, 0, h]
        stem = axis(p, [0, 0, 0], end, .002, end*[.35, .35, .65])
        for j, t in enumerate(np.linspace(.22, .83, 5)):
            q = stem[round(t*(len(stem)-1))]; phi = a+j*np.pi/2
            if stage == "flowering":
                for sign in (-1, 1):
                    p.leaf(q, sign*radial(phi)+[0, 0, .35],
                           rng.uniform(.06, .11)*(1-t*.30), .025,
                           shape="toothed", roll=sign*rng.uniform(.65, 1.25), bend=-.18)
            if j == 3 and rng.random() < .8:
                head = q+radial(phi)*.09+[0, 0, h*.21]
                axis(p, q, head, .001)
                bergamot_head(p, head, rng, stage)
        bergamot_head(p, end, rng, stage)


def bur_oak(p, rng, stage):
    """Open-grown young oak: broad, low forks and irregular ascending twigs.

    This first grammar draws a young tree, not a measured mature-tree crown.
    The leaf is a lobed bur-oak cue; acorns and corky twigs are future work.
    """
    top = np.array([rng.uniform(-.12, .12), rng.uniform(-.08, .08), .95])
    axis(p, [0, 0, 0], top, .075, top*[.1, .1, .6], True)

    def branch(base, direction, length, radius, depth):
        d = unit(direction); end = base+d*length
        mid = (base+end)/2+np.array([rng.uniform(-.08, .08), rng.uniform(-.06, .06), -.05])*length
        stem = axis(p, base, end, radius, mid, depth > 1)
        if depth:
            n = rng.randint(2, 3)
            for j in range(n):
                q = stem[rng.randint(10, 16)]
                phi = np.arctan2(d[1], d[0])+(j-(n-1)/2)*rng.uniform(.65, 1.0)
                direction2 = radial(phi, rng.uniform(.5, 1.4))
                branch(q, direction2, length*rng.uniform(.53, .72), radius*.51, depth-1)
        elif stage == "leafy":
            count = rng.randint(5, 8)
            for j in range(count):
                t = .25+.75*j/(count-1); q = stem[min(17, round(t*17))]
                phi = np.arctan2(d[1], d[0])+j*2.4
                # Alternate leaves, with short actual petioles.
                dr = radial(phi, rng.uniform(.15, .75)); pet = q+unit(dr)*.025
                axis(p, q, pet, .001)
                p.leaf(pet, dr, rng.uniform(.15, .24), rng.uniform(.085, .135),
                       shape="oak", roll=rng.uniform(.35, 1.25)*(-1 if j%2 else 1), bend=-.25)
    for k in range(rng.randint(5, 7)):
        phi = k*2.39996+rng.uniform(-.25, .25)
        q = top*rng.uniform(.48, .95)
        branch(q, radial(phi, rng.uniform(.35, .95)), rng.uniform(.75, 1.1), .039, 2)


def generate(species, seed=1, *, stage=None, vigor=1.0, wind=0.0):
    if species not in SPECIES:
        raise ValueError(f"unknown species {species!r}; choose {', '.join(SPECIES)}")
    info = SPECIES[species]; stage = stage or info["stages"][0]
    if stage not in info["stages"]:
        raise ValueError(f"{species} stages: {', '.join(info['stages'])}")
    if not np.isfinite(vigor) or not .4 <= vigor <= 1.6:
        raise ValueError("vigor must be between 0.4 and 1.6")
    if not np.isfinite(wind) or not -1 <= wind <= 1:
        raise ValueError("wind must be between -1 and 1")
    if not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    p = Plant(dict(species=species, **info, seed=seed, stage=stage, vigor=vigor,
                   wind=wind, generator_version="0.1.0", units="metres"))
    rng = random.Random(seed)
    if species in ("little_bluestem", "side_oats_grama"):
        grass(p, rng, stage, species == "side_oats_grama")
    else:
        {"leadplant": leadplant, "prairie_smoke": prairie_smoke,
         "wild_bergamot": wild_bergamot, "bur_oak": bur_oak}[species](p, rng, stage)
    height = max(p.points()[:, 2].max(), .1)
    def deform(points):
        q = points.copy()*vigor
        q[:, 0] += wind*.22*q[:, 2]**2/(height*vigor)
        return q
    return p.transform(deform)
