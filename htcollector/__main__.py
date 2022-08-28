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
#  version: 20220828124631

import argparse
from sys import stderr, exit
from os import environ
import logging

from .Server import Interceptor
from .Database import MeasurementDatabase


# all arguments/options can be set using environment variables or command line options
# if both are present, command line options take precedence


def get_args(arguments=None):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--database",
        type=str,
        default=environ.get("MARIADB_DATABASE", "shellyht"),
        help="database schema",
    )
    parser.add_argument(
        "--dbuser", type=str, default=environ.get("MARIADB_USER", "=test-user")
    )
    parser.add_argument(
        "--dbpassword", type=str, default=environ.get("MARIADB_PASSWORD", "test_secret")
    )
    parser.add_argument(
        "--dbhost",
        type=str,
        default=environ.get("DBSERVER", "127.0.0.1"),
        help="database host",
    )
    parser.add_argument(
        "--dbport",
        type=str,
        default=environ.get("DBPORT", "3306"),
        help="database port",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=int(environ.get("PORT", 1883)),
        help="port to listen on",
    )
    parser.add_argument(
        "-b",
        "--bind",
        type=str,
        default=environ.get("BIND", ""),
        help="address to bind to",
    )
    parser.add_argument(
        "-l",
        "--loglevel",
        type=str,
        default=environ.get("LOGLEVEL", "INFO"),
        help="verbosity of log messages",
    )
    parser.add_argument(
        "-r",
        "--resourcedir",
        type=str,
        default=environ.get("RESOURCEDIR", "./static"),
        help="directory containing static resources",
    )
    parser.add_argument(
        "-x", "--ping", action="store_true", help="ping database end exit"
    )
    return parser.parse_args(arguments)


if __name__ == "__main__":  # pragma: no cover
    args = get_args()

    logging.basicConfig(format="%(asctime)s %(message)s", level=args.loglevel)

    db = MeasurementDatabase(
        args.database, args.dbhost, args.dbport, args.dbuser, args.dbpassword
    )

    logging.info(
        f"OK: database {args.database} can be reached on {args.dbhost}:{args.dbport} by {args.dbuser}"
    )
    if args.ping:
        exit()

    logging.info(f"starting server, listening on {args.bind}:{args.port}")

    while True:  # apparently serve_forever() does return on a 104 error
        server = Interceptor((args.bind, args.port), db, args.resourcedir)
        server.serve_forever()
        logging.warning("restarting server on a 104 error")
