import argparse
from pysmt.shortcuts import Symbol, Or, And, GE, LT, Plus, Equals, Int, get_model
from pysmt.typing import INT
from gitgraph import GitGraph

parser = argparse.ArgumentParser()
parser.add_argument("root")
args = parser.parse_args()

graph = GitGraph(args.root)
graph.print()
domains = And([ Or(v.terminal, v.sequential) for v in graph.vertices ])
# result = [graph.vertices[i:i+2] for i in range(len(graph.vertices)-2+1)]
# print(result)
# problem = And([And(v.structural, u.structural) for v,u in   ])


# hello = [Symbol(s, INT) for s in "hello"]
# world = [Symbol(s, INT) for s in "world"]
# letters = set(hello+world)
# domains = And([And(GE(l, Int(1)),
#                    LT(l, Int(10))) for l in letters])

# sum_hello = Plus(hello) # n-ary operators can take lists
# sum_world = Plus(world) # as arguments
# problem = And(Equals(sum_hello, sum_world),
#               Equals(sum_hello, Int(25)))
# formula = And(domains, problem)

# print("Serialization of the formula:")
# print(formula)

# model = get_model(formula)
# if model:
#   print(model)
# else:
#   print("No solution found")

# import argparse
# from pysmt.shortcuts import Equals, Symbol, And, Not, GE, Int, get_model
# from pysmt.typing import INT
# from z3 import *
# from gitgraph import GitGraph, Vertex

# parser = argparse.ArgumentParser()
# parser.add_argument("root")
# args = parser.parse_args()

# graph = GitGraph(args.root).getData()

# def isTerminal(v: Vertex):
# 	return Bool(v.terminal)

# def isStructural(v: Vertex):
# 	return Equals(v.structural, True)

# def isBranching(v: Vertex):
# 	return Equals(v.branching, True)

# def isMerging(v: Vertex):
# 	return Equals(v.merging, True)

# def uniqCommitType(v: Vertex):
# 	return Or( And(isTerminal(v), Not(isStructural(v))), And(Not(isTerminal(v)), isStructural(v)) )

# validTypes = And([ isTerminal(v) for v in graph.vertices ])

# def branchThenMerge(u: Vertex, v: Vertex):
# 	return Implies(isBranching(u), isMerging(v))

# def multipleEdges(u: Vertex, v: Vertex):
# 	count = Symbol(len([Equals(child, v.commit.hexsha) for child in u.children]), INT)
# 	return GE(count, Int(2))

# validOrdering = Or([ branchThenMerge(u,v) for u,v in graph ])

# formula = validTypes

# # # Solve:
# model = get_model(formula)
# if model:
# 	print(model)
# 	print(eval(formula))
# else:
# 	print("No solution found")

# # if r == sat:
# #     m = s.model()
# #     for d in m:
# #         print(d, m[d])

