"""Past-level scale for total intervals; no new point forecast or label input."""
import math
from demand_shared_interval import total_interval


def local_scale(point, prefix_mean):
    if type(point) not in (int, float) or not math.isfinite(point) or point < 0:
        raise ValueError('finite nonnegative saved baseline required')
    if type(prefix_mean) not in (int, float) or not math.isfinite(prefix_mean) or prefix_mean <= 0:
        raise ValueError('finite positive saved prefix mean required')
    floor = .01*14*prefix_mean
    return {'scale': max(point, floor), 'floor': floor, 'floor_active': point <= floor,
            'baseline_to_fixed_scale': point/(14*prefix_mean)}


def restore(point, prefix_mean, calibration):
    scale = local_scale(point, prefix_mean)
    return dict(total_interval(point, scale['scale']/14, calibration), local_scale=scale)
