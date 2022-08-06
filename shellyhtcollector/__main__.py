import argparse
from datetime import datetime
from sys import stderr, exit
from os import environ

from dateutil import tz

from .Server import Interceptor
from .Database import MeasurementDatabase

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
parser.add_argument("-p", "--port", type=int, default=1883, help="port to listen on")
parser.add_argument("-b", "--bind", type=str, default="", help="address to bind to")
parser.add_argument(
    "-x",
    "--ping",
    action="store_true",
    help="ping database end exit",
)
args = parser.parse_args()

db = MeasurementDatabase(
    args.database, args.dbhost, args.dbport, environ["DBUSER"], environ["DBPASSWORD"]
)

if args.ping:
    exit()

print(f"starting server, listening on {args.bind}:{args.port}", file=stderr, flush=True)
while True:  # apparently serve_forever() does return on a 104 error
    server = Interceptor((args.bind, args.port), db)
    server.serve_forever()
    print("restarting server on a 104 error", file=stderr, flush=True)
