"""python -m bsci {certify,verify,universal,replay} ..."""
import argparse,json,sys
from pathlib import Path
from .model import Instance
from .certify import certify
from .replay import verify,replay
from .families import universal,verify_universal

def main():
    p=argparse.ArgumentParser(description='Offline certificates for the declared volatile-index model')
    p.add_argument('command',choices=['certify','verify','universal','verify-universal','replay'])
    p.add_argument('instance',type=Path);p.add_argument('--packet',type=Path)
    p.add_argument('--optional',type=Path,help='JSON array of eligible [node,time] resets')
    p.add_argument('--k',type=int,help='required independent cardinality budget for universal commands')
    p.add_argument('--out',type=Path)
    a=p.parse_args()
    if a.command in ('universal','verify-universal') and a.k is None:
        p.error('--k is required for universal and verify-universal')
    try:
        ins=Instance.from_dict(json.loads(a.instance.read_text()))
        optional=json.loads(a.optional.read_text()) if a.optional else []
        packet=json.loads(a.packet.read_text()) if a.packet else None
        if a.command=='certify':out=certify(ins,optional)
        elif a.command=='universal':out=universal(ins,dict(kind='cardinality',k=a.k))
        elif a.command in ('verify','verify-universal'):
            if packet is None:p.error('--packet is required')
            good=(verify(ins,packet,expected_optional=optional) if a.command=='verify' else
                  verify_universal(ins,packet,expected_rule=dict(kind='cardinality',k=a.k)))
            out={'valid':good}
            if not good:print(json.dumps(out));return 1
        else:
            if packet is None:p.error('--packet is required')
            out=replay(ins,packet['optional'],packet['arrivals'],include_trace=True)
        text=json.dumps(out,indent=2)+'\n'
        if a.out:a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(text)
        else:print(text,end='')
        return 0
    except (OSError,ValueError,KeyError,TypeError) as e:
        print(f'error: {e}',file=sys.stderr);return 2

if __name__=='__main__':sys.exit(main())
