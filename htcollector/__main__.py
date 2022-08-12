#  shellyhtcollector, a python module to process sensor readings from Shelly H&T devices
#
# (C) 2022 Michel Anders (varkenvarken)
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#
#  version: 20220811145330

import argparse
from datetime import datetime
from sys import stderr, exit
from os import environ

from dateutil import tz

from .Server import Interceptor
from .Database import MeasurementDatabase


def get_args(arguments=None):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--database", type=str, default="shellyht", help="database schema"
    )
    parser.add_argument("--dbhost", type=str, default="127.0.0.1", help="database host")
    parser.add_argument("--dbport", type=str, default="3306", help="database port")
    parser.add_argument(
        "-p", "--port", type=int, default=1883, help="port to listen on"
    )
    parser.add_argument("-b", "--bind", type=str, default="", help="address to bind to")
    parser.add_argument(
        "-x", "--ping", action="store_true", help="ping database end exit"
    )
    return parser.parse_args(arguments)


if __name__ == "__main__":
    args = get_args()
    db = MeasurementDatabase(
        args.database,
        args.dbhost,
        args.dbport,
        environ["DBUSER"],
        environ["DBPASSWORD"],
    )

    if args.ping:
        exit()

    print(
        f"starting server, listening on {args.bind}:{args.port}",
        file=stderr,
        flush=True,
    )
    while True:  # apparently serve_forever() does return on a 104 error
        server = Interceptor((args.bind, args.port), db)
        server.serve_forever()
        print("restarting server on a 104 error", file=stderr, flush=True)
