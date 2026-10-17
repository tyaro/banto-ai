"""Input-only integration and descriptive support audit; no targets or fitting."""
from collections import Counter
from fractions import Fraction as F
from datetime import timedelta

from demand_bounded_metrics import Arithmetic
from demand_input_boundary_v2 import FIT, CUTS, day, input_readiness
from demand_prefix_adapter import input_features
from demand_ordered_weight_v2 import encode_features, SCHEMA

METRICS = ('all_stored_positive_count', 'usable_positive_count', 'eligible_r', 'eligible_r2',
           'weighted_r', 'weighted_r2', 'old_energy', 'new_energy',
           'old_col0', 'old_col1', 'old_col2', 'new_col0', 'new_col1', 'new_col2')


def quarter(origin):
    return (int(origin[5:7])-1)//3+1


def encode_input(row, transforms, checkpoint=lambda: None):
    # Old transforms are usable at 2014 cutoff, not retrospectively at a 2013 origin.
    x, reasons = input_features(row, transforms)
    packet = {'schema': SCHEMA, 'origin': row['origin'], 'records': [
        {'date': d, 'available_at': av, 'value': v}
        for d, av, v in zip(row['past_dates'], row['past_available_at'], row['past_values'])]}
    result = encode_features(packet, x, checkpoint)
    return {'key': row['key'], 'store': row['store'], 'origin': row['origin'],
            'history': packet, 'old_features': x, 'old_reasons': reasons,
            'baseline': list(row['matched_mean28']), 'assumed_open_mask': list(row['assumed_open_mask']),
            'scale': transforms['scales'][str(row['store'])],
            'transform_usable_from': max(transforms['scale_usable_from'], transforms['closure_usable_from']),
            'encoded': result}


def make_groups(inputs, encoded, transforms, availability):
    bykey = {r['key']: r for r in inputs}
    if len(bykey) != len(inputs) or set(bykey) != set(encoded):
        raise ValueError('unique matching input and encoded keys')
    out = []

    def add(name, rows, kind, q=None, cutoff=None):
        E = Counter(r['store'] for r in rows if r['old_features'] is not None)
        I = Counter(r['store'] for r in rows)
        members = []
        for r in sorted(rows, key=lambda r: (r['origin'], r['store'])):
            eligible = r['old_features'] is not None
            members.append({'key': r['key'], 'store': r['store'], 'origin': r['origin'], 'old_E': eligible,
                'objective_weight': str(F(1, 10*E[r['store']])) if eligible else '0',
                'risk_weight': str(F(1, 10*I[r['store']])) if kind == 'historical' else None})
        out.append({'name': name, 'kind': kind, 'quarter': q, 'cutoff': cutoff,
                    'I_provenance': 'pinned_prior_accepted_keys' if kind == 'historical' else 'unknown_no_labels_decoded',
                    'members': members})

    for q, cutoff in enumerate(CUTS, 1):
        ledger = availability[cutoff]
        if ledger['cutoff'] != cutoff or len(set(ledger['accepted_keys'])) != len(ledger['accepted_keys']):
            raise ValueError('unique trusted accepted ledger')
        if set(ledger['accepted_keys']) != set(ledger['decoded_keys']):
            raise ValueError('prior accepted and decoded metadata mismatch')
        rows = []
        for key in ledger['accepted_keys']:
            inp = bykey[key]
            if inp['target_dates'][-1] >= cutoff or str(day(inp['origin']) + timedelta(days=14)) > cutoff:
                raise ValueError('historical membership after cutoff')
            if not input_readiness(inp, transforms, asof=cutoff, purpose='historical_fit')['ready']:
                raise ValueError('historical preprocessing unavailable')
            if quarter(inp['origin']) == q:
                rows.append(encoded[key])
        expected = (30,60,70,50)[q-1]
        if (len(rows) != expected or sum(r['old_features'] is not None for r in rows) != expected
                or {r['origin'][:4] for r in rows} != {'2013'}
                or len({r['origin'] for r in rows}) != (3,6,7,5)[q-1]
                or set(r['store'] for r in rows) != set(FIT)):
            raise ValueError('preserved own-quarter E/I structural counts')
        add('train_Q'+str(q), rows, 'historical', q, cutoff)
    issue = [r for r in encoded.values() if r['origin'].startswith('2014-')]
    add('issue_all260', issue, 'issue')
    add('issue_normal250', [r for r in issue if r['origin']!='2014-01-01'], 'issue')
    add('issue_newyear10', [r for r in issue if r['origin']=='2014-01-01'], 'issue')
    add('issue_yearend', [r for r in issue if r['origin'].startswith('2014-12-')], 'issue')
    for q in range(1,5):
        rows = [r for r in issue if quarter(r['origin'])==q]
        add('issue_Q'+str(q)+'_all', rows, 'issue', q)
        add('issue_Q'+str(q)+'_normal', [r for r in rows if r['origin']!='2014-01-01'], 'issue', q)
    return out


