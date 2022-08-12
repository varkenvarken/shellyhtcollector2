import argparse
import json
from datetime import datetime, timedelta
from sys import stderr, exit
from os import environ

from dateutil import tz

from htcollector.Database import MeasurementDatabase
from htcollector.Utils import DatetimeEncoder

now = datetime.now(tz=tz.tzlocal())
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
parser.add_argument("--html", default=False, action="store_true")
args = parser.parse_args()

db = MeasurementDatabase(
    args.database, args.dbhost, args.dbport, environ["DBUSER"], environ["DBPASSWORD"]
)

if args.html:
    print(db.lastMeasurementsAsHTML(args.stationid))
else:
    print(json.dumps(db.retrieveLastMeasurement(args.stationid), cls=DatetimeEncoder))
