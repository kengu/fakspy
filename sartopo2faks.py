import json
import os
import sys
import geojson

# Mapping folders to sink files (Folder titles help categorize features)
folder_to_sink = {
    "01 Etterretning": "Etterretningsreflekser.geojson",
    "02 SPOR Mannskaper": "Mobilspor.geojson",
    "04 SPOR Motorisert": "Mobilspor.geojson",
    "03 SPOR Hund m/Fører": "Mobilspor.geojson",
    "05 SPOR Luftfartøy": "Mobilspor.geojson",
    # Add more folder mappings here if needed
}


def calculate_bounding_box(coordinates):
    """
    Calculate the bounding box (minLat, maxLat, minLng, maxLng) for a given Polygon's coordinates.
    """
    lats = [point[1] for linear_ring in coordinates for point in linear_ring]
    lngs = [point[0] for linear_ring in coordinates for point in linear_ring]

    return {
        "minLat": min(lats),
        "maxLat": max(lats),
        "minLng": min(lngs),
        "maxLng": max(lngs)
    }

def derive_mission_status(features, properties):

    period_id = properties.get("operationalPeriodId", "")

    period = next(
        (feature for feature in features if feature["id"] == period_id),
        None
    )

    if period:
        title = period.get("properties", {}).get("title", "").lower()
        if title == "01 klargjorte oppdrag":
            return "empty"
        if title == "02 søkes nå":
            return "assigned"
        if title == "03 ferdig søkt":
            return "searched"

    status = properties.get("status", "").lower()
    if status == "draft":
        return "empty"
    if status == "prepared":
        return "empty"
    if status == "inprogress":
        return "assigned"
    if status == "completed":
        return "searched"

    return "empty"

def derive_point_category(properties):
    """
    Derives the 'category' field based on the given 'marker-symbol'.

    Args:
        marker_symbol (str): The marker-symbol property from the source.

    Returns:
        str: The resulting category.
    """

    title = properties.get("title", "").lower()
    marker_symbol = properties.get("marker-symbol", "").lower()

    if "oppmøte" in title:
        return "Oppmøtested"

    if "cp" in marker_symbol or "ko" in title or "kommandoplass" in title:
        return "Kommandoplass"

    if "bosted" in title or "bopel" in title or "bopæl" in title:
        return "Bosted"

    if "funn" in title:
        return "Funn av spor"

    # Add more conditions or mappings as needed
    return "Annet"

# --- Gjenkjent ---
# Oppmøtested
# Kommandoplass
# Bosted
# Funn av spor
# Annet

# --- Ikke gjenkjent ---
# Interesse av hund
# Hindring
# Ikke søkbart
# Mobilspor
# Observasjon
# Utkikkspunkt
# Sperrepost

def enrich_features(source_data):
    """
    Enrich source features by calculating bounding boxes and adding optional relationships.
    """
    enriched_features = []
    transformed_properties = {}
    source_features = source_data["features"]

    for feature in source_features:
        # Extract existing geometry and properties
        geometry = feature.get("geometry")
        properties = feature.get("properties", {})

        # Skip features with missing or invalid geometry
        if not geometry:
            continue

        feature_type = geometry.get("type", "")
        feature_class = properties.get("class", "")
        feature_title = properties.get("title", properties.get("number", ""))

        # Detect geometry type and add derived information
        if feature_class == "Assignment":
            if feature_type == "Polygon":
                transformed_properties = {
                    "aid": feature.get("id", ""),  # Map the unique id to aid
                    "title": feature_title,  # Use 'title' from source
                    "class": feature_class,
                    "category": "area",
                    "missionStatus": derive_mission_status(source_features, properties)
                }

            if feature_type == "LineString":
                transformed_properties = {
                    "aid": feature.get("id", ""),  # Map the unique id to aid
                    "title": feature_title,  # Use 'title' from source
                    "class": feature_class,
                    "category": "path",
                    "missionStatus": derive_mission_status(source_features, properties)
                }

        else:

            # Not an Assignment
            if feature_type == "Point":
                # Map known fields to the new structure
                transformed_properties = {
                    "aid": feature.get("id", ""),  # Map the unique id to aid
                    "title": properties.get("title", ""),  # Use 'title' from source
                    "class": feature_class,
                    "level": "Punkt",  # Assign static value
                    "category": derive_point_category(properties),
                    "message": properties.get(
                        "description", properties.get("message", "")
                    )
                }

            if feature_type == "Polygon":
                transformed_properties = {
                    "aid": feature.get("id", ""),  # Map the unique id to aid
                    "title": feature_title,  # Use 'title' from source
                    "class": feature_class,
                    "category": "area",
                    "missionStatus": "empty"
                }

            if feature_type == "LineString":
                transformed_properties = {
                    "aid": feature.get("id", ""),  # Map the unique id to aid
                    "title": feature_title,  # Use 'title' from source
                    "class": feature_class,
                    "category": "path",
                    "missionStatus": "empty"
                }

        # Enrich the feature with new properties
        enriched_features.append(
            geojson.Feature(
                geometry=geometry,
                properties=transformed_properties
            )
        )

    # Return the enriched data structure
    return {"type": "FeatureCollection", "features": enriched_features}

