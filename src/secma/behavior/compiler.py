"""Compile bundled control policy without activating a commitment workflow."""
from pathlib import Path
from .validated_reference import ROOT, load_yaml, validate_behavior


def compile_profile(path: str | None = None) -> dict:
    source = Path(path) if path else ROOT / 'examples/behavior/executive-secretary.yaml'
    if source.stat().st_size > 65536:
        raise ValueError('Profile exceeds the S00 size limit')
    receipt, prompt = validate_behavior(load_yaml(source))
    return {'receipt': receipt, 'prompt': prompt,
            'activation': 'NOT_ACTIVATED', 'runtime_scope': 'S00_FIXTURE_ONLY'}
