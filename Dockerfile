FROM python:3.11
WORKDIR /usr/src/app
ADD . ./
RUN pip install -r requirements.txt
CMD python run.py