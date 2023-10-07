import os
import re
import secrets
import yt_dlp

from flask import Blueprint, flash, redirect, render_template, request, current_app, url_for, Markup
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
    project      = os.path.join(current_app.root_path, project)
    frames_path  = video.extract_frames(video_path, subtitle_frames, frames_path_to)
    labels_path  = objectDetection.detect_object(os.path.normpath(model_path), os.path.join(current_app.root_path, os.path.normpath(frames_path)), project, name)
    sub_pos_path = subtitle.get_positioned_subtitle(subtitle_path, fps, labels_path, default_pos, class_list)
    frames_path_db = os.path.normpath(frames_path).split('/') if '/' in os.path.normpath(frames_path) else os.path.normpath(frames_path).split('\\')
    frames_path_db = ('/'.join(frames_path_db[1:]))
    labels_path_db = os.path.normpath(labels_path).split('/') if '/' in os.path.normpath(labels_path) else os.path.normpath(labels_path).split('\\')
    labels_path_db = ('/'.join(labels_path_db[1:]))
    sub_pos_path_db = os.path.normpath(sub_pos_path).split('/') if '/' in os.path.normpath(sub_pos_path) else os.path.normpath(sub_pos_path).split('\\')
    sub_pos_path_db = ('/'.join(sub_pos_path_db[1:]))
    
    db.execute("UPDATE Video SET frames_path = ?, labels_path = ? WHERE filepath = ?", (frames_path_db, labels_path_db, video_path))
    db.execute("UPDATE Subtitle SET positioned_subtitle_path = ? WHERE filepath = ?", (sub_pos_path_db, subtitle_path))
    db.commit()

def check_yt_subtitles(info_dict, type_subs):
    subtitle_dict = {}
    for code in info_dict.get(type_subs):
        try:
            language = info_dict.get(type_subs)[code][0]['name']
            subtitle_dict[code]= language
        except:
            continue
    if subtitle_dict:
        return subtitle_dict
    else:
        return False
 

@bp.route("/", methods=['GET', 'POST'])
def upload():
    db = get_db()
    message_type = ""
    if request.method == 'POST':
        if ('video' or 'subtitle') not in request.files:
            if 'video' not in request.files: flash('Video belum dimasukkan')
            elif 'subtitle' not in request.files: flash('Subtitle belum dimasukkan')
            else: flash('No video and subtitle part')
            message_type = "alert-danger"
        video    = request.files['video']
        subtitle = request.files['subtitle']
        if (video.filename or subtitle.filename) == '':
            if video.filename == "": flash('Pilih video!')
            elif subtitle.filename == "": flash('Pilih Subtitle!')
            else: flash('Pilih video dan subtitle!')
            message_type = "alert-danger"
            
        if not (request.form['model'] and request.form.getlist('objectDetection') and request.form['fontColor'] and request.form['transparency']):
            flash('Semua form harus diisi!')
            message_type = "alert-danger"
        else:
            video_name    = secure_filename(video.filename)
            subtitle_name = secure_filename(subtitle.filename)
            odmodel       = request.form['model']
            objectList    = [int(objectClass) for objectClass in request.form.getlist('objectDetection')]
            subtitlePos   = int(request.form['subtitlePosition'])
            fontColor     = request.form['fontColor']
            bgTrans       = int(request.form['transparency'])
            
            video_filename    = secure_filename(video_name)
            subtitle_filename = secure_filename(subtitle_name)
            url_path      = generate_unique_random_url(db)
            base_path     = f"static/uploads/{url_path}"
            video_path    = f"{base_path}/video/{video_filename}"
            subtitle_path = f"{base_path}/subtitle/{subtitle_filename}"
            
            video.save(os.path.join('app', video_path))
            subtitle.save(os.path.join('app', subtitle_path))
            
            # video part
            fps    = video.get_fps(os.path.join('app', video_path))
            width  = video.get_width(os.path.join('app', video_path))
            height = video.get_height(os.path.join('app', video_path))
            
            # subtitle part
            preprocessed_subtitle_path    = subtitle.process_convert_to_ass(os.path.join('app', subtitle_path), width, height)
            preprocessed_subtitle_path_db = os.path.normpath(preprocessed_subtitle_path).split('/') if '/' in os.path.normpath(preprocessed_subtitle_path) else os.path.normpath(preprocessed_subtitle_path).split('\\')
            preprocessed_subtitle_path_db = "/".join(preprocessed_subtitle_path_db[1:])
            subtitle_frames               = subtitle.process_frames_from_subtitle(preprocessed_subtitle_path, fps)
            
            # set subtitle style
            subtitle.set_style(preprocessed_subtitle_path, fontColor, bgTrans)
            db = get_db()
            db.execute("INSERT INTO Video (filename, filepath, fps, width, height) VALUES (?, ?, ?, ?, ?)", (video_name, video_path, fps, width, height))
            db.execute("INSERT INTO Subtitle (filename, filepath, preprocessed_subtitle_path, font_color, default_position, bg_transparency) VALUES (?, ?, ?, ?, ?, ?)", (subtitle_name, subtitle_path, preprocessed_subtitle_path_db, fontColor, subtitlePos, bgTrans))
            db.commit()
            
            modeldb    = db.execute('SELECT * FROM ObjectDetectionModel WHERE name = ?', (odmodel,)).fetchone()
            videodb    = db.execute('SELECT video_id FROM Video WHERE filepath = ?', (video_path,)).fetchone()
            subtitledb = db.execute('SELECT subtitle_id FROM Subtitle WHERE filepath = ?', (subtitle_path,)).fetchone()
            model_path = os.path.join(current_app.root_path, modeldb['filepath'])
            
            # run this in background
            executor.submit_stored(url_path, extract_detect_all_subtitle_frame, os.path.join('app', video_path), preprocessed_subtitle_path, subtitle_frames, subtitlePos, os.path.join('app', base_path), model_path, objectList)
            db = get_db()
            db.execute("INSERT INTO Process (url_path, video_id, subtitle_id, model_id, object_detect) VALUES (?, ?, ?, ?, ?)", (url_path, videodb['video_id'], subtitledb['subtitle_id'], modeldb['model_id'], (','.join(map(str, objectList)))))
            db.commit()
            url_preview = url_for('preview.preview_video', url_path=url_path)
            flash(Markup(f'Video sedang diproses, cek progress di <a href="{url_preview}">sini</a>'))
            message_type = "alert-success"
    return render_template("upload.html", message_type=message_type)

