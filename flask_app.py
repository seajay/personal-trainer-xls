import os, time
from flask import Flask, request, redirect, url_for, render_template, send_from_directory
from werkzeug.utils import secure_filename

import pandas as pd
import sqlite3
from datetime import datetime


UPLOAD_FOLDER = os.path.dirname(os.path.abspath(__file__)) + '/uploads/'
DOWNLOAD_FOLDER = os.path.dirname(os.path.abspath(__file__)) + '/downloads/'
ALLOWED_EXTENSIONS = {'db'}

app = Flask(__name__, static_url_path="/static")
DIR_PATH = os.path.dirname(os.path.realpath(__file__))
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['DOWNLOAD_FOLDER'] = DOWNLOAD_FOLDER
# limit upload size upto 8mb
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'file' not in request.files:
            print('No file attached in request')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            print('No file selected')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename) + str(time.clock())
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            process_file(os.path.join(app.config['UPLOAD_FOLDER'], filename), filename)
            return redirect(url_for('uploaded_file', filename=filename + '.xls'))
    return render_template('index.html')


def process_file(path, filename):

    try:
        db = sqlite3.connect(path)
    
        history = pd.read_sql_query("select * from history", db)
        exhistory = pd.read_sql_query("select * from history_exercises", db)
        exercises = pd.read_sql_query("select * from exercises", db)
    
    except sqlite3.Error as e:
        print("Database error: %s" % e)
        exit()
    except Exception as e:
        print("Query error: %s" % e)
        exit()
    
    finally:
        if db:
            db.close()
    
    history.rename(columns={'id':'history_id'}, inplace=True)
    exhistory.rename(columns={'id':'set_id'}, inplace=True)
    exercises.rename(columns={'id':'exercise_id'}, inplace=True)
    
    history.drop(['duration', 'percentage', 'backedup', 'realdays'], axis=1, inplace=True)
    exhistory.drop(['backedup', 'percentage', 'type', 'duration'], axis=1, inplace=True)
    
    joined = pd.merge(history, exhistory, on='history_id', how = 'left')
    
    exnames = pd.merge(joined, exercises[['exercise_id', 'exercise_name']], on='exercise_id', how = 'left')
    
    exnames['date'] = exnames['date'].apply(lambda x:datetime.fromtimestamp(x/1000).isoformat(' '))
    
    exnames.to_excel(app.config['DOWNLOAD_FOLDER'] + filename + '.xls', index=False)


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['DOWNLOAD_FOLDER'], filename, as_attachment=True)
