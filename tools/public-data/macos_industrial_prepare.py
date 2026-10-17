"""Prepare bounded public industrial inputs; no model import, fit, or scoring."""
from array import array
from collections import Counter, defaultdict
import csv
import ctypes as C
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path
import re
import sys
import traceback
import zipfile
from macos_industrial_fetch import close, digest, write, ROOT
from macos_demand_runtime import MacCheckpoint


def load_module(name, path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m


def metro(raw,out,check):
    m=load_module('metropt3_import',ROOT/'tools/public-data/import_metropt3.py')
    result=m.import_metropt3(raw/'metropt3',accepted=True)
    if result != out: raise ValueError('unexpected fixed MetroPT output')
    fp=json.loads((out/'fingerprint.json').read_text())
    expected='e6210e4e48e05c025fc8895ddeddf0c53a49dc53fd1c2f49e8c3272a3c7b37b0'
    if fp['dataset_fingerprint'] != expected: raise ValueError('canonical fingerprint differs from old contract')
    # The adapter only forms tensors/scales/origins; this does not run the model.
    check.check()
    return {'status':'prepared','fingerprint':fp['dataset_fingerprint'],
            'source_and_transform': 'fixed 2020-02-21 exploratory day; not a new holdout',
            'model_runs':0,'rows':1440,'signals':14}


def hydraulic(raw,out,check):
    out.mkdir(parents=True,exist_ok=False)
    signals=[('PS1','bar'),('PS2','bar'),('EPS1','W')]
    meta={'format':'little-endian-float32-cycle-major','cycles':2205,'samples_per_cycle':600,
          'source_rate_hz':100,'prepared_rate_hz':10,'cycle_seconds':60,
          'transform':'mean of each consecutive 10 source samples; bin-end timestamps',
          'signals':[{'id':n,'unit':u,'file':n+'.f32le'} for n,u in signals],
          'splits':{'train':[0,1323],'validation':[1323,1764],'test':[1764,2205]},
          'split_status':'fixed exploratory cycle blocks; same rig, not independent equipment',
          'labels_file':'condition-labels.json','labels_are_features':False,'scaling_applied':False}
    with zipfile.ZipFile(raw/'hydraulic/hydraulic.zip') as z:
        for name,unit in signals:
            count=0
            with z.open(name+'.txt') as src,(out/(name+'.f32le')).open('xb') as dst:
                for line in src:
                    check.check()
                    values=[float(v) for v in line.split()]
                    if len(values)!=6000 or not all(map(math.isfinite,values)):
                        raise ValueError('invalid hydraulic cycle width/nonfinite')
                    down=array('f',(math.fsum(values[i:i+10])/10 for i in range(0,6000,10)))
                    if sys.byteorder!='little':down.byteswap()
                    if dst.tell()+len(down)*4>32*1024**2:raise ValueError('single output cap')
                    dst.write(down.tobytes());count+=1
                if count!=2205:raise ValueError('unexpected cycle count')
        labels=[]
        with z.open('profile.txt') as f:
            for line in f:
                row=[int(v) for v in line.split()]
                if len(row)!=5:raise ValueError('condition label width')
                labels.append(row)
        if len(labels)!=2205:raise ValueError('condition label count')
        write(out/'condition-labels.json',{'role':'offline condition targets; not input or known-future',
              'columns':['cooler_percent','valve_percent','pump_leakage_class','accumulator_bar','unstable_flag'],
              'rows':labels})
        for name in ('description.txt','documentation.txt'):
            (out/name).write_bytes(z.read(name))
    write(out/'dataset.json',meta)
    from industrial_data import hydraulic_window
    probes=[]
    for cycle,split in ((0,'train'),(1323,'validation'),(1764,'test')):
        w=hydraulic_window(out,cycle,128,split=split)
        if len(w['context'])!=3 or any(len(v)!=128 for v in w['context']) or any(len(v)!=32 for v in w['future_target']):
            raise ValueError('prepared loader shape')
        probes.append({'cycle':cycle,'split':split,'context_shape':[3,128],'target_shape':[3,32]})
    refusals=0
    for cycle,origin,split in ((0,127,'train'),(0,569,'train'),(1323,128,'train')):
        try:hydraulic_window(out,cycle,origin,split=split)
        except ValueError:refusals+=1
        else:raise ValueError('boundary refusal missing')
    # Independently read source cycle 0 and compare exactly the first prepared mean.
    with zipfile.ZipFile(raw/'hydraulic/hydraulic.zip') as z:
        for name,_ in signals:
            with z.open(name+'.txt') as f: reference=math.fsum(map(float,next(f).split()[:10]))/10
            with (out/(name+'.f32le')).open('rb') as f:
                actual=array('f');actual.frombytes(f.read(4))
                if sys.byteorder!='little':actual.byteswap()
            rounded=array('f',[reference])[0]
            if actual[0]!=rounded:raise ValueError('source to binary readback mismatch')
    return {'status':'prepared','cycles':2205,'signals':3,'samples_per_cycle':600,
            'all_selected_source_cells_finite':True,'loader_probes':probes,'refusals':refusals,
            'first_bin_independent_source_checks':3,'model_runs':0}


class RarReader:
    """macOS system libarchive multivolume reader; no filesystem extraction."""
    def __init__(self,files):
        self.lib=C.CDLL('/usr/lib/libarchive.dylib');lib=self.lib
        specs={'archive_read_new':([],C.c_void_p),'archive_read_support_format_all':([C.c_void_p],C.c_int),
               'archive_read_support_filter_all':([C.c_void_p],C.c_int),
               'archive_read_open_filenames':([C.c_void_p,C.POINTER(C.c_char_p),C.c_size_t],C.c_int),
               'archive_read_next_header':([C.c_void_p,C.POINTER(C.c_void_p)],C.c_int),
               'archive_entry_pathname':([C.c_void_p],C.c_char_p),'archive_entry_size':([C.c_void_p],C.c_int64),
               'archive_read_data':([C.c_void_p,C.c_void_p,C.c_size_t],C.c_ssize_t),
               'archive_error_string':([C.c_void_p],C.c_char_p),'archive_read_free':([C.c_void_p],C.c_int)}
        for n,(args,res) in specs.items():getattr(lib,n).argtypes=args;getattr(lib,n).restype=res
        self.a=lib.archive_read_new();lib.archive_read_support_format_all(self.a);lib.archive_read_support_filter_all(self.a)
        self.names=(C.c_char_p*(len(files)+1))(*[str(p).encode() for p in files],None)
        rc=lib.archive_read_open_filenames(self.a,self.names,1024**2)
        if rc!=0:raise RuntimeError(self.error())
        self.buf=C.create_string_buffer(1024**2)
    def error(self):
        return (self.lib.archive_error_string(self.a) or b'libarchive error').decode(errors='replace')
    def entries(self):
        try:
            while True:
                entry=C.c_void_p();rc=self.lib.archive_read_next_header(self.a,C.byref(entry))
                if rc==1:break
                if rc!=0:raise RuntimeError(self.error())
                yield self.lib.archive_entry_pathname(entry).decode('utf-8').replace('\\','/'),self.lib.archive_entry_size(entry)
        finally:self.lib.archive_read_free(self.a)
    def chunks(self):
        while True:
            n=self.lib.archive_read_data(self.a,self.buf,len(self.buf))
            if n<0:raise RuntimeError(self.error())
            if n==0:return
            yield self.buf.raw[:n]


def xjtu(raw,out,check):
    out.mkdir(parents=True,exist_ok=False)
    files=[raw/f'xjtu-part{i:02}'/f'XJTU-SY_Bearing_Datasets.part{i:02}.rar' for i in range(1,7)]
    for f in files:
        manifest=json.loads((f.parent/'source-manifest.json').read_text())
        if digest(f)!=manifest['archive']['sha256']:raise ValueError('RAR part hash changed')
    rr=RarReader(files);inventory=[];counts=defaultdict(list);features=defaultdict(list)
    # Pilot features only for bearing ordinal 1 in each condition, selected before reading.
    pilot={'Bearing1_1','Bearing2_1','Bearing3_1'}
    for name,size in rr.entries():
        check.check()
        if name.startswith('/') or '..' in Path(name).parts:raise ValueError('unsafe RAR member')
        match=re.search(r'(Bearing([123])_([1-5]))/(\d+)\.csv$',name,re.I)
        chosen=bool(match and match.group(1) in pilot)
        h=hashlib.sha256();payload=bytearray();n=0
        for chunk in rr.chunks():
            h.update(chunk);n+=len(chunk)
            if chosen:
                if len(payload)+len(chunk)>4*1024**2:raise ValueError('CSV pilot buffer cap')
                payload.extend(chunk)
        if n!=size:raise ValueError(f'RAR member length mismatch: {name}')
        inventory.append({'path':name,'bytes':n,'sha256':h.hexdigest()})
        if not match:continue
        bearing,condition,ordinal,index=match.groups();index=int(index);counts[bearing].append(index)
        if chosen:
            reader=csv.reader(io.StringIO(payload.decode('utf-8-sig')));header=next(reader)
            if len(header)!=2 or 'horizontal' not in header[0].lower() or 'vertical' not in header[1].lower():
                raise ValueError(f'XJTU axis header mismatch: {header}')
            axes=[[],[]]
            for row in reader:
                if len(row)!=2:raise ValueError('XJTU row width')
                a,b=map(float,row)
                if not math.isfinite(a) or not math.isfinite(b):raise ValueError('nonfinite vibration')
                axes[0].append(a);axes[1].append(b)
            if any(len(v)!=32768 for v in axes):raise ValueError('XJTU waveform sample count')
            vals=[]
            for v in axes:
                mean=math.fsum(v)/len(v);rms=math.sqrt(math.fsum(x*x for x in v)/len(v))
                std=math.sqrt(math.fsum((x-mean)**2 for x in v)/len(v))
                vals.extend([mean,rms,std,max(v)-min(v)])
            features[bearing].append({'sample_index':index,'feature_values':vals})
    expected={f'Bearing{c}_{b}' for c in range(1,4) for b in range(1,6)}
    if set(counts)!=expected:raise ValueError('not all 15 bearings present')
    for bearing,ids in counts.items():
        if sorted(ids)!=list(range(1,len(ids)+1)):raise ValueError('missing/duplicate waveform index')
    write(out/'member-inventory.json',inventory)
    for bearing,rows in features.items():
        with (out/(bearing+'-features.jsonl')).open('x') as f:
            for row in sorted(rows,key=lambda r:r['sample_index']):f.write(json.dumps(row,separators=(',',':'))+'\n')
        if len(rows)!=len(counts[bearing]):raise ValueError('partial pilot trajectory')
    write(out/'dataset.json',{'bearings':{b:len(v) for b,v in sorted(counts.items())},
          'sampling_hz_within_waveform':25600,'samples_per_waveform':32768,'waveform_duration_seconds':1.28,
          'waveform_interval_minutes':1,'waveforms_are_not_contiguous_raw_sampling':True,
          'pilot_features':sorted(pilot),'feature_order':['horizontal_mean','horizontal_rms','horizontal_std','horizontal_peak_to_peak',
          'vertical_mean','vertical_rms','vertical_std','vertical_peak_to_peak'],
          'feature_normalization':'none','remaining_life_or_total_length_in_features':False,
          'label_policy':'no fault type or RUL labels generated; total file counts are metadata only',
          'split_policy':{'unit':'complete bearing, never random waveform/window',
          'train_ordinals':[1,2,3],'validation_ordinals':[4],'test_ordinals':[5],
          'status':'proposed development split, not formal holdout; no training or evaluation'},
          'raw_parts':[str(f) for f in files]})
    return {'status':'prepared','rar_all_members_read_without_error':True,'members':len(inventory),
            'bearings':len(counts),'waveforms':sum(map(len,counts.values())),
            'pilot_features':{b:len(v) for b,v in features.items()},'model_runs':0}


def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('kind',choices=['metro','hydraulic','xjtu']);p.add_argument('--raw',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();raw,out=Path(a.raw),Path(a.output);check=MacCheckpoint(seconds=870);status='failed'
    if out.exists():raise FileExistsError('refuse existing output')
    try:
        result=globals()[a.kind](raw,out,check);result['resources']=check.check()
        write(out/'preparation-summary.json',result);status='complete';print(json.dumps(result))
    except BaseException:
        if out.exists():write(out/'preparation-failure.json',{'traceback':traceback.format_exc()})
        raise
    finally:
        if out.exists():close(out,status)


if __name__=='__main__':main()