def create_sink_files():
    # Sink files to prepare output
    return {
        "Etterretningsreflekser.geojson": {"type": "FeatureCollection", "features": []},
        "Linjer.geojson": {"type": "FeatureCollection", "features": []},
        "Mobilspor.geojson": {"type": "FeatureCollection", "features": []},
        "Punkter.geojson": {"type": "FeatureCollection", "features": []},
        "Regioner.geojson": {"type": "FeatureCollection", "features": []},
        "Soeksarealer.geojson": {"type": "FeatureCollection", "features": []},
        "Sperret.geojson": {"type": "FeatureCollection", "features": []},
        "Statistiske_reflekser.geojson": {"type": "FeatureCollection", "features": []},
    }

def classify_features(source_data, output_folder):
    """
    Classify features from the source data into appropriate sink files
    and write the output to the specified output folder.
    """
    # Enrich source features before classifying them
    enriched_data = enrich_features(source_data)

    sink_files = create_sink_files()

    for feature in enriched_data["features"]:
        feature_type = feature["geometry"].get("type", "")
        feature_class = feature["properties"].get("class", "")
        feature_title = feature["properties"].get("title", "")
        feature_geometry = feature.get("geometry", None)

        # Classify based on feature class
        if feature_class == "Folder":
            # Folders themselves aren't geometric; categorize based on folder-to-sink mapping
            if feature_title in folder_to_sink:
                sink_files[folder_to_sink[feature_title]]["features"].append(feature)
        elif feature_geometry:
            if feature_type == "Point":
                # All Point features go to Punkter.geojson
                sink_files["Punkter.geojson"]["features"].append(feature)
            elif feature_type == "LineString":  # Line features
                # All LineString features go to Punkter.geojson
                sink_files["Linjer.geojson"]["features"].append(feature)
            elif feature_type == "Polygon":  # Polygon features
                sink_files["Soeksarealer.geojson"]["features"].append(feature)

    # Ensure the output folder exists (create it if necessary)
    os.makedirs(output_folder, exist_ok=True)

    # Write output to sink files
    for sink_file, content in sink_files.items():
        file_path = os.path.join(output_folder, sink_file)  # Write each sink file to the output folder
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(content, f, ensure_ascii=False, indent=2)

    print(f"Features successfully classified and written to sink files in '{output_folder}'!")


if __name__ == "__main__":
    # Check command-line arguments
    if len(sys.argv) != 3:
        print("Usage: python sartopo2faks.py <source_file> <output_folder>")
        sys.exit(1)

    # Get arguments from the command line
    source_file = sys.argv[1]
    output_folder = sys.argv[2]

    # Load the source GeoJSON data
    try:
        with open(source_file, "r", encoding="utf-8") as f:
            source_data = json.load(f)
    except Exception as e:
        print(f"Error reading source file '{source_file}': {e}")
        sys.exit(1)

    # Run feature classification
    classify_features(source_data, output_folder)