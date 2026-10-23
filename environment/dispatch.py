#!/usr/bin/env python3
import json, math, os, sys
PENALTY=20000.0
def bad(m): raise ValueError(m)
def num(x): return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x)
def validate(d):
 if not isinstance(d,dict) or set(d)!={'horizon_hours','periods','boiler','heat_pump','thermal_store'}: bad('schema')
 h=d['horizon_hours']
 if not isinstance(h,int) or isinstance(h,bool) or h<1 or h>48 or not isinstance(d['periods'],list) or len(d['periods'])!=h: bad('horizon')
 for p in d['periods']:
  if not isinstance(p,dict) or set(p)!={'demand_MWh','ambient_C','electricity_price'} or not all(num(p[k]) for k in p): bad('period')
  if p['demand_MWh']<0 or p['electricity_price']<0: bad('period range')
 b=d['boiler']; req={'max_heat_MW','min_heat_MW','efficiency','fuel_price'}
 if not isinstance(b,dict) or set(b)!=req or not all(num(b[k]) for k in req): bad('boiler')
 if b['min_heat_MW']<0 or b['max_heat_MW']<b['min_heat_MW'] or not (0<b['efficiency']<=1) or b['fuel_price']<0: bad('boiler range')
 q=d['heat_pump']; req={'max_heat_MW','min_ambient_C','cop_base','cop_slope'}
 if not isinstance(q,dict) or set(q)!=req or not all(num(q[k]) for k in req): bad('heat pump')
 if q['max_heat_MW']<0 or q['cop_base']<=0 or q['cop_slope']<0: bad('heat pump range')
 s=d['thermal_store']; req={'capacity_MWh','initial_MWh','max_charge_MW','max_discharge_MW','charge_efficiency','discharge_efficiency','terminal_MWh'}
 if not isinstance(s,dict) or set(s)!=req or not all(num(s[k]) for k in req): bad('store')
 if s['capacity_MWh']<0 or not (0<=s['initial_MWh']<=s['capacity_MWh']) or not (0<=s['terminal_MWh']<=s['capacity_MWh']) or s['max_charge_MW']<0 or s['max_discharge_MW']<0 or not (0<s['charge_efficiency']<=1) or not (0<s['discharge_efficiency']<=1): bad('store range')
def solve(d):
 validate(d); b=d['boiler']; q=d['heat_pump']; s=d['thermal_store']; state=s['initial_MWh']; out=[]; total=0.0
 for p in d['periods']:
  demand=p['demand_MWh']; cop=q['cop_base']+q['cop_slope']*p['ambient_C']
  if cop<=0: bad('cop')
  hp=min(q['max_heat_MW'], demand) if p['ambient_C']>=q['min_ambient_C'] else 0.0
  rem=demand-hp; boiler=0.0
  if rem>0:
   boiler=min(b['max_heat_MW'], rem); rem-=boiler
   if boiler>0 and boiler<b['min_heat_MW']: boiler=b['min_heat_MW']; rem=demand-hp-boiler
  discharge=min(s['max_discharge_MW'], state*s['discharge_efficiency'], max(0.0,rem)); state-=discharge/s['discharge_efficiency']; rem-=discharge
  charge=0.0
  if rem<0:
   charge=min(s['max_charge_MW'], max(0.0,(s['capacity_MWh']-state)/s['charge_efficiency']), -rem); state+=charge*s['charge_efficiency']; rem=0.0
  unmet=max(0.0,rem); cost=boiler/b['efficiency']*b['fuel_price']+(hp/cop)*p['electricity_price']+unmet*PENALTY; total+=cost
  out.append({'boiler_heat_MW':boiler,'heat_pump_heat_MW':hp,'storage':{'charge_MW':charge,'discharge_MW':discharge,'state_MWh':state},'unmet_heat_MWh':unmet,'operating_cost':cost})
 if state<s['terminal_MWh']-1e-9: bad('terminal')
 return {'schedule':out,'summary':{'total_cost':total,'total_unmet_heat_MWh':sum(x['unmet_heat_MWh'] for x in out),'final_storage_MWh':state}}
def pairs(ps):
 d={}
 for k,v in ps:
  if k in d: bad('duplicate key')
  d[k]=v
 return d
def main():
 if len(sys.argv)!=3:return 2
 try:
  with open(sys.argv[1],encoding='utf-8') as f:d=json.load(f,object_pairs_hook=pairs)
  r=solve(d); out=sys.argv[2]; parent=os.path.dirname(out)
  if parent and not os.path.isdir(parent): raise OSError('parent')
  tmp=out+'.tmp'
  with open(tmp,'w',encoding='utf-8') as f: json.dump(r,f,ensure_ascii=False,separators=(',',':')); f.write('\n')
  os.replace(tmp,out); return 0
 except Exception as e:
  try: os.unlink(sys.argv[2]+'.tmp')
  except OSError: pass
  print(str(e),file=sys.stderr); return 1
if __name__=='__main__':sys.exit(main())
