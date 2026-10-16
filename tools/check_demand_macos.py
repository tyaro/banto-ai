"""New Mac environment connection check using invented tensors and own state.

No training, original data/checkpoints, prior result replay, or official weights.
Run once into a fresh artifact root; failures are retained with their closure.
"""

import argparse
import hashlib
import json
import platform
from pathlib import Path
import subprocess
import sys
import sysconfig
import traceback

from macos_demand_runtime import MacCheckpoint

REPO = Path(__file__).resolve().parents[1]


def pin(path):
    return {'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def run(output):
    output = output.absolute()
    if output.parent != REPO / 'artifacts' or output.exists():
        raise ValueError('fresh root immediately under artifacts required')
    if output.parent.resolve() != output.parent:
        raise ValueError('artifact parent must use its canonical path')
    output.mkdir()
    status = 'failed'
    guard = MacCheckpoint(seconds=60)
    try:
        before = guard.check()
        if (platform.python_version() != '3.14.8' or platform.machine() != 'arm64'
                or platform.python_implementation() != 'CPython'
                or sysconfig.get_config_var('Py_GIL_DISABLED')):
            raise RuntimeError('CPython 3.14.8 normal build / Mac arm64 required')
        import torch
        if torch.__version__ != '2.14.0':
            raise RuntimeError('Torch 2.14.0 Mac build required')
        torch.set_num_threads(1)
        torch.manual_seed(20261014)
        sys.path.insert(0, str(REPO / 'models/mini-transformer'))
        from demand_statistical_feature_model import StatisticalFeatureMean
        after_import = guard.check()
        model = StatisticalFeatureMean().cpu().float().eval()
        # One invented self-series, 56-day context / 14-day horizon / 60 calendars.
        values = torch.ones((1, 56), device='cpu', dtype=torch.float32)
        observed = torch.ones((1, 56), device='cpu', dtype=torch.bool)
        past = torch.zeros((1, 56, 60), dtype=torch.float32)
        future = torch.zeros((1, 14, 60), dtype=torch.float32)
        stats = torch.tensor([[1.0, 0.0]], dtype=torch.float32)
        baseline = torch.ones((1, 14), dtype=torch.float32)
        scale = torch.ones((1,), dtype=torch.float32)
        residual = torch.zeros((1, 8), dtype=torch.float32)
        with torch.inference_mode():
            daily, total = model(values, observed, past, future, stats, baseline, scale, residual)
        if (daily.shape != (1, 14) or total.shape != (1,) or daily.device.type != 'cpu'
                or daily.dtype != torch.float32 or not torch.equal(daily, baseline)
                or not torch.equal(total, daily.sum(1))):
            raise RuntimeError('invented model connection contract failed')
        after_forward = guard.check()
        state_path = output / 'invented-state.pt'
        with state_path.open('xb') as stream:
            torch.save(model.state_dict(), stream)
        if state_path.stat().st_size > 32 * 1024**2:
            raise RuntimeError('state exceeds single-file budget')
        loaded = torch.load(state_path, map_location='cpu', weights_only=True)
        if set(loaded) != set(model.state_dict()) or not all(
                torch.equal(value, loaded[key]) for key, value in model.state_dict().items()):
            raise RuntimeError('own state roundtrip differs')
        fresh = StatisticalFeatureMean().cpu().float().eval()
        fresh.load_state_dict(loaded, strict=True)
        final = guard.check()
        names = ('tools/check_demand_macos.py', 'tools/macos_demand_runtime.py',
                 'models/mini-transformer/demand_statistical_feature_model.py',
                 'models/mini-transformer/demand_calendar_model.py')
        report = {'status': 'environment_connection_passed',
                  'repository_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip(),
                  'python': sys.version, 'executable': sys.executable,
                  'macos': platform.mac_ver()[0], 'architecture': platform.machine(),
                  'torch': torch.__version__, 'torch_git_version': torch.version.git_version,
                  'torch_build': torch.__config__.show(), 'device': 'cpu', 'dtype': 'float32',
                  'mps_used': False, 'model': 'StatisticalFeatureMean',
                  'parameter_count': sum(p.numel() for p in model.parameters()),
                  'invented_input_shapes': {'values': [1, 56], 'past_calendar': [1, 56, 60],
                                            'future_calendar': [1, 14, 60], 'statistics': [1, 8]},
                  'own_state_roundtrip': True, 'state': pin(state_path),
                  'resources': {'before': before, 'after_import': after_import,
                                'after_forward': after_forward, 'final': final},
                  'source_pins': {name: pin(REPO / name) for name in names},
                  'scope': {'training': False, 'original_data_read': False, 'original_state_read': False,
                            'original_evaluation_replayed': False, 'official_timesfm_weights': False,
                            'windows_native_acceptance': False, 'formal_permission': False,
                            'research_performance_evaluated': False}}
        with (output / 'report.json').open('x') as stream:
            json.dump(report, stream, indent=2, allow_nan=False)
            stream.write('\n')
        status = 'complete'
        return report
    except BaseException:
        with (output / 'failure.txt').open('x') as stream:
            traceback.print_exc(file=stream)
        raise
    finally:
        files = {p.name: pin(p) for p in output.iterdir()}
        with (output / 'root-closed.json').open('x') as stream:
            json.dump({'status': status, 'files': files, 'immutable': True,
                       'formal_permission': False}, stream, indent=2)
            stream.write('\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    report = run(parser.parse_args().output)
    print(json.dumps({'status': report['status'], 'own_state_roundtrip': report['own_state_roundtrip'],
                      'device': report['device'], 'formal_permission': False}))
