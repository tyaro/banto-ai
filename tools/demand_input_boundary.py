"""Typed input/label contracts under explicit day-level availability assumptions.

No model fitting, forecasting, scoring, or legacy mixed-source loading here.
Integrity hashes are not authentication or a sandbox against arbitrary Python.
"""
import datetime as dt
import hashlib
import json
import math
from pathlib import Path

FIT=(6,7,10,13,15,17,19,23,26,27)
CUTS=('2014-01-01','2014-04-01','2014-07-01','2014-10-01')
POLICY='full2013-policy-v1'
DAY_ASSUMPTION='source-calendar-next-day-assumed; actual-arrival-timezone-unknown'
INPUT_FIELDS={'schema','key','store','origin','past_dates','past_values','past_observed','past_available_at','target_dates','assumed_open_mask','operating_status','matched_mean28','policy_ref'}
LABEL_FIELDS={'schema','key','store','origin','target_dates','available_at','availability_basis','raw_actual','observed'}
INDEX_FIELDS={'key','store','origin','target_dates','available_at','offset','length','pin'}
TRANSFORM_FIELDS={'schema','policy_ref','scale_period','scale_usable_from','scales','closure_period','closure_usable_from','month_days','availability_basis'}


def exact(obj, fields):
    if type(obj) is not dict or set(obj)!=set(fields):raise ValueError('strict fields mismatch')


def day(text):
    if type(text) is not str:raise ValueError('ISO calendar date required')
    d=dt.date.fromisoformat(text)
    if d.isoformat()!=text:raise ValueError('canonical ISO date required')
    return d


def canonical(obj):return json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()


def pin_bytes(raw):return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def pin_file(path):
    path=Path(path)
    if not path.is_file() or path.is_symlink() or path.stat().st_size>32*1024**2:raise ValueError('plain bounded file required')
    return pin_bytes(path.read_bytes())


