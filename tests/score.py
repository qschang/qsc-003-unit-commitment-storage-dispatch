#!/usr/bin/env python3
import argparse,json,xml.etree.ElementTree as ET
p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--junit',required=True);p.add_argument('--report-out',required=True);p.add_argument('--reward-out',required=True);a=p.parse_args()
cfg=json.load(open(a.config,encoding='utf-8')); root=ET.parse(a.junit).getroot(); cases=root.findall('.//testcase'); names=[f"{c.attrib.get('classname','')}::{c.attrib.get('name','')}" for c in cases]
gates=list(cfg.get('gate_tests',[])); expected=gates+list(cfg.get('tests',{})); ok=(len(cases)==len(expected) and set(names)==set(expected) and len(set(names))==len(names) and all(int(root.attrib.get(k,'0'))==0 for k in ('failures','errors','skipped')) and all(not c.findall('./failure') and not c.findall('./error') and not c.findall('./skipped') for c in cases))
score=1.0 if ok else 0.0
import os
os.chmod(a.reward_out,0o644)
json.dump({'score':score,'expected_tests':len(expected),'observed_tests':len(cases),'gate_tests':gates,'passed':ok},open(a.report_out,'w',encoding='utf-8'),sort_keys=True)
with open(a.reward_out,'w',encoding='utf-8') as f:f.write(f'{score:.3f}\n')
os.chmod(a.reward_out,0o444)
raise SystemExit(0 if ok else 1)
