"""Headless PMX to FBX conversion for the local Reimu presentation asset."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import bpy


TEXTURE_SUFFIXES = {".bmp", ".png", ".jpg", ".jpeg", ".tga", ".spa", ".sph"}


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--fbx", required=True)
    parser.add_argument("--blend", required=True)
    parser.add_argument("--textures", required=True)
    parser.add_argument("--report", required=True)
    return parser.parse_args(argv)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    args = parse_args()
    source = Path(args.input).resolve()
    fbx = Path(args.fbx).resolve()
    blend = Path(args.blend).resolve()
    textures = Path(args.textures).resolve()
    report = Path(args.report).resolve()
    if not source.is_file():
        raise FileNotFoundError(source)

    for directory in (fbx.parent, blend.parent, textures, report.parent):
        directory.mkdir(parents=True, exist_ok=True)

    bpy.ops.preferences.addon_enable(module="mmd_tools")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    bpy.ops.mmd_tools.import_model(
        filepath=str(source),
        types={"MESH", "ARMATURE", "MORPHS"},
        scale=0.08,
        clean_model=True,
        remove_doubles=False,
        fix_bone_order=True,
        fix_ik_links=False,
        apply_bone_fixed_axis=False,
        rename_bones=True,
        use_underscore=False,
        log_level="INFO",
        save_log=True,
    )

    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    if not meshes or not armatures:
        raise RuntimeError(f"PMX import did not create a mesh and armature: meshes={len(meshes)}, armatures={len(armatures)}")

    for obj in bpy.context.scene.objects:
        obj.select_set(obj.type in {"MESH", "ARMATURE", "EMPTY"})

    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    bpy.ops.export_scene.fbx(
        filepath=str(fbx),
        use_selection=True,
        apply_unit_scale=True,
        apply_scale_options="FBX_SCALE_ALL",
        axis_forward="-Z",
        axis_up="Y",
        add_leaf_bones=False,
        use_armature_deform_only=True,
        bake_anim=False,
        path_mode="COPY",
        embed_textures=True,
    )
    if not fbx.is_file() or fbx.stat().st_size == 0:
        raise RuntimeError("FBX export did not produce a non-empty file.")

    copied_textures = []
    for candidate in source.parent.iterdir():
        if candidate.is_file() and candidate.suffix.lower() in TEXTURE_SUFFIXES:
            destination = textures / candidate.name
            shutil.copy2(candidate, destination)
            copied_textures.append(destination.name)

    material_names = sorted(
        {
            slot.material.name
            for mesh in meshes
            for slot in mesh.material_slots
            if slot.material is not None
        }
    )
    material_textures = {}
    for material_name in material_names:
        material = bpy.data.materials.get(material_name)
        image_names = set()
        if material is not None and material.node_tree is not None:
            for node in material.node_tree.nodes:
                image = getattr(node, "image", None)
                if image is not None and image.filepath:
                    image_names.add(Path(bpy.path.abspath(image.filepath)).name)
        material_textures[material_name] = sorted(image_names)
    bone_count = sum(len(armature.data.bones) for armature in armatures)
    vertex_count = sum(len(mesh.data.vertices) for mesh in meshes)
    result = {
        "status": "completed",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "path": str(source),
            "sha256": sha256(source),
        },
        "toolchain": {
            "blender_version": bpy.app.version_string,
            "blender_build_hash": bpy.app.build_hash.decode("ascii"),
            "mmd_tools_module": "mmd_tools",
        },
        "model": {
            "mesh_count": len(meshes),
            "armature_count": len(armatures),
            "bone_count": bone_count,
            "vertex_count": vertex_count,
            "material_count": len(material_names),
            "materials": material_names,
            "material_textures": material_textures,
        },
        "outputs": {
            "fbx_path": str(fbx),
            "fbx_sha256": sha256(fbx),
            "fbx_bytes": fbx.stat().st_size,
            "blend_path": str(blend),
            "blend_sha256": sha256(blend),
            "textures_path": str(textures),
            "textures": sorted(copied_textures),
        },
        "physics_imported": False,
    }
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("REIMU_CONVERSION_OK", json.dumps(result["model"], ensure_ascii=False))


if __name__ == "__main__":
    main()
