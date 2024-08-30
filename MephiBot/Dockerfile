FROM alpine:3.18

# Install python/pip
ENV PYTHONUNBUFFERED=1
COPY . /app
WORKDIR /app

RUN apk add --update --no-cache python3 && ln -sf python3 /usr/bin/python && \
python3 -m ensurepip && \
pip3 install --no-cache --upgrade pip setuptools && pip install --no-cache-dir -r requirements.txt

ENTRYPOINT ["python", "bot.py"]
