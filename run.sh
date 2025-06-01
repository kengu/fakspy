#!/bin/bash

# Setting environment variables for Flask
export FLASK_APP=main.py
export FLASK_ENV=development  # Optional: Enables debug mode for Flask

# Run Flask application
flask run