@bp.route('/upload-youtube/check', methods=["POST"])
def check_link():
    link = request.form['youtube_link']
    regex_youtube = r"^(?:https?:\/\/)?(?:(?:www|m)\.)?(?:youtu\.be\/|youtube(?:-nocookie)?\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=))((\w|-){11})(?:\S+)?$"
    youtube_confirm = False
    if not re.match(regex_youtube, link):
        flash("Bukan link video Youtube!")
        message_type = 'alert-warning'
        return render_template("youtube.html", confirm=youtube_confirm, message_type=message_type)
    else:
        check_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        ydl = yt_dlp.YoutubeDL(check_opts)
        try:
            info_dict = ydl.extract_info(link, download=False)
        except Exception as e:
            flash("Video tidak memiliki subtitile")
            message_type = 'alert-warning'
            return render_template("youtube.html", confirm=youtube_confirm, message_type=message_type)
        duration = info_dict.get('duration') if info_dict.get('duration') else 1000
        if duration > 900 or info_dict.get('is_live'):
            if info_dict.get('is_live'): flash("Video sedang live, tidak dapat diproses")
            else: flash("Durasi video lebih dari 15 menit")
            message_type = 'alert-warning'
            return render_template("youtube.html", confirm=youtube_confirm, message_type=message_type)
        if not (check_yt_subtitles(info_dict, 'subtitles') or check_yt_subtitles(info_dict, 'automatic_captions')):
            flash("Video tidak memiliki subtitile")
            message_type = 'alert-warning'
            return render_template("youtube.html", confirm=youtube_confirm, message_type=message_type)
        else:
            subtitles     = check_yt_subtitles(info_dict, 'subtitles') if check_yt_subtitles(info_dict, 'subtitles') else check_yt_subtitles(info_dict, 'automatic_captions')
            subtitle_type = "Subtitle" if check_yt_subtitles(info_dict, 'subtitles') else "Subtitle otomatis"
            flash(subtitle_type + " ditemukan")
            message_type = 'alert-info'
            youtube_confirm = True
            return render_template("youtube.html", confirm=youtube_confirm, message_type=message_type, youtube_link=link, subtitles=subtitles)       

