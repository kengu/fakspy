@echo off

:: Setting environment variables for Flask
set FLASK_APP=main.py
set FLASK_ENV=development  :: Optional: Enables debug mode for Flask

:: Run Flask application
flask run