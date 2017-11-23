#FROM docker/whalesay:latest
FROM python:3
LABEL Name=pling-plong-odometer Version=0.0.1 
MAINTAINER Havard gulldahl <havard.gulldahl@nrk.no>

# We copy just the requirements.txt first to leverage Docker cache
COPY ./src/webapp/requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip install -r requirements.txt

COPY ./src/webapp /app

ENTRYPOINT [ "python" ]

CMD [ "./app.py" ]

# To run in development mode - where changes are displayed immediately, use the --mount option
# docker run -d -p 8000:8000 --name odometer --mount type=bind,source=$PWD/src/webapp,destination=/app,readonly pling-plong-odometer