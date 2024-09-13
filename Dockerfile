# pull official base image
FROM python:3.11.9

# set work directory
WORKDIR /usr/app

# copy requirements file
COPY ./requirements.txt /usr/app/requirements.txt

# install dependencies
RUN set -eux \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libssl-dev \
        libffi-dev \
        gcc \
        libc6-dev \
        python3-dev \
        cmake \
    && pip install --upgrade pip setuptools wheel \
    && pip install -r /usr/app/requirements.txt \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /root/.cache/pip

# copy project
COPY . /usr/app/

VOLUME /usr/app

CMD  ["uvicorn", "app.main:app", "--reload", "--workers", "-1", "--host", "0.0.0.0", "--port", "8000"]