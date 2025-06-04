import json
import os
import uuid
import shutil
import zipfile

from datetime import datetime, timedelta
from flask import Flask, request, redirect, flash, jsonify, render_template, url_for, send_file
from flask_session import Session
from werkzeug.utils import secure_filename
from apscheduler.schedulers.background import BackgroundScheduler

from sartopo2faks import classify_features

app = Flask(__name__)
sess = Session()

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
DEFAULT_EXPIRATION_TIME = timedelta(hours=24)

# Create directories if not exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

# Scheduler for handling background tasks
scheduler = BackgroundScheduler()
scheduler.start()

# In-memory dictionary to keep track of scheduled deletions
# This can be replaced with a database for persistence
scheduled_jobs = {}

@app.route('/')
def home_page():
    # Render the upload form
    return render_template('index.html')

@app.route('/about')
def about_page():
    return render_template('about.html')

@app.route('/help')
def help_page():
    return render_template('help.html')

@app.route('/privacy')
def privacy_page():
    return render_template('privacy.html')

@app.route('/tos')
def tos_page():
    return render_template('tos.html')

@app.route('/process', methods=['POST'])
def process():
    # Generate a unique job id using a UUID
    job_id = f"{uuid.uuid4()}"

    # Secure the filename and save it to UPLOAD_FOLDER
    upload_path = upload(job_id)

    # Determine the action (either 'select' or 'convert')
    action = request.form.get('action')
    if action == 'select':
        return list_features(job_id, upload_path)
    elif action == 'convert':
        return convert(job_id, upload_path, [])
    else:
        flash('Invalid action specified!', 'error')
        return redirect(request.url)

