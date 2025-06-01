@echo off

REM Check if requirements.txt exists
IF NOT EXIST requirements.txt (
    echo requirements.txt not found!
    exit /b 1
)

REM Check for missing dependencies
python - <<EOF >nul 2>&1
import pkg_resources, os
requirements_file = "requirements.txt"
if os.path.exists(requirements_file):
    with open(requirements_file) as f:
        try:
            pkg_resources.require(f.read().splitlines())
        except (pkg_resources.DistributionNotFound, pkg_resources.VersionConflict):
            exit(1)
EOF

IF ERRORLEVEL 1 (
    echo Dependencies are missing. Installing...
    pip install -r requirements.txt
) ELSE (
    echo All dependencies are already installed.
)

REM Run the Python script
echo Running main.py...
python main.py