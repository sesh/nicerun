import decimal
import json
import json as json_lib
import ssl
from collections import defaultdict, namedtuple
from datetime import datetime, timedelta
from math import asin, cos, radians, sin, sqrt
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from dateutil.parser import parse

AVG_EARTH_RADIUS = 6371  # in km


def format_mins_seconds(d):
    d = int(d)
    minutes, seconds = divmod(d, 60)
    return f"{minutes:02}:{seconds:02}"


def semicircle_to_degrees(semicircles):
    """Convert a number in semicricles to degrees"""
    return semicircles * (180.0 / 2.0**31)


def etree_to_dict_no_namespaces(t):
    tag = t.tag.split("}")[-1]
    d = {tag: {} if t.attrib else None}

    children = list(t)
    if children:
        dd = defaultdict(list)
        for dc in map(etree_to_dict_no_namespaces, children):
            for k, v in dc.items():
                dd[k.split("}")[-1]].append(v)
        d = {tag: {k.split("}")[-1]: v[0] if len(v) == 1 else v for k, v in dd.items()}}
    if t.attrib:
        d[tag].update(("@" + k, v) for k, v in t.attrib.items())
    if t.text:
        text = t.text.strip()
        if children or t.attrib:
            if text:
                d[tag]["#text"] = text
        else:
            d[tag] = text
    return d


def haversine(point1, point2, miles=False):
    """Calculate the great-circle distance between two points on the Earth surface.
    :input: two 2-tuples, containing the latitude and longitude of each point
    in decimal degrees.
    Example: haversine((45.7597, 4.8422), (48.8567, 2.3508))
    :output: Returns the distance bewteen the two points.
    The default unit is kilometers. Miles can be returned
    if the ``miles`` parameter is set to True.
    """
    # unpack latitude/longitude
    lat1, lng1 = point1[0], point1[1]
    lat2, lng2 = point2[0], point2[1]

    # convert all latitudes/longitudes from decimal degrees to radians
    lat1, lng1, lat2, lng2 = map(radians, (lat1, lng1, lat2, lng2))

    # calculate haversine
    lat = lat2 - lat1
    lng = lng2 - lng1
    d = sin(lat * 0.5) ** 2 + cos(lat1) * cos(lat2) * sin(lng * 0.5) ** 2
    h = 2 * AVG_EARTH_RADIUS * asin(sqrt(d))
    if miles:
        return h * 0.621371  # in miles
    else:
        return h  # in kilometers
