#
# (C) Semantix Information Technologies, Neuropublic, IB Krates
#     and European Space Agency
#
# Licensed under the GPL with Runtime Exception.
# Note that there are no charges (royalties) for the generated code.
'''
This is the code generator for the QGenAda code mappers.
This backend is called by aadl2glueC, when a QGenAda subprogram
is identified in the input concurrency view.

This code generator supports both UPER/ACN and Native encodings,
and also supports UPER/ACN using both ASN1SCC and Nokalva.

Matlab/QGenAda is a member of the synchronous "club" (SCADE, etc) ;
The subsystem developer (or rather, the APLC developer) is
building a model in QGenAda, and the generated code is offered
in the form of a "function" that does all the work.
To that end, we create "glue" functions for input and output
parameters, which have C callable interfaces. The necessary
stubs (to allow calling from the VM side) are also generated.
'''

from typing import List
from ..commonPy.utility import panicWithCallStack
from ..commonPy.asnAST import (
    sourceSequenceLimit, isSequenceVariable, AsnInt, AsnReal, AsnEnumerated,
    AsnBool, AsnSequenceOrSet, AsnSequenceOrSetOf, AsnChoice, AsnOctetString,
    AsnNode)
from ..commonPy.asnParser import AST_Lookup, AST_Leaftypes
from ..commonPy.aadlAST import AadlPort, AadlParameter, ApLevelContainer, Param
from ..commonPy.recursiveMapper import RecursiveMapper
from .synchronousTool import SynchronousToolGlueGenerator

isAsynchronous = False


def IsElementMappedToPrimitive(node: AsnSequenceOrSetOf, names: AST_Lookup) -> bool:
    contained = node._containedType
    while isinstance(contained, str):
        contained = names[contained]
    return isinstance(contained, (AsnInt, AsnReal, AsnBool, AsnEnumerated))


