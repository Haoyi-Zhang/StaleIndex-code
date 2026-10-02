import copy,itertools,unittest
from bsci.model import Instance,Message
from bsci.certify import certify,endpoint_sets
from bsci.replay import verify,replay
from bsci.oracle import exhaustive,scalar
from bsci.families import universal,verify_universal,rolling_legal
from bsci.star import packing,phase_bounds,window
from bsci.flow import minimum_resets

class CertificateTests(unittest.TestCase):
    def setUp(self):
        self.safe=Instance(2,3,0,(Message(0,1,0,1,2),),((1,3),))
        self.early=Instance(2,2,0,(Message(0,1,0,1,2),),((1,2),),((1,2),))
    def test_latest_is_not_worst(self):
        self.assertEqual(replay(self.early,(),[1])['answer'],-1)
        self.assertEqual(replay(self.early,(),[2])['answer'],0)
        self.assertFalse(certify(self.early)['safe'])
    def test_positive(self):
        p=certify(self.safe);self.assertTrue(p['safe']);self.assertTrue(verify(self.safe,p))
    def test_missing_query_prerequisite(self):
        p=certify(self.safe);p['steps']=p['steps'][1:];self.assertFalse(verify(self.safe,p))
    def test_wrong_timestamp(self):
        p=certify(self.safe);p['steps'][-1][1]=3;self.assertFalse(verify(self.safe,p))
    def test_wrong_message(self):
        p=certify(self.safe);p['steps'][-1]=[0,0,'msg',17];self.assertFalse(verify(self.safe,p))
    def test_memory_across_reset(self):
        p=dict(safe=True,optional=[],steps=[[1,2,'query'],[1,1,'mem',2],[0,0,'msg',0]])
        self.assertFalse(verify(self.early,p))
    def test_negative_outside_interval(self):
        p=certify(self.early);p['arrivals']=[0];self.assertFalse(verify(self.early,p))
    def test_negative_false_failure(self):
        p=certify(self.early);p['arrivals']=[2];self.assertFalse(verify(self.early,p))
    def test_illegal_optional(self):
        p=certify(self.early);p['optional']=[[1,1]];self.assertFalse(verify(self.early,p))
    def test_generator_optional(self):
        ins=Instance(2,2,0,self.early.messages,((1,2),),(),((1,2),))
        p=certify(ins,(r for r in ins.candidates));self.assertEqual(p['optional'],[[1,2]]);self.assertTrue(verify(ins,p))
    def test_duplicate_derivation(self):
        p=certify(self.safe);p['steps'].append(p['steps'][0]);self.assertFalse(verify(self.safe,p))
    def test_malformed(self):
        for p in ({},None,[],{'safe':'yes','optional':[]},{'safe':True,'optional':[],'steps':[None]},
                  {'safe':False,'optional':[],'arrivals':[True]}):
            self.assertFalse(verify(self.safe,p))
    def test_family_missing_coverage(self):
        ins=Instance(2,3,0,(Message(0,1,2,3,3),),((1,3),),(),((1,1),(1,2)))
        p=universal(ins,dict(kind='cardinality',k=1));self.assertTrue(verify_universal(ins,p))
        p['certificates'].pop();self.assertFalse(verify_universal(ins,p))
    def test_family_over_budget(self):
        ins=Instance(2,2,0,self.early.messages,((1,2),),(),((1,2),))
        p=universal(ins,dict(kind='cardinality',k=1));self.assertFalse(p['safe'])
        p['rule']['k']=0;self.assertFalse(verify_universal(ins,p))
    def test_minimum_not_implied_by_witness(self):
        ins=Instance(2,2,0,self.early.messages,((1,2),),(),((1,2),))
        p=universal(ins,dict(kind='cardinality',k=1));p['minimal_optional_count']=0
        self.assertTrue(verify_universal(ins,p));self.assertFalse(verify_universal(ins,p,True))
    def test_no_fresh_send(self):
        ins=Instance(2,3,2,self.safe.messages,((1,3),))
        self.assertFalse(certify(ins)['safe']);self.assertTrue(verify(ins,certify(ins)))
    def test_query_origin(self):
        ins=Instance(1,3,2,(),((0,3),));self.assertTrue(certify(ins)['safe'])
    def test_late_arrival_retained(self):
        ins=Instance(2,4,0,(Message(0,1,0,1,4),),((1,2),))
        self.assertFalse(certify(ins)['safe']);self.assertGreater(certify(ins)['arrivals'][0],2)
    def test_reset_then_arrival_then_send(self):
        ins=Instance(3,3,0,(Message(0,1,0,2,2),Message(1,2,2,3,3)),((2,3),),((1,2),))
        self.assertEqual(scalar(ins,(),[2,3]),0);self.assertTrue(certify(ins)['safe'])
    def test_packet_survives_sender_reset(self):
        ins=Instance(3,4,0,(Message(0,1,0,1,1),Message(1,2,1,4,4)),((2,4),),((1,2),))
        self.assertEqual(replay(ins,(),[1,4])['answer'],0)
    def test_rolling_boundaries(self):
        self.assertTrue(rolling_legal(((1,1),(2,4)),1,3));self.assertFalse(rolling_legal(((1,1),(2,3)),1,3))
        self.assertTrue(rolling_legal(((1,4),(2,4)),2,3));self.assertFalse(rolling_legal(((1,4),(2,4),(3,4)),2,3))
    def test_cut_rejects_intervals(self):
        with self.assertRaises(ValueError):minimum_resets(self.safe)
    def test_sparse_star_rejected(self):
        with self.assertRaises(ValueError):packing(self.safe,1,3)
    def test_star_example(self):
        self.assertEqual(phase_bounds(4,2,1,3,[0,0,0])['bound'],5)
        self.assertEqual(phase_bounds(4,2,1,3,[0,1,2])['bound'],4)
    def test_phase_boundary_small_oracle(self):
        for P,D,r,b,W in itertools.product((2,3),(1,2),(2,3),(1,2),(2,3)):
            phases=list(range(r));phases=[p%P for p in phases]
            for B,q in itertools.product(range(1,5),range(P)):
                ins=window(P,D,phases,B,q);out=packing(ins,b,W)
                ages=sorted(D+(q-D-p)%P for p in phases)
                expected=any(a<=B and a<=1+W*(j//b) for j,a in enumerate(ages))
                self.assertEqual(out['safe'],expected)
    def test_joint_query_quantifier(self):
        messages=(Message(0,1,0,1,2),Message(1,2,1,3,3),Message(1,3,2,3,3))
        joint=Instance(4,3,0,messages,((2,3),(3,3)),((1,2),))
        self.assertTrue(certify(joint)['safe'])
        for query in joint.queries:
            individual=Instance(4,3,0,messages,(query,),joint.mandatory)
            packet=certify(individual)
            self.assertFalse(packet['safe']);self.assertTrue(verify(individual,packet))
    def test_star_mandatory_rejected(self):
        ins=Instance(2,3,0,(Message(0,1,0,1,2),),((1,3),),((1,2),),((1,1),(1,3)))
        with self.assertRaises(ValueError):packing(ins,1,2)
    def test_replica_count_necessary_not_sufficient(self):
        # The necessary bound is derived from the largest available rank threshold.
        for r,P,D,b,W in itertools.product(range(1,5),range(1,5),range(1,5),(1,2),(1,2,3)):
            if D>1+W*((r-1)//b):
                for phases in itertools.combinations_with_replacement(range(P),r):
                    self.assertIsNone(phase_bounds(P,D,b,W,phases)['bound'])
        # Passing the count condition does not make every phase choice finite.
        self.assertIsNone(phase_bounds(3,2,1,1,[0,0])['bound'])
    def test_invalid_instances(self):
        for m in (Message(0,1,1,1,2),Message(0,0,0,1,2),Message(0,1,0,True,2)):
            with self.assertRaises(ValueError):Instance(2,3,0,(m,),((1,3),))
        with self.assertRaises(ValueError):Instance(2,3,0,(),((1,3),),((1,2),),((1,2),))

if __name__=='__main__':unittest.main()
