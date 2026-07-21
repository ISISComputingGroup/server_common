# This file is part of the ISIS IBEX application.
# Copyright (C) 2012-2016 Science & Technology Facilities Council.
# All rights reserved.
#
# This program is distributed in the hope that it will be useful.
# This program and the accompanying materials are made available under the
# terms of the Eclipse Public License v1.0 which accompanies this distribution.
# EXCEPT AS EXPRESSLY SET FORTH IN THE ECLIPSE PUBLIC LICENSE V1.0, THE PROGRAM
# AND ACCOMPANYING MATERIALS ARE PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND.  See the Eclipse Public License v1.0 for more details.
#
# You should have received a copy of the Eclipse Public License v1.0
# along with this program; if not, you can obtain a copy from
# https://www.eclipse.org/org/documents/epl-v10.php or
# http://opensource.org/licenses/eclipse-1.0.php
"""
Utilities for running block server and related ioc's.
"""

import binascii
import datetime
import json
import re
import threading
import time
import zlib
from typing import Any
from xml.etree import ElementTree

from server_common.common_exceptions import MaxAttemptsExceededException
from server_common.loggers.logger import Logger

# ruff: noqa: ANN401
# Default to base class - does not actually log anything
LOGGER = Logger()
_LOGGER_LOCK = threading.RLock()  # To prevent message interleaving between different threads.


class SEVERITY(object):
    """
    Standard message severities.
    """

    INFO = "INFO"
    MINOR = "MINOR"
    MAJOR = "MAJOR"


def char_waveform(length: object) -> dict[str, str | list[int] | Any]:
    """
    Helper function for creating a char waveform PV.

    Args:
        length: The length of the array.

    Return:
        The dictionary to add to the PVDB.
    """
    return {"type": "char", "count": length, "value": [0]}


def set_logger(logger: Logger) -> None:
    """Sets the logger used by the print_and_log function.

    Args:
        logger (Logger): The logger to use. Must inherit from Logger.
    """
    global LOGGER
    LOGGER = logger


def print_and_log(
    message: str | object, severity: str = SEVERITY.INFO, src: str = "BLOCKSVR"
) -> None:
    """Prints the specified message to the console and writes it to the log.

    Args:
        message (string|exception): The message to log
        severity (string, optional): Gives the severity of the message. Expected severities are
                                    MAJOR, MINOR and INFO. Default severity is INFO.
        src (string, optional): Gives the source of the message. Default source is BLOCKSVR.
    """
    with _LOGGER_LOCK:
        message = "[{}] {}: {}".format(datetime.datetime.now(), severity, message)
        print(message)
        LOGGER.write_to_log(message, severity, src)


def compress_and_hex(value: str) -> bytes:
    """Compresses the inputted string and encodes it as hex.

    Args:
        value (str): The string to be compressed
    Returns:
        bytes : A compressed and hexed version of the inputted string
    """
    (
        isinstance(value, str),
        (
            "Non-str argument passed to compress_and_hex, maybe Python 2/3 compatibility issue\n"
            "Argument was type {} with value {}".format(value.__class__.__name__, value)
        ),
    )
    compr = zlib.compress(bytes(value, "utf-8"))
    return binascii.hexlify(compr)


def dehex_and_decompress(value: bytes) -> bytes:
    """Decompresses the inputted string, assuming it is in hex encoding.

    Args:
        value (bytes): The string to be decompressed, encoded in hex

    Returns:
        bytes : A decompressed version of the inputted string
    """
    assert isinstance(value, bytes), (
        "Non-bytes argument passed to dehex_and_decompress, maybe Python 2/3 compatibility issue\n"
        "Argument was type {} with value {}".format(value.__class__.__name__, value)
    )
    return zlib.decompress(binascii.unhexlify(value))


def dehex_and_decompress_waveform(value: list) -> bytes:
    """Decompresses the inputted waveform, assuming it is an array of integers
        representing characters (null terminated).

    Args:
        value (list[int]): The string to be decompressed

    Returns:
        bytes : A decompressed version of the inputted string
    """
    assert isinstance(value, list), (
        "Non-list argument passed to dehex_and_decompress_waveform\n"
        "Argument was type {} with value {}".format(value.__class__.__name__, value)
    )

    unicode_rep = waveform_to_string(value)
    bytes_rep = unicode_rep.encode("ascii")
    return dehex_and_decompress(bytes_rep)


def convert_to_json(value: object) -> str:
    """Converts the inputted object to JSON format.

    Args:
        value (obj): The object to be converted

    Returns:
        string : The JSON representation of the inputted object
    """
    return json.dumps(value)


def convert_from_json(value: str) -> object:
    """Converts the inputted string into a JSON object.

    Args:
        value (string): The JSON representation of an object

    Returns:
        obj : An object corresponding to the given string
    """
    return json.loads(value)


def parse_boolean(string: str) -> bool:
    """Parses an xml true/false value to boolean

    Args:
        string (string): String containing the xml representation of true/false

    Returns:
        bool : A python boolean representation of the string

    Raises:
        ValueError : If the supplied string is not "true" or "false"
    """
    if string.lower() == "true":
        return True
    elif string.lower() == "false":
        return False
    else:
        raise ValueError(str(string) + ': Attribute must be "true" or "false"')


