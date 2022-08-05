from datetime import date, datetime

import matplotlib as mpl
import matplotlib.dates as mdates
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from matplotlib import cm
from matplotlib.colors import ListedColormap
from matplotlib.ticker import PercentFormatter

blue2red = ListedColormap(
    np.dstack((np.linspace(0, 1, 256), np.zeros(256), np.linspace(1, 0, 256)))[0]
)


class Graph:
    def __init__(self, db):
        self.db = db

    def graph(
        self,
        stationid,
        starttime,
        endtime,
        title="Indoor measurements",
        tcolor="#d22c2b",
        hcolor="#2c2cd2",
        font="Amaranth",
        fontcolor="#d22c2b",
        **kwargs,
    ):
        data = self.db.retrieveMeasurements(stationid, starttime, endtime)

        # duplicate last entry and set time to endtime to extend last measurement
        data.append(list(data[-1]))
        data[-1][0] = endtime
        data = np.array(data)
        time = data[:, 0]
        temp = data[:, 2]
        hum = data[:, 3]
        fig = plt.figure(**kwargs)
        plt.title(
            f"{title} (now: {temp[-1]:.1f}°C / {hum[-1]:.1f}% )",
            fontfamily=font,
            color=fontcolor,
        )
        ax = fig.axes[0]
        ax.set_xlim(left=starttime, right=endtime)
        ax.set_ylabel("Temp (°C)", color=tcolor)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        ax.set_facecolor(kwargs["facecolor"])
        ax.plot(time, temp, color="red")
        ax2 = ax.twinx()
        ax2.set_ylabel("Humidity (%)", color=hcolor)
        ax2.plot(time, hum, color="blue")
        ax2.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        fig.autofmt_xdate()
        return fig
