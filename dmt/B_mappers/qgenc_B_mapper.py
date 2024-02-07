#
# (C) Semantix Information Technologies, Neuropublic, IB Krates
#     and European Space Agency
#
# Licensed under the GPL with Runtime Exception.
# Note that there are no charges (royalties) for the generated code.
'''
This is the code generator for the QGenC code mappers.
This backend is called by aadl2glueC, when a QGenC subprogram
is identified in the input concurrency view.

This code generator supports both UPER/ACN and Native encodings,
and also supports UPER/ACN using both ASN1SCC and Nokalva.

Matlab/QGenC is a member of the synchronous "club" (SCADE, etc) ;
The subsystem developer (or rather, the APLC developer) is
building a model in QGenC, and the generated code is offered
in the form of a "function" that does all the work.
To that end, we create "glue" functions for input and output
parameters, which have C callable interfaces. The necessary
stubs (to allow calling from the VM side) are also generated.
'''

from typing import List
from ..commonPy.utility import panicWithCallStack
from ..commonPy.asnAST import (
    AsnAsciiString, sourceSequenceLimit, isSequenceVariable, AsnInt, AsnReal, AsnEnumerated,
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
class FromQGenCToASN1SCC(RecursiveMapper):
    def __init__(self) -> None:
        self.uniqueID = 0

    def UniqueID(self) -> int:
        self.uniqueID += 1
        return self.uniqueID

    def GenerateUniqueLoopVariableName(self) -> str:
        uniqueID = self.UniqueID()
        return "loopVariable_" + str(uniqueID)

    def MapInteger(self, srcQGenC: str, destVar: str, _: AsnInt, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return ["%s = %s;\n" % (destVar, srcQGenC)]

    def MapReal(self, srcQGenC: str, destVar: str, _: AsnReal, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return ["%s = %s;\n" % (destVar, srcQGenC)]

    def MapBoolean(self, srcQGenC: str, destVar: str, _: AsnBool, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return ["%s = %s;\n" % (destVar, srcQGenC)]

    def MapOctetString(self, srcQGenC: str, destVar: str, node: AsnOctetString, _: AST_Leaftypes, __: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("OCTET STRING (in %s) must have a SIZE constraint inside ASN.1,\nor else we can't generate C code!" % node.Location())  # pragma: no cover

        lines = []  # type: List[str]
        loopVariableName = self.GenerateUniqueLoopVariableName()

        lines.append("for(int %s = 0; %s < %s; ++%s) {\n" % (loopVariableName, loopVariableName, node._range[-1], loopVariableName))
        lines.append("    %s.arr[%s] = %s.arr[%s];\n" % (destVar, loopVariableName, srcQGenC, loopVariableName))
        lines.append("}\n")

        if isSequenceVariable(node):
            lines.append("\n%s.nCount= %s.nCount;\n" % (destVar, srcQGenC))

        return lines

    def MapIA5String(self, srcVar: str, destVar: str, node: AsnAsciiString, _: AST_Leaftypes, __: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("IA5String (in %s) must have a SIZE constraint inside ASN.1,\nor else we can't generate C code!" % node.Location())  # pragma: no cover

        lines = []  # type: List[str]
        loopVariableName = self.GenerateUniqueLoopVariableName()

        lines.append("for(int %s = 0; %s < %s; ++%s) {\n" % (loopVariableName, loopVariableName, node._range[-1] + 1, loopVariableName))
        lines.append("    %s[%s] = %s.arr[%s];\n" % (destVar, loopVariableName, srcVar, loopVariableName))
        lines.append("}\n")

        return lines

    def MapEnumerated(self, srcQGenC: str, destVar: str, _: AsnEnumerated, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return ["%s = %s;\n" % (destVar, srcQGenC)]

    def MapSequence(self, srcVar: str, destVar: str, node: AsnSequenceOrSet, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        lines = []  # type: List[str]
        for child in node._members:
            lines.extend(
                self.Map(
                    srcVar + "." + self.CleanName(child[0]),
                    destVar + "." + self.CleanName(child[0]),
                    child[1],
                    leafTypeDict,
                    names))
        return lines

    def MapChoice(self, srcQGenC: str, destVar: str, node: AsnChoice, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        lines = []  # type: List[str]
        childNo = 0
        for child in node._members:
            childNo += 1
            lines.append("%sif(%s.choiceIdx == %d) {\n" % (self.maybeElse(childNo), srcQGenC, childNo))
            lines.extend(
                ['    ' + x
                 for x in self.Map(
                     "%s.%s" % (srcQGenC, self.CleanName(child[0])),
                     destVar + ".u." + self.CleanName(child[0]),
                     child[1],
                     leafTypeDict,
                     names)])
            lines.append("    %s.kind = %s;\n" % (destVar, self.CleanName(child[2])))
            lines.append("}\n")
        return lines

    def MapSequenceOf(self, srcQGenC: str, destVar: str, node: AsnSequenceOrSetOf, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("need a SIZE constraint or else we can't generate C code (%s)!\n" % node.Location())  # pragma: no cover

        loopVariableName = self.GenerateUniqueLoopVariableName()
        pattern = self.Map(("%s.arr[%s]" % (srcQGenC, loopVariableName)), ("%s.arr[%s]" % (destVar, loopVariableName)), node._containedType, leafTypeDict, names)
        lines = []  # type: List[str]

        lines.extend(["for(int %s = 0; %s < %d; ++%s) {\n" % (loopVariableName, loopVariableName, node._range[-1], loopVariableName)])
        lines.extend(["    "])
        lines.extend(pattern)
        lines.extend(["}\n"])

        if isSequenceVariable(node):
            lines.append("\n%s.nCount = %s.nCount;\n" % (destVar, srcQGenC))

        return lines


# pylint: disable=no-self-use
class FromASN1SCCtoQGenC(RecursiveMapper):
    def __init__(self) -> None:
        self.uniqueID = 0

    def UniqueID(self) -> int:
        self.uniqueID += 1
        return self.uniqueID

    def GenerateUniqueLoopVariableName(self) -> str:
        uniqueID = self.UniqueID()
        return "loopVariable_" + str(uniqueID)

    def MapInteger(self, srcVar: str, dstQGenC: str, _: AsnInt, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return ["%s = %s;\n" % (dstQGenC, srcVar)]

    def MapReal(self, srcVar: str, dstQGenC: str, _: AsnReal, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return ["%s = %s;\n" % (dstQGenC, srcVar)]

    def MapBoolean(self, srcVar: str, dstQGenC: str, _: AsnBool, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return ["%s = %s;\n" % (dstQGenC, srcVar)]

    def MapOctetString(self, srcVar: str, dstQGenC: str, node: AsnOctetString, _: AST_Leaftypes, __: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("OCTET STRING (in %s) must have a SIZE constraint inside ASN.1,\nor else we can't generate C code!" % node.Location())  # pragma: no cover

        lines = []  # type: List[str]
        loopVariableName = self.GenerateUniqueLoopVariableName()
        limit = sourceSequenceLimit(node, srcVar)

        lines.append("for(int %s = 0; %s < %s; ++%s) {\n" % (loopVariableName, loopVariableName, node._range[-1], loopVariableName))
        lines.append("    %s.arr[%s] = %s.arr[%s];\n" % (dstQGenC, loopVariableName, srcVar, loopVariableName))
        lines.append("}\n")

        if isSequenceVariable(node):
            lines.append("\n%s.nCount = %s;\n" % (dstQGenC, limit))

        return lines

    def MapIA5String(self, srcVar: str, destVar: str, node: AsnAsciiString, _: AST_Leaftypes, __: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("IA5String (in %s) must have a SIZE constraint inside ASN.1,\nor else we can't generate C code!" % node.Location())  # pragma: no cover

        lines = []  # type: List[str]
        loopVariableName = self.GenerateUniqueLoopVariableName()

        lines.append("for(int %s = 0; %s < %s; ++%s) {\n" % (loopVariableName, loopVariableName, node._range[-1] + 1, loopVariableName))
        lines.append("    %s.arr[%s] = %s[%s];\n" % (destVar, loopVariableName, srcVar, loopVariableName))
        lines.append("}\n")

        return lines

    def MapEnumerated(self, srcVar: str, dstQGenC: str, node: AsnEnumerated, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if None in [x[1] for x in node._members]:
            panicWithCallStack("an ENUMERATED must have integer values! (%s)" % node.Location())  # pragma: no cover

        return ["%s = %s;\n" % (dstQGenC, srcVar)]

    def MapSequence(self, srcVar: str, dstQGenC: str, node: AsnSequenceOrSet, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        lines = []  # type: List[str]
        for child in node._members:
            lines.extend(
                self.Map(
                    srcVar + "." + self.CleanName(child[0]),
                    "%s.%s" % (dstQGenC, self.CleanName(child[0])),
                    child[1],
                    leafTypeDict,
                    names))
        return lines

    def MapChoice(self, srcVar: str, dstQGenC: str, node: AsnChoice, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        lines = []  # type: List[str]
        childNo = 0
        for child in node._members:
            childNo += 1
            lines.append("%sif (%s.kind == %s) {\n" % (self.maybeElse(childNo), srcVar, self.CleanName(child[2])))
            lines.extend(
                ['    ' + x
                 for x in self.Map(
                     srcVar + ".u." + self.CleanName(child[0]),
                     "%s.%s" % (dstQGenC, self.CleanName(child[0])),
                     child[1],
                     leafTypeDict,
                     names)])
            lines.append("    %s.choiceIdx = %d;\n" % (dstQGenC, childNo))
            lines.append("}\n")
        return lines

    def MapSequenceOf(self, srcVar: str, dstQGenC: str, node: AsnSequenceOrSetOf, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("need a SIZE constraint or else we can't generate C code (%s)!\n" % node.Location())  # pragma: no cover

        loopVariableName = self.GenerateUniqueLoopVariableName()
        pattern = self.Map(("%s.arr[%s]" % (srcVar, loopVariableName)), ("%s.arr[%s]" % (dstQGenC, loopVariableName)), node._containedType, leafTypeDict, names)
        lines = []  # type: List[str]

        lines.extend(["for(int %s = 0; %s < %d; ++%s) {\n" % (loopVariableName, loopVariableName, node._range[-1], loopVariableName)])
        lines.extend(["    "])
        lines.extend(pattern)
        lines.extend(["}\n"])

        if isSequenceVariable(node):
            lines.append("\n%s.nCount = %s.nCount;\n" % (dstQGenC, srcVar))

        return lines


class QGenCGlueGenerator(SynchronousToolGlueGenerator):
    g_FVname = None  # type: str

    def Version(self) -> None:
        print("Code generator: " + "$Id: qgenc_B_mapper.py 2390 2014-11-27 12:39:17Z dtuulik $")  # pragma: no cover

    def FromToolToASN1SCC(self) -> RecursiveMapper:
        return FromQGenCToASN1SCC()

    def FromASN1SCCtoTool(self) -> RecursiveMapper:
        return FromASN1SCCtoQGenC()

    def HeadersOnStartup(self, unused_modelingLanguage: str, unused_asnFile: str, subProgram: ApLevelContainer, unused_subProgramImplementation: str, unused_outputDir: str, unused_maybeFVname: str) -> None:
        self.C_SourceFile.write("#include \"%s.h\" // Space certified compiler generated\n" % self.asn_name)
        if subProgram._simulinkInterfaceType == "full":
            self.C_SourceFile.write("#include \"qgen_entry_%s.h\"\n\n" % self.CleanNameAsToolWants(subProgram._id).lower())
            self.C_SourceFile.write("qgen_entry_%s_comp_Input cInput;\n\n" % self.CleanNameAsToolWants(subProgram._id))
            self.C_SourceFile.write("qgen_entry_%s_comp_Output cOutput;\n\n" % self.CleanNameAsToolWants(subProgram._id))
            self.C_SourceFile.write("int is_%s_initialized = 0;\n\n" % self.CleanNameAsToolWants(subProgram._id))
        else:
            self.C_SourceFile.write("#include \"qgen_entry_%s.h\"\n\n" % self.CleanNameAsToolWants(subProgram._simulinkFullInterfaceRef).lower())
            self.C_SourceFile.write("extern qgen_entry_%s_comp_Input cInput;\n\n" % self.CleanNameAsToolWants(subProgram._simulinkFullInterfaceRef))
            self.C_SourceFile.write("extern qgen_entry_%s_comp_Output cOutput;\n\n" % self.CleanNameAsToolWants(subProgram._simulinkFullInterfaceRef))
            self.C_SourceFile.write("extern int is_%s_initialized;\n\n" % self.CleanNameAsToolWants(subProgram._simulinkFullInterfaceRef))
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
            srcQGenC = "cOutput.%s" % param._id  # pragma: no cover
        elif isinstance(param._sourceElement, AadlParameter):
            srcQGenC = "cOutput.%s" % param._id
        else:  # pragma: no cover
            panicWithCallStack("%s not supported (yet?)\n" % str(param._sourceElement))  # pragma: no cover
        return srcQGenC

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
            dstQGenC = "cInput.%s" % param._id  # pragma: no cover
        elif isinstance(param._sourceElement, AadlParameter):
            dstQGenC = "cInput.%s" % param._id
        else:  # pragma: no cover
            panicWithCallStack("%s not supported (yet?)\n" % str(param._sourceElement))  # pragma: no cover
        return dstQGenC

    def InitializeBlock(self, unused_modelingLanguage: str, unused_asnFile: str, sp: ApLevelContainer, unused_subProgramImplementation: str, unused_maybeFVname: str) -> None:
        fullInterfaceName = ''
        if sp._simulinkInterfaceType == "full":
            fullInterfaceName = self.CleanNameAsADAWants(sp._id)
        else:
            fullInterfaceName = self.CleanNameAsADAWants(sp._simulinkFullInterfaceRef)

        self.C_SourceFile.write("   if (!is_%s_initialized) {\n" % fullInterfaceName)
        self.C_SourceFile.write("       is_%s_initialized = 1;\n" % fullInterfaceName)
        self.C_SourceFile.write("       qgen_entry_%s_init();\n" % fullInterfaceName)
        self.C_SourceFile.write("   }\n")

    def ExecuteBlock(self, unused_modelingLanguage: str, unused_asnFile: str, sp: ApLevelContainer, unused_subProgramImplementation: str, unused_maybeFVname: str) -> None:
        fullInterfaceName = ''
        if sp._simulinkInterfaceType == "full":
            fullInterfaceName = self.CleanNameAsADAWants(sp._id)
        else:
            fullInterfaceName = self.CleanNameAsADAWants(sp._simulinkFullInterfaceRef)

        self.C_SourceFile.write("    qgen_entry_%s_comp(&cInput, &cOutput);\n" % fullInterfaceName)


qgencBackend: QGenCGlueGenerator


def OnStartup(modelingLanguage: str, asnFile: str, subProgram: ApLevelContainer, subProgramImplementation: str, outputDir: str, maybeFVname: str) -> None:
    global qgencBackend
    qgencBackend = QGenCGlueGenerator()
    qgencBackend.OnStartup(modelingLanguage, asnFile, subProgram, subProgramImplementation, outputDir, maybeFVname)


def OnBasic(nodeTypename: str, node: AsnNode, subProgram: ApLevelContainer, subProgramImplementation: str, param: Param, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> None:
    qgencBackend.OnBasic(nodeTypename, node, subProgram, subProgramImplementation, param, leafTypeDict, names)


def OnSequence(nodeTypename: str, node: AsnNode, subProgram: ApLevelContainer, subProgramImplementation: str, param: Param, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> None:
    qgencBackend.OnSequence(nodeTypename, node, subProgram, subProgramImplementation, param, leafTypeDict, names)


def OnSet(nodeTypename: str, node: AsnNode, subProgram: ApLevelContainer, subProgramImplementation: str, param: Param, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> None:
    qgencBackend.OnSet(nodeTypename, node, subProgram, subProgramImplementation, param, leafTypeDict, names)  # pragma: nocover


def OnEnumerated(nodeTypename: str, node: AsnNode, subProgram: ApLevelContainer, subProgramImplementation: str, param: Param, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> None:
    qgencBackend.OnEnumerated(nodeTypename, node, subProgram, subProgramImplementation, param, leafTypeDict, names)


def OnSequenceOf(nodeTypename: str, node: AsnNode, subProgram: ApLevelContainer, subProgramImplementation: str, param: Param, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> None:
    qgencBackend.OnSequenceOf(nodeTypename, node, subProgram, subProgramImplementation, param, leafTypeDict, names)


def OnSetOf(nodeTypename: str, node: AsnNode, subProgram: ApLevelContainer, subProgramImplementation: str, param: Param, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> None:
    qgencBackend.OnSetOf(nodeTypename, node, subProgram, subProgramImplementation, param, leafTypeDict, names)  # pragma: nocover


def OnChoice(nodeTypename: str, node: AsnNode, subProgram: ApLevelContainer, subProgramImplementation: str, param: Param, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> None:
    qgencBackend.OnChoice(nodeTypename, node, subProgram, subProgramImplementation, param, leafTypeDict, names)


def OnShutdown(modelingLanguage: str, asnFile: str, sp: ApLevelContainer, subProgramImplementation: str, maybeFVname: str) -> None:
    qgencBackend.OnShutdown(modelingLanguage, asnFile, sp, subProgramImplementation, maybeFVname)
