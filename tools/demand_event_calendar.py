"""As-of event-relative inputs; holidays do not imply store closure."""
import datetime as dt

RADIUS = 3


def _aware(value):
    if not isinstance(value,dt.datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError('timezone-aware availability time required')
    return value


def _versions(records, as_of):
    chosen = {}; excluded = []
    for record in records:
        identity = record['record_id']
        if not isinstance(identity,str) or not identity:
            raise ValueError('stable nonempty record ID required')
        known = record['known_at']
        if known is None:
            excluded.append({'record_id':identity,'reason':'unknown_availability_time'});continue
        known = _aware(known)
        if known > as_of:
            excluded.append({'record_id':identity,'reason':'not_yet_known'});continue
        if identity in chosen and chosen[identity][0] == known:
            raise ValueError('ambiguous versions at the same availability time')
        if identity not in chosen or known > chosen[identity][0]:
            chosen[identity] = (known,record)
    return [chosen[key][1] for key in sorted(chosen)], excluded


def _applies(record, store):
    stores = record['stores']
    if stores is None:
        return True
    if not isinstance(stores,(tuple,list)) or any(type(s) is not int for s in stores):
        raise ValueError('explicit store scope required')
    return store in stores


def _active(record):
    if type(record['cancelled']) is not bool:
        raise ValueError('explicit cancellation state required')
    return not record['cancelled']


def build_inputs(events, operating_records, days, as_of, store, kinds, event_schedule_complete=False):
    as_of = _aware(as_of)
    if type(store) is not int or type(event_schedule_complete) is not bool:
        raise ValueError('store identity and explicit completeness flag required')
    if not kinds or len(kinds)!=len(set(kinds)) or any(not isinstance(k,str) or not k for k in kinds):
        raise ValueError('distinct declared event kinds required')
    if not days or any(type(d) is not dt.date for d in days) or len(days)!=len(set(days)):
        raise ValueError('distinct local calendar dates required')
    selected_events,event_excluded = _versions(events,as_of)
    selected_operations,operation_excluded = _versions(operating_records,as_of)
    if event_schedule_complete and any(r['reason']=='unknown_availability_time' for r in event_excluded):
        raise ValueError('unknown event availability cannot certify calendar completeness')
    columns=[{'kind':kind,'relative_day':offset} for kind in kinds for offset in range(-RADIUS,RADIUS+1)]
    index={(c['kind'],c['relative_day']):i for i,c in enumerate(columns)}
    rows={day:{'date':str(day),'features':[0]*len(columns),'event_matches':[],
               'operating_status':'unknown','operating_known':False} for day in days}
    for record in selected_events:
        if not _applies(record,store) or not _active(record):continue
        day=record['date'];kind=record['kind']
        if type(day) is not dt.date or kind not in kinds:
            raise ValueError('calendar date and declared kind required')
        for target,row in rows.items():
            relative=(target-day).days
            if -RADIUS<=relative<=RADIUS:
                row['features'][index[kind,relative]]=1
                row['event_matches'].append({'record_id':record['record_id'],'kind':kind,'relative_day':relative})
    seen_status={}
    for record in selected_operations:
        if not _applies(record,store) or not _active(record):continue
        day=record['date']
        if type(day) is not dt.date:raise ValueError('local operating date required')
        if day not in rows:continue
        status=record['status']
        if status not in ('open','closed','unknown'):raise ValueError('explicit operating status required')
        if day in seen_status and seen_status[day]!=status:raise ValueError('conflicting operating records')
        seen_status[day]=status
        rows[day]['operating_status']=status;rows[day]['operating_known']=status!='unknown'
    return {'as_of':as_of.isoformat(),'store':store,'columns':columns,'daily':[rows[d] for d in days],
            'event_schedule_complete':event_schedule_complete,'excluded_event_versions':event_excluded,
            'excluded_operating_versions':operation_excluded,'sales_or_forecast_changed':False}
