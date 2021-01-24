# Pull official base image
FROM python:3.9-alpine

# Set work directory
WORKDIR /usr/src/app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install dependencies
COPY requirements.txt /usr/src/app/requirements.txt
RUN \
    apk add --no-cache python3 postgresql-libs && \
    apk add --no-cache --virtual .build-deps gcc python3-dev musl-dev postgresql-dev && \
    pip install --upgrade pip && \
    pip install -r /usr/src/app/requirements.txt && \
    apk --purge del .build-deps

# Copy project
COPY . /usr/src/app/

# Allow access from other sources
CMD ["flask", "real_estate.py"]
