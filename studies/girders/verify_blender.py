"""Native Blender checks for a girders fixture.

Run inside Blender:
  blender -b --python verify_blender.py -- --scene SCENE.json.gz --out DIR
"""

from __future__ import annotations

import argparse
import json
import resource
import sys
from collections import Counter
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import build
import look
import numpy as np
from mathutils import Vector


def args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--scene", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    return p.parse_args(argv)


def main():
    a = args()
    a.out.mkdir(parents=True, exist_ok=True)
    data = build.read_scene(a.scene)
    scene, stats, _ = build.build_scene(data)
    expected = {
        "blocks": len(data["blocks"]),
        "beams": len(data["beams"]),
        "details": len([d for d in data["details"] if d.get("kind") in build.DETAIL_KINDS]),
    }
    deps = bpy.context.evaluated_depsgraph_get()
    instancer_objects = [
        obj for obj in scene.objects
        if any(mod.type == "NODES" for mod in obj.modifiers)
    ]
    source_counts = {
        obj["girders_instancer"]: int(obj["source_count"])
        for obj in instancer_objects
    }
    instance_names = Counter()
    sampled_polygons = []
    detail_polygons = {}
    total_instances = 0
    for item in deps.object_instances:
        if not item.is_instance:
            continue
        total_instances += 1
        instance_names[item.object.name] += 1
        if item.object.name.startswith("d"):
            detail_polygons[item.object.name] = len(item.object.data.polygons)
        if total_instances <= 12:
            sampled_polygons.append(len(item.object.data.polygons))
    used_materials = {
        name.rsplit(" ", 1)[-1] for name in instance_names
        if name.startswith(("p", "b", "d"))
    }
    used_profiles = {
        name.split(" ", 1)[0] for name in instance_names if name.startswith("p")
    }
    used_detail_kinds = {
        name.split(" ", 1)[0] for name in instance_names if name.startswith("d")
    }
    profile_assets = bpy.data.collections.get("Girders assets | profiles")
    built_profile_indices = {
        obj.name.split(" ", 1)[0] for obj in profile_assets.objects
    } if profile_assets else set()
    checks = {
        "format_is_v1": data["format"] == build.FORMAT,
        "source_counts_match_json": stats["counts"] == expected,
        "exactly_three_instancer_objects": len(instancer_objects) == 3,
        "roughly_one_scene_object_per_category": len(scene.objects) <= 8,
        "native_instance_total_matches_source": total_instances == sum(expected.values()),
        "beam_point_cloud_count": source_counts.get("Girders | beam instances") == expected["beams"],
        "block_point_cloud_count": source_counts.get("Girders | block instances") == expected["blocks"],
        "detail_point_cloud_count": source_counts.get("Girders | detail instances") == expected["details"],
        "sampled_instances_are_meshes": all(n > 0 for n in sampled_polygons),
        "detail_assets_have_modeled_detail": max(detail_polygons.values(), default=0) >= 30,
        "all_schema_materials_present": all(
            bpy.data.materials.get(name) is not None for name in build.MATERIAL_NAMES
        ),
        "material_variants_are_picked_not_stacked": (
            total_instances == sum(expected.values())
            and max(instance_names.values(), default=0) < expected["beams"] * 7
        ),
        "multiple_material_variants_selected": len(used_materials) >= 5,
        "all_profile_assets_built": len(built_profile_indices) == len(data["profiles"]),
        "multiple_detail_kinds_selected": len(used_detail_kinds) >= 5,
    }
    # Check the schema frame for horizontal, upward/downward and nearly
    # vertical members. These directions exposed an incorrect downward web.
    frame_ok = True
    for direction in ((1, 0, 0), (0, 0, 1), (0, 0, -1), (.001, 0, -1)):
        x = Vector(direction).normalized()
        zero = build._beam_rotation(np.array(x), 0).to_matrix()
        quarter = build._beam_rotation(np.array(x), np.pi / 2).to_matrix()
        frame_ok &= (zero @ Vector((1, 0, 0)) - x).length < 1e-5
        expected_web = ((Vector((1, 0, 0)) - x * x.x).normalized()
                        if abs(x.z) > .9999 else
                        (Vector((0, 0, 1)) - x * x.z).normalized())
        frame_ok &= (zero @ Vector((0, 0, 1)) - expected_web).length < 1e-5
        frame_ok &= (quarter @ Vector((0, 0, 1)) - x.cross(expected_web)).length < 1e-5
    checks["beam_frame_matches_schema"] = bool(frame_ok)
    def signed_volume(mesh):
        mesh.calc_loop_triangles()
        return sum(mesh.vertices[t.vertices[0]].co.dot(
            mesh.vertices[t.vertices[1]].co.cross(mesh.vertices[t.vertices[2]].co))
            for t in mesh.loop_triangles) / 6
    checks["profile_and_block_normals_outward"] = all(
        signed_volume(obj.data) > 0
        for name in ("profiles", "blocks")
        for obj in bpy.data.collections["Girders assets | " + name].objects)
    haze = look._haze_box(scene, data, .0003, "overcast")
    checks["atmosphere_normals_outward"] = signed_volume(haze.data) > 0
    bpy.data.objects.remove(haze, do_unlink=True)
    checks["groups_preserved"] = json.loads(scene["girders_groups"]) == data.get("groups", [])
    for obj, rows in ((next(o for o in instancer_objects if o.name.startswith("BEAMS")), data["beams"]),
                      (next(o for o in instancer_objects if o.name.startswith("BLOCKS")), data["blocks"])):
        checks[obj.name.split(" |")[0].lower() + "_group_ids_preserved"] = [
            a.value for a in obj.data.attributes["source_group"].data
        ] == [row.get("group", -1) for row in rows]
    for hint in data.get("camera_hints", []):
        if "axon" not in hint.get("name", ""):
            continue
        scene.render.resolution_x, scene.render.resolution_y = 3840, 2160
        cam, _ = look._camera(scene, "overcast", data, hint["name"])
        # Update matrix_world before projecting to the camera frame.
        bpy.context.view_layer.update()
        inverse = cam.matrix_world.inverted()
        lo, hi = look._bounds(data)
        projected = [inverse @ Vector((x, y, z))
                     for x in (lo.x, hi.x) for y in (lo.y, hi.y) for z in (lo.z, hi.z)]
        checks["axon_fits_bounds_at_16_9"] = all(
            abs(v.x) <= cam.data.ortho_scale / 2 and
            abs(v.y) <= cam.data.ortho_scale / 2 * 2160 / 3840 for v in projected)
    bpy.ops.wm.save_as_mainfile(filepath=str((a.out / "verified.blend").resolve()))
    report = {
        "passed": all(checks.values()),
        "blender": bpy.app.version_string,
        "checks": checks,
        "expected": expected,
        "source_counts": source_counts,
        "native_instances": total_instances,
        "unique_instanced_assets": len(instance_names),
        "used_materials": sorted(used_materials),
        "used_profiles": sorted(used_profiles),
        "used_detail_kinds": sorted(used_detail_kinds),
        "instance_asset_counts": dict(instance_names.most_common()),
        "sampled_polygons": sampled_polygons,
        "detail_polygon_range": [
            min(detail_polygons.values(), default=0),
            max(detail_polygons.values(), default=0),
        ],
        "scene_objects": len(scene.objects),
        "build": stats,
        "peak_rss_mib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
    }
    (a.out / "verify.json").write_text(json.dumps(report, indent=2) + "\n")
    print("GIRDERS_VERIFY", json.dumps(report), flush=True)
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
