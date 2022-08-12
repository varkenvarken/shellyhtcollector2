FROM python:3.8

RUN apt-get install -qy curl ; curl https://downloads.mariadb.com/MariaDB/mariadb_repo_setup > mariadb_repo_setup ; chmod +x mariadb_repo_setup ; ./mariadb_repo_setup --mariadb-server-version="mariadb-10.6" ; apt-get install -qy libmariadb3 libmariadb-dev

RUN python -m pip install htcollector[graph]

CMD ["python",  "-m", "htcollector", "--dbhost", "docker_dbserver_1"]
