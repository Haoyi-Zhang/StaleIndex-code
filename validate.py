#!/usr/bin/env python3
"""Run the documented offline checks in a fresh output directory, without TeX.

Reference results are read-only. The runner records actual exits and compares
scientific fields; it never substitutes a successful command for an equality
check. It uses one child command at a time and no third-party dependency.
"""
import argparse
import json
import os
from pathlib import Path
import re
import resource
import subprocess
import sys
import time
from bsci.evidence import strict_equal, compare_derived

class ValidationPaused(Exception):
    """A deliberate bounded checkpoint, not a successful validation."""


PILOT_OBSERVATIONS = {'cpu_seconds', 'wall_seconds', 'peak_rss_kib', 'projection'}


def save(path: Path, obj: object) -> None:
    path.write_text(json.dumps(obj, indent=2) + '\n')


def compare_pilot(reference: Path, candidate: Path) -> dict:
    expected, actual = (json.loads(p.read_text()) for p in (reference, candidate))
    left = {k: v for k, v in expected.items() if k not in PILOT_OBSERVATIONS}
    right = {k: v for k, v in actual.items() if k not in PILOT_OBSERVATIONS}
    if not strict_equal(left, right):
        raise ValueError(f'Pilot scientific fields differ: {reference.name}')
    return {'non_observational_fields_equal': True,
            'excluded_fields': sorted(PILOT_OBSERVATIONS),
            'candidate_observations': actual}


def compare_directory(reference: Path, candidate: Path) -> list[str]:
    expected = sorted(p.name for p in reference.iterdir() if p.is_file())
    actual = sorted(p.name for p in candidate.iterdir() if p.is_file())
    if actual != expected:
        raise ValueError(f'File coverage differs: {reference.name}')
    for name in expected:
        a, b = reference / name, candidate / name
        # Compare JSON values, not irrelevant serialization whitespace.
        equal = (strict_equal(json.loads(a.read_text()), json.loads(b.read_text()))
                 if a.suffix == '.json' else a.read_bytes() == b.read_bytes())
        if not equal:
            raise ValueError(f'Deterministic output differs: {reference.name}/{name}')
    return expected


def create_workspace(root: Path, requested: Path) -> Path:
    out = (requested if requested.is_absolute() else root / requested).resolve()
    # Refuse existing directories rather than overwrite evidence or source files.
    if out.exists():
        raise ValueError('Output directory already exists; choose a new --out path')
    protected = [root / name for name in ('bsci', 'tests', 'pilots', 'inputs',
                 'proofs', 'licenses')]
    protected += [root / 'results' / name for name in
                  ('campaign', 'derived', 'examples', 'epoch-audit')]
    if any(out == p.resolve() or p.resolve() in out.parents for p in protected):
        raise ValueError('Output directory must not be inside source or reference data')
    out.mkdir(parents=True, exist_ok=False)
    return out


