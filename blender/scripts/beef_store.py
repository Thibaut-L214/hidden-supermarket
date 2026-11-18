"""Refrigerated scannable beef shelf; geometry stays within the north-wall opening.

An open chilled case: dark outer shell, white liner, cool LED strips down both sides and under
the canopy, film-wrapped trays (glossy: clearcoat) with a generic printed label, printed shelf
edges. Labels come from the fictitious atlas (pack_atlas.py): bars for text, no price, no claim.
"""

import pack_atlas as atlas
import store_props as props
from common import MeshBuilder, bevel, box, empty, helper_volume, material


def _film(mat, roughness: float, coat: float) -> None:
    """Plastic film look: low roughness under a clear coat (KHR_materials_clearcoat in the GLB)."""
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Coat Weight"].default_value = coat
    bsdf.inputs["Coat Roughness"].default_value = 0.06


def beef_shelf(root, M):
    shelf = empty("SHELF_BEEF_ROOT", (6, 8.4, 0), root)
    shelf["chainId"] = "beef"
    tray = material("M_BEEF_TRAY", "#ECE7DA", roughness=0.3)
    meat = material("M_BEEF_PACKAGED", "#98594F", roughness=0.22)
    _film(meat, 0.22, 1.0)
    dark = material("M_BEEF_REFRIGERATOR", "#59686A", metallic=0.3)
    liner, led = props.M["fridge_inner"], props.M["fridge_led"]
    for side, label in ((-1, "L"), (1, "R")):
        hinge = empty("HINGE_BEEF_" + label, (side * 1.5, 0, 0), shelf)
        # Trays are open underneath and labels are single faces: windings are kept as built.
        frame, goods = MeshBuilder(), MeshBuilder(recalc_normals=False)
        labels = MeshBuilder(recalc_normals=False)
        x0, x1 = (0, 1.5) if side < 0 else (-1.5, 0)
        # Shell: back, kick plate, canopy, side posts.
        frame.box((x0, 0.55, 0.1), (x1, 0.6, 2.2), dark)
        frame.box((x0, 0, 0), (x1, 0.6, 0.12), dark)
        frame.box((x0, -0.03, 2.08), (x1, 0.6, 2.2), dark)
        for x in (x0, x1 - 0.04):
            frame.box((x, 0, 0.1), (x + 0.04, 0.6, 2.1), dark)
        # Liner: back, both sides and the underside of the canopy.
        frame.box((x0 + 0.04, 0.538, 0.12), (x1 - 0.04, 0.55, 2.08), liner)
        frame.box((x0 + 0.04, 0.02, 0.12), (x0 + 0.046, 0.538, 2.08), liner)
        frame.box((x1 - 0.046, 0.02, 0.12), (x1 - 0.04, 0.538, 2.08), liner)
        frame.box((x0 + 0.046, 0.05, 2.068), (x1 - 0.046, 0.538, 2.08), liner)
        # LED strips: down each side behind the posts, and along the canopy.
        for x in (x0 + 0.05, x1 - 0.064):
            frame.box((x, 0.022, 0.16), (x + 0.014, 0.036, 2.04), led)
        frame.box((x0 + 0.07, 0.022, 2.05), (x1 - 0.07, 0.04, 2.064), led)
        for level, z in enumerate((0.14, 0.61, 1.08, 1.55)):
            frame.box((x0 + 0.046, 0, z), (x1 - 0.046, 0.538, z + 0.025), liner)
            frame.box((x0, -0.015, z - 0.035), (x1, 0.015, z + 0.025), props.M["rail"])
            for i in range(5):
                x = x0 + 0.045 + i * 0.29
                cell = atlas.uv(atlas.rail((level * 2 + i + (side > 0)) % 4))
                props.pack_box(labels, (x, -0.0165, z - 0.035), (x + 0.25, 0.0, z + 0.025), {"-y": cell})
                for row, y in enumerate((0.07, 0.32)):
                    top = z + 0.055
                    goods.box((x, y, z + 0.025), (x + 0.25, y + 0.2, top), tray, skip=("-z",))
                    # Raised rim: the meat sits in the tray, under the film.
                    for rx0, ry0, rx1, ry1 in ((x, y, x + 0.25, y + 0.012), (x, y + 0.188, x + 0.25, y + 0.2), (x, y + 0.012, x + 0.012, y + 0.188), (x + 0.238, y + 0.012, x + 0.25, y + 0.188)):
                        goods.box((rx0, ry0, top), (rx1, ry1, top + 0.012), tray, skip=("-z",))
                    if side < 0:
                        goods.ellipsoid((x + 0.118, y + 0.104, top + 0.008), (0.092, 0.07, 0.026), meat, u=8, v=5)
                    else:
                        # Fine separate ridges distinguish minced beef from a smooth steak.
                        goods.box((x + 0.025, y + 0.03, top), (x + 0.2, y + 0.175, top + 0.014), meat, skip=("-z",))
                        for strand in range(6):
                            sy = y + 0.036 + strand * 0.023
                            dx = 0.008 if strand % 2 else 0
                            goods.box((x + 0.03 + dx, sy, top + 0.014), (x + 0.195 - dx, sy + 0.012, top + 0.026), meat, skip=("-z",))
                    # Generic printed label on the film, in the corner clear of the meat.
                    lx = x + 0.152
                    props.pack_box(labels, (lx, y + 0.014, top), (lx + 0.085, y + 0.061, top + 0.0135), {"+z": atlas.uv(atlas.tray_label(i + row))})
        door = bevel(frame.build("DOOR_BEEF_" + label, parent=hinge), 0.006)
        # Lit from within: no baked occlusion on the case (it reads as a black box otherwise).
        door["ao_skip"] = True
        goods.build("DOOR_BEEF_" + label + "_GOODS", parent=door)
        prints = labels.build("DOOR_BEEF_" + label + "_LABELS", parent=door)
        prints["uv_authored"] = True
        prints["ao_skip"] = True
        product = "STEAK" if side < 0 else "MINCE"
        sign = MeshBuilder().box((-0.67, -0.015, -0.08), (0.67, 0.015, 0.08), M["sign"]).build(
            "PRODUCT_SIGN_BEEF_" + product, ((x0 + x1) / 2, -0.04, 1.95), door)
        sign["label"] = "Steaks" if side < 0 else "Viande hachée"
        helper_volume(MeshBuilder().box((x0, 0, 0), (x1, 0.6, 2.2)).build("COL_DOOR_BEEF_" + label, parent=door))
    helper_volume(box("SCAN_BEEF", (4.5, 8.4, 0), (7.5, 9, 2.2), None, shelf))
    helper_volume(box("TRIGGER_BEEF_ENTRY", (4.5, 8.4, 0), (7.5, 9.6, 2.2), None, shelf))
    box("STORE_THRESHOLD_BEEF", (4.5, 9, -0.1), (7.5, 9.3, 0), M["floor"], shelf)
    empty("ANCHOR_BEEF_TERRACE", (0, 0.9, 0), shelf)
    box("SIGN_BEEF", (5.1, 8.96, 2.45), (6.9, 9, 2.95), M["sign"], shelf)
    box("PICTO_SCAN_BEEF", (7, 8.96, 2.5), (7.4, 9, 2.9), M["sign"], shelf)
