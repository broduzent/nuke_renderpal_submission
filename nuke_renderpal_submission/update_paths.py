import nuke
import logging
import os


LOGGER = logging.getLogger("Nuke Render")


def assemble_render_path(scene_path=None):
    if not scene_path:
        scene_path = os.path.normpath(nuke.root().knob('name').value())
    nice_name = assemble_render_set_name(scene_path)
    project_name, shot, version, user = nice_name.split("_")

    path_elements = os.path.normpath(scene_path).split(os.sep)
    path_elements[0] = "L:/"
    task = path_elements[-2]

    base_path = os.path.join(*path_elements[:-4]).replace("\\", "/")
    render_path = os.path.join(base_path, "Rendering")
    out_path = os.path.join(render_path, "2dRender", task, version)
    exr_path = os.path.join(out_path, "exr")
    mp4_path = os.path.join(out_path, "mp4")
    outfile = f"{shot}_{task}_{version}"

    LOGGER.info("Setting Render Paths")
    LOGGER.info(f"Setting exr path to {exr_path}")
    LOGGER.info(f"Setting mp4 path to {mp4_path}")
    LOGGER.info(f"Setting filename to {outfile}")

    return exr_path, mp4_path, outfile


def update_write_nodes(exr_path, outfile):
    node = nuke.toNode('Write1')
    current_path = node.knob("file").value()
    expected_path = os.path.join(exr_path, f"{outfile}.####.exr")
    if not current_path == expected_path:
        os.makedirs(os.path.dirname(expected_path), exist_ok=True)
        node.knob("file").setValue(expected_path.replace("\\", "/"))


def assemble_render_set_name(scene_path):
    path_elem = scene_path.split(os.sep)
    naming_elem = path_elem[-1].split("_")
    nice_name = "_".join(
        ["Robo-Comp", path_elem[4], naming_elem[-4], naming_elem[-2]]
    )
    return nice_name
