import os
import shutil

from flask import Blueprint, flash, g, jsonify, redirect, render_template, current_app, request, url_for, send_file, abort
from app import main
from app.db import get_db
from app.utils import subtitle
from app.extension import executor

bp = Blueprint('preview', __name__, url_prefix="/preview")

@bp.route('/<url_path>')
def preview_video(url_path):
    db = get_db()
    check_url = db.execute("SELECT COUNT(*) FROM Process WHERE url_path = ?", (url_path,)).fetchone()[0]
    #print(executor.futures.done(url_path))
    if check_url == 0:
        flash("File not found!")
        return redirect(url_for('main.upload'))
    #if not executor.futures.done(url_path):
    #    data_db = db.execute('SELECT v.filename FROM Process AS p JOIN Video AS v ON p.video_id = v.video_id WHERE p.url_path = ?', (url_path,)).fetchone()
    #    flash(f"Video {data_db['filename']} sedang diproses...") 
    #    message_type = "alert-info"
    #    completed = False
    #    return render_template(
    #        'preview.html', 
    #        exist=check_url,
    #        message_type = message_type,
    #        completed=completed
    #    )
    else:
        data_db = db.execute(
            'SELECT v.filename, v.filepath, s.preprocessed_subtitle_path, s.positioned_subtitle_path '
            'FROM Process AS p '
            'JOIN Video AS v ON p.video_id = v.video_id '
            'JOIN Subtitle AS s ON p.subtitle_id = s.subtitle_id '
            'WHERE p.url_path = ?', (url_path,)).fetchone()
        
        video_name = data_db['filename']
        video_ext  = os.path.splitext(data_db['filepath'])[-1].lstrip('.')
        video_path = data_db['filepath'].split("static/")[1]
        preprocessed_sub_path  = data_db['preprocessed_subtitle_path'].split("static/")[1].replace("\\", "/")
        positioned_sub_path    = data_db['positioned_subtitle_path'].split("static/")[1].replace("\\", "/")
        
        return render_template(
            'preview.html', 
            exist=check_url, 
            video_title=video_name, 
            extension=video_ext, 
            video_path=video_path, 
            preprocessed_subtitle_path=preprocessed_sub_path, 
            positioned_subtitle_path=positioned_sub_path,
            url_path=url_path
        )
        
@bp.route('/delete/<url_path>')
def delete_file(url_path):
    db = get_db()
    check_url = db.execute("SELECT COUNT(*) FROM Process WHERE url_path = ?", (url_path,)).fetchone()[0]
    if check_url == 0:
        flash("File not found!")
        return render_template('upload.html')
    else:
        process_path = os.path.join(current_app.root_path, 'static', url_path)
        shutil.rmtree(process_path)
        db = get_db()
        db.execute('DELETE FROM Process WHERE url_path = ?', (url_path,))
        db.commit()
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
        
        data_db = db.execute('SELECT v.fps, v.labels_path, s.preprocessed_subtitle_path '
        'FROM Process AS p '
        'JOIN Video AS v ON p.video_id = v.video_id '
        'JOIN Subtitle AS s ON p.subtitle_id = s.subtitle_id '
        'WHERE p.url_path = ?', (url_path,)).fetchone()
        
        subtitle_path = os.path.join('app', data_db['preprocessed_subtitle_path'])
        fps           = data_db['fps']
        labels_path   = os.path.join('app', data_db['labels_path'])
        sub_pos_path  = subtitle.get_positioned_subtitle(subtitle_path, fps, labels_path, subtitlePos, objectList)
        sub_pos_path_db = os.path.normpath(sub_pos_path).split('/') if '/' in os.path.normpath(sub_pos_path) else os.path.normpath(sub_pos_path).split('\\')
        sub_pos_path_db = ('/'.join(sub_pos_path_db[1:]))
        subtitle.set_style(sub_pos_path, fontColor, bgTrans)
        
        db.execute("UPDATE Subtitle SET positioned_subtitle_path = ? WHERE preprocessed_subtitle_path = ?", (sub_pos_path_db, data_db['preprocessed_subtitle_path']))
        db.commit()
        
        positioned_sub_path    = sub_pos_path.split('static/')[1].replace("\\", "/")
        
        return jsonify(url_for('static', filename=positioned_sub_path))
        
        
        