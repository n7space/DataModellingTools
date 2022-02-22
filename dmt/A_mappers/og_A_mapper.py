# (C) Semantix Information Technologies, Neuropublic, and European Space Agency
#
# Licensed under the GPL with Runtime Exception.
# Note that there are no charges (royalties) for the generated code.

# This is an evolving test implementation of mapping ASN.1 constructs
# to SDL. It is used by the backend of Semantix's code generator A.

# import re

from ..commonPy import asnParser
from ..commonPy.cleanupNodes import SetOfBadTypenames
from ..commonPy.asnAST import AsnBasicNode, AsnSequenceOrSet, AsnSequenceOrSetOf, AsnEnumerated, AsnChoice
from ..commonPy.asnParser import AST_Leaftypes

g_outputDir = ""
g_asnFile = ""


def Version() -> None:
    print("Code generator: " + "$Id: og_A_mapper.py 2382 2012-06-22 08:35:33Z ttsiodras $")  # pragma: no cover


def OnStartup(unused_modelingLanguage: str, asnFile: str, outputDir: str, unused_badTypes: SetOfBadTypenames) -> None:
    global g_asnFile
    g_asnFile = asnFile
    global g_outputDir
    g_outputDir = outputDir


def OnBasic(unused_nodeTypename: str, unused_node: AsnBasicNode, unused_leafTypeDict: AST_Leaftypes) -> None:
    pass


def OnSequence(unused_nodeTypename: str, unused_node: AsnSequenceOrSet, unused_leafTypeDict: AST_Leaftypes) -> None:
    pass


def OnSet(unused_nodeTypename: str, unused_node: AsnSequenceOrSet, unused_leafTypeDict: AST_Leaftypes) -> None:
    pass  # pragma: nocover


def OnEnumerated(unused_nodeTypename: str, unused_node: AsnEnumerated, unused_leafTypeDict: AST_Leaftypes) -> None:
    pass


def OnSequenceOf(unused_nodeTypename: str, unused_node: AsnSequenceOrSetOf, unused_leafTypeDict: AST_Leaftypes) -> None:
    pass


def OnSetOf(unused_nodeTypename: str, unused_node: AsnSequenceOrSetOf, unused_leafTypeDict: AST_Leaftypes) -> None:
    pass  # pragma: nocover


def OnChoice(unused_nodeTypename: str, unused_node: AsnChoice, unused_leafTypeDict: AST_Leaftypes) -> None:
    pass

# obsolete, now the grammar is re-created from the AST (PrintGrammarFromAST)
#
# def ClearUp(text):
#     outputText = ""
#     lParen = 0
#     for c in text:
#         if c == '(':
#             lParen += 1
#         if c == ')':
#             lParen -= 1
#         if 0 == lParen:
#             outputText += c.replace('-', '_')
#         else:
#             outputText += c
#     return outputText


def OnShutdown(unused_badTypes: SetOfBadTypenames) -> None:
    # text = open(g_asnFile, 'r').read()
    # text = re.sub(r'^.*BEGIN', 'Datamodel DEFINITIONS ::= BEGIN', text)
    # text = re.sub(r'--.*', '', text)
    outputFile = open(g_outputDir + "DataView.pr", 'w')
    outputFile.write('Datamodel DEFINITIONS ::= BEGIN\n\n')
    asnParser.PrintGrammarFromAST(outputFile)
    outputFile.write('END\n')
    outputFile.close()
