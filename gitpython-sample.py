import os
from git import Repo

bare_repo = Repo.init(os.path.join(os.getcwd(), 'bare-repo'), bare=True)
assert bare_repo.bare