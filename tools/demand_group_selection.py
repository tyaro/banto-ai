"""Fixed store split and two checkpoint choices on one transfer-stopped trajectory."""
import math
from demand_training_adequacy import split_keys, EarlyStopper

GROUP_A = (6, 10, 15, 19, 26)
GROUP_B = (7, 13, 17, 23, 27)
GROUP_C = (9, 14, 18, 25, 30)
FIT = tuple(sorted(GROUP_A + GROUP_B))
POSITIVE = tuple(sorted(FIT + GROUP_C))


def cohort_split(keys):
    split = split_keys(keys)
    if set(s for s, _ in keys) != set(POSITIVE) or split['crossing']:
        raise ValueError('fixed positive15 and no crossing labels required')
    for s in POSITIVE:
        if sum(store == s for store, _ in split['train']) != 30 or sum(store == s for store, _ in split['validation']) != 12:
            raise ValueError('fixed 30 fit-period and 12 validation-period keys required')
    return {'fit': [k for k in split['train'] if k[0] in FIT],
            'time_validation': [k for k in split['validation'] if k[0] in FIT],
            'transfer_validation': [k for k in split['validation'] if k[0] in GROUP_C],
            'unused_C_preperiod': [k for k in split['train'] if k[0] in GROUP_C],
            'cutoff': split['cutoff']}


class DualSelector:
    def __init__(self, **policy):
        self.transfer = EarlyStopper(**policy)
        self.time_best, self.time_best_step = None, None

    def observe(self, step, time_loss, transfer_loss):
        if type(time_loss) not in (int, float) or not math.isfinite(time_loss) or time_loss < 0:
            raise ValueError('finite nonnegative time validation required')
        selected = self.transfer.observe(step, transfer_loss)
        time_new = self.time_best is None or time_loss < self.time_best
        if time_new:
            self.time_best, self.time_best_step = time_loss, step
        return {'time_new_best': time_new, 'time_best_step': self.time_best_step,
                'time_best_loss': self.time_best, 'transfer_new_best': selected['new_best'],
                'transfer_best_step': selected['best_step'], 'transfer_best_loss': selected['best_validation_loss'],
                'stop': selected['stop'], 'bad_checkpoints': selected['bad_checkpoints'],
                'meaningful_transfer_improvement': selected['meaningful_improvement']}


def progress(candidate, baseline, support_unchanged, minimum=2.0):
    """Provisional development investment gate, not a business adoption criterion."""
    for values in (candidate, baseline):
        if any(type(values[k]) not in (int, float) or not math.isfinite(values[k]) or values[k] < 0
               for k in ('daily', 'total', 'joint')):
            raise ValueError('finite complete fixed metrics required')
    if type(support_unchanged) is not bool or baseline['joint'] <= 0 or not 0 < minimum < 100:
        raise ValueError('explicit support and positive baseline required')
    improvement = 100*(1-candidate['joint']/baseline['joint'])
    passed = (support_unchanged and improvement >= minimum
              and candidate['daily'] <= baseline['daily'] and candidate['total'] <= baseline['total'])
    return {'improvement_percent': improvement, 'minimum_percent': minimum,
            'daily_no_worse': candidate['daily'] <= baseline['daily'],
            'total_no_worse': candidate['total'] <= baseline['total'],
            'support_unchanged': support_unchanged, 'development_progress': passed,
            'business_adoption': False}
