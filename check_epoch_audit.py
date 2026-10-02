"""Compare every scientific epoch-audit record; resources are not equality targets."""
import argparse
import json
from pathlib import Path
from bsci.evidence import strict_equal


def compare(reference: Path, candidate: Path) -> dict:
    counts = {}
    for name in ('cases.jsonl', 'summary.json'):
        a = (reference / name).read_text()
        b = (candidate / name).read_text()
        if name.endswith('.jsonl'):
            expected = [json.loads(line) for line in a.splitlines() if line.strip()]
            actual = [json.loads(line) for line in b.splitlines() if line.strip()]
            counts['case_records_compared'] = len(expected)
        else:
            expected, actual = json.loads(a), json.loads(b)
        if not strict_equal(expected, actual):
            raise ValueError(f'Scientific audit mismatch in {name}')
    return {**counts, 'summary_compared': True, 'all_scientific_fields_equal': True,
            'excluded': 'Separate measured resource observations only'}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, default=Path('results/epoch-audit'))
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--out', type=Path, default=Path('results/epoch-reproduction-check.json'))
    args = parser.parse_args()
    try:
        result = compare(args.reference, args.candidate)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2))
    except (OSError, ValueError) as exc:
        parser.exit(1, f'Epoch audit comparison failed: {exc}\n')


if __name__ == '__main__':
    main()
