"""Blender backend: evaluated architecture, volume foliage, Geometry Nodes and cameras.

Run with Blender 4.5 LTS or the official bpy wheel. INFERNAL_CASE selects a
compiled specimen; INFERNAL_TERRAIN a prepared erosion state. Every primitive
comes from `geometry.py`, so the scene grammars never touch bpy. This backend
mirrors each mesh into Blender, lets Geometry Nodes repeat the duration modules
and the Displace modifier roughen the terrain, exports the evaluated meshes, and
checks that the realised repetition equals the builder's own instancing.
"""
from pathlib import Path
import json, os
import bpy
import numpy as np
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
import geometry as G
import scene as S


class BlenderBuilder(G.SceneBuilder):
    def __init__(self, architecture, terrain_z, scene_name):
        self.SC = bpy.data.scenes.new(scene_name); bpy.context.window.scene = self.SC
        self.bpy_materials = []; self.records = {}; self._mirror = True; self.name_mismatches = []
        super().__init__(architecture, terrain_z)

    def material(self, name, color, roughness=.88):
        index = super().material(name, color, roughness)
        m = bpy.data.materials.new('IE | ' + name)
        m.diffuse_color = tuple(int(color[k:k + 2], 16) / 255 for k in (1, 3, 5)) + (1.,)
        m.use_nodes = True
        p = m.node_tree.nodes.get('Principled BSDF')
        p.inputs['Base Color'].default_value = m.diffuse_color
        p.inputs['Roughness'].default_value = roughness
        self.bpy_materials.append(m)
        return index

    def _object(self, rec, verts, faces, mat):
        # Blender deduplicates object names itself; the builder predicts the
        # same .001 suffixes so the dry run's records read like this one's.
        me = bpy.data.meshes.new(rec['base_name']); me.from_pydata(verts, [], faces); me.update()
        o = bpy.data.objects.new(rec['base_name'], me)
        if rec['link']: self.SC.collection.objects.link(o)
        o.data.materials.append(self.bpy_materials[mat]); o['hatch'] = rec['hatch']; o['material_id'] = mat
        if o.name != rec['name']: self.name_mismatches.append((rec['name'], o.name))
        rec['object'] = o; rec['name'] = o.name; self.records[o.name] = rec
        return o

    def mesh(self, name, verts, faces, mat=1, hatch=True, link=True, kind='sheet'):
        rec = super().mesh(name, verts, faces, mat, hatch, link, kind)
        if self._mirror:
            self._object(rec, [tuple(v) for v in rec['verts']], rec['faces'], mat if isinstance(mat, int) else 1)
        return rec

    def terrain_grid(self, gx, gy):
        rec = super().terrain_grid(gx, gy)
        tex = bpy.data.textures.new('Stone undulation', type='CLOUDS'); tex.noise_scale = 2.3; tex.noise_depth = 1
        mod = rec['object'].modifiers.new('Evaluated ground detail', 'DISPLACE')
        mod.texture = tex; mod.strength = .08; mod.mid_level = .5
        return rec

    def repeat(self, host_name, module, count, offset, location, *, group_name, modifier_name, props=None):
        """The module becomes an unlinked source object; a Geometry Nodes tree
        on the host instances it `Bays` times along `offset` and realises it."""
        self._mirror = False
        try:
            rec = super().repeat(host_name, module, count, offset, location, group_name=group_name,
                                 modifier_name=modifier_name, props=props)
        finally:
            self._mirror = True
        me = bpy.data.meshes.new(module.name); me.from_pydata(module.verts, [], module.faces); me.update()
        for m in self.bpy_materials: me.materials.append(m)
        for p, i in zip(me.polygons, module.mats): p.material_index = i
        source = bpy.data.objects.new(host_name.split(' | ')[0] + ' | unlinked bay source', me)
        host = self._object(rec, [], [], 1); host.location = tuple(location)
        g = bpy.data.node_groups.new(group_name, 'GeometryNodeTree')
        s = g.interface.new_socket(name='Bays', in_out='INPUT', socket_type='NodeSocketInt')
        s.default_value = count; s.min_value = 1; s.max_value = 24
        g.interface.new_socket(name='Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
        n = g.nodes; l = g.links; i = n.new('NodeGroupInput'); i.location = (-600, 100)
        line = n.new('GeometryNodeMeshLine'); line.mode = 'OFFSET'; line.location = (-380, 100)
        line.inputs['Offset'].default_value = tuple(offset); l.new(i.outputs['Bays'], line.inputs['Count'])
        info = n.new('GeometryNodeObjectInfo'); info.location = (-380, -150); info.inputs['Object'].default_value = source
        inst = n.new('GeometryNodeInstanceOnPoints'); inst.location = (-100, 100)
        l.new(line.outputs['Mesh'], inst.inputs['Points']); l.new(info.outputs['Geometry'], inst.inputs['Instance'])
        real = n.new('GeometryNodeRealizeInstances'); real.location = (150, 100); l.new(inst.outputs['Instances'], real.inputs['Geometry'])
        out = n.new('NodeGroupOutput'); out.location = (400, 100); l.new(real.outputs['Geometry'], out.inputs['Geometry'])
        host.modifiers.new(modifier_name, 'NODES').node_group = g
        for k, v in (props or {}).items(): host[k] = v
        rec['bays_socket'] = s.identifier
        return rec

    def camera(self, name, eye, target, focal):
        super().camera(name, eye, target, focal)
        d = bpy.data.cameras.new('IE ' + name); ob = bpy.data.objects.new('Camera ' + name, d)
        self.SC.collection.objects.link(ob)
        ob.location = eye; ob.rotation_euler = (Vector(target) - ob.location).to_track_quat('-Z', 'Y').to_euler()
        d.type = 'PERSP'; d.sensor_fit = 'HORIZONTAL'; d.sensor_width = 36; d.lens = focal * 36 / self.W
        d.clip_start = .25; d.clip_end = 300

    def finish(self):
        SC = self.SC
        SC.render.resolution_x = self.W; SC.render.resolution_y = self.H; SC.render.resolution_percentage = 100
        SC.render.pixel_aspect_x = SC.render.pixel_aspect_y = 1; SC.camera = bpy.data.objects['Camera main']
        sun_data = bpy.data.lights.new('Low afternoon sun', 'SUN'); sun_data.energy = 2.1; sun_data.angle = .035
        sun = bpy.data.objects.new('Low afternoon sun', sun_data); SC.collection.objects.link(sun)
        sun.rotation_euler = Vector((10, 8, -9)).to_track_quat('-Z', 'Y').to_euler()
        world = bpy.data.worlds.new('Warm sky'); world.use_nodes = True
        world.node_tree.nodes['Background'].inputs[0].default_value = (.73, .77, .85, 1)
        world.node_tree.nodes['Background'].inputs[1].default_value = .5; SC.world = world
        SC.render.engine = 'CYCLES'; SC.cycles.device = 'CPU'; SC.cycles.samples = 12; SC.cycles.use_denoising = True
        SC.render.threads_mode = 'FIXED'; SC.render.threads = 4; SC.view_settings.view_transform = 'Standard'

    def evaluate(self):
        """Export the evaluated meshes, including Geometry Nodes and Displace, once."""
        bpy.context.view_layer.update(); deps = bpy.context.evaluated_depsgraph_get()
        vertices = []; faces = []; mats = []; normals = []; names = []; hatch = []; terrain_faces = []; objects = []
        material_names = [m.name for m in self.bpy_materials]; terrain = self.terrain['object']; self.realisation = []
        for ob in self.SC.objects:
            if ob.type != 'MESH': continue
            ev = ob.evaluated_get(deps); me = ev.to_mesh(); off = len(vertices)
            world = [list(ev.matrix_world @ v.co) for v in me.vertices]; vertices.extend(world)
            for p in me.polygons:
                k = len(faces); faces.append([off + i for i in p.vertices])
                mat = me.materials[p.material_index] if len(me.materials) else ob.data.materials[0]
                mats.append(material_names.index(mat.name))
                normals.append(list((ev.matrix_world.to_3x3().inverted().transposed() @ p.normal).normalized()))
                names.append(ob.name); hatch.append(bool(ob.get('hatch', True)))
                if ob == terrain: terrain_faces.append(k)
            rec = self.records.get(ob.name, {})
            objects.append(dict(name=ob.name, kind=rec.get('kind', 'sheet'), faces=len(me.polygons)))
            if rec.get('kind') == 'module':
                # The realised repetition must be the builder's own instancing:
                # the same vertices (to float32) in the same order, the same faces.
                mine = rec['verts']; got = np.asarray(world, float)
                same_faces = [list(p.vertices) for p in me.polygons] == [list(f) for f in rec['faces']]
                error = float(np.abs(got - mine).max()) if len(got) == len(mine) and len(got) else float('inf')
                self.realisation.append(dict(name=ob.name, faces=len(me.polygons), realised_matches_numpy=bool(same_faces and error < 1e-4),
                                             max_vertex_error=error, bays_socket=rec.get('bays_socket')))
            ev.to_mesh_clear()
        return dict(vertices=vertices, faces=faces, materials=mats, normals=normals, names=names, hatch=hatch,
                    terrain_faces=terrain_faces, objects=objects)

    def export(self, **kw):
        data = self.record(self.evaluate(), backend='blender', blender=bpy.app.version_string,
                           terrain_modifier=dict(type='DISPLACE', strength=.08), **kw)
        data['geometry_nodes'] = self.realisation
        return data


ctx = S.context(); CASE, OUT, A = ctx['case'], ctx['out'], ctx['A']
B = BlenderBuilder(A, ctx['terrain_z'], 'Infernal Engine | ' + CASE)
extras = S.assemble(B, ctx); B.finish()
data = B.export(footprints=extras['footprints'], routes=extras['routes'], terrain_mode=ctx['terrain_mode'],
                planar_trees=extras['planar_trees'], terrain_state=ctx['state'])
(OUT / 'scene.json').write_text(json.dumps(data, separators=(',', ':')))
SC = B.SC; W, H = B.W, B.H; errors = []
for name, c in B.cameras.items():
    cam = bpy.data.objects['Camera ' + name]; eye = np.array(c['eye'], float); fwd = np.array(c['target'], float) - eye; fwd /= np.linalg.norm(fwd)
    right = np.cross(fwd, [0, 0, 1]); right /= np.linalg.norm(right); up = np.cross(right, fwd)
    def page(p):
        q = np.array(p) - eye; z = q @ fwd
        if z <= 0: return False
        x, y = W / 2 + c['focal_px'] * (q @ right) / z, H / 2 - c['focal_px'] * (q @ up) / z
        return 0 <= x <= W and 0 <= y <= H
    # The four reference points lie on the estate cameras' pages. A closer
    # camera (the plate studies') sees few or none of them; far off its page
    # or near its lens, Blender's single-precision projection departs by
    # thousandths of a pixel, so it is measured beside its own target instead.
    refs = [p for p in [(-7, 5, 3), (3, 8, 5), (0, 16, 2), (7, -2, .5)] if page(p)]
    t = np.array(c['target'], float)
    refs += [tuple(t + right * a + up * b) for a, b in ((-1.5, -1.), (1.5, -1.), (1.5, 1.), (-1.5, 1.))][:4 - len(refs)]
    for p in refs:
        q = np.array(p) - eye; z = q @ fwd
        xy = np.array([W / 2 + c['focal_px'] * (q @ right) / z, H / 2 - c['focal_px'] * (q @ up) / z])
        uv = world_to_camera_view(SC, cam, Vector(p)); errors.append(float(np.max(abs(np.array([uv.x * W, (1 - uv.y) * H]) - xy))))
(OUT / 'blender-checks.json').write_text(json.dumps(dict(backend='blender', blender=bpy.app.version_string, evaluated_faces=len(data['faces']),
      native_camera_max_error_px=max(errors), geometry_nodes=B.realisation,
      object_name_mismatches=B.name_mismatches, outward_audit=G.outward_audit(data)), indent=2))
SC['architecture_json'] = json.dumps(A); SC['printed_width_mm'] = 156
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / ('Infernal_' + CASE + '.blend')), compress=True)
if os.environ.get('INFERNAL_RENDER', '1') != '0':
    SC.render.resolution_percentage = 38; SC.render.filepath = str(OUT / 'clay.png'); bpy.ops.render.render(write_still=True)
print(json.dumps(dict(case=CASE, faces=len(data['faces']), native_camera_max_error=max(errors),
                      geometry_nodes=B.realisation)), flush=True)
