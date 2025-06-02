import os
import uuid
import json
import zipfile

from datetime import datetime
from werkzeug.utils import secure_filename
from flask import Flask, request, redirect, url_for, flash, jsonify, render_template, send_file
from flask_session import Session

from sartopo2faks import classify_features

app = Flask(__name__)
sess = Session()

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'

# Create directories if not exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER


@app.route('/')
def home():
    # Render the upload form
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/help')
def help_page():
    return render_template('help.html')

@app.route('/process', methods=['POST'])
def process():
    # Secure the filename and save it to UPLOAD_FOLDER
    upload_path = upload()

    # Determine the action (either 'select' or 'convert')
    action = request.form.get('action')
    if action == 'select':
        return list_features(upload_path)
    elif action == 'convert':
        return convert(upload_path, [])
    else:
        flash('Invalid action specified!', 'error')
        return redirect(request.url)

# Get the list of features from the uploaded GeoJSON file
def list_features(upload_path):
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
            features=feature_list,
            upload_path=upload_path
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500

def upload():
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

    # Generate a unique folder name using a UUID
    unique_folder = f"upload_{uuid.uuid4()}"
    upload_folder = os.path.join(UPLOAD_FOLDER, unique_folder)

    # Ensure the unique upload folder exists (create it if necessary)
    os.makedirs(upload_folder, exist_ok=True)

    upload_path = os.path.join(upload_folder, filename)
    file.save(upload_path)

    return upload_path

def convert(upload_path, selected_ids):
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

        print(source_data)

        # Generate a unique folder name using a UUID
        unique_folder = f"job_{uuid.uuid4()}"

        # Create the unique folder path
        sink_path = os.path.join(app.config['OUTPUT_FOLDER'], unique_folder)
        classify_features(source_data, sink_path)

        processed_files = [os.path.join(sink_path, file) for file in os.listdir(sink_path)
                           if os.path.isfile(os.path.join(sink_path, file))]

        upload_name = os.path.splitext(os.path.basename(upload_path))[0]
        zip_path = os.path.join(
            app.config['OUTPUT_FOLDER'], unique_folder, f"{upload_name}.zip"
        )

        # Zip all files in the sink folder
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for file in processed_files:
                zipf.write(file, os.path.basename(file))

        # Return the zip file to the client for download
        return send_file(zip_path, as_attachment=True)

    except Exception as e:
        flash(f"Error while converting file: {str(e)}", 'error')
        return redirect(request.url)

@app.route('/export', methods=['POST'])
def export():
    upload_path = request.form.get('upload_path')
    selected_ids = request.form.getlist('features')  # Extract selected feature IDs

    return convert(upload_path, selected_ids)

if __name__ == "__main__":
    # Quick test configuration. Please use proper Flask configuration options
    # in production settings, and use a separate file or environment variables
    # to manage the secret key!
    app.secret_key = 'some_secret_key'
    app.config['SESSION_TYPE'] = 'filesystem'

    sess.init_app(app)

    app.run(host="0.0.0.0")
