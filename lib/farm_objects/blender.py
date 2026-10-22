"""Blender adapter; run with Blender 4.5+ or its official bpy Python package.

Creates a new collection. Does not delete, reset, or overwrite an existing scene.
Surface marks are bevel-free 3D POLY curves for editing and downstream projection.
"""
from pathlib import Path
import json


def import_record(record, name='Farm remnants'):
    import bpy
    collection=bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(collection)
    colors=record.get('colors', ['#bfb79d','#bcb29b','#716b53','#8d4e39','#6e7165','#dbceb2','#4e6450'])
    materials=[]
    for i,color in enumerate(colors):
        m=bpy.data.materials.new(f'{name} material {i}')
        m.diffuse_color=tuple(int(color[j:j+2],16)/255 for j in (1,3,5))+(1.,)
        materials.append(m)
    by_name={}
    for i,n in enumerate(record['names']):by_name.setdefault(n,[]).append(i)
    for n,indices in by_name.items():
        faces=[record['faces'][i] for i in indices]
        old=sorted({v for f in faces for v in f});lookup={v:k for k,v in enumerate(old)}
        mesh=bpy.data.meshes.new(n)
        mesh.from_pydata([record['vertices'][i] for i in old],[],[[lookup[v] for v in f] for f in faces]);mesh.update()
        obj=bpy.data.objects.new(n,mesh);collection.objects.link(obj)
        for m in materials:mesh.materials.append(m)
        for p,i in zip(mesh.polygons,indices):p.material_index=record['materials'][i]
        obj['farm_hatch']=bool(record['hatch'][indices[0]])
    curves={}
    for s in record['strokes']:
        pen=int(s['ink'])
        if pen not in curves:
            curve=bpy.data.curves.new(f'{name} pen {pen}',type='CURVE');curve.dimensions='3D'
            obj=bpy.data.objects.new(curve.name,curve);collection.objects.link(obj)
            obj['plotter_pen']=pen;curves[pen]=curve
        spline=curves[pen].splines.new('POLY');spline.points.add(len(s['pts'])-1)
        for point,xyz in zip(spline.points,s['pts']):point.co=(*xyz,1.)
    collection['farm_parameters']=json.dumps(record.get('metadata',{}))
    return collection


def main():
    import argparse,sys,bpy
    ap=argparse.ArgumentParser();ap.add_argument('record',type=Path);ap.add_argument('--save',type=Path)
    args=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:])
    import_record(json.loads(args.record.read_text()),args.record.stem)
    if args.save:
        if args.save.exists():raise FileExistsError('Refusing to overwrite existing blend: '+str(args.save))
        bpy.ops.wm.save_as_mainfile(filepath=str(args.save.resolve()))

if __name__=='__main__':main()
