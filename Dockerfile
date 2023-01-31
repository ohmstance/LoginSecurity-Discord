FROM python:3.11.1-bullseye

WORKDIR /usr/src/app

COPY . .

ENV DEBIAN_FRONTEND=noninteractive
RUN apt update && apt-get install --no-install-recommends --yes default-libmysqlclient-dev build-essential && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.txt

CMD [ "python", "./discordbot.py" ]
