"""Independent exact checks for the manuscript's finite counts and model consequences.

The checks do not verify the historical origins or physical yarrow probabilities.
"""
from fractions import Fraction as F
from itertools import product
from math import comb, perm

assert comb(78,10)==1258315963905
assert perm(78,10)==4566176969818464000
assert perm(78,10)*2**10==4675765217094107136000

def check(weights):
    # Each line outcome supplies (primary bit, resulting bit, probability).
    line=[(0,1,weights[0]),(1,1,weights[1]),(0,0,weights[2]),(1,0,weights[3])]
    primary=[F(0) for _ in range(64)]
    resulting=[F(0) for _ in range(64)]
    joint={}
    for outcomes in product(line,repeat=6):
        a=sum(o[0]<<i for i,o in enumerate(outcomes))
        b=sum(o[1]<<i for i,o in enumerate(outcomes))
        p=F(1)
        for o in outcomes:p*=o[2]
        primary[a]+=p;resulting[b]+=p
        assert (a,b) not in joint
        joint[a,b]=p
    assert len(joint)==4096
    assert sum(joint.values())==1
    assert set(primary)=={F(1,64)}
    return primary,resulting,joint

_,res,joint=check([F(1,16),F(5,16),F(7,16),F(3,16)])
assert res[0]==F(5,8)**6 and res[63]==F(3,8)**6
assert len(set(res))>1
assert F(1,16)/F(1,2)==F(1,8)
assert F(3,16)/F(1,2)==F(3,8)
for x in range(64):
    for y in range(64):
        conditional=F(1)
        for i in range(6):
            flip=F(3,8) if x>>i&1 else F(1,8)
            conditional*=flip if (x^y)>>i&1 else 1-flip
        assert joint[x,y]/F(1,64)==conditional
_,res,_=check([F(1,8),F(3,8),F(3,8),F(1,8)])
assert set(res)=={F(1,64)}
print('Exact card counts and all 4096 transition outcomes checked under each stated model.')
