from Graph import GitGraph
from Vertex import Vertex
import argparse
from pysmt.shortcuts import Not, Or, And, GE, Int, get_model, is_sat, Bool

parser = argparse.ArgumentParser()
parser.add_argument("root")
args = parser.parse_args()

graph = GitGraph(args.root)

def branchThenMerge(u: Vertex, v: Vertex):
    return And(Bool(u.branching), Bool(v.merging))

def sameDirection(u: Vertex, v: Vertex):
    edges = len([Bool(True) for x in u.children if x==v.commit.hexsha ])
    return GE(Int(edges), Int(2))

def pruned(u, v):
    return And(Not(Bool(u.sequential)), Not(Bool(v.sequential)))

problem = Or([And(pruned(u,v), branchThenMerge(u,v), sameDirection(u,v)) for (u, v) in graph.stream()])
print(is_sat(problem))