from math import sqrt

import srtm

from core.activities.utils import haversine


def get_elevation_for_lat_lon(lat, lon):
    elevation_data = srtm.get_data(local_cache_dir=".srtm")
    return elevation_data.get_elevation(lat, lon)


def get_line_equation_coefficients(location1, location2):
    """
    Get line equation coefficients for:
    [0] * a + longitude * b + c = 0
    This is a normal cartesian line (not spherical!)
    """
    if location1[1] == location2[1]:
        # Vertical line:
        return float(0), float(1), float(-location1[1])
    else:
        a = float(location1[0] - location2[0]) / (location1[1] - location2[1])
        b = location1[0] - location1[1] * a
        return float(1), float(-a), float(-b)


def distance_from_line(point, line_point_1, line_point_2):
    """Distance of point from a line given with two points."""
    a = haversine(line_point_1, line_point_2) * 1000

    if not a:
        return haversine(line_point_1, point) * 1000

    b = haversine(line_point_1, point) * 1000
    c = haversine(line_point_2, point) * 1000

    if a is not None and b is not None and c is not None:
        s = (a + b + c) / 2.0
        return 2.0 * sqrt(abs(s * (s - a) * (s - b) * (s - c))) / a
    return None


def simplify_polyline(points, max_distance):
    """Does Ramer-Douglas-Peucker algorithm for simplification of polyline"""
    _max_distance = max_distance

    if len(points) < 3:
        return points

    begin, end = points[0], points[-1]

    # Use a "normal" line just to detect the most distant point (not its real distance)
    # this is because this is faster to compute than calling distance_from_line() for
    # every point.
    #
    # This is an approximation and may have some errors near the poles and if
    # the points are too distant, but it should be good enough for most use
    # cases...
    a, b, c = get_line_equation_coefficients(begin, end)

    # Initialize to safe values
    tmp_max_distance = 0.0
    tmp_max_distance_position = 1

    # Check distance of all points between begin and end, exclusive
    for point_no in range(1, len(points) - 1):
        point = points[point_no]
        d = abs(a * point[0] + b * point[1] + c)
        if d > tmp_max_distance:
            tmp_max_distance = d
            tmp_max_distance_position = point_no

    # Now that we have the most distance point, compute its real distance:
    real_max_distance = distance_from_line(points[tmp_max_distance_position], begin, end)

    # If furthest point is less than max_distance, remove all points between begin and end
    if real_max_distance is not None and real_max_distance < _max_distance:
        return [begin, end]

    # If furthest point is more than max_distance, use it as anchor and run
    # function again using (begin to anchor) and (anchor to end), remove extra anchor
    return (
        simplify_polyline(points[: tmp_max_distance_position + 1], _max_distance)
        + simplify_polyline(points[tmp_max_distance_position:], _max_distance)[1:]
    )
