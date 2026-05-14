import asyncio

from pysnmp.hlapi.v1arch.asyncio import (
    CommunityData,
    ObjectIdentity,
    ObjectType,
    SnmpDispatcher,
    UdpTransportTarget,
    walk_cmd,
)
from pysnmp.smi import builder, compiler, error, rfc1902, view

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


async def walkasync(
    host: str, oid: str, requested_mibs: list[str] = INTERESTING_MIBS
) -> dict[str, str]:
    mibmap = dict()
    async for error_indication, error_status, error_index, var_binds in walk_cmd(
        SnmpDispatcher(),
        CommunityData("public", mpModel=0),
        await UdpTransportTarget.create((host, 161), timeout=3, retries=0),
        ObjectType(ObjectIdentity(oid)),
        lookupMib=False,
        lexicographicMode=False,
        lookupNames=True,
        lookupValues=True,
    ):
        if error_indication:
            ## we need to look at later - currently will print forever for a moxa that is
            ## not on the network. Maybe return status and let caller decide whether to print
            # print_and_log(f"Error:: for {host}: {errorIndication}", severity=SEVERITY.MINOR)
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
            # You may want to catch and ignore resolution errors here
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
                # print(name.prettyPrint(), ' = ', value.prettyPrint())
                if mib in requested_mibs:
                    mibmap[name.prettyPrint()] = value.prettyPrint()
                    # print('MIB-->', mib, ' port-->', port, ' = ', value.prettyPrint())
                    # print_and_log('MIB -->%s, port --> %s, = %s' % (mib, port, value))

    return mibmap


def walk(host: str, oid: str, requested_mibs: list[str] = INTERESTING_MIBS) -> dict[str, str]:
    return asyncio.run(walkasync(host, oid, requested_mibs=requested_mibs))


# walk('130.246.49.46', '1.3.6.1.2.1')
