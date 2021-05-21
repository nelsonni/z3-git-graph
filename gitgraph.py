import argparse
from tqdm import tqdm # for progressbar
from git import Repo
from git.objects.commit import Commit
from git.types import PathLike
from typing import Dict, List, Tuple


class Vector():

    commit: Commit = {}
    parents = 0
    children = 0

    def __init__(self, commit: Commit):
        self.commit = commit

    def incrementParent(self):
        self.parents += 1

    def incrementChild(self):
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
        if commit.hexsha not in self.vectors.keys(): # no duplicate commits
            self.vectors.update({commit.hexsha: Vector(commit)})     
            for _ in range(len(commit.parents)):
                self.vectors.get(commit.hexsha).incrementParent()
            return True
        else:
            return False

    def __addParents__(self, commit: Commit):
        for parent in commit.parents:
            if parent not in self.vectors.keys():
                self.__addCommit__(self.repo.commit(parent))
            self.__addEdge__(commit.hexsha, parent)
            self.vectors.get(parent.hexsha).incrementChild()

    def parse(self):
        branches = filter(lambda ref: ref not in self.repo.tags, self.repo.refs)
        progress = tqdm(list(branches))
        for branch in progress:
            progress.set_description('{0}'.format(branch))
            for commit in self.repo.iter_commits(branch):
                new = self.__addCommit__(commit)
                if new: # only new commits should have their parents parsed
                    self.__addParents__(commit)
            # break

    def print(self):
        print('Vectors: {0}, Edges: {1}'.format(len(self.vectors), len(self.edges)))
        terminal = list(filter(lambda vector: vector.parents == 0 or vector.children == 0, self.vectors.values()))
        sequential = list(filter(lambda vector: vector.parents == 1 and vector.children == 1, self.vectors.values()))
        structural = list(filter(lambda vector: (vector not in terminal) and (vector.parents + vector.children) > 2, self.vectors.values()))
        print('  Terminal: {0}'.format(len(terminal)))
        print('  Sequential: {0}'.format(len(sequential)))
        print('  Structural: {0}'.format(len(structural)))

parser = argparse.ArgumentParser()
parser.add_argument("root")
args = parser.parse_args()

graph = GitGraph(args.root)
graph.parse()
graph.print()