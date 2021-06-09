from git import Repo
from Vertex import Vertex
from tqdm import tqdm
from git.types import PathLike
from typing import Dict, List, Tuple

class GitGraph():

    def __init__(self, root: PathLike):
        self.repo = Repo(root)
        self.graph: Dict[str, Vertex] = dict()  # hexsha -> Vertex
        self.parse()
        self.link()
        self.prune()
        self.label()

    def __repr__(self):
        entries = ["{0}\n\tparents: {1}\n\tchildren: {2}".format(key, vertex.parents, vertex.children) for key, vertex in self.graph.items()]
        return "\n".join(entries)
    
    def __str__(self):
        return self.__repr__()

    # Time complexity: O(B * C), where B is the number of branches and C is the number of commits
    def parse(self):
        progress = tqdm(list(filter(lambda ref: ref not in self.repo.tags and str(ref) != 'origin/HEAD', self.repo.refs)))
        for branch in progress:
            progress.set_description('PARSE: {0}'.format(branch))
            for commit in self.repo.iter_commits(branch):
                if not self.graph.get(commit.hexsha):
                    self.graph.update({ commit.hexsha: Vertex(commit) })
        
    # Time complexity: O(V + E), where V is the number of vertices and E is the number of edges
    def link(self):
        progress = tqdm(list(self.graph.values()))
        vertex: Vertex              # type annotation in for-loop, per PEP 526
        for vertex in progress:
            progress.set_description('LINK: {0}'.format(vertex.commit.hexsha))
            for parent in vertex.parents:
                self.graph.get(parent).children.append(vertex.commit.hexsha)
    
    # Time complexity: O(V), where V is the number of vertices (dict.get and dict.update are O(1) constant)
    def prune(self):
        progress = tqdm(list(filter(lambda vertex: len(vertex.parents) == 1 and len(vertex.children) == 1, self.graph.values())))
        sequential: Vertex          # type annotation in for-loop, per PEP 526
        for sequential in progress:
            progress.set_description('PRUNE: {0}'.format(sequential.commit.hexsha))

            sequential = self.graph.get(sequential.commit.hexsha)   # retrieve any vertex updates
            parent = self.graph.get(sequential.parents[0])          # sequential type guarantees only 1 parent
            child = self.graph.get(sequential.children[0])          # sequential type guarantess only 1 child

            child.parents = [parent.commit.hexsha if p == sequential.commit.hexsha else p for p in child.parents]
            parent.children = [child.commit.hexsha if c == sequential.commit.hexsha else c for c in parent.children]

            self.graph.update({ parent.commit.hexsha: parent })
            self.graph.update({ child.commit.hexsha: child })

            self.graph.pop(sequential.commit.hexsha)

    # Time complexity: O(V), where V is the number of vertices (dict.update is O(1) constant)
    def label(self):
        progress = tqdm(list(self.graph.values()))
        vertex: Vertex              # type annotation in for-loop, per PEP 526
        for vertex in progress:
            progress.set_description('LABEL: {0}'.format(vertex.commit.hexsha))
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
            self.graph.update({ vertex.commit.hexsha: vertex })

    def topologicalSortUtil(self, k, visited, stack):
        visited.update({k: True})   # mark the current vertex as visited

        # recurse for all adjacent child vertices
        for v in self.graph.get(k).children:
            if visited.get(v) == False:
                self.topologicalSortUtil(v, visited, stack)

        stack.append(k)             # push current vertex to results stack

    # Time complexity: O(V + E), where V is the number of vertices and E is the number of edges
    def topologicalSort(self):
        # mark all vertices as not visited
        visited = dict.fromkeys(self.graph.keys(), False)
        stack = []

        # call recursive helper function to store topological sort starting
        # from all vertices one by one
        for k in self.graph.keys():
            if visited.get(k) == False:
                self.topologicalSortUtil(k, visited, stack)

        return stack[::-1]          # return list in reverse order

    # Time complexity: O(V + E), where V is the number of vertices and E is the number of edges
    def stream(self):
        pairs: List[Tuple[Vertex, Vertex]] = []
        progress = tqdm(self.topologicalSort())
        hexsha: str                 # type annotation in for-loop, per PEP 526
        for hexsha in progress:
            vertex = self.graph.get(hexsha)
            progress.set_description('STREAM: {0}'.format(vertex.commit.hexsha))
            for hexsha in vertex.children:
                child = self.graph.get(hexsha)
                pairs.append([vertex, child])
                
        return pairs                # return list of pairs