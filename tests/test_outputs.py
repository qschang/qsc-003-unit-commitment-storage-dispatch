import json, os, subprocess, sys, tempfile
from pathlib import Path
from pathlib import Path
import re
import pytest

@pytest.fixture(autouse=True)
def emit_case_id(request):
    m=re.search(r'CASE-QSC003-[A-Z0-9-]+', request.function.__doc__ or '')
    if m: print(m.group(0))
APP=os.environ.get('APP','/app/dispatch.py')
def assert_no_side_effects(extras):
    """Rejected inputs publish no temporary, report, ledger, summary, or checkpoint artifacts."""
    forbidden={'report','ledger','summary','checkpoint'}
    assert all(not any(word in name.lower() for word in forbidden) for name in extras)
def base():
 return {'horizon_hours':3,'periods':[{'demand_MWh':5,'ambient_C':8,'electricity_price':100},{'demand_MWh':2,'ambient_C':15,'electricity_price':50},{'demand_MWh':6,'ambient_C':5,'electricity_price':120}], 'boiler':{'max_heat_MW':4,'min_heat_MW':0,'efficiency':0.8,'fuel_price':40},'heat_pump':{'max_heat_MW':3,'min_ambient_C':7,'cop_base':2.5,'cop_slope':0.05},'thermal_store':{'capacity_MWh':4,'initial_MWh':1,'max_charge_MW':2,'max_discharge_MW':2,'charge_efficiency':0.9,'discharge_efficiency':0.8,'terminal_MWh':0}}
def run(d,existing=False):
 with tempfile.TemporaryDirectory() as td:
  p=Path(td); i=p/'i.json'; o=p/'o.json'; i.write_text(json.dumps(d)); sentinel=b'keep'
  if existing:o.write_bytes(sentinel)
  r=subprocess.run([sys.executable,APP,str(i),str(o)],capture_output=True,timeout=20)
  extras=sorted(x.name for x in p.iterdir() if x.name not in {'i.json','o.json'})
  return r,o.read_bytes() if o.exists() else None,sentinel,extras
def good(d=None):
 r,b,_,_=run(base() if d is None else d); assert r.returncode==0,r.stderr.decode(); return json.loads(b)
def test_cop_uses_ambient_slope():
 """CASE-QSC003-HP-01: ambient COP equation."""
 d=base(); d['horizon_hours']=1; d['periods']=[{'demand_MWh':2,'ambient_C':10,'electricity_price':100}]; x=good(d); assert x['schedule'][0]['heat_pump_heat_MW']==pytest.approx(2)
def test_heat_pump_is_unavailable_below_threshold():
 """CASE-QSC003-HP-02: ambient threshold."""
 d=base(); d['horizon_hours']=1; d['periods']=[{'demand_MWh':2,'ambient_C':0,'electricity_price':100}]; x=good(d); assert x['schedule'][0]['heat_pump_heat_MW']==0
def test_boiler_heat_respects_limit():
 """CASE-QSC003-BOILER-01: boiler capacity."""
 d=base(); d['horizon_hours']=1; d['periods']=[{'demand_MWh':9,'ambient_C':0,'electricity_price':100}]; x=good(d); assert x['schedule'][0]['boiler_heat_MW']<=4
def test_store_recursion_uses_efficiency():
 """CASE-QSC003-STORE-01: storage efficiency recursion."""
 x=good(); s=1.0; q=x['schedule'][0]['storage']; s+=q['charge_MW']*.9-q['discharge_MW']/.8; assert q['state_MWh']==pytest.approx(s,abs=1e-9)
def test_store_capacity_and_terminal_state():
 """CASE-QSC003-STORE-02: storage capacity and terminal state."""
 x=good(); assert all(0<=q['storage']['state_MWh']<=4+1e-9 for q in x['schedule']); assert x['summary']['final_storage_MWh']>=0
def test_heat_balance_is_closed():
 """CASE-QSC003-BAL-01: heat balance."""
 x=good(); d=base()
 for p,q in zip(d['periods'],x['schedule']): assert q['boiler_heat_MW']+q['heat_pump_heat_MW']+q['storage']['discharge_MW']+q['unmet_heat_MWh']-q['storage']['charge_MW']==pytest.approx(p['demand_MWh'],abs=1e-9)
def test_cost_contains_penalty():
 """CASE-QSC003-COST-01: unmet heat penalty."""
 d=base(); d['horizon_hours']=1; d['periods']=[{'demand_MWh':20,'ambient_C':0,'electricity_price':100}]; x=good(d); assert x['summary']['total_cost']>=20000*x['summary']['total_unmet_heat_MWh']
def test_output_shape_is_exact():
 """CASE-QSC003-SCHEMA-01: output schema."""
 x=good(); assert list(x)==['schedule','summary']; assert list(x['schedule'][0])==['boiler_heat_MW','heat_pump_heat_MW','storage','unmet_heat_MWh','operating_cost']
def test_repeat_is_byte_identical():
 """CASE-QSC003-IO-01: deterministic bytes."""
 r1,b1,_,_=run(base()); r2,b2,_,_=run(base()); assert r1.returncode==r2.returncode==0 and b1==b2
def test_duplicate_key_is_rejected():
 """CASE-QSC003-REJECT-01: duplicate keys."""
 with tempfile.TemporaryDirectory() as td:
  p=Path(td); i=p/'i.json'; o=p/'o.json'; i.write_text('{"horizon_hours":1,"horizon_hours":1}'); r=subprocess.run([sys.executable,APP,str(i),str(o)],capture_output=True); assert r.returncode!=0 and not o.exists()
  assert sorted(x.name for x in p.iterdir())==['i.json']; assert_no_side_effects([])
