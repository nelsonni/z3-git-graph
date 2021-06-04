import argparse
from pysmt.shortcuts import Symbol, And, Not, get_model, is_sat
from typing import List, Tuple
from z3 import *
import gitgraph

parser = argparse.ArgumentParser()
parser.add_argument("root")
args = parser.parse_args()

graph = gitgraph.GitGraph(args.root).getData()

s = Solver()

def Compare(vector1: gitgraph.Vector, vector2: gitgraph.Vector):
	return vector1.commit.hexsha != vector2.commit.hexsha

def StartAndEnd(vector1: gitgraph.Vector, vector2: gitgraph.Vector):
	return Or(And(vector1.branching == True, vector2.merging == True), And(vector1.merging== True, vector2.branching == True))

def Contains(vector1: gitgraph.Vector, vector2: gitgraph.Vector, edges: List[Tuple[str, str]]):
    return Or([And(vector1 == x, vector2 == y) for x, y in edges])

def SameDirection(child: gitgraph.Vector, parent: gitgraph.Vector, edges: List[Tuple[str, str]]):
	return len([And(child == x, parent == y) for x, y in edges]) >= 2


vectorList = list(graph.vectors.values())
vectors = list(zip(graph.vectors, graph.vectors[1:] + graph.vectors[:1]))
formula = Or([And(Compare(vector1, vector2), StartAndEnd(vector1, vector2), SameDirection(vector1, vector2, graph.edges)) for vector1, vector2 in vectors])
s.add(formula)

# # Solve:
r = s.check()
print("Solver said: %s" % r)
model = s.model()
print(model)
if model:
    print(eval(formula))

# if r == sat:
#     m = s.model()
#     for d in m:
#         print(d, m[d])

