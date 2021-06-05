import argparse
from pysmt.shortcuts import Equals, Symbol, And, Not, GE, Int, get_model
from pysmt.typing import INT
from z3 import *
from gitgraph import GitGraph, Vertex

parser = argparse.ArgumentParser()
parser.add_argument("root")
args = parser.parse_args()

graph = GitGraph(args.root).getData()

def isTerminal(v: Vertex):
	return Bool(v.terminal)

def isStructural(v: Vertex):
	return Equals(v.structural, True)

def isBranching(v: Vertex):
	return Equals(v.branching, True)

def isMerging(v: Vertex):
	return Equals(v.merging, True)

def uniqCommitType(v: Vertex):
	return Or( And(isTerminal(v), Not(isStructural(v))), And(Not(isTerminal(v)), isStructural(v)) )

validTypes = And([ isTerminal(v) for v in graph.vertices ])

def branchThenMerge(u: Vertex, v: Vertex):
	return Implies(isBranching(u), isMerging(v))

def multipleEdges(u: Vertex, v: Vertex):
	count = Symbol(len([Equals(child, v.commit.hexsha) for child in u.children]), INT)
	return GE(count, Int(2))

validOrdering = Or([ branchThenMerge(u,v) for u,v in graph ])

formula = validTypes

# # Solve:
model = get_model(formula)
if model:
	print(model)
	print(eval(formula))
else:
	print("No solution found")

# if r == sat:
#     m = s.model()
#     for d in m:
#         print(d, m[d])

