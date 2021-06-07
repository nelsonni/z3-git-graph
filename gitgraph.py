import argparse
import re
from itertools import tee, count
from git.util import IterableList
from tqdm import tqdm # for progressbar
from git import Repo
from git.objects.commit import Commit
from git.types import PathLike
from typing import Dict, List, Tuple

class Vertex():

    def __init__(self, commit: Commit):
        self.commit: Commit = commit
        self.parents: List[str] = [parent.hexsha for parent in commit.parents]
        self.children = []
        self.branching = False
        self.merging = False
        self.terminal = False
        self.sequential = False
        self.structural = False

    def __hash__(self):
        return self.commit.hexsha

    def __repr__(self):
        return '{0}\n\tparents: {1}\n\tchildren: {2}\n\tterminal: {3}\n\tsequential: {4}\n\tstructural: {5}\n\tbranching: {6}\n\tmerging: {7}\n'.format(self.commit.hexsha, self.parents, self.children, self.terminal, self.sequential, self.structural, self.branching, self.merging)
    
    def __str__(self):
        return self.__repr__()

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.commit.hexsha == other.commit.hexsha
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

class Branch():

    def __init__(self, branch: str, remotes: IterableList):
        self.branch: str = str(branch)
        self.names: List[str] = [str(remote) + '/' + self.branch for remote in remotes]
        self.names.append(self.branch)
        self.vertices: List[Vertex] = []

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return other.branch in self.names
        else:
            return False
    
    def __repr__(self):
        return '{0}\n\tnames: {1}\n\tvertices: {2}\n'.format(self.branch, self.names, [v.commit.hexsha for v in self.vertices])
    
    def __str__(self):
        return self.__repr__()
    
    def __find__(self, vertex: Vertex) -> Tuple[bool, int]:
        existing = False
        index = -1
        for i, v in enumerate(self.vertices):
            if vertex.commit.hexsha == v.commit.hexsha:
                existing = True
            if vertex.commit.hexsha in [p.hexsha for p in v.commit.parents]:
                index = i
        return [existing, index]

    def sliding_window(iterable, n=2):
        iterables = tee(iterable, n)
    
        for iterable, num_skipped in zip(iterables, count()):
            for _ in range(num_skipped):
                next(iterable, None)
    
        return zip(*iterables)

    def addVertex(self, vertex: Vertex):
        [existing, index] = self.__find__(vertex)
        if not existing:
            if index >= 0:
                self.vertices.insert(index, vertex)
            else:
                self.vertices.append(vertex)
        

