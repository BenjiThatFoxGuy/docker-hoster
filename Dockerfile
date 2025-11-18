FROM python:3.14-alpine

COPY requirements.txt /tmp/requirements.txt
RUN pip3 install -r /tmp/requirements.txt

RUN mkdir /hoster
WORKDIR /hoster
COPY hoster.py /hoster/

CMD ["python3", "-u", "hoster.py"]