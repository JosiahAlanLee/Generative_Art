"""Reconstruct the supplied scene.json in Blender, with its matching camera.
Open this file in Blender's Scripting workspace and run. No add-ons required.
Not executed in the delivery environment, which has no Blender installation.
"""
from pathlib import Path
import json,math
import bpy
from mathutils import Vector

root=Path(__file__).resolve().parent
data=json.loads((root/'output/scene.json').read_text())
scene=bpy.data.scenes.new('Three Gates - hybrid study')
bpy.context.window.scene=scene
mesh=bpy.data.meshes.new('Three Gates mesh')
mesh.from_pydata(data['vertices'],[],data['faces']);mesh.update()
ob=bpy.data.objects.new('Sluice and banks',mesh);scene.collection.objects.link(ob)
for i,color in enumerate(data['colors']):
 mat=bpy.data.materials.new('Receiving material '+str(i));mat.use_nodes=True
 rgb=tuple(int(color[k:k+2],16)/255 for k in (1,3,5))
 mat.diffuse_color=(*rgb,1)
 mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(*rgb,1)
 mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.8
 mesh.materials.append(mat)
for p,i in zip(mesh.polygons,data['materials']):p.material_index=i
cam=bpy.data.cameras.new('Shared perspective camera')
cam.type='PERSP';cam.sensor_fit='HORIZONTAL';cam.sensor_width=36
cam.lens=data['camera']['focal_px']/data['camera']['resolution'][0]*cam.sensor_width
cx,cy=data['camera']['principal_point'];w,h=data['camera']['resolution']
cam.shift_x=(w/2-cx)/w;cam.shift_y=(cy-h/2)/w
co=bpy.data.objects.new('Shared perspective camera',cam);scene.collection.objects.link(co)
co.location=data['camera']['eye']
direction=Vector(data['camera']['target'])-co.location
co.rotation_euler=direction.to_track_quat('-Z','Y').to_euler();scene.camera=co
sun=bpy.data.lights.new('Shared sun','SUN');sun.energy=2;sun.angle=math.radians(2)
so=bpy.data.objects.new('Shared sun',sun);scene.collection.objects.link(so)
so.rotation_euler=(-Vector(data['light_direction'])).to_track_quat('-Z','Y').to_euler()
scene.world=bpy.data.worlds.new('Three Gates paper world');scene.world.color=(.22,.22,.20)
scene.render.resolution_x,scene.render.resolution_y=data['camera']['resolution']
scene.render.resolution_percentage=100
scene.render.filepath=str(root/'output/blender-massing.png')
print('Three Gates scene created. The CPU proof and Blender shading differ; geometry and camera match.')
