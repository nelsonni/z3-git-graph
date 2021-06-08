import argparse
from gitgraph import GitGraph
from pysmt.shortcuts import Not, Symbol, Or, And, GE, LT, Plus, Equals, Int, get_model, is_sat, Bool
from pysmt.typing import INT

parser = argparse.ArgumentParser()
parser.add_argument("root")
args = parser.parse_args()

graph = GitGraph(args.root)

domain = And([Or(Bool(v.terminal), Bool(v.structural)) for v in graph.vertices.values()])

pruned_graph = And([Not(Bool(v.sequential)) for v in graph.vertices.values()])

def branchThenMerge(u, v):
    return And(Bool(u.branching), Bool(v.merging))

def sameDirection(u, v):
    edges = len([Bool(True) for [x,y] in graph.edges if u==y and v==x ])
    return GE(Int(edges), Int(2))

def pruned(u, v):
    return And(Not(Bool(u.sequential)), Not(Bool(v.sequential)))

maintenance_cycle = Or([And(pruned(u,v), branchThenMerge(u,v), sameDirection(u,v)) for (u, v) in graph])
[print(a,b) for (a,b) in graph]
# print("-----------------------")
# [print(e) for e in graph.edges]

# TODO: Fix reconnecting the edges during pruning

# a = Symbol("a", INT)
# domain = And(GE(a, Int(32)), LT(a, Int(35)))

# phi = And(a, Not(a))

# print(phi)
# string_repr = str(phi)
# seriailized_strinf = phi.serialize()

# check = is_sat(phi)
# print(check)

# b = Symbol("b")
# psi = Or(phi, b)

print(is_sat(domain))
print(is_sat(pruned_graph))
print(is_sat(maintenance_cycle))
# m = get_model(domain)
# print(m)

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

