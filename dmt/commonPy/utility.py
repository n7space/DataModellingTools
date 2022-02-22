# (C) Semantix Information Technologies, Neuropublic, and European Space Agency
#
# Licensed under the GPL with Runtime Exception.
# Note that there are no charges (royalties) for the generated code.
#
import sys
import os
import re
import platform
import traceback

from typing import Dict, Union, Match, Any  # NOQA pylint: disable=unused-import
from mypy_extensions import NoReturn  # NOQA pylint: disable=unused-import

from . import configMT


def inform(fmt: str, *args: Any) -> None:
    if configMT.verbose:
        print(fmt % args)


def warn(fmt: str, *args: Any) -> None:
    sys.stderr.write(("WARNING: " + fmt) % args)
    sys.stderr.write("\n")


def panic(x: str) -> NoReturn:
    if not x.endswith("\n"):
        x += "\n"
    sys.stderr.write("\n" + chr(27) + "[32m" + x + chr(27) + "[0m\n")
    sys.exit(1)


def panicWithCallStack(msg: str) -> NoReturn:
    if configMT.verbose:
        sys.stderr.write("\n" + chr(27) + "[32m" + msg + chr(27) + "[0m\n")
        sys.stderr.write(
            "\nCall stack was:\n%s\n" % "".join(traceback.format_stack()))
        sys.exit(1)
    else:
        panic(msg)


def lcfirst(word: str) -> str:
    if word:
        return word[:1].lower() + word[1:]
    else:
        return word


def ucfirst(word: str) -> str:
    if word:
        return word[:1].upper() + word[1:]
    else:
        return word


def collapseCAPSgroups(word: str) -> str:
    while 1:
        m = re.match('^(.*?)([A-Z][A-Z]+)(.*?)$', word)
        if m:
            word = m.group(1) + lcfirst(m.group(2)) + m.group(3)
        else:
            break
    return word


def readContexts(tapNumbers: str) -> Dict[str, str]:
    data = {}
    for line in open(tapNumbers, "r").readlines():
        line = line.rstrip(os.linesep)
        lista = line.split(":")
        data[lista[0]] = lista[1]
    return data


def mysystem(cmd: str) -> int:
    p = platform.system()
    if p == "Windows" or p.startswith("CYGWIN"):
        return os.system('"' + cmd + '"')
    else:
        return os.system(cmd)

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
