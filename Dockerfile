# Dockerfile
## Build 
FROM python:3.10.4-slim-buster as build 

# Install curl, build-base and libffi-dev
RUN apt-get update && \
     apt-get install -y curl build-essential libffi-dev \
     && rm -rf /var/lib/apt/lists/* \
     && apt-get clean

# Install poetry
RUN curl -sSL https://install.python-poetry.org | python3 - --version 1.3.2
ENV PATH /root/.local/bin:$PATH

#Set Working directory and copy files
WORKDIR /app
COPY pyproject.toml poetry.lock ./

# The `--copies` option tells `venv` to copy libs and binaries
# instead of using symlinks
RUN python -m venv --copies /app/venv
RUN . /app/venv/bin/activate && poetry install --no-dev

# Deploy
FROM python:3.10.4-slim-buster as deploy 

COPY --from=build /app/venv /app/venv
ENV PATH /app/venv/bin:$PATH

#Set Working directory and copy app files
WORKDIR /app
COPY . .

# Import requests
CMD python -c "import requests"

# Healthcheck on the application
HEALTHCHECK --start-period=30s CMD python -c "requests.get('http://localhost:8000/health', timeout=2)"

EXPOSE 8000
#Application entry
CMD ["uvicorn", "hesaving.main:app", "--host", "0.0.0.0", "--port", "8000"]