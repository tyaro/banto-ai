"""Declared positive-scale cohort ridge; zero-scale series use baseline only."""
import datetime as dt
import math


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def solve_spd(matrix, rhs):
    n = len(rhs)
    if not 1 <= n <= 8 or len(matrix) != n or any(len(row) != n for row in matrix):
        raise ValueError('bounded square system required')
    if any(not finite(v) for row in matrix for v in row) or any(not finite(v) for v in rhs):
        raise ValueError('finite system required')
    if any(matrix[i][j] != matrix[j][i] for i in range(n) for j in range(n)):
        raise ValueError('symmetric system required')
    lower = [[0.]*n for _ in range(n)]
    for i in range(n):
        for j in range(i+1):
            value = matrix[i][j]-math.fsum(lower[i][k]*lower[j][k] for k in range(j))
            if i == j:
                if value <= 0 or not math.isfinite(value):
                    raise ValueError('positive definite system required')
                lower[i][j] = math.sqrt(value)
            else:
                lower[i][j] = value/lower[j][j]
    forward = [0.]*n
    for i in range(n):
        forward[i] = (rhs[i]-math.fsum(lower[i][j]*forward[j] for j in range(i)))/lower[i][i]
    answer = [0.]*n
    for i in range(n-1, -1, -1):
        answer[i] = (forward[i]-math.fsum(lower[j][i]*answer[j] for j in range(i+1,n)))/lower[i][i]
    if any(not math.isfinite(v) for v in answer):
        raise ValueError('nonfinite solution')
    return answer


def fit(rows, train_stores):
    stores = tuple(train_stores)
    if not stores or len(stores) != len(set(stores)):
        raise ValueError('distinct declared stores required')
    seen = set()
    for row in rows:
        if row['store'] not in stores:
            raise ValueError('row outside declared training stores')
        day = dt.date.fromisoformat(row['origin'])
        if day < dt.date(2013,1,1) or day+dt.timedelta(days=13) >= dt.date(2015,1,1):
            raise ValueError('label must end before 2015')
        key = row['store'], day
        if key in seen:
            raise ValueError('duplicate training window')
        seen.add(key)
        if len(row['features']) != 8 or any(not finite(v) for v in row['features']) or not finite(row['y']):
            raise ValueError('eight supported finite features and label required')
    counts = {s:sum(r['store'] == s for r in rows) for s in stores}
    if any(n < 10 for n in counts.values()):
        raise ValueError('ten supported windows per declared store required')
    n = len(rows)
    weights = [n/(len(stores)*counts[r['store']]) for r in rows]
    total = math.fsum(weights)
    center = [math.fsum(w*r['features'][k] for w,r in zip(weights,rows))/total for k in range(8)]
    scale = [math.sqrt(math.fsum(w*(r['features'][k]-center[k])**2 for w,r in zip(weights,rows))/total) for k in range(8)]
    z = [[(r['features'][k]-center[k])/scale[k] if scale[k] > 0 else 0. for k in range(8)] for r in rows]
    intercept = math.fsum(w*r['y'] for w,r in zip(weights,rows))/total
    gram = [[math.fsum(w*x[i]*x[j] for w,x in zip(weights,z))+float(i==j) for j in range(8)] for i in range(8)]
    rhs = [math.fsum(w*x[k]*(r['y']-intercept) for w,x,r in zip(weights,z,rows)) for k in range(8)]
    slopes = solve_spd(gram,rhs)
    residual = max(abs(math.fsum(a*b for a,b in zip(row,slopes))-v) for row,v in zip(gram,rhs))
    return {'train_stores':stores,'rows':n,'store_counts':counts,
            'store_weight_sums':{s:math.fsum(w for w,r in zip(weights,rows) if r['store']==s) for s in stores},
            'weight_sum':total,'center':center,'scale':scale,'intercept':intercept,'slopes':slopes,
            'ridge':1.,'constant_columns':[k for k,s in enumerate(scale) if s==0],
            'normal_equation_max_abs_residual':residual}


def predict(model, baseline, scale, features):
    if baseline is None:
        return {'available':False,'baseline':None,'intercept':None,'weekly':None,'reason':'baseline_unavailable'}
    if not finite(baseline) or baseline < 0 or not finite(scale) or scale < 0:
        raise ValueError('nonnegative finite baseline and fit scale required')
    if scale == 0:
        return {'available':True,'baseline':baseline,'intercept':baseline,'weekly':baseline,
                'reason':'unsupported_zero_fit_scale','feature_supported':False}
    control = max(0.,baseline+14*scale*model['intercept'])
    if features is None:
        return {'available':True,'baseline':baseline,'intercept':control,'weekly':baseline,
                'reason':'weekly_support_baseline_fallback','feature_supported':False}
    if len(features) != 8 or any(not finite(v) for v in features):
        raise ValueError('eight finite prediction features required')
    z = [(v-c)/s if s>0 else 0. for v,c,s in zip(features,model['center'],model['scale'])]
    weekly = max(0.,baseline+14*scale*(model['intercept']+math.fsum(a*b for a,b in zip(model['slopes'],z))))
    if not math.isfinite(control) or not math.isfinite(weekly):
        raise ValueError('nonfinite total prediction')
    return {'available':True,'baseline':baseline,'intercept':control,'weekly':weekly,
            'reason':None,'feature_supported':True}
