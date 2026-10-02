"""Generate and check the three small, human-readable certificate cases."""
import argparse,json
from pathlib import Path
from bsci.model import Instance
from bsci.certify import certify
from bsci.replay import verify,replay
from bsci.families import universal,verify_universal

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',default='results/examples');args=parser.parse_args()
    root=Path(__file__).resolve().parent;out=Path(args.out)
    if not out.is_absolute():out=root/out
    out.mkdir(parents=True,exist_ok=True)
    def save(name,obj):(out/(name+'.json')).write_text(json.dumps(obj,indent=2)+'\n')
    cases={name:Instance.from_dict(json.loads((root/'inputs'/(name+'.json')).read_text())) for name in ('case-001','case-002','case-003')}
    for name,ins in cases.items():
        packet=certify(ins);assert verify(ins,packet,expected_optional=());save(name+'-certificate',packet)
        if not packet['safe']:save(name+'-trace',replay(ins,packet['optional'],packet['arrivals'],True))
    assert not certify(cases['case-001'])['safe']
    assert replay(cases['case-001'],(),[2])['answer']==0
    joint=cases['case-002'];assert certify(joint)['safe']
    short=dict(safe=True,optional=[],steps=[[2,3,'query'],[3,3,'query'],[1,1,'msg',1],[1,2,'msg',2],[0,0,'msg',0]])
    assert verify(joint,short,expected_optional=())
    save('case-002-short-derivation',short)
    for j,query in enumerate(joint.queries):
        ins=Instance(joint.n,joint.horizon,joint.cutoff,joint.messages,(query,),joint.mandatory,joint.candidates)
        packet=certify(ins);assert not packet['safe'] and verify(ins,packet,expected_optional=())
        save('case-002-individual-'+str(j),dict(instance=ins.to_dict(),certificate=packet))
    for k,label in ((1,'one'),(2,'two')):
        packet=universal(cases['case-003'],dict(kind='cardinality',k=k))
        assert verify_universal(cases['case-003'],packet,True,expected_rule=dict(kind='cardinality',k=k))
        assert packet['safe']==(k==1)
        if k==2:assert packet['minimal_optional_count']==2
        save('case-003-budget-'+label,packet)
    save('checks',dict(cases=3,individual_query_checks=2,aggregate_budget_checks=2,all_passed=True))
    print('Three exact cases and their certificates checked.')
if __name__=='__main__':main()
