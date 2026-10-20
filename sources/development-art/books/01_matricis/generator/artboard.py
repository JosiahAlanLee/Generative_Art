from portable_paths import OUTPUT
import sys, json, html as H
from layout import html_box, WEB

FONTS = {
 1: "https://fonts.googleapis.com/css2?family=IM+Fell+English:ital@0;1&amp;family=IM+Fell+English+SC&amp;family=IM+Fell+DW+Pica:ital@0;1&amp;family=IM+Fell+DW+Pica+SC&amp;display=swap",
 2: "https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,500;1,400&amp;display=swap",
 3: "https://fonts.googleapis.com/css2?family=DM+Serif+Display&amp;family=Spectral:ital@0;1&amp;family=Spectral+SC&amp;family=IBM+Plex+Mono:ital@0;1&amp;display=swap",
}

def page(n, title, boxes, pal, bg, ink, blob, alt, base_font):
    out = ['<!doctype html>', '<html lang="en">', '<head>', '<meta charset="utf-8">', f'<title>{H.escape(title)}</title>',
           '<script src="./support.js"></script>', '</head>', '<body>', '<x-dc>', '<helmet>',
           f'<link rel="stylesheet" href="{FONTS[n]}">', '<style>', 'body{margin:0}',
           f'a{{color:{pal["red"]}}}a:hover{{color:{ink}}}', '</style>', '</helmet>',
           f'<div style="position: relative; width: 1000px; height: 1600px; overflow: hidden; background: {bg}; color: {ink}; font-family: {WEB[base_font]}">',
           f'<img src="{blob}" alt="{H.escape(alt)}" style="position: absolute; left: 0px; top: 0px; width: 1000px; height: 1600px">']
    keyrow = [b for b in boxes if b['id'].startswith('key')]
    for b in boxes:
        if b['id'].startswith('key'):
            continue
        out.append(html_box(b, pal, indent=''))
    if keyrow:
        b0 = keyrow[0]
        spans = ''.join(f'<span style="flex: 1 1 0px; text-align: center">{H.escape(b["runs"][0][0])}</span>' for b in keyrow)
        out.append(f'<div style="position: absolute; left: 56px; top: {b0["y"]:.0f}px; width: 888px; display: flex; font-family: {WEB[b0["font"]]}; font-size: {b0["size"]}px; line-height: {b0["lh"]}px; color: {b0["color"]}; font-style: italic">{spans}</div>')
    out += ['</div>', '</x-dc>',
            '<script type="text/x-dc" data-dc-script data-props=\'{"$preview":{"width":1000,"height":1600}}\'>',
            'class Component extends DCLogic {', 'renderVals() {', 'return {};', '}', '}', '</script>', '</body>', '</html>']
    return '\n'.join(out)

if __name__ == '__main__':
    n = int(sys.argv[1])
    if n == 1:
        import text1, page1
        meta = json.load(open(f'{OUTPUT}/p1_meta.json'))
        print(page(1, 'Tabula VIII — Of an Outage Delayed by Authority', text1.boxes(meta), text1.PAL, page1.PAPER, page1.INK,
                   '/_blob/76289767766b580325e73a90ac2fc661',
                   'Engraved plate: an escalation route runs down from the NOC through a required gate and a horned executive triangle, waits on a ladder, then reaches technical dispatch, the field crew and the fiber break in the ground. A red added route leaves just below the NOC and arrives directly at dispatch. Rulers mark the two measured intervals; cipher inscriptions run up the margins.',
                   'IM FELL DW Pica'))
    if n == 2:
        import text2, page2
        _, meta = page2.build()
        print(page(2, 'Tabula XIII — Of the Twelve Marks and the Mark', text2.boxes(meta), text2.PAL, page2.EARTH, page2.MEAL,
                   '/_blob/16b70e1f4df5768cc3585d14df34f525',
                   'Twelve seals drawn as if in cornmeal on dark earth, one for each sketching mark, each ringed with its meaning in the cipher hand; below, a great seal holding the open, branching spiral in red ochre, ringed with two inscriptions, and a key to the cipher alphabet.',
                   'EB Garamond'))
    if n == 3:
        import text3, page3
        print(page(3, 'Tabula III — Of the Speed of Correction', text3.boxes({}), text3.PAL, page3.PAPER, page3.PENS['dk'],
                   '/_blob/3045512fc5b04d49a8f420ccb0997fe5',
                   'A plotter drawing: a horned figure with raised arms and a spiral on its torso stands in a square divided into sixteen triangular cells. Each cell’s hatching density follows the number it carries; the two cells of unknowns are marked with hollow circles instead of hatching. A cipher inscription runs around the frame.',
                   'Spectral'))
