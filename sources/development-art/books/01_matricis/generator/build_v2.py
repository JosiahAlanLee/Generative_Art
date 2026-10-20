from portable_paths import OUTPUT
import sys, json
from layout import box_height
from preview import compose

def viii():
    import v2_viii as V
    svg, meta = V.build_face()
    bx = V.face_boxes(meta)
    D = V.DY; AX = V.AX
    keep = []
    for b in bx:
        if b.get('rot'): keep.append((60, b['y']-D+9-b['w']/2, 92, b['y']-D+9+b['w']/2)); continue
        keep.append((b['x'], b['y']-D, b['x']+b['w'], b['y']-D+box_height(b)))
    keep += [(AX-112, 240, AX+112, 1060), (AX-152, 690, AX+152, 762), (AX-112, 262, AX+112, 322),
             (86, meta['yN']-24, 116, meta['yD']+24), (884, meta['yD']-24, 918, meta['yGr']+24), (300, 780, 470, 850),
             (100, 1010, 900, 1070), (290, 270, 360, 312), (170, 860, 410, 905)]
    for (x, y) in meta['route']: keep.append((x-30, y-30, x+30, y+30))
    far = max(meta['route'], key=lambda p: p[0]); keep.append((far[0], far[1]-50, far[0]+80, far[1]+50))
    svg, meta = V.build_face(keep=keep)
    open(f'{OUTPUT}/v2_viii_face.svg','w').write(svg)
    vs, vb, vmeta = V.build_verso()
    open(f'{OUTPUT}/v2_viii_verso.svg','w').write(vs)
    pal = {'red': V.RED, 'ink': V.INK}
    print(compose(svg, bx, pal, V.PAPER, 1000, 1600, 'v2_viii_face'))
    print(compose(vs, vb, pal, V.PAPER, 1000, 1600, 'v2_viii_verso'))
    json.dump({'face_boxes': bx, 'verso_boxes': vb}, open(f'{OUTPUT}/v2_viii_boxes.json','w'))
    print('verso cols', vmeta['y_cols'], 'dep', vmeta['y_dep'], 'key', vmeta['y_key'])

def iii():
    import v2_iii as V
    svg, meta = V.build_face()
    bx = V.face_boxes(meta)
    open(f'{OUTPUT}/v2_iii_face.svg','w').write(svg)
    pal = {'red': V.PENS['rr'], 'ink': V.PENS['dk']}
    print(compose(svg, bx, pal, V.PAPER, 1000, 1600, 'v2_iii_face'))
    vs, vb, vm = V.build_slip()
    open(f'{OUTPUT}/v2_iii_slip.svg','w').write(vs)
    print(compose(vs, vb, pal, V.PAPER, 1000, 1600, 'v2_iii_slip'))
    print('slip', vm, 'face bytes', len(svg))
    json.dump({'face_boxes': bx, 'slip_boxes': vb}, open(f'{OUTPUT}/v2_iii_boxes.json','w'))

def xiii():
    import v2_xiii as V
    svg, meta = V.build_face()
    bx = V.face_boxes(meta)
    open(f'{OUTPUT}/v2_xiii_face.svg','w').write(svg)
    pal = {'red': V.OCHRE, 'ink': V.MEAL}
    print(compose(svg, bx, pal, V.PAPER, 1000, 1600, 'v2_xiii_face'))
    vs, vb, vm = V.build_verso()
    open(f'{OUTPUT}/v2_xiii_verso.svg','w').write(vs)
    print(compose(vs, vb, {'red': V.Hd.RED, 'ink': V.Hd.INK}, '#ebe1c8', 1000, 1600, 'v2_xiii_verso'))
    ks, km = V.build_keyslip()
    kb = V.keyslip_boxes(km)
    open(f'{OUTPUT}/v2_keyslip.svg','w').write(ks)
    print(compose(ks, kb, {'red': V.Hd.RED, 'ink': V.Hd.INK}, '#ebe1c8', km['W'], km['H'], 'v2_keyslip'))
    print('verso', vm, 'face bytes', len(svg))
    json.dump({'face_boxes': bx, 'verso_boxes': vb, 'key_boxes': kb}, open(f'{OUTPUT}/v2_xiii_boxes.json','w'))

def ii():
    import ii as V
    svg, meta = V.build_face()
    bx = V.face_boxes(meta)
    open(f'{OUTPUT}/ii_face.svg','w').write(svg)
    pal = {'red': V.RED, 'ink': V.INK}
    print(compose(svg, bx, pal, V.PAPER, 1000, 1600, 'ii_face'))
    vs, vb, vm = V.build_verso()
    open(f'{OUTPUT}/ii_verso.svg','w').write(vs)
    print(compose(vs, vb, pal, V.PAPER, 1000, 1600, 'ii_verso'))
    json.dump({'face_boxes': bx, 'verso_boxes': vb}, open(f'{OUTPUT}/ii_boxes.json','w'))
    print(vm, len(svg))

