from git.objects.commit import Commit
from typing import List

class Vertex():

    def __init__(self, commit: Commit):
        self.commit: Commit = commit
        self.parents: List[str] = [parent.hexsha for parent in commit.parents]  # backwards adjacency list
        self.children: List[str] = []                                           # forward adjacency list
        self.branching = False
        self.merging = False
        self.terminal = False
        self.sequential = False
        self.structural = False

    def __hash__(self):
        return self.commit.hexsha

    def __repr__(self):
        return "".join((
            "{0}\n".format(self.commit.hexsha),
            "\tparents: {0}\n".format(self.parents),
            "\tchildren: {0}\n".format(self.children),
            "\tterminal: {0}\n".format(self.terminal),
            "\tsequential: {0}\n".format(self.sequential),
            "\tbranching: {0}\n".format(self.branching),
            "\tmerging: {0}\n".format(self.merging)
        ))
    
    def __str__(self):
        return self.__repr__()

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.commit.hexsha == other.commit.hexsha
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)