def test_invalid_input_preserves_sentinel():
 """CASE-QSC003-REJECT-02: sentinel preservation."""
 d=base(); d['periods'][1]['demand_MWh']=-1; r,b,s,tmp=run(d,True); assert r.returncode!=0 and b==s and tmp==[]; assert_no_side_effects(tmp)
def test_late_invalid_record_is_atomic():
 """CASE-QSC003-REJECT-03: late validation."""
 d=base(); d['periods'][2]['ambient_C']=float('nan'); r,b,_,tmp=run(d); assert r.returncode!=0 and b is None and tmp==[]; assert_no_side_effects(tmp)
def test_missing_parent_is_rejected():
 """CASE-QSC003-IO-02: missing parent."""
 with tempfile.TemporaryDirectory() as td:
  p=Path(td); i=p/'i.json'; i.write_text(json.dumps(base())); o=p/'missing'/'o.json'; r=subprocess.run([sys.executable,APP,str(i),str(o)],capture_output=True); assert r.returncode!=0 and not o.exists()
  assert sorted(x.name for x in p.iterdir())==['i.json']; assert_no_side_effects([])
def test_efficiency_boundary_one_is_valid():
 """CASE-QSC003-BOUND-01: inclusive efficiency boundary."""
 d=base(); d['thermal_store']['charge_efficiency']=1.0; d['thermal_store']['discharge_efficiency']=1.0; assert 'summary' in good(d)
def test_boolean_numeric_is_rejected():
 """CASE-QSC003-REJECT-04: booleans are not numbers."""
 d=base(); d['boiler']['efficiency']=True; r,b,_,extras=run(d); assert r.returncode!=0 and b is None and extras==[]; assert_no_side_effects(extras)

def test_zero_efficiency_is_rejected():
    """CASE-QSC003-REJECT-05: zero store efficiency is invalid."""
    d=base(); d['thermal_store']['charge_efficiency']=0; r,b,_,extras=run(d); assert r.returncode!=0 and b is None and extras==[]; assert_no_side_effects(extras)

def test_zero_initial_inventory_is_valid():
    """CASE-QSC003-BOUND-02: zero initial inventory is inclusive."""
    d=base(); d['thermal_store']['initial_MWh']=0; assert 'summary' in good(d)

def test_initial_inventory_zero_boundary_is_accepted():
    """CASE-QSC003-BOUND-03: zero lower bound is accepted."""
    d=base(); d['thermal_store'].update({'capacity_MWh':1,'initial_MWh':0,'terminal_MWh':0}); assert 'schedule' in good(d)
def test_capacity_upper_boundary_is_accepted():
    """CASE-QSC003-BOUND-04: capacity upper bound is accepted."""
    d=base(); d['thermal_store'].update({'capacity_MWh':1,'initial_MWh':1,'terminal_MWh':1,'max_charge_MW':0,'max_discharge_MW':0}); d['periods']=[{'demand_MWh':0,'ambient_C':10,'electricity_price':0}]*3; assert good(d)['summary']['final_storage_MWh']==pytest.approx(1)

def test_heat_pump_threshold_is_inclusive():
    """CASE-QSC003-HP-03: threshold equality enables heat pump."""
    d=base(); d['horizon_hours']=1; d['periods']=[{'demand_MWh':1,'ambient_C':7,'electricity_price':100}]; assert good(d)['schedule'][0]['heat_pump_heat_MW']==pytest.approx(1)
def test_efficiency_upper_boundary_is_inclusive():
    """CASE-QSC003-BOUND-05: efficiency one is accepted."""
    d=base(); d['thermal_store']['charge_efficiency']=1.0; d['thermal_store']['discharge_efficiency']=1.0; assert 'schedule' in good(d)

def test_cross_period_inventory_obligation_is_carried_forward():
    """CASE-QSC003-STATE-01: inventory from one period constrains the next."""
    d=base(); d['horizon_hours']=2
    d['periods']=[{'demand_MWh':0,'ambient_C':20,'electricity_price':1}, {'demand_MWh':3,'ambient_C':0,'electricity_price':1}]
    d['boiler'].update({'max_heat_MW':0,'min_heat_MW':0}); d['heat_pump']['max_heat_MW']=0
    d['thermal_store'].update({'capacity_MWh':3,'initial_MWh':3,'max_discharge_MW':3,'terminal_MWh':0})
    x=good(d); assert x['schedule'][1]['storage']['discharge_MW']>0

def test_cost_uses_cop_and_electricity_price_independently():
    """CASE-QSC003-COST-02: COP changes electrical heat cost."""
    d=base(); d['horizon_hours']=1; d['periods']=[{'demand_MWh':2,'ambient_C':10,'electricity_price':100}]
    x=good(d); expected=2/(2.5+0.05*10)*100
    assert x['schedule'][0]['operating_cost']==pytest.approx(expected)

def test_state_transition_accept_reject_accept_isolated():
    """CASE-QSC003-STATE-02: accepted, rejected, then accepted runs are isolated."""
    first=good(); bad=base(); bad['periods'][0]['demand_MWh']=-1
    rejected, _, _, extras=run(bad); assert rejected.returncode != 0; assert_no_side_effects(extras)
    second=good(); assert json.dumps(first,separators=(',',':')) == json.dumps(second,separators=(',',':'))
