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
    branching = False
    merging = False
    terminal = False
    sequential = False
    structural = False

    def __init__(self, commit: Commit, branch: str):
        self.commit = commit
        self.branch = branch
        self.parents = [parent.hexsha for parent in commit.parents]
        self.children = []

    def __hash__(self):
        return self.commit.hexsha

    def __repr__(self):
        return '{0}\n\tparents: {1}\n\tchildren: {2}\n\tterminal: {3}\n\tsequential: {4}\n\tstructural: {5}\n'.format(self.commit.hexsha, self.parents, self.children, self.terminal, self.sequential, self.structural)
    
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
    branches: List[str] = []                                # all branches; 'alias/name' format (e.g. 'origin/main')
    vertices: List[Vertex] = []                             # all vertices; [hexsha: Vertex] format
    edges: List[Tuple[Vertex, Vertex]] = []                 # all directed edges; [start, end] format

    def __init__(self, root: PathLike):
        self.repo = Repo(root)
        self.branches = list(filter(lambda ref: ref not in self.repo.tags, self.repo.refs))
        self.parse()

    def __addEdge__(self, start: Vertex, end: Vertex):
        candidate = [start, end]
        existing = list(filter(lambda e: candidate == e, self.edges))
        if len(existing) == 0:                              # no duplicate directed edges
            self.edges.append(candidate)

    def __addVertex__(self, commit: Commit, branch: str):
        # print("addVertex: {0}".format(commit.hexsha))
        exists = len([v for v in self.vertices if v.commit.hexsha == commit.hexsha]) > 0
        if not exists:                                      # no duplicate commits
            self.vertices.append(Vertex(commit, branch))

    def __getVertex__(self, hexsha: str):
        search = [v for v in self.vertices if v.commit.hexsha == hexsha]
        return search[0] if len(search) > 0 else None

    def __updateVertex__(self, updated: Vertex):
        [updated if updated.commit.hexsha == vertex.commit.hexsha else vertex for vertex in self.vertices]

    def __categorize__(self, vertex: Vertex):
        if (len(vertex.parents) == 0 or len(vertex.children) == 0):
            vertex.terminal = True
        if (len(vertex.parents) == 1 and len(vertex.children) == 1):
            vertex.sequential = True
        if (len(vertex.parents) + len(vertex.children) > 2):
            vertex.structural = True
        if (len(vertex.children) > 1 and len(vertex.parents) > 0):
            vertex.branching = True
        if (len(vertex.children) > 0 and len(vertex.parents) > 1):
            vertex.merging = True
        self.__updateVertex__(vertex)

    def parse(self):
        print("Parsing git for branches and commits...")
        progress = tqdm(self.branches)
        for branch in progress:
            progress.set_description('{0}'.format(branch))
            for commit in self.repo.iter_commits(branch):
                self.__addVertex__(commit, branch)          # only add none duplicate vectors

        print("Parsing vertices for parent and child linkage...")
        progress = tqdm(self.vertices)
        for vertex in progress:
            progress.set_description('{0}'.format(vertex.commit.hexsha))
            for hexsha in vertex.parents:
                parent = self.__getVertex__(hexsha)
                if parent:
                    self.__addEdge__(vertex, parent)
                    parent.children.append(vertex.commit.hexsha)
                    self.__updateVertex__(parent)
            self.__categorize__(vertex)
    
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