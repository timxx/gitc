# -*- coding: utf-8 -*-

from collections import defaultdict
from datetime import date

from pygit2 import (
    Repository,
    GIT_SORT_TOPOLOGICAL,
    GIT_REF_OID,
    discover_repository,
    GitError
)

import subprocess
import os
import bisect
import re

from .common import Commit


class GitProcess():

    def __init__(self, repoDir, args):
        startupinfo = None
        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        self._process = subprocess.Popen(
            ["git"] + args,
            cwd=repoDir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            startupinfo=startupinfo)

    @property
    def process(self):
        return self._process

    @property
    def returncode(self):
        return self._process.returncode

    def communicate(self):
        return self._process.communicate()


class Ref():
    INVALID = -1
    TAG = 0
    HEAD = 1
    REMOTE = 2

    def __init__(self, type, name):
        self._type = type
        self._name = name

    def __str__(self):
        string = "type: {0}\n".format(self._type)
        string += "name: {0}".format(self._name)

        return string

    def __lt__(self, other):
        return self._type < other._type

    @property
    def type(self):
        return self._type

    @type.setter
    def type(self, type):
        self._type = type

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._name = name

    @classmethod
    def fromRawString(cls, name):
        if not name.startswith("refs/"):
            return None

        name = name[5:]

        _type = Ref.INVALID
        _name = None

        if name.startswith("heads/"):
            _type = Ref.HEAD
            _name = name[6:]
        elif name.startswith("remotes") \
                and not name.endswith("HEAD"):
            _type = Ref.REMOTE
            _name = name
        elif name.startswith("tags/"):
            _type = Ref.TAG
            if name.endswith("^{}"):
                _name = name[5:-3]
            else:
                _name = name[5:]
        else:
            return None

        return cls(_type, _name)


class Git():
    # NOT thread-safe
    repo = None
    REF_MAP = {}
    REV_HEAD = None

    # local uncommitted changes
    LUC_SHA1 = "0000000000000000000000000000000000000000"
    # local changes checked
    LCC_SHA1 = "0000000000000000000000000000000000000001"

    @staticmethod
    def run(args):
        return GitProcess(Git.repo.workdir, args)

    @staticmethod
    def checkOutput(args):
        process = Git.run(args)
        data = process.communicate()[0]
        if process.returncode != 0:
            return None

        return data

    @staticmethod
    def load(directory):
        """ load a git repository from @directory
        if @directory is not a repository, None returned,
        otherwise pygit2.Repository is returned
        """
        if not os.path.isdir(directory):
            return None
        if not os.path.exists(directory):
            return None

        path = discover_repository(directory)
        if not path:
            return None

        return Repository(path)

    @staticmethod
    def loadForBranch(repo, branch):
        worktrees = repo.list_worktrees()
        if not worktrees:
            return None

        # current repo is in worktree
        index = repo.path.rfind(".git/worktrees/")
        if index > 0 and os.path.basename(repo.path.rstrip('/')) in worktrees:
            main_repo = Repository(repo.path[:index])
            if main_repo.head.shorthand == branch:
                return main_repo

            return None

        for wt in worktrees:
            # FIXME: seems pygit2 no way to get the worktree branch name
            try:
                wt_repo = Repository(repo.lookup_worktree(wt).path)
                if wt_repo.head.shorthand == branch:
                    return wt_repo
            except GitError:
                pass
        return None

    @staticmethod
    def refs():
        refMap = defaultdict(list)
        for r in Git.repo.references:
            ref = Ref.fromRawString(r)
            if not ref:
                continue

            reference = Git.repo.references[r]
            if reference.type == GIT_REF_OID:
                sha1 = reference.target.hex
            else:
                sha1 = reference.target
            bisect.insort(refMap[sha1], ref)

        return refMap

    @staticmethod
    def revHead():
        return Git.repo.head.target.hex

    @staticmethod
    def branches():
        cur_branch = Git.repo.head.shorthand
        return list(Git.repo.branches), cur_branch

    @staticmethod
    def commitSummary(sha1):
        commit = Git.repo.revparse_single(sha1)
        dt = date.fromtimestamp(float(commit.author.time))

        return {"sha1": commit.short_id,
                "subject": commit.message.split('\n')[0],
                "date": "%d-%02d-%02d" % (dt.year, dt.month, dt.day),
                "author": commit.author.name,
                "email": commit.author.email}

    @staticmethod
    def commitSubject(sha1):
        commit = Git.repo.get(sha1)
        return commit.message.split('\n')[0]

    @staticmethod
    def externalDiff(commit, path=None, tool=None):
        args = ["difftool"]
        if commit.sha1 == Git.LUC_SHA1:
            pass
        elif commit.sha1 == Git.LCC_SHA1:
            args.append("--cached")
        else:
            args.append("{0}^..{0}".format(commit.sha1))

        if tool:
            args.append("--tool={}".format(tool))

        if path:
            args.append("--")
            args.append(path)

        process = Git.run(args)

    @staticmethod
    def conflictFiles():
        args = ["diff", "--name-only",
                "--diff-filter=U",
                "-no-color"]
        data = Git.checkOutput(args)
        if not data:
            return None
        return data.rstrip(b'\n').decode("utf-8").split('\n')

    @staticmethod
    def isMergeInProgress():
        """return True only if in merge state and has unmerged paths"""
        path = Git.gitPath("MERGE_HEAD")
        if not path:
            return False
        if not os.path.exists(path):
            return False

        # use raw data without splitting
        args = ["diff", "--name-only",
                "--diff-filter=U",
                "-no-color"]
        data = Git.checkOutput(args)
        if not data:
            return False

        return len(data.rstrip(b'\n')) > 0

    @staticmethod
    def gitPath(name):
        dir = Git.repo.path
        if not dir:
            return None
        if dir[-1] != '/' and dir[-1] != '\\':
            dir += '/'

        return dir + name

    @staticmethod
    def mergeBranchName():
        """return the current merge branch name"""
        # TODO: is there a better way?
        path = Git.gitPath("MERGE_MSG")
        if not os.path.exists(path):
            return None

        name = None
        with open(path, "r") as f:
            line = f.readline()
            m = re.match("Merge.* '(.*)' into .*", line)
            if m:
                name = m.group(1)

        # likely a sha1
        if name and re.match("[a-f0-9]{7,40}", name):
            data = Git.checkOutput(["branch", "--remotes",
                                    "--contains", name])
            if data:
                data = data.rstrip(b'\n')
                if data:
                    # might have more than one branch
                    name = data.decode("utf-8").split('\n')[0].strip()

        return name

    @staticmethod
    def resolveBy(ours, path):
        args = ["checkout",
                "--ours" if ours else "--theirs",
                path]
        process = Git.run(args)
        process.communicate()
        if process.returncode != 0:
            return False

        args = ["add", path]
        process = Git.run(args)
        process.communicate()
        return True if process.returncode == 0 else False

    @staticmethod
    def undoMerge(path):
        """undo a merge on the @path"""
        if not path:
            return False

        args = ["checkout", "-m", path]
        process = Git.run(args)
        process.communicate()

        return process.returncode == 0
