import json
import os
import logging
import subprocess
from string import Template
from pathlib import Path

import nuke

from nuke_renderpal_submission import update_paths as nuke_paths
from nuke_renderpal_submission.precheck import run_precheck
from renderpal_submission import submission

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger("Render Submission")
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
LOGGER.addHandler(ch)


def submit_render(dry_run=False):
    scene_path = os.path.normpath(nuke.root().knob('name').value())
    exr_path, mp4_path, outfile = nuke_paths.assemble_render_path()
    render_path = os.path.abspath(os.path.join(exr_path, "..", "..", ".."))

    write_node = nuke.toNode('Write1')
    if not write_node:
        nuke.alert("You need a 'Write1' node connected to render on the farm, Brudi.")
        return

    if not run_precheck(render_path, exr_path):
        return

    nuke_paths.update_write_nodes(exr_path, outfile)
    os.makedirs(mp4_path, exist_ok=True)

    nice_name = nuke_paths.assemble_render_set_name(scene_path)

    rset_dest = rf"L:\krasse_robots\00_Pipeline\Rendersets\shot_renderset_{outfile}.rset"

    cmd = assemble_cmd(
        nice_name,
        create_import_set(write_node, rset_dest),
        scene_path
    )

    LOGGER.info(f"Submitting to Renderpal with: \n{cmd}")
    print(f"Submitting to Renderpal with: \n{cmd}")

    if dry_run:
        return

    nuke.scriptSave()
    run_wake_up_bats()
    child = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    stdout_data, stderr_data = child.communicate()

    if child.returncode == 1:
        LOGGER.error(f"Submission failed with {stderr_data}")
        return

    job_id = child.returncode
    LOGGER.info(f"Submitted {nice_name} (id: {job_id})")

    imgconvert_renderset_dest = f"L:/krasse_robots/00_Pipeline/Rendersets/shot_renderset_{outfile}_imgconvert.rset"
    imgconvert_set = submission.create_renderpal_set(
        "imgconvert_renderset",
        imgconvert_renderset_dest,
        in_pattern=f'{exr_path}/{outfile}.####.exr'.replace("\\", "/"),
        out_file=f"{mp4_path}/{outfile}.mp4".replace("\\", "/"),
        start_frame=f"frame{nuke.toNode('Read1')['first'].value()}",
        end_frame=f"frame{nuke.toNode('Read1')['last'].value()}",
        colorspace="srgb",
        pythonscript="L:/krasse_robots/00_Pipeline/Packages/renderpal_submission/renderpal_submission/autocomp/imgconvert.py"
    )
    imgconvert_jid = submission.submit(
        f"CONVERT_{nice_name}",
        "IMGCONVERT",
        "ca-user:polytopixel",
        "Nuke/Imgconvert",
        import_set=imgconvert_set,
        project="Robo",
        dependency=job_id,
        deptype=0,
        color="125,158,192"
    )
    nuke.message(f"Submitted Imgconvert-job ({imgconvert_jid})")

    project_name, shot, version, user = nice_name.split("_")

    user_mapping_path = os.path.join(os.environ.get("PIPELINE_CONFIG_PATH"), "user_mapping.json").replace("\\", "/")
    with open (user_mapping_path, "r") as f:
        user_mapping = json.load(f)
    user=nice_name.split("_")[-1]
    user_abbr = user_mapping[user]["hdmabbr"]

    kitsu_renderset_dest = rf"L:\krasse_robots\00_Pipeline\Rendersets\shot_renderset_{outfile}_kitsu.rset"
    kitsu_set = submission.create_renderpal_set(
        "kitsu_shot_renderset",
        kitsu_renderset_dest,
        pythonscript=r"L:/krasse_robots/00_Pipeline/Packages/renderpal_submission/renderpal_submission/kitsu/kitsu_publish_shot.py",
        sequence_name=shot.split("-")[0],
        shot_name=shot.split("-")[1],
        task_name=outfile.split("_")[1],
        user_name=user_abbr,
        clippath=os.path.join(mp4_path, f"{outfile}.mp4").replace("\\", "/"),
        version=version,
        pipeconfig=os.getenv("PIPELINE_CONFIG_PATH").replace("\\", "/"),
        gazu_root="L:/krasse_robots/00_Pipeline/Packages/gazu_patched"
    )

    kitsu_jid = submission.submit(
        f"KITSU_{nice_name}",
        "Kitsu_Shot_Publish",
        "ca-user:polytopixel",
        "Python3/Kitsu Shot Publish",
        import_set=kitsu_set,
        project="Robo",
        dependency=imgconvert_jid,
        deptype=0,
        color="125,158,192"
    )
    nuke.message(f"Submitted Kitsu-job ({kitsu_jid})")


def assemble_cmd(render_name, import_set, scene_path, chunk_size=100):
    return " ".join(
        [
            f'"{get_renderpal_exe()}"',
            '-login="ca-user:polytopixel"',
            '-nj_renderer="Nuke/Robo Nuke"',
            f'-nj_splitmode="2,{chunk_size}"',
            "-retnjid",
            f'-nj_name="{render_name}"',
            '-nj_project="Robo"',
            '-nj_color "125,158,192"'
            f'-importset="{import_set}"',
            f'"{scene_path}"'
        ]
    )


def assemble_ffmpeg_cmd(render_name, import_set, dep_id):
    return " ".join(
        [
            f'"{get_renderpal_exe()}"',
            '-login="ca-user:polytopixel"',
            '-nj_renderer="Frog FFmpeg/Default"',
            "-retnjid",
            f"-nj_dependency {dep_id}",
            "-nj_deptype 0",
            f'-nj_name="{render_name}"',
            '-nj_project="Robo"',
            f'-importset="{import_set}"',
            "FFMPEG"
        ]
    )


def create_import_set(writenode, destination):
    content = """
    <RenderSet>
        <Values>
            <frames>
                <Value>{0}-{1}</Value>
            </frames>
            <writenode>
                <Value>{2}</Value>
            </writenode>
        </Values>
    </RenderSet>
    """.format(*get_frame_ramge(), writenode)
    r_set_file = destination

    with open(r_set_file, "w") as r_set:
        r_set.write(content)

    return r_set_file


def get_frame_ramge():
    return nuke.Root()["first_frame"].getValue(), nuke.Root()["last_frame"].getValue()


def run_wake_up_bats():
    LOGGER.info("Waking up computers :)")
    subprocess.Popen(
        "K:/wake_042.bat", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT
    )
    subprocess.Popen(
        "K:/wake_043.bat", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT
    )


def assemble_ffmpeg_rset(shot, version, destination):
    root_dir = Path(os.path.dirname(os.path.abspath(__file__))).parent
    search_path = nuke_paths.assemble_render_path().replace("####", "%04d")
    parent_path = os.path.dirname(nuke.root().knob("name").value())
    file = os.path.join(root_dir, "resources", "ffmpeg_rset_template.txt")

    d = {
        "input": search_path.replace(os.sep, "/"),
        "out_dir":os.path.dirname(search_path).replace(os.sep, "/"),
        "out_file": f"Shot_{shot}_{version}_qc_render.mp4",
        "start_frame": int(nuke.Root()['first_frame'].value())
    }

    with open(file, "r") as f:
        src = Template(f.read())
        result = src.substitute(d)

    r_set_file = os.path.join(destination)

    with open(r_set_file, "w") as r_set:
        r_set.write(result)

    return r_set_file


def get_renderpal_exe():
    return "C:\Program Files (x86)\RenderPal V2\CmdRC\RpRcCmd.exe"
