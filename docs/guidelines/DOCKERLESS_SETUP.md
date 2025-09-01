# Dockerless Local Development Setup

This guide explains how to set up and run the Photonix application locally without using Docker. This is intended as a workaround for situations where the Docker environment is unavailable or problematic.

## 1. Prerequisites

You will need to install several system-level dependencies. The following commands are for Debian-based systems like Ubuntu.

### 1.1. Core Services
- **PostgreSQL**: The main database for the application.
- **Redis**: Used for caching and as a message broker for Celery.

```bash
sudo apt-get update
sudo apt-get install -y postgresql postgresql-contrib redis-server
```

### 1.2. Python Environment
The project's dependencies are not compatible with very recent versions of Python. These instructions use Python 3.8.

```bash
# Add the deadsnakes PPA to get older Python versions
sudo apt-get install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt-get update

# Install Python 3.8 and its development headers
sudo apt-get install -y python3.8 python3.8-venv python3.8-dev
```

### 1.3. Image and Photo Processing Tools
These command-line utilities are used for processing photos and extracting metadata.
- **Exiftool**: For reading and writing image metadata.
- **dcraw**: For processing raw image files.

```bash
sudo apt-get install -y exiftool dcraw
```

## 2. One-Time Setup

### 2.1. Database Configuration
You need to create a PostgreSQL user and database for the application.

```bash
# Start the PostgreSQL service
sudo service postgresql start

# Create the database and user
sudo -u postgres psql -c "CREATE DATABASE photonix;"
sudo -u postgres psql -c "CREATE USER photonix WITH PASSWORD 'password';"
sudo -u postgres psql -c "GRANT ALL ON SCHEMA public TO photonix;"
```

### 2.2. Machine Learning Models
The application requires several pre-trained machine learning models.

```bash
# Create the necessary directories
sudo mkdir -p /data/models/face
sudo chown -R $USER:$USER /data

# Download the face recognition model weights
curl -L https://huggingface.co/junjiang/GestureFace/resolve/33b794e5b80359007642ecd62e0746794175be3b/facenet_weights.h5 -o /data/models/face/facenet_weights.h5
```

## 3. Running the Application

A script is provided to automate the installation of Python dependencies and the execution of the application services.

```bash
# Make the script executable
chmod +x system/run_local.sh

# Run the script
./system/run_local.sh
```

This script will:
1.  Downgrade `setuptools` to a compatible version.
2.  Install all necessary Python packages into the `python3.8` global site-packages.
3.  Run the Django database migrations.
3.  Start the following services as background processes:
    -   Celery worker
    -   Flower monitoring UI
    -   Django development server

## 4. Verification

### 4.1. Check Running Processes
You can check if the services are running with the following command:
```bash
ps aux | grep python3.8
```
You should see processes for `celery`, `flower`, and `manage.py runserver`.

### 4.2. Check Flower Dashboard
The Flower dashboard should be accessible at `http://localhost:5555`. You can check this with `curl`:
```bash
curl http://localhost:5555
```
This should return the HTML of the Flower dashboard.

### 4.3. Run a Test Task
You can verify that Celery is working by dispatching a test task.

1.  **Open a Django shell:**
    ```bash
    PYTHONPATH=. python3.8 photonix/manage.py shell
    ```

2.  **Run the task:**
    ```python
    from photonix.photos.tasks import add
    add.delay(2, 2)
    ```

3.  **Check the Flower dashboard again.** The "Processed" count should now be 1.
