import json
import os
from typing import Dict

def get_macro_values() -> Dict[str, str]:
    """
    Parse macro environment JSON into dict. To make this work use the icpconfigGetMacros program.

    Returns: Macro Key:Value pairs as dict
    """
    macros = json.loads(os.environ.get("MACROS", "{}"))
    macros = {key: value for (key, value) in macros.items()}
    print("Defined macros: " + str(macros))
    return macros


def _get_env_var(name: str) -> str:
    try:
        return os.environ[name]
    except:
        return ""


MACROS = {
    "$(MYPVPREFIX)": _get_env_var("MYPVPREFIX"),
    "$(EPICS_KIT_ROOT)": _get_env_var("EPICS_KIT_ROOT"),
    "$(ICPCONFIGROOT)": _get_env_var("ICPCONFIGROOT"),
    "$(ICPVARDIR)": _get_env_var("ICPVARDIR"),
}
CONTROL_SYSTEM_PREFIX = MACROS["$(MYPVPREFIX)"] + "CS:"
PVPREFIX_MACRO = "$(MYPVPREFIX)"
BLOCK_PREFIX = "CS:SB:"
