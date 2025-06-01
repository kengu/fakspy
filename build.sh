#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Check if requirements.txt exists
if [ ! -f "requirements.txt" ]; then
    echo "requirements.txt not found!"
    exit 1
fi

# Function to check for missing dependencies
missing_deps() {
    python3 - <<EOF
import pkg_resources, os
requirements_file = "requirements.txt"
if os.path.exists(requirements_file):
    with open(requirements_file) as f:
        try:
            pkg_resources.require(f.read().splitlines())
        except pkg_resources.DistributionNotFound:
            print("missing")
        except pkg_resources.VersionConflict:
            print("missing")
EOF
}

# Check for missing dependencies
if [ "$(missing_deps)" == "missing" ]; then
    echo "Dependencies are missing. Installing..."
    pip install -r requirements.txt
else
    echo "All dependencies are already installed."
fi