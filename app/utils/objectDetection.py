import os
import subprocess
from flask import current_app

def detect_object(model_path: str, source: str, project: str, name:str):
    path = current_app.root_path
    detect = os.path.join(path, "ext/yolov7/detect.py")
    command = ['python',
            detect,
            '--no-trace',
            '--nosave',
            '--save-txt',
            '--exist-ok',
            '--img-size', '640',
            '--weights', model_path,
            '--conf', '0.6',
            '--source', source,
            '--project', project,
            '--name', name]
    subprocess.run(command, check=True)

    label_folder = os.path.join(project, name, "labels")
    return label_folder