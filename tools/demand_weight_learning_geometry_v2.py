"""Frozen-feature geometry and own-store span only. No training or forecasting."""
from collections import Counter
from datetime import date,timedelta
import hashlib,json
from fractions import Fraction as F
from demand_bounded_metrics import Arithmetic
from demand_ordered_weight_audit_v3 import rank,gram,sum_exact,compare_fraction

FIT=(6,7,10,13,15,17,19,23,26,27)
TRAIN={'key','store','origin','old_x','z','r','w','v'}
ISSUE={'key','store','origin','old_x','z','r'}

def fraction_ratio(n,d,a):
    return None if not d else str(a.div(n,d))

def date_geometry(rows,a):
    old=[(row['key'],list(map(a.value,row['old_x']))) for row in rows if row['old_x'] is not None]
    new=[(row['key'],list(map(a.value,row['z']))) for row in rows if row['old_x'] is not None]
    weights=[a.value(row['w']) for row in rows if row['old_x'] is not None]
    full={'old_rank':rank(old,a),'new_rank':rank(new,a),'old_gram':gram(old,weights,a),'new_gram':gram(new,weights,a)}
    deletions=[]
    for origin in sorted({row['origin'] for row in rows}):
        a.checkpoint();removed=[row for row in rows if row['origin']==origin];remaining=[row for row in rows if row['origin']!=origin]
        assert len(removed)==len({row['store'] for row in removed})
        oo=[(row['key'],list(map(a.value,row['old_x']))) for row in remaining if row['old_x'] is not None]
        nn=[(row['key'],list(map(a.value,row['z']))) for row in remaining if row['old_x'] is not None]
        ww=[a.value(row['w']) for row in remaining if row['old_x'] is not None]
        record={'removed_origin':origin,'removed_keys':[row['key'] for row in removed],
            'remaining_keys':[row['key'] for row in remaining],'remaining_rows':len(remaining),
            'remaining_E':len(nn),'remaining_nonzero_rows':sum(any(F(x) for x in row['z']) for row in remaining if row['z'] is not None),
            'remaining_nonzero_stores':sorted({row['store'] for row in remaining if row['z'] is not None and any(F(x) for x in row['z'])}),
            'remaining_origins':sorted({row['origin'] for row in remaining}),
            'remaining_original_objective_weight':str(sum_exact(ww,a)),
            'remaining_original_risk_weight':str(sum_exact((a.value(row['v']) for row in remaining),a)),
            'original_denominators_reestimated':False}
        for name,vectors in (('old',oo),('new',nn)):
            record[name+'_rank']=rank(vectors,a);G=gram(vectors,ww,a);record[name+'_gram']=G;base=full[name+'_gram']
            trace=a.value(base['trace']);det=a.value(base['determinant']);remaining_det=a.value(G['determinant'])
            record[name+'_removed_energy_share']=fraction_ratio(a.sub(trace,a.value(G['trace'])),trace,a)
            record[name+'_determinant_retention']=fraction_ratio(remaining_det,det,a)
            record[name+'_removed_column_shares']=[fraction_ratio(a.sub(a.value(base['matrix'][j][j]),a.value(G['matrix'][j][j])),a.value(base['matrix'][j][j]),a) for j in range(3)]
            for value in (record[name+'_removed_energy_share'],record[name+'_determinant_retention'],*record[name+'_removed_column_shares']):
                if value is not None and (compare_fraction(F(value),F(),a)<0 or compare_fraction(F(value),F(1),a)>0):raise AssertionError('geometry ratio outside [0,1]')
        deletions.append(record)
    return {'full':full,'deletions':deletions,
        'all_single_date_remaining_rank3':all(row['new_rank']['rank']==3 for row in deletions),
        'full_rank3':full['new_rank']['rank']==3}

def store_span(train,issues,a):
    own=[(row['key'],list(map(a.value,row['z']))) for row in train if row['z'] is not None]
    cert=rank(own,a);n=cert['rank'];probes=[]
    for row in issues:
        a.checkpoint();z=row['z']
        if z is None:
            probes.append({'key':row['key'],'origin':row['origin'],'status':'old_unsupported','augmented_rank':None})
            continue
        vector=list(map(a.value,z));aug=rank(own+[(row['key'],vector)],a)['rank']
        probes.append({'key':row['key'],'origin':row['origin'],'status':'eligible_zero' if not any(vector) else 'nonzero_outside_own_span' if aug>n else 'nonzero_in_own_span','augmented_rank':aug})
    return {'train_rows':len(train),'train_E':len(own),'train_nonzero_rows':sum(any(v) for key,v in own),'train_rank':cert,
        'train_original_objective_mass':str(sum_exact((a.value(row['w']) for row in train),a)),
        'train_original_risk_mass':str(sum_exact((a.value(row['v']) for row in train),a)),
        'train_informative_original_objective_mass':str(sum_exact((a.value(row['w']) for row in train if row['z'] is not None and any(F(x) for x in row['z'])),a)),
        'zero_own_signal':n==0,'issue_rows':len(issues),'issue_status_counts':dict(Counter(row['status'] for row in probes)),
        'potential_shared_application_without_own_signal':[row['key'] for row in probes if n==0 and row['status']=='nonzero_outside_own_span'],
        'probes':probes,'beta_or_prediction_computed':False}

