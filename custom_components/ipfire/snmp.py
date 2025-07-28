import logging
from pysnmp.hlapi import *

_LOGGER = logging.getLogger(__name__)

def get_snmp_value(host, community, oid):
    iterator = getCmd(
        SnmpEngine(),
        CommunityData(community, mpModel=1),
        UdpTransportTarget((host, 161)),
        ContextData(),
        ObjectType(ObjectIdentity(oid))
    )
    errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
    if errorIndication:
        _LOGGER.error(f"SNMP error: {errorIndication}")
        return None
    elif errorStatus:
        _LOGGER.error(f"SNMP error: {errorStatus.prettyPrint()}")
        return None
    else:
        for varBind in varBinds:
            return varBind[1]
    return None