# Get the list of features from the uploaded GeoJSON file
def list_features(job_id, upload_path):
    try:
        # Open uploaded GeoJSON file
        with open(upload_path, 'r') as file:
            geojson_data = json.load(file)
            features = geojson_data.get('features', [])

        # Create a dictionary to map folderId to folder
        # names (for 'Folder' features)
        folder_mapping = {}
        for feature in features:
            folder_id = feature.get('id')
            properties = feature.get('properties', {})
            if properties.get('class', '') == 'Folder':
                if folder_id:
                    folder_mapping[folder_id] = properties.get('title', 'None')

        feature_list = []
        # Extract feature properties (like 'id' or 'name') for rendering
        for i, feature in enumerate(features):
            geometry = feature.get('geometry', {})
            properties = feature.get('properties', {})
            if geometry:
                folder_id = properties.get('folderId')
                folder_name = folder_mapping.get(folder_id, 'None')
                feature_list.append({
                    'id': i,
                    'name': f"[{folder_name}]"
                            f"[{properties.get('class', '')}] "
                            f"{properties.get('title', 'Unknown')}",
                    'folder': folder_name
                })

        return render_template('select.html',
            job_id=job_id,
            features=feature_list,
            upload_file=os.path.basename(upload_path)
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500

def upload(job_id):
    # Check if the post request has the file part
    if 'geojson_file' not in request.files:
        flash('No file uploaded!', 'error')
        return redirect(request.url)

    file = request.files['geojson_file']

    # Check if the file is selected
    if file.filename == '':
        flash('No selected file!', 'error')
        return redirect(request.url)

    # Secure the filename and save it to UPLOAD_FOLDER
    filename = secure_filename(file.filename)

    # Generate a unique folder
    unique_folder = f"job_{job_id}"
    upload_folder = os.path.join(UPLOAD_FOLDER, unique_folder)

    # Ensure the unique upload folder exists (create it if necessary)
    os.makedirs(upload_folder, exist_ok=True)

    upload_path = os.path.join(upload_folder, filename)
    file.save(upload_path)

    # Schedule the file for deletion
    delete_time = datetime.now() + DEFAULT_EXPIRATION_TIME
    scheduled_jobs[job_id] = delete_time
    scheduler.add_job(
        func=delete,
        trigger="date",
        run_date=delete_time,
        args=[job_id],  # Pass the file name to delete function
        id=job_id  # Use file name as job ID
    )

    return upload_path

def convert(job_id, upload_path, selected_ids):
    try:
        # Load original GeoJSON data
        with open(upload_path, 'r') as file:
            geojson_data = json.load(file)

        # Filter features based on user selection
        if selected_ids:
            filtered_features = [geojson_data['features'][int(i)] for i in selected_ids]
        else:
            filtered_features = geojson_data['features']

        source_data = { "features": filtered_features }

        # Prepare working on job
        unique_folder = f"job_{job_id}"

        # Output feature files to unique job folder
        sink_path = os.path.join(app.config['OUTPUT_FOLDER'], unique_folder)
        classify_features(source_data, sink_path)

        processed_files = [os.path.join(sink_path, file) for file in os.listdir(sink_path)
                           if os.path.isfile(os.path.join(sink_path, file))]

        upload_name = get_file_name_without_ext(upload_path)
        zip_path = os.path.join(
            app.config['OUTPUT_FOLDER'], unique_folder, f"{upload_name}.zip"
        )

        # Zip all files in the sink folder
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for file in processed_files:
                zipf.write(file, os.path.basename(file))

        # Return redirect URL for client to initiate automatic download
        job_url = url_for(
            'job',
            job_id=job_id,
            _external=True
        )

        return redirect(f"{job_url}?dl=1")

    except Exception as e:
        flash(f"Error while converting file: {str(e)}", 'error')
        return redirect(request.url)

@app.route('/export', methods=['POST'])
def export():
    job_id = request.form.get('job_id')
    upload_file = request.form.get('upload_file')
    selected_ids = request.form.getlist('features')  # Extract selected feature IDs
    upload_path = os.path.join(UPLOAD_FOLDER, f"job_{job_id}", upload_file)
    return convert(job_id, upload_path, selected_ids)

# Get the only file in the upload folder
def get_file_name_without_ext(file):
    return os.path.splitext(os.path.basename(file))[0]

# Get the only file in the upload folder
def get_upload_file(job_id):
    job_path = os.path.join(
        app.config['UPLOAD_FOLDER'], f"job_{job_id}"
    )
    files = [f for f in os.listdir(job_path)
        if os.path.isfile(os.path.join(job_path, f))]

    # Assuming there's only one file in the folder
    if len(files) > 0:
        # Return first file name without extension
        return files[0]
    else:
        raise FileNotFoundError("No files found in the upload folder.")

@app.route('/job/<job_id>')
def job(job_id):
    # Locate the file to download
    job_path = os.path.join(
        app.config['OUTPUT_FOLDER'], f"job_{job_id}"
    )
    if not os.path.exists(job_path):
        return redirect(url_for('home_page1'))

    upload_file = get_upload_file(job_id)
    upload_name = get_file_name_without_ext(upload_file)

    delete_url = url_for(
        'delete',
        job_id=job_id,
        _external=True
    )

    download_url = url_for(
        'download',
        job_id=job_id,
        _external=True
    )

    download_file = f"{upload_name}.zip"
    download_automatic = request.args.get('dl') == '1'

    # Calculate the hour difference
    hours = int(DEFAULT_EXPIRATION_TIME.total_seconds() / 3600)

    return render_template('job.html',
        job_id=job_id,
        upload_file = upload_file,
        download_url=download_url,
        download_file=download_file,
        download_automatic = download_automatic,
        delete_after=f"{hours} timer",
        delete_url=delete_url,
    )

@app.route('/download/<job_id>')
def download(job_id):

    upload_file = get_upload_file(job_id)
    upload_name = get_file_name_without_ext(upload_file)
    # Locate the file to download
    zip_path = os.path.join(
        app.config['OUTPUT_FOLDER'], f"job_{job_id}", f"{upload_name}.zip"
    )

    if not os.path.exists(zip_path):
        return redirect(url_for('home_page'))

    # Stream the file to the client
    response = send_file(zip_path, as_attachment=True)

    return response

@app.route('/job/<job_id>/delete', methods=['POST'])
def delete(job_id):
    # Locate job folders
    upload_path = os.path.join(
        app.config['UPLOAD_FOLDER'], f"job_{job_id}"
    )
    if os.path.exists(upload_path):
        print(f"Deleted job folder: {upload_path}")
        shutil.rmtree(upload_path)

    output_path = os.path.join(
        app.config['OUTPUT_FOLDER'], f"job_{job_id}"
    )
    if os.path.exists(output_path):
        print(f"Deleted job folder: {output_path}")
        shutil.rmtree(output_path)

    scheduled_jobs.pop(job_id)

    return redirect(url_for('home_page'))

@app.route('/job/scheduled')
def job_scheduled():
    return jsonify(scheduled_jobs)

def init_scheduler():
    # Initialize job deletions
    for folder in os.listdir(UPLOAD_FOLDER):
        folder_path = os.path.join(UPLOAD_FOLDER, folder)
        if os.path.isdir(folder_path) and folder.startswith("job_"):
            # Extract the job_id from the folder name by removing the "job_" prefix
            job_id = folder[4:]  # Extract everything after "job_"

            # Calculate delete time
            delete_time = datetime.now() + DEFAULT_EXPIRATION_TIME

            # Initialize scheduled_jobs with job_id and folder metadata
            scheduled_jobs[job_id] = delete_time

            # Schedule job
            scheduler.add_job(
                func=delete,
                trigger="date",
                run_date=delete_time,
                args=[job_id],  # Pass the file name to delete function
                id=job_id  # Use file name as job ID
            )

init_scheduler()

if __name__ == "__main__":

    # Quick test configuration. Please use proper Flask configuration options
    # in production settings, and use a separate file or environment variables
    # to manage the secret key!
    app.secret_key = 'some_secret_key'
    app.config['SESSION_TYPE'] = 'filesystem'

    sess.init_app(app)

    app.run(host="0.0.0.0")
