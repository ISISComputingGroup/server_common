import asyncio

from pysnmp.hlapi.v1arch.asyncio import (
    CommunityData,
    ObjectIdentity,
    ObjectType,
    SnmpDispatcher,
    UdpTransportTarget,
    next_cmd,
)
from pysnmp.smi import builder, compiler, error, rfc1902, view

# must import pysnmp_sync_adapter after pysnmp.hlapi to ensure correct v1 functions chosen
# from pysnmp_sync_adapter import create_transport, next_cmd_sync
from server_common.utilities import SEVERITY, print_and_log

# Assemble MIB browser
MIB_BUILDER = builder.MibBuilder()
MIB_VIEW_CONTROLLER = view.MibViewController(MIB_BUILDER)

# compiler.addMibCompiler(mibBuilder, sources=['https://mibs.pysnmp.com/asn1/@mib@'],
# destination='snmp/mibs')
# The below code needs MIBS to have been downloaded in the below subfolder.
compiler.addMibCompiler(MIB_BUILDER, sources=["file://snmp/mibs"])
# Pre-load MIB modules we expect to work with
MIB_BUILDER.load_modules(
    "SNMPv2-MIB", "SNMP-COMMUNITY-MIB", "DISMAN-EXPRESSION-MIB", "RFC1213-MIB", "IF-MIB"
)

INTERESTING_MIBS = [
    "DISMAN-EXPRESSION-MIB::sysUpTimeInstance",
    "SNMPv2-MIB::sysName",
    "IF-MIB::ifOperStatus",
    "IF-MIB::ifSpeed",
    "IF-MIB::ifInOctets",
    "IF-MIB::ifOutOctets",
]


async def walk_async(
    host: str, oid: str, requested_mibs: list[str] = INTERESTING_MIBS
) -> dict[str, str]:
    mibmap = dict()
    current_oid = ObjectType(ObjectIdentity(oid))
    with SnmpDispatcher() as snmp_dispatcher:
        while True:
            error_indication, error_status, error_index, var_binds = await next_cmd(
                snmp_dispatcher,
                CommunityData("public", mpModel=0),
                await UdpTransportTarget.create((host, 161), timeout=5, retries=0),
                current_oid,
                lookupMib=False,
                lexicographicMode=False,
                lookupNames=True,
                lookupValues=True,
            )
            if error_indication:
                ## we need to look at later - currently will print forever for a moxa that is
                ## not on the network. Maybe return status and let caller decide whether to print
                print_and_log(f"Error:: for {host}: {error_indication}", severity=SEVERITY.MINOR)
                break

            elif error_status:
                print_and_log(
                    "host {}: {} at {}".format(
                        host,
                        error_status,
                        error_index and var_binds[int(error_index) - 1][0] or "?",
                    ),
                    severity=SEVERITY.MAJOR,
                )
                break

            else:
                # Run var-binds through MIB resolver
                # We get some `Excessive instance identifier sub-OIDs left at MibTableRow` errors
                # which is what the error.SmiError ignore is all about
                res_var_binds = []
                for x in var_binds:
                    try:
                        y = rfc1902.ObjectType(rfc1902.ObjectIdentity(x[0]), x[1]).resolveWithMib(
                            MIB_VIEW_CONTROLLER
                        )
                        res_var_binds.append((y[0], y[1]))
                    except error.SmiError:
                        pass
                for name, value in res_var_binds:
                    mib, exists, port = name.prettyPrint().partition(".")
                    if mib in requested_mibs:
                        mibmap[name.prettyPrint()] = value.prettyPrint()
                current_oid = var_binds[0]
    return mibmap


# for example     walk('130.246.49.46', '1.3.6.1.2.1')
def walk(host: str, oid: str, requested_mibs: list[str] = INTERESTING_MIBS) -> dict[str, str]:
    return asyncio.run(walk_async(host, oid, requested_mibs))
