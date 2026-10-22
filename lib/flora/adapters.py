"""Non-destructive bridges to Blender and the existing Infernal SceneBuilder."""
import numpy as np


def add_to_scene_builder(plant, builder, *, name='Wisconsin plant', material=6, detail=1):
    """Add true surfaces and ink to a caller-owned scene/camera.

    Works with studies/infernal-landscape/geometry.py SceneBuilder and its
    BlenderBuilder subclass. The receiving renderer owns final visibility.
    Surface hatching stays off: explicit leaf venation is the drawing texture.
    """
    records=[]
    for i, surface in enumerate(plant.surfaces):
        records.append(builder.mesh(f'{name} {surface.role} {i}', surface.vertices,
            surface.triangles, material, hatch=False,
            kind='beam' if surface.organ == 'axis' else 'leaf'))
    for i, stroke in enumerate(plant.strokes):
        if stroke.detail <= detail:
            builder.ink(f'{name} {stroke.role} {i}', stroke.points, mm=.16)
    return records


def to_blender(plant, *, scene=None, name=None, ink=False):
    """Create a new collection; never reset, delete or replace an existing scene.

    Returns the collection. Import bpy lazily so generation never needs Blender.
    Surface geometry is joined per organ role to keep the outliner manageable.
    """
    import bpy
    scene = scene or bpy.context.scene
    name = name or plant.metadata.get('common', 'Wisconsin plant')
    col = bpy.data.collections.new(name); scene.collection.children.link(col)
    for role in sorted({s.role for s in plant.surfaces}):
        verts=[]; faces=[]
        for s in plant.surfaces:
            if s.role != role:
                continue
            off=len(verts); verts.extend(s.vertices.tolist())
            faces.extend((s.triangles+off).tolist())
        mesh=bpy.data.meshes.new(name+' '+role); mesh.from_pydata(verts, [], faces); mesh.update()
        ob=bpy.data.objects.new(name+' '+role, mesh); col.objects.link(ob)
        for key in ('species', 'seed', 'stage', 'vigor', 'wind', 'generator_version'):
            if key in plant.metadata:
                ob[key]=plant.metadata[key]
    if ink:
        cu=bpy.data.curves.new(name+' full ink', 'CURVE'); cu.dimensions='3D'
        cu.bevel_depth=.0003; cu.bevel_resolution=0
        for s in plant.strokes:
            sp=cu.splines.new('POLY'); sp.points.add(len(s.points)-1)
            sp.points.foreach_set('co', np.c_[s.points, np.ones(len(s.points))].ravel())
        ob=bpy.data.objects.new(name+' full ink', cu); col.objects.link(ob)
        ob['note']='Unclipped model strokes; SVG visibility is camera dependent.'
    return col