def validate_packet(packet,a):
    if set(packet)!={'schema','groups','source_pins'} or packet['schema']!='weight-learning-geometry-v1' or len(packet['groups'])!=4:raise ValueError('strict four-season projection required')
    seen=set();seen_pairs=set()
    for q,group in enumerate(packet['groups'],1):
        if set(group)!={'quarter','train','issues'} or group['quarter']!=q:raise ValueError('ordered quarter metadata')
        train=group['train'];issues=group['issues']
        if len(train)!=(30,60,70,50)[q-1] or len(issues)!=(70,60,70,60)[q-1]:raise ValueError('frozen membership counts')
        for kind,rows in (('train',train),('issues',issues)):
            first=date(2013,2,26) if kind=='train' else date(2014,1,1)
            total=21 if kind=='train' else 26
            expected={str(first+timedelta(days=14*j)) for j in range(total) if (first+timedelta(days=14*j)).month in range(3*q-2,3*q+1)}
            if {row['origin'] for row in rows}!=expected:raise ValueError('exact frozen issue calendar')
            for origin in expected:
                at=[row for row in rows if row['origin']==origin]
                if len(at)!=10 or {row['store'] for row in at}!=set(FIT):raise ValueError('exact FIT10 per date')
        ne=Counter(row['store'] for row in train if row['old_x'] is not None);ni=Counter(row['store'] for row in train)
        if set(ne)!=set(FIT) or set(ni)!=set(FIT):raise ValueError('original ten-store membership')
        for kind,rows in (('train',train),('issues',issues)):
            for row in rows:
                if set(row)!=(TRAIN if kind=='train' else ISSUE) or row['key'] in seen:raise ValueError('strict unique projected row')
                seen.add(row['key'])
                pair=(row['store'],row['origin'])
                if pair in seen_pairs:raise ValueError('duplicate store/origin')
                seen_pairs.add(pair)
                origin=date.fromisoformat(row['origin'])
                targets=[str(origin+timedelta(days=j)) for j in range(14)]
                raw=json.dumps({'schema':'demand-key-v1','store':row['store'],'origin':row['origin'],'target_dates':targets},sort_keys=True,separators=(',',':')).encode()
                if hashlib.sha256(raw).hexdigest()!=row['key']:raise ValueError('source identity key mismatch')
                if row['store'] not in FIT or not row['origin'].startswith('2013-' if kind=='train' else '2014-') or (int(row['origin'][5:7])-1)//3+1!=q:raise ValueError('allowed year/quarter/store')
                weight=a.value(row['r'])
                if not 0<=weight<=1:raise ValueError('stored r range')
                xs=None if row['old_x'] is None else list(map(a.value,row['old_x']));zs=None if row['z'] is None else list(map(a.value,row['z']))
                if xs is None:
                    if zs is not None:raise ValueError('unsupported still None')
                elif len(xs)!=3 or xs[0]!=1 or zs!=[a.mul(weight,x) for x in xs]:raise ValueError('exact saved feature product')
                if kind=='train':
                    if a.value(row['w'])!=(F(1,10*ne[row['store']]) if xs is not None else 0) or a.value(row['v'])!=F(1,10*ni[row['store']]):raise ValueError('preserved original E/I weights')

def analyze(packet,checkpoint=lambda:None):
    a=Arithmetic(checkpoint);validate_packet(packet,a);quarters={};stores={}
    for group in packet['groups']:
        q=group['quarter'];quarters['Q'+str(q)]=date_geometry(group['train'],a)
        for store in FIT:stores[str(store)+'/Q'+str(q)]=store_span([row for row in group['train'] if row['store']==store],[row for row in group['issues'] if row['store']==store],a)
    return {'status':'complete','quarters':quarters,'stores':stores,'deletions':sum(len(q['deletions']) for q in quarters.values()),
        'geometry_structure_met':all(q['full_rank3'] and q['all_single_date_remaining_rank3'] for q in quarters.values()),
        'max_bits':a.max_bits,'new_r':False,'new_fit':False,'new_prediction':False,'new_label_quantity_decode':False,'new_performance_score':False,'new2015':False,
        'training_consumer_implemented':False,'explicit_learning_restart_authorized':False,'can_launch_learning':False,'fit_ready':False}
