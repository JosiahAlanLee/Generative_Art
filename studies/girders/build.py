"""Build a girders-scene-1 file inside Blender 5.2 using Geometry Nodes instances.

Run:
  blender -b --python build.py -- --scene SCENE --out SCENE.blend
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
import random
import resource
import sys
import time
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector


ROOT = Path(__file__).resolve().parent
FORMAT = "girders-scene-1"
MATERIAL_NAMES = (
    "concrete", "steel", "steel_painted", "rust",
    "glass", "grating", "accent",
)
DETAIL_KINDS = (
    "bolt_plate", "rivet_row", "vent", "light",
    "ladder", "railing", "pipe_run", "cable",
)


def read_scene(path: Path) -> dict:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rb") as f:
        data = json.load(f)
    if data.get("format") != FORMAT:
        raise ValueError(f"{path}: expected format {FORMAT!r}")
    data.setdefault("blocks", [])
    data.setdefault("beams", [])
    data.setdefault("details", [])
    data.setdefault("profiles", {})
    data.setdefault("materials", list(MATERIAL_NAMES))
    data.setdefault("camera_hints", [])
    return data


def _socket(node, *names):
    for name in names:
        if name in node.inputs:
            return node.inputs[name]
    raise KeyError(f"{node.bl_idname}: none of {names!r}; has {[x.name for x in node.inputs]}")


def _material(name: str):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    n, links = m.node_tree.nodes, m.node_tree.links
    n.clear()
    out = n.new("ShaderNodeOutputMaterial")
    out.location = (660, 0)
    bsdf = n.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (390, 0)
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    tex = n.new("ShaderNodeTexNoise")
    tex.location = (-620, 120)
    tex.inputs["Scale"].default_value = 5.0
    tex.inputs["Detail"].default_value = 5.0
    tex.inputs["Roughness"].default_value = .7
    ramp = n.new("ShaderNodeValToRGB")
    ramp.location = (-320, 180)
    bump = n.new("ShaderNodeBump")
    bump.location = (100, -180)
    bump.inputs["Strength"].default_value = .16
    bump.inputs["Distance"].default_value = .018
    links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
    links.new(tex.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    _socket(bsdf, "Roughness").default_value = .65
    _socket(bsdf, "Metallic").default_value = .0

    if name == "concrete":
        ramp.color_ramp.elements[0].color = (.19, .18, .165, 1)
        ramp.color_ramp.elements[1].color = (.43, .41, .36, 1)
        tex.inputs["Scale"].default_value = 7.5
        bump.inputs["Distance"].default_value = .035
        _socket(bsdf, "Roughness").default_value = .86
    elif name == "steel":
        ramp.color_ramp.elements[0].color = (.055, .065, .070, 1)
        ramp.color_ramp.elements[1].color = (.19, .21, .22, 1)
        tex.inputs["Scale"].default_value = 24
        _socket(bsdf, "Metallic").default_value = .78
        _socket(bsdf, "Roughness").default_value = .47
        bump.inputs["Strength"].default_value = .11
        bump.inputs["Distance"].default_value = .0035
    elif name == "steel_painted":
        ramp.color_ramp.elements[0].color = (.055, .085, .085, 1)
        ramp.color_ramp.elements[1].color = (.20, .27, .27, 1)
        tex.inputs["Scale"].default_value = 9
        _socket(bsdf, "Metallic").default_value = .30
        _socket(bsdf, "Roughness").default_value = .63
        bump.inputs["Strength"].default_value = .094
        bump.inputs["Distance"].default_value = .004
    elif name == "rust":
        ramp.color_ramp.elements[0].color = (.065, .025, .013, 1)
        ramp.color_ramp.elements[1].color = (.38, .095, .028, 1)
        tex.inputs["Scale"].default_value = 4.5
        _socket(bsdf, "Metallic").default_value = .08
        _socket(bsdf, "Roughness").default_value = .89
        bump.inputs["Strength"].default_value = .28
        bump.inputs["Distance"].default_value = .009
    elif name == "glass":
        ramp.color_ramp.elements[0].color = (.018, .045, .052, 1)
        ramp.color_ramp.elements[1].color = (.10, .20, .22, 1)
        tex.inputs["Scale"].default_value = 2.5
        _socket(bsdf, "Metallic").default_value = .0
        _socket(bsdf, "Roughness").default_value = .13
        _socket(bsdf, "Transmission Weight", "Transmission").default_value = .68
        _socket(bsdf, "IOR").default_value = 1.45
    elif name == "grating":
        ramp.color_ramp.elements[0].color = (.038, .043, .041, 1)
        ramp.color_ramp.elements[1].color = (.125, .14, .13, 1)
        tex.inputs["Scale"].default_value = 38
        _socket(bsdf, "Metallic").default_value = .42
        _socket(bsdf, "Roughness").default_value = .72
        bump.inputs["Strength"].default_value = .35
        bump.inputs["Distance"].default_value = .008
    elif name == "accent":
        ramp.color_ramp.elements[0].color = (.20, .008, .002, 1)
        ramp.color_ramp.elements[1].color = (.72, .060, .014, 1)
        tex.inputs["Scale"].default_value = 2.5
        _socket(bsdf, "Metallic").default_value = .08
        _socket(bsdf, "Roughness").default_value = .39
        _socket(bsdf, "Emission Color").default_value = (.62, .025, .006, 1)
        _socket(bsdf, "Emission Strength").default_value = .16
    else:
        raise ValueError(f"unknown material {name!r}")
    m.diffuse_color = tuple(ramp.color_ramp.elements[1].color)
    return m


def build_materials(names):
    return {name: _material(name) for name in MATERIAL_NAMES if name in names}


def _mesh_object(name, collection, verts, faces, material):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj


def _prism_mesh(profile: dict, material):
    kind = profile["kind"]
    h = float(profile.get("h", profile.get("d", .1)))
    w = float(profile.get("w", profile.get("d", h)))
    t = float(profile.get("t", profile.get("tw", max(h * .04, .002))))
    tf = float(profile.get("tf", t))
    tw = float(profile.get("tw", t))
    if kind == "I":
        section = [
            (-w / 2, -h / 2), (-w / 2, -h / 2 + tf),
            (-tw / 2, -h / 2 + tf), (-tw / 2, h / 2 - tf),
            (-w / 2, h / 2 - tf), (-w / 2, h / 2),
            (w / 2, h / 2), (w / 2, h / 2 - tf),
            (tw / 2, h / 2 - tf), (tw / 2, -h / 2 + tf),
            (w / 2, -h / 2 + tf), (w / 2, -h / 2),
        ]
    elif kind == "C":
        section = [
            (-w / 2, -h / 2), (w / 2, -h / 2),
            (w / 2, -h / 2 + tf), (-w / 2 + tw, -h / 2 + tf),
            (-w / 2 + tw, h / 2 - tf), (w / 2, h / 2 - tf),
            (w / 2, h / 2), (-w / 2, h / 2),
        ]
    elif kind == "L":
        section = [
            (-w / 2, -h / 2), (w / 2, -h / 2),
            (w / 2, -h / 2 + t), (-w / 2 + t, -h / 2 + t),
            (-w / 2 + t, h / 2), (-w / 2, h / 2),
        ]
    elif kind == "box":
        section = [(-w / 2, -h / 2), (w / 2, -h / 2),
                   (w / 2, h / 2), (-w / 2, h / 2)]
    elif kind == "rod":
        d = float(profile.get("d", h))
        n = 12
        section = [(math.cos(i * math.tau / n) * d / 2,
                    math.sin(i * math.tau / n) * d / 2) for i in range(n)]
    elif kind == "tube":
        d = float(profile.get("d", h))
        t = min(t, d * .45)
        n = 16
        outer = [(math.cos(i * math.tau / n) * d / 2,
                  math.sin(i * math.tau / n) * d / 2) for i in range(n)]
        inner = [(math.cos(i * math.tau / n) * (d / 2 - t),
                  math.sin(i * math.tau / n) * (d / 2 - t)) for i in range(n)]
        verts = [(-.5, y, z) for y, z in outer] + [(.5, y, z) for y, z in outer]
        verts += [(-.5, y, z) for y, z in inner] + [(.5, y, z) for y, z in inner]
        faces = []
        for i in range(n):
            j = (i + 1) % n
            faces.extend([
                (i, j, n + j, n + i),
                (2 * n + i, 3 * n + i, 3 * n + j, 2 * n + j),
                (i, 2 * n + i, 2 * n + j, j),
                (n + i, n + j, 3 * n + j, 3 * n + i),
            ])
        return verts, faces
    else:
        raise ValueError(f"unknown profile kind {kind!r}")

    n = len(section)
    verts = [(-.5, y, z) for y, z in section] + [(.5, y, z) for y, z in section]
    faces = [tuple(reversed(range(n))), tuple(range(n, 2 * n))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    return verts, faces


class PartMesh:
    """Accumulate tiny boxes and cylinders into one detail mesh."""

    def __init__(self):
        self.verts = []
        self.faces = []

    def box(self, center, size):
        x, y, z = center
        sx, sy, sz = (v * .5 for v in size)
        off = len(self.verts)
        self.verts.extend([
            (x - sx, y - sy, z - sz), (x + sx, y - sy, z - sz),
            (x + sx, y + sy, z - sz), (x - sx, y + sy, z - sz),
            (x - sx, y - sy, z + sz), (x + sx, y - sy, z + sz),
            (x + sx, y + sy, z + sz), (x - sx, y + sy, z + sz),
        ])
        self.faces.extend([
            tuple(off + i for i in f) for f in (
                (0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
                (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7),
            )
        ])

    def cyl(self, center, radius, height, segments=10):
        x, y, z = center
        off = len(self.verts)
        for zz in (z - height / 2, z + height / 2):
            for i in range(segments):
                a = i * math.tau / segments
                self.verts.append((x + math.cos(a) * radius,
                                   y + math.sin(a) * radius, zz))
        self.faces.append(tuple(reversed(range(off, off + segments))))
        self.faces.append(tuple(range(off + segments, off + 2 * segments)))
        for i in range(segments):
            j = (i + 1) % segments
            self.faces.append((off + i, off + j,
                               off + segments + j, off + segments + i))


def _detail_mesh(kind):
    p = PartMesh()
    if kind == "bolt_plate":
        p.box((0, 0, 0), (1, 1, .14))
        for x in (-.34, .34):
            for y in (-.34, .34):
                p.cyl((x, y, -.105), .095, .075, 8)
                p.cyl((x, y, .105), .082, .07, 8)
    elif kind == "rivet_row":
        p.box((0, 0, 0), (1, .22, .16))
        for i in range(9):
            p.cyl((- .42 + i * .105, 0, .11), .044, .075, 8)
    elif kind == "vent":
        p.box((0, 0, 0), (1, .10, 1))
        for i in range(7):
            p.box((0, -.075, -.38 + i * .127), (.90, .055, .042))
        for x in (-.45, .45):
            p.box((x, -.035, 0), (.055, .13, .95))
    elif kind == "light":
        p.box((0, 0, 0), (.82, .55, .55))
        p.box((0, -.34, 0), (.48, .12, .25))
        for x in (-.28, .28):
            p.cyl((x, .30, 0), .035, .42, 7)
    elif kind == "ladder":
        for x in (-.42, .42):
            p.box((x, 0, 0), (.075, .12, 1))
        for i in range(10):
            p.box((0, 0, -.41 + i * .091), (.78, .075, .038))
    elif kind == "railing":
        for x in (-.5, .5):
            p.box((x, 0, 0), (.07, .12, 1))
        p.box((0, 0, .43), (1, .075, .065))
        p.box((0, 0, .10), (1, .06, .052))
        for i in range(6):
            p.box((-.43 + i * .172, 0, -.02), (.032, .05, .67))
    elif kind == "pipe_run":
        p.cyl((0, 0, 0), .42, 1, 12)
        for z in (-.42, 0, .42):
            p.cyl((0, 0, z), .53, .075, 12)
    elif kind == "cable":
        p.cyl((0, 0, 0), .36, 1, 8)
    else:
        return None
    return p.verts, p.faces


def _unit_cube():
    verts = [(x, y, z) for x in (-.5, .5) for y in (-.5, .5) for z in (-.5, .5)]
    # The corner order above makes these faces explicit and outward.
    faces = [
        (0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4),
        (1, 3, 7, 5), (3, 2, 6, 7), (2, 0, 4, 6),
    ]
    return verts, faces


def _set_point_vector(mesh, name, values):
    attr = mesh.attributes.new(name, "FLOAT_VECTOR", "POINT")
    attr.data.foreach_set("vector", np.asarray(values, dtype=np.float32).ravel())


def _set_point_float(mesh, name, values):
    attr = mesh.attributes.new(name, "FLOAT", "POINT")
    attr.data.foreach_set("value", np.asarray(values, dtype=np.float32))


def _set_point_int(mesh, name, values):
    attr = mesh.attributes.new(name, "INT", "POINT")
    attr.data.foreach_set("value", np.asarray(values, dtype=np.int32))


def _points_object(name, collection, positions, attrs):
    mesh = bpy.data.meshes.new(name + " points")
    flat = np.asarray(positions, dtype=np.float32).ravel()
    mesh.vertices.add(len(flat) // 3)
    mesh.vertices.foreach_set("co", flat)
    mesh.update()
    for attr_name, (kind, values) in attrs.items():
        if kind == "vector":
            _set_point_vector(mesh, attr_name, values)
        elif kind == "float":
            _set_point_float(mesh, attr_name, values)
        else:
            _set_point_int(mesh, attr_name, values)
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj


def _named(g, name, data_type, x, y):
    n = g.nodes.new("GeometryNodeInputNamedAttribute")
    n.data_type = data_type
    n.inputs["Name"].default_value = name
    n.location = (x, y)
    return n


def _math(g, op, x, y, a=None, b=None):
    n = g.nodes.new("ShaderNodeMath")
    n.operation = op
    n.location = (x, y)
    for i, value in enumerate((a, b)):
        if value is None:
            continue
        if isinstance(value, tuple):
            g.links.new(value[0].outputs[value[1]], n.inputs[i])
        else:
            n.inputs[i].default_value = value
    return n


def _instancer(name, points, collection, variant_count, collection_name):
    g = bpy.data.node_groups.new(name + " graph", "GeometryNodeTree")
    g.interface.new_socket(name="Geometry", in_out="INPUT",
                           socket_type="NodeSocketGeometry")
    g.interface.new_socket(name="Geometry", in_out="OUTPUT",
                           socket_type="NodeSocketGeometry")
    out = g.nodes.new("NodeGroupOutput")
    out.location = (740, 0)
    mesh_in = g.nodes.new("NodeGroupInput")
    mesh_in.location = (-820, 120)
    to_points = g.nodes.new("GeometryNodeMeshToPoints")
    to_points.location = (-610, 120)
    g.links.new(mesh_in.outputs["Geometry"], to_points.inputs["Mesh"])

    ci = g.nodes.new("GeometryNodeCollectionInfo")
    ci.location = (-610, -260)
    ci.transform_space = "ORIGINAL"
    ci.inputs["Collection"].default_value = collection
    ci.inputs["Separate Children"].default_value = True
    ci.inputs["Reset Children"].default_value = True

    inst = g.nodes.new("GeometryNodeInstanceOnPoints")
    inst.location = (420, 120)
    inst.inputs["Pick Instance"].default_value = True
    g.links.new(to_points.outputs["Points"], inst.inputs["Points"])
    g.links.new(ci.outputs["Instances"], inst.inputs["Instance"])

    profile = _named(g, "profile_index", "INT", -610, 430)
    material = _named(g, "source_material_index", "INT", -610, 280)
    matmul = _math(g, "MULTIPLY", -390, 390,
                   (profile, "Attribute"), float(variant_count))
    index = _math(g, "ADD", -180, 330,
                  (matmul, 0), (material, "Attribute"))
    g.links.new(index.outputs[0], inst.inputs["Instance Index"])

    length = _named(g, "beam_length", "FLOAT", -610, 30)
    variation = _named(g, "variation", "FLOAT", -610, -110)
    vmul = _math(g, "MULTIPLY_ADD", -390, 30, (variation, "Attribute"), .008)
    g.links.new(length.outputs["Attribute"], vmul.inputs[2])
    scale = g.nodes.new("ShaderNodeCombineXYZ")
    scale.location = (-170, 20)
    g.links.new(vmul.outputs[0], scale.inputs["X"])
    vary_scale = _math(g, "MULTIPLY_ADD", -390, -140,
                       (variation, "Attribute"), .006)
    vary_scale.inputs[2].default_value = 1.0
    g.links.new(vary_scale.outputs[0], scale.inputs["Y"])
    g.links.new(vary_scale.outputs[0], scale.inputs["Z"])
    g.links.new(scale.outputs[0], inst.inputs["Scale"])
    rotation = _named(g, "instance_rotation", "FLOAT_VECTOR", -390, -310)
    g.links.new(rotation.outputs["Attribute"], inst.inputs["Rotation"])
    g.links.new(inst.outputs["Instances"], out.inputs["Geometry"])

    modifier = points.modifiers.new(collection_name, "NODES")
    modifier.node_group = g
    points["girders_instancer"] = collection_name
    points["girders_variants"] = variant_count
    return g


def _beam_rotation(direction: np.ndarray, roll: float):
    x = Vector((float(direction[0]), float(direction[1]), float(direction[2])))
    x.normalize()
    if abs(x.z) > .9999:
        y = Vector((0, -1, 0))
        z = x.cross(y).normalized()
    else:
        y = Vector((0, 0, 1)).cross(x).normalized()
        z = x.cross(y).normalized()
    if roll:
        q = Quaternion(x, roll)
        y = q @ y
        z = q @ z
    return Matrix((x, y, z)).transposed().to_euler("XYZ")


def _build_beams(data, collection, materials, profile_order, profile_collection):
    beams = data["beams"]
    if not beams:
        return 0
    n = len(beams)
    a = np.empty((n, 3), dtype=np.float64)
    b = np.empty((n, 3), dtype=np.float64)
    profile_index = np.empty(n, dtype=np.int32)
    material_index = np.empty(n, dtype=np.int32)
    rolls = np.empty(n, dtype=np.float64)
    profile_lookup = {name: i for i, name in enumerate(profile_order)}
    material_lookup = {name: i for i, name in enumerate(MATERIAL_NAMES)}
    for i, beam in enumerate(beams):
        a[i] = beam["a"]
        b[i] = beam["b"]
        profile_index[i] = profile_lookup[beam["profile"]]
        material_index[i] = material_lookup[beam["material"]]
        rolls[i] = float(beam.get("roll", 0.0))
    delta = b - a
    lengths = np.linalg.norm(delta, axis=1)
    valid = lengths > 1e-7
    if not np.all(valid):
        raise ValueError(f"{int((~valid).sum())} zero-length beams")
    midpoint = (a + b) * .5
    directions = delta / lengths[:, None]
    rotations = np.empty((n, 3), dtype=np.float32)
    for i in range(n):
        rotations[i] = _beam_rotation(directions[i], float(rolls[i]))
    rng = np.random.default_rng(int(data.get("seed", 0)) & 0xffffffff)
    variation = rng.random(n).astype(np.float32)
    points = _points_object("BEAMS | instanced members", collection, midpoint, {
        "profile_index": ("int", profile_index),
        "source_material_index": ("int", material_index),
        "beam_length": ("float", lengths),
        "instance_rotation": ("vector", rotations),
        "variation": ("float", variation),
    })
    _instancer("Beams", points, profile_collection,
               len(materials), "Girders | beam instances")
    points["source_count"] = n
    return n


def _build_blocks(data, collection, materials, block_collection):
    blocks = data["blocks"]
    if not blocks:
        return 0
    n = len(blocks)
    positions = np.empty((n, 3), dtype=np.float32)
    scales = np.empty((n, 3), dtype=np.float32)
    rotations = np.empty((n, 3), dtype=np.float32)
    material_index = np.empty(n, dtype=np.int32)
    lookup = {name: i for i, name in enumerate(MATERIAL_NAMES)}
    for i, block in enumerate(blocks):
        positions[i] = block["center"]
        scales[i] = block["size"]
        rotations[i] = (0, 0, float(block.get("yaw", 0.0)))
        material_index[i] = lookup[block["material"]]
    points = _points_object("BLOCKS | instanced masses", collection, positions, {
        "source_material_index": ("int", material_index),
        "instance_rotation": ("vector", rotations),
        "block_size": ("vector", scales),
    })
    # Blocks reuse the same graph and use block_size as XYZ instance scale.
    _instancer("Blocks", points, block_collection,
               len(materials), "Girders | block instances")
    g = points.modifiers["Girders | block instances"].node_group
    # The shared graph expects beam_length plus YZ variation. Retarget its scale
    # combine inputs without altering the reusable profile graph.
    inst = next(n for n in g.nodes if n.bl_idname == "GeometryNodeInstanceOnPoints")
    scale = inst.inputs["Scale"].links[0].from_node
    for input_name, attr_name in (("X", "block_size"), ("Y", "block_size"), ("Z", "block_size")):
        named = _named(g, attr_name, "FLOAT_VECTOR", -610, -510)
        sep = g.nodes.new("ShaderNodeSeparateXYZ")
        sep.location = (-390, -510)
        g.links.new(named.outputs["Attribute"], sep.inputs["Vector"])
        g.links.new(sep.outputs[input_name], scale.inputs[input_name])
    points["source_count"] = n
    return n


def _build_details(data, collection, materials, detail_collection):
    rows = []
    known = set(DETAIL_KINDS)
    for detail in data["details"]:
        if detail.get("kind") in known:
            rows.append(detail)
    if not rows:
        return 0
    n = len(rows)
    positions = np.empty((n, 3), dtype=np.float32)
    scales = np.empty((n, 3), dtype=np.float32)
    rotations = np.empty((n, 3), dtype=np.float32)
    material_index = np.empty(n, dtype=np.int32)
    kind_index = np.empty(n, dtype=np.int32)
    kind_lookup = {name: i for i, name in enumerate(DETAIL_KINDS)}
    material_lookup = {name: i for i, name in enumerate(MATERIAL_NAMES)}
    identity = Matrix.Identity(4)
    for i, detail in enumerate(rows):
        values = detail.get("transform")
        if values:
            matrix = Matrix((
                (values[0], values[4], values[8], values[12]),
                (values[1], values[5], values[9], values[13]),
                (values[2], values[6], values[10], values[14]),
                (values[3], values[7], values[11], values[15]),
            ))
        else:
            matrix = identity
        position, rotation, transform_scale = matrix.decompose()
        positions[i] = position
        rotations[i] = rotation.to_euler("XYZ")
        scales[i] = np.multiply(transform_scale, detail["size"])
        material_index[i] = material_lookup[detail["material"]]
        kind_index[i] = kind_lookup[detail["kind"]]
    points = _points_object("DETAILS | instanced parts", collection, positions, {
        "profile_index": ("int", kind_index),
        "source_material_index": ("int", material_index),
        "instance_rotation": ("vector", rotations),
        "beam_length": ("float", np.ones(n, dtype=np.float32)),
        "variation": ("float", np.zeros(n, dtype=np.float32)),
    })
    _instancer("Details", points, detail_collection,
               len(materials), "Girders | detail instances")
    # Detail scale uses three independent object dimensions.
    g = points.modifiers["Girders | detail instances"].node_group
    inst = next(n for n in g.nodes if n.bl_idname == "GeometryNodeInstanceOnPoints")
    combine = inst.inputs["Scale"].links[0].from_node
    vec = _named(g, "detail_size", "FLOAT_VECTOR", -610, -460)
    sep = g.nodes.new("ShaderNodeSeparateXYZ")
    sep.location = (-390, -460)
    g.links.new(vec.outputs["Attribute"], sep.inputs["Vector"])
    for dim in ("X", "Y", "Z"):
        g.links.new(sep.outputs[dim], combine.inputs[dim])
    # Recreate the detail_size attribute on the point cloud.
    _set_point_vector(points.data, "detail_size", scales)
    points["source_count"] = n
    return n


def build_asset_collections(materials, profiles):
    assets = {}
    for key, cube in (("profiles", False), ("blocks", True), ("details", False)):
        c = bpy.data.collections.new(f"Girders assets | {key}")
        assets[key] = c
    for profile_i, (name, profile) in enumerate(profiles.items()):
        verts, faces = _prism_mesh(profile, materials["steel"])
        for mat_i, mat_name in enumerate(MATERIAL_NAMES):
            mat = materials.get(mat_name, materials["steel"])
            _mesh_object(f"p{profile_i:03d} m{mat_i:03d} {name} {mat_name}",
                         assets["profiles"],
                         verts, faces, mat)
    cv, cf = _unit_cube()
    for mat_i, mat_name in enumerate(MATERIAL_NAMES):
        _mesh_object(f"b{mat_i:03d} {mat_name}", assets["blocks"], cv, cf,
                     materials.get(mat_name, materials["concrete"]))
    for kind_i, kind in enumerate(DETAIL_KINDS):
        shape = _detail_mesh(kind)
        for mat_i, mat_name in enumerate(MATERIAL_NAMES):
            verts, faces = shape
            obj = _mesh_object(f"d{kind_i:03d} m{mat_i:03d} {kind} {mat_name}",
                               assets["details"], verts, faces,
                               materials.get(mat_name, materials["steel"]))
            bevel = obj.modifiers.new("Micro chamfer", "BEVEL")
            bevel.width = .0025
            bevel.segments = 1
            bevel.limit_method = "ANGLE"
            bevel.angle_limit = math.radians(35)
    return assets, list(profiles)


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = "Girders"
    return scene


def build_scene(data: dict, fresh=True) -> tuple:
    start = time.perf_counter()
    scene = reset_scene() if fresh else bpy.context.scene
    mnames = [x for x in data.get("materials", MATERIAL_NAMES) if x in MATERIAL_NAMES]
    if not mnames:
        mnames = list(MATERIAL_NAMES)
    materials = build_materials(mnames)
    for name in MATERIAL_NAMES:
        materials.setdefault(name, _material(name))
    scene["girders_format"] = FORMAT
    scene["girders_seed"] = int(data.get("seed", 0))
    scene["girders_generator"] = json.dumps(data.get("generator", {}))
    assets, profile_order = build_asset_collections(materials, data["profiles"])
    instancers = bpy.data.collections.new("GIRDERS | instancers")
    scene.collection.children.link(instancers)
    beam_n = _build_beams(data, instancers, materials, profile_order, assets["profiles"])
    block_n = _build_blocks(data, instancers, materials, assets["blocks"])
    detail_n = _build_details(data, instancers, materials, assets["details"])
    scene["girders_counts"] = json.dumps({
        "blocks": block_n, "beams": beam_n, "details": detail_n,
    })
    bpy.context.view_layer.update()
    elapsed = time.perf_counter() - start
    stats = {
        "format": FORMAT,
        "counts": {"blocks": block_n, "beams": beam_n, "details": detail_n},
        "instancer_objects": len([x for x in instancers.objects]),
        "scene_objects": len(bpy.context.scene.objects),
        "profiles": len(profile_order),
        "build_seconds": round(elapsed, 3),
        "peak_rss_mib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
        "blender": bpy.app.version_string,
    }
    scene["girders_build_stats"] = json.dumps(stats)
    return scene, stats, materials


def _parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--scene", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--stats-out", type=Path)
    p.add_argument("--render-look")
    p.add_argument("--camera", default="auto")
    p.add_argument("--res", default="3840x2160")
    p.add_argument("--samples", type=int, default=128)
    p.add_argument("--out-dir", type=Path)
    p.add_argument("--preview", action="store_true")
    p.add_argument("--exr", action="store_true")
    p.add_argument("--no-render", action="store_true")
    return p.parse_args(argv)


def main():
    args = _parse_args()
    data = read_scene(args.scene)
    scene, stats, materials = build_scene(data)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.out.resolve()))
    if args.stats_out:
        args.stats_out.parent.mkdir(parents=True, exist_ok=True)
        args.stats_out.write_text(json.dumps(stats, indent=2) + "\n")
    print("GIRDERS_BUILD", json.dumps(stats), flush=True)
    if args.render_look and not args.no_render:
        if not args.out_dir:
            raise ValueError("--out-dir is required with --render-look")
        sys.path.insert(0, str(ROOT))
        import look as look_lib
        result = look_lib.render_scene(
            scene, data, materials, args.scene, args.out_dir,
            args.render_look, args.camera, args.res, args.samples,
            args.preview, args.exr, stats,
        )
        print("GIRDERS_RENDER", json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
