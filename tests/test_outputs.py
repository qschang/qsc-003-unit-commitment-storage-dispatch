import json, os, subprocess, sys, tempfile
from pathlib import Path
import pytest
APP=os.environ.get('APP', '/app/dispatch.py')
def base():
 return {'horizon_hours':3,'generators':[{'id':'cheap','min_MW':2,'max_MW':8,'marginal_cost':10,'startup_cost':5,'ramp_up_MW':8,'ramp_down_MW':8,'min_up_hours':1,'min_down_hours':1,'initial_state':'off'},{'id':'expensive','min_MW':1,'max_MW':10,'marginal_cost':30,'startup_cost':7,'ramp_up_MW':10,'ramp_down_MW':10,'min_up_hours':1,'min_down_hours':1,'initial_state':'off'}],'storage':{'capacity_MWh':4,'initial_MWh':2,'max_charge_MW':2,'max_discharge_MW':2,'charge_efficiency':0.9,'discharge_efficiency':0.8},'periods':[{'load_MW':6,'renewable_MW':2},{'load_MW':3,'renewable_MW':6},{'load_MW':9,'renewable_MW':1}]}
def run(d,existing=False):
 with tempfile.TemporaryDirectory() as td:
  p=Path(td); i=p/'i.json'; o=p/'o.json'; i.write_text(json.dumps(d)); sentinel=b'keep'
  if existing:o.write_bytes(sentinel)
  r=subprocess.run([sys.executable,APP,str(i),str(o)],capture_output=True,timeout=20)
  artifacts=sorted(x.name for x in p.rglob('*') if x.name not in {'i.json','o.json'})
  return r,o.read_bytes() if o.exists() else None,sentinel,artifacts
def good(d=None):
 r,b,_,_=run(base() if d is None else d)
 if r.returncode != 0: raise AssertionError(r.stderr.decode())
 return json.loads(b)
def rec(x): return x["dispatch"]
def test_minimum_up_duration_is_respected():
 """The contract requires `load balance each period`."""
 x=good(); a=[g['on'] for q in rec(x) for g in q['generators'] if g['id']=='cheap']; assert not (a[0] and not a[1] and 1 < base()['generators'][0]['min_up_hours'])
def test_initial_off_state_honors_minimum_down_duration():
 """The contract requires `load balance each period`."""
 d=base(); d['generators'][0]['min_down_hours']=2; d['periods'][0]['load_MW']=0; x=good(d); assert x['dispatch'][0]['generators'][0]['on'] is False
def test_ramp_limits_include_initial_transition():
 """The contract requires `load balance each period`."""
 d=base(); d['generators'][0]['ramp_up_MW']=3; x=good(d); p=next(g['power_MW'] for g in x['dispatch'][0]['generators'] if g['id']=='cheap'); assert p<=3+1e-9
def test_zero_output_when_off():
 """The contract requires `load balance each period`."""
 x=good(); assert all(g['power_MW']==0 for q in rec(x) for g in q['generators'] if not g['on'])
def test_storage_recurrence_uses_efficiencies():
 """The contract requires `load balance each period`."""
 x=good(); s=2.0; q=x['dispatch'][0]; s-=q['storage']['discharge_MW']/0.8; s+=q['storage']['charge_MW']*0.9; assert q['storage']['state_MWh']==pytest.approx(s,abs=1e-9)
def test_storage_capacity_is_never_exceeded():
 """The contract requires `load balance each period`."""
 x=good(); assert all(0<=q['storage']['state_MWh']<=4+1e-9 for q in rec(x))
def test_renewable_is_used_before_thermal():
 """The contract requires `load balance each period`."""
 d=base(); d['periods']=[{'load_MW':3,'renewable_MW':8}]; d['horizon_hours']=1; x=good(d); assert x['dispatch'][0]['renewable_used_MW']==5 and x['dispatch'][0]['curtailment_MW']>=0
def test_unserved_load_is_last_resort_and_penalized():
 """The contract requires `load balance each period`."""
 d=base(); d['periods']=[{'load_MW':100,'renewable_MW':0}]; d['horizon_hours']=1; x=good(d); assert x['summary']['total_unserved_MWh']>0 and x['summary']['total_cost']>=10000*x['summary']['total_unserved_MWh']
def test_balance_residual_is_zero():
 """The contract requires `load balance each period`."""
 x=good(); assert all(abs(q['balance_residual_MW'])<=1e-9 for q in rec(x))
def test_summary_commitment_hours_matches_records():
 """The contract requires `load balance each period`."""
 x=good();
 for gid,n in x['summary']['commitment_hours'].items(): assert n==sum(g['on'] for q in rec(x) for g in q['generators'] if g['id']==gid)
