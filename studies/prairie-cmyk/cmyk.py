"""Four process-ink vector separations and a subtractive composite.

The CMYK TIFF stores the exact rendered separation values; it is device CMYK,
without an output profile. The SVG preserves editable ink groups. Its RGB ink
colours and multiply style are a viewing convention, not a press profile.
"""
from pathlib import Path
import io,json
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import cairosvg

INKS=[('C','#00a9d5'),('M','#e64a91'),('Y','#f5d800'),('K','#242321')]
NS='http://www.inkscape.org/namespaces/inkscape'

def simplify(p,tol=.12):
    p=np.asarray(p,float)
    if len(p)<3:return p
    keep=np.zeros(len(p),bool);keep[[0,-1]]=True;stack=[(0,len(p)-1)]
    while stack:
        a,b=stack.pop()
        if b-a<2:continue
        d=p[b]-p[a];q=p[a+1:b]-p[a];den=d@d
        t=np.clip(q@d/den,0,1) if den>1e-20 else np.zeros(len(q))
        err=np.sum((q-t[:,None]*d)**2,axis=1);j=int(np.argmax(err))
        if err[j]>tol*tol:k=a+1+j;keep[k]=True;stack.extend([(a,k),(k,b)])
    return p[keep]

def write(out,name,groups,W,H):
    """groups: (label, [(xy,width),...], (C,M,Y,K) ink strengths)."""
    out=Path(out);head=f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="{NS}" width="300mm" height="{300*H/W:.4f}mm" viewBox="0 0 {W} {H}">'
    encoded=[]
    for label,paths,values in groups:
        rows=[]
        for p,w in paths:
            p=simplify(p)
            if len(p)>1:rows.append(f'<path stroke-width="{w:.3f}" d="M'+ ' L'.join(f'{x:.2f},{y:.2f}' for x,y in p)+'"/>')
        encoded.append((label,rows,values))
    arrays=[];svgs=[];counts={}
    for ink,(letter,col) in enumerate(INKS):
        body=[];count=0
        for label,rows,values in encoded:
            strength=values[ink]
            if strength<=0:continue
            body.append(f'<g data-source="{label}" stroke-opacity="{strength:.3f}">')
            body.extend(rows);body.append('</g>');count+=len(rows)
        attributes='fill="none" stroke-linecap="round" stroke-linejoin="round"'
        mono=head+f'<g {attributes} stroke="black">'+''.join(body)+'</g></svg>'
        (out/f'{name}_{letter}.svg').write_text(mono)
        png=cairosvg.svg2png(bytestring=mono.encode(),output_width=W,output_height=H,background_color='white')
        mask=255-np.asarray(Image.open(io.BytesIO(png)).convert('L'))
        arrays.append(mask);Image.fromarray(255-mask).save(out/f'{name}_{letter}.png')
        svgs.append(f'<g inkscape:groupmode="layer" inkscape:label="{letter} process ink" {attributes} stroke="{col}" style="mix-blend-mode:multiply">'+''.join(body)+'</g>')
        counts[letter]=count
    (out/f'{name}.svg').write_text(head+'<title>Prairie bluffs and oaks - CMYK separations</title><g style="isolation:isolate">'+''.join(svgs)+'</g></svg>')
    coverage=np.stack(arrays,axis=-1).astype(np.uint8)
    tif=Image.fromarray(coverage,'CMYK');tif.save(out/f'{name}.tif',compression='tiff_lzw',dpi=(W/(300/25.4),W/(300/25.4)))
    # The screen preview is computed directly from the four ink arrays. A warm
    # paper base does not change the white-paper CMYK TIFF or channel masks.
    ink=coverage.astype(float)/255
    rgb=(1-ink[...,:3])*(1-ink[...,3,None])
    rgb*=np.array([.975,.958,.915])
    Image.fromarray(np.rint(np.clip(rgb,0,1)*255).astype('uint8')).save(out/f'{name}.png')
    return {'paths_per_ink':counts,'mode':tif.mode,'separation_frame':[W,H],
            'maximum_total_ink':float(ink.sum(axis=-1).max()),'output_profile':None}

def sheet(out,name):
    out=Path(out);W,H=1200,1000
    im=Image.new('RGB',(W,H),'#f9f4e8');d=ImageDraw.Draw(im)
    font=ImageFont.truetype(str(Path(__file__).parent/'vendor/fonts/IBMPlexMono-Regular.ttf'),24)
    for k,(letter,color) in enumerate(INKS):
        x=30+(k%2)*600;y=35+(k//2)*490
        d.text((x,y),letter+' / PROCESS INK',font=font,fill=color)
        mask=np.asarray(Image.open(out/f'{name}_{letter}.png').convert('L'),float)/255
        bg=np.ones((*mask.shape,3));col=np.array([int(color[i:i+2],16)/255 for i in [1,3,5]])
        rgb=mask[...,None]+(1-mask[...,None])*col
        tile=Image.fromarray(np.rint(rgb*255).astype('uint8'));tile.thumbnail((550,400))
        im.paste(tile,(x,y+52))
    im.save(out/f'{name}_Separations.png')
