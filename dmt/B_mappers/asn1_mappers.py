import os
import re
import math

from typing import cast, Union, List, Tuple, IO, Any, Dict  # NOQA pylint: disable=unused-import

from ..commonPy.utility import panic, panicWithCallStack
from ..commonPy.asnAST import (
    AsnBasicNode, AsnInt, AsnSequence, AsnSet, AsnChoice, AsnSequenceOf,
    AsnSetOf, AsnEnumerated, AsnMetaMember, isSequenceVariable,
    AsnNode, AsnString, AsnReal, AsnOctetString,
    AsnSequenceOrSetOf, AsnSequenceOrSet, AsnBool)
from ..commonPy.asnParser import AST_Lookup, AST_Leaftypes
from ..commonPy.aadlAST import (
    InParam, OutParam, AadlPort, AadlParameter,
)
from ..commonPy.aadlAST import Param, ApLevelContainer  # NOQA pylint: disable=unused-import
from ..commonPy import asnParser

from ..commonPy.recursiveMapper import RecursiveMapperGeneric
from .synchronousTool import SynchronousToolGlueGeneratorGeneric

def CleanName(name: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_]', '_', name)

class MapASN1ToVHDLCircuit(RecursiveMapperGeneric[str, str]):
    def MapInteger(self, direction: str, dstVHDL: str, node: AsnInt, _: AST_Leaftypes, __: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("INTEGERs need explicit ranges when generating VHDL code... (%s)" % node.Location())  # pragma: no cover
        bits = math.log(max(abs(x) for x in node._range) + 1, 2)
        bits += bits if node._range[0] < 0 else 0
        return [dstVHDL + ' : ' + direction + ('std_logic_vector(63 downto 0); -- ASSERT uses 64 bit INTEGERs (optimal would be %d bits)' % bits)]

    def MapReal(self, direction: str, dstVHDL: str, unused_node: AsnReal, ___: AST_Leaftypes, dummy: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return [dstVHDL + ' : ' + direction + ('std_logic_vector(63 downto 0);')]

    def MapBoolean(self, direction: str, dstVHDL: str, _: AsnBool, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return [dstVHDL + ' : ' + direction + 'std_logic_vector(7 downto 0);']

    def MapOctetString(self, direction: str, dstVHDL: str, node: AsnOctetString, _: AST_Leaftypes, __: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("OCTET STRING (in %s) must have a SIZE constraint inside ASN.1,\nor else we can't generate C code!" % node.Location())  # pragma: no cover
        if len(node._range) > 1 and node._range[0] != node._range[1]:
            panicWithCallStack("VHDL OCTET STRING (in %s) must have a fixed SIZE constraint !" % node.Location())  # pragma: no cover
        maxlen = len(str(node._range[-1]))
        lines = []  # type: List[str]
        for i in range(node._range[-1]):
            lines.append(dstVHDL + ('_elem_%0*d: ' % (maxlen, i)) + direction + 'std_logic_vector(7 downto 0);')
        return lines

    def MapEnumerated(self, direction: str, dstVHDL: str, _: AsnEnumerated, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return [dstVHDL + ' : ' + direction + 'std_logic_vector(7 downto 0);']

    def MapSequence(self, direction: str, dstVHDL: str, node: Union[AsnSequenceOrSet, AsnChoice], leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        lines = []  # type: List[str]
        for x in node._members:
            lines.extend(self.Map(direction, dstVHDL + "_" + CleanName(x[0]), x[1], leafTypeDict, names))
        return lines

    def MapSet(self, direction: str, dstVHDL: str, node: AsnSequenceOrSet, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return self.MapSequence(direction, dstVHDL, node, leafTypeDict, names)  # pragma: nocover

    def MapChoice(self, direction: str, dstVHDL: str, node: AsnChoice, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        lines = []  # type: List[str]
        lines.append(dstVHDL + '_choiceIdx : ' + direction + 'std_logic_vector(7 downto 0);')
        lines.extend(self.MapSequence(direction, dstVHDL, node, leafTypeDict, names))
        return lines

    def MapSequenceOf(self, direction: str, dstVHDL: str, node: AsnSequenceOrSetOf, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("For VHDL, a SIZE constraint is mandatory (%s)!\n" % node.Location())  # pragma: no cover
        if len(node._range) > 1 and node._range[0] != node._range[1]:
            panicWithCallStack("Must have a fixed SIZE constraint (in %s) for VHDL code!" % node.Location())  # pragma: no cover
        maxlen = len(str(node._range[-1]))
        lines = []  # type: List[str]
        for i in range(node._range[-1]):
            lines.extend(self.Map(
                direction, dstVHDL + ('_elem_%0*d' % (maxlen, i)), node._containedType, leafTypeDict, names))
        return lines

    def MapSetOf(self, direction: str, dstVHDL: str, node: AsnSequenceOrSetOf, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return self.MapSequenceOf(direction, dstVHDL, node, leafTypeDict, names)  # pragma: nocover


# pylint: disable=no-self-use


# pylint: disable=no-self-use
# class MapASN1ToVHDLinput(RecursiveMapperGeneric[str, str]):
#     def MapInteger(self, _: str, dstVHDL: str, node: AsnInt, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
#         if not node._range:
#             panicWithCallStack("INTEGERs need explicit ranges when generating VHDL code... (%s)" % node.Location())  # pragma: no cover
#         bits = math.log(max(abs(x) for x in node._range) + 1, 2)
#         bits += (bits if node._range[0] < 0 else 0)
#         return ['' + dstVHDL + ' : ' + ('std_logic_vector(63 downto 0); -- ASSERT uses 64 bit INTEGERs (optimal would be %d bits)' % bits)]

#     def MapReal(self, _: str, dstVHDL: str, unused_node: AsnReal, ___: AST_Leaftypes, dummy: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
#         return ['' + dstVHDL + ' : ' + ('std_logic_vector(63 downto 0);')]

#     def MapBoolean(self, _: str, dstVHDL: str, __: AsnBool, ___: AST_Leaftypes, dummy: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
#         return ['' + dstVHDL + ' : ' + 'std_logic_vector(7 downto 0);']

#     def MapOctetString(self, _: str, dstVHDL: str, node: AsnOctetString, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
#         if not node._range:
#             panicWithCallStack("OCTET STRING (in %s) must have a SIZE constraint inside ASN.1,\nor else we can't generate C code!" % node.Location())  # pragma: no cover
#         if len(node._range) > 1 and node._range[0] != node._range[1]:
#             panicWithCallStack("VHDL OCTET STRING (in %s) must have a fixed SIZE constraint !" % node.Location())  # pragma: no cover
#         maxlen = len(str(node._range[-1]))
#         lines = []  # type: List[str]
#         for i in range(node._range[-1]):
#             lines.append('' + dstVHDL + ('_elem_%0*d: ' % (maxlen, i)) + 'std_logic_vector(7 downto 0);')
#         return lines

#     def MapEnumerated(self, _: str, dstVHDL: str, __: AsnEnumerated, ___: AST_Leaftypes, dummy: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
#         return ['' + dstVHDL + ' : ' + 'std_logic_vector(7 downto 0);']

#     def MapSequence(self, _: str, dstVHDL: str, node: Union[AsnSequenceOrSet, AsnChoice], leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
#         lines = []  # type: List[str]
#         for x in node._members:
#             lines.extend(self.Map(_, dstVHDL + "_" + CleanName(x[0]), x[1], leafTypeDict, names))
#         return lines

#     def MapSet(self, _: str, dstVHDL: str, node: AsnSequenceOrSet, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
#         return self.MapSequence(_, dstVHDL, node, leafTypeDict, names)  # pragma: nocover

#     def MapChoice(self, _: str, dstVHDL: str, node: AsnChoice, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
#         lines = []  # type: List[str]
#         lines.append('' + dstVHDL + '_choiceIdx : ' + 'std_logic_vector(7 downto 0);')
#         lines.extend(self.MapSequence(_, dstVHDL, node, leafTypeDict, names))
#         return lines

#     def MapSequenceOf(self, _: str, dstVHDL: str, node: AsnSequenceOrSetOf, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
#         if not node._range:
#             panicWithCallStack("For VHDL, a SIZE constraint is mandatory (%s)!\n" % node.Location())  # pragma: no cover
#         if len(node._range) > 1 and node._range[0] != node._range[1]:
#             panicWithCallStack("Must have a fixed SIZE constraint (in %s) for VHDL code!" % node.Location())  # pragma: no cover
#         maxlen = len(str(node._range[-1]))
#         lines = []  # type: List[str]
#         for i in range(node._range[-1]):
#             lines.extend(self.Map(
#                 _, dstVHDL + ('_elem_%0*d' % (maxlen, i)), node._containedType, leafTypeDict, names))
#         return lines

#     def MapSetOf(self, _: str, dstVHDL: str, node: AsnSequenceOrSetOf, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
#         return self.MapSequenceOf(_, dstVHDL, node, leafTypeDict, names)  # pragma: nocover


# pylint: disable=no-self-use
# class MapASN1ToVHDLinputassign(RecursiveMapperGeneric[str, str]):
#     def MapInteger(self, _: str, dstVHDL: str, node: AsnInt, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
#         if not node._range:
#             panicWithCallStack("INTEGERs need explicit ranges when generating VHDL code... (%s)" % node.Location())  # pragma: no cover
#         bits = math.log(max(abs(x) for x in node._range) + 1, 2)
#         bits += (bits if node._range[0] < 0 else 0)
#         return ['' + dstVHDL + ' => (others => \'0\'),']

#     def MapReal(self, _: str, dstVHDL: str, unused_node: AsnReal, ___: AST_Leaftypes, dummy: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
#         return ['' + dstVHDL + ' => (others => \'0\'),']

#     def MapBoolean(self, _: str, dstVHDL: str, __: AsnBool, ___: AST_Leaftypes, dummy: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
#         return ['' + dstVHDL + ' => (others => \'0\'),']

#     def MapOctetString(self, _: str, dstVHDL: str, node: AsnOctetString, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
#         if not node._range:
#             panicWithCallStack("OCTET STRING (in %s) must have a SIZE constraint inside ASN.1,\nor else we can't generate C code!" % node.Location())  # pragma: no cover
#         if len(node._range) > 1 and node._range[0] != node._range[1]:
#             panicWithCallStack("VHDL OCTET STRING (in %s) must have a fixed SIZE constraint !" % node.Location())  # pragma: no cover
#         maxlen = len(str(node._range[-1]))
#         lines = []  # type: List[str]
#         for i in range(node._range[-1]):
#             lines.append('' + dstVHDL + ('_elem_%0*d' % (maxlen, i)) + ' => (others => \'0\'),')
#         return lines

#     def MapEnumerated(self, _: str, dstVHDL: str, __: AsnEnumerated, ___: AST_Leaftypes, dummy: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
#         return ['' + dstVHDL + ' => (others => \'0\'),']

#     def MapSequence(self, _: str, dstVHDL: str, node: Union[AsnSequenceOrSet, AsnChoice], leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
#         lines = []  # type: List[str]
#         for x in node._members:
#             lines.extend(self.Map(_, dstVHDL + "_" + CleanName(x[0]), x[1], leafTypeDict, names))
#         return lines

#     def MapSet(self, _: str, dstVHDL: str, node: AsnSequenceOrSet, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
#         return self.MapSequence(_, dstVHDL, node, leafTypeDict, names)  # pragma: nocover

#     def MapChoice(self, _: str, dstVHDL: str, node: AsnChoice, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
#         lines = []  # type: List[str]
#         lines.append('' + dstVHDL + '_choiceIdx' + ' => (others => \'0\'),')
#         lines.extend(self.MapSequence(_, dstVHDL, node, leafTypeDict, names))
#         return lines

#     def MapSequenceOf(self, _: str, dstVHDL: str, node: AsnSequenceOrSetOf, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
#         if not node._range:
#             panicWithCallStack("For VHDL, a SIZE constraint is mandatory (%s)!\n" % node.Location())  # pragma: no cover
#         if len(node._range) > 1 and node._range[0] != node._range[1]:
#             panicWithCallStack("Must have a fixed SIZE constraint (in %s) for VHDL code!" % node.Location())  # pragma: no cover
#         maxlen = len(str(node._range[-1]))
#         lines = []  # type: List[str]
#         for i in range(node._range[-1]):
#             lines.extend(self.Map(
#                 _, dstVHDL + ('_elem_%0*d' % (maxlen, i)), node._containedType, leafTypeDict, names))
#         return lines

#     def MapSetOf(self, _: str, dstVHDL: str, node: AsnSequenceOrSetOf, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
#         return self.MapSequenceOf(_, dstVHDL, node, leafTypeDict, names)  # pragma: nocover


# pylint: disable=no-self-use
class MapASN1ToVHDLinputRegisters(RecursiveMapperGeneric[str, str]):
    def MapInteger(self, _: str, dstVHDL: str, node: AsnInt, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("INTEGERs need explicit ranges when generating VHDL code... (%s)" % node.Location())  # pragma: no cover
        bits = math.log(max(abs(x) for x in node._range) + 1, 2)
        bits += (bits if node._range[0] < 0 else 0)
        return ['signal ' + dstVHDL + '_reg_d' + ', ' + dstVHDL + '_reg_q' + ' : ' + ('std_logic_vector(31 downto 0); -- ASSERT uses 64 bit INTEGERs (optimal would be %d bits)' % bits)]

    def MapReal(self, _: str, dstVHDL: str, unused_node: AsnReal, ___: AST_Leaftypes, dummy: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return ['signal ' + dstVHDL + ' : ' + ('std_logic_vector(63 downto 0);')]

    def MapBoolean(self, _: str, dstVHDL: str, __: AsnBool, ___: AST_Leaftypes, dummy: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return ['signal ' + dstVHDL + ' : ' + 'std_logic_vector(7 downto 0);']

    def MapOctetString(self, _: str, dstVHDL: str, node: AsnOctetString, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("OCTET STRING (in %s) must have a SIZE constraint inside ASN.1,\nor else we can't generate C code!" % node.Location())  # pragma: no cover
        if len(node._range) > 1 and node._range[0] != node._range[1]:
            panicWithCallStack("VHDL OCTET STRING (in %s) must have a fixed SIZE constraint !" % node.Location())  # pragma: no cover
        maxlen = len(str(node._range[-1]))
        lines = []  # type: List[str]
        for i in range(node._range[-1]):
            lines.append('' + dstVHDL + ('_elem_%0*d: ' % (maxlen, i)) + 'std_logic_vector(7 downto 0);')
        return lines

    def MapEnumerated(self, _: str, dstVHDL: str, __: AsnEnumerated, ___: AST_Leaftypes, dummy: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return ['signal ' + dstVHDL + ' : ' + 'std_logic_vector(7 downto 0);']

    def MapSequence(self, _: str, dstVHDL: str, node: Union[AsnSequenceOrSet, AsnChoice], leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        lines = []  # type: List[str]
        for x in node._members:
            lines.extend(self.Map(_, dstVHDL + "_" + CleanName(x[0]), x[1], leafTypeDict, names))
        return lines

    def MapSet(self, _: str, dstVHDL: str, node: AsnSequenceOrSet, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return self.MapSequence(_, dstVHDL, node, leafTypeDict, names)  # pragma: nocover

    def MapChoice(self, _: str, dstVHDL: str, node: AsnChoice, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        lines = []  # type: List[str]
        lines.append('signal ' + dstVHDL + '_choiceIdx : ' + 'std_logic_vector(7 downto 0);')
        lines.extend(self.MapSequence(_, dstVHDL, node, leafTypeDict, names))
        return lines

    def MapSequenceOf(self, _: str, dstVHDL: str, node: AsnSequenceOrSetOf, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("For VHDL, a SIZE constraint is mandatory (%s)!\n" % node.Location())  # pragma: no cover
        if len(node._range) > 1 and node._range[0] != node._range[1]:
            panicWithCallStack("Must have a fixed SIZE constraint (in %s) for VHDL code!" % node.Location())  # pragma: no cover
        maxlen = len(str(node._range[-1]))
        lines = []  # type: List[str]
        for i in range(node._range[-1]):
            lines.extend(self.Map(
                _, dstVHDL + ('_elem_%0*d' % (maxlen, i)), node._containedType, leafTypeDict, names))
        return lines

    def MapSetOf(self, _: str, dstVHDL: str, node: AsnSequenceOrSetOf, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return self.MapSequenceOf(_, dstVHDL, node, leafTypeDict, names)  # pragma: nocover

class MapASN1ToVHDLoutputRegisters(RecursiveMapperGeneric[str, str]):
    def MapInteger(self, _: str, dstVHDL: str, node: AsnInt, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("INTEGERs need explicit ranges when generating VHDL code... (%s)" % node.Location())  # pragma: no cover
        bits = math.log(max(abs(x) for x in node._range) + 1, 2)
        bits += (bits if node._range[0] < 0 else 0)
        return ['signal ' + dstVHDL + '_reg_d' + ', ' + dstVHDL + '_reg_q' + ' : ' + ('std_logic_vector(63 downto 0); -- ASSERT uses 64 bit INTEGERs (optimal would be %d bits)' % bits)]

    def MapReal(self, _: str, dstVHDL: str, unused_node: AsnReal, ___: AST_Leaftypes, dummy: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return ['signal ' + dstVHDL + ' : ' + ('std_logic_vector(63 downto 0);')]

    def MapBoolean(self, _: str, dstVHDL: str, __: AsnBool, ___: AST_Leaftypes, dummy: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return ['signal ' + dstVHDL + ' : ' + 'std_logic_vector(7 downto 0);']

    def MapOctetString(self, _: str, dstVHDL: str, node: AsnOctetString, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("OCTET STRING (in %s) must have a SIZE constraint inside ASN.1,\nor else we can't generate C code!" % node.Location())  # pragma: no cover
        if len(node._range) > 1 and node._range[0] != node._range[1]:
            panicWithCallStack("VHDL OCTET STRING (in %s) must have a fixed SIZE constraint !" % node.Location())  # pragma: no cover
        maxlen = len(str(node._range[-1]))
        lines = []  # type: List[str]
        for i in range(node._range[-1]):
            lines.append('' + dstVHDL + ('_elem_%0*d: ' % (maxlen, i)) + 'std_logic_vector(7 downto 0);')
        return lines

    def MapEnumerated(self, _: str, dstVHDL: str, __: AsnEnumerated, ___: AST_Leaftypes, dummy: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return ['signal ' + dstVHDL + ' : ' + 'std_logic_vector(7 downto 0);']

    def MapSequence(self, _: str, dstVHDL: str, node: Union[AsnSequenceOrSet, AsnChoice], leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        lines = []  # type: List[str]
        for x in node._members:
            lines.extend(self.Map(_, dstVHDL + "_" + CleanName(x[0]), x[1], leafTypeDict, names))
        return lines

    def MapSet(self, _: str, dstVHDL: str, node: AsnSequenceOrSet, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return self.MapSequence(_, dstVHDL, node, leafTypeDict, names)  # pragma: nocover

    def MapChoice(self, _: str, dstVHDL: str, node: AsnChoice, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        lines = []  # type: List[str]
        lines.append('signal ' + dstVHDL + '_choiceIdx : ' + 'std_logic_vector(7 downto 0);')
        lines.extend(self.MapSequence(_, dstVHDL, node, leafTypeDict, names))
        return lines

    def MapSequenceOf(self, _: str, dstVHDL: str, node: AsnSequenceOrSetOf, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("For VHDL, a SIZE constraint is mandatory (%s)!\n" % node.Location())  # pragma: no cover
        if len(node._range) > 1 and node._range[0] != node._range[1]:
            panicWithCallStack("Must have a fixed SIZE constraint (in %s) for VHDL code!" % node.Location())  # pragma: no cover
        maxlen = len(str(node._range[-1]))
        lines = []  # type: List[str]
        for i in range(node._range[-1]):
            lines.extend(self.Map(
                _, dstVHDL + ('_elem_%0*d' % (maxlen, i)), node._containedType, leafTypeDict, names))
        return lines

    def MapSetOf(self, _: str, dstVHDL: str, node: AsnSequenceOrSetOf, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return self.MapSequenceOf(_, dstVHDL, node, leafTypeDict, names)  # pragma: nocover

class MapASN1ToVHDLinternalOutputSignals(RecursiveMapperGeneric[str, str]):
    def MapInteger(self, _: str, dstVHDL: str, node: AsnInt, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("INTEGERs need explicit ranges when generating VHDL code... (%s)" % node.Location())  # pragma: no cover
        bits = math.log(max(abs(x) for x in node._range) + 1, 2)
        bits += (bits if node._range[0] < 0 else 0)
        return ['signal ' + 'int_' + dstVHDL + ' : ' + ('std_logic_vector(63 downto 0);')]


    def MapReal(self, _: str, dstVHDL: str, unused_node: AsnReal, ___: AST_Leaftypes, dummy: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return ['signal ' + dstVHDL + ' : ' + ('std_logic_vector(63 downto 0);')]

    def MapBoolean(self, _: str, dstVHDL: str, __: AsnBool, ___: AST_Leaftypes, dummy: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return ['signal ' + dstVHDL + ' : ' + 'std_logic_vector(7 downto 0);']

    def MapOctetString(self, _: str, dstVHDL: str, node: AsnOctetString, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("OCTET STRING (in %s) must have a SIZE constraint inside ASN.1,\nor else we can't generate C code!" % node.Location())  # pragma: no cover
        if len(node._range) > 1 and node._range[0] != node._range[1]:
            panicWithCallStack("VHDL OCTET STRING (in %s) must have a fixed SIZE constraint !" % node.Location())  # pragma: no cover
        maxlen = len(str(node._range[-1]))
        lines = []  # type: List[str]
        for i in range(node._range[-1]):
            lines.append('' + dstVHDL + ('_elem_%0*d: ' % (maxlen, i)) + 'std_logic_vector(7 downto 0);')
        return lines

    def MapEnumerated(self, _: str, dstVHDL: str, __: AsnEnumerated, ___: AST_Leaftypes, dummy: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return ['signal ' + dstVHDL + ' : ' + 'std_logic_vector(7 downto 0);']

    def MapSequence(self, _: str, dstVHDL: str, node: Union[AsnSequenceOrSet, AsnChoice], leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        lines = []  # type: List[str]
        for x in node._members:
            lines.extend(self.Map(_, dstVHDL + "_" + CleanName(x[0]), x[1], leafTypeDict, names))
        return lines

    def MapSet(self, _: str, dstVHDL: str, node: AsnSequenceOrSet, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return self.MapSequence(_, dstVHDL, node, leafTypeDict, names)  # pragma: nocover

    def MapChoice(self, _: str, dstVHDL: str, node: AsnChoice, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        lines = []  # type: List[str]
        lines.append('signal ' + dstVHDL + '_choiceIdx : ' + 'std_logic_vector(7 downto 0);')
        lines.extend(self.MapSequence(_, dstVHDL, node, leafTypeDict, names))
        return lines

    def MapSequenceOf(self, _: str, dstVHDL: str, node: AsnSequenceOrSetOf, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("For VHDL, a SIZE constraint is mandatory (%s)!\n" % node.Location())  # pragma: no cover
        if len(node._range) > 1 and node._range[0] != node._range[1]:
            panicWithCallStack("Must have a fixed SIZE constraint (in %s) for VHDL code!" % node.Location())  # pragma: no cover
        maxlen = len(str(node._range[-1]))
        lines = []  # type: List[str]
        for i in range(node._range[-1]):
            lines.extend(self.Map(
                _, dstVHDL + ('_elem_%0*d' % (maxlen, i)), node._containedType, leafTypeDict, names))
        return lines

    def MapSetOf(self, _: str, dstVHDL: str, node: AsnSequenceOrSetOf, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return self.MapSequenceOf(_, dstVHDL, node, leafTypeDict, names)  # pragma: nocover


class MapASN1ToVHDLinternalSignals(RecursiveMapperGeneric[str, str]):
    def MapInteger(self, _: str, dstVHDL: str, node: AsnInt, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("INTEGERs need explicit ranges when generating VHDL code... (%s)" % node.Location())  # pragma: no cover
        bits = math.log(max(abs(x) for x in node._range) + 1, 2)
        bits += (bits if node._range[0] < 0 else 0)
        return ['' + dstVHDL + ' <= AXI_SLAVE_CTRL_r.' + dstVHDL + ';\n']

    def MapReal(self, _: str, dstVHDL: str, unused_node: AsnReal, ___: AST_Leaftypes, dummy: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return ['' + dstVHDL + ' <= AXI_SLAVE_CTRL_r.' + dstVHDL + ';\n']

    def MapBoolean(self, _: str, dstVHDL: str, __: AsnBool, ___: AST_Leaftypes, dummy: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return ['' + dstVHDL + ' <= AXI_SLAVE_CTRL_r.' + dstVHDL + ';\n']

    def MapOctetString(self, _: str, dstVHDL: str, node: AsnOctetString, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("OCTET STRING (in %s) must have a SIZE constraint inside ASN.1,\nor else we can't generate C code!" % node.Location())  # pragma: no cover
        if len(node._range) > 1 and node._range[0] != node._range[1]:
            panicWithCallStack("VHDL OCTET STRING (in %s) must have a fixed SIZE constraint !" % node.Location())  # pragma: no cover
        maxlen = len(str(node._range[-1]))
        lines = []  # type: List[str]
        for i in range(node._range[-1]):
            lines.append('' + dstVHDL + ('_elem_%0*d' % (maxlen, i)) + ' <= AXI_SLAVE_CTRL_r.' + dstVHDL + ('_elem_%0*d' % (maxlen, i)) + ';\n')
        return lines

    def MapEnumerated(self, _: str, dstVHDL: str, __: AsnEnumerated, ___: AST_Leaftypes, dummy: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return ['' + dstVHDL + ' <= AXI_SLAVE_CTRL_r.' + dstVHDL + ';\n']

    def MapSequence(self, _: str, dstVHDL: str, node: Union[AsnSequenceOrSet, AsnChoice], leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        lines = []  # type: List[str]
        for x in node._members:
            lines.extend(self.Map(_, dstVHDL + "_" + CleanName(x[0]), x[1], leafTypeDict, names))
        return lines

    def MapSet(self, _: str, dstVHDL: str, node: AsnSequenceOrSet, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return self.MapSequence(_, dstVHDL, node, leafTypeDict, names)  # pragma: nocover

    def MapChoice(self, _: str, dstVHDL: str, node: AsnChoice, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        lines = []  # type: List[str]
        lines.append('' + dstVHDL + '_choiceIdx' + ' <= AXI_SLAVE_CTRL_r.' + dstVHDL + '_choiceIdx' + ';\n')
        lines.extend(self.MapSequence(_, dstVHDL, node, leafTypeDict, names))
        return lines

    def MapSequenceOf(self, _: str, dstVHDL: str, node: AsnSequenceOrSetOf, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("For VHDL, a SIZE constraint is mandatory (%s)!\n" % node.Location())  # pragma: no cover
        if len(node._range) > 1 and node._range[0] != node._range[1]:
            panicWithCallStack("Must have a fixed SIZE constraint (in %s) for VHDL code!" % node.Location())  # pragma: no cover
        maxlen = len(str(node._range[-1]))
        lines = []  # type: List[str]
        for i in range(node._range[-1]):
            lines.extend(self.Map(
                _, dstVHDL + ('_elem_%0*d' % (maxlen, i)), node._containedType, leafTypeDict, names))
        return lines

    def MapSetOf(self, _: str, dstVHDL: str, node: AsnSequenceOrSetOf, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return self.MapSequenceOf(_, dstVHDL, node, leafTypeDict, names)  # pragma: nocover

# pylint: disable=no-self-use
class MapASN1ToVHDLreadinputdata(RecursiveMapperGeneric[List[int], str]):  # pylint: disable=invalid-sequence-index
    def MapInteger(self, reginfo: List[int], dstVHDL: str, node: AsnInt, _: AST_Leaftypes, __: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("INTEGERs need explicit ranges when generating VHDL code... (%s)" % node.Location())  # pragma: no cover
        # bits = math.log(max(map(abs, node._range)+1),2)+(1 if node._range[0] < 0 else 0)
        lines = []  # type: List[str]
        lines.append('when (%s) => v.%s(31 downto  0) := S_AXI_WDATA;' % (reginfo[0], dstVHDL))
        lines.append('when (%s) => v.%s(63 downto  32) := S_AXI_WDATA;' % (reginfo[0] + 4, dstVHDL))
        reginfo[0] += 8
        return lines

    def MapReal(self, reginfo: List[int], dstVHDL: str, unused_node: AsnReal, ___: AST_Leaftypes, dummy: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        lines = []  # type: List[str]
        lines.append('when (%s) => v.%s(31 downto  0) := S_AXI_WDATA;' % (reginfo[0], dstVHDL))
        lines.append('when (%s) => v.%s(63 downto  32) := S_AXI_WDATA;' % (reginfo[0] + 4, dstVHDL))
        reginfo[0] += 8
        return lines

    def MapBoolean(self, reginfo: List[int], dstVHDL: str, _: AsnBool, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        lines = ['when X"%s" => %s(7 downto 0) <= axii.pwdata(7 downto 0);' % (hex(reginfo[0])[2:] if len(hex(reginfo[0])[2:]) > 3 else ('0' + hex(reginfo[0])[2:]), dstVHDL)]
        reginfo[0] += 4
        return lines

    def MapOctetString(self, reginfo: List[int], dstVHDL: str, node: AsnOctetString, _: AST_Leaftypes, __: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("OCTET STRING (in %s) must have a SIZE constraint inside ASN.1,\nor else we can't generate C code!" % node.Location())  # pragma: no cover
        if len(node._range) > 1 and node._range[0] != node._range[1]:
            panicWithCallStack("VHDL OCTET STRING (in %s) must have a fixed SIZE constraint !" % node.Location())  # pragma: no cover
        if node._range[-1] % 4 != 0:  # TODO
            panicWithCallStack("OCTET STRING (in %s) is not a multiple of 4 bytes (this is not yet supported)." % node.Location())
        maxlen = len(str(node._range[-1]))
        lines = []  # type: List[str]
        for i in range(node._range[-1]):
            if (i) % 4 == 0:
                lines.append('when X"%s" => %s_elem_%0*d(7 downto 0) <= axii.pwdata(7 downto 0);' % (hex(reginfo[0])[2:] if len(hex(reginfo[0])[2:]) > 3 else ('0' + hex(reginfo[0])[2:]), dstVHDL, maxlen, i + 0))
                lines.append('                %s_elem_%0*d(7 downto 0) <= axii.pwdata(15 downto 8);' % (dstVHDL, maxlen, i + 1))
                lines.append('                %s_elem_%0*d(7 downto 0) <= axii.pwdata(23 downto 16);' % (dstVHDL, maxlen, i + 2))
                lines.append('                %s_elem_%0*d(7 downto 0) <= axii.pwdata(31 downto 24);' % (dstVHDL, maxlen, i + 3))
            reginfo[0] += 1
        return lines

    def MapEnumerated(self, reginfo: List[int], dstVHDL: str, _: AsnEnumerated, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        lines = ['when X"%s" => %s(7 downto 0) <= axii.pwdata(7 downto 0);' % (hex(reginfo[0])[2:] if len(hex(reginfo[0])[2:]) > 3 else ('0' + hex(reginfo[0])[2:]), dstVHDL)]
        reginfo[0] += 4
        return lines

    def MapSequence(self, reginfo: List[int], dstVHDL: str, node: Union[AsnSequenceOrSet, AsnChoice], leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        lines = []  # type: List[str]
        for x in node._members:
            lines.extend(self.Map(reginfo, dstVHDL + "_" + CleanName(x[0]), x[1], leafTypeDict, names))
        return lines

    def MapSet(self, reginfo: List[int], dstVHDL: str, node: AsnSequenceOrSet, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return self.MapSequence(reginfo, dstVHDL, node, leafTypeDict, names)  # pragma: nocover

    def MapChoice(self, reginfo: List[int], dstVHDL: str, node: AsnChoice, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        lines = ['when X"%s" => %s_choiceIdx(7 downto 0) <= axii.pwdata(7 downto 0);' % (hex(reginfo[0])[2:], dstVHDL)]
        reginfo[0] += 1
        lines.extend(self.MapSequence(reginfo, dstVHDL, node, leafTypeDict, names))
        return lines

    def MapSequenceOf(self, reginfo: List[int], dstVHDL: str, node: AsnSequenceOrSetOf, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("For VHDL, a SIZE constraint is mandatory (%s)!\n" % node.Location())  # pragma: no cover
        if len(node._range) > 1 and node._range[0] != node._range[1]:
            panicWithCallStack("Must have a fixed SIZE constraint (in %s) for VHDL code!" % node.Location())  # pragma: no cover
        maxlen = len(str(node._range[-1]))
        lines = []  # type: List[str]
        for i in range(node._range[-1]):
            lines.extend(self.Map(
                reginfo, dstVHDL + ('_elem_%0*d' % (maxlen, i)), node._containedType, leafTypeDict, names))
        return lines

    def MapSetOf(self, reginfo: List[int], dstVHDL: str, node: AsnSequenceOrSetOf, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return self.MapSequenceOf(reginfo, dstVHDL, node, leafTypeDict, names)


# pylint: disable=no-self-use
class MapASN1ToVHDLwriteoutputdata(RecursiveMapperGeneric[List[int], str]):  # pylint: disable=invalid-sequence-index
    def MapInteger(self, reginfo: List[int], dstVHDL: str, node: AsnInt, _: AST_Leaftypes, __: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("INTEGERs need explicit ranges when generating VHDL code... (%s)" % node.Location())  # pragma: no cover
        # bits = math.log(max(map(abs, node._range)+1),2)+(1 if node._range[0] < 0 else 0)
        lines = []  # type: List[str]
        lines.append('when (%s) => v_comb_out.rdata(31 downto 0) := %s(31 downto  0);' % (reginfo[0] + 0, dstVHDL))
        lines.append('when (%s) => v_comb_out.rdata(31 downto 0) := %s(63 downto  32);' % (reginfo[0] + 4, dstVHDL))
        reginfo[0] += 8
        return lines

    def MapReal(self, reginfo: List[int], dstVHDL: str, unused_node: AsnReal, ___: AST_Leaftypes, dummy: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        lines = []  # type: List[str]
        lines.append('when (%s) => v_comb_out.rdata(31 downto 0) := %s(31 downto  0);' % (reginfo[0] + 0, dstVHDL))
        lines.append('when (%s) => v_comb_out.rdata(31 downto 0) := %s(63 downto  32);' % (reginfo[0] + 4, dstVHDL))
        reginfo[0] += 8
        return lines

    def MapBoolean(self, reginfo: List[int], dstVHDL: str, _: AsnBool, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        lines = ['when X"%s" => axio.prdata(7 downto 0) <= %s(7 downto 0);' % (hex(reginfo[0])[2:] if len(hex(reginfo[0])[2:]) > 3 else ('0' + hex(reginfo[0])[2:]), dstVHDL)]
        reginfo[0] += 4
        return lines

    def MapOctetString(self, reginfo: List[int], dstVHDL: str, node: AsnOctetString, _: AST_Leaftypes, __: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("OCTET STRING (in %s) must have a SIZE constraint inside ASN.1,\nor else we can't generate C code!" % node.Location())  # pragma: no cover
        if len(node._range) > 1 and node._range[0] != node._range[1]:
            panicWithCallStack("VHDL OCTET STRING (in %s) must have a fixed SIZE constraint !" % node.Location())  # pragma: no cover
        if node._range[-1] % 4 != 0:  # TODO
            panicWithCallStack("OCTET STRING (in %s) is not a multiple of 4 bytes (this is not yet supported)." % node.Location())
        maxlen = len(str(node._range[-1]))
        lines = []  # type: List[str]
        for i in range(node._range[-1]):
            if (i) % 4 == 0:
                lines.append('when X"%s" => axio.prdata(7 downto 0) <= %s_elem_%0*d(7 downto 0);' % (hex(reginfo[0])[2:] if len(hex(reginfo[0])[2:]) > 3 else ('0' + hex(reginfo[0])[2:]), dstVHDL, maxlen, i + 0))
                lines.append('                axio.prdata(15 downto 8) <= %s_elem_%0*d(7 downto 0);' % (dstVHDL, maxlen, i + 1))
                lines.append('                axio.prdata(23 downto 16) <= %s_elem_%0*d(7 downto 0);' % (dstVHDL, maxlen, i + 2))
                lines.append('                axio.prdata(31 downto 24) <= %s_elem_%0*d(7 downto 0);' % (dstVHDL, maxlen, i + 3))
            reginfo[0] += 1
        return lines

    def MapEnumerated(self, reginfo: List[int], dstVHDL: str, _: AsnEnumerated, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        lines = ['when X"%s" => axio.prdata(7 downto 0) <= %s(7 downto 0);' % (hex(reginfo[0])[2:] if len(hex(reginfo[0])[2:]) > 3 else ('0' + hex(reginfo[0])[2:]), dstVHDL)]
        reginfo[0] += 4
        return lines

    def MapSequence(self, reginfo: List[int], dstVHDL: str, node: Union[AsnSequenceOrSet, AsnChoice], leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        lines = []  # type: List[str]
        for x in node._members:
            lines.extend(self.Map(reginfo, dstVHDL + "_" + CleanName(x[0]), x[1], leafTypeDict, names))
        return lines

    def MapSet(self, reginfo: List[int], dstVHDL: str, node: AsnSequenceOrSet, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return self.MapSequence(reginfo, dstVHDL, node, leafTypeDict, names)

    def MapChoice(self, reginfo: List[int], dstVHDL: str, node: AsnChoice, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        lines = ['when X"%s" => axio.prdata(7 downto 0) <= %s_choiceIdx(7 downto 0);' % (hex(reginfo[0])[2:], dstVHDL)]
        reginfo[0] += 1
        lines.extend(self.MapSequence(reginfo, dstVHDL, node, leafTypeDict, names))
        return lines

    def MapSequenceOf(self, reginfo: List[int], dstVHDL: str, node: AsnSequenceOrSetOf, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("For VHDL, a SIZE constraint is mandatory (%s)!\n" % node.Location())  # pragma: no cover
        if len(node._range) > 1 and node._range[0] != node._range[1]:
            panicWithCallStack("Must have a fixed SIZE constraint (in %s) for VHDL code!" % node.Location())  # pragma: no cover
        maxlen = len(str(node._range[-1]))
        lines = []  # type: List[str]
        for i in range(node._range[-1]):
            lines.extend(self.Map(
                reginfo, dstVHDL + ('_elem_%0*d' % (maxlen, i)), node._containedType, leafTypeDict, names))
        return lines

    def MapSetOf(self, reginfo: List[int], dstVHDL: str, node: AsnSequenceOrSetOf, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return self.MapSequenceOf(reginfo, dstVHDL, node, leafTypeDict, names)  # pragma: nocover


# pylint: disable=no-self-use
class MapASN1ToVHDLinputIPconnections(RecursiveMapperGeneric[str, str]):
    def MapInteger(self, srcRegister: str, dstCircuitPort: str, _: AsnInt, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        # Need to set different value for output signal
        return [dstCircuitPort + ' => ' + 'X"00000000" & ' + srcRegister + '_reg_q']
            

    def MapReal(self, srcRegister: str, dstCircuitPort: str, unused_node: AsnReal, ___: AST_Leaftypes, dummy: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return [dstCircuitPort + ' => ' + srcRegister]

    def MapBoolean(self, srcRegister: str, dstCircuitPort: str, __: AsnBool, ___: AST_Leaftypes, dummy: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return [dstCircuitPort + ' => ' + srcRegister]

    def MapOctetString(self, srcRegister: str, dstCircuitPort: str, node: AsnOctetString, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("OCTET STRING (in %s) must have a SIZE constraint inside ASN.1,\nor else we can't generate C code!" % node.Location())  # pragma: no cover
        if len(node._range) > 1 and node._range[0] != node._range[1]:
            panicWithCallStack("VHDL OCTET STRING (in %s) must have a fixed SIZE constraint !" % node.Location())  # pragma: no cover
        maxlen = len(str(node._range[-1]))
        lines = []  # type: List[str]
        for i in range(node._range[-1]):
            lines.append(dstCircuitPort + ('_elem_%0*d' % (maxlen, i)) + ' => ' + srcRegister + ('_elem_%0*d' % (maxlen, i)))
        return lines

    def MapEnumerated(self, srcRegister: str, dstCircuitPort: str, __: AsnEnumerated, ___: AST_Leaftypes, dummy: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return [dstCircuitPort + ' => ' + srcRegister]

    def MapSequence(self, srcRegister: str, dstCircuitPort: str, node: Union[AsnSequenceOrSet, AsnChoice], leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        lines = []  # type: List[str]
        for x in node._members:
            lines.extend(self.Map(srcRegister + "_" + CleanName(x[0]), dstCircuitPort + "_" + CleanName(x[0]), x[1], leafTypeDict, names))
        return lines

    def MapSet(self, srcRegister: str, dstCircuitPort: str, node: AsnSequenceOrSet, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return self.MapSequence(srcRegister, dstCircuitPort, node, leafTypeDict, names)  # pragma: nocover

    def MapChoice(self, srcRegister: str, dstCircuitPort: str, node: AsnChoice, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        lines = []  # type: List[str]
        lines.append(dstCircuitPort + '_choiceIdx => ' + srcRegister + '_choiceIdx')
        lines.extend(self.MapSequence(srcRegister, dstCircuitPort, node, leafTypeDict, names))
        return lines

    def MapSequenceOf(self, srcRegister: str, dstCircuitPort: str, node: AsnSequenceOrSetOf, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("For VHDL, a SIZE constraint is mandatory (%s)!\n" % node.Location())  # pragma: no cover
        if len(node._range) > 1 and node._range[0] != node._range[1]:
            panicWithCallStack("Must have a fixed SIZE constraint (in %s) for VHDL code!" % node.Location())  # pragma: no cover
        maxlen = len(str(node._range[-1]))
        lines = []  # type: List[str]
        for i in range(node._range[-1]):
            lines.extend(self.Map(
                srcRegister + ('_elem_%0*d' % (maxlen, i)), dstCircuitPort + ('_elem_%0*d' % (maxlen, i)), node._containedType, leafTypeDict, names))
        return lines

    def MapSetOf(self, srcRegister: str, dstCircuitPort: str, node: AsnSequenceOrSetOf, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return self.MapSequenceOf(srcRegister, dstCircuitPort, node, leafTypeDict, names)

class MapASN1ToVHDLoutputIPconnections(RecursiveMapperGeneric[str, str]):
    def MapInteger(self, srcRegister: str, dstCircuitPort: str, _: AsnInt, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        # Need to set different value for output signal
        return [dstCircuitPort + ' => ' + 'int_' + dstCircuitPort]
            

    def MapReal(self, srcRegister: str, dstCircuitPort: str, unused_node: AsnReal, ___: AST_Leaftypes, dummy: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return [dstCircuitPort + ' => ' + srcRegister]

    def MapBoolean(self, srcRegister: str, dstCircuitPort: str, __: AsnBool, ___: AST_Leaftypes, dummy: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return [dstCircuitPort + ' => ' + srcRegister]

    def MapOctetString(self, srcRegister: str, dstCircuitPort: str, node: AsnOctetString, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("OCTET STRING (in %s) must have a SIZE constraint inside ASN.1,\nor else we can't generate C code!" % node.Location())  # pragma: no cover
        if len(node._range) > 1 and node._range[0] != node._range[1]:
            panicWithCallStack("VHDL OCTET STRING (in %s) must have a fixed SIZE constraint !" % node.Location())  # pragma: no cover
        maxlen = len(str(node._range[-1]))
        lines = []  # type: List[str]
        for i in range(node._range[-1]):
            lines.append(dstCircuitPort + ('_elem_%0*d' % (maxlen, i)) + ' => ' + srcRegister + ('_elem_%0*d' % (maxlen, i)))
        return lines

    def MapEnumerated(self, srcRegister: str, dstCircuitPort: str, __: AsnEnumerated, ___: AST_Leaftypes, dummy: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return [dstCircuitPort + ' => ' + srcRegister]

    def MapSequence(self, srcRegister: str, dstCircuitPort: str, node: Union[AsnSequenceOrSet, AsnChoice], leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        lines = []  # type: List[str]
        for x in node._members:
            lines.extend(self.Map(srcRegister + "_" + CleanName(x[0]), dstCircuitPort + "_" + CleanName(x[0]), x[1], leafTypeDict, names))
        return lines

    def MapSet(self, srcRegister: str, dstCircuitPort: str, node: AsnSequenceOrSet, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return self.MapSequence(srcRegister, dstCircuitPort, node, leafTypeDict, names)  # pragma: nocover

    def MapChoice(self, srcRegister: str, dstCircuitPort: str, node: AsnChoice, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        lines = []  # type: List[str]
        lines.append(dstCircuitPort + '_choiceIdx => ' + srcRegister + '_choiceIdx')
        lines.extend(self.MapSequence(srcRegister, dstCircuitPort, node, leafTypeDict, names))
        return lines

    def MapSequenceOf(self, srcRegister: str, dstCircuitPort: str, node: AsnSequenceOrSetOf, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("For VHDL, a SIZE constraint is mandatory (%s)!\n" % node.Location())  # pragma: no cover
        if len(node._range) > 1 and node._range[0] != node._range[1]:
            panicWithCallStack("Must have a fixed SIZE constraint (in %s) for VHDL code!" % node.Location())  # pragma: no cover
        maxlen = len(str(node._range[-1]))
        lines = []  # type: List[str]
        for i in range(node._range[-1]):
            lines.extend(self.Map(
                srcRegister + ('_elem_%0*d' % (maxlen, i)), dstCircuitPort + ('_elem_%0*d' % (maxlen, i)), node._containedType, leafTypeDict, names))
        return lines

    def MapSetOf(self, srcRegister: str, dstCircuitPort: str, node: AsnSequenceOrSetOf, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return self.MapSequenceOf(srcRegister, dstCircuitPort, node, leafTypeDict, names)

# pylint: disable=no-self-use
class MapASN1ToOutputs(RecursiveMapperGeneric[str, int]):
    def MapInteger(self, paramName: str, _: int, dummy: AsnInt, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return [paramName]

    def MapReal(self, paramName: str, __: int, unused_node: AsnReal, ___: AST_Leaftypes, dummy: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return [paramName]

    def MapBoolean(self, paramName: str, _: int, dummy: AsnBool, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return [paramName]

    def MapOctetString(self, paramName: str, _: int, node: AsnOctetString, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("OCTET STRING (in %s) must have a SIZE constraint inside ASN.1,\nor else we can't generate C code!" % node.Location())  # pragma: no cover
        if len(node._range) > 1 and node._range[0] != node._range[1]:
            panicWithCallStack("VHDL OCTET STRING (in %s) must have a fixed SIZE constraint !" % node.Location())  # pragma: no cover
        maxlen = len(str(node._range[-1]))
        lines = []  # type: List[str]
        for i in range(node._range[-1]):
            lines.append('%s_elem_%0*d' % (paramName, maxlen, i))
        return lines

    def MapEnumerated(self, paramName: str, dummy: int, _: AsnEnumerated, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        lines = [paramName]
        return lines

    def MapSequence(self, paramName: str, dummy: int, node: Union[AsnSequenceOrSet, AsnChoice], leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        lines = []  # type: List[str]
        for x in node._members:
            lines.extend(self.Map(paramName + "_" + CleanName(x[0]), dummy, x[1], leafTypeDict, names))
        return lines

    def MapSet(self, paramName: str, dummy: int, node: AsnSequenceOrSet, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return self.MapSequence(paramName, dummy, node, leafTypeDict, names)  # pragma: nocover

    def MapChoice(self, paramName: str, dummy: int, node: AsnChoice, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        lines = ['%s_choiceIdx' % paramName]
        lines.extend(self.MapSequence(paramName, dummy, node, leafTypeDict, names))
        return lines

    def MapSequenceOf(self, paramName: str, dummy: int, node: AsnSequenceOrSetOf, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("For VHDL, a SIZE constraint is mandatory (%s)!\n" % node.Location())  # pragma: no cover
        if len(node._range) > 1 and node._range[0] != node._range[1]:
            panicWithCallStack("Must have a fixed SIZE constraint (in %s) for VHDL code!" % node.Location())  # pragma: no cover
        maxlen = len(str(node._range[-1]))
        lines = []  # type: List[str]
        for i in range(node._range[-1]):
            lines.extend(self.Map(paramName + ('_elem_%0*d' % (maxlen, i)), dummy, node._containedType, leafTypeDict, names))
        return lines

    def MapSetOf(self, reginfo: str, dstVHDL: int, node: AsnSequenceOrSetOf, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return self.MapSequenceOf(reginfo, dstVHDL, node, leafTypeDict, names)  # pragma: nocover

class MapASN1ToVHDLfinStateOutputs(RecursiveMapperGeneric[str, str]):
    def MapInteger(self, srcRegister: str, dstCircuitPort: str, _: AsnInt, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        # Need to set different value for output signal
        return [srcRegister + '_reg_d' + ' <= ' + 'int_' + dstCircuitPort]
            

    def MapReal(self, srcRegister: str, dstCircuitPort: str, unused_node: AsnReal, ___: AST_Leaftypes, dummy: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return [dstCircuitPort + ' => ' + srcRegister]

    def MapBoolean(self, srcRegister: str, dstCircuitPort: str, __: AsnBool, ___: AST_Leaftypes, dummy: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return [dstCircuitPort + ' => ' + srcRegister]

    def MapOctetString(self, srcRegister: str, dstCircuitPort: str, node: AsnOctetString, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("OCTET STRING (in %s) must have a SIZE constraint inside ASN.1,\nor else we can't generate C code!" % node.Location())  # pragma: no cover
        if len(node._range) > 1 and node._range[0] != node._range[1]:
            panicWithCallStack("VHDL OCTET STRING (in %s) must have a fixed SIZE constraint !" % node.Location())  # pragma: no cover
        maxlen = len(str(node._range[-1]))
        lines = []  # type: List[str]
        for i in range(node._range[-1]):
            lines.append(dstCircuitPort + ('_elem_%0*d' % (maxlen, i)) + ' => ' + srcRegister + ('_elem_%0*d' % (maxlen, i)))
        return lines

    def MapEnumerated(self, srcRegister: str, dstCircuitPort: str, __: AsnEnumerated, ___: AST_Leaftypes, dummy: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return [dstCircuitPort + ' => ' + srcRegister]

    def MapSequence(self, srcRegister: str, dstCircuitPort: str, node: Union[AsnSequenceOrSet, AsnChoice], leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        lines = []  # type: List[str]
        for x in node._members:
            lines.extend(self.Map(srcRegister + "_" + CleanName(x[0]), dstCircuitPort + "_" + CleanName(x[0]), x[1], leafTypeDict, names))
        return lines

    def MapSet(self, srcRegister: str, dstCircuitPort: str, node: AsnSequenceOrSet, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return self.MapSequence(srcRegister, dstCircuitPort, node, leafTypeDict, names)  # pragma: nocover

    def MapChoice(self, srcRegister: str, dstCircuitPort: str, node: AsnChoice, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        lines = []  # type: List[str]
        lines.append(dstCircuitPort + '_choiceIdx => ' + srcRegister + '_choiceIdx')
        lines.extend(self.MapSequence(srcRegister, dstCircuitPort, node, leafTypeDict, names))
        return lines

    def MapSequenceOf(self, srcRegister: str, dstCircuitPort: str, node: AsnSequenceOrSetOf, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("For VHDL, a SIZE constraint is mandatory (%s)!\n" % node.Location())  # pragma: no cover
        if len(node._range) > 1 and node._range[0] != node._range[1]:
            panicWithCallStack("Must have a fixed SIZE constraint (in %s) for VHDL code!" % node.Location())  # pragma: no cover
        maxlen = len(str(node._range[-1]))
        lines = []  # type: List[str]
        for i in range(node._range[-1]):
            lines.extend(self.Map(
                srcRegister + ('_elem_%0*d' % (maxlen, i)), dstCircuitPort + ('_elem_%0*d' % (maxlen, i)), node._containedType, leafTypeDict, names))
        return lines

    def MapSetOf(self, srcRegister: str, dstCircuitPort: str, node: AsnSequenceOrSetOf, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return self.MapSequenceOf(srcRegister, dstCircuitPort, node, leafTypeDict, names)


# pylint: disable=no-self-use
class MapASN1ToVHDLregisterDefaults(RecursiveMapperGeneric[str, str]):
    def MapInteger(self, direction: str, dstVHDL: str, node: AsnInt, _: AST_Leaftypes, __: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("INTEGERs need explicit ranges when generating VHDL code... (%s)" % node.Location())  # pragma: no cover
        bits = math.log(max(abs(x) for x in node._range) + 1, 2)
        bits += (bits if node._range[0] < 0 else 0)

        if direction == "in " :
            return [dstVHDL + '_reg_d' + ' <= ' + dstVHDL + '_reg_q;']
        else :
            return['']

    def MapReal(self, direction: str, dstVHDL: str, unused_node: AsnReal, ___: AST_Leaftypes, dummy: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return [dstVHDL + ' : ' + direction + ('std_logic_vector(63 downto 0);')]

    def MapBoolean(self, direction: str, dstVHDL: str, _: AsnBool, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return [dstVHDL + ' : ' + direction + 'std_logic_vector(7 downto 0);']

    def MapOctetString(self, direction: str, dstVHDL: str, node: AsnOctetString, _: AST_Leaftypes, __: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("OCTET STRING (in %s) must have a SIZE constraint inside ASN.1,\nor else we can't generate C code!" % node.Location())  # pragma: no cover
        if len(node._range) > 1 and node._range[0] != node._range[1]:
            panicWithCallStack("VHDL OCTET STRING (in %s) must have a fixed SIZE constraint !" % node.Location())  # pragma: no cover
        maxlen = len(str(node._range[-1]))
        lines = []  # type: List[str]
        for i in range(node._range[-1]):
            lines.append(dstVHDL + ('_elem_%0*d: ' % (maxlen, i)) + direction + 'std_logic_vector(7 downto 0);')
        return lines

    def MapEnumerated(self, direction: str, dstVHDL: str, _: AsnEnumerated, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return [dstVHDL + ' : ' + direction + 'std_logic_vector(7 downto 0);']

    def MapSequence(self, direction: str, dstVHDL: str, node: Union[AsnSequenceOrSet, AsnChoice], leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        lines = []  # type: List[str]
        for x in node._members:
            lines.extend(self.Map(direction, dstVHDL + "_" + CleanName(x[0]), x[1], leafTypeDict, names))
        return lines

    def MapSet(self, direction: str, dstVHDL: str, node: AsnSequenceOrSet, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return self.MapSequence(direction, dstVHDL, node, leafTypeDict, names)  # pragma: nocover

    def MapChoice(self, direction: str, dstVHDL: str, node: AsnChoice, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        lines = []  # type: List[str]
        lines.append(dstVHDL + '_choiceIdx : ' + direction + 'std_logic_vector(7 downto 0);')
        lines.extend(self.MapSequence(direction, dstVHDL, node, leafTypeDict, names))
        return lines

    def MapSequenceOf(self, direction: str, dstVHDL: str, node: AsnSequenceOrSetOf, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("For VHDL, a SIZE constraint is mandatory (%s)!\n" % node.Location())  # pragma: no cover
        if len(node._range) > 1 and node._range[0] != node._range[1]:
            panicWithCallStack("Must have a fixed SIZE constraint (in %s) for VHDL code!" % node.Location())  # pragma: no cover
        maxlen = len(str(node._range[-1]))
        lines = []  # type: List[str]
        for i in range(node._range[-1]):
            lines.extend(self.Map(
                direction, dstVHDL + ('_elem_%0*d' % (maxlen, i)), node._containedType, leafTypeDict, names))
        return lines

    def MapSetOf(self, direction: str, dstVHDL: str, node: AsnSequenceOrSetOf, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return self.MapSequenceOf(direction, dstVHDL, node, leafTypeDict, names)  # pragma: nocover

class MapASN1ToVHDLregisterIndex(RecursiveMapperGeneric[str, str]):
    def MapInteger(self, _: str, dstVHDL: str, node: AsnInt, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("INTEGERs need explicit ranges when generating VHDL code... (%s)" % node.Location())  # pragma: no cover
        bits = math.log(max(abs(x) for x in node._range) + 1, 2)
        bits += (bits if node._range[0] < 0 else 0)
        return ['constant ' + dstVHDL.upper() + '_IDX ' + ': integer := ']
    
    def MapReal(self, _: str, dstVHDL: str, unused_node: AsnReal, ___: AST_Leaftypes, dummy: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return ['signal ' + dstVHDL + ' : ' + ('std_logic_vector(63 downto 0);')]

    def MapBoolean(self, _: str, dstVHDL: str, __: AsnBool, ___: AST_Leaftypes, dummy: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return ['signal ' + dstVHDL + ' : ' + 'std_logic_vector(7 downto 0);']

    def MapOctetString(self, _: str, dstVHDL: str, node: AsnOctetString, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("OCTET STRING (in %s) must have a SIZE constraint inside ASN.1,\nor else we can't generate C code!" % node.Location())  # pragma: no cover
        if len(node._range) > 1 and node._range[0] != node._range[1]:
            panicWithCallStack("VHDL OCTET STRING (in %s) must have a fixed SIZE constraint !" % node.Location())  # pragma: no cover
        maxlen = len(str(node._range[-1]))
        lines = []  # type: List[str]
        for i in range(node._range[-1]):
            lines.append('' + dstVHDL + ('_elem_%0*d: ' % (maxlen, i)) + 'std_logic_vector(7 downto 0);')
        return lines

    def MapEnumerated(self, _: str, dstVHDL: str, __: AsnEnumerated, ___: AST_Leaftypes, dummy: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return ['signal ' + dstVHDL + ' : ' + 'std_logic_vector(7 downto 0);']

    def MapSequence(self, _: str, dstVHDL: str, node: Union[AsnSequenceOrSet, AsnChoice], leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        lines = []  # type: List[str]
        for x in node._members:
            lines.extend(self.Map(_, dstVHDL + "_" + CleanName(x[0]), x[1], leafTypeDict, names))
        return lines

    def MapSet(self, _: str, dstVHDL: str, node: AsnSequenceOrSet, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return self.MapSequence(_, dstVHDL, node, leafTypeDict, names)  # pragma: nocover

    def MapChoice(self, _: str, dstVHDL: str, node: AsnChoice, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        lines = []  # type: List[str]
        lines.append('signal ' + dstVHDL + '_choiceIdx : ' + 'std_logic_vector(7 downto 0);')
        lines.extend(self.MapSequence(_, dstVHDL, node, leafTypeDict, names))
        return lines

    def MapSequenceOf(self, _: str, dstVHDL: str, node: AsnSequenceOrSetOf, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("For VHDL, a SIZE constraint is mandatory (%s)!\n" % node.Location())  # pragma: no cover
        if len(node._range) > 1 and node._range[0] != node._range[1]:
            panicWithCallStack("Must have a fixed SIZE constraint (in %s) for VHDL code!" % node.Location())  # pragma: no cover
        maxlen = len(str(node._range[-1]))
        lines = []  # type: List[str]
        for i in range(node._range[-1]):
            lines.extend(self.Map(
                _, dstVHDL + ('_elem_%0*d' % (maxlen, i)), node._containedType, leafTypeDict, names))
        return lines

    def MapSetOf(self, _: str, dstVHDL: str, node: AsnSequenceOrSetOf, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return self.MapSequenceOf(_, dstVHDL, node, leafTypeDict, names)  # pragma: nocover

class MapASN1ToVHDLregisterAPBwrites(RecursiveMapperGeneric[str, str]):
    def MapInteger(self, _: str, dstVHDL: str, node: AsnInt, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("INTEGERs need explicit ranges when generating VHDL code... (%s)" % node.Location())  # pragma: no cover
        bits = math.log(max(abs(x) for x in node._range) + 1, 2)
        bits += (bits if node._range[0] < 0 else 0)
        
        if _ == "in ":
            ret = "            when " + dstVHDL.upper() + '_IDX => \n'
            ret += '                ' + dstVHDL + '_reg_d' + '<= s_apb_master.pwdata;\n' 
            return [ret]
        else:
            return ['']
            

        #return ['CONSTANT ' + dstVHDL.upper() + '_IDX ' + ': integer := ']
    
    def MapReal(self, _: str, dstVHDL: str, unused_node: AsnReal, ___: AST_Leaftypes, dummy: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return ['signal ' + dstVHDL + ' : ' + ('std_logic_vector(63 downto 0);')]

    def MapBoolean(self, _: str, dstVHDL: str, __: AsnBool, ___: AST_Leaftypes, dummy: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return ['signal ' + dstVHDL + ' : ' + 'std_logic_vector(7 downto 0);']

    def MapOctetString(self, _: str, dstVHDL: str, node: AsnOctetString, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("OCTET STRING (in %s) must have a SIZE constraint inside ASN.1,\nor else we can't generate C code!" % node.Location())  # pragma: no cover
        if len(node._range) > 1 and node._range[0] != node._range[1]:
            panicWithCallStack("VHDL OCTET STRING (in %s) must have a fixed SIZE constraint !" % node.Location())  # pragma: no cover
        maxlen = len(str(node._range[-1]))
        lines = []  # type: List[str]
        for i in range(node._range[-1]):
            lines.append('' + dstVHDL + ('_elem_%0*d: ' % (maxlen, i)) + 'std_logic_vector(7 downto 0);')
        return lines

    def MapEnumerated(self, _: str, dstVHDL: str, __: AsnEnumerated, ___: AST_Leaftypes, dummy: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return ['signal ' + dstVHDL + ' : ' + 'std_logic_vector(7 downto 0);']

    def MapSequence(self, _: str, dstVHDL: str, node: Union[AsnSequenceOrSet, AsnChoice], leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        lines = []  # type: List[str]
        for x in node._members:
            lines.extend(self.Map(_, dstVHDL + "_" + CleanName(x[0]), x[1], leafTypeDict, names))
        return lines

    def MapSet(self, _: str, dstVHDL: str, node: AsnSequenceOrSet, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return self.MapSequence(_, dstVHDL, node, leafTypeDict, names)  # pragma: nocover

    def MapChoice(self, _: str, dstVHDL: str, node: AsnChoice, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        lines = []  # type: List[str]
        lines.append('signal ' + dstVHDL + '_choiceIdx : ' + 'std_logic_vector(7 downto 0);')
        lines.extend(self.MapSequence(_, dstVHDL, node, leafTypeDict, names))
        return lines

    def MapSequenceOf(self, _: str, dstVHDL: str, node: AsnSequenceOrSetOf, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("For VHDL, a SIZE constraint is mandatory (%s)!\n" % node.Location())  # pragma: no cover
        if len(node._range) > 1 and node._range[0] != node._range[1]:
            panicWithCallStack("Must have a fixed SIZE constraint (in %s) for VHDL code!" % node.Location())  # pragma: no cover
        maxlen = len(str(node._range[-1]))
        lines = []  # type: List[str]
        for i in range(node._range[-1]):
            lines.extend(self.Map(
                _, dstVHDL + ('_elem_%0*d' % (maxlen, i)), node._containedType, leafTypeDict, names))
        return lines

    def MapSetOf(self, _: str, dstVHDL: str, node: AsnSequenceOrSetOf, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return self.MapSequenceOf(_, dstVHDL, node, leafTypeDict, names)  # pragma: nocover

class MapASN1ToVHDLregisterAPBreads(RecursiveMapperGeneric[str, str]):
    def MapInteger(self, _: str, dstVHDL: str, node: AsnInt, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("INTEGERs need explicit ranges when generating VHDL code... (%s)" % node.Location())  # pragma: no cover
        bits = math.log(max(abs(x) for x in node._range) + 1, 2)
        bits += (bits if node._range[0] < 0 else 0)
        ret = "            when " + dstVHDL.upper() + '_IDX => \n'
        if _ == "in ":
            ret += '                ' + 's_apb_slave.prdata ' + '<= ' + dstVHDL + '_reg_q' + ';'
        else:
            ret += '                ' + 's_apb_slave.prdata ' + '<= ' + dstVHDL + '_reg_q(31 downto 0)' + ';'
        
        return [ret]
            

        #return ['CONSTANT ' + dstVHDL.upper() + '_IDX ' + ': integer := ']
    
    def MapReal(self, _: str, dstVHDL: str, unused_node: AsnReal, ___: AST_Leaftypes, dummy: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return ['signal ' + dstVHDL + ' : ' + ('std_logic_vector(63 downto 0);')]

    def MapBoolean(self, _: str, dstVHDL: str, __: AsnBool, ___: AST_Leaftypes, dummy: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return ['signal ' + dstVHDL + ' : ' + 'std_logic_vector(7 downto 0);']

    def MapOctetString(self, _: str, dstVHDL: str, node: AsnOctetString, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("OCTET STRING (in %s) must have a SIZE constraint inside ASN.1,\nor else we can't generate C code!" % node.Location())  # pragma: no cover
        if len(node._range) > 1 and node._range[0] != node._range[1]:
            panicWithCallStack("VHDL OCTET STRING (in %s) must have a fixed SIZE constraint !" % node.Location())  # pragma: no cover
        maxlen = len(str(node._range[-1]))
        lines = []  # type: List[str]
        for i in range(node._range[-1]):
            lines.append('' + dstVHDL + ('_elem_%0*d: ' % (maxlen, i)) + 'std_logic_vector(7 downto 0);')
        return lines

    def MapEnumerated(self, _: str, dstVHDL: str, __: AsnEnumerated, ___: AST_Leaftypes, dummy: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return ['signal ' + dstVHDL + ' : ' + 'std_logic_vector(7 downto 0);']

    def MapSequence(self, _: str, dstVHDL: str, node: Union[AsnSequenceOrSet, AsnChoice], leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        lines = []  # type: List[str]
        for x in node._members:
            lines.extend(self.Map(_, dstVHDL + "_" + CleanName(x[0]), x[1], leafTypeDict, names))
        return lines

    def MapSet(self, _: str, dstVHDL: str, node: AsnSequenceOrSet, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return self.MapSequence(_, dstVHDL, node, leafTypeDict, names)  # pragma: nocover

    def MapChoice(self, _: str, dstVHDL: str, node: AsnChoice, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        lines = []  # type: List[str]
        lines.append('signal ' + dstVHDL + '_choiceIdx : ' + 'std_logic_vector(7 downto 0);')
        lines.extend(self.MapSequence(_, dstVHDL, node, leafTypeDict, names))
        return lines

    def MapSequenceOf(self, _: str, dstVHDL: str, node: AsnSequenceOrSetOf, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("For VHDL, a SIZE constraint is mandatory (%s)!\n" % node.Location())  # pragma: no cover
        if len(node._range) > 1 and node._range[0] != node._range[1]:
            panicWithCallStack("Must have a fixed SIZE constraint (in %s) for VHDL code!" % node.Location())  # pragma: no cover
        maxlen = len(str(node._range[-1]))
        lines = []  # type: List[str]
        for i in range(node._range[-1]):
            lines.extend(self.Map(
                _, dstVHDL + ('_elem_%0*d' % (maxlen, i)), node._containedType, leafTypeDict, names))
        return lines

    def MapSetOf(self, _: str, dstVHDL: str, node: AsnSequenceOrSetOf, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return self.MapSequenceOf(_, dstVHDL, node, leafTypeDict, names)  # pragma: nocover

class MapASN1ToVHDLregisterResets(RecursiveMapperGeneric[str, str]):
    def MapInteger(self, _: str, dstVHDL: str, node: AsnInt, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("INTEGERs need explicit ranges when generating VHDL code... (%s)" % node.Location())  # pragma: no cover
        bits = math.log(max(abs(x) for x in node._range) + 1, 2)
        bits += (bits if node._range[0] < 0 else 0)
        return [dstVHDL + '_reg_q' + ' <= ' + '(others => \'0\');']

    def MapReal(self, _: str, dstVHDL: str, unused_node: AsnReal, ___: AST_Leaftypes, dummy: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return ['signal ' + dstVHDL + ' : ' + ('std_logic_vector(63 downto 0);')]

    def MapBoolean(self, _: str, dstVHDL: str, __: AsnBool, ___: AST_Leaftypes, dummy: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return ['signal ' + dstVHDL + ' : ' + 'std_logic_vector(7 downto 0);']

    def MapOctetString(self, _: str, dstVHDL: str, node: AsnOctetString, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("OCTET STRING (in %s) must have a SIZE constraint inside ASN.1,\nor else we can't generate C code!" % node.Location())  # pragma: no cover
        if len(node._range) > 1 and node._range[0] != node._range[1]:
            panicWithCallStack("VHDL OCTET STRING (in %s) must have a fixed SIZE constraint !" % node.Location())  # pragma: no cover
        maxlen = len(str(node._range[-1]))
        lines = []  # type: List[str]
        for i in range(node._range[-1]):
            lines.append('' + dstVHDL + ('_elem_%0*d: ' % (maxlen, i)) + 'std_logic_vector(7 downto 0);')
        return lines

    def MapEnumerated(self, _: str, dstVHDL: str, __: AsnEnumerated, ___: AST_Leaftypes, dummy: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return ['signal ' + dstVHDL + ' : ' + 'std_logic_vector(7 downto 0);']

    def MapSequence(self, _: str, dstVHDL: str, node: Union[AsnSequenceOrSet, AsnChoice], leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        lines = []  # type: List[str]
        for x in node._members:
            lines.extend(self.Map(_, dstVHDL + "_" + CleanName(x[0]), x[1], leafTypeDict, names))
        return lines

    def MapSet(self, _: str, dstVHDL: str, node: AsnSequenceOrSet, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return self.MapSequence(_, dstVHDL, node, leafTypeDict, names)  # pragma: nocover

    def MapChoice(self, _: str, dstVHDL: str, node: AsnChoice, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        lines = []  # type: List[str]
        lines.append('signal ' + dstVHDL + '_choiceIdx : ' + 'std_logic_vector(7 downto 0);')
        lines.extend(self.MapSequence(_, dstVHDL, node, leafTypeDict, names))
        return lines

    def MapSequenceOf(self, _: str, dstVHDL: str, node: AsnSequenceOrSetOf, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("For VHDL, a SIZE constraint is mandatory (%s)!\n" % node.Location())  # pragma: no cover
        if len(node._range) > 1 and node._range[0] != node._range[1]:
            panicWithCallStack("Must have a fixed SIZE constraint (in %s) for VHDL code!" % node.Location())  # pragma: no cover
        maxlen = len(str(node._range[-1]))
        lines = []  # type: List[str]
        for i in range(node._range[-1]):
            lines.extend(self.Map(
                _, dstVHDL + ('_elem_%0*d' % (maxlen, i)), node._containedType, leafTypeDict, names))
        return lines

    def MapSetOf(self, _: str, dstVHDL: str, node: AsnSequenceOrSetOf, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return self.MapSequenceOf(_, dstVHDL, node, leafTypeDict, names)  # pragma: nocover

class MapASN1ToVHDLregisterClocked(RecursiveMapperGeneric[str, str]):
    def MapInteger(self, _: str, dstVHDL: str, node: AsnInt, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("INTEGERs need explicit ranges when generating VHDL code... (%s)" % node.Location())  # pragma: no cover
        bits = math.log(max(abs(x) for x in node._range) + 1, 2)
        bits += (bits if node._range[0] < 0 else 0)
        return [dstVHDL + '_reg_q' + ' <= ' + dstVHDL + '_reg_d;']

    def MapReal(self, _: str, dstVHDL: str, unused_node: AsnReal, ___: AST_Leaftypes, dummy: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return ['signal ' + dstVHDL + ' : ' + ('std_logic_vector(63 downto 0);')]

    def MapBoolean(self, _: str, dstVHDL: str, __: AsnBool, ___: AST_Leaftypes, dummy: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return ['signal ' + dstVHDL + ' : ' + 'std_logic_vector(7 downto 0);']

    def MapOctetString(self, _: str, dstVHDL: str, node: AsnOctetString, __: AST_Leaftypes, ___: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("OCTET STRING (in %s) must have a SIZE constraint inside ASN.1,\nor else we can't generate C code!" % node.Location())  # pragma: no cover
        if len(node._range) > 1 and node._range[0] != node._range[1]:
            panicWithCallStack("VHDL OCTET STRING (in %s) must have a fixed SIZE constraint !" % node.Location())  # pragma: no cover
        maxlen = len(str(node._range[-1]))
        lines = []  # type: List[str]
        for i in range(node._range[-1]):
            lines.append('' + dstVHDL + ('_elem_%0*d: ' % (maxlen, i)) + 'std_logic_vector(7 downto 0);')
        return lines

    def MapEnumerated(self, _: str, dstVHDL: str, __: AsnEnumerated, ___: AST_Leaftypes, dummy: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return ['signal ' + dstVHDL + ' : ' + 'std_logic_vector(7 downto 0);']

    def MapSequence(self, _: str, dstVHDL: str, node: Union[AsnSequenceOrSet, AsnChoice], leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        lines = []  # type: List[str]
        for x in node._members:
            lines.extend(self.Map(_, dstVHDL + "_" + CleanName(x[0]), x[1], leafTypeDict, names))
        return lines

    def MapSet(self, _: str, dstVHDL: str, node: AsnSequenceOrSet, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return self.MapSequence(_, dstVHDL, node, leafTypeDict, names)  # pragma: nocover

    def MapChoice(self, _: str, dstVHDL: str, node: AsnChoice, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        lines = []  # type: List[str]
        lines.append('signal ' + dstVHDL + '_choiceIdx : ' + 'std_logic_vector(7 downto 0);')
        lines.extend(self.MapSequence(_, dstVHDL, node, leafTypeDict, names))
        return lines

    def MapSequenceOf(self, _: str, dstVHDL: str, node: AsnSequenceOrSetOf, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        if not node._range:
            panicWithCallStack("For VHDL, a SIZE constraint is mandatory (%s)!\n" % node.Location())  # pragma: no cover
        if len(node._range) > 1 and node._range[0] != node._range[1]:
            panicWithCallStack("Must have a fixed SIZE constraint (in %s) for VHDL code!" % node.Location())  # pragma: no cover
        maxlen = len(str(node._range[-1]))
        lines = []  # type: List[str]
        for i in range(node._range[-1]):
            lines.extend(self.Map(
                _, dstVHDL + ('_elem_%0*d' % (maxlen, i)), node._containedType, leafTypeDict, names))
        return lines

    def MapSetOf(self, _: str, dstVHDL: str, node: AsnSequenceOrSetOf, leafTypeDict: AST_Leaftypes, names: AST_Lookup) -> List[str]:  # pylint: disable=invalid-sequence-index
        return self.MapSequenceOf(_, dstVHDL, node, leafTypeDict, names)  # pragma: nocover        