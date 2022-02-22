# (C) Semantix Information Technologies, Neuropublic, and European Space Agency
#
# Licensed under the GPL with Runtime Exception.
# Note that there are no charges (royalties) for the generated code.
import sys
import os
import re
import platform
import traceback

import configMT


def inform(format, *args):
    if configMT.verbose:
        print(format % args)


def warn(format, *args):
    sys.stderr.write(("WARNING: " + format) % args)
    sys.stderr.write("\n")


def panic(x):
    if not x.endswith("\n"):
        x += "\n"
    sys.stderr.write("\n"+chr(27)+"[32m" + x + chr(27) + "[0m\n")
    sys.exit(1)


def panicWithCallStack(msg):
    if configMT.verbose:
        sys.stderr.write("\n"+chr(27)+"[32m" + msg + chr(27) + "[0m\n")
        sys.stderr.write("\nCall stack was:\n%s\n" % "".join(traceback.format_stack()))
    else:
        panic(msg)


def lcfirst(word):
    if len(word):
        return word[:1].lower() + word[1:]
    else:
        return word


def ucfirst(word):
    if len(word):
        return word[:1].upper() + word[1:]
    else:
        return word


def collapseCAPSgroups(word):
    while 1:
        m = re.match('^(.*?)([A-Z][A-Z]+)(.*?)$', word)
        if m:
            word = m.group(1) + lcfirst(m.group(2)) + m.group(3)
        else:
            break
    return word


def readContexts(tapNumbers):
    data={}
    for line in open(tapNumbers, "r").readlines():
        line = line.rstrip(os.linesep)
        lista = line.split(":")
        data[lista[0]] = lista[1]
    return data


class Matcher:
    def __init__(self, pattern, flags=0):
        self._pattern = re.compile(pattern, flags)
        self._lastOne = None

    def match(self, line):
        self._match=re.match(self._pattern, line)
        self._lastOne='Match'
        return self._match

    def search(self, line):
        self._search=re.search(self._pattern, line)
        self._lastOne='Search'
        return self._search

    def group(self, idx):
        if self._lastOne == 'Match':
            return self._match.group(idx)
        elif self._lastOne == 'Search':
            return self._search.group(idx)
        else:
            return panic("Matcher group called with index %d before match/search!\n" % idx)

    def groups(self):
        if self._lastOne == 'Match':
            return self._match.groups()
        elif self._lastOne == 'Search':
            return self._search.groups()
        else:
            return panic("Matcher groups called with match/search!\n")


def mysystem(cmd):
    if platform.system() == "Windows" or platform.system().startswith("CYGWIN"):
        return os.system('"' + cmd + '"')
    else:
        return os.system(cmd)
