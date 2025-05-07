# FHIR Facade Project

This project is a FastAPI application that provides a FHIR interface over a PostgreSQL database.

## Prerequisites

- Python 3.8+
- Poetry (or pip) for dependency management
- A running PostgreSQL instance
- Database connection details configured (this might be directly in the code or via environment variables in your deployment environment).

## Getting Started

### 1. Clone the Repository (if you haven't already)

```bash
git clone <your-repository-url>
cd <your-repository-name>
```

### 2. Create a Virtual Environment

It's highly recommended to use a virtual environment to manage project dependencies.

**Using `venv` (Python's built-in module):**

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```

**Using `conda` (if you prefer):**

```bash
conda create -n fhir-facade python=3.9  # Or your preferred Python version
conda activate fhir-facade
```

### 3. Install Dependencies

Install the required Python packages using the `requirements.txt` file:

```bash
pip3 install -r requirements.txt
```

### 4. Running PostgreSQL with Docker Compose (Recommended for Local Development)

This project includes a `docker-compose.yaml` file to easily set up a PostgreSQL database service.

**Prerequisites for Docker:**

- Docker installed and running.
- Docker Compose installed (usually comes with Docker Desktop).

To start the PostgreSQL service:

```bash
docker-compose up -d
# or if you're using a newer version of Docker Compose
# docker compose up -d
```

This command will start a PostgreSQL 15 instance.

- The database will be accessible on `localhost:5440`.
- The default user is `postgres`.
- The password is `postgres` (as defined in `docker-compose.yaml`).

To stop the service:

```bash
docker-compose down
# or
# docker compose down
```

### 5. Database Setup & Seeding

**If using Docker Compose (from step 4):**
The database server will be running. The application (`app/main.py`) is configured to automatically create the necessary tables if they don't exist when it starts.

To populate the database with initial sample data, use the `seed_database.sql` script. You'll need a PostgreSQL client like `psql`.

Run the following command from your project root after the Docker container is running:

```bash
psql -h localhost -p 5440 -U postgres -f seed_database.sql postgres
```

You will be prompted for the password, which is `postgres`.

**If using your own PostgreSQL instance:**
Ensure your PostgreSQL server is running and accessible. The application will attempt to connect to the database as configured (likely within `app/db.py` or via environment variables if you set them up). You will also need to manually create the database if it doesn't exist and then run the `seed_database.sql` script against your database, adjusting the connection parameters accordingly. For example:

```bash
# Example for a local PostgreSQL instance on default port 5432, with user 'your_user' and database 'your_db'
# psql -h localhost -p 5432 -U your_user -f seed_database.sql your_db
```

The application (`app/main.py`) is configured to automatically create the necessary tables if they don't exist when it starts.

### 6. Run the Application

Start the FastAPI application using Uvicorn:

```bash
uvicorn app.main:app --reload
```

- `app.main:app` tells Uvicorn where to find the FastAPI application instance (`app`) located in the `app/main.py` file.
- `--reload` enables auto-reloading, so the server will restart automatically when you make code changes. This is useful for development.

The application will typically be available at `http://127.0.0.1:8000`.

### 7. Access the API Documentation

Once the server is running, you can access the interactive API documentation (Swagger UI) at:

[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

And the alternative ReDoc documentation at:

[http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)


## License

This project is licensed under the MIT License - see the `LICENSE.md` file for details (You might want to create this file).