@bp.route('/upload-youtube', methods=['GET', 'POST'])
def youtube():
    if request.method == 'POST':
        if (request.form['subtitle'] and request.form['model'] and request.form.getlist('objectDetection') and request.form['fontColor'] and request.form['transparency']):
            link = request.form['youtube_link']
            check_opts = {
                'quiet': True,
                'no_warnings': True,
            }
            ydl = yt_dlp.YoutubeDL(check_opts)
            info_dict = ydl.extract_info(link, download=False)
            db        = get_db()
            url_path  = generate_unique_random_url(db)
            sub_code  = request.form['subtitle']
            video_name = info_dict['title']
            subtitle_name = f"{info_dict['title']}.{sub_code}"
            video_filename    = secure_filename(f"{info_dict['title']}.mp4")
            subtitle_filename = secure_filename(f"{info_dict['title']}.{sub_code}.srv3")
            subtitle_type = "Subtitle" if check_yt_subtitles(info_dict, 'subtitles') else "Subtitle otomatis"
            url_path      = generate_unique_random_url(db)
            base_path     = f"static/uploads/{url_path}"
            video_path    = f"{base_path}/video/{video_filename}"
            subtitle_path = f"{base_path}/subtitle/{subtitle_filename}"
            odmodel       = request.form['model']
            objectList    = [int(objectClass) for objectClass in request.form.getlist('objectDetection')]
            subtitlePos   = int(request.form['subtitlePosition'])
            fontColor     = request.form['fontColor']
            bgTrans       = int(request.form['transparency'])
            os.makedirs(os.path.dirname(os.path.join('app', base_path)), exist_ok=True)
            os.makedirs(os.path.dirname(os.path.join('app', video_path)), exist_ok=True)
            os.makedirs(os.path.dirname(os.path.join('app', subtitle_path)), exist_ok=True)
            
            dl_opts  = {
                'format': 'mp4[height<720]',
                'outtmpl': os.path.join('app', base_path, video_filename),
                'subtitlesformat': 'srv3',
                'subtitleslangs': [sub_code],
                'noplaylist':True
            }
            if subtitle_type == "Subtitle": dl_opts['writesubtitles']=True
            else: dl_opts['writeautomaticsub']=True
            ydl = yt_dlp.YoutubeDL(dl_opts)
            ydl.download(link)
            
            os.rename(os.path.join('app', base_path, video_filename), os.path.join('app', video_path))
            os.rename(os.path.join('app', base_path, subtitle_filename), os.path.join('app', subtitle_path))
            # video part
            fps    = video.get_fps(os.path.join('app', video_path))
            width  = video.get_width(os.path.join('app', video_path))
            height = video.get_height(os.path.join('app', video_path))
            
            # subtitle part
            preprocessed_subtitle_path    = subtitle.process_convert_to_ass(os.path.join('app', subtitle_path), width, height)
            preprocessed_subtitle_path_db = os.path.normpath(preprocessed_subtitle_path).split('/') if '/' in os.path.normpath(preprocessed_subtitle_path) else os.path.normpath(preprocessed_subtitle_path).split('\\')
            preprocessed_subtitle_path_db = "/".join(preprocessed_subtitle_path_db[1:])
            subtitle_frames               = subtitle.process_frames_from_subtitle(preprocessed_subtitle_path, fps)
            
            # set subtitle style
            subtitle.set_style(preprocessed_subtitle_path, fontColor, bgTrans)
            
            db.execute("INSERT INTO Video (filename, filepath, fps, width, height) VALUES (?, ?, ?, ?, ?)", (video_name, video_path, fps, width, height))
            db.execute("INSERT INTO Subtitle (filename, filepath, preprocessed_subtitle_path, font_color, default_position, bg_transparency) VALUES (?, ?, ?, ?, ?, ?)", (subtitle_name, subtitle_path, preprocessed_subtitle_path_db, fontColor, subtitlePos, bgTrans))
            db.commit()
        
            modeldb    = db.execute('SELECT * FROM ObjectDetectionModel WHERE name = ?', (odmodel,)).fetchone()
            videodb    = db.execute('SELECT video_id FROM Video WHERE filepath = ?', (video_path,)).fetchone()
            subtitledb = db.execute('SELECT subtitle_id FROM Subtitle WHERE filepath = ?', (subtitle_path,)).fetchone()
            model_path = os.path.join(current_app.root_path, modeldb['filepath'])
            
            # run this in background
            extract_detect_all_subtitle_frame(os.path.join('app', video_path), preprocessed_subtitle_path, fps, subtitle_frames, subtitlePos, os.path.join('app', base_path), model_path, objectList)
            #executor.submit_stored(url_path, extract_detect_all_subtitle_frame, os.path.join('app', video_path), preprocessed_subtitle_path, fps, subtitle_frames, subtitlePos, os.path.join('app', base_path), model_path, objectList)
            db.execute("INSERT INTO Process (url_path, video_id, subtitle_id, model_id, object_detect) VALUES (?, ?, ?, ?, ?)", (url_path, videodb['video_id'], subtitledb['subtitle_id'], modeldb['model_id'], (','.join(map(str, objectList)))))
            db.commit()
            url_preview = url_for('preview.preview_video', url_path=url_path)
            flash(Markup(f'Video sedang diproses, cek progress di <a href="{url_preview}">sini</a>'))
            message_type = "alert-success"
            return render_template("youtube.html", message_type=message_type)
                
    return render_template("youtube.html")