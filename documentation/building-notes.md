# building - PyPi

!!!Just some documentation for my own workflow on preparing and testing docker images.

From the top level directory of this repository we make sure
we updatedthe pypi release first if needed (credentials are
in `~/.pypirc`):

```
python setup.py sdist
twine upload dist/`ls -1 dist/ | tail -1`
rm dist/*
```

Verify that it is updated [on Pypi](https://pypi.org/project/htcollector/).

# building - Docker

```
docker build -t varkenvarken/htcollector:latest -f docker/Dockerfile .
```

# testing

Run htcollector and the mariadb database:

```
docker-compose -f docker/docker-compose.yml up -d
```

The test it by adding a couple of measurements en then retrieving a
graph and an html page:

```
http GET "http://localhost:8083/sensorlog?hum=70&temp=24&id=test-123456"
... # perhaps sleep a bit
http GET "http://localhost:8083/sensorlog?hum=65&temp=25&id=test-123456"

http GET "http://localhost:8083/graph?id=test-123456" > /tmp/f.png ; display /tmp/f.png

```

# push the image

```
docker login
docker push varkenvarken/htcollector:latest
```