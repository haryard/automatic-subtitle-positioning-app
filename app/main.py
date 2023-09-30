import functools

from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename

from app.db import get_db

bp = Blueprint('main', __name__)

@bp.route("/", methods=('GET', 'POST'))
def index():
    if request.method == 'POST':
        video        = request.files['video'].filename
        subtitle     = request.files['subtitle'].filename
        odmodel      = request.form['model']
        objectDetect = request.form['objectDetection']
        subtitlePos  = request.form['subtitlePosition']
        fontColor    = request.form['fontColor']
        bgTrans      = request.form['transparency']
        
        flash(f"video: '{video}', subtitle: '{subtitle}', odmodel: {odmodel}, objectDetect: {objectDetect}, subtitlePos: {subtitlePos}, fontColor: {fontColor}, bgTrans: {bgTrans}")
    return render_template("upload.html")