def value_list_to_xml(
    value_list: dict, grp: ElementTree.Element, group_tag: str, item_tag: str
) -> None:
    """Converts a list of values to corresponding xml.

    Args:
        value_list (dict[str, dict[object, object]]): The dictionary of names and their values,
            values are in turn a dictionary of names and value {name: {parameter : value,
            parameter : value}}
        grp (ElementTree.SubElement): The SubElement object to append the list on to
        group_tag (string): The tag that corresponds to the group for the items given in the list
            e.g. macros
        item_tag (string): The tag that corresponds to each item in the list e.g. macro
    """
    xml_list = ElementTree.SubElement(grp, group_tag)
    if len(value_list) > 0:
        for n, c in value_list.items():
            xml_item = ElementTree.SubElement(xml_list, item_tag)
            xml_item.set("name", n)
            for cn, cv in c.items():
                xml_item.set(str(cn), str(cv))


def check_pv_name_valid(name: str) -> bool:
    """Checks that text conforms to the ISIS PV naming standard

    Args:
        name (string): The text to be checked

    Returns:
        bool : True if text conforms to standard, False otherwise
    """
    if re.match(r"[A-Za-z0-9_]*", name) is None:
        return False
    return True


def create_pv_name(
    name: str, current_pvs: list, default_pv: str, limit: int = 6, allow_colon: bool = False
) -> str:
    """Uses the given name as a basis for a valid PV.

    Args:
        name (string): The basis for the PV
        current_pvs (list): List of already allocated pvs
        default_pv (string): Basis for the PV if name is unreasonable, must be a valid PV name
        limit (integer): Character limit for the PV
        allow_colon (bool): If True, pv name is allowed to contain colons; else, remove the colons

    Returns:
        string : A valid PV
    """
    pv_text = name.upper().replace(" ", "_")

    replacement_string = r"[^:a-zA-Z0-9_]" if allow_colon else r"\W"
    pv_text = re.sub(replacement_string, "", pv_text)

    # Check some edge cases of unreasonable names
    if re.search(r"[^0-9_]", pv_text) is None or pv_text == "":
        pv_text = default_pv

    # Cut down pvs to limit
    pv_text = pv_text[0:limit]

    # Make sure PVs are unique
    i = 1
    pv = pv_text

    # Append a number if the PV already exists
    while pv in current_pvs:
        if len(pv) > limit - 2:
            pv = pv[0 : limit - 2]
        pv += format(i, "02d")
        i += 1

    return pv


def parse_xml_removing_namespace(file_path: str) -> Any:
    """Creates an Element object from a given xml file, removing the namespace.

    Args:
        file_path (string): The location of the xml file

    Returns:
        Element : A object holding all the xml information
    """
    it = ElementTree.iterparse(file_path)
    for _, el in it:
        if ":" in el.tag:
            el.tag = el.tag.split("}", 1)[1]
    return it.root


def waveform_to_string(data: Any) -> str:
    """
    Args:
        data: waveform as null terminated string

    Returns: waveform as a sting

    """
    output = str()
    for i in data:
        if i == 0:
            break
        output += chr(i)
    return output


def ioc_restart_pending(ioc_pv: Any, channel_access: Any) -> Any:
    """Check if a particular IOC is restarting. Assumes it has suitable restart PV

    Args:
        ioc_pv: The base PV for the IOC with instrument PV prefix
        channel_access (ChannelAccess): The channel access object to be used for accessing PVs

    Return
        bool: True if restarting, else False
    """
    return channel_access.caget(ioc_pv + ":RESTART", as_string=True) == "Busy"


def retry(max_attempts: int, interval: int, exception: Any) -> Any:
    """
    Attempt to perform a function a number of times in specified intervals before failing.

    Args:
        max_attempts: The maximum number of tries to execute the function
        interval: The retry interval
        exception: The type of exception to handle by retrying

    Returns:
        The input function wrapped in a retry loop

    """

    def _tags_decorator(func: Any) -> Any:
        def _wrapper(*args: Any, **kwargs: Any) -> Any:
            attempts = 0
            last_exception = ValueError("Max attempts should be > 0, it is {}".format(max_attempts))
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except exception as ex:
                    last_exception = ex
                    attempts += 1
                    time.sleep(interval)

            raise MaxAttemptsExceededException(last_exception)

        return _wrapper

    return _tags_decorator


def remove_from_end(string: str | None, text_to_remove: str) -> str | None:
    """
    Remove a String from the end of a string if it exists
    Args:
        string (str): string to edit
        text_to_remove (str): the text to remove

    Returns: the string with the text removed

    """
    if string is not None and string.endswith(text_to_remove):
        return string[: -len(text_to_remove)]
    return string


def lowercase_and_make_unique(in_list: list[str]) -> set[str]:
    """
    Takes a collection of strings, and returns it with all strings lowercased and with duplicates
        removed.

    Args:
        in_list (List[str]): the collection of strings to operate on

    Returns:
        set[str]: the lowercased unique set of strings.
    """
    return {x.lower() for x in in_list}


def parse_date_time_arg_exit_on_fail(date_arg: str, error_code: int = 1) -> datetime.datetime:
    """
    Parse a date argument and exit the program with an error code if that argument is not a date
    Args:
        date_arg: date argument to parse
        error_code: the error code to exit with if it is not a date

    Returns:
        a date time of the argument

    """
    try:
        return datetime.datetime.strptime(date_arg, "%Y-%m-%dT%H:%M:%S")
    except (ValueError, TypeError) as ex:
        print(f"Can not interpret date '{date_arg}' error: {ex}")
        exit(error_code)


def dehex_and_decompress_waveform_value(value: str | bytes) -> str:
    """Decompresses the inputted waveform, assuming it is available as string.

    Args:
        value: The string to be decompressed

    Returns:
        str : A decompressed and unhexed version of the input string

    Raises:
        ValueError : If the supplied string is not valid hexadecimal characters
    """
    if value and len(value) % 2 == 0:
        return zlib.decompress(binascii.unhexlify(value)).decode("utf-8")
    else:
        raise ValueError(f"Invalid hex string: value is empty or has odd length ({len(value)})")
