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
#  version: 20220806105227

import re
import mariadb
from datetime import datetime, timedelta
from dateutil import tz


class Measurement:
    idchars = re.compile(r"^[a-z01-9-]+$", re.IGNORECASE)

    def __init__(self, stationid, temperature, humidity):
        print(stationid, temperature, humidity)
        if re.match(self.idchars, stationid):
            self.stationid = stationid
        else:
            raise ValueError("stationid argument contains illegal characters")
        try:
            self.temperature = float(temperature)
            self.humidity = float(humidity)
        except TypeError as e:
            e.args = (
                "temperature and humidity arguments most be floats or convertible to floats",
            )
            raise e

    def __repr__(self):
        return f'Measurement("{self.stationid}", {self.temperature}, {self.humidity})'


class MeasurementDatabase:
    def __init__(self, database, host, port, user, password):
        self.connection = mariadb.connect(
            user=user, password=password, host=host, database=database
        )
        self.connection.auto_reconnect = True

        cursor = self.connection.cursor()
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS Measurements(
            Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            Stationid VARCHAR(100),
            Temperature REAL,
            Humidity REAL);"""
        )
        cursor.execute("""CREATE INDEX IF NOT EXISTS ts ON Measurements(Timestamp);""")
        cursor.execute("""CREATE INDEX IF NOT EXISTS si ON Measurements(Stationid);""")
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS StationidToName(
            Stationid  VARCHAR(100) NOT NULL PRIMARY KEY,
            Name TEXT NOT NULL);"""
        )

    def storeMeasurement(self, measurement):
        cursor = self.connection.cursor()
        cursor.execute(
            """INSERT INTO Measurements(Stationid, Temperature, Humidity)
                                    VALUES (?,?,?)""",
            (
                measurement.stationid,
                measurement.temperature,
                measurement.humidity,
            ),
        )
        self.connection.commit()
        cursor.close()

    def retrieveMeasurements(self, stationid, starttime, endtime=None):
        # get the data
        if stationid == "*":
            rows = [
                row
                for row in self.connection.cursor(dictionary=True).execute(
                    """SELECT Timestamp as 'Timestamp [timestamp]', Stationid, Temperature, Humidity
            FROM Measurements
            WHERE datetime(Timestamp) >= datetime(?) AND datetime(Timestamp) <= datetime(?)""",
                    (
                        starttime,
                        endtime if endtime is not None else tz.tzlocal(),
                    ),
                )
            ]
        else:
            rows = [
                row
                for row in self.connection.cursor(dictionary=True).execute(
                    """SELECT Timestamp as 'Timestamp [timestamp]', Stationid, Temperature, Humidity
            FROM Measurements
            WHERE Stationid = ? AND datetime(Timestamp) >= datetime(?) AND datetime(Timestamp) <= datetime(?)""",
                    (
                        stationid,
                        starttime,
                        endtime if endtime is not None else tz.tzlocal(),
                    ),
                )
            ]

        # convert the timestamps to the local timezone
        utc = tz.tzutc()  # sqlite timestamps are stored in UTC but without tz info
        ltz = tz.tzlocal()

        rows = [
            (
                row["Timestamp"],  # .replace(tzinfo=utc).astimezone(ltz),
                row["Stationid"],
                row["Temperature"],
                row["Humidity"],
            )
            for row in rows
        ]

        return rows

    def retrieveLastMeasurement(self, stationid):
        if stationid == "*":
            rows = []
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute("SELECT DISTINCT(Stationid) FROM Measurements")
            for row in cursor.fetchall():
                rows.extend(self.retrieveLastMeasurement(row[0]))
        else:
            # get the data
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(
                """SELECT Timestamp as 'Timestamp [timestamp]', Measurements.Stationid, Name, Temperature, Humidity
            FROM Measurements, StationidToName
            WHERE Measurements.Stationid = ? AND Measurements.Stationid = StationidToName.Stationid ORDER BY timestamp DESC LIMIT 1;""",
                (stationid,),
            )
            rows = cursor.fetchall()

            rows = [
                {
                    "time": row[0],  # .replace(tzinfo=utc).astimezone(ltz),
                    "deltat": datetime.now() - row[0],
                    "stationid": row[1],
                    "name": row[2],
                    "temperature": row[3],
                    "humidity": row[4],
                }
                for row in rows
            ]
        return rows

    def lastMeasurementsAsHTML(self, stationid):
        ms = self.retrieveLastMeasurement(stationid)
        mdivs = "\n".join(
            f"""
            <div class="measurement{' late' if m['deltat'].total_seconds()>24*3600 else ''}" id="{m["stationid"]}">
            <div class="station">{m["name"]}</div>
            <div class="time" data-time="{m["time"]}">{m['time']:%H:%M}</div>
            <div class="temp">{m["temperature"]:.1f}<span class="degrees">°C</span></div>
            <div class="hum">{m["humidity"]:.0f}<span class=percent>%</span></div>
            </div>"""
            for m in ms
        )
        style = """
        .body {width:100%; }
        .measurements {width: 90%;}
        .measurement {float:left; width:200px;}
        .station {float:left; font-size:16pt;}
        .time {float:left; font-size:12pt;}
        .temp {float:left; clear:both; font-size:40pt;}
        .hum {float:left; font-size:12pt;}
        .late { background-color:red; }
        """
        return f"""<html>
        <head><meta charset="UTF-8"><meta http-equiv="refresh" content="300"><title>Temperatuur binnen</title>
        <style>{style}</style>
        </head>
        <body>
        <div class="measurements">
        {mdivs}
        </div>
        </body>
        </html>
        """

    def retrieveMeasurementsLast24Hours(self, stationid):
        ltz = tz.tzlocal()
        d = timedelta(hours=24)
        end = datetime.now(tz=ltz)
        start = end - d
        return self.retrieveMeasurements(stationid, start, end)

    def names(self, stationid, name):
        if stationid == "*":
            conn = self.connection
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM StationidToName")
            return [(row[0], row[1]) for row in cursor.fetchall()]
        else:
            conn = self.connection
            cursor = conn.cursor()
            cursor.execute(
                "REPLACE StationidToName(Stationid, Name) VALUES(?,?)",
                (stationid, name),
            )
            conn.commit()
            return []
