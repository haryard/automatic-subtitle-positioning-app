import os
import shutil
import math
import threading

from flask import Blueprint, flash, g, jsonify, redirect, render_template, current_app, request, url_for, send_file, abort
from markupsafe import Markup
from app import main
from app.db import get_db
from app.utils import subtitle
from app.extension import background_processes

bp = Blueprint('preview', __name__, url_prefix="/preview")

def calculate_aspect_ratio(width, height):
    gcd = math.gcd(width, height)
    aspect_ratio = (width // gcd, height // gcd)
    return aspect_ratio

@bp.route('/<url_path>')
def preview_video(url_path):
    db        = get_db()
    check_url = db.execute("SELECT COUNT(*) FROM Process WHERE url_path = ?", (url_path,)).fetchone()[0]
    if check_url == 0:
        flash("Video tidak ditemukan!", category='danger')
        return redirect(url_for('main.upload'))
    check_subtitle_positioning = db.execute("SELECT s.positioned_subtitle_path FROM Process AS p JOIN Subtitle AS s ON p.subtitle_id = s.subtitle_id WHERE url_path = ?", (url_path,)).fetchone()[0]
    if check_subtitle_positioning is None:
        data_db = db.execute('SELECT v.filename FROM Process AS p JOIN Video AS v ON p.video_id = v.video_id WHERE p.url_path = ?', (url_path,)).fetchone()
        flash(Markup(f"<h3>Video `{data_db['filename']}` sedang diproses</h3><p>Lama waktu proses setidaknya setengah dari durasi video</p>"), "info") 
        completed = False
        return render_template(
            'preview.html', 
            exist=check_url,
            completed=completed,
            video_title=data_db['filename'],
        )
    else:
        data_db = db.execute(
            'SELECT v.filename, v.filepath, v.height, v.width, s.preprocessed_subtitle_path, s.positioned_subtitle_path '
            'FROM Process AS p '
            'JOIN Video AS v ON p.video_id = v.video_id '
            'JOIN Subtitle AS s ON p.subtitle_id = s.subtitle_id '
            'WHERE p.url_path = ?', (url_path,)).fetchone()
        
        video_name = data_db['filename']
        video_ext  = os.path.splitext(data_db['filepath'])[-1].lstrip('.')
        video_path = data_db['filepath'].split("static/")[1]
        video_height = data_db['height']
        video_width  = data_db['width']
        aspect_ratio = calculate_aspect_ratio(video_width, video_height)
        preprocessed_sub_path  = data_db['preprocessed_subtitle_path'].split("static/")[1].replace("\\", "/")
        positioned_sub_path    = data_db['positioned_subtitle_path'].split("static/")[1].replace("\\", "/")
        
        return render_template(
            'preview.html', 
            exist=check_url, 
            video_title=video_name,
            width=video_width,
            height=video_height,
            aspect_ratio=aspect_ratio,
            extension=video_ext, 
            video_path=video_path, 
            preprocessed_subtitle_path=preprocessed_sub_path, 
            positioned_subtitle_path=positioned_sub_path,
            url_path=url_path,
            completed=True
        )
        
@bp.route('/cancel/<url_path>')
def cancel_process(url_path):
    if url_path in background_processes and background_processes[url_path].is_alive():
        background_processes[url_path].stop()
        process_path = os.path.join(current_app.root_path, 'static','uploads', url_path)
        shutil.rmtree(process_path)
        db = get_db()
        db.execute('DELETE FROM Process WHERE url_path = ?', (url_path,))
        db.commit()
    flash("Proses video berhasil dibatalkan", category='success')
    return redirect(url_for('main.upload'))

@bp.route('/delete/<url_path>')
def delete_file(url_path):
    db = get_db()
    check_url = db.execute("SELECT COUNT(*) FROM Process WHERE url_path = ?", (url_path,)).fetchone()[0]
    if check_url == 0:
        flash("Video tidak ditemukan!", category='danger')
        return render_template('upload.html')
    else:
        process_path = os.path.join(current_app.root_path, 'static','uploads', url_path)
        shutil.rmtree(process_path)
        db = get_db()
        db.execute('DELETE FROM Process WHERE url_path = ?', (url_path,))
        db.commit()
        flash("Video berhasil dihapus!", category='success')
        return redirect(url_for('main.upload'))

@bp.route('/download_sub/<url_path>')
def download_positioned_subtitle(url_path):
    db = get_db()
    check_url = db.execute("SELECT COUNT(*) FROM Process WHERE url_path = ?", (url_path,)).fetchone()[0]
    if check_url == 0:
        abort(404)
    else:
        data_db = db.execute('SELECT s.positioned_subtitle_path '
        'FROM Process AS p '
        'JOIN Subtitle AS s ON p.subtitle_id = s.subtitle_id '
        'WHERE p.url_path = ?', (url_path,)).fetchone()
        return send_file(data_db['positioned_subtitle_path'], as_attachment=True)
    
    #{{ url_for (get_subtitle_data, url_path=url_path)}}
@bp.route('/get_sub_data/<url_path>')
def get_subtitle_data(url_path):
    db = get_db()
    check_url = db.execute("SELECT COUNT(*) FROM Process WHERE url_path = ?", (url_path,)).fetchone()[0]
    if check_url == 0:
        abort(404)
    else:
        data_db = db.execute(
            'SELECT p.object_detect, s.font_color, s.default_position, s.bg_transparency, s.positioned_subtitle_path '
            'FROM Process AS p '
            'JOIN Video AS v ON p.video_id = v.video_id '
            'JOIN Subtitle AS s ON p.subtitle_id = s.subtitle_id '
            'WHERE p.url_path = ?', (url_path,)).fetchone()
        
        data = {
            'object': data_db['object_detect'].split(','),
            'position' : data_db['default_position'],
            'color' : data_db['font_color'],
            'transparency' : data_db['bg_transparency']
        }
        return jsonify(data)
    
@bp.route('/process_subtitle_edit/<url_path>', methods=['POST'])
def process_subtitle_edit(url_path):
    db = get_db()
    check_url = db.execute("SELECT COUNT(*) FROM Process WHERE url_path = ?", (url_path,)).fetchone()[0]
    if check_url == 0:
        abort(404)
    else:
        objectList    = [int(objectClass) for objectClass in request.form.getlist('objectDetection')]
        subtitlePos   = int(request.form['subtitlePosition'])
        fontColor     = request.form['fontColor']
        bgTrans       = int(request.form['transparency'])
        
        data_db = db.execute('SELECT v.fps, v.labels_path, s.preprocessed_subtitle_path, s.positioned_subtitle_path, '
        'p.object_detect, s.default_position '
        'FROM Process AS p '
        'JOIN Video AS v ON p.video_id = v.video_id '
        'JOIN Subtitle AS s ON p.subtitle_id = s.subtitle_id '
        'WHERE p.url_path = ?', (url_path,)).fetchone()
        
        subtitle_path = os.path.join(current_app.root_path, data_db['preprocessed_subtitle_path'])
        fps           = data_db['fps']
        labels_path   = os.path.join(current_app.root_path, data_db['labels_path'])
        sub_pos_path  = os.path.join(current_app.root_path, data_db['positioned_subtitle_path']) if (data_db['object_detect'].split(',') == objectList and data_db['default_position'] == subtitlePos) else subtitle.get_positioned_subtitle(subtitle_path, fps, labels_path, subtitlePos, objectList)
        sub_pos_path_db = data_db['positioned_subtitle_path']
        subtitle.set_style(sub_pos_path, fontColor, bgTrans)
        
        db.execute("UPDATE Process SET object_detect = ? WHERE url_path = ?", ((','.join(map(str, objectList))), url_path))
        db.execute("UPDATE Subtitle SET font_color = ?, "
        "default_position = ?, "
        "bg_transparency =?, "
        "positioned_subtitle_path = ? "
        "WHERE preprocessed_subtitle_path = ?", (fontColor, subtitlePos, bgTrans, sub_pos_path_db, data_db['preprocessed_subtitle_path']))
        db.commit()
        
        flash("Subtitle berhasil disesuaikan!", category='success')
        return redirect(url_for('preview.preview_video', url_path=url_path))

