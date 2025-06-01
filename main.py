import os
import uuid
import json
import zipfile

from werkzeug.utils import secure_filename
from flask import Flask, request, jsonify, render_template, send_file

from sartopo2faks import enrich_features, classify_features

app = Flask(__name__)

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


@app.route('/select', methods=['POST'])
def list_features():
    # Get the list of features from the uploaded GeoJSON file
    try:
        # Handle file upload
        if 'geojson_file' not in request.files:
            return jsonify({"error": "No file part"}), 400

        file = request.files['geojson_file']
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400

        # Save the uploaded GeoJSON file
        filename = secure_filename(file.filename)
        geojson_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(geojson_path)

        with open(geojson_path, 'r') as file:
            geojson_data = json.load(file)
            features = geojson_data.get('features', [])

        # Extract feature properties (like 'id' or 'name') for rendering
        properties_list = [feature.get('properties', {}) for i, feature in enumerate(features) ]
        feature_list = [{'id': i, 'name': f"[{properties.get('class', '')}] "
                                          f"{properties.get('title', 'Unknown')}"}
            for i, properties in enumerate(properties_list)
                if properties.get('class', '') == 'Marker'
                    or properties.get('class', '') == 'Assignment']

        return render_template('select.html',
            features=feature_list,
            file_path=geojson_path
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/export', methods=['POST'])
def export_features():
    try:
        selected_ids = request.form.getlist('features')  # Extract selected feature IDs
        geojson_path = request.form.get('geojson_path')

        # Load original GeoJSON data
        with open(geojson_path, 'r') as file:
            geojson_data = json.load(file)

        # Filter features based on user selection
        filtered_features = [geojson_data['features'][int(i)] for i in selected_ids]
        source_data = {
            "features": filtered_features,
        }

        # Classify the enriched features
        sink_path = os.path.join(app.config['OUTPUT_FOLDER'], "sink_files")
        classify_features(source_data, sink_path)

        processed_files = [os.path.join(sink_path, file) for file in os.listdir(sink_path)
                           if os.path.isfile(os.path.join(sink_path, file))]

        upload_name = os.path.splitext(os.path.basename(geojson_path))[0]

        # Zip all files in the sink folder
        zip_path = os.path.join(app.config['OUTPUT_FOLDER'], upload_name+".zip")
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for file in processed_files:
                zipf.write(file, os.path.basename(file))

        # Return the zip file to the client for download
        return send_file(zip_path, as_attachment=True)


    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/process', methods=['POST'])
def process_file():
    try:
        # Handle file upload
        if 'geojson_file' not in request.files:
            return jsonify({"error": "No file part"}), 400

        file = request.files['geojson_file']
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400

        # TODO: Check if files exists in uploads
        filename = secure_filename(file.filename)
        geojson_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(geojson_path)

        if not os.path.exists(geojson_path):
            return jsonify({"error": f"{geojson_path} not found"}), 500

        # Open the uploaded file and parse it as JSON
        with open(geojson_path, "r") as source_file:
            source_data = json.load(source_file)  # Parse JSON from file

        # Classify the enriched features
        sink_path = os.path.join(app.config['OUTPUT_FOLDER'], "sink_files")
        classify_features(source_data, sink_path)

        processed_files = [os.path.join(sink_path, file) for file in os.listdir(sink_path)
            if os.path.isfile(os.path.join(sink_path, file))]

        upload_name = os.path.splitext(os.path.basename(filename))[0]

        # Zip all files in the sink folder
        zip_path = os.path.join(app.config['OUTPUT_FOLDER'], upload_name+".zip")
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for file in processed_files:
                zipf.write(file, os.path.basename(file))

        # Return the zip file to the client for download
        return send_file(zip_path, as_attachment=True)

    except Exception as e:
        return jsonify({"error": str(e)}), 500



if __name__ == "__main__":
    app.run(host="0.0.0.0")
