import argparse
import json
from sys import stderr, exit
from os import environ

from htcollector.Database import MeasurementDatabase

parser = argparse.ArgumentParser()
parser.add_argument(
    "stationid",
    type=str,
    help="shellyht station id (use * to list all stations)",
    nargs="?",
    default="*",
)
parser.add_argument("name", type=str, help="station name", nargs="?", default="")
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
args = parser.parse_args()

db = MeasurementDatabase(
    args.database, args.dbhost, args.dbport, environ["DBUSER"], environ["DBPASSWORD"]
)

print(db.names(args.stationid, args.name))
