"""Validate exported paths and make compact review sheets (not plot layers)."""
from pathlib import Path
import argparse,json,re,hashlib
import xml.etree.ElementTree as ET
from PIL import Image,ImageOps,ImageDraw,ImageFont


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,default=Path(__file__).parent/'output');args=ap.parse_args();out=args.out
    metrics=json.loads((out/'metrics.json').read_text());results={}
    for name,entry in metrics.items():
        path=out/(name+'.svg');root=ET.parse(path).getroot();w,h=entry['page_mm'];count=0
        for el in root.iter():
            tag=el.tag.split('}')[-1]
            if tag in ('image','mask','clipPath','text','rect','polygon'):raise AssertionError((name,tag))
            if tag=='g':assert el.attrib['fill']=='none'
            if tag=='path':
                q=list(map(float,re.findall(r'-?\d+(?:\.\d+)?',el.attrib['d'])))
                assert len(q)%2==0 and len(q)>=4
                assert all(0<=x<=w for x in q[::2]) and all(0<=y<=h for y in q[1::2]),name
                count+=1
        assert count==sum(v['paths'] for v in entry['layers'].values())
        with Image.open(out/(name+'.png')) as im:im.load()
        results[name]=dict(paths=count,bounds=True,stroke_only=True,png_integrity=True,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    try:font=ImageFont.truetype('DejaVuSans.ttf',21)
    except OSError:font=ImageFont.load_default()
    cards=[('barn-22-d72','Timber barn'),('tractor-23-d72','Open-seat tractor'),('disk_harrow-24-d72','Disk harrow'),('hay_rake-25-d72','Dump hay rake'),('wagon-26-d72','Slatted wagon'),('barn-22-d90','Barn / heavy decay')]
    if all(n in metrics for n,_ in cards):
        sheet=Image.new('RGB',(1500,1100),'#f7f2e8');d=ImageDraw.Draw(sheet)
        for i,(name,label) in enumerate(cards):
            x=(i%3)*500;y=(i//3)*550
            q=ImageOps.contain(Image.open(out/(name+'.png')).convert('RGB'),(490,450))
            sheet.paste(q,(x+(500-q.width)//2,y+(450-q.height)//2+20));d.text((x+25,y+493),label,fill='#24251f',font=font)
        sheet.save(out/'sampler.jpg',quality=91)
    if 'farmyard' in metrics:
        Image.open(out/'farmyard.png').convert('RGB').save(out/'farmyard.jpg',quality=91)
    names=['barn-22-d00','barn-22-d38','barn-22-d90']
    if all(n in metrics for n in names):
        sheet=Image.new('RGB',(1800,500),'#f7f2e8');d=ImageDraw.Draw(sheet)
        for i,name in enumerate(names):
            q=ImageOps.contain(Image.open(out/(name+'.png')).convert('RGB'),(590,430));sheet.paste(q,(i*600+(600-q.width)//2,0))
            d.text((i*600+25,450),'Same seed / decay '+name[-2:]+'%',fill='#24251f',font=font)
        sheet.save(out/'decay-comparison.jpg',quality=91)
    (out/'validation.json').write_text(json.dumps(dict(plates=results,physical_plot=False,native_blender=False),indent=2)+'\n')
    print(f'{len(results)} SVGs passed bounds/layer/path checks; PNGs decoded fully.')

if __name__=='__main__':main()
