FROM python:3.13

WORKDIR /app

COPY . .

RUN apt-get update && apt-get install -y libgl1

RUN pip install zfec opencv-python

CMD ["bash"]