def validate(root: Path, out: Path, *, resume=False, max_commands=None) -> dict:
    logs = out / 'logs'
    logs.mkdir(exist_ok=resume)
    previous = json.loads((out / 'commands.json').read_text()) if resume else {}
    commands = previous.get('commands', [])
    sessions = previous.get('completed_session_resources', [])
    cursor = 0
    newly_executed = 0
    started = time.perf_counter()
    own_start = time.process_time()
    child_start = resource.getrusage(resource.RUSAGE_CHILDREN)
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE='1',
                       OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')

    def rel(path: Path) -> str:
        return os.path.relpath(path, root)

    def command_record():
        return {'commands': commands, 'workers': 1,
                'completed_session_resources': sessions}

    def run(name: str, args: list[str], expected: int = 0) -> str:
        nonlocal cursor, newly_executed
        requested = ['python', *args]
        output = logs / (name + '.txt')
        if cursor < len(commands):
            record = commands[cursor]
            if (record['name'] != name or record['command'] != requested or
                    record['expected_exit'] != expected or not record['passed'] or
                    record['observed_exit'] != expected or not output.is_file()):
                raise ValueError('Checkpoint does not match this command sequence')
            cursor += 1
            return output.read_text()
        if max_commands is not None and newly_executed >= max_commands:
            raise ValidationPaused('Bounded command batch ended before validation completed')
        before = resource.getrusage(resource.RUSAGE_CHILDREN)
        wall = time.perf_counter()
        output = logs / (name + '.txt')
        try:
            with output.open('w') as stream:
                result = subprocess.run([sys.executable, *args], cwd=root,
                    env=environment, stdout=stream, stderr=subprocess.STDOUT,
                    timeout=1800, check=False)
            status = result.returncode
        except subprocess.TimeoutExpired:
            status = 'timeout'
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        record = {'name': name, 'command': ['python', *args],
                  'expected_exit': expected, 'observed_exit': status,
                  'passed': status == expected,
                  'cpu_seconds': after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime,
                  'wall_seconds': time.perf_counter() - wall,
                  'cumulative_peak_child_rss_kib': after.ru_maxrss}
        commands.append(record)
        cursor += 1
        newly_executed += 1
        save(out / 'commands.json', command_record())
        if status != expected:
            raise RuntimeError(f'{name}: exit {status}, expected {expected}; see logs/{name}.txt')
        print(f'{name}: expected exit {expected}', flush=True)
        return output.read_text()

    def cli(name, command, case, extra=(), expected=0):
        return run(name, ['-m', 'bsci', command, f'inputs/{case}.json', *extra], expected)

    try:
        text = run('unit-tests', ['-m', 'unittest', 'discover', '-s', 'tests', '-v'])
        count = re.search(r'Ran (\d+) tests?', text)
        if count is None:
            raise ValueError('Could not establish executed unit-test count')
        unit_count = int(count.group(1))
        for label, script in (('initial', 'initial'), ('compact', 'compact')):
            run('pilot-' + label, [f'pilots/{script}.py', '--out', rel(out / 'pilots' / (label + '.json'))])
        run('examples', ['examples.py', '--out', rel(out / 'examples')])
        run('full-campaign', ['reproduce.py', '--out', rel(out / 'campaign')])
        run('summarize-reproduced', ['-m', 'bsci.summarize', '--results', rel(out / 'campaign'),
                                    '--out', rel(out / 'reproduced-derived')])
        run('compare-campaign', ['check_reproduction.py', '--reference', 'results/campaign',
                                '--candidate', rel(out / 'campaign'), '--out', rel(out / 'reproduction-check.json')])
        run('epoch-audit', ['epoch_audit.py', '--out', rel(out / 'epoch-audit')])
        run('compare-epoch', ['check_epoch_audit.py', '--reference', 'results/epoch-audit',
                             '--candidate', rel(out / 'epoch-audit'), '--out', rel(out / 'epoch-reproduction-check.json')])
        run('single-family', ['-m', 'bsci.campaign', 'random', '--out', rel(out / 'single-family')])
        if (out / 'single-family/random.jsonl').read_bytes() != (root / 'results/campaign/random.jsonl').read_bytes():
            raise ValueError('Standalone random-family output differs')
        run('summarize-retained', ['-m', 'bsci.summarize', '--results', 'results/campaign',
                                  '--out', rel(out / 'retained-derived')])
        packets = out / 'cli'
        packets.mkdir(exist_ok=True)
        for case in ('case-001', 'case-002'):
            packet = rel(packets / (case + '.json'))
            cli('certify-' + case, 'certify', case, ['--out', packet])
            result = cli('verify-' + case, 'verify', case, ['--packet', packet])
            if json.loads(result) != {'valid': True}:
                raise ValueError('Expected a valid fixed-pattern verification')
        cli('replay-case-001', 'replay', 'case-001',
            ['--packet', rel(packets / 'case-001.json'), '--out', rel(packets / 'trace.json')])
        budget_packet = rel(packets / 'budget-one.json')
        cli('universal-one', 'universal', 'case-003', ['--k', '1', '--out', budget_packet])
        cli('verify-universal-one', 'verify-universal', 'case-003', ['--k', '1', '--packet', budget_packet])
        text = cli('reject-budget-mismatch', 'verify-universal', 'case-003',
                   ['--k', '2', '--packet', budget_packet], expected=1)
        if json.loads(text) != {'valid': False}:
            raise ValueError('Budget mismatch did not return invalid')
        cli('reject-missing-budget', 'verify-universal', 'case-003', ['--packet', budget_packet], expected=2)
        optional = packets / 'optional.json'
        save(optional, [[1, 2]])
        selected_packet = rel(packets / 'selected.json')
        cli('certify-selected', 'certify', 'case-003', ['--optional', rel(optional), '--out', selected_packet])
        cli('verify-selected', 'verify', 'case-003', ['--optional', rel(optional), '--packet', selected_packet])
        cli('reject-pattern-mismatch', 'verify', 'case-003', ['--packet', selected_packet], expected=1)
        # The Python rolling-family and explicit minimum paths from the README.
        from bsci.model import Instance
        from bsci.families import universal, verify_universal
        ins = Instance.from_dict(json.loads((root / 'inputs/case-003.json').read_text()))
        rule = {'kind': 'rolling', 'b': 1, 'W': 2}
        packet = universal(ins, rule)
        if not packet['safe'] or not verify_universal(ins, packet, expected_rule=rule):
            raise ValueError('Rolling-family Python example failed')
        for k in (1, 2):
            rule = {'kind': 'cardinality', 'k': k}
            packet = universal(ins, rule)
            if not verify_universal(ins, packet, verify_minimum=True, expected_rule=rule):
                raise ValueError('Minimum-count Python example failed')
        pilots = {name: compare_pilot(root / 'results' / reference,
                  out / 'pilots' / (name + '.json')) for name, reference in
                  (('initial', 'pilot-result.json'), ('compact', 'compact-pilot-result.json'))}
        examples = compare_directory(root / 'results/examples', out / 'examples')
        derived = compare_directory(root / 'results/derived', out / 'retained-derived')
        reproduced_derived = compare_derived(root / 'results/derived', out / 'reproduced-derived')
        children = resource.getrusage(resource.RUSAGE_CHILDREN)
        child_cpu = sum(x['cpu_seconds'] for x in commands)
        summary = {'all_checks_passed': True, 'commands': len(commands),
                   'unique_unit_tests': unit_count,
                   'unit_execution_note': 'The same suite also runs inside reproduce.py; not additional unique tests.',
                   'pilots': pilots, 'examples_equal': examples,
                   'retained_derived_files_equal': derived,
                   'reproduced_derived_scientific_comparison': reproduced_derived,
                   'campaign_deterministic_equal': True, 'epoch_scientific_equal': True,
                   'single_family_equal': True, 'python_rolling_and_minimum_examples_passed': True,
                   'child_command_cpu_seconds': child_cpu,
                   'runner_cpu_seconds': sum(x['runner_cpu_seconds'] for x in sessions) + time.process_time() - own_start,
                   'active_session_wall_seconds': sum(x['wall_seconds'] for x in sessions) + time.perf_counter() - started,
                   'peak_child_rss_kib': max(x['cumulative_peak_child_rss_kib'] for x in commands), 'workers': 1,
                   'resumed': bool(sessions),
                   'scope': 'Offline execution and exact record checks in a fresh output directory. '
                            'Not a proof assistant, deployment evaluation, or independent research review.'}
        if cursor != len(commands):
            raise ValueError('Checkpoint contains commands outside this sequence')
        save(out / 'summary.json', summary)
        return summary
    except ValidationPaused as exc:
        sessions.append({'runner_cpu_seconds': time.process_time() - own_start,
                         'wall_seconds': time.perf_counter() - started})
        save(out / 'commands.json', command_record())
        save(out / 'summary.json', {'all_checks_passed': False, 'status': 'incomplete',
                                   'completed_commands': len(commands),
                                   'next_action': 'Resume unchanged sources and inputs with --resume'})
        raise
    except (OSError, ValueError, RuntimeError) as exc:
        save(out / 'summary.json', {'all_checks_passed': False, 'error': str(exc),
                                   'completed_commands': len(commands)})
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=Path('results/validation-run'))
    parser.add_argument('--resume', action='store_true',
                        help='resume a checkpoint only while sources and inputs are unchanged')
    parser.add_argument('--max-commands', type=int,
                        help='pause with exit 3 after this many new commands')
    args = parser.parse_args()
    if not __debug__:
        parser.exit(2, 'Validation requires assertions enabled; do not use -O or PYTHONOPTIMIZE.\n')
    if args.max_commands is not None and args.max_commands < 1:
        parser.error('--max-commands must be positive')
    root = Path(__file__).resolve().parent
    try:
        if args.resume:
            out = (args.out if args.out.is_absolute() else root / args.out).resolve()
            if not (out / 'commands.json').is_file():
                raise ValueError('No validation checkpoint exists at --out')
        else:
            out = create_workspace(root, args.out)
        result = validate(root, out, resume=args.resume, max_commands=args.max_commands)
        print(json.dumps(result, indent=2))
    except ValidationPaused as exc:
        parser.exit(3, f'Validation incomplete: {exc}. Resume with --resume.\n')
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(1, f'Validation failed: {exc}\n')


if __name__ == '__main__':
    main()
