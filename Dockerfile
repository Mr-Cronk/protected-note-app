FROM python:3.10-alpine
WORKDIR /protected-note-app
RUN apk get update
RUN apk add --no-cache gcc musl-dev linux-headers
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN pip install --extra-index-url https://alpine-wheels.github.io/index numpy
RUN pip install --extra-index-url https://alpine-wheels.github.io/index Pillow
RUN pip install --extra-index-url https://alpine-wheels.github.io/index cffi
COPY . /protected-note-app
CMD [ "python3", "run.py" ]
