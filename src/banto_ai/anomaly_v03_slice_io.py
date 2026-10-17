"""Read one caller-pinned saved evaluation, retain only compact slice counts."""
from pathlib import Path
from . import anomaly_v03_slices as slices
from .anomaly_v03_observation_audit import read_pinned, scores, MIB


def read_saved_evaluation(path, pin, identity, prior_audit):
    """Caller must authenticate the pin and prior audit from a trusted savepoint.

    Reads at most 64 MiB of encoded JSON, one evaluation at a time. No source
    execution, score/matching replay, output write or global campaign is started.
    """
    slices.exact(prior_audit['identity'],identity,'requested audit identity')
    raw=read_pinned(Path(path),pin,64*MIB)
    result=scores.strict_json(raw)
    del raw
    slices.exact(result['identity'],identity,'requested payload identity')
    return slices.summarize_evaluation(result,prior_audit)
