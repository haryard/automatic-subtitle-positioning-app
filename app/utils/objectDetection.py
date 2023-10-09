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
    for filename in os.listdir(label_folder):
        if filename.endswith(".txt"):
            number_part = filename.split("_")[-1]
            new_filename = number_part
            old_file_path = os.path.join(label_folder, filename)
            new_file_path = os.path.join(label_folder, new_filename)
            os.rename(old_file_path, new_file_path)
    return label_folder
