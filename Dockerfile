FROM python:3.11.1-bullseye AS builder

COPY requirements.txt .

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install --no-install-recommends --yes default-libmysqlclient-dev build-essential && rm -rf /var/lib/apt/lists/*
RUN pip install --user --no-cache-dir -r requirements.txt

FROM python:3.11.1-slim-bullseye

WORKDIR /usr/src/app

RUN apt-get update && apt-get install --no-install-recommends --yes default-libmysqlclient-dev && rm -r /var/lib/apt/lists*

COPY --from=builder /root/.local /root/.local
COPY . .

ENV PATH=/root/.local:$PATH

CMD [ "python", "./discordbot.py" ]
