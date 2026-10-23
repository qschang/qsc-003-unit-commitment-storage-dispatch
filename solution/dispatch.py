#!/usr/bin/env python3
import json, math, os, sys
PENALTY=20000.0
def fail(m): raise ValueError(m)
def number(v): return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v)
def require(o, keys, label):
    if not isinstance(o,dict) or set(o)!=set(keys): fail(label+' schema')
def validate_period(p):
    keys=['demand_MWh','ambient_C','electricity_price']; require(p,keys,'period')
    if not all(number(p[k]) for k in keys): fail('period types')
    if p['demand_MWh']<0 or p['electricity_price']<0: fail('period range')
def validate_boiler(b):
    keys=['max_heat_MW','min_heat_MW','efficiency','fuel_price']; require(b,keys,'boiler')
    if not all(number(b[k]) for k in keys): fail('boiler types')
    if b['min_heat_MW']<0 or b['max_heat_MW']<b['min_heat_MW'] or not 0<b['efficiency']<=1 or b['fuel_price']<0: fail('boiler range')
def validate_pump(q):
    keys=['max_heat_MW','min_ambient_C','cop_base','cop_slope']; require(q,keys,'heat pump')
    if not all(number(q[k]) for k in keys): fail('heat pump types')
    if q['max_heat_MW']<0 or q['cop_base']<=0 or q['cop_slope']<0: fail('heat pump range')
def validate_store(s):
    keys=['capacity_MWh','initial_MWh','max_charge_MW','max_discharge_MW','charge_efficiency','discharge_efficiency','terminal_MWh']; require(s,keys,'store')
    if not all(number(s[k]) for k in keys): fail('store types')
    if s['capacity_MWh']<0 or s['max_charge_MW']<0 or s['max_discharge_MW']<0: fail('store range')
    if not 0<=s['initial_MWh']<=s['capacity_MWh'] or not 0<=s['terminal_MWh']<=s['capacity_MWh']: fail('inventory range')
    if not 0<s['charge_efficiency']<=1 or not 0<s['discharge_efficiency']<=1: fail('store efficiency')
def validate(d):
    require(d,['horizon_hours','periods','boiler','heat_pump','thermal_store'],'input')
    h=d['horizon_hours']
    if not isinstance(h,int) or isinstance(h,bool) or not 1<=h<=48 or not isinstance(d['periods'],list) or len(d['periods'])!=h: fail('horizon')
    for p in d['periods']: validate_period(p)
    validate_boiler(d['boiler']); validate_pump(d['heat_pump']); validate_store(d['thermal_store'])
def available_pump_heat(period, pump):
    if period['ambient_C'] < pump['min_ambient_C']:
        return 0.0
    return min(pump['max_heat_MW'], period['demand_MWh'])
def boiler_heat_for(period, pump_heat, boiler):
    heat = min(boiler['max_heat_MW'], period['demand_MWh'] - pump_heat)
    return boiler['min_heat_MW'] if 0 < heat < boiler['min_heat_MW'] else heat
def withdraw_from_store(state, requested, store):
    amount = min(store['max_discharge_MW'], state * store['discharge_efficiency'], max(0.0, requested))
    return state - amount / store['discharge_efficiency'], amount
def put_into_store(state, excess, store):
    if excess <= 0: return state, 0.0
    headroom = max(0.0, (store['capacity_MWh'] - state) / store['charge_efficiency'])
    amount = min(store['max_charge_MW'], headroom, excess)
    return state + amount * store['charge_efficiency'], amount
def operating_cost(boiler_heat, pump_heat, unmet, cop, period, boiler):
    fuel = boiler_heat / boiler['efficiency'] * boiler['fuel_price']
    electricity = pump_heat / cop * period['electricity_price']
    return fuel + electricity + unmet * PENALTY
def period_step(p,b,q,s,state):
    demand=p['demand_MWh']; cop=q['cop_base']+q['cop_slope']*p['ambient_C']
    if cop<=0: fail('cop')
    hp=available_pump_heat(p,q)
    boiler=boiler_heat_for(p,hp,b)
    remaining=demand-hp-boiler
    state,discharge=withdraw_from_store(state,remaining,s); remaining-=discharge
    state,charge=put_into_store(state,-remaining,s); remaining=max(0.0,remaining-charge)
    unmet=remaining; cost=operating_cost(boiler,hp,unmet,cop,p,b)
    return state,{'boiler_heat_MW':boiler,'heat_pump_heat_MW':hp,'storage':{'charge_MW':charge,'discharge_MW':discharge,'state_MWh':state},'unmet_heat_MWh':unmet,'operating_cost':cost}
def solve(d):
    validate(d); b,q,s=d['boiler'],d['heat_pump'],d['thermal_store']; state=s['initial_MWh']; rows=[]; total=0.0
    for p in d['periods']:
        state,row=period_step(p,b,q,s,state); rows.append(row); total+=row['operating_cost']
    if state<s['terminal_MWh']-1e-9: fail('terminal')
    return {'schedule':rows,'summary':{'total_cost':total,'total_unmet_heat_MWh':sum(r['unmet_heat_MWh'] for r in rows),'final_storage_MWh':state}}
def pairs(items):
    out={}
    for k,v in items:
        if k in out: fail('duplicate key')
        out[k]=v
    return out
def publish(path,value):
    parent=os.path.dirname(path)
    if parent and not os.path.isdir(parent): fail('parent')
    tmp=path+'.tmp'
    try:
        with open(tmp,'w',encoding='utf-8') as f: json.dump(value,f,ensure_ascii=False,separators=(',',':')); f.write('\n')
        os.replace(tmp,path)
    except Exception:
        try: os.unlink(tmp)
        except OSError: pass
        raise
def main():
    if len(sys.argv)!=3:return 2
    try:
        with open(sys.argv[1],encoding='utf-8') as f: data=json.load(f,object_pairs_hook=pairs)
        publish(sys.argv[2],solve(data)); return 0
    except Exception as e: print(str(e),file=sys.stderr); return 1
if __name__=='__main__': sys.exit(main())
