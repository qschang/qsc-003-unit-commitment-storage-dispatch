#!/usr/bin/env python3
import sys, xml.etree.ElementTree as ET
EXPECTED = {
'test_minimum_up_duration_is_respected','test_initial_off_state_honors_minimum_down_duration','test_ramp_limits_include_initial_transition','test_zero_output_when_off','test_storage_recurrence_uses_efficiencies','test_storage_capacity_is_never_exceeded','test_renewable_is_used_before_thermal','test_unserved_load_is_last_resort_and_penalized','test_balance_residual_is_zero','test_summary_commitment_hours_matches_records','test_output_schema_is_exact_and_ordered','test_invalid_input_preserves_absent_output','test_invalid_input_preserves_sentinel','test_late_invalid_period_is_atomic'}
root=ET.parse(sys.argv[1]).getroot(); cases=root.findall('.//testcase'); names=[c.attrib.get('name','') for c in cases]
if len(cases)!=len(EXPECTED) or set(names)!=EXPECTED or len(set(names))!=len(names): raise SystemExit('unexpected testcase identities')
for k in ('failures','errors','skipped','disabled'):
 if int(root.attrib.get(k,'0'))!=0: raise SystemExit('non-passing junit status')
if len(cases)!=len(EXPECTED): raise SystemExit('wrong test count')
