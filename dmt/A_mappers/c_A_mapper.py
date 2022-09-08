# (C) Semantix Information Technologies, Neuropublic, and European Space Agency
#
# Licensed under the GPL with Runtime Exception.
# Note that there are no charges (royalties) for the generated code.
'''This contains the implementation of model level mapping
of ASN.1 constructs to C. It is used as a backend of Semantix's
code generator A.'''

import os
from distutils import spawn
from typing import List

from ..commonPy.utility import panic
from ..commonPy.cleanupNodes import SetOfBadTypenames
from ..commonPy.asnAST import AsnBasicNode, AsnSequenceOrSet, AsnSequenceOrSetOf, AsnEnumerated, AsnChoice
from ..commonPy.asnParser import AST_Leaftypes


def Version() -> None:
    print("Code generator: " + "$Id: c_A_mapper.py 2382 2012-06-22 08:35:33Z ttsiodras $")  # pragma: no cover


# Especially for the C mapper, since we need to pass the complete ASN.1 files list to ASN1SCC,
# the second param is not asnFile, it is asnFiles

def OnStartup(unused_modelingLanguage: str, asnFiles: List[str], outputDir: str, unused_badTypes: SetOfBadTypenames) -> None:  # pylint: disable=invalid-sequence-index
    # print "Use ASN1SCC to generate the structures for '%s'" % asnFile
    asn1SccPath = spawn.find_executable('asn1scc')
    if not asn1SccPath:
        panic("ASN1SCC seems to be missing from your system (asn1scc not found in PATH).\n")  # pragma: no cover
    os.system(
        "\"{}\" -typePrefix asn1Scc -fp AUTO -renamePolicy 3 -c -uPER -o \"".format(asn1SccPath) +
        outputDir + "\" \"" + "\" \"".join(asnFiles) + "\"")
#   cmd = 'rm -f '
#   for i in ['real.c', 'asn1crt.c', 'acn.c']:
#       cmd += ' "' + outputDir + '"/' + i
#   os.system(cmd)
#   for tmp in asnFiles:
#       os.system("rm -f \"" + outputDir + os.sep + os.path.basename(os.path.splitext(tmp)[0]) + ".c\"")


def OnBasic(unused_nodeTypename: str, unused_node: AsnBasicNode, unused_leafTypeDict: AST_Leaftypes) -> None:
    pass  # pragma: no cover


def OnSequence(unused_nodeTypename: str, unused_node: AsnSequenceOrSet, unused_leafTypeDict: AST_Leaftypes) -> None:
    pass  # pragma: no cover


def OnSet(unused_nodeTypename: str, unused_node: AsnSequenceOrSet, unused_leafTypeDict: AST_Leaftypes) -> None:
    pass  # pragma: no cover


def OnEnumerated(unused_nodeTypename: str, unused_node: AsnEnumerated, unused_leafTypeDict: AST_Leaftypes) -> None:
    pass  # pragma: no cover


def OnSequenceOf(unused_nodeTypename: str, unused_node: AsnSequenceOrSetOf, unused_leafTypeDict: AST_Leaftypes) -> None:
    pass  # pragma: no cover


def OnSetOf(unused_nodeTypename: str, unused_node: AsnSequenceOrSetOf, unused_leafTypeDict: AST_Leaftypes) -> None:
    pass  # pragma: no cover


def OnChoice(unused_nodeTypename: str, unused_node: AsnChoice, unused_leafTypeDict: AST_Leaftypes) -> None:
    pass  # pragma: no cover


def OnShutdown(unused_badTypes: SetOfBadTypenames) -> None:
    pass  # pragma: no cover
