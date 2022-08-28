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
#  version: 20220828180356

import logging
import re
import mariadb
from datetime import datetime, timedelta
from dateutil import tz


class Measurement:
    """
    Represents a measurement of temperature and humidity by a station.

    Args:
        stationid (str): station identification. Must contain only 1 or more alphnumeric characters or hyphens
        temperature (float): _description_
        humidity (float): _description_

    Raises:
        ValueError: if the stationid argument contains illegal characters or temperature or humidity arguments are not compatible to floats

    """

    idchars = re.compile(r"^[a-z01-9-]+$", re.IGNORECASE)

    def __init__(self, stationid, temperature, humidity):
        if re.match(self.idchars, stationid):
            self.stationid = stationid
        else:
            raise ValueError("stationid argument contains illegal characters")
        try:
            self.temperature = float(temperature)
            self.humidity = float(humidity)
        except ValueError as e:
            e.args = (
                "temperature and humidity arguments most be floats or convertible to floats",
            )
            raise e

    def __repr__(self):
        return f'Measurement("{self.stationid}", {self.temperature}, {self.humidity})'


class MeasurementDatabase:
    """
    Implements a databases containing measurements and station descriptions.

    The backing database should be a MariaDB database server.

    Args:
        database (str): name of the database
        host (str): hostname or ip-address of teh database server
        port (str): port that the database server is listening on
        user (str): username of a user with access privileges to the database
        password (str): password of the user

    """

    def __init__(self, database, host, port, user, password):
        self.pool = mariadb.ConnectionPool(
            pool_name="connection_pool_1",
            user=user,
            password=password,
            host=host,
            database=database,
        )

        with self.pool.get_connection() as connection:
            connection.auto_reconnect = True

            # the timestamp is configured for millisecond resolution
            with connection.cursor() as cursor:
                cursor.execute(
                    """CREATE TABLE IF NOT EXISTS Measurements(
                    Timestamp DATETIME(3) DEFAULT CURRENT_TIMESTAMP,
                    Stationid VARCHAR(100),
                    Temperature REAL,
                    Humidity REAL);"""
                )
                cursor.execute(
                    """CREATE INDEX IF NOT EXISTS ts ON Measurements(Timestamp);"""
                )
                cursor.execute(
                    """CREATE INDEX IF NOT EXISTS si ON Measurements(Stationid);"""
                )
                cursor.execute(
                    """CREATE TABLE IF NOT EXISTS StationidToName(
                    Stationid  VARCHAR(100) NOT NULL PRIMARY KEY,
                    Name TEXT NOT NULL);"""
                )

    def storeMeasurement(self, measurement):
        """
        Store a measurement into the database.

        Args:
            measurement (Measurement): the measurement

        Measurements do not contain timestamps, the are added automatically.
        """
        with self.pool.get_connection() as connection:
            connection.auto_reconnect = True
            with connection.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO Measurements(Stationid, Temperature, Humidity)
                           VALUES (?,?,?)""",
                    (
                        measurement.stationid,
                        measurement.temperature,
                        measurement.humidity,
                    ),
                )
                connection.commit()
                n = cursor.rowcount
                cursor.close()
                return n

    def retrieveMeasurements(
        self, stationid, starttime: datetime, endtime: datetime = None
    ):
        """
        Get measurements inside a given timeframe.

        Args:
            stationid (str): stationid or asterisk '*'
            starttime (datetime): starttime of measurement period (inclusive)
            endtime (datetime, optional): endtime of measurement period (inclusive) or None for now. Defaults to None.

        Returns:
            list: of dict(timestamp:t, stationid:id, temperature:t, humidity:h)
        """
        # timestamps in MariaDB are stored in UTC
        endtime = (
            endtime.astimezone(tz.UTC)
            if endtime is not None
            else datetime.now(tz=tz.UTC)
        )
        starttime = starttime.astimezone(tz.UTC)
        starttime = starttime.replace(
            microsecond=(starttime.microsecond // 1000) * 1000
        )  # round down to millis
        if stationid == "*":
            with self.pool.get_connection() as connection:
                connection.auto_reconnect = True
                with connection.cursor() as cursor:
                    cursor.execute(
                        f"""SELECT Timestamp, Stationid, Temperature, Humidity
                                FROM Measurements
                                WHERE Timestamp >= ? AND Timestamp <= ?""",
                        (starttime, endtime),
                    )
                    rows = cursor.fetchall()
        else:
            with self.pool.get_connection() as connection:
                connection.auto_reconnect = True
                with connection.cursor() as cursor:
                    cursor.execute(
                        f"""SELECT Timestamp, Stationid, Temperature, Humidity
                                FROM Measurements
                                WHERE Stationid = ? AND Timestamp >= ? AND Timestamp <= ?""",
                        (stationid, starttime, endtime),
                    )
                    rows = cursor.fetchall()

        # mariadb / mysql timestamps are in UTC but returned as 'naive' datetime objects
        rows = [
            {
                "timestamp": row[0].replace(tzinfo=tz.UTC).astimezone(tz.tzlocal()),
                "stationid": row[1],
                "temperature": row[2],
                "humidity": row[3],
            }
            for row in rows
        ]

        return rows

    def retrieveLastMeasurement(
        self, stationid=None, _names=None, _unique_stations=None
    ):
        """
        Return the last measurement data for a station or all stations.

        Args:
            stationid (str): the stationid or an asterisk '*'

        Returns:
            list: a list of dict objects, one for each station
        """
        logging.debug(
            f"retrieveLastMeasurement {stationid} names={_names} unique_stations{_unique_stations}"
        )
        if _names is None:
            _names = self.names("*")

        if _unique_stations is None:
            _unique_stations = self.uniqueStations()

        if stationid is None:
            rows = []
            for unique_station in _unique_stations:
                rows.extend(
                    self.retrieveLastMeasurement(
                        unique_station, _names=_names, _unique_stations=_unique_stations
                    )
                )
        else:
            # get the data
            with self.pool.get_connection() as connection:
                connection.auto_reconnect = True
                with connection.cursor() as cursor:
                    cursor.execute(
                        """SELECT Timestamp as 'Timestamp [timestamp]', Stationid, Temperature, Humidity
                            FROM Measurements
                            WHERE Stationid = ? ORDER BY timestamp DESC LIMIT 1;""",
                        (stationid,),
                    )
                    rows = cursor.fetchall()
                    # mariadb / mysql timestamps are in UTC but returned as 'naive' datetime objects
                    logging.info(f"retrieveLastMeasurement {stationid}, {rows}")
                    rows = [
                        {
                            "time": row[0].replace(tzinfo=tz.UTC),
                            "deltat": datetime.now() - row[0],
                            "stationid": row[1],
                            "name": _names.get(row[1], "unknown"),
                            "temperature": row[2],
                            "humidity": row[3],
                        }
                        for row in rows
                    ]
        return rows

    def retrieveDatetimeBefore(self, stationid: str, t: datetime):
        """
        Returns the time of the last measurement preceding a given time.

        Args:
            stationid (str): the station id
            t (datetime): the timestamp

        Returns:
            datetime or None: the time of the last measurement preceding a given time or None if the isn one
        """

        t = t.astimezone(tz=tz.UTC)

        logging.debug(f"retrieveDatetimeBefore {stationid} {t}")

        with self.pool.get_connection() as connection:
            connection.auto_reconnect = True
            with connection.cursor() as cursor:
                cursor.execute(
                    """SELECT Timestamp
                    FROM Measurements
                    WHERE Stationid = ? AND Timestamp < ? ORDER BY Timestamp DESC LIMIT 1""",
                    (stationid, t),
                )
                rows = cursor.fetchall()
                print(t, rows, flush=True)
                # mariadb / mysql timestamps are in UTC but returned as 'naive' datetime objects
                return rows[0][0].replace(tzinfo=tz.UTC) if len(rows) else None

    def uniqueStations(self):
        with self.pool.get_connection() as connection:
            connection.auto_reconnect = True
            with connection.cursor() as cursor:
                cursor.execute("SELECT DISTINCT(Stationid) FROM Measurements")
                return [row[0] for row in cursor.fetchall()]

    def names(self, stationid, name=None):
        """
        Insert or replace a name for a stationid, or return a list of all stations._

        Args:
            stationid (str): the shellyht station id or an asterisk '*'
            name (str)): the name to associate with a stationid (ignored if stationid is '*')

        Returns:
            dict: a dict(stationid:name)
        """
        if stationid == "*":
            stationids = self.uniqueStations()
            with self.pool.get_connection() as connection:
                connection.auto_reconnect = True
                with connection.cursor() as cursor:
                    cursor.execute("SELECT * FROM StationidToName")
                    rows = cursor.fetchall()
                    print("names>>>", rows)
                    stationmap = {row[0]: row[1] for row in rows}
                    for s in stationids:
                        if s not in stationmap:
                            stationmap[s] = "Unknown"
                    return stationmap
        else:
            with self.pool.get_connection() as connection:
                connection.auto_reconnect = True
                with connection.cursor() as cursor:
                    cursor.execute(
                        "REPLACE StationidToName(Stationid, Name) VALUES(?,?)",
                        (stationid, name),
                    )
                    connection.commit()
                    return self.names("*")
