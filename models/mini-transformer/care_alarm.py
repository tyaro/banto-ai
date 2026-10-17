"""Fixed CARE r1 alarm semantics and portable forecast record definitions."""
import math
import struct

# event uint32, ordinal uint32, source ID int64, issue int64, availability int64,
# flags u8+7pad; actual2, neural p50(2), baseline p50(2), scores(2) float64;
# lead1 quantiles [3,3] float32, 4pad =144 bytes.
PREDICTION=struct.Struct('<IIqqqB7x2d2d2d2d9f4x')
VALIDATION=struct.Struct('<II384f')  # step, ordinal, actual3x32, quantile3x32x3
NEURAL_ISSUED=1
COMMON=2
NATIVE=4
BASELINE_ISSUED=8
METHODS=('neural-common','baseline-common','baseline-native')


def calibration_threshold(scores):
    if len(scores)<512 or any(not math.isfinite(x) or x<0 for x in scores):raise ValueError('unsupported/nonfinite calibration')
    index=(199*len(scores)+199)//200-1
    return {'threshold':sorted(scores)[index],'n':len(scores),'order_index':index,'quantile':.995,'comparison':'strict >'}


def episodes(rows,method,threshold):
    if method not in METHODS or not math.isfinite(threshold):raise ValueError('invalid alarm method/threshold')
    flag=NATIVE if method=='baseline-native' else COMMON
    score_index=12 if method=='neural-common' else 13
    high=low=0;active=None;last=None;result=[]
    def close(at,reason):
        nonlocal active
        if active is not None:
            if at<=active['open']:raise ValueError('nonpositive alarm duration')
            result.append({**active,'close':at,'reason':reason});active=None
    for row in rows:
        available=row[4]
        if not row[5]&flag:
            if last is not None:close(last+600,'missing-or-gap')
            high=low=0;last=None;continue
        if last is not None and available-last!=600:
            close(last+600,'missing-or-gap');high=low=0
        score=row[score_index]
        if not math.isfinite(score):raise ValueError('eligible nonfinite alarm score')
        if score>threshold:
            high+=1;low=0
            if active is None and high>=3:active={'open':available,'open_ordinal':row[1],'open_source_id':row[2]}
        else:
            low+=1;high=0
            if active is not None and low>=3:close(available,'three-nonexceedances')
        last=available
    if last is not None:close(last+600,'file-end')
    return result


def eligible_seconds(rows,method):
    flag=NATIVE if method=='baseline-native' else COMMON
    return 600*sum(bool(r[5]&flag) for r in rows)


def active_seconds(rows,method,alarms):
    flag=NATIVE if method=='baseline-native' else COMMON
    return sum(max(0,min(row[4]+600,e['close'])-max(row[4],e['open']))
               for row in rows if row[5]&flag for e in alarms)


def event_result(alarms,start,end):
    if not start<end:raise ValueError('invalid anomaly interval')
    candidates=[e for e in alarms if start<=e['open']<=end]
    found=min(candidates,key=lambda e:e['open']) if candidates else None
    return {'hit':found is not None,'first_open':found['open'] if found else None,
            'lead_proxy_seconds':end-found['open'] if found else None,
            'earliness':min(1.,max(0.,(end-found['open'])/(end-start))) if found else 0.,
            'already_active_before_start':[e for e in alarms if e['open']<start<e['close']],
            'off_window_episodes':[e for e in alarms if not start<=e['open']<=end]}
