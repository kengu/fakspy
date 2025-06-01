import json
import os
import sys
import geojson
import shapely
from shapely.geometry import shape

# Sink files to prepare output
sink_files = {
    "Etterretningsreflekser.geojson": {"type": "FeatureCollection", "features": []},
    "Linjer.geojson": {"type": "FeatureCollection", "features": []},
    "Mobilspor.geojson": {"type": "FeatureCollection", "features": []},
    "Punkter.geojson": {"type": "FeatureCollection", "features": []},
    "Regioner.geojson": {"type": "FeatureCollection", "features": []},
    "Soeksarealer.geojson": {"type": "FeatureCollection", "features": []},
    "Sperret.geojson": {"type": "FeatureCollection", "features": []},
    "Statistiske_reflekser.geojson": {"type": "FeatureCollection", "features": []},
}

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

def derive_category(properties):
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

    for feature in source_data["features"]:
        # Extract existing geometry and properties
        geometry = feature.get("geometry")
        properties = feature.get("properties", {})

        # Skip features with missing or invalid geometry
        if not geometry:
            continue

        if geometry.get("type", "") == "Point":
            # Map known fields to the new structure
            transformed_properties = {
                "aid": feature.get("id", ""),  # Map the unique id to aid
                "title": properties.get("title", ""),  # Use 'title' from source
                "name": properties.get("title") or feature.get("id", ""),  # Fallback to 'id' if title is missing
                "level": "Punkt",  # Assign static value
                "category": derive_category(properties),
                "class": properties.get("class"),
                "imageIds": [],  # Default empty list since no images exist in source
                "message": properties.get("description", "")  # Use 'description' for message, fallback to empty string
            }

        # Detect geometry type and add derived information
        if geometry.get("type", "") == "Polygon":
            # Calculate bounding box for Polygon geometry
            bounding_box = calculate_bounding_box(geometry["coordinates"])
            transformed_properties = {
                "id": feature.get("id", ""),  # Map the unique id to aid
                "arealId": feature.get("id", ""),  # Map the unique id to aid
                "title": properties.get("title", ""),  # Use 'title' from source
                "name": properties.get("title") or feature.get("id", ""),  # Fallback to 'id' if title is missing
                "class": properties.get("class"),
                "boundingBox": bounding_box,   # Add bounding box to properties
            }

        # Add placeholder or real related features
        transformed_properties["relatedFeatures"] = []  # Relationships can be added here later, if applicable

        # Enrich the feature with new properties
        enriched_features.append(
            geojson.Feature(
                geometry=geometry,
                properties=transformed_properties
            )
        )

    # Return the enriched data structure
    return {"type": "FeatureCollection", "features": enriched_features}


def classify_features(source_data, output_folder):
    """
    Classify features from the source data into appropriate sink files
    and write the output to the specified output folder.
    """
    # Enrich source features before classifying them
    enriched_data = enrich_features(source_data)

    for feature in enriched_data["features"]:
        feature_class = feature["properties"].get("class", "")
        feature_title = feature["properties"].get("title", "")
        feature_geometry = feature.get("geometry", None)

        # Classify based on feature class
        if feature_class == "Folder":
            # Folders themselves aren't geometric; categorize based on folder-to-sink mapping
            if feature_title in folder_to_sink:
                sink_files[folder_to_sink[feature_title]]["features"].append(feature)
        elif feature_class == "Marker":
            # All point features go to Punkter.geojson
            sink_files["Punkter.geojson"]["features"].append(feature)
        elif feature_class == "Assignment" and feature_geometry:
            # Classify shapes further by their geometry type
            if feature_geometry["type"] == "LineString":  # Line features
                sink_files["Linjer.geojson"]["features"].append(feature)
            elif feature_geometry["type"] == "Polygon":  # Polygon features
                sink_files["Soeksarealer.geojson"]["features"].append(feature)
        # Add custom classifications if needed for other classes or scenarios

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