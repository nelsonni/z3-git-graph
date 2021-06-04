import argparse
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

class Vertex():

    commit: Commit = {}
    parents: List[str] = []
    children: List[str] = []
    processed = False
    branching = False
    merging = False
    commitType: CommitType

    def __init__(self, commit: Commit):
        self.commit = commit
        self.parents = []
        self.children = []

    def __repr__(self):
        return 'Vertex {0}: commit: {{ hexsha: {1}, parents: {2} }}, parents: {3}, children: {4}, processed: {5}'.format(
            self.commit.hexsha, self.commit.hexsha, self.commit.parents, 
            self.parents, self.children, self.processed)
    
    def __str__(self):
        return 'Vertex {0}: commit: {{ hexsha: {1}, parents: {2} }}, parents: {3}, children: {4}, processed: {5}'.format(
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
    vertices: Dict[str, Vertex] = dict()                    # all commits
    edges: List[Tuple[str, str]] = []                       # all edges

    def __init__(self, root: PathLike):
        self.repo = Repo(root)

    def __addEdge__(self, start: str, end: str):
        candidate = [start, end]
        existing = list(filter(lambda e: candidate == e, self.edges))
        if len(existing) == 0:                              # no duplicate directed edges
            self.edges.append(candidate)

    def __addVector__(self, commit: Commit) -> bool:
        if self.vertices.get(commit.hexsha) is None:        # no duplicate commits
            self.vertices.update({commit.hexsha: Vertex(commit)})

    def __addParent__(self, parent: str, child: Commit):
        self.__addVector__(self.repo.commit(parent))        # guarantee parent vector exists
        self.vertices.get(parent.hexsha).children.append(child.hexsha)
        self.__addEdge__(child.hexsha, parent.hexsha)
    
    def __parseParents__(self, child: Commit):
        if self.vertices.get(child.hexsha).processed is False:
            self.vertices.get(child.hexsha).processed = True
            for parent in child.parents:
                self.vertices.get(child.hexsha).parents.append(parent.hexsha)
                self.__addParent__(parent, child)

    def getData(self) -> Dict[str, Union[List[Vertex], List[Tuple[str, str]]]]:
        return { "vertices": list(self.vertices.values()), "edges": self.edges }

    def parse(self):
        branches = filter(lambda ref: ref not in self.repo.tags, self.repo.refs)
        progress = tqdm(list(branches))
        for branch in progress:
            progress.set_description('{0}'.format(branch))
            for commit in self.repo.iter_commits(branch):
                self.__addVector__(commit)                  # only add none duplicate vectors
                self.__parseParents__(commit)               # only add none duplicate parent vectors and edges
    
    def assign(self):
        terminals = list(filter(lambda vector: len(vector.parents) == 0 or len(vector.children) == 0, self.vertices.values()))
        sequentials = list(filter(lambda vector: len(vector.parents) == 1 and len(vector.children) == 1, self.vertices.values()))
        structurals = list(filter(lambda vector: (vector not in terminals) and (len(vector.parents) + len(vector.children)) > 2, self.vertices.values()))
        branching = list (filter (lambda vector: (len(vector.children) > 1) and (len(vector.parents) >= 1), self.vertices.values()))
        merging = list (filter (lambda vector: (len(vector.children) >= 1) and (len(vector.parents) > 1), self.vertices.values()))

        vectors = list (self.vertices.values())
        for vector in vectors:
            if (vector in terminals):
                vector.commitType = CommitType.TERMINAL
            if (vector in sequentials):
                vector.commitType = CommitType.SEQUENTIAL
            if (vector in structurals):
                vector.commitType = CommitType.STRUCTURAL
            if (vector in branching):
                vector.branching = True
            if (vector in merging):
                vector.merging = True

    def prune(self):
        sequentials = tqdm(list(filter(lambda vertex: len(vertex.parents) == 1 and len(vertex.children) == 1, self.vertices.values())))
        for sequential in sequentials:
            sequentials.set_description('{0}'.format(sequential.commit.hexsha))

            # handle the parent vector
            parent = self.vertices[sequential.parents[0]]
            parentEdges = list(filter(lambda edge: [sequential.commit.hexsha, sequential.parents[0]] == edge, self.edges))
            for edge in parentEdges:
                self.edges.remove(edge)

            # handle the child vector
            child = self.vertices.get(sequential.children[0])
            childEdges = list(filter(lambda edge: [sequential.children[0], sequential.commit.hexsha] == edge, self.edges))
            for edge in childEdges:
                self.edges.remove(edge)

            # add edge between child and parent, bypassing the commit
            if child is not None and parent is not None:
                self.__addEdge__(child.commit.hexsha, parent.commit.hexsha)

            # remove the sequential vector
            self.vertices.pop(sequential.commit.hexsha)

    def print(self, show_all = False):
        data = self.getData()
        print('Vectors: {0}, Edges: {1}'.format(len(data['vertices']), len(data['edges'])))
        print('  Terminals: {0}'.format(len(list(filter(lambda vertex: vertex.commitType == CommitType.TERMINAL, data['vertices'])))))
        print('  Sequentials: {0}'.format(len(list(filter(lambda vertex: vertex.commitType == CommitType.SEQUENTIAL, data['vertices'])))))
        print('  Structurals: {0}'.format(len(list(filter(lambda vertex: vertex.commitType == CommitType.STRUCTURAL, data['vertices'])))))
        print('  Branching: {0}'.format(len(list(filter(lambda vertex: vertex.branching == True, data['vertices'])))))
        print('  Merging: {0}'.format(len(list(filter(lambda vertex: vertex.merging == True, data['vertices'])))))
        if show_all:
            for key, value in data.items():
                print(key, ' : ', value)

parser = argparse.ArgumentParser()
parser.add_argument("root")
args = parser.parse_args()

graph = GitGraph(args.root)
graph.parse()
graph.prune()
graph.assign()
graph.print()