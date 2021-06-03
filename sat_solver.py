import argparse
from pysmt.shortcuts import Symbol, And, Not, is_sat
from z3 import *
import gitgraph

parser = argparse.ArgumentParser()
parser.add_argument("root")
args = parser.parse_args()

graph = gitgraph.GitGraph(args.root)


s = Solver()

def Compare(vector1, vector2):
	return vector1.commit.hexsha != vector2.commit.hexsha

def StartAndEnd(vector1, vector2):
	return Or(And(vector1.branching == True, vector2.merging == True), And(vector1.merging== True, vector2.branching == True))

def Contains(vector1, vector2, edges):
    return Or([And(vector1 == x, vector2 == y) for x, y in vectors])

def SameDirection(child, parent, edges):
	return len([And(child == x, parent == y) for x, y in edges]) >= 2

vectors = list(graph.vectors.values())
s.add(Or([And(Compare(vector1, vector2)) for vector1, vector2 in list(zip(vectors, vectors[1:] + vectors[:1]))]))



# Solve:
r = s.check()
# if r == sat:
#     m = s.model()
#     for x in range(2):
#         print ("%s -> %s" % (x, m.evaluate(Select(mapping, x))))
# else:
print ("Solver said: %s" % r)

# varA = Symbol("A")
# varB = Symbol("B")
# f = And(varA, Not(varB))

# print(f)
# print(is_sat(f))

# g = f.substitute({varB: varA})
# print(g)
# print(is_sat(g))

