import argparse
from datetime import datetime,timedelta
from os import environ
from sys import stdout

from htcollector.Database import MeasurementDatabase
from htcollector.Graph import graph

from dateutil import tz

now = datetime.now(tz=tz.tzlocal())
yesterday = now - timedelta(1.0)

parser = argparse.ArgumentParser()
parser.add_argument(
    "--database",
    type=str,
    default="shellyht",
    help="database schema",
)
parser.add_argument(
    "--dbhost",
    type=str,
    default="127.0.0.1",
    help="database host",
)
parser.add_argument(
    "--dbport",
    type=str,
    default="3306",
    help="database port",
)
parser.add_argument(
    "--stationid",
    type=str,
    default="*",
    help="Station id of a shellyht",
)
parser.add_argument(
    "filename",
    type=str,
    default="-",
    help="filename of the output file or - for stdout",
)
args = parser.parse_args()

db = MeasurementDatabase(
    args.database, args.dbhost, args.dbport, environ["DBUSER"], environ["DBPASSWORD"])

file = stdout if args.filename == "-" else args.filename

graph(db, file, args.stationid, yesterday, now)
