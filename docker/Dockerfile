FROM python:3.8

WORKDIR /htcollector

RUN apt-get install -qy curl ; curl https://downloads.mariadb.com/MariaDB/mariadb_repo_setup > mariadb_repo_setup ; chmod +x mariadb_repo_setup ; ./mariadb_repo_setup --mariadb-server-version="mariadb-10.6" ; apt-get install -qy libmariadb3 libmariadb-dev

CMD ["python",  "-m", "htcollector"]

#CMD ["sleep", "36000"]

COPY . ./ 

RUN python -m pip install -rrequirements.txt

RUN python setup.py install

