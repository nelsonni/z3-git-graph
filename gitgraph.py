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

    commit: Commit = {}
    parents: List[str] = []
    children: List[str] = []
    branching = False
    merging = False
    terminal = False
    sequential = False
    structural = False

    def __init__(self, commit: Commit):
        self.commit = commit
        self.parents = [parent.hexsha for parent in commit.parents]
        self.children = []

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
        print('{0} addVertex({1}) -> existing: {2}, index: {3}'.format(self.branch, vertex.commit.hexsha, existing, index))
        if not existing:
            if index >= 0:
                print('\tadding vertex {0} at index {1}'.format(vertex.commit.hexsha, index))
                self.vertices.insert(index, vertex)
            else:
                print('\tappending vertex {0} at end of list'.format(vertex.commit.hexsha))
                self.vertices.append(vertex)
        print('Branch {0} has {1} vertices'.format(self.branch, len(self.vertices)))
        

class GitGraph():

    def __init__(self, root: PathLike):
        self.repo = Repo(root)
        self.branches: List[Branch] = []                    # all branches; [branch: [hexsha, ...]] format (branch format: 'alias/name')
        self.vertices: Dict[str, Vertex] = dict()           # all vertices; [hexsha: Vertex] format
        self.edges: List[Tuple[Vertex, Vertex]] = []        # all directed edges; [start, end] format

        self.parse()

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
        print(vertex)
        self.vertices.update({ vertex.commit.hexsha: vertex })

    def parse(self):
        print("Parsing git for branches and commits...")
        branches = list(filter(lambda ref: ref not in self.repo.tags and str(ref) != 'origin/HEAD', self.repo.refs))
        progress = tqdm(branches)
        prevBranchRef = None
        for branch in progress:
            progress.set_description('{0}'.format(branch))
            branchRef = self.__getBranch__(branch)
            if (prevBranchRef):
                same = prevBranchRef == branchRef
                print("prev: {0}, curr: {1}, same: {2}".format(prevBranchRef.branch, branchRef.branch, same))
            prevBranchRef = branchRef

            for commit in self.repo.iter_commits(branch):
                # print('Commit {0} on branch {1}'.format(commit.hexsha, branch))
                vertex = self.__getVertex__(commit)
                self.__getBranch__(branch).addVertex(vertex)
            # print("Branch {0} has {1} vertices".format(branchRef.branch, len(branchRef.vertices)))

        print('Vectors: {0}, Edges: {1}, Branches: {2}'.format(len(self.vertices), len(self.edges), len(self.branches)))
        for branch in self.branches:
            print('Branch: {0}'.format(branch))

        # print("Parsing vertices for parent and child linkage...")
        # progress = tqdm(self.vertices)
        # for vertex in progress:
        #     progress.set_description('{0}'.format(vertex.commit.hexsha))
        #     for hexsha in vertex.parents:
        #         parent = self.vertices.get(hexsha)
        #         if parent:
        #             self.__addEdge__(vertex, parent)
        #             parent.children.append(vertex.commit.hexsha)
        #             self.__updateVertex__(parent)
        # [self.__categorize__(vertex) for vertex in self.vertices]   # wait to categorize until after all vertices have been added

    def pairwise(self):
        a, b = tee(self.vertices)
        next(b, None)
        return zip(a, b)
    
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
        print('Vectors: {0}, Edges: {1}'.format(len(self.vertices), len(self.edges)))
        print('  Terminals: {0}'.format(len(list(filter(lambda vertex: vertex.terminal == True, self.vertices)))))
        print('  Sequentials: {0}'.format(len(list(filter(lambda vertex: vertex.sequential == True, self.vertices)))))
        print('  Structurals: {0}'.format(len(list(filter(lambda vertex: vertex.structural == True, self.vertices)))))
        print('  Branching: {0}'.format(len(list(filter(lambda vertex: vertex.branching == True, self.vertices)))))
        print('  Merging: {0}'.format(len(list(filter(lambda vertex: vertex.merging == True, self.vertices)))))
        if show_all:
            print("VERTICES:")
            for v in self.vertices:
                print(v)
            print("EDGES:")
            for e in self.edges:
                print(e)
            # for key, value in self.items():
            #     print(key, ' : ', value)


class GitGraphIterator:

    def __init__(self, graph: GitGraph):
        self._graph = graph
        self._branch_index = 0
        self._vertex_index = 0

    def __next__(self):
        if self._branch_index < len(self._graph.branches):
            branchVertices = [v for v in self._graph.vertices if v.branch == self._graph.branches[self._branch_index]]
            if self._vertex_index == len(branchVertices):
                self._branch_index += 1
                self._vertex_index = 0
                branchVertices = self._graph.branches.keys()[self._branch_index]
            if self._vertex_index < len(branchVertices):
                result = branchVertices[self._vertex_index]
                self._vertex_index += 1
                return result
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