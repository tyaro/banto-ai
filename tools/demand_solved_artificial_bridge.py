"""Explicit synthetic-fit provenance around the immutable input-only bridge."""
import json
from datetime import date
from demand_weighted_problem_consumer import pin_value
from demand_input_boundary_v2 import CUTS
from demand_weighted_daily_bridge import forecast as fixed_forecast

class ConnectionFailure(ValueError):pass

def forecast(payload,*,verify_certificate,checkpoint=lambda:None):
    if type(payload) is not dict or set(payload)!={'schema','compiled','certificate','input','weighted','transforms'} or payload['schema']!='solved-synthetic-daily-request-v1':raise ConnectionFailure('strict synthetic connector schema; no caller beta or issue labels')
    compiled=payload['compiled'];cert=payload['certificate'];inp=payload['input']
    if type(compiled) is not dict or compiled.get('schema')!='compiled-weighted-season-problem-v1' or type(cert) is not dict:raise ConnectionFailure('compiled/certificate schema')
    q=compiled['quarter'];cut=compiled['cutoff']
    if type(q) is not int or q not in range(1,5) or cut!=CUTS[q-1] or compiled['lambda']!='1' or compiled['solve_called'] is not False:raise ConnectionFailure('same compiled ownQ and fixed lambda')
    issue=date.fromisoformat(inp['origin'])
    if issue.year!=2014 or (issue.month-1)//3+1!=q or cut>inp['origin']:raise ConnectionFailure('same issue quarter and available cutoff')
    if any(row['quarter']!=q for row in compiled['problem']['rows']) or cert.get('problem_pin')!=pin_value(compiled['problem']):raise ConnectionFailure('compiled/source problem binding')
    verification=verify_certificate(compiled['problem'],cert,checkpoint)
    if verification['status']!='exact_artificial_optimum_verified' or verification['quarter']!=q or verification['gap']!='0' or not verification['all_original_constraints'] or verification['beta']!=cert['beta']:raise ConnectionFailure('verified certificate required')
    legacy={'schema':'weighted-daily-artificial-request-v1','input':payload['input'],'transforms':payload['transforms'],'weighted':payload['weighted'],
            'state':{'schema':'fixed-artificial-coefficients-v1','source_quarter':q,'cutoff':cut,'usable_from':cut,'beta':cert['beta'][:],'fit_performed':False}}
    # A strict JSON projection prevents future labels, rows, readers, or provenance
    # dictionaries entering the pure prediction component.
    legacy=json.loads(json.dumps(legacy,allow_nan=False));daily=fixed_forecast(legacy,checkpoint)
    return {'schema':'solved-synthetic-daily-result-v1','artificial_prefix_fit_performed':True,'real_fit_performed':False,'source_quarter':q,'cutoff':cut,'beta':cert['beta'][:],
            'bindings':{'consumer_input':compiled['input_pin'],'compiled':pin_value(compiled),'problem':pin_value(compiled['problem']),'certificate':pin_value(cert),'verification':pin_value(verification),'issue_input':pin_value(inp),'legacy_payload':pin_value(legacy)},
            'legacy_fit_flag_scope':'bridge component only; coefficients originated in synthetic prefix solve','verification':verification,'legacy_payload':legacy,'daily':daily,'fit_ready':False,'can_launch_learning':False}
