import nuke
import os

def run_precheck(render_path, exr_path):
    if not os.path.isdir(render_path):
        return False

    if os.path.isdir(exr_path):
        return nuke.ask("Brudi, diese Version wurde schon mal auf die Farm geschickt.\nBist du sicher, dass du mögliche Files überschreiben willst?")

    return True
