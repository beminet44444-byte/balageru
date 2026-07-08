FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt gunicorn==23.0.0

COPY . /app

# Data directory is a mounted volume in docker-compose so it survives restarts
RUN mkdir -p /app/data

EXPOSE 5000

# A single worker keeps the JSON file locking simple and fully consistent.
# For a small restaurant this is plenty; graduate to a real database
# (see README) before scaling past one process.
CMD ["gunicorn", "-w", "1", "--threads", "4", "-b", "0.0.0.0:5000", "app:create_app()"]