def rank(rows, a, columns=(0,1,2)):
    """Incremental exact echelon basis with original-row witnesses."""
    basis = []
    for key, values in rows:
        a.checkpoint()
        v = [a.value(values[j]) for j in columns]
        for pivot, b, witness in basis:
            factor = v[pivot]
            v = [a.sub(x, a.mul(factor,y)) for x,y in zip(v,b)]
        if any(v):
            pivot = next(i for i,x in enumerate(v) if x)
            div = v[pivot];v = [a.div(x,div) for x in v]
            basis.append((pivot, v, key));basis.sort(key=lambda row:row[0])
    # Upper certificate: every original row reduces to zero in this span.
    for key, values in rows:
        v = [a.value(values[j]) for j in columns]
        for pivot,b,witness in basis:
            factor = v[pivot];v = [a.sub(x,a.mul(factor,y)) for x,y in zip(v,b)]
        if any(v):raise AssertionError('rank span certificate failed')
    return {'rank':len(basis), 'columns':list(columns), 'pivot_columns':[columns[p] for p,b,k in basis],
            'witness_keys':[k for p,b,k in basis], 'basis':[[str(v) for v in b] for p,b,k in basis]}


def sum_exact(xs, a):
    result = F(0)
    for x in xs:result = a.add(result,x)
    return result


def gram(rows, weights, a):
    G = [[sum_exact((a.mul(w,a.mul(v[i],v[j])) for (key,v),w in zip(rows,weights)),a) for j in range(3)] for i in range(3)]
    # Explicit 3x3 determinant, checked before and after cancellation.
    minor = lambda i,j,k,l:a.sub(a.mul(G[i][j],G[k][l]),a.mul(G[i][l],G[k][j]))
    determinant = a.add(a.sub(a.mul(G[0][0],minor(1,1,2,2)),a.mul(G[0][1],minor(1,0,2,2))),a.mul(G[0][2],minor(1,0,2,1)))
    if determinant < 0:raise AssertionError('Gram determinant must be nonnegative')
    product = a.mul(a.mul(G[0][0],G[1][1]),G[2][2])
    if product and not 0 <= a.div(determinant,product) <= 1:raise AssertionError('normalized determinant bounds')
    cos2 = {str(i)+str(j):str(a.div(a.square(G[i][j]),a.mul(G[i][i],G[j][j]))) if G[i][i] and G[j][j] else None for i,j in ((0,1),(0,2),(1,2))}
    if any(not 0 <= F(v) <= 1 for v in cos2.values() if v is not None):raise AssertionError('cosine squared bounds')
    return {'matrix':[[str(v) for v in row] for row in G], 'trace':str(sum_exact((G[i][i] for i in range(3)),a)),
            'determinant':str(determinant), 'normalized_determinant':str(a.div(determinant,product)) if product else None,
            'uncentered_cos_squared':cos2}


def concentration(masses, a):
    total = sum_exact(masses.values(),a)
    if total < 0 or any(v<0 for v in masses.values()):raise ValueError('nonnegative mass required')
    order = sorted(masses,key=lambda k:(-masses[k],k))
    if not total:
        return {'total':'0','shares':{str(k):None for k in order},'top1':None,'top3':None,
                'HHI':None,'mass_equivalent_groups':None,'reason':'zero_total'}
    shares = {str(k):a.div(masses[k],total) for k in order}
    hhi = sum_exact((a.square(v) for v in shares.values()),a)
    def top(n):
        chosen = order[:n];cut = masses[chosen[-1]]
        return {'keys':[str(k) for k in chosen], 'share':str(sum_exact((shares[str(k)] for k in chosen),a)),
                'boundary_tie_keys':[str(k) for k in order if masses[k]==cut]}
    return {'total':str(total),'shares':{k:str(v) for k,v in shares.items()},'top1':top(1),'top3':top(3),
            'HHI':str(hhi),'mass_equivalent_groups':str(a.div(1,hhi)),'reason':None}


