import os
import shutil

from flask import Blueprint, flash, g, redirect, render_template, request, current_app, url_for, send_file
from werkzeug.utils import secure_filename
from app.db import get_db
from app.utils import subtitle, video, objectDetection
from app.extension import executor

bp = Blueprint('preview', __name__, url_prefix="/preview")

@bp.route('/<url_path>')
def preview_video(url_path):
    db = get_db()
    check_url = db.execute("SELECT COUNT(*) FROM Process WHERE random_url = ?", (url_path)).fetchone()[0]
    if check_url == 0:
        flash("File not found!")
        return render_template('preview.html', exist=check_url)
    else:    
        data_db = db.execute('SELECT v.filename, v.filepath, s.preprocessed_subtitle_path, s.positioned_subtitle_path'
        'FROM Process AS p'
        'JOIN Video AS v ON p.video_id = v.video_id'
        'JOIN Subtitle AS s ON p.subtitle_id = s.subtitle_id'
        'WHERE p.url_path = ?', (url_path)).fetchall()
        
        video_name = data_db['v.filename']
        video_ext  = os.path.splitext(data_db['v.filepath'])
        path_temp  = os.path.normpath(data_db['v.filepath']).split(os.path.sep)
        video_path = os.path.join(*path_temp[(path_temp.index('static')) + 1])
        path_temp  = os.path.normpath(data_db['s.preprocessed_subtitle_path']).split(os.path.sep)
        preprocessed_sub_path = os.path.join(*path_temp[(path_temp.index('static')) + 1])
        path_temp             = os.path.normpath(data_db['s.positioned_subtitle_path']).split(os.path.sep)
        positioned_sub_path   = os.path.join(*path_temp[(path_temp.index('static')) + 1])
        
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
    check_url = db.execute("SELECT COUNT(*) FROM Process WHERE random_url = ?", (url_path)).fetchone()[0]
    if check_url == 0:
        flash("File not found!")
        return render_template('upload.html')
    else:
        process_path = os.path.join(current_app.root_path, 'static', url_path)
        shutil.rmtree(process_path)
        db = get_db()
        db.execute('DELETE FROM Process WHERE url_path = ?', (url_path,))
        db.commit()
        return redirect(url_for('main.index'))

@bp.route('/download_sub/<url_path>')
def download_positioned_subtitle(url_path):
    db = get_db()
    check_url = db.execute("SELECT COUNT(*) FROM Process WHERE random_url = ?", (url_path)).fetchone()[0]
    if check_url == 0:
        flash("File not found!")
        return render_template('upload.html')
    else:
        data_db = db.execute('SELECT s.positioned_subtitle_path'
        'FROM Process AS p'
        'JOIN Subtitle AS s ON p.subtitle_id = s.subtitle_id'
        'WHERE p.url_path = ?', (url_path)).fetchall()
        return send_file(data_db['s.positioned_subtitle_path'], as_attachment=True)