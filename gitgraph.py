import argparse
from unicodedata import numeric
from tqdm import tqdm # for progressbar
from git import Repo
from git.objects.commit import Commit
from git.types import PathLike
from typing import Dict, List, Tuple


class Vector():

    commit: Commit = {}
    parents = 0
    children = 0
    parsed = False

    def __init__(self, commit: Commit):
        self.commit = commit

    def incrementChildren(self):
        self.children += 1
class GitGraph():

    repo = {}
    vectors: Dict[str, Vector] = dict()     # all commits; including terminal, sequential, and structural commits
    edges: List[Tuple[Commit, Commit]] = [] # all edges; including those linking sequential commits

    def __init__(self, root: PathLike):
        self.repo = Repo(root)

    def __addEdge__(self, start: str, end: str):
        candidate = [start, end]
        existing = list(filter(lambda e: candidate == e, self.edges))
        if len(existing) == 0: # no duplicate directed edges
            self.edges.append(candidate)

    def __addCommit__(self, commit: Commit) -> bool:
        if self.vectors.get(commit.hexsha) is None: # no duplicate commits
            self.vectors.update({commit.hexsha: Vector(commit)})
            self.vectors.get(commit.hexsha).parents = len(commit.parents)

    def __addParent__(self, parent: Commit, child: str):
        if self.vectors.get(parent.hexsha) is None:
            self.__addCommit__(self.repo.commit(parent.hexsha))
        self.vectors.get(parent.hexsha).incrementChildren()
        self.__addEdge__(child, parent.hexsha)

    def parse(self):
        branches = filter(lambda ref: ref not in self.repo.tags, self.repo.refs)
        progress = tqdm(list(branches))

        for branch in progress:
            progress.set_description('{0}'.format(branch))
            for commit in self.repo.iter_commits(branch):
                if self.vectors.get(commit.hexsha) is None: # no duplicate commits
                    self.__addCommit__(commit)
                    for parent in commit.parents:
                        self.vectors.get(commit.hexsha).parsed = True
                        self.__addParent__(parent, commit.hexsha)
                else:
                    # back propogation needed to handle unparsed parent vectors for their child links
                    if self.vectors.get(commit.hexsha).parsed is False:
                        for parent in commit.parents:
                            self.__addParent__(parent, commit.hexsha)
    
    def prune(self):
        sequentials = list(filter(lambda vector: vector.parents == 1 and vector.children == 1, self.vectors.values()))
        for sequential in sequentials:
            # (parent) <--- [seq.hexsha, parent.hexsha] --- (seq) <--- [child.hexsha, seq.hexsha] --- (child)
            # (parent) <--- [child.hexsha, parent.hexsha] --- (child)

            # handle the parent vector
            # parent = self.vectors[sequential.commit.parents[0].hexsha]
            # parentEdges = list(filter(lambda edge: [sequential.commit.hexsha, parent.commit.hexsha] == edge, self.edges))

            # handle the child vector
            child = list(filter(lambda vector: sequential.commit.hexsha in vector.commit.parents, self.vectors.values()))
            for vector in self.vectors.values():
                # print('commit: {0}, parent: {1}'.format(vector.commit.hexsha, len(vector.commit.parents)))
                if sequential.commit.hexsha in vector.commit.parents:
                    print('FOUND IT! commit: {0}, vector: {1}'.format(sequential.commit.hexsha, vector.commit.hexsha))
                for parent in vector.commit.parents:
                    if sequential.commit.hexsha == parent:
                        print('FOUND IT! parent: {0}'.format(parent))

            # childEdges = list(filter(lambda edge: [child[0].commit.hexsha, sequential.commit.hexsha] == edge, self.edges))

            # print('parent: {0}, child: {1}'.format(parent.commit.hexsha, len(child)))
            # print('parentEdges: {0}, childEdges: {1}'.format(len(parentEdges), len(childEdges)))

            # self.edges.remove(parentEdge)
            # self.edges.remove(childEdge)
            # self.__addEdge__(child.commit.hexsha, parent.commit.hexsha)

            # remove the sequential vector
            # self.vectors.pop(sequential.commit.hexsha)

    def print(self):
        print('Vectors: {0}, Edges: {1}'.format(len(self.vectors), len(self.edges)))
        terminal = list(filter(lambda vector: vector.parents == 0 or vector.children == 0, self.vectors.values()))
        sequential = list(filter(lambda vector: vector.parents == 1 and vector.children == 1, self.vectors.values()))
        structural = list(filter(lambda vector: (vector not in terminal) and (vector.parents + vector.children) > 2, self.vectors.values()))
        print('  Terminal: {0}'.format(len(terminal)))
        print('  Sequential: {0}'.format(len(sequential)))
        print('  Structural: {0}'.format(len(structural)))

        parentless = list(filter(lambda vector: vector.parents == 0, terminal))
        childless = list(filter(lambda vector: vector.children == 0, terminal))
        print('  Parentless Terminals: {0}'.format(len(parentless)))
        print('  Childless Terminals: {0}'.format(len(childless)))

parser = argparse.ArgumentParser()
parser.add_argument("root")
args = parser.parse_args()

graph = GitGraph(args.root)
graph.parse()
# graph.prune()
graph.print()