def audit_group(group, encoded, checkpoint=lambda: None):
    a = Arithmetic(checkpoint);members = group['members']
    if len(members)>512:raise ValueError('audit row limit')
    eligible = [m for m in members if m['old_E']]
    old = [(m['key'],list(map(a.value,encoded[m['key']]['old_features']))) for m in eligible]
    new = [(m['key'],list(map(a.value,encoded[m['key']]['encoded']['features_exact']))) for m in eligible]
    positive_old = [(k,v) for k,v in old if F(encoded[k]['encoded']['state']['r_stored'])>0]
    weights = [a.value(m['objective_weight']) for m in eligible]
    oldrank = rank(old,a);newrank = rank(new,a);positive_rank = rank(positive_old,a)
    if newrank['rank'] != positive_rank['rank']:raise AssertionError('positive-row rank identity')
    table = {axis:{} for axis in ('store','origin')}
    flags = Counter();mass_rows = {};category_support = {}
    for m in members:
        checkpoint();r = encoded[m['key']];state = r['encoded']['state'];weight = a.value(m['objective_weight']);stored = a.value(state['r_stored'])
        flags['rows'] += 1;flags['old_E'] += m['old_E'];flags['raw_positive'] += F(state['r_raw'])>0
        flags['stored_positive'] += stored>0;flags['usable_positive'] += m['old_E'] and stored>0
        flags['computed'] += state['computed'];flags['reason:'+state['reason']] += 1
        if not m['old_E']:flags['old_unsupported'] += 1
        direction = m['old_E'] and stored>0 and any(F(x)!=0 for x in r['old_features'][1:])
        flags['usable_nonzero_direction'] += bool(direction)
        categories={'all_rows':True,'old_E':m['old_E'],'r_raw_positive':F(state['r_raw'])>0,'r_stored_positive':stored>0,
                    'usable_positive':m['old_E'] and stored>0,'nonzero_direction':bool(direction),'computed':state['computed'],
                    'weight_fallback':not state['computed'],'old_unsupported':not m['old_E'],
                    'positive_rounded_zero':state['reason']=='positive_weight_rounded_to_zero'}
        for category,yes in categories.items():
            cell=category_support.setdefault(category,{'rows':0,'stores':set(),'origins':set()})
            if yes:cell['rows']+=1;cell['stores'].add(r['store']);cell['origins'].add(r['origin'])
        masses = {k:F(0) for k in METRICS};masses['all_stored_positive_count'] = F(stored>0);masses['usable_positive_count'] = F(m['old_E'] and stored>0)
        if m['old_E']:
            xs = list(map(a.value,r['old_features']));zs = list(map(a.value,r['encoded']['features_exact']))
            masses.update(eligible_r=stored,eligible_r2=a.square(stored),weighted_r=a.mul(weight,stored),weighted_r2=a.mul(weight,a.square(stored)))
            for j in range(3):masses['old_col'+str(j)] = a.mul(weight,a.square(xs[j]));masses['new_col'+str(j)] = a.mul(weight,a.square(zs[j]))
            masses['old_energy'] = sum_exact((masses['old_col'+str(j)] for j in range(3)),a)
            masses['new_energy'] = sum_exact((masses['new_col'+str(j)] for j in range(3)),a)
        mass_rows[m['key']] = masses
        for axis in table:
            key = r[axis]
            if key not in table[axis]:table[axis][key] = {'rows':0,'old_E':0,'stored_positive':0,'usable_positive':0,'all_stored_r_sum':F(0),**{k:F(0) for k in METRICS}}
            cell = table[axis][key];cell['rows'] += 1;cell['old_E'] += m['old_E'];cell['stored_positive'] += stored>0;cell['usable_positive'] += m['old_E'] and stored>0
            cell['all_stored_r_sum'] = a.add(cell['all_stored_r_sum'],stored)
            for k in METRICS:cell[k] = a.add(cell[k],masses[k])
    axis_output = {}
    for axis,cells in table.items():
        ranks = {}
        for key in cells:
            oo = [(k,v) for k,v in old if encoded[k][axis]==key];nn = [(k,v) for k,v in new if encoded[k][axis]==key]
            ranks[str(key)] = {'old':rank(oo,a),'new':rank(nn,a)}
        axis_output[axis] = {'table':{str(key):{k:str(v) if isinstance(v,F) else v for k,v in cell.items()} for key,cell in sorted(cells.items())},
            'concentration':{metric:concentration({key:cell[metric] for key,cell in cells.items()},a) for metric in METRICS}, 'ranks':ranks}
    og = gram(old,weights,a);ng = gram(new,weights,a)
    if F(og['trace']) != sum_exact((v['old_energy'] for v in mass_rows.values()),a) or F(ng['trace']) != sum_exact((v['new_energy'] for v in mass_rows.values()),a):raise AssertionError('Gram/energy total mismatch')
    if (F(og['determinant'])>0)!=(oldrank['rank']==3) or (F(ng['determinant'])>0)!=(newrank['rank']==3):raise AssertionError('Gram determinant rank identity')
    positive_members = [m for m in eligible if F(encoded[m['key']]['encoded']['state']['r_stored'])>0]
    return {'name':group['name'],'kind':group['kind'],'counts':dict(flags),
        'category_support':{key:{'rows':cell['rows'],'store_count':len(cell['stores']),'origin_count':len(cell['origins']),'stores':sorted(cell['stores']),'origins':sorted(cell['origins'])} for key,cell in category_support.items()},
        'old_E_denominators':{str(s):sum(m['store']==s for m in eligible) for s in FIT},
        'I_denominators':{str(s):sum(m['store']==s for m in members) for s in FIT} if group['kind']=='historical' else None,
        'objective_weight_sum':str(sum_exact(weights,a)),
        'risk_weight_sum':str(sum_exact((a.value(m['risk_weight']) for m in members),a)) if group['kind']=='historical' else None,
        'usable_positive_stores':sorted({m['store'] for m in positive_members}), 'usable_positive_origins':sorted({m['origin'] for m in positive_members}),
        'old_rank':oldrank,'new_rank':newrank,'old_positive_subset_rank':positive_rank,
        'old_direction_rank':rank(old,a,(1,2)), 'new_direction_rank':rank(new,a,(1,2)),
        'old_gram':og,'new_gram':ng,'axes':axis_output,'max_bits':a.max_bits,
        'independent_sample_size_claim':False,'fit_ready':False}
