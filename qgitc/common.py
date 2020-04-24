# -*- coding: utf-8 -*-

import cProfile
import pstats
import io
import os
import sys

from datetime import datetime, timezone, timedelta


html_escape_table = {
    "&": "&amp;",
    '"': "&quot;",
    "'": "&apos;",
    ">": "&gt;",
    "<": "&lt;",
}


class Commit():

    def __init__(self):

        self.sha1 = ""
        self.comments = ""
        self.author = ""
        self.authorDate = ""
        self.committer = ""
        self.committerDate = ""
        self.parents = []
        self.children = None

    def __str__(self):
        return "Commit: {0}\n"  \
               "Author: {1} {2}\n"  \
               "Committer: {3} {4}\n\n"    \
               "{5}".format(self.sha1,
                            self.author, self.authorDate,
                            self.committer, self.committerDate,
                            self.comments)

    @classmethod
    def fromRawString(cls, string):
        commit = cls()

        parts = string.split("\x01")
        if len(parts) != 7:
            return commit

        commit.sha1 = parts[0]
        commit.comments = parts[1].strip("\n")
        commit.author = parts[2]
        commit.authorDate = parts[3]
        commit.committer = parts[4]
        commit.committerDate = parts[5]
        commit.parents = [x for x in parts[6].split(" ") if x]

        return commit

    @classmethod
    def fromRawCommit(cls, rawCommit):
        """ Convert from pygit2's comit """
        commit = cls()

        def timeStr(signature):
            tzinfo = timezone(timedelta(minutes=signature.offset))
            dt = datetime.fromtimestamp(float(signature.time), tzinfo)
            return dt.strftime('%x %X %z')

        def authorStr(author):
            return author.name + " <" + author.email + ">"

        commit.sha1 = rawCommit.id.hex
        commit.comments = rawCommit.message.rstrip()
        commit.author = authorStr(rawCommit.author)
        commit.authorDate = timeStr(rawCommit.author)
        commit.committer = authorStr(rawCommit.committer)
        commit.committerDate = timeStr(rawCommit.committer)
        commit.parents = []
        for id in rawCommit.parent_ids:
            commit.parents.append(id.hex)

        return commit


class MyProfile():

    def __init__(self):
        self.pr = cProfile.Profile()
        self.pr.enable()

    def __del__(self):
        self.pr.disable()
        s = io.StringIO()
        ps = pstats.Stats(self.pr, stream=s).sort_stats("cumulative")
        ps.print_stats()
        print(s.getvalue())


class FindField():

    AddOrDel = 0
    Changes = 1
    Comments = 2
    # for highlight only
    All = 0xff

    @staticmethod
    def isDiff(field):
        return field == FindField.AddOrDel or \
            field == FindField.Changes


class FindParameter():

    def __init__(self, range, pattern, field, flag):
        self.range = range
        self.pattern = pattern
        self.field = field
        self.flag = flag

    def __eq__(self, other):
        if not other:
            return False

        if self.field != other.field:
            return False
        if self.flag != other.flag:
            return False
        if self.pattern != other.pattern:
            return False
        # ignore range compare
        return True


# refer to find type combobox
FIND_EXTACT = 0
FIND_IGNORECASE = 1
FIND_REGEXP = 2

FIND_NOTFOUND = -1
FIND_CANCELED = -2


def htmlEscape(text):
    return "".join(html_escape_table.get(c, c) for c in text)


def appDirPath():
    # qApp.applicationDirPath not works as expected
    path = os.path.realpath(__file__)
    return os.path.dirname(path)


def dataDirPath():
    return appDirPath() + "/data"


def normPath(path):
    return os.path.normcase(os.path.normpath(path))


def isSamePath(path1, path2):
    return normPath(path1) == normPath(path2)
