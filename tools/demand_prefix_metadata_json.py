"""Bounded ASCII JSON path projection. Quantity subtrees never reach json.loads."""
import hashlib,json,re
MAX_BYTES=8*1024**2
NUMBER=re.compile(rb'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?')
INPUT={'schema':'leaf','key':'leaf','store':'leaf','origin':'leaf','past_dates':['leaf'],'past_available_at':['leaf'],'target_dates':['leaf'],'assumed_open_mask':['leaf'],'operating_status':'leaf','policy_ref':'leaf','past_values':None,'past_observed':None,'matched_mean28':None}
PIN={'bytes':'leaf','sha256':'leaf'}
TRANSFORM={'schema':'leaf','policy_ref':'leaf','availability_basis':'leaf','scale_period':{'start':'leaf','end':'leaf'},'closure_period':{'start':'leaf','end':'leaf'},'scale_usable_from':'leaf','closure_usable_from':'leaf','month_days':['leaf'],'scales':('map',None)}
STATE={k:None for k in ('counts','J','s','mu','weekday_counts','weekday_means','z_grid','z_rounding_error','levels','changes','a','b','V','r_raw','r_stored','r_grid_numerator','r_rounding_error','computed','reason','max_bits')}
STATE.update({'schema':'leaf','origin':'leaf','past_start':'leaf','past_end':'leaf','availability':'leaf','tau':'leaf','precision_bits_absolute':'leaf','rounding':'leaf','input_pin':PIN})
ENCODED={'key':'leaf','store':'leaf','origin':'leaf','history':{'schema':'leaf','origin':'leaf','records':[{'date':'leaf','available_at':'leaf','value':None}]},'old_features':None,'old_reasons':['leaf'],'baseline':None,'assumed_open_mask':['leaf'],'scale':None,'transform_usable_from':'leaf','encoded':{'state':('pin',STATE),'old_eligible':'leaf','features_exact':None,'retain_old_objective_and_risk_denominators':'leaf'}}
SPECS={'inputs':[('pin',INPUT)],'transforms':TRANSFORM,'encoded':('map',('pin',ENCODED))}

def raw_pin(raw):return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}

class ProjectionFailure(ValueError):pass

