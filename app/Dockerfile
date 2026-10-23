FROM python:3.12-slim

WORKDIR /code

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .

EXPOSE 5000

RUN useradd -md /home/ali ali

USER ali

CMD ["python","app.py"]