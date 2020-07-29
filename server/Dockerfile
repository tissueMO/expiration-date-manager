FROM python:3.7

# 依存パッケージのインストール
RUN apt-get update && apt-get install -y \
    apache2 \
    apache2-dev \
    wget \
    ca-certificates \
    make \
    gcc \
    musl-dev \
    build-essential \
    zlib1g-dev \
    libssl-dev \
    libffi-dev \
    sqlite3 \
    libsqlite3-dev \
    libbz2-dev \
    libncurses5-dev \
    libgdbm-dev \
    liblzma-dev \
    libssl-dev \
    tcl-dev \
    tk-dev \
    libreadline-dev \
 && apt-get clean \
 && apt-get autoremove \
 && rm -rf /var/lib/apt/lists/*

# mod_wsgi のソースインストール
RUN wget -O /tmp/mod_wsgi.tar.gz https://github.com/GrahamDumpleton/mod_wsgi/archive/4.5.6.tar.gz && \
    tar -C /tmp -xvf /tmp/mod_wsgi.tar.gz && \
    rm /tmp/mod_wsgi.tar.gz
WORKDIR /tmp/mod_wsgi-4.5.6
RUN ./configure CFLAGS=-fPIC --with-python=/usr/local/bin/python3 --with-apxs=/usr/bin/apxs && \
    make && make install

WORKDIR /var/www/apache-flask

# サーバーアプリケーションの依存パッケージのインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
 && pip freeze

# Apache の mod_wsgi に関する設定ファイルを適用
COPY apache-flask.conf /etc/apache2/sites-available/apache-flask.conf
RUN a2ensite apache-flask
RUN a2enmod headers

# WSGI Web アプリケーションをホストから丸ごとコピー
ADD app app
ADD migrate migrate
ADD model model
COPY apache-flask.wsgi .
COPY alembic.ini .
COPY logging.ini .
# COPY settings.conf .
RUN mkdir /var/www/apache-flask/db

# Apache の mod_wsgi に関する設定ファイルを適用
RUN a2dissite 000-default.conf
RUN a2ensite apache-flask.conf

# コンテナー側のポートを開ける
EXPOSE 80
EXPOSE 5000

# DBマイグレーションを実行、デフォルトのレコードを流し込む
RUN alembic upgrade head \
 && alembic revision --autogenerate \
 && alembic upgrade head \
 && python ./model/main.py \
 && chown -R www-data:www-data /var/www/apache-flask/db

# Apache をフォアグラウンドで起動
CMD /usr/sbin/apache2ctl -D FOREGROUND
