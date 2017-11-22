
#FROM docker/whalesay:latest
FROM python:3
LABEL Name=pling-plong-odometer Version=0.0.1 
ADD webapp/ /
RUN pip install -r requirements.txt
CMD [ "python", "./app.py" ]