# pylint: disable=no-self-use
class FromQGenAdaToASN1SCC(RecursiveMapper):
    def MapInteger(self, srcQGenAda: str, destVar: str, _: AsnInt, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return ["%s := (asn1SccSint) %s;\n" % (destVar, srcQGenAda)]

    def MapReal(self, srcQGenAda: str, destVar: str, _: AsnReal, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return ["%s := %s;\n" % (destVar, srcQGenAda)]

    def MapBoolean(self, srcQGenAda: str, destVar: str, _: AsnBool, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return ["%s := (asn1SccUint) %s;\n" % (destVar, srcQGenAda)]

    def MapOctetString(self, srcQGenAda: str, destVar: str, node: AsnOctetString, _: AST_Leaftypes, __: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        lines = ["-- TODO: MapOctetString: \n"]  # type: List[str]
        if not node._range:
            panicWithCallStack("OCTET STRING (in %s) must have a SIZE constraint inside ASN.1,\nor else we can't generate C code!" % node.Location())  # pragma: no cover
        for i in range(0, node._range[-1]):
            lines.append("%s.data(%d) := %s.element_data(%d);\n" % (destVar, i + 1, srcQGenAda, i + 1))
        if isSequenceVariable(node):
            lines.append("%s.nCount := %s.length;\n" % (destVar, srcQGenAda))
        # No nCount anymore
        # else:
        #     lines.append("%s.nCount = %s;\n" % (destVar, node._range[-1]))
        return lines

    def MapEnumerated(self, srcQGenAda: str, destVar: str, _: AsnEnumerated, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return ["TODO: MapEnumerated: %s = %s;\n" % (destVar, srcQGenAda)]

    def MapSequence(self, unused_srcQGenAda: str, unused_destVar: str, node: AsnSequenceOrSet, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        lines = []  # type: List[str]
        for child in node._members:
            lines.extend(
                self.Map(
                    "%s" % (self.CleanName(child[0])),
                    self.CleanName(child[0]),
                    child[1],
                    leafTypeDict,
                    names))
        return lines

    def MapSet(self, srcQGenAda: str, destVar: str, node: AsnSequenceOrSet, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return self.MapSequence(srcQGenAda, destVar, node, leafTypeDict, names)  # pragma: nocover

    def MapChoice(self, srcQGenAda: str, destVar: str, node: AsnChoice, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        lines = ["-- TODO: MapChoice\n"]  # type: List[str]
        childNo = 0
        for child in node._members:
            childNo += 1
            lines.append("%sif (%s.choiceIdx == %d) {\n" % (self.maybeElse(childNo), srcQGenAda, childNo))
            lines.extend(
                ['    ' + x
                 for x in self.Map(
                     "%s.%s" % (srcQGenAda, self.CleanName(child[0])),
                     destVar + ".u." + self.CleanName(child[0]),
                     child[1],
                     leafTypeDict,
                     names)])
            lines.append("    %s.kind = %s;\n" % (destVar, self.CleanName(child[2])))
            lines.append("}\n")
        return lines

    def MapSequenceOf(self, srcQGenAda: str, destVar: str, node: AsnSequenceOrSetOf, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("need a SIZE constraint or else we can't generate C code (%s)!\n" % node.Location())  # pragma: no cover
        isMappedToPrimitive = IsElementMappedToPrimitive(node, names)
        lines = ["-- TODO: MapSequenceOf\n"]  # type: List[str]
        for i in range(0, node._range[-1]):
            lines.extend(
                self.Map(("%s.element_data(%d)" % (srcQGenAda, i + 1)) if isMappedToPrimitive else ("%s.element_%02d" % (srcQGenAda, i + 1)),
                         destVar + ".data(%d)" % (i + 1),
                         node._containedType,
                         leafTypeDict,
                         names))
        if isSequenceVariable(node):
            lines.append("%s.nCount := %s.length;\n" % (destVar, srcQGenAda))
        # No nCount anymore
        # else:
        #     lines.append("%s.nCount = %s;\n" % (destVar, node._range[-1]))
        return lines

    def MapSetOf(self, srcQGenAda: str, destVar: str, node: AsnSequenceOrSetOf, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return self.MapSequenceOf(srcQGenAda, destVar, node, leafTypeDict, names)  # pragma: nocover


# pylint: disable=no-self-use
class FromASN1SCCtoQGenAda(RecursiveMapper):
    def MapInteger(self, srcVar: str, dstQGenAda: str, _: AsnInt, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return ["-- TODO: FromASN1SCCtoQGenAda: MapInteger:\n", "%s := %s;\n" % (dstQGenAda, srcVar)]

    def MapReal(self, srcVar: str, dstQGenAda: str, _: AsnReal, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return ["-- TODO: FromASN1SCCtoQGenAda: MapReal:\n", " %s := %s;\n" % (dstQGenAda, srcVar)]

    def MapBoolean(self, srcVar: str, dstQGenAda: str, _: AsnBool, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return ["-- TODO: FromASN1SCCtoQGenAda: MapBoolean:\n", " %s := %s;\n" % (dstQGenAda, srcVar)]

    def MapOctetString(self, srcVar: str, dstQGenAda: str, node: AsnOctetString, _: AST_Leaftypes, __: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("OCTET STRING (in %s) must have a SIZE constraint inside ASN.1,\nor else we can't generate C code!" % node.Location())  # pragma: no cover

        lines = ["-- TODO: FromASN1SCCtoQGenAda: MapOctetString\n"]  # type: List[str]
        limit = sourceSequenceLimit(node, srcVar)
        for i in range(0, node._range[-1]):
            lines.append("if (%s>=%d) %s.element_data(%d) = %s.data(%d); else %s.element_data(%d) = 0;\n" %
                         (limit, i + 1, dstQGenAda, i + 1, srcVar, i + 1, dstQGenAda, i + 1))
        if len(node._range) > 1 and node._range[0] != node._range[1]:
            lines.append("%s.length = %s;\n" % (dstQGenAda, limit))
        return lines

    def MapEnumerated(self, srcVar: str, dstQGenAda: str, node: AsnEnumerated, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if None in [x[1] for x in node._members]:
            panicWithCallStack("an ENUMERATED must have integer values! (%s)" % node.Location())  # pragma: no cover
        return ["-- TODO: FromASN1SCCtoQGenAda: MapEnumerated:\n", " %s = %s;\n" % (dstQGenAda, srcVar)]

    def MapSequence(self, srcVar: str, dstQGenAda: str, node: AsnSequenceOrSet, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        lines = ["-- TODO: FromASN1SCCtoQGenAda: MapSequence\n"]  # type: List[str]
        for child in node._members:
            lines.extend(
                self.Map(
                    srcVar + "." + self.CleanName(child[0]),
                    "%s.%s" % (dstQGenAda, self.CleanName(child[0])),
                    child[1],
                    leafTypeDict,
                    names))
        return lines

    def MapSet(self, srcVar: str, dstQGenAda: str, node: AsnSequenceOrSet, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return self.MapSequence(srcVar, dstQGenAda, node, leafTypeDict, names)  # pragma: nocover

    def MapChoice(self, srcVar: str, dstQGenAda: str, node: AsnChoice, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        lines = ["-- TODO: FromASN1SCCtoQGenAda: MapChoice\n"]  # type: List[str]
        childNo = 0
        for child in node._members:
            childNo += 1
            lines.append("%sif (%s.kind == %s) {\n" % (self.maybeElse(childNo), srcVar, self.CleanName(child[2])))
            lines.extend(
                ['    ' + x
                 for x in self.Map(
                     srcVar + ".u." + self.CleanName(child[0]),
                     "%s.%s" % (dstQGenAda, self.CleanName(child[0])),
                     child[1],
                     leafTypeDict,
                     names)])
            lines.append("    %s.choiceIdx = %d;\n" % (dstQGenAda, childNo))
            lines.append("}\n")
        return lines

    def MapSequenceOf(self, srcVar: str, dstQGenAda: str, node: AsnSequenceOrSetOf, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("need a SIZE constraint or else we can't generate C code (%s)!\n" % node.Location())  # pragma: no cover
        isMappedToPrimitive = IsElementMappedToPrimitive(node, names)
        lines = ["-- TODO: FromASN1SCCtoQGenAda: MapSequenceOf\n"]  # type: List[str]
        for i in range(0, node._range[-1]):
            lines.extend(self.Map(
                srcVar + ".data(%d)" % (i + 1),
                ("%s.element_data(%d)" % (dstQGenAda, i + 1)) if isMappedToPrimitive else ("%s.element_%02d" % (dstQGenAda, i + 1)),
                node._containedType,
                leafTypeDict,
                names))
        if isSequenceVariable(node):
            lines.append("%s.length = %s.nCount;\n" % (dstQGenAda, srcVar))
        return lines

    def MapSetOf(self, srcVar: str, dstQGenAda: str, node: AsnSequenceOrSetOf, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return self.MapSequenceOf(srcVar, dstQGenAda, node, leafTypeDict, names)  # pragma: nocover


class QGenAdaGlueGenerator(SynchronousToolGlueGenerator):
    g_FVname = None  # type: str

    def Version(self) -> None:
        print("Code generator: " + "$Id: qgenada_B_mapper.py 2390 2022-02-DD 12:39:17Z a_perez $")  # pragma: no cover

    def FromToolToASN1SCC(self) -> RecursiveMapper:
        return FromQGenAdaToASN1SCC()

    def FromASN1SCCtoTool(self) -> RecursiveMapper:
        return FromASN1SCCtoQGenAda()

    def HeadersOnStartup(self, unused_mofdelingLanguage: str, unused_asnFile: str, subProgram: ApLevelContainer, unused_subProgramImplementation: str, unused_outputDir: str, unused_maybeFVname: str) -> None:
        self.C_SourceFile.write("#include \"%s.h\" // Space certified compiler generated\n" % self.asn_name)
        self.C_SourceFile.write("#include \"qgen_entry_%s.h\"\n\n" % self.CleanNameAsToolWants(subProgram._id).lower())
        self.C_SourceFile.write("static qgen_entry_%s_comp_Input cInput;\n\n" % self.CleanNameAsToolWants(subProgram._id))
        self.C_SourceFile.write("static qgen_entry_%s_comp_Output cOutput;\n\n" % self.CleanNameAsToolWants(subProgram._id))
        self.g_FVname = subProgram._id

    def SourceVar(self,
                  unused_nodeTypename: str,
                  unused_encoding: str,
                  unused_node: AsnNode,
                  unused_subProgram: ApLevelContainer,
                  unused_subProgramImplementation: str,
                  param: Param,
                  unused_leafTypeDict: AST_Leaftypes,
                  unused_names: AST_Lookup) -> str:
        if isinstance(param._sourceElement, AadlPort):
            srcQGenAda = "cOutput.%s" % param._id  # pragma: no cover
        elif isinstance(param._sourceElement, AadlParameter):
            srcQGenAda = "cOutput.%s" % param._id
        else:  # pragma: no cover
            panicWithCallStack("%s not supported (yet?)\n" % str(param._sourceElement))  # pragma: no cover
        return srcQGenAda

    def TargetVar(self,
                  unused_nodeTypename: str,
                  unused_encoding: str,
                  unused_node: AsnNode,
                  unused_subProgram: ApLevelContainer,
                  unused_subProgramImplementation: str,
                  param: Param,
                  unused_leafTypeDict: AST_Leaftypes,
                  unused_names: AST_Lookup) -> str:
        if isinstance(param._sourceElement, AadlPort):
            dstQGenAda = "cInput.%s" % param._id  # pragma: no cover
        elif isinstance(param._sourceElement, AadlParameter):
            dstQGenAda = "cInput.%s" % param._id
        else:  # pragma: no cover
            panicWithCallStack("%s not supported (yet?)\n" % str(param._sourceElement))  # pragma: no cover
        return dstQGenAda

    def InitializeBlock(self, unused_modelingLanguage: str, unused_asnFile: str, unused_sp: ApLevelContainer, unused_subProgramImplementation: str, unused_maybeFVname: str) -> None:
        self.C_SourceFile.write("    static int initialized = 0;\n")
        self.C_SourceFile.write("    if (!initialized) {\n")
        self.C_SourceFile.write("        initialized = 1;\n")
        self.C_SourceFile.write("         qgen_entry_%s_init();\n" % self.g_FVname)
        self.C_SourceFile.write("    }\n")

    def ExecuteBlock(self, unused_modelingLanguage: str, unused_asnFile: str, unused_sp: ApLevelContainer, unused_subProgramImplementation: str, unused_maybeFVname: str) -> None:
        self.C_SourceFile.write("    qgen_entry_%s_comp(&cInput, &cOutput);\n" % self.g_FVname)


qgenAdaBackend: QGenAdaGlueGenerator


def OnStartup(modelingLanguage: str, asnFile: str, subProgram: ApLevelContainer, subProgramImplementation: str, outputDir: str, maybeFVname: str) -> None:
    global qgenAdaBackend
    qgenAdaBackend = QGenAdaGlueGenerator()
    qgenAdaBackend.OnStartup(modelingLanguage, asnFile, subProgram, subProgramImplementation, outputDir, maybeFVname)


def OnBasic(nodeTypename: str, node: AsnNode, subProgram: ApLevelContainer, subProgramImplementation: str, param: Param, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> None:
    qgenAdaBackend.OnBasic(nodeTypename, node, subProgram, subProgramImplementation, param, leafTypeDict, names)


def OnSequence(nodeTypename: str, node: AsnNode, subProgram: ApLevelContainer, subProgramImplementation: str, param: Param, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> None:
    qgenAdaBackend.OnSequence(nodeTypename, node, subProgram, subProgramImplementation, param, leafTypeDict, names)


def OnSet(nodeTypename: str, node: AsnNode, subProgram: ApLevelContainer, subProgramImplementation: str, param: Param, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> None:
    qgenAdaBackend.OnSet(nodeTypename, node, subProgram, subProgramImplementation, param, leafTypeDict, names)  # pragma: nocover


def OnEnumerated(nodeTypename: str, node: AsnNode, subProgram: ApLevelContainer, subProgramImplementation: str, param: Param, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> None:
    qgenAdaBackend.OnEnumerated(nodeTypename, node, subProgram, subProgramImplementation, param, leafTypeDict, names)


def OnSequenceOf(nodeTypename: str, node: AsnNode, subProgram: ApLevelContainer, subProgramImplementation: str, param: Param, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> None:
    qgenAdaBackend.OnSequenceOf(nodeTypename, node, subProgram, subProgramImplementation, param, leafTypeDict, names)


def OnSetOf(nodeTypename: str, node: AsnNode, subProgram: ApLevelContainer, subProgramImplementation: str, param: Param, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> None:
    qgenAdaBackend.OnSetOf(nodeTypename, node, subProgram, subProgramImplementation, param, leafTypeDict, names)  # pragma: nocover


def OnChoice(nodeTypename: str, node: AsnNode, subProgram: ApLevelContainer, subProgramImplementation: str, param: Param, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> None:
    qgenAdaBackend.OnChoice(nodeTypename, node, subProgram, subProgramImplementation, param, leafTypeDict, names)


def OnShutdown(modelingLanguage: str, asnFile: str, sp: ApLevelContainer, subProgramImplementation: str, maybeFVname: str) -> None:
    qgenAdaBackend.OnShutdown(modelingLanguage, asnFile, sp, subProgramImplementation, maybeFVname)
