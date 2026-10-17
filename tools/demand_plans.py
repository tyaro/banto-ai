"""As-of selection of daily family-level planned promotion snapshots.

This is an input mechanism, not a demand model. Caller-provided provenance and
publication clocks still require source evidence. Realized promotion rows are
not an alternative to planned snapshots.
"""
from __future__ import annotations
import datetime as dt

FIELDS = {'series_id', 'target_date', 'available_at', 'onpromotion',
          'status', 'source_kind', 'scope', 'source_id', 'revision_id'}


def _clock(value):
    if not isinstance(value, str) or len(value) > 40:
        raise ValueError('publication timestamp must be an ISO string with offset')
    clock = dt.datetime.fromisoformat(value)
    if clock.tzinfo is None or clock.utcoffset() is None:
        raise ValueError('publication timestamp needs an explicit offset')
    return clock.astimezone(dt.timezone.utc)


def _identifier(value, name):
    if not isinstance(value, str) or not value or len(value) > 128:
        raise ValueError('invalid ' + name)
    return value


def promotion_features(records, *, series_id, issue_time, target_dates):
    """Latest available revision per series/date; unknown is a masked null.

    'cancelled' is an explicit zero for the *whole family snapshot*. Cancelling
    one event is not enough to produce a family-level zero. A newer 'unknown'
    revision supersedes older known data rather than silently falling back.
    """
    _identifier(series_id, 'series_id')
    if not isinstance(issue_time, dt.datetime) or issue_time.tzinfo is None or issue_time.utcoffset() is None:
        raise ValueError('issue_time must be an aware datetime')
    issue_time = issue_time.astimezone(dt.timezone.utc)
    if not isinstance(records, (list, tuple)) or len(records) > 4096:
        raise ValueError('at most 4096 planned snapshots per call')
    if not isinstance(target_dates, (list, tuple)) or not 1 <= len(target_dates) <= 14:
        raise ValueError('one to fourteen target dates required')
    if any(type(date) is not dt.date for date in target_dates) or len(set(target_dates)) != len(target_dates):
        raise ValueError('target dates must be distinct civil dates')
    requested = set(target_dates)
    selected, clocks = {}, set()
    for row in records:
        if not isinstance(row, dict) or set(row) != FIELDS:
            raise ValueError('planned snapshot schema differs')
        if row['source_kind'] != 'planned':
            raise ValueError('realized promotion cannot be used as a planned input')
        if row['scope'] != 'family_total':
            raise ValueError('a complete family-level daily snapshot is required')
        if row['series_id'] != series_id:
            continue
        if not isinstance(row['target_date'], str):
            raise ValueError('target_date must be an ISO civil-date string')
        date = dt.date.fromisoformat(row['target_date'])
        if str(date) != row['target_date']:
            raise ValueError('target_date must use YYYY-MM-DD')
        if date not in requested:
            continue
        available = _clock(row['available_at'])
        if available > issue_time:
            continue  # Do not inspect unavailable numerical payload or status.
        key = (date, available)
        if key in clocks:
            raise ValueError('ambiguous revisions at the same publication timestamp')
        clocks.add(key)
        _identifier(row['source_id'], 'source_id')
        _identifier(row['revision_id'], 'revision_id')
        status, count = row['status'], row['onpromotion']
        if status == 'unknown':
            if count is not None:
                raise ValueError('unknown promotion count must be null')
        elif status in ('known', 'cancelled'):
            if type(count) is not int or count < 0:
                raise ValueError('known promotion count must be a nonnegative integer')
            if status == 'cancelled' and count != 0:
                raise ValueError('cancelled family snapshot must explicitly have zero count')
        else:
            raise ValueError('unsupported planned status')
        if date not in selected or available > selected[date][0]:
            selected[date] = (available, row)
    output = []
    for date in target_dates:
        chosen = selected.get(date)
        if chosen is None:
            output.append({'target_date': str(date), 'onpromotion': None, 'known': False,
                'status': 'unknown', 'missing_reason': 'no_available_snapshot',
                'source_id': None, 'revision_id': None, 'available_at': None})
        else:
            available, row = chosen
            known = row['status'] != 'unknown'
            output.append({'target_date': str(date), 'onpromotion': row['onpromotion'], 'known': known,
                'status': row['status'], 'missing_reason': None if known else 'published_unknown',
                'source_id': row['source_id'], 'revision_id': row['revision_id'], 'available_at': available.isoformat()})
    return output
