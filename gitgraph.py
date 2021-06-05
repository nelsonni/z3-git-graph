import argparse
from tqdm import tqdm # for progressbar
from git import Repo
from git.objects.commit import Commit
from git.types import PathLike
from typing import Dict, List, Tuple

class Vertex():

    branch: str = ''
    commit: Commit = {}
    parents: List[str] = []
    children: List[str] = []
    processed = False
    branching = False
    merging = False
    terminal = False
    sequential = False
    structural = False

    def __init__(self, branch: str, commit: Commit):
        self.branch = branch
        self.commit = commit
        self.parents = []
        self.children = []

    def __hash__(self):
        return self.commit.hexsha

    def __repr__(self):
        return 'Vertex {0}: commit: {{ hexsha: {1}, parents: {2} }}, parents: {3}, children: {4}, processed: {5}, branching: {6}, merging: {7}'.format(
            self.commit.hexsha, self.commit.hexsha, self.commit.parents, self.parents, self.children, 
            self.processed, self.branching, self.merging)
    
    def __str__(self):
        return self.__repr__()

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.commit.hexsha == other.commit.hexsha
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

class GitGraph():

    repo = {}
    branches: Dict[str, List[Vertex]] = dict()
    vertices: Dict[str, Vertex] = dict()                    # all vertices; key is hexsha, value is commit
    edges: List[Tuple[Vertex, Vertex]] = []                 # all directed edges; [start, end] format

    def __init__(self, root: PathLike):
        self.repo = Repo(root)

    def __addEdge__(self, start: Vertex, end: Vertex):
        candidate = [start, end]
        existing = list(filter(lambda e: candidate == e, self.edges))
        if len(existing) == 0:                              # no duplicate directed edges
            self.edges.append(candidate)

    def __addVertex__(self, branch: str, commit: Commit) -> bool:
        if self.vertices.get(commit.hexsha) is None:        # no duplicate commits
            newVertex = Vertex(branch, commit)
            branchVertices = self.branches.get(branch)
            if branchVertices:
                self.branches.update({branch: branchVertices.append(newVertex)})
            self.vertices.update({commit.hexsha: newVertex})

    def __addParent__(self, branch: str, parent: str, child: Commit):
        self.__addVertex__(branch, self.repo.commit(parent))        # guarantee parent vector exists
        self.vertices.get(parent.hexsha).children.append(child.hexsha)
        self.__addEdge__(self.vertices[child.hexsha], self.vertices[parent.hexsha])
    
    def __parseParents__(self, branch: str, child: Commit):
        if self.vertices.get(child.hexsha).processed is False:
            self.vertices.get(child.hexsha).processed = True
            for parent in child.parents:
                self.vertices.get(child.hexsha).parents.append(parent.hexsha)
                self.__addParent__(branch, parent, child)

    def getData(self):
        self.parse()
        self.prune()
        self.assign()
        return GitGraphData(self)

    def parse(self):
        branches = filter(lambda ref: ref not in self.repo.tags, self.repo.refs)
        progress = tqdm(list(branches))
        for branch in progress:
            progress.set_description('{0}'.format(branch))
            for commit in self.repo.iter_commits(branch):
                self.__addVertex__(branch, commit)          # only add none duplicate vectors
                self.__parseParents__(branch, commit)       # only add none duplicate parent vectors and edges
    
    def assign(self):
        terminals = list(filter(lambda vector: len(vector.parents) == 0 or len(vector.children) == 0, self.vertices.values()))
        sequentials = list(filter(lambda vector: len(vector.parents) == 1 and len(vector.children) == 1, self.vertices.values()))
        structurals = list(filter(lambda vector: (vector not in terminals) and (len(vector.parents) + len(vector.children)) > 2, self.vertices.values()))
        branching = list (filter (lambda vector: (len(vector.children) > 1) and (len(vector.parents) >= 1), self.vertices.values()))
        merging = list (filter (lambda vector: (len(vector.children) >= 1) and (len(vector.parents) > 1), self.vertices.values()))

        for vertex in list(self.vertices.values()):
            if (vertex in terminals):
                vertex.terminal = True
            if (vertex in sequentials):
                vertex.sequential = True
            if (vertex in structurals):
                vertex.structural = True
            if (vertex in branching):
                vertex.branching = True
            if (vertex in merging):
                vertex.merging = True

    def prune(self):
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
        data = self.getData()
        print('Vectors: {0}, Edges: {1}'.format(len(data.vertices), len(data.edges)))
        print('  Terminals: {0}'.format(len(list(filter(lambda vertex: vertex.terminal == True, data.vertices)))))
        print('  Sequentials: {0}'.format(len(list(filter(lambda vertex: vertex.sequential == True, data.vertices)))))
        print('  Structurals: {0}'.format(len(list(filter(lambda vertex: vertex.structural == True, data.vertices)))))
        print('  Branching: {0}'.format(len(list(filter(lambda vertex: vertex.branching == True, data.vertices)))))
        print('  Merging: {0}'.format(len(list(filter(lambda vertex: vertex.merging == True, data.vertices)))))
        if show_all:
            for key, value in data.items():
                print(key, ' : ', value)


class GitGraphIterator:

    def __init__(self, graph):
        self._graph = graph
        self._branch_index = 0
        self._vertex_index = 0

    def __next__(self):
        if self._branch_index < len(self._graph.branches):
            branchVertices = self._graph.branches.keys()[self._branch_index]
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

# parser = argparse.ArgumentParser()
# parser.add_argument("root")
# args = parser.parse_args()

# graph = GitGraph(args.root)
# graph.parse()
# graph.prune()
# graph.assign()
# graph.print()