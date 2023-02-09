# (C) Semantix Information Technologies, Neuropublic, and European Space Agency
#
# Licensed under the GPL with Runtime Exception.
# Note that there are no charges (royalties) for the generated code.

#g_nodes    = []
g_signals = {}
g_apLevelContainers = {}

g_subProgramImplementations = []
g_processImplementations = []
g_threadImplementations = []

g_systems = {}

# AST classes


class AadlParameter:
    def __init__(self, direction, type):
        assert direction in ['IN', 'OUT', 'INOUT']
        self._direction = direction
        self._type = type


class AadlSubProgramFeature:
    def __init__(self, id, parameter):
        self._id = id
        self._parameter = parameter


class AadlPropertyAssociationNoModes:
    def __init__(self, name, pe):
        self._name = name
        self._propertyExpressionOrList = pe


class AadlPort:
    def __init__(self, direction, type):
        self._direction = direction
        self._type = type


class AadlEventPort:
    def __init__(self, direction, sp):
        self._direction = direction
        self._sp = sp

    def __repr__(self):
        result = "AadlEventPort("+self._direction+","
        if self._sp:
            result+=self._sp
        result+=")"
        return result


class AadlEventDataPort(AadlPort):
    def __init__(self, direction, type):
        AadlPort.__init__(self, direction, type)


class AadlThreadFeature:
    def __init__(self, id, port):
        assert(isinstance(port, AadlPort))
        self._id = id
        self._port = port


class AadlProcessFeature:
    def __init__(self, id, port):
        assert(isinstance(port, AadlPort))
        self._id = id
        self._port = port


class AadlContainedPropertyAssociation:
    def __init__(self, name, value):
        self._name = name
        self._value = value


class Signal:
    def __init__(self, asnFilename, asnNodename, asnSize):
        self._asnFilename = asnFilename
        self._asnNodename = asnNodename
        self._asnSize = asnSize


class Port:
    def __init__(self, signal):
        self._signal = signal


class DualPort(Port):
    def __init__(self, signal):
        Port.__init__(self, signal)


class UniPort(Port):
    def __init__(self, signal):
        Port.__init__(self, signal)


class IncomingUniPort(UniPort):
    def __init__(self, signal):
        UniPort.__init__(self, signal)


class OutgoingUniPort(UniPort):
    def __init__(self, signal):
        UniPort.__init__(self, signal)


class ApLevelContainer:
    def __init__(self, id):
        self._id = id
        self._calls = []
        self._params = []
        self._connections = []
        self._fpgaConfigurations = '' # The configuration(s)/"mode(s)" for which the Function's HW implementation shall apply (execution in FPGA)
        self._language = None
        self._simulinkInterfaceType = "full"
        self._simulinkFullInterfaceRef = ''

    def AddCalledAPLC(self, idAPLC):
        self._calls.append(idAPLC)

    def AddConnection(self, srcUniquePortId, destUniquePortId):
        if srcUniquePortId._componentId is None:
            srcUniquePortId._componentId = self._id
        if destUniquePortId._componentId is None:
            destUniquePortId._componentId = self._id
        self._connections.append(Connection(srcUniquePortId, destUniquePortId))

    def AddParam(self, param):
        self._params.append(param)

    def SetLanguage(self, language):
        self._language = language

    # Assign FPGA configurations
    def SetFPGAConfigurations(self, fpgaConfigurations):
        self._fpgaConfigurations = fpgaConfigurations

    def SetSimulinkInterfaceType(self, simulinkInterfaceType):
        self._simulinkInterfaceType = simulinkInterfaceType

    def SetSimulinkFullInterfaceRef(self, simulinkFullInterfaceRef):
        self._simulinkFullInterfaceRef = simulinkFullInterfaceRef

class Param:
    def __init__(self, aplcID, id, signal, sourceElement):
        self._id = id
        # It is the Process, Thread or Subprogram ID
        self._aplcID = aplcID
        # Could be string (i.e. AADL DataType name) or Signal (i.e. asnFilename, asnNodename)
        self._signal = signal
        self._sourceElement = sourceElement  # Could be AadlPort, AadlEventDataPort, AadlParameter


class InParam(Param):
    def __init__(self, aplcID, id, signal, sourceElement):
        Param.__init__(self, aplcID, id, signal, sourceElement)


class OutParam(Param):
    def __init__(self, aplcID, id, signal, sourceElement):
        Param.__init__(self, aplcID, id, signal, sourceElement)


class InOutParam(Param):
    def __init__(self, aplcID, id, signal, sourceElement):
        Param.__init__(self, aplcID, id, signal, sourceElement)


class UniquePortIdentifier:
    def __init__(self, componentId, portId):
        self._componentId = componentId
        self._portId = portId


class Connection:
    def __init__(self, fromC, toC):
        self._from = fromC
        self._to = toC
