"""Compatibility entry point; the portable skill owns the implementation."""
import importlib.util
from pathlib import Path
import runpy

HELPER = Path(__file__).resolve().parent / 'skills/render-vertical-video/scripts/render_short.py'

if __name__ == '__main__':
    runpy.run_path(str(HELPER), run_name='__main__')
else:
    spec = importlib.util.spec_from_file_location('starter_helper', HELPER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    digest = module.digest
    local_asset = module.local_asset
    load = module.load
    fonts = module.fonts
    wrapped = module.wrapped
    frame = module.frame
    render = module.render
