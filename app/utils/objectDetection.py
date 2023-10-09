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

def rename_labels(filepath):
    for filename in os.listdir(filepath):
        if filename.endswith(".txt"):
        # Extract the number part of the filename
            number_part = filename.split("_")[1]

            # Create the new filename
            new_filename = f"{number_part}.txt"

            # Construct the full paths
            old_file_path = os.path.join(filepath, filename)
            new_file_path = os.path.join(filepath, new_filename)

            # Rename the file
            os.rename(old_file_path, new_file_path)