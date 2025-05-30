from flask import Flask, request, jsonify, render_template, send_file
from werkzeug.utils import secure_filename
import os
import zipfile
from sartopo2faks import calculate_bounding_box, derive_category, enrich_features, classify_features

app = Flask(__name__)

UPLOAD_FOLDER = './uploads'
OUTPUT_FOLDER = './output'

# Create directories if not exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER


@app.route('/')
def home():
    # Render the upload form
    return render_template('index.html')


import json


@app.route('/process', methods=['POST'])
def process_file():
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

        # Actual processing logic using key functions and attributes
        from sartopo2faks import calculate_bounding_box, derive_category, enrich_features, classify_features

        processed_files = []

        # Open the uploaded file and parse it as JSON
        with open(geojson_path, "r") as source_file:
            source_data = json.load(source_file)  # Parse JSON from file

        # Enrich the data
        enriched_data = enrich_features(source_data)

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
    app.run(debug=True)
