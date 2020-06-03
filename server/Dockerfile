FROM python:3.7

WORKDIR /app

# 起動時にソースディレクトリーをマウントして使う
# ADD src .
ADD src/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 起動時に上書きして 1 にすることでリモートデバッグを有効にできる仕掛け
ENV REMOTE_DEBUG 0

EXPOSE 3000 5000

ENTRYPOINT [ "flask", "run", "--host", "0.0.0.0", "--port", "3000" ]
