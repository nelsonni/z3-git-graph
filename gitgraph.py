import argparse
from git import Repo
class GitGraph():
    vectors = []
    edges = []
    branches = []
    repo = {}

    def __init__(self, root):
        self.repo = Repo(root)
        refs = filter(lambda ref: ref not in self.repo.tags, self.repo.refs)
        print('branches:')
        for ref in refs:
            self.branches.append(ref)
            print(ref)
        
    def printTop(self):
        for branch in self.branches:
            top3 = list(self.repo.iter_commits(branch, max_count=3))
            print('{0} commits:'.format(branch))
            for commit in top3:
                print('{0} => {1}'.format(commit.hexsha, commit.parents))

parser = argparse.ArgumentParser()
parser.add_argument("root")
args = parser.parse_args()

graph = GitGraph(args.root)
graph.printTop()