class GitGraph():

    def __init__(self, root: PathLike):
        self.repo = Repo(root)
        self.branches: List[Branch] = []                    # all branches; [branch: [hexsha, ...]] format (branch format: 'alias/name')
        self.vertices: Dict[str, Vertex] = dict()           # all vertices; [hexsha: Vertex] format
        self.edges: List[Tuple[Vertex, Vertex]] = []        # all directed edges; [start, end] format
        self.parse()

    def __iter__(self):
        return GitGraphIterator(self)

    def __getEdge__(self, start: Vertex, end: Vertex) -> Tuple[Vertex, Vertex]:
        candidate = [start, end]
        existing = list(filter(lambda e: candidate == e, self.edges))
        if len(existing) == 0:                              # no duplicate directed edges
            self.edges.append(candidate)
        return candidate

    def __getVertex__(self, commit: Commit) -> Vertex:
        vertex = self.vertices.get(commit.hexsha)
        if vertex is None:                                  # no duplicate commits
            vertex = Vertex(commit)
            self.vertices.update({ commit.hexsha: vertex })
        return vertex
    
    def __getBranch__(self, branchName: str) -> Branch:
        branch = Branch(branchName, self.repo.remotes)
        existing = [b for b in self.branches if b == branch]
        if len(existing) == 0:                              # no duplicate branches
            self.branches.append(branch)
            return branch
        else:
            return existing[0]

    def __categorize__(self, vertex: Vertex):
        if (len(vertex.parents) == 0 or len(vertex.children) == 0):
            vertex.terminal = True
        if (len(vertex.parents) == 1 and len(vertex.children) == 1):
            vertex.sequential = True
        if (len(vertex.parents) + len(vertex.children) > 2):
            vertex.structural = True
        if (len(vertex.children) > 1):
            vertex.branching = True
        if (len(vertex.parents) > 1):
            vertex.merging = True
        self.vertices.update({ vertex.commit.hexsha: vertex })

    def parse(self):
        print("Parsing git for branches and commits...")
        branches = list(filter(lambda ref: ref not in self.repo.tags and str(ref) != 'origin/HEAD', self.repo.refs))
        progress = tqdm(branches)
        for branch in progress:
            progress.set_description('{0}'.format(branch))
            for commit in self.repo.iter_commits(branch):
                vertex = self.__getVertex__(commit)
                self.__getBranch__(branch).addVertex(vertex)

        print("Parsing vertices for parent and child linkage...")
        # progress = tqdm(list(self.vertices.values()))
        for vertex in self.vertices.values():
            # progress.set_description('{0}'.format(vertex.commit.hexsha))
            for hexsha in vertex.parents:
                parent = self.vertices.get(str(hexsha))
                if parent:
                    self.__getEdge__(vertex, parent)
                    parent.children.append(vertex.commit.hexsha)
                    vertex.parents.append(parent)
        [self.__categorize__(vertex) for vertex in self.vertices.values()]   # wait to categorize until after all vertices have been added
        # self.print()
    
    def prune(self):
        print("Pruning sequential vertices from the graph...")
        sequentials = tqdm(list(filter(lambda vertex: len(vertex.parents) == 1 and len(vertex.children) == 1, self.vertices.values())))
        for sequential in sequentials:
            sequentials.set_description('{0}'.format(sequential.commit.hexsha))

            # handle the parent vertex
            parent = self.vertices[sequential.parents[0]]
            parentEdges = list(filter(lambda edge: [sequential.commit.hexsha, sequential.parents[0]] == edge, self.edges))
            for edge in parentEdges:
                self.edges.remove(edge)

            # handle the child vertex
            child = self.vertices.get(sequential.children[0])
            childEdges = list(filter(lambda edge: [sequential.children[0], sequential.commit.hexsha] == edge, self.edges))
            for edge in childEdges:
                self.edges.remove(edge)

            # add edge between child and parent, bypassing the commit
            if child is not None and parent is not None:
                self.__addEdge__(child.commit.hexsha, parent.commit.hexsha)

            # remove the sequential vertex
            branchVertices = self.branches.get(sequential.branch)
            if branchVertices:
                self.branches.update({sequential.branch: branchVertices.remove(sequential)})
            self.vertices.pop(sequential.commit.hexsha)

    def print(self, show_all = False):
        print('Vectors: {0}, Edges: {1}, Branches: {2}'.format(len(self.vertices), len(self.edges), len(self.branches)))
        print('  Terminals: {0}'.format(len(list(filter(lambda vertex: vertex.terminal == True, self.vertices.values())))))
        print('  Sequentials: {0}'.format(len(list(filter(lambda vertex: vertex.sequential == True, self.vertices.values())))))
        print('  Structurals: {0}'.format(len(list(filter(lambda vertex: vertex.structural == True, self.vertices.values())))))
        print('  Branching: {0}'.format(len(list(filter(lambda vertex: vertex.branching == True, self.vertices.values())))))
        print('  Merging: {0}'.format(len(list(filter(lambda vertex: vertex.merging == True, self.vertices.values())))))
        if show_all:
            print("VERTICES:")
            for v in self.vertices.values():
                print(v)
            print("EDGES:")
            for e in self.edges:
                print(e)
            print("BRANCHES:")
            for b in self.branches:
                print(b)

class GitGraphIterator:

    def __init__(self, graph: GitGraph):
        self._graph = graph
        self._branch_index = 0
        self._branch_vertices = []
        self._pairs_index = 0

    def pairwise(self, iterable):
        a, b = tee(iterable)
        next(b, None)
        return zip(a, b)

    def __next__(self):
        if self._branch_index < len(self._graph.branches):
            if len(self._branch_vertices) == 0:                 # handle the first iteration through a branch
                self._branch_vertices = list(self.pairwise(self._graph.branches[self._branch_index].vertices))
            if self._pairs_index == len(self._branch_vertices): # handle the end of the interations of a branch
                self._branch_index += 1                     
                self._branch_vertices = list(self.pairwise(self._graph.branches[self._branch_index].vertices))
                self._pairs_index = 0
            if self._pairs_index < len(self._branch_vertices):  # handle the middle of the interations of a branch
                pair = self._branch_vertices[self._pairs_index]
                self._pairs_index += 1
                return pair
        raise StopIteration

class GitGraphData():

    branches: Dict[str, List[Vertex]] = dict()
    vertices: List[Vertex] = []                             # all vertices; key is hexsha, value is commit
    edges: List[Tuple[Vertex, Vertex]] = []                 # all directed edges; [start, end] format

    def __init__(self, graph: GitGraph):
        self.branches = graph.branches
        self.vertices = list(graph.vertices.values())
        self.edges = graph.edges

    def __iter__(self):
        return GitGraphIterator(self)

    def print(self):
        print(self.vertices)

# parser = argparse.ArgumentParser()
# parser.add_argument("root")
# args = parser.parse_args()

# graph = GitGraph(args.root)
# graph.parse()
# graph.prune()
# graph.assign()
# graph.print()