def _pairs(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('duplicate JSON key')
        result[key]=value
    return result


def strict_json(raw):
    def invalid(value):raise ValueError('nonfinite JSON constant')
    return json.loads(raw,object_pairs_hook=_pairs,parse_constant=invalid)


def quantity(value, nullable=False):
    if value is None and nullable:return
    if type(value) not in (int,float) or not math.isfinite(value) or value<0:raise ValueError('nonnegative finite quantity, not bool, required')


def identity(store, origin):
    if type(store) is not int or store not in FIT:raise ValueError('FIT10 store required')
    o=day(origin)
    if not dt.date(2013,1,1)<=o or o+dt.timedelta(days=13)>=dt.date(2015,1,1):raise ValueError('pre-2015 scope required')
    targets=[str(o+dt.timedelta(days=j)) for j in range(14)]
    key=hashlib.sha256(canonical({'schema':'demand-key-v1','store':store,'origin':origin,'target_dates':targets})).hexdigest()
    return o,targets,key


def validate_input(row):
    exact(row,INPUT_FIELDS)
    o,targets,key=identity(row['store'],row['origin'])
    if row['schema']!='demand-input-v1' or row['key']!=key or row['target_dates']!=targets or row['policy_ref']!=POLICY:raise ValueError('input identity/policy mismatch')
    dates=[str(o-dt.timedelta(days=k)) for k in range(56,0,-1)]
    if day(dates[0])<dt.date(2013,1,1) or row['past_dates']!=dates:raise ValueError('fixed allowed past56 dates required')
    if row['past_available_at']!=[str(day(d)+dt.timedelta(days=1)) for d in dates]:raise ValueError('context availability assumption mismatch')
    for k in ('past_values','past_observed'):
        if type(row[k]) is not list or len(row[k])!=56:raise ValueError('past56 arrays required')
    for v,b in zip(row['past_values'],row['past_observed']):
        quantity(v,True)
        if type(b) is not bool or b!=(v is not None):raise ValueError('raw context observation mismatch')
    mask=[d[5:] not in ('01-01','12-25') for d in targets]
    if row['assumed_open_mask']!=mask or any(type(v) is not bool for v in row['assumed_open_mask']) or row['operating_status']!='unknown':raise ValueError('fixed assumed closure/unknown required')
    b=row['matched_mean28']
    if type(b) is not list or len(b)!=14:raise ValueError('existing mean28 array required')
    weekdays={w:[] for w in range(7)}
    for d,v in zip(dates[-28:],row['past_values'][-28:]):
        if v is not None:weekdays[day(d).weekday()].append(v)
    if min(map(len,weekdays.values()))<3:raise ValueError('old baseline support contract failed')
    for d,open_,v in zip(targets,mask,b):
        quantity(v)
        expected=math.fsum(weekdays[day(d).weekday()])/len(weekdays[day(d).weekday()]) if open_ else 0.
        if abs(v-expected)>1e-8:raise ValueError('existing mean28/context mismatch')
    return row


def validate_transforms(t):
    exact(t,TRANSFORM_FIELDS)
    if t['schema']!='demand-transform-v1' or t['policy_ref']!=POLICY or t['availability_basis']!=DAY_ASSUMPTION:raise ValueError('fixed transform policy required')
    for period_name,usable_name in (('scale_period','scale_usable_from'),('closure_period','closure_usable_from')):
        p=t[period_name];exact(p,{'start','end'})
        if p!={'start':'2013-01-01','end':'2013-12-31'} or t[usable_name]!='2014-01-01' or day(p['end'])>=day(t[usable_name]):raise ValueError('pre-2014 provenance required')
    exact(t['scales'],set(map(str,FIT)))
    for value in t['scales'].values():
        quantity(value)
        if value<=0:raise ValueError('positive scale required')
    if t['month_days']!=['01-01','12-25']:raise ValueError('closure assumption changed')
    return t


def input_readiness(row, transforms, *, asof=None, purpose='prediction'):
    validate_input(row);validate_transforms(transforms)
    if purpose not in ('prediction','historical_fit'):raise ValueError('fixed purpose required')
    at=day(row['origin'] if asof is None else asof)
    if not dt.date(2013,1,1)<=at<dt.date(2015,1,1):raise ValueError('pre-2015 asof required')
    if purpose=='prediction' and at!=day(row['origin']):raise ValueError('prediction asof must equal origin')
    reasons=[]
    if purpose=='historical_fit' and day(row['origin'])>=at:reasons.append('origin_not_before_fit_cutoff')
    if any(day(d)>at for d in row['past_available_at']):reasons.append('context_not_available')
    for name in ('scale','closure'):
        if day(transforms[name+'_period']['end'])>=at or day(transforms[name+'_usable_from'])>at:reasons.append(name+'_not_available')
    return {'ready':not reasons,'reasons':reasons,'purpose':purpose,'asof':str(at),'feature_support_for_new_model_verified':False}


def load_inputs(path, expected_pin):
    if pin_file(path)!=expected_pin:raise ValueError('input pin mismatch')
    rows=strict_json(Path(path).read_bytes())
    if type(rows) is not list:raise ValueError('input list required')
    seen=set()
    for row in rows:
        validate_input(row)
        if row['key'] in seen:raise ValueError('duplicate input key')
        seen.add(row['key'])
    return rows


def load_transforms(path, expected_pin):
    if pin_file(path)!=expected_pin:raise ValueError('transform pin mismatch')
    return validate_transforms(strict_json(Path(path).read_bytes()))


def issue_schedule():
    # Does not accept labels, mixed source, label counts, or label existence.
    return [(s,str(dt.date(2014,1,1)+dt.timedelta(days=14*k))) for k in range(26) for s in FIT]


def issue_groups(inputs):
    rr=[r for r in inputs if day(r['origin']).year==2014]
    for r in inputs:validate_input(r)
    keys=[(r['store'],r['origin']) for r in rr]
    if len(set(keys))!=len(keys) or set(keys)!=set(issue_schedule()):raise ValueError('input-only complete FIT10 issue calendar required')
    return {d:[r['key'] for r in sorted(rr,key=lambda r:r['store']) if r['origin']==d] for d in sorted({d for s,d in issue_schedule()})}


def project_input(legacy):
    # Intentionally touches only the allowlisted context fields; never target quantities.
    o,targets,key=identity(legacy['store'],legacy['origin'])
    row={'schema':'demand-input-v1','key':key,'store':legacy['store'],'origin':legacy['origin'],
         'past_dates':[str(o-dt.timedelta(days=k)) for k in range(56,0,-1)],'past_values':list(legacy['past_original_quantity']),
         'past_observed':list(legacy['past_original_observed']),'past_available_at':[str(o-dt.timedelta(days=k)+dt.timedelta(days=1)) for k in range(56,0,-1)],
         'target_dates':targets,'assumed_open_mask':list(legacy['open_mask']),'operating_status':legacy['operating_status'],
         'matched_mean28':list(legacy['matched_mean28']),'policy_ref':POLICY}
    return validate_input(row)


def validate_label(label):
    exact(label,LABEL_FIELDS)
    o,targets,key=identity(label['store'],label['origin'])
    if label['schema']!='demand-label-v1' or label['key']!=key or label['target_dates']!=targets or label['available_at']!=str(o+dt.timedelta(days=14)) or label['availability_basis']!=DAY_ASSUMPTION:raise ValueError('label identity/availability mismatch')
    if type(label['raw_actual']) is not list or len(label['raw_actual'])!=14 or type(label['observed']) is not list or len(label['observed'])!=14:raise ValueError('raw label14 arrays required')
    for value,flag in zip(label['raw_actual'],label['observed']):
        quantity(value,True)
        if type(flag) is not bool or flag!=(value is not None):raise ValueError('raw label observation mismatch')
    return label


def project_label(legacy):
    o,targets,key=identity(legacy['store'],legacy['origin']);raw=list(legacy['actual'])
    return validate_label({'schema':'demand-label-v1','key':key,'store':legacy['store'],'origin':legacy['origin'],'target_dates':targets,
        'available_at':str(o+dt.timedelta(days=14)),'availability_basis':DAY_ASSUMPTION,'raw_actual':raw,'observed':[v is not None for v in raw]})


def label_payload(labels):
    lines=[];index=[];offset=0;seen=set()
    for label in sorted(labels,key=lambda r:(r['available_at'],r['store'])):
        validate_label(label)
        if label['key'] in seen:raise ValueError('duplicate label key')
        seen.add(label['key']);raw=canonical(label)+b'\n'
        index.append({k:label[k] for k in ('key','store','origin','target_dates','available_at')}|{'offset':offset,'length':len(raw),'pin':pin_bytes(raw)})
        lines.append(raw);offset+=len(raw)
    return b''.join(lines),index


def validate_index(index, inputs, payload_size):
    if type(index) is not list:raise ValueError('label index list required')
    for row in inputs:validate_input(row)
    by_key={r['key']:r for r in inputs};seen=set();offset=0
    if len(by_key)!=len(inputs):raise ValueError('duplicate input identity')
    for entry in index:
        exact(entry,INDEX_FIELDS);o,targets,key=identity(entry['store'],entry['origin'])
        if entry['key']!=key or key not in by_key or key in seen or entry['target_dates']!=targets or entry['available_at']!=str(o+dt.timedelta(days=14)):raise ValueError('label index key/time mismatch')
        r=by_key[key]
        if any(entry[k]!=r[k] for k in ('key','store','origin','target_dates')):raise ValueError('cross-store/date binding mismatch')
        if type(entry['offset']) is not int or type(entry['length']) is not int or entry['offset']!=offset or not 0<entry['length']<=32768:raise ValueError('contiguous bounded label index required')
        exact(entry['pin'],{'bytes','sha256'})
        if entry['pin']['bytes']!=entry['length'] or type(entry['pin']['sha256']) is not str or len(entry['pin']['sha256'])!=64:raise ValueError('label row pin required')
        seen.add(key);offset+=entry['length']
    if seen!=set(by_key) or offset!=payload_size:raise ValueError('one-to-one complete label binding required')


class LabelReader:
    """Only authorized past rows are decoded; input-only consumers never instantiate this."""
    def __init__(self,path,index,inputs,payload_pin):
        if pin_file(path)!=payload_pin:raise ValueError('label payload pin mismatch')
        validate_index(index,inputs,payload_pin['bytes'])
        self.path=Path(path);self.index={r['key']:r for r in index};self.decoded_keys=[]

    def _decode(self,entry):
        with self.path.open('rb') as stream:
            stream.seek(entry['offset']);raw=stream.read(entry['length'])
        if pin_bytes(raw)!=entry['pin']:raise ValueError('label row pin mismatch')
        value=validate_label(strict_json(raw))
        if any(value[k]!=entry[k] for k in ('key','store','origin','target_dates','available_at')):raise ValueError('label/index identity mismatch')
        self.decoded_keys.append(entry['key']);return value

    def read_available(self,row,asof):
        validate_input(row);at=day(asof)
        if not dt.date(2013,1,1)<=at<dt.date(2015,1,1):raise ValueError('pre-2015 label asof required')
        entry=self.index[row['key']]
        if any(entry[k]!=row[k] for k in ('key','store','origin','target_dates')):raise ValueError('input/index identity mismatch')
        # Guard BEFORE _decode/seek/quantity conversion. Equal availability is allowed.
        if day(entry['target_dates'][-1])>=at or day(entry['available_at'])>at:raise ValueError('label unavailable before cutoff')
        return self._decode(entry)


def fit_prefix(inputs,transforms,reader,cutoff):
    if cutoff not in CUTS:raise ValueError('fixed quarter cutoff required')
    accepted=[];excluded=[]
    for row in sorted(inputs,key=lambda r:(r['origin'],r['store'])):
        readiness=input_readiness(row,transforms,asof=cutoff,purpose='historical_fit')
        end=day(row['target_dates'][-1]);available=day(row['target_dates'][0])+dt.timedelta(days=14)
        if not readiness['ready'] or end>=day(cutoff) or available>day(cutoff):
            excluded.append({'key':row['key'],'reason':'input_or_label_date_not_available'});continue
        label=reader.read_available(row,cutoff)
        if None in label['raw_actual']:
            excluded.append({'key':row['key'],'reason':'past_label_incomplete'});continue
        accepted.append(row['key'])
    return {'cutoff':cutoff,'accepted_keys':accepted,'excluded':excluded,'decoded_keys':list(reader.decoded_keys),'model_fit_performed':False}


def label_scenarios(row,label):
    validate_input(row);validate_label(label)
    if any(row[k]!=label[k] for k in ('key','store','origin','target_dates')):raise ValueError('scenario identity mismatch')
    raw=list(label['raw_actual']);assumed=[0. if v is None and not opened else v for v,opened in zip(raw,row['assumed_open_mask'])]
    return {'observed':{'raw_actual':list(raw),'actual':list(raw),'complete':None not in raw},
            'assumed_missing_zero':{'raw_actual':list(raw),'actual':assumed,'complete':None not in assumed},
            'imputed_positions':[j for j,(a,b) in enumerate(zip(raw,assumed)) if a is None and b==0.],
            'original_observed_days':sum(v is not None for v in raw)}
