import argparse
from unicodedata import numeric
from tqdm import tqdm # for progressbar
from git import Repo
from git.objects.commit import Commit
from git.types import PathLike
from typing import Dict, List, Tuple, Union
from enum import Enum

class CommitType (Enum):
    TERMINAL = 1
    SEQUENTIAL = 2
    STRUCTURAL = 3

class Vector():

    commit: Commit = {}
    parents: List[str] = []
    children: List[str] = []
    processed = False
    branching = False
    merging = False
    types: CommitType

    def __init__(self, commit: Commit):
        self.commit = commit
        self.parents = []
        self.children = []

    def __repr__(self):
        return 'Vector {0}: commit: {{ hexsha: {1}, parents: {2} }}, parents: {3}, children: {4}, processed: {5}'.format(
            self.commit.hexsha, self.commit.hexsha, self.commit.parents, 
            self.parents, self.children, self.processed)
    
    def __str__(self):
        return 'Vector {0}: commit: {{ hexsha: {1}, parents: {2} }}, parents: {3}, children: {4}, processed: {5}'.format(
            self.commit.hexsha, self.commit.hexsha, self.commit.parents, 
            self.parents, self.children, self.processed)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.commit.hexsha == other.commit.hexsha
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)
class GitGraph():

    repo = {}
    vectors: Dict[str, Vector] = dict()                     # all commits
    edges: List[Tuple[str, str]] = []                       # all edges

    def __init__(self, root: PathLike):
        self.repo = Repo(root)

    def __addEdge__(self, start: str, end: str):
        candidate = [start, end]
        existing = list(filter(lambda e: candidate == e, self.edges))
        if len(existing) == 0:                              # no duplicate directed edges
            self.edges.append(candidate)

    def __addVector__(self, commit: Commit) -> bool:
        if self.vectors.get(commit.hexsha) is None:         # no duplicate commits
            self.vectors.update({commit.hexsha: Vector(commit)})

    def __addParent__(self, parent: str, child: Commit):
        self.__addVector__(self.repo.commit(parent)) # guarantees parent vector exists
        self.vectors.get(parent.hexsha).children.append(child.hexsha)
        self.__addEdge__(child.hexsha, parent.hexsha)
    
    def __parseParents__(self, child: Commit):
        if self.vectors.get(child.hexsha).processed is False:
            self.vectors.get(child.hexsha).processed = True
            for parent in child.parents:
                self.vectors.get(child.hexsha).parents.append(parent.hexsha)
                self.__addParent__(parent, child)

    def getData(self) -> Dict[str, Union[List[Vector], List[Tuple[str, str]]]]:
        return { "vectors": list(self.vectors.values()), "edges": List[Tuple[str, str]] }

    def parse(self):
        branches = filter(lambda ref: ref not in self.repo.tags, self.repo.refs)
        progress = tqdm(list(branches))
        for branch in progress:
            progress.set_description('{0}'.format(branch))
            for commit in self.repo.iter_commits(branch):
                self.__addVector__(commit)                  # only add none duplicate vectors
                self.__parseParents__(commit)               # only add none duplicate parent vectors and edges
    
    def assign(self):
        terminals = list(filter(lambda vector: len(vector.parents) == 0 or len(vector.children) == 0, self.vectors.values()))
        sequentials = list(filter(lambda vector: len(vector.parents) == 1 and len(vector.children) == 1, self.vectors.values()))
        structurals = list(filter(lambda vector: (vector not in terminals) and (len(vector.parents) + len(vector.children)) > 2, self.vectors.values()))
        branching = list (filter (lambda vector: (len(vector.children) > 1) and (len(vector.parents) >= 1), self.vectors.values()))
        merging = list (filter (lambda vector: (len(vector.children) >= 1) and (len(vector.parents) > 1), self.vectors.values()))

        vectors = list (self.vectors.values())
        for vector in vectors:
            if (vector in terminals):
                vector.types = CommitType.TERMINAL
            if (vector in sequentials):
                vector.types = CommitType.SEQUENTIAL
            if (vector in structurals):
                vector.types = CommitType.STRUCTURAL
            if (vector in branching):
                vector.branching = True
            if (vector in merging):
                vector.merging = True

    def prune(self):
        sequentials = tqdm(list(filter(lambda vector: len(vector.parents) == 1 and len(vector.children) == 1, self.vectors.values())))
        for sequential in sequentials:
            sequentials.set_description('{0}'.format(sequential.commit.hexsha))

            # handle the parent vector
            parent = self.vectors[sequential.parents[0]]
            parentEdges = list(filter(lambda edge: [sequential.commit.hexsha, sequential.parents[0]] == edge, self.edges))
            for edge in parentEdges:
                self.edges.remove(edge)

            # handle the child vector
            child = self.vectors.get(sequential.children[0])
            childEdges = list(filter(lambda edge: [sequential.children[0], sequential.commit.hexsha] == edge, self.edges))
            for edge in childEdges:
                self.edges.remove(edge)

            # add edge between child and parent, bypassing the commit
            if child is not None and parent is not None:
                self.__addEdge__(child.commit.hexsha, parent.commit.hexsha)

            # remove the sequential vector
            self.vectors.pop(sequential.commit.hexsha)

    def print(self):
        print('Vectors: {0}, Edges: {1}'.format(len(self.vectors), len(self.edges)))
        terminals = list(filter(lambda vector: len(vector.parents) == 0 or len(vector.children) == 0, self.vectors.values()))
        sequentials = list(filter(lambda vector: len(vector.parents) == 1 and len(vector.children) == 1, self.vectors.values()))
        structurals = list(filter(lambda vector: (vector not in terminals) and (len(vector.parents) + len(vector.children)) > 2, self.vectors.values()))
        print('  Terminals: {0}'.format(len(terminals)))
        print('  Sequentials: {0}'.format(len(sequentials)))
        print('  Structurals: {0}'.format(len(structurals)))

parser = argparse.ArgumentParser()
parser.add_argument("root")
args = parser.parse_args()

graph = GitGraph(args.root)
graph.parse()
graph.prune()
graph.assign()