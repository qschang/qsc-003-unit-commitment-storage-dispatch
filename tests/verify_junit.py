#!/usr/bin/env python3
import sys,xml.etree.ElementTree as ET,json
root=ET.parse(sys.argv[1]).getroot(); cfg=json.load(open(sys.argv[2],encoding='utf-8')) if len(sys.argv)>2 else None
cases=root.findall('.//testcase'); names=[f"{c.attrib.get('classname','')}::{c.attrib.get('name','')}" for c in cases]
expected=list(cfg.get('tests',{})) if cfg else []
if len(cases)!=len(expected) or set(names)!=set(expected) or len(set(names))!=len(names): raise SystemExit('unexpected testcase identities')
for k in ('failures','errors','skipped','disabled'):
 if int(root.attrib.get(k,'0'))!=0: raise SystemExit('non-passing junit status')
for c in cases:
 if c.findall('./failure') or c.findall('./error') or c.findall('./skipped'): raise SystemExit('non-passing testcase')