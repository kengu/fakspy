# Safe file read function
import fcntl
import json
import os
import shutil
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler

# Scheduler for handling background tasks
scheduler = BackgroundScheduler()
scheduler.start()

# File path to store the data
PERSISTENT_FILE = "scheduled_jobs.json"

DEFAULT_EXPIRATION_TIME = timedelta(hours=24)

def safe_read(file_path):
    if not os.path.exists(file_path):
        return {}
    with open(file_path, "r") as f:
        fcntl.flock(f, fcntl.LOCK_SH)
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = {}
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
    return data


# Safe file write function
def safe_write(file_path, data):
    with open(file_path, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            json.dump(data, f, indent=4)
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)

# Load and save jobs
def load_scheduled_jobs():
    return safe_read(PERSISTENT_FILE)

def save_scheduled_jobs(jobs):
    safe_write(PERSISTENT_FILE, jobs)

def delete_job(app, job_id):
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

    scheduled_jobs = load_scheduled_jobs()
    scheduled_jobs.pop(job_id)
    save_scheduled_jobs(scheduled_jobs)

def schedule_job(app, job_id,delete_time):
    scheduled_jobs = load_scheduled_jobs()
    scheduled_jobs[job_id] = delete_time
    save_scheduled_jobs(scheduled_jobs)
    scheduler.add_job(
        func=delete_job,
        trigger="date",
        run_date=delete_time,
        args=[app,job_id],  # Pass the file name to delete function
        id=job_id  # Use file name as job ID
    )

LOCK_FILE_PATH = "/tmp/scheduler.lock"

def init_scheduler(app):

    """Use a file lock to ensure only one instance initializes the scheduler."""
    lock_file = open(LOCK_FILE_PATH, "w")
    try:
        # Try to acquire an exclusive file lock
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        print("Lock acquired: Initializing scheduler...")

        # Load the existing scheduled_jobs from the shared file
        scheduled_jobs = load_scheduled_jobs()

        # Initialize job deletions
        for folder in os.listdir(app.config['UPLOAD_FOLDER']):
            folder_path = os.path.join(app.config['UPLOAD_FOLDER'], folder)
            if os.path.isdir(folder_path) and folder.startswith("job_"):
                # Extract the job_id from the folder name by removing the "job_" prefix
                job_id = folder[4:]  # Extract everything after "job_"

                # Calculate delete time
                delete_time = datetime.now() + DEFAULT_EXPIRATION_TIME

                # Initialize scheduled_jobs with job_id and folder metadata
                scheduled_jobs[job_id] = delete_time.isoformat()

                # Schedule job
                scheduler.add_job(
                    func=delete_job,
                    trigger="date",
                    run_date=delete_time,
                    args=[app,job_id],  # Pass the file name to delete function
                    id=job_id  # Use file name as job ID
                )

        # Save the updated scheduled_jobs to the shared file
        save_scheduled_jobs(scheduled_jobs)

    except BlockingIOError:
        print("Another instance has initialized the scheduler. Skipping...")
    finally:
        # Lock file remains open to keep the lock active
        lock_file.close()

