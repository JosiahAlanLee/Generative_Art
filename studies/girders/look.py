"""Cycles look, camera and atmosphere rigs for girders scenes."""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
import time
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
LOOKS = ("overcast", "low_sun", "night", "mineral", "ink")


def _set(node, names, value):
    for name in names:
        if name in node.inputs:
            node.inputs[name].default_value = value
            return
    raise KeyError(f"{node.bl_idname}: none of {names!r}")


def _linear(hex_color):
    values = [int(hex_color[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4
                 for v in values)


def _world(scene, look):
    world = bpy.data.worlds.new("Girders look | " + look)
    scene.world = world
    world.use_nodes = True
    nodes, links = world.node_tree.nodes, world.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputWorld")
    bg = nodes.new("ShaderNodeBackground")
    links.new(bg.outputs["Background"], out.inputs["Surface"])
    specs = {
        "mineral": dict(top=(.19, .23, .26), horizon=(.60, .64, .65),
                        strength=.85, haze=.0018),
        "ink": dict(top=(.82, .81, .77), horizon=(.82, .81, .77),
                    strength=.8, haze=0),
        "overcast": dict(
            top=(.50, .57, .63), horizon=(.68, .72, .72),
            strength=1.18, haze=.00032),
        "low_sun": dict(
            top=(.08, .16, .30), horizon=(.57, .31, .17),
            strength=.95, haze=.00030),
        "night": dict(
            top=(.004, .012, .035), horizon=(.075, .13, .22),
            strength=.28, haze=.00022),
    }[look]
    bg.inputs["Strength"].default_value = specs["strength"]
    coord = nodes.new("ShaderNodeTexCoord")
    coord.location = (-650, 0)
    separate = nodes.new("ShaderNodeSeparateXYZ")
    separate.location = (-450, 0)
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.location = (-230, 0)
    ramp.color_ramp.elements[0].position = .44
    ramp.color_ramp.elements[0].color = (*specs["horizon"], 1)
    ramp.color_ramp.elements[1].position = .72
    ramp.color_ramp.elements[1].color = (*specs["top"], 1)
    links.new(coord.outputs["Generated"], separate.inputs["Vector"])
    links.new(separate.outputs["Z"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bg.inputs["Color"])
    world.mist_settings.start = .5
    world.mist_settings.depth = 420
    world.mist_settings.falloff = "QUADRATIC"
    return specs["haze"]


def _haze_box(scene, data, density, look):
    """Finite atmosphere; an infinite world volume would extinguish the scene."""
    lo, hi = _bounds(data)
    center = (lo + hi) * .5
    extent = (hi - lo) * 3.0 + Vector((120, 120, 100))
    verts = [(x, y, z) for x in (-.5, .5) for y in (-.5, .5) for z in (-.5, .5)]
    faces = [
        (0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4),
        (1, 3, 7, 5), (3, 2, 6, 7), (2, 0, 4, 6),
    ]
    mesh = bpy.data.meshes.new("Girders atmosphere")
    # Outward winding is essential: inward volume normals extinguish sunlight
    # outside the box rather than containing the atmosphere inside it.
    mesh.from_pydata(verts, [], [tuple(reversed(face)) for face in faces])
    mesh.update()
    obj = bpy.data.objects.new("Girders atmosphere", mesh)
    scene.collection.objects.link(obj)
    obj.location = center
    obj.scale = extent
    mat = bpy.data.materials.new("Girders atmosphere " + look)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    vol = nodes.new("ShaderNodeVolumePrincipled")
    vol.inputs["Color"].default_value = (
        (.73, .80, .88, 1) if look != "night" else (.18, .28, .46, 1)
    )
    vol.inputs["Density"].default_value = density
    vol.inputs["Anisotropy"].default_value = .38
    links.new(vol.outputs["Volume"], out.inputs["Volume"])
    mesh.materials.append(mat)
    return obj


def _area(scene, name, location, target, energy, size, color=(1, 1, 1)):
    light = bpy.data.lights.new(name, "AREA")
    light.energy = energy
    light.shape = "DISK"
    light.size = size
    light.color = color
    obj = bpy.data.objects.new(name, light)
    scene.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()
    return obj


def _sun(scene, name, direction, energy, color, angle):
    light = bpy.data.lights.new(name, "SUN")
    light.energy = energy
    light.color = color
    light.angle = angle
    obj = bpy.data.objects.new(name, light)
    scene.collection.objects.link(obj)
    obj.rotation_euler = Vector(direction).to_track_quat("-Z", "Y").to_euler()
    return obj


def _bounds(data):
    lo = Vector(data.get("bounds", {}).get("min", (-20, -20, 0)))
    hi = Vector(data.get("bounds", {}).get("max", (20, 20, 20)))
    if hi.x <= lo.x or hi.y <= lo.y or hi.z <= lo.z:
        raise ValueError("scene bounds must have positive extent")
    return lo, hi


def _camera_selection(data, requested):
    hints = list(data.get("camera_hints", []))
    # Look-development cameras work with any generator without rewriting its data.
    lo, hi = _bounds(data)
    center, extent = (lo + hi) * .5, hi - lo
    preset = data.get("generator", {}).get("params", {}).get("preset")
    if preset == "fault-spine" and requested in ("worm", "canyon", "auto", None, ""):
        return {"name": "worm", "location": [lo.x - extent.x * .04, -2.8, 5.8],
                "target": [center.x + extent.x * .18, 1.2, lo.z + extent.z * .44],
                "lens_mm": 24}
    if requested == "section" and preset == "suspended-delta":
        span = max(extent.x, extent.y)
        return {"name": "section", "location": [center.x + span * 1.4,
                center.y - span * .8, lo.z + extent.z * .58],
                "target": [center.x, center.y, lo.z + extent.z * .43], "lens_mm": 52}
    if requested == "section":
        return {"name": "section", "location": [hi.x + extent.x * .48,
                lo.y - extent.y * .58, lo.z + extent.z * .35],
                "target": [center.x, center.y, lo.z + extent.z * .48], "lens_mm": 48}
    if requested == "print-axon":
        span = max(extent.x, extent.y, extent.z)
        return {"name": "print-axon", "location": [center.x + span * 1.8,
                center.y - span * 1.1, center.z + span * 1.5],
                "target": list(center), "ortho_scale": span * 1.12}

    if requested not in (None, "", "auto"):
        for hint in hints:
            if hint.get("name") == str(requested):
                return dict(hint)
        if str(requested).isdigit() and int(requested) < len(hints):
            return dict(hints[int(requested)])
        raise ValueError(f"camera {requested!r} is not present in camera_hints")
    if hints:
        named = {h.get("name"): h for h in hints}
        return dict(named.get("worm") or hints[0])
    lo, hi = _bounds(data)
    center = (lo + hi) * .5
    extent = hi - lo
    return {
        "name": "auto-worm",
        "location": [hi.x + extent.x * .22, lo.y - extent.y * .72,
                     lo.z + extent.z * .035],
        "target": [center.x, center.y, lo.z + extent.z * .58],
        "lens_mm": 26,
    }


def _camera(scene, look, data, requested):
    spec = _camera_selection(data, requested)
    lo, hi = _bounds(data)
    location = Vector(spec["location"])
    target = Vector(spec["target"])
    if location == target:
        raise ValueError("camera location and target are identical")
    cam_data = bpy.data.cameras.new(f"Girders camera | {spec.get('name', 'camera')}")
    cam_data.lens = float(spec.get("lens_mm", 45))
    cam_data.sensor_width = 36
    cam_data.clip_start = .02
    cam_data.clip_end = max(1000, (hi - lo).length * 12)
    if "axon" in str(spec.get("name", "")).lower():
        cam_data.type = "ORTHO"
        cam_data.ortho_scale = float(spec.get(
            "ortho_scale",
            max(hi.x - lo.x, hi.y - lo.y, (hi.z - lo.z) * 1.55) * 1.18,
        ))
    else:
        cam_data.type = "PERSP"
        cam_data.dof.use_dof = True
        cam_data.dof.focus_distance = (target - location).length
        cam_data.dof.aperture_fstop = 11 if look == "overcast" else 8
    obj = bpy.data.objects.new(cam_data.name, cam_data)
    scene.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = obj
    if cam_data.type == "ORTHO":
        # Fit all eight bounds corners in camera space, including aspect ratio.
        # A world-axis maximum clips tall/diagonal structures in a wide image.
        inverse = obj.rotation_euler.to_matrix().transposed()
        corners = [inverse @ Vector((x, y, z))
                   for x in (lo.x, hi.x) for y in (lo.y, hi.y)
                   for z in (lo.z, hi.z)]
        left, right = min(v.x for v in corners), max(v.x for v in corners)
        bottom, top = min(v.y for v in corners), max(v.y for v in corners)
        aspect = scene.render.resolution_x / scene.render.resolution_y
        cam_data.ortho_scale = max(cam_data.ortho_scale,
                                   max(right - left, (top - bottom) * aspect) * 1.06)
        frame_center = obj.rotation_euler.to_matrix() @ Vector(
            ((left + right) / 2, (bottom + top) / 2, 0))
        projected_location = inverse @ obj.location
        obj.location += frame_center - obj.rotation_euler.to_matrix() @ Vector(
            (projected_location.x, projected_location.y, 0))
        spec["ortho_scale"] = cam_data.ortho_scale
        spec["location"] = list(obj.location)
        spec["target"] = list(obj.location + (target - location))
    return obj, spec


def _light_rig(scene, look, data, camera=None):
    lo, hi = _bounds(data)
    center = (lo + hi) * .5
    extent = hi - lo
    if look == "mineral":
        fault = data.get("generator", {}).get("params", {}).get("preset") == "fault-spine"
        direction = ((.8, .15, -.45) if fault and camera in ("worm", "canyon", "auto", None, "")
                     else (-.6, .45, -.55))
        _sun(scene, "Pale raking sun", direction, 3.4,
             (1, .94, .84), math.radians(2.2))
        _area(scene, "Canyon sky", (lo.x, lo.y, hi.z + extent.z),
              center, 22000, max(extent.x, extent.y) * .6, (.78, .86, 1))
        if fault:
            _area(scene, "Canyon entrance bounce", (lo.x - 15, 0, hi.z * .45),
                  center, 90000, 30, (.80, .88, 1))
    elif look == "ink":
        _sun(scene, "Print key", (.4, .2, -.8), 2.6,
             (1, 1, 1), math.radians(7))
    elif look == "overcast":
        _sun(scene, "Break in cloud", (.5, .3, -.7), 1.8, (.82, .9, 1), math.radians(12))
        _area(scene, "Overcast key", (lo.x - extent.x * .3, lo.y - extent.y * .4,
                                      hi.z + extent.z * .9),
              center, 18000, max(extent.x, extent.y) * .18, (.88, .93, 1))
        _area(scene, "Overcast bounce", (hi.x * .1, hi.y, hi.z * .2),
              center, 7600, max(extent.x, extent.y) * .22, (.75, .84, .93))
    elif look == "low_sun":
        _sun(scene, "Low sun", (-.55, .65, -.35), 5.8, (1.0, .72, .48), math.radians(.8))
        _area(scene, "Cold sky fill", (-extent.x, extent.y * .3, hi.z + extent.z),
              center, 8200, extent.x * .18, (.42, .58, .78))
    else:
        _sun(scene, "Moon", (-.38, .52, -.76), .80, (.35, .52, 1.0),
             math.radians(.7))
        _area(scene, "Night edge light", (lo.x, lo.y, hi.z + 8),
              center, 3600, extent.x * .12, (.20, .35, .72))
    if look == "night":
        shown = 0
        for detail in data.get("details", []):
            if detail.get("kind") != "light" or shown >= 24:
                continue
            m = detail.get("transform")
            if not m:
                continue
            light = bpy.data.lights.new("Practical", "POINT")
            light.energy = 180
            light.color = (1.0, .20, .045)
            light.shadow_soft_size = .20
            obj = bpy.data.objects.new(light.name, light)
            scene.collection.objects.link(obj)
            obj.location = (m[12], m[13], m[14])
            shown += 1
        for material in bpy.data.materials:
            if not material.use_nodes:
                continue
            for node in material.node_tree.nodes:
                if node.bl_idname == "ShaderNodeBsdfPrincipled" and material.name == "accent":
                    _set(node, ("Emission Strength",), 18.0)
        scene["girders_practicals"] = shown


def _engine(scene, samples, preview):
    scene.render.engine = "CYCLES"
    scene.cycles.device = "GPU"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "OPTIX"
        prefs.get_devices()
        for device in prefs.devices:
            device.use = device.type == "OPTIX"
    except Exception as exc:
        print("GIRDERS_GPU_SETUP_WARNING", repr(exc), flush=True)
        scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = .018 if not preview else .04
    scene.cycles.use_denoising = True
    try:
        scene.cycles.denoiser = "OPTIX"
    except Exception as exc:
        print("GIRDERS_DENOISER_WARNING", repr(exc), flush=True)
        scene.cycles.denoiser = "OPENIMAGEDENOISE"
    scene.cycles.max_bounces = 8 if not preview else 4
    scene.cycles.diffuse_bounces = 4
    scene.cycles.glossy_bounces = 4
    scene.cycles.transmission_bounces = 6
    scene.cycles.volume_bounces = 2
    scene.cycles.caustics_reflective = False
    scene.cycles.caustics_refractive = False
    scene.render.use_persistent_data = True
    scene.render.film_transparent = False
    scene.render.use_file_extension = True
    scene.view_layers[0].use_pass_mist = True
    scene.view_settings.view_transform = "AgX"
    for candidate in ("AgX - Medium High Contrast", "Medium High Contrast"):
        try:
            scene.view_settings.look = candidate
            break
        except TypeError:
            pass
    scene.view_settings.exposure = {
        "overcast": -.25, "low_sun": -.45, "night": .15,
    }.get(scene.get("girders_look", "overcast"), 0)


def _art_materials(look):
    """Two restrained palettes; AO preserves joints without expensive edge geometry."""
    if look not in ("mineral", "ink"):
        return
    ink = look == "ink"
    palette = {
        "concrete": (.48, .46, .41) if ink else (.31, .32, .30),
        "steel": (.035, .038, .038) if ink else (.095, .115, .12),
        "steel_painted": (.075, .078, .075) if ink else (.18, .22, .22),
        "rust": (.13, .125, .11) if ink else (.17, .16, .14),
        "grating": (.08, .085, .08) if ink else (.12, .15, .15),
        "glass": (.22, .23, .22) if ink else (.16, .20, .21),
        "accent": (.46, .105, .025),
    }
    for name, color in palette.items():
        mat = bpy.data.materials.get(name)
        if not mat or not mat.use_nodes:
            continue
        mat.diffuse_color = (*color, 1)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
        # Replace the color chain only; retain physically scaled surface wear.
        for link in list(bsdf.inputs["Base Color"].links):
            links.remove(link)
        ao = nodes.new("ShaderNodeAmbientOcclusion")
        ao.inputs["Color"].default_value = (*color, 1)
        ao.inputs["Distance"].default_value = .8 if ink else 1.6
        ao.samples = 8
        if not ink:
            noise = next((n for n in nodes if n.type == "TEX_NOISE"), None)
            if noise:
                mineral = nodes.new("ShaderNodeValToRGB")
                mineral.color_ramp.elements[0].color = tuple(c * .65 for c in color) + (1,)
                mineral.color_ramp.elements[1].color = tuple(c * 1.25 for c in color) + (1,)
                links.new(noise.outputs["Fac"], mineral.inputs["Fac"])
                links.new(mineral.outputs["Color"], ao.inputs["Color"])
        links.new(ao.outputs["Color"], bsdf.inputs["Base Color"])
        _set(bsdf, ("Metallic",), 0 if ink else (.45 if "steel" in name else .05))
        _set(bsdf, ("Roughness",), .85 if ink else .64)
        _set(bsdf, ("Transmission Weight", "Transmission"), 0)
        if ink:
            for link in list(bsdf.inputs["Normal"].links):
                links.remove(link)
        if name == "accent":
            _set(bsdf, ("Emission Color",), (*color, 1))
            _set(bsdf, ("Emission Strength",), .1 if ink else .8)


def configure_scene(scene, data, look, camera, res=(3840, 2160),
                    samples=128, preview=False):
    if look not in LOOKS:
        raise ValueError(f"look must be one of {LOOKS}")
    scene["girders_look"] = look
    _art_materials(look)
    haze = _world(scene, look)
    if look == "mineral" and camera == "section":
        haze *= .38  # longer sight line: keep the near structure legible
    scene["girders_haze_density"] = haze
    if haze:
        _haze_box(scene, data, haze, look)
    _light_rig(scene, look, data, camera)
    lo, hi = _bounds(data)
    bpy.ops.mesh.primitive_plane_add(size=max((hi - lo).length * 80, 10000),
                                    location=((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z - .03))
    ground = bpy.context.object
    ground.name = "Girders | surrounding ground"
    ground_mat = bpy.data.materials.new("Girders | ground")
    ground_mat.use_nodes = True
    ground_bsdf = ground_mat.node_tree.nodes.get("Principled BSDF")
    ground_bsdf.inputs["Base Color"].default_value = ((.76, .74, .69, 1) if look == "ink" else (.12, .135, .14, 1))
    ground_bsdf.inputs["Roughness"].default_value = .93
    ground.data.materials.append(ground_mat)
    width, height = res
    if preview:
        width, height = max(1, width // 4), max(1, height // 4)
        samples = min(samples, 16)
    scene.render.resolution_x = int(width)
    scene.render.resolution_y = int(height)
    scene.render.resolution_percentage = 100
    scene.render.pixel_aspect_x = scene.render.pixel_aspect_y = 1
    cam, spec = _camera(scene, look, data, camera)
    _engine(scene, samples, preview)
    scene.view_settings.exposure = {
        "overcast": .05, "low_sun": .35, "night": .55,
        "mineral": .65, "ink": .1,
    }[look]
    if look == "ink":
        cam.data.dof.use_dof = False
        scene.cycles.adaptive_threshold = .008
        scene.cycles.use_denoising = False
        scene.view_settings.view_transform = "Standard"
        scene.view_settings.look = "None"
    return cam, spec


def _git(*args):
    try:
        return subprocess.check_output(
            ["git", "-C", str(REPO), *args], text=True,
            stderr=subprocess.DEVNULL).strip()
    except Exception:
        return ""


def _gpu_info():
    try:
        return subprocess.check_output([
            "nvidia-smi", "--query-gpu=name,utilization.gpu,memory.used,memory.total",
            "--format=csv,noheader",
        ], text=True, timeout=5).strip()
    except Exception:
        return "unavailable"


def _wait_for_capture():
    """Respect the shared GPU even when build.py is invoked directly."""
    while True:
        busy = []
        for proc in Path("/proc").iterdir():
            if not proc.name.isdigit():
                continue
            try:
                args = (proc / "cmdline").read_bytes().decode().split("\0")
            except (OSError, UnicodeError):
                continue
            if not args:
                continue
            executable = Path(args[0]).name
            if (executable == "Rack" or
                    (executable.startswith("python") and
                     ("gorgon.capture" in args or
                      any(Path(arg).name == "capture_existing_jack.py" for arg in args)))):
                busy.append(proc.name)
        if not busy:
            return
        print("GIRDERS_GPU_WAIT capture/Rack PIDs=" + ",".join(busy), flush=True)
        time.sleep(10)


def render_scene(scene, data, materials, scene_path, out_dir, look, camera,
                 res_text, samples, preview, want_exr, build_stats):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        resolution = tuple(int(x) for x in res_text.lower().split("x"))
        if len(resolution) != 2:
            raise ValueError
    except Exception as exc:
        raise ValueError(f"invalid resolution {res_text!r}; expected WIDTHxHEIGHT") from exc
    start = time.perf_counter()
    cam, camera_spec = configure_scene(
        scene, data, look, camera, resolution, samples, preview,
    )
    scan_name = Path(scene_path).name.replace(".json.gz", "").replace(".json", "")
    stem = f"{scan_name}-{look}-{cam.name.rsplit('|', 1)[-1].strip().replace(' ', '-')}"
    png = out_dir / (stem + ".png")
    exr = out_dir / (stem + ".exr")
    blend = out_dir / (stem + ".blend")
    scene.render.image_settings.file_format = "OPEN_EXR" if want_exr else "PNG"
    scene.render.image_settings.color_mode = "RGB"
    if want_exr:
        scene.render.image_settings.color_depth = "32"
        scene.render.image_settings.exr_codec = "ZIP"
        scene.render.filepath = str(exr)
        first_output = exr
    else:
        scene.render.image_settings.color_depth = "16"
        scene.render.image_settings.compression = 20
        scene.render.filepath = str(png)
        first_output = png
    bpy.ops.wm.save_as_mainfile(filepath=str(blend.resolve()))
    print(f"GIRDERS_RENDERING {first_output} {scene.render.resolution_x}x{scene.render.resolution_y} "
          f"samples={scene.cycles.samples}", flush=True)
    _wait_for_capture()
    bpy.ops.render.render(write_still=True)
    elapsed = time.perf_counter() - start
    if want_exr:
        if not exr.is_file() or exr.stat().st_size == 0:
            raise RuntimeError(f"Cycles did not write {exr}")
        rendered = bpy.data.images.load(str(exr), check_existing=False)
        scene.render.image_settings.file_format = "PNG"
        scene.render.image_settings.color_depth = "16"
        scene.render.image_settings.compression = 20
        rendered.save_render(str(png), scene=scene)
        bpy.data.images.remove(rendered)
    if not png.is_file() or png.stat().st_size == 0:
        raise RuntimeError(f"render did not write {png}")
    script_hashes = {}
    for name in ("build.py", "look.py", "render.py", "testscene.py"):
        path = ROOT / name
        if path.exists():
            script_hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    provenance = {
        "scene": str(Path(scene_path).resolve()),
        "scene_sha256": hashlib.sha256(Path(scene_path).read_bytes()).hexdigest(),
        "blender_version": bpy.app.version_string,
        "script_commit": _git("rev-parse", "HEAD"),
        "script_dirty": bool(_git("status", "--porcelain", "--", "studies/girders")),
        "script_sha256": script_hashes,
        "generator": data.get("generator", {}),
        "look": look,
        "atmosphere_density": scene.get("girders_haze_density", 0),
        "camera": camera_spec,
        "resolution": [scene.render.resolution_x, scene.render.resolution_y],
        "samples": scene.cycles.samples,
        "denoiser": scene.cycles.denoiser if scene.cycles.use_denoising else None,
        "denoising": scene.cycles.use_denoising,
        "preview": bool(preview),
        "build": build_stats,
        "render_seconds": round(elapsed, 3),
        "outputs": {"png": str(png), "exr": str(exr) if want_exr else None,
                    "blend": str(blend)},
        "gpu": _gpu_info(),
    }
    (out_dir / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    return provenance
