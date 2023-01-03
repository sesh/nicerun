import decimal
import json
from datetime import datetime, timedelta, timezone
from math import asin, cos, floor, radians, sin, sqrt
from xml.etree import ElementTree

from dateutil.parser import parse
from fitparse import FitFile

from core.activities.fix import get_elevation_for_lat_lon, simplify_polyline
from core.activities.utils import *

utc_offset = lambda offset: timezone(timedelta(seconds=offset))


# Features
SIMPLIFY = True
FIX_ELEVATION = False
GENERATE_NAME = False
FASTEST_X = []


class Activity:
    def __str__(self):
        return f"{self.name} {self.distance}km in {self.duration} ({self.provider} - {self.source_id})"

    @classmethod
    def load_fit(cls, fn):
        ff = FitFile(fn)
        ff.parse()

        args = {}
        points = []
        laps = []

        for m in ff.get_messages():
            if m.name == "record":
                points.append(m.get_values())
            elif m.name == "sport":
                args["activity_type"] = m.get_values()["sport"]
            elif m.name == "lap":
                laps.append(m.get_values()["start_time"])

        args["name"] = ""
        args["source_id"] = ""
        args["start"] = points[0]["timestamp"].replace(tzinfo=utc_offset(0))
        args["start_local"] = points[0]["timestamp"] + timedelta(hours=10)

        args["duration"] = (points[-1]["timestamp"] - points[0]["timestamp"]).seconds

        args["longitude_values"] = [semicircle_to_degrees(p["position_long"]) for p in points if "position_long" in p]
        args["latitude_values"] = [semicircle_to_degrees(p["position_lat"]) for p in points if "position_lat" in p]
        args["elevation_values"] = [p.get("enhanced_altitude") for p in points]
        args["clock_values"] = [(p["timestamp"] - points[0]["timestamp"]).seconds for p in points]
        args["heart_rate_values"] = [p.get("heart_rate", 0) for p in points]
        args["distance_values"] = []
        args["laps"] = laps

        d = 0.0

        for pt in zip(args["latitude_values"], args["longitude_values"]):
            if len(args["distance_values"]) == 0:
                args["distance_values"].append(d)
            else:
                d += haversine(prev_pt, pt)
                args["distance_values"].append(d)

            prev_pt = pt

        args["distance"] = args["distance_values"][-1]

        args["external_id"] = None
        args["provider"] = None

        return Activity(**args)

    @classmethod
    def load_gpx(cls, gpx, fn=None):
        """
        {
            "ele": "86.9",
            "time": "2020-06-07T22:54:50Z",
            "extensions": {
              "TrackPointExtension": {
                "hr": "165",
                "cad": "80"
              }
            },
            "@lat": "-37.8892827",
            "@lon": "145.2788971"
        }
        """
        tree = ElementTree.fromstring(gpx)
        d = etree_to_dict_no_namespaces(tree)

        args = {}
        try:
            args["name"] = d["gpx"]["trk"]["name"]
        except:
            args["name"] = "Unnamed Run"

        points = []

        if type(d["gpx"]["trk"]["trkseg"]) == list:
            for seg in d["gpx"]["trk"]["trkseg"]:
                if seg and "trkpt" in seg:
                    for pt in seg["trkpt"]:
                        points.append(pt)
        else:
            points = d["gpx"]["trk"]["trkseg"]["trkpt"]

        args["source_id"] = ""
        args["start"] = parse(points[0]["time"])
        args["duration"] = (parse(points[-1]["time"]) - args["start"]).seconds
        args["start_local"] = args["start"] + timedelta(hours=10)

        args["activity_type"] = d["gpx"]["trk"]["type"].lower()

        args["longitude_values"] = [float(x["@lon"]) for x in points]
        args["latitude_values"] = [float(x["@lat"]) for x in points]
        args["elevation_values"] = [float(x["ele"]) for x in points]
        args["clock_values"] = [(parse(v["time"]) - args["start"]).seconds for v in points]

        try:
            args["heart_rate_values"] = [x["extensions"]["TrackPointExtension"].get("hr", 0.0) for x in points]
        except:
            print("No heart rate values, that's okay")

        args["distance_values"] = []

        d = 0.0
        prev_pt = None

        for pt in zip(args["latitude_values"], args["longitude_values"]):
            if len(args["distance_values"]) == 0:
                args["distance_values"].append(d)
            else:
                d += haversine(prev_pt, pt)
                args["distance_values"].append(d)

            prev_pt = pt

        args["distance"] = args["distance_values"][-1]
        return Activity(**args)

    def __init__(
        self,
        *,
        name,
        source_id,
        start,
        start_local,
        distance,
        duration,
        activity_type="running",
        distance_values=[],
        longitude_values=[],
        latitude_values=[],
        elevation_values=[],
        clock_values=[],
        heart_rate_values=[],
        laps=[],
        external_id=None,
        provider=None,
        **kwargs,
    ):
        self.name = name
        self.source_id = source_id
        self.external_id = external_id  # id on another service
        self.start = start
        self.start_local = start_local
        self.distance = distance  # in kms
        self.duration = duration  # in seconds
        self.activity_type = activity_type
        self.distance_values = distance_values  # cumulative distance in kms
        self.longitude_values = longitude_values
        self.latitude_values = latitude_values
        self.elevation_values = elevation_values  # in m
        self.clock_values = clock_values  # in s
        self.heart_rate_values = heart_rate_values  # in bpm
        self.provider = provider
        self.laps = (laps,)  # start times as datetime
        self._splits = self.splits()
        self._fastest = {}

        if SIMPLIFY:
            self.simplify()

        if FIX_ELEVATION:
            self.fix_elevation()

        if GENERATE_NAME:
            self.name = self.generated_name()

        for m in FASTEST_X:
            self.fastest(m)

        self.distance = self.calculated_distance()
        self.uphill, self.downhill = self.calculate_uphill_downhill()

    def to_json(self):
        return json.dumps(
            {
                "name": self.name,
                "source_id": self.source_id,
                "external_id": self.external_id,  # id on another service
                "start": str(self.start),
                "start_local": str(self.start_local),
                "distance": self.distance,  # in kms
                "duration": self.duration,  # in seconds
                "activity_type": self.activity_type,
                "distance_values": self.distance_values,  # cumulative distance in kms
                "longitude_values": self.longitude_values,
                "latitude_values": self.latitude_values,
                "elevation_values": self.elevation_values,  # in m
                "clock_values": self.clock_values,  # in s
                "heart_rate_values": self.heart_rate_values,  # in bpm
                "provider": self.provider,
                "_fastest": self._fastest,
                "uphill": self.uphill,
                "downhill": self.downhill,
                "splits": self._splits,
                "laps": [str(l) for l in self.laps],
            },
            indent=2,
        )

    def fix_elevation(self):
        for i, (lat, lon) in enumerate(zip(self.latitude_values, self.longitude_values)):
            self.elevation_values[i] = get_elevation_for_lat_lon(lat, lon)

    def simplify(self, distance=0.02):
        points = [
            (
                self.latitude_values[i],
                self.longitude_values[i],
                self.elevation_values[i],
                self.clock_values[i],
                self.distance_values[i],
                self.heart_rate_values[i] if self.heart_rate_values else None,
            )
            for i in range(len(self.latitude_values))
        ]
        x = len(points)
        points = simplify_polyline(points, distance)

        self.latitude_values = [x[0] for x in points]
        self.longitude_values = [x[1] for x in points]
        self.elevation_values = [x[2] for x in points]
        self.clock_values = [x[3] for x in points]
        self.distance_values = [x[4] for x in points]
        self.heart_rate_values = [x[5] for x in points]

        self.distance = self.calculated_distance()

    def short_date(self):
        return self.start_local.strftime("%b. %-d")

    def pace(self):
        return (self.duration / 60.0) / self.calculated_distance()

    def uphill_str(self):
        return f"{self.calculate_uphill_downhill()[0]:.0f}m"

    def downhill_str(self):
        return f"{self.calculate_uphill_downhill()[1]:.0f}m"

    def sparkline_values(self):
        return [72 - (x / 5) for x in self.splits(decimal.Decimal("0.5"))]

    def effort(self, max_hr, pace_5k=None):
        hard_effort = int(max_hr * 0.79)
        max_effort = int(max_hr * 0.92)

        if pace_5k:
            hard_pace = int(pace_5k * 1.25)
            max_pace = int(pace_5k * 0.92)

        above = 0.0
        below = 0.0

        if len([x for x in self.heart_rate_values if x]) == 0 and pace_5k:
            # no heart rate data - use pace instead
            for s in self.splits(decimal.Decimal(0.5)):
                pace = s * 2
                if pace < max_pace:
                    above += s * 2
                elif pace < hard_pace:
                    above += s
                else:
                    below += s
        elif max_hr:
            for i, hr in enumerate(self.heart_rate_values):
                if int(hr) < 40:
                    continue

                if i + 1 == len(self.clock_values):
                    continue

                duration = self.clock_values[i + 1] - self.clock_values[i]
                if int(hr) > max_effort:
                    above += duration * 2
                elif int(hr) > hard_effort:
                    above += duration
                else:
                    below += duration

        return int(((above / 60.0) * 2) + ((below / 60.0) * 0.25))

    def average_hr(self):
        hr = [int(x) for x in self.heart_rate_values if x]
        try:
            return floor(sum(hr) / len(hr))
        except:
            return 0

    def max_hr(self):
        hr = [int(x) for x in self.heart_rate_values if x]

        try:
            return max(hr)
        except:
            return 0

    def calculated_distance(self):
        distance = 0.0
        prev = None
        for point in zip(self.latitude_values, self.longitude_values):
            if prev:
                distance += haversine(point, prev)
            prev = point
        return distance

    def splits(self, split=decimal.Decimal("0.1")):
        splits = []
        next_split = split
        split_start = 0

        for i, distance in enumerate(self.distance_values):
            if distance >= next_split:
                splits.append((self.clock_values[i] - split_start) * (float(next_split) / distance))
                split_start = self.clock_values[i]
                next_split += split

        return splits

    def generated_name(self):
        if getattr(self, "_generated_name", None):
            return self._generated_name

        s = "🏃‍♂ "
        s += f"{self.calculated_distance():0.1f} km "

        hour = self.start_local.hour

        if hour < 12:
            s += "Morning "
        elif hour < 14:
            s += "Lunch "
        elif hour < 18:
            s += "Afternoon "
        else:
            s += "Evening "
        s += "Run"

        self._generated_name = s
        return s

    def calculate_uphill_downhill(self):
        # source: https://github.com/tkrajina/gpxpy/blob/dev/gpxpy/geo.py
        elevations = [int(m / 10) for m in self.elevation_values]

        if not elevations:
            return 0, 0

        size = len(elevations)

        def __filter(n: int) -> float:
            current_ele = elevations[n]
            if current_ele is None:
                return False
            if 0 < n < size - 1:
                previous_ele = elevations[n - 1]
                next_ele = elevations[n + 1]
                if previous_ele is not None and current_ele is not None and next_ele is not None:
                    return previous_ele * 0.3 + current_ele * 0.4 + next_ele * 0.3
            return current_ele

        smoothed_elevations = list(map(__filter, range(size)))

        uphill, downhill = 0.0, 0.0
        for prev, cur in zip(smoothed_elevations, smoothed_elevations[1:]):
            if prev is not None and cur is not None:
                d = cur - prev
                if d > 0:
                    uphill += d
                else:
                    downhill -= d

        return uphill, downhill

    def fastest(self, distance):
        if not getattr(self, "_fastest", None):
            self._fastest = {}

        if self._fastest.get(str(distance)):
            return self._fastest.get(str(distance))

        if self.calculated_distance() < distance:
            return

        t = None

        for i, d in enumerate(self.distance_values):
            if self.calculated_distance() < distance + d:
                return t

            # find the first point that is d + distance
            for i2, d2 in enumerate(self.distance_values[i:]):
                i2 = i + i2

                if d2 >= d + distance:
                    t2 = self.clock_values[i2] - self.clock_values[i]
                    if not t or t2 < t:
                        t = t2
                    continue

        self._fastest[str(distance)] = t
        return t

    def chart_values_hr(self):
        return [str(int(x)) if x else "0" for x in self.heart_rate_values]

    def chart_values_clock(self):
        return [str(x) for x in self.clock_values]
