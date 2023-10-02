import os
import secrets

from flask import Blueprint, flash, g, redirect, render_template, request, current_app, url_for
from werkzeug.utils import secure_filename
from app.db import get_db
from app.utils import subtitle, video, objectDetection
from app.extension import executor

bp = Blueprint('main', __name__)

def generate_unique_random_url(db):
    while True:
        random_url = secrets.token_hex(5)
        count = db.execute("SELECT COUNT(*) FROM Process WHERE url_path = ?", (random_url,)).fetchone()[0]
        if count == 0: return random_url
        
def extract_detect_all_subtitle_frame(video_path, subtitle_path, fps, subtitle_frames, default_pos, base_path, model_path, class_list):
    frames_path_to = os.path.join(base_path, "frames")
    db = get_db()
    project,name = os.path.split(base_path)
    frames_path  = video.extract_frames(video_path, subtitle_frames, frames_path_to)
    labels_path  = objectDetection.detect_object(model_path, frames_path, project, name)
    sub_pos_path = subtitle.get_positioned_subtitle(subtitle_path, fps, labels_path, default_pos, class_list)
    
    db.execute("UPDATE Video SET frames_path = ?, labels_path = ? WHERE filepath = ?", (frames_path, labels_path, video_path))
    db.execute("UPDATE Subtitle SET positioned_subtitle_path = ? WHERE filepath = ?", (sub_pos_path, subtitle_path))
    db.commit()
    

@bp.route("/", methods=('GET', 'POST'))
def index():
    db = get_db()
    if request.method == 'POST':
        if ('video' or 'subtitle') not in request.files:
            if 'video' not in request.files: flash('No video part')
            elif 'subtitle' not in request.files: flash('No subtitle part')
            else: flash('No video and subtitle part')
            return redirect(request.url)
        video    = request.files['video']
        subtitle = request.files['subtitle']
        if (video.filename or subtitle.filename) == '':
            if video.filename == "": flash('No selected video')
            elif subtitle.filename == "": flash('No selected subtitle')
            else: flash('No selected subtitle')
            return redirect(request.url)
            
        odmodel       = request.form['model']
        objectList    = [int(objectClass) for objectClass in request.form['objectDetection'].split(',')]
        subtitlePos   = int(request.form['subtitlePosition'])
        fontColor     = request.form['fontColor']
        bgTrans       = int(request.form['transparency'])
        
        video_name    = secure_filename(video.filename)
        subtitle_name = secure_filename(subtitle.filename)
        url_path      = generate_unique_random_url(db)
        base_path     = os.path.join("static", "uploads", url_path)
        video_path    = os.path.join(base_path, "video", video_name)
        subtitle_path = os.path.join(base_path, "subtitle", subtitle_name)
        
        video.save(video_path)
        subtitle.save(subtitle_path)
        
        # video part
        fps    = video.get_fps(video_path)
        width  = video.get_width(video_path)
        height = video.get_height(video_path)
        
        # subtitle part
        preprocessed_subtitle_path = subtitle.process_convert_to_ass(subtitle_path)
        subtitle_frames            = subtitle.process_frames_from_subtitle(subtitle_path, fps)
        
        db.execute("INSERT INTO Video (filename, filepath, fps, width, height) VALUES (?, ?, ?, ?, ?)", (video_name, video_path, fps, width, height))
        db.execute("INSERT INTO Subtitle (filename, filepath, preprocessed_subtitle_path, font_color, default_position, bg_transparency) VALUES (?, ?, ?, ?, ?, ?)", (subtitle_name, subtitle_path, preprocessed_subtitle_path, fontColor, subtitlePos, bgTrans))
        db.commit()
        
        modeldb    = db.execute('SELECT * FROM ObjectDetectionModel WHERE name = ?', (odmodel,)).fetchall()
        videodb    = db.execute('SELECT * FROM Video WHERE filepath = ?', (video_path,)).fetchall()
        subtitledb = db.execute('SELECT * FROM Subtitle WHERE filepath = ?', (subtitle_path,)).fetchall()
        model_path = os.path.join(current_app.root_path, modeldb['filepath'])
        
        # run this in background
        executor.submit_stored(url_path, extract_detect_all_subtitle_frame, video_path, subtitle_path, subtitle_frames, subtitlePos, base_path, model_path, objectList)
        
        db.execute("INSERT INTO Process (url_path, video_id, subtitle_id, model_id, object_detect) VALUES (?, ?, ?, ?, ?)", (url_path, videodb['video_id'], subtitledb['subtitle_id'], modeldb['model_id'], ','.join([obj for obj in objectList])))
        db.commit()
        flash(f"Video sedang diproses cek progress di { url_for('preview', url_path=url_path) }")
    return render_template("upload.html")

