"""
Garlic - An asynchronous Python 3.8+ API Wrapper for Onionoo.

.. currentmodule:: garlic

.. autosummary::
    :toctree:

    client
    types
    exc
    utils
"""
from garlic.client import Client

from garlic.types import (
    Flag,
    ExitPolicy,
    RelaySummary,
    BridgeSummary,
    RelayDetails,
    BridgeDetails,
    GraphHistory,
    RelayBandwidth,
    BridgeBandwidth,
    RelayWeight,
    BridgeClients,
    RelayUptime,
    BridgeUptime,
    Response,
    RelayDescriptor,
    BridgeDescriptor,
)
