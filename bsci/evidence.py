"""Type-preserving comparisons for retained scientific evidence, not fingerprints."""
import csv
import json
from pathlib import Path


def strict_equal(left, right):
    """JSON equality without Python's True == 1 == 1.0 type aliases."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(strict_equal(left[k], right[k]) for k in left)
    if isinstance(left, (list, tuple)):
        return len(left) == len(right) and all(strict_equal(a, b) for a, b in zip(left, right))
    return left == right


SCALING_OBSERVATIONS = frozenset(
    f'{metric}_{suffix}' for metric in ('producer_cpu', 'verifier_cpu')
    for suffix in ('median_ms', 'min_ms', 'max_ms', 'error_minus', 'error_plus'))


def compare_derived(reference: Path, candidate: Path):
    """Check every derived scientific field while leaving timings observational."""
    reference, candidate = Path(reference), Path(candidate)
    expected = sorted(p.name for p in reference.iterdir() if p.is_file())
    actual = sorted(p.name for p in candidate.iterdir() if p.is_file())
    if expected != actual:
        raise ValueError('Derived file coverage differs')
    checked = []
    for name in expected:
        a, b = reference / name, candidate / name
        if name == 'summary.json':
            left, right = (json.loads(path.read_text()) for path in (a, b))
            # Resource totals are measured anew, not scientific equality targets.
            left = {k: v for k, v in left.items() if k != 'resources'}
            right = {k: v for k, v in right.items() if k != 'resources'}
            equal = strict_equal(left, right)
        elif name in ('scaling.csv', 'scaling-events.csv', 'scaling-time.csv'):
            def read(path):
                with path.open(newline='') as stream:
                    reader = csv.DictReader(stream)
                    fields = reader.fieldnames
                    rows = [{k: v for k, v in row.items() if k not in SCALING_OBSERVATIONS}
                            for row in reader]
                    return fields, rows
            equal = strict_equal(list(read(a)), list(read(b)))
        else:
            equal = a.read_bytes() == b.read_bytes()
        if not equal:
            raise ValueError(f'Derived scientific output differs: {name}')
        checked.append(name)
    return {'files': checked, 'all_scientific_fields_equal': True,
            'excluded_summary_fields': ['resources'],
            'excluded_scaling_columns': sorted(SCALING_OBSERVATIONS)}
