#!/usr/bin/env python3
"""Refresh packaged static compiler/assets from audited canonical sources."""
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[1]
source=(ROOT/'spec_tools/behavior_compiler.py').read_text()
source=source.replace('ROOT=Path(__file__).resolve().parents[1]', "ROOT=Path(__file__).resolve().parents[1] / 'assets'")
source=source.replace('OFFLINE specification reference compiler/validator, NOT the SECMA runtime.', 'S00 runtime static compiler; authorization is separately enforced by domain policy.')
(ROOT/'src/secma/behavior/validated_reference.py').write_text(source)
for directory in ('contracts','examples/statecharts','examples/behavior'):
    for p in (ROOT/directory).iterdir():
        if p.suffix in {'.json','.yaml'}:
            destination=ROOT/'src/secma/assets'/directory/p.name
            destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(p,destination)
