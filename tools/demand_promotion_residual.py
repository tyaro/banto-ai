"""Fixed one-feature ridge residual correction, with explicit missing fallback."""
import math


def fit(rows):
    if len(rows) < 10:
        raise ValueError('at least ten fully supported training windows required')
    x = [r['x'] for r in rows]
    y = [r['y'] for r in rows]
    if any(not math.isfinite(v) for v in x+y):
        raise ValueError('finite training data required')
    n = len(x)
    center = math.fsum(x)/n
    scale = math.sqrt(math.fsum((v-center)**2 for v in x)/n)
    intercept = math.fsum(y)/n
    z = [(v-center)/scale for v in x] if scale > 0 else [0.0]*n
    slope = math.fsum(v*(target-intercept) for v,target in zip(z,y))/(math.fsum(v*v for v in z)+1)
    return {'n': n, 'center': center, 'scale': scale, 'intercept': intercept,
            'slope': slope, 'ridge': 1, 'dates': [r['origin'] for r in rows]}


def predict(model, baseline, train_scale, x):
    if not math.isfinite(baseline) or baseline < 0 or not math.isfinite(train_scale) or train_scale <= 0:
        raise ValueError('valid nonnegative baseline and positive fixed scale required')
    if x is not None and not math.isfinite(x):
        raise ValueError('finite feature or missing required')
    z = (x-model['center'])/model['scale'] if x is not None and model['scale'] > 0 else 0.0
    return {'baseline': baseline,
            'intercept': max(0.0, baseline+14*train_scale*model['intercept']),
            'promotion': max(0.0, baseline+14*train_scale*(model['intercept']+model['slope']*z)),
            'feature_supported': x is not None, 'standardized_feature': z}
