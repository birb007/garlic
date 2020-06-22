"""
Utility definitions/functions.

.. currentmodule:: garlic.utils

.. py:data:: UTC_FORMAT
   :value: "%Y-%m-%d %H:%M:%S"
"""
import datetime as dt

UTC_FORMAT = "%Y-%m-%d %H:%M:%S"

def decode_utc(timestamp: str) -> dt.datetime:
    """
    Decode UTC timestamp.

    :param timestamp: UTC timestamp.
    """
    return dt.datetime.strptime(timestamp, UTC_FORMAT)
