"""Read prepared cycle windows without crossing a cycle or using condition labels."""
from array import array
import json
from pathlib import Path
import sys


def hydraulic_window(root, cycle, origin, *, context=128, horizon=32, split):
    root = Path(root)
    m = json.loads((root/'dataset.json').read_text())
    if type(cycle) is not int or type(origin) is not int or context <= 0 or horizon <= 0:
        raise ValueError('integer cycle/origin and positive window lengths required')
    if not 0 <= cycle < m['cycles'] or origin < context or origin+horizon > m['samples_per_cycle']:
        raise ValueError('window would cross a cycle boundary')
    bounds = m['splits'][split]
    if not bounds[0] <= cycle < bounds[1]: raise ValueError('cycle is outside requested split')
    x,y = [],[]
    for s in m['signals']:
        with (root/s['file']).open('rb') as f:
            f.seek((cycle*m['samples_per_cycle']+origin-context)*4)
            data = array('f'); data.frombytes(f.read((context+horizon)*4))
        if sys.byteorder != 'little': data.byteswap()
        if len(data) != context+horizon: raise ValueError('truncated prepared data')
        x.append(list(data[:context]));y.append(list(data[context:]))
    return {'context':x,'future_target':y,'cycle':cycle,'origin':origin,'split':split,
            'condition_labels_in_input':False}