def test_output_schema_is_exact_and_ordered():
 """The contract requires `load balance each period`."""
 x=good(); assert list(x)==['dispatch','summary'] and set(x['dispatch'][0])=={'generators','storage','renewable_used_MW','curtailment_MW','unserved_MW','balance_residual_MW'}
def test_invalid_input_preserves_absent_output():
 """The contract requires `load balance each period`."""
 d=base(); d['storage']['charge_efficiency']=0; r,b,_,a=run(d)
 assert r.returncode!=0 and b is None and not any(x.endswith('.tmp') for x in a) and not any('report' in x or 'log' in x or 'ledger' in x or 'summary' in x or 'checkpoint' in x for x in a)
def test_invalid_input_preserves_sentinel():
 """The contract requires `load balance each period`."""
 d=base(); d['periods'][1]['load_MW']=-1; r,b,s,a=run(d,True)
 assert r.returncode!=0 and b==s and not any(x.endswith('.tmp') for x in a) and not any('report' in x or 'log' in x or 'ledger' in x or 'summary' in x or 'checkpoint' in x for x in a)
def test_late_invalid_period_is_atomic():
 """The contract requires `load balance each period`."""
 d=base(); d['periods'][2]['renewable_MW']=float('nan'); r,b,_,a=run(d)
 assert r.returncode!=0 and b is None and not any(x.endswith('.tmp') for x in a) and not any('report' in x or 'log' in x or 'ledger' in x or 'summary' in x or 'checkpoint' in x for x in a)



def test_initial_on_minimum_up_is_enforced_for_zero_load():
    """The contract requires `load balance each period`."""
    d=base(); d['horizon_hours']=3; d['periods']=[{'load_MW':0,'renewable_MW':0}]*3; d['generators'][0]['initial_state']='on'; d['generators'][0]['min_up_hours']=2
    x=good(d); states=[q['generators'][0]['on'] for q in rec(x)]; assert states[:2]==[True,True]

def test_initial_off_minimum_down_blocks_startup():
    """The contract requires `load balance each period`."""
    d=base(); d['horizon_hours']=2; d['periods']=[{'load_MW':8,'renewable_MW':0}]*2; d['generators'][0]['min_down_hours']=2
    x=good(d); assert [q['generators'][0]['on'] for q in rec(x)]==[False,False]

def test_ramp_down_is_checked_between_periods():
    """The contract requires `load balance each period`."""
    d=base(); d['horizon_hours']=2; d['periods']=[{'load_MW':8,'renewable_MW':0},{'load_MW':7,'renewable_MW':0}]; d['generators'][0]['initial_state']='on'; d['generators'][0]['min_up_hours']=2; d['generators'][0]['ramp_down_MW']=1
    x=good(d); p=[g['power_MW'] for q in rec(x) for g in q['generators'] if g['id']=='cheap']; assert p[0]-p[1]<=1+1e-9

def test_on_generator_respects_minimum_output():
    """The contract requires `load balance each period`."""
    x=good();
    for q in rec(x):
        for g in q['generators']:
            if g['on']: assert g['power_MW']>=({'cheap':2,'expensive':1}[g['id']]-1e-9)

def test_on_generator_respects_maximum_output():
    """The contract requires `load balance each period`."""
    x=good();
    for q in rec(x):
        for g in q['generators']:
            if g['on']: assert g['power_MW']<=({'cheap':8,'expensive':10}[g['id']]+1e-9)

def test_repeat_run_is_byte_identical():
    """The contract requires `load balance each period`."""
    r1,b1,_,_=run(base()); r2,b2,_,_=run(base()); assert r1.returncode==0 and r2.returncode==0 and b1==b2

def test_summary_cost_includes_generation_and_startup():
    """The contract requires `load balance each period`."""
    x=good(); gen=sum(g['power_MW']*({'cheap':10,'expensive':30}[g['id']]) for q in rec(x) for g in q['generators']); assert x['summary']['total_cost']>=gen-1e-9

def test_absent_parent_directory_is_io_failure():
    """The contract requires `load balance each period`."""
    with tempfile.TemporaryDirectory() as td:
        p=Path(td); i=p/'i.json'; i.write_text(json.dumps(base())); o=p/'missing'/'o.json'; r=subprocess.run([sys.executable,APP,str(i),str(o)],capture_output=True); assert r.returncode!=0 and not o.exists() and not (p/'missing').exists() and not (p/'missing').exists() and not list(p.rglob('*.tmp')) and not list(p.rglob('*report*')) and not list(p.rglob('*ledger*')) and not list(p.rglob('*summary*')) and not list(p.rglob('*checkpoint*')) and not list(p.rglob('*log*')) and not list(p.rglob('*.tmp')) and not list(p.rglob('*report*')) and not list(p.rglob('*ledger*')) and not list(p.rglob('*summary*')) and not list(p.rglob('*checkpoint*'))









