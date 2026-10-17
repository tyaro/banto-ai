"""As-of interval events and separate operating calendar; no sales or fitting.

Dates are inclusive local dates. Unknown end never implies infinite duration.
Same-kind flags are binary; each event's duration remains in event_positions.
"""
import datetime as dt

from demand_event_calendar import RADIUS, _active, _applies, _aware, _versions


def _date(value):
    if type(value) is not dt.date:
        raise ValueError('local calendar date required')
    return value


def _operating_calendar(records, store):
    calendar = {}
    for record in records:
        if not _applies(record, store) or not _active(record):
            continue
        day = _date(record['date'])
        status = record['status']
        if status not in ('open', 'closed', 'unknown'):
            raise ValueError('explicit operating status required')
        if day in calendar and calendar[day] != status:
            raise ValueError('conflicting operating records')
        calendar[day] = status
    return calendar


def _closure_runs(calendar):
    blocks = []
    for day in sorted(d for d, status in calendar.items() if status == 'closed'):
        if blocks and (day - blocks[-1][-1]).days == 1:
            blocks[-1].append(day)
        else:
            blocks.append([day])
    lookup = {}
    for block in blocks:
        start, end = block[0], block[-1]
        # Missing calendar neighbours and explicit unknowns cannot close a run.
        left_open = calendar.get(start - dt.timedelta(days=1)) == 'open' if start > dt.date.min else False
        right_open = calendar.get(end + dt.timedelta(days=1)) == 'open' if end < dt.date.max else False
        summary = {'start_confirmed':str(start), 'end_confirmed':str(end),
                   'length_lower_bound':len(block), 'left_boundary_known':left_open,
                   'right_boundary_known':right_open,
                   'length':len(block) if left_open and right_open else None}
        for day in block:
            lookup[day] = summary
    return lookup


def build_interval_inputs(events, operating_records, days, as_of, store, kinds,
                          event_schedule_complete=False):
    """Select available versions before touching dates, lengths or scope.

    A finite event uses start/end and end_status='scheduled'. An unresolved
    event uses end=None, confirmed_through, and end_status='ongoing' or
    'schedule_unavailable'. Active membership after confirmed_through is unknown.
    All supplied operating dates are used, including outside the target window.
    """
    as_of = _aware(as_of)
    if type(store) is not int or type(event_schedule_complete) is not bool:
        raise ValueError('store identity and explicit completeness required')
    if not kinds or any(not isinstance(k, str) or not k for k in kinds) or len(set(kinds)) != len(kinds):
        raise ValueError('distinct declared event kinds required')
    if not days or any(type(d) is not dt.date for d in days) or len(set(days)) != len(days):
        raise ValueError('distinct local calendar dates required')
    selected, excluded = _versions(events, as_of)
    operations, operation_excluded = _versions(operating_records, as_of)
    if event_schedule_complete and any(x['reason'] == 'unknown_availability_time' for x in excluded):
        raise ValueError('unknown availability cannot certify completeness')
    phases = [f'before_{k}' for k in range(RADIUS, 0, -1)] + ['during']
    phases += [f'after_{k}' for k in range(1, RADIUS + 1)] + ['undetermined']
    columns = [{'kind':kind, 'phase':phase} for kind in kinds for phase in phases]
    index = {(c['kind'], c['phase']):i for i, c in enumerate(columns)}
    calendar = _operating_calendar(operations, store)
    closures = _closure_runs(calendar)
    rows = {day:{'date':str(day), 'features':[0]*len(columns), 'event_positions':[],
                 'operating_status':calendar.get(day, 'unknown'),
                 'operating_known':calendar.get(day, 'unknown') != 'unknown',
                 'closure_run':closures.get(day)} for day in days}
    intervals = []
    for record in selected:
        if not _applies(record, store) or not _active(record):
            continue
        kind, start, end = record['kind'], _date(record['start']), record['end']
        if kind not in kinds:
            raise ValueError('declared event kind required')
        end_status = record['end_status']
        if end is not None:
            end = _date(end)
            if end < start or end_status != 'scheduled':
                raise ValueError('ordered scheduled interval required')
            extent, length = end, (end-start).days + 1
        else:
            if end_status not in ('ongoing', 'schedule_unavailable'):
                raise ValueError('explicit unresolved end reason required')
            extent = _date(record['confirmed_through'])
            if extent < start:
                raise ValueError('confirmed extent must reach start')
            if event_schedule_complete:
                raise ValueError('unresolved event cannot certify completeness')
            length = None
        intervals.append({'record_id':record['record_id'], 'kind':kind,
                          'known_at':record['known_at'].isoformat(), 'start':str(start),
                          'end':str(end) if end is not None else None,
                          'confirmed_through':str(extent), 'end_status':end_status,
                          'length':length, 'length_known':length is not None})
        for target, row in rows.items():
            from_start = (target-start).days
            from_end = (target-end).days if end is not None else None
            if target < start:
                phase = 'before'
                channel = f'before_{-from_start}' if from_start >= -RADIUS else None
            elif target <= extent:
                phase, channel = 'during', 'during'
            elif end is None:
                phase, channel = 'undetermined', 'undetermined'
            else:
                phase = 'after'
                channel = f'after_{from_end}' if from_end <= RADIUS else None
            if channel is not None:
                row['features'][index[kind, channel]] = 1
            row['event_positions'].append({'record_id':record['record_id'], 'kind':kind,
                'phase':phase, 'days_from_start':from_start, 'days_from_end':from_end,
                'length':length, 'length_known':length is not None,
                'length_unknown_reason':None if length is not None else end_status})
    return {'as_of':as_of.isoformat(), 'store':store, 'columns':columns,
            'intervals':intervals, 'daily':[rows[d] for d in days],
            'event_schedule_complete':event_schedule_complete,
            'excluded_event_versions':excluded, 'excluded_operating_versions':operation_excluded,
            'sales_or_forecast_changed':False}