class Projector:
    def __init__(self,raw,checkpoint=lambda:None):
        if type(raw) is not bytes or len(raw)>MAX_BYTES or any(x>127 for x in raw):raise ProjectionFailure('bounded ASCII bytes required')
        self.raw=raw;self.i=0;self.tokens=0;self.checkpoint=checkpoint;self.decoded_scalars=0;self.skipped_values=0
    def white(self):
        while self.i<len(self.raw) and self.raw[self.i] in b' \t\r\n':self.i+=1
    def token(self):
        self.tokens+=1
        if self.tokens>1000000:raise ProjectionFailure('token limit')
        if self.tokens%256==0:self.checkpoint()
    def string(self):
        start=self.i;self.i+=1
        while self.i<len(self.raw):
            c=self.raw[self.i];self.i+=1
            if self.i-start>32768:raise ProjectionFailure('string limit')
            if c==34:return start,self.i
            if c<32:raise ProjectionFailure('string control')
            if c==92:
                if self.i>=len(self.raw):raise ProjectionFailure('truncated escape')
                e=self.raw[self.i];self.i+=1
                if e==117:
                    digits=self.raw[self.i:self.i+4]
                    if len(digits)!=4 or any(c not in b'0123456789abcdefABCDEF' for c in digits):raise ProjectionFailure('unicode escape')
                    self.i+=4
                elif e not in b'"\\/bfnrt':raise ProjectionFailure('escape')
        raise ProjectionFailure('unterminated string')
    def punct(self,value):
        self.white()
        if self.raw[self.i:self.i+1]!=value:raise ProjectionFailure('JSON punctuation')
        self.i+=1
    def scalar(self,decode):
        self.white();start=self.i
        if self.raw[self.i:self.i+1]==b'"':self.string()
        elif self.raw[self.i:self.i+1] in (b't',b'f',b'n'):
            lit=next((x for x in (b'true',b'false',b'null') if self.raw.startswith(x,self.i)),None)
            if lit is None:raise ProjectionFailure('literal')
            self.i+=len(lit)
        else:
            match=NUMBER.match(self.raw,self.i)
            if match is None:raise ProjectionFailure('number syntax')
            self.i=match.end()
            if self.i-start>2468:raise ProjectionFailure('number token limit')
            if decode and (self.i-start>10 or any(c in self.raw[start:self.i] for c in b'.eE')):raise ProjectionFailure('metadata integer only')
        if decode:self.decoded_scalars+=1;return json.loads(self.raw[start:self.i])
        return None
    def parse(self,spec,depth=0):
        if depth>64:raise ProjectionFailure('depth limit')
        self.white();start=self.i;self.token()
        if isinstance(spec,tuple) and spec[0]=='pin':
            value=self.parse(spec[1],depth+1)
            return {'metadata':value,'source_span':{'start':start,'end':self.i,'pin':raw_pin(self.raw[start:self.i])}}
        c=self.raw[self.i:self.i+1]
        if spec=='leaf':
            if c in (b'{',b'['):raise ProjectionFailure('metadata scalar required')
            return self.scalar(True)
        if c==b'{':
            if spec is not None and not isinstance(spec,dict) and not (isinstance(spec,tuple) and spec[0]=='map'):raise ProjectionFailure('object spec')
            self.i+=1;out={};seen=set();self.white()
            if self.raw[self.i:self.i+1]!=b'}':
                while True:
                    self.white()
                    if self.raw[self.i:self.i+1]!=b'"':raise ProjectionFailure('object key')
                    s,e=self.string();key=None if spec is None else json.loads(self.raw[s:e])
                    if spec is not None:
                        if key in seen:raise ProjectionFailure('duplicate metadata key')
                        seen.add(key)
                        if isinstance(spec,dict) and key not in spec:raise ProjectionFailure('unexpected metadata field')
                    self.punct(b':');child=None if spec is None else spec[key] if isinstance(spec,dict) else spec[1]
                    value=self.parse(child,depth+1)
                    if spec is not None:out[key]=value
                    self.white();sep=self.raw[self.i:self.i+1];self.i+=1
                    if sep==b'}':break
                    if sep!=b',':raise ProjectionFailure('object separator')
            else:self.i+=1
            if isinstance(spec,dict) and seen!=set(spec):raise ProjectionFailure('missing metadata field')
            if spec is None:self.skipped_values+=1;return None
            return out
        if c==b'[':
            if spec is not None and (type(spec) is not list or len(spec)!=1):raise ProjectionFailure('array spec')
            self.i+=1;out=[];self.white()
            if self.raw[self.i:self.i+1]!=b']':
                while True:
                    value=self.parse(None if spec is None else spec[0],depth+1)
                    if spec is not None:out.append(value)
                    self.white();sep=self.raw[self.i:self.i+1];self.i+=1
                    if sep==b']':break
                    if sep!=b',':raise ProjectionFailure('array separator')
            else:self.i+=1
            if spec is None:self.skipped_values+=1;return None
            return out
        if spec is not None:raise ProjectionFailure('structured metadata required')
        self.skipped_values+=1;return self.scalar(False)

def extract(raw,kind,checkpoint=lambda:None):
    p=Projector(raw,checkpoint);out=p.parse(SPECS[kind]);p.white()
    if p.i!=len(raw):raise ProjectionFailure('trailing JSON')
    checkpoint()
    return {'kind':kind,'file_pin':raw_pin(raw),'metadata':out,'decoded_metadata_scalars':p.decoded_scalars,'quantity_scalars_decoded':0,'tokens':p.tokens,'skipped_values':p.skipped_values}