def iv():
    import iv as V
    from PIL import Image, ImageDraw
    svg, meta = V.build_face()
    bx = V.face_boxes(meta)
    open(f'{OUTPUT}/iv_face.svg','w').write(svg)
    pal = {'red': V.Hd.RED, 'ink': V.Hd.INK}
    p = compose(svg, bx, pal, V.PAPER, 1000, 1600, 'iv_face')
    im = Image.open(p); d = ImageDraw.Draw(im, 'RGBA')
    x, y, w, h = meta['patch']; d.rectangle([x, y, x+w, y+h], fill=(231,222,200,245))
    im.save(p.replace('.png', '_patched.png'))
    vs, vb, vm = V.build_verso()
    open(f'{OUTPUT}/iv_verso.svg','w').write(vs)
    print(compose(vs, vb, pal, V.PAPER, 1000, 1600, 'iv_verso'))
    json.dump({'face_boxes': bx, 'verso_boxes': vb, 'patch': meta['patch']}, open(f'{OUTPUT}/iv_boxes.json','w'))
    print(p, len(svg))

def vi():
    import vi as V, re
    svg, meta = V.build_inside()
    bx = V.inside_boxes(meta)
    open(f'{OUTPUT}/vi_inside.svg','w').write(svg)
    pal = {'red': V.PENS['rr'], 'ink': V.PENS['dk']}
    # preview: the closed tab laid over the plate, as the artboard shows it before it is lifted
    tx0, ty0, tw, th = V.TAB
    tab_inner = re.sub(r'^<svg[^>]*>', '', V.tab_svg()).rsplit('</svg>', 1)[0]
    over = (f'<rect x="{tx0+2}" y="{ty0+4}" width="{tw}" height="{th}" fill="#7a6a4e" opacity="0.25"/>'
            f'<rect x="{tx0}" y="{ty0}" width="{tw}" height="{th}" fill="#fbf7ec"/>'
            f'<g transform="translate({tx0},{ty0})">{tab_inner}</g>')
    closed = svg.rsplit('</svg>', 1)[0] + over + '</svg>'
    print(compose(closed, bx, pal, V.PAPER, V.W2, V.H2, 'vi_inside'))
    print(compose(svg, bx, pal, V.PAPER, V.W2, V.H2, 'vi_inside_lifted'))
    os_, om = V.build_outside(meta)
    ob = V.outside_boxes()
    open(f'{OUTPUT}/vi_outside.svg','w').write(os_)
    print(compose(os_, ob, pal, V.PAPER, V.WO, V.HO, 'vi_outside'))
    json.dump({'inside_boxes': bx, 'outside_boxes': ob, 'res': meta['res']}, open(f'{OUTPUT}/vi_boxes.json','w'))
    print('residuals', [round(r, 2) for r in meta['res']], 'bytes', len(svg))

def xi():
    import xi as V
    svg, meta = V.build_face()
    bx = V.face_boxes(meta)
    open(f'{OUTPUT}/xi_face.svg','w').write(svg)
    pal = {'red': V.RED, 'ink': V.INK}
    print(compose(svg, bx, pal, V.PAPER, 1000, 1600, 'xi_face'))
    vs, vb, vm = V.build_verso()
    open(f'{OUTPUT}/xi_verso.svg','w').write(vs)
    print(compose(vs, vb, pal, V.PAPER, 1000, 1600, 'xi_verso'))
    sb = {}
    for side in ('front', 'back'):
        ss, sm = V.build_strip(side)
        b = V.strip_boxes(side, sm)
        sb[side] = b
        open(f'{OUTPUT}/xi_strip_{side}.svg','w').write(ss)
        print(compose(ss, b, pal, V.STRIP_PAPER, V.STRIP_W, V.STRIP_H, f'xi_strip_{side}'))
    json.dump({'face_boxes': bx, 'verso_boxes': vb, 'strip_front': sb['front'], 'strip_back': sb['back']},
              open(f'{OUTPUT}/xi_boxes.json','w'))
    ct = V.transpose("UNKNOWN IS NOT ABSENT.")
    print('cipher', ct, ct == V.CIPHER, 'decode', V.untranspose(V.CIPHER), 'letters', sum(c.isalpha() for c in V.CIPHER),
          'pads', V.CIPHER.count('.'), 'bytes', len(svg))

def slips():
    import slips as V
    pal = {'red': V.Hd.RED, 'ink': V.Hd.INK}
    ks, km = V.build_keyproof()
    kb = V.keyproof_boxes(km)
    open(f'{OUTPUT}/keyproof.svg','w').write(ks)
    print(compose(ks, kb, pal, V.SLIP_BG, V.KW, V.KH, 'keyproof'))
    hs, hm = V.build_h()
    hb = V.h_boxes(hm)
    open(f'{OUTPUT}/slip_h.svg','w').write(hs)
    print(compose(hs, hb, pal, V.H_MOUNT, V.HW, V.HH, 'slip_h'))
    is_, im = V.build_i()
    ib = V.i_boxes(im)
    open(f'{OUTPUT}/slip_i.svg','w').write(is_)
    print(compose(is_, ib, pal, V.H_MOUNT, V.IW, V.IH, 'slip_i'))
    json.dump({'key_boxes': kb, 'h_boxes': hb, 'i_boxes': ib}, open(f'{OUTPUT}/slips_boxes.json','w'))
    import tx
    print(tx.codes(V.EX), tx.decode(tx.encode(V.EX)))

if __name__ == '__main__':
    globals()[sys.argv[1]]()
