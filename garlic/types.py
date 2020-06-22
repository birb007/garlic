"""
Implementation of types utilised internally and externally.

.. currentmodule:: garlic.types

.. py:data:: RelayDescriptor
   :value: Union[RelaySummary, PartialRelayDetails, RelayDetails, RelayBandwidth, RelayWeight, RelayUptime]

.. py:data:: BridgeDescriptor
   :value: Union[BridgeSummary, PartialBridgeDetails, BridgeDetails, BridgeBandwidth, BridgeClients, BridgeUptime]
"""

import datetime as dt

from abc import ABC, abstractclassmethod
from dataclasses import dataclass
from enum import Enum
from typing import List, TypeVar, Union, Dict, Optional, NewType, Set

from garlic import utils


class Deserialisable(ABC):
    """
    Abstract deserialisable interface for relay/bridge descriptor
    objects.
    """

    @abstractclassmethod
    def from_json(cls, json: dict):
        """
        Deserialise JSON into an instance of the implementing class.

        :param json: Raw JSON response.
        """
        ...


class Flag(Enum):
    """
    Representation of each node flag.

    :cvar EXIT: Exit flag.
    :cvar GUARD: Guard flag.
    :cvar FAST: Fast flag.
    :cvar STABLE: Stable flag.
    :cvar V2DIR: V2Dir flag.
    :cvar HSDIR: HSDir flag.
    :cvar RUNNING: Running flag.
    :cvar VALID: Valid flag.
    """

    EXIT = "Exit"
    GUARD = "Guard"
    FAST = "Fast"
    STABLE = "Stable"
    V2DIR = "V2Dir"
    HSDIR = "HSDir"
    RUNNING = "Running"
    VALID = "Valid"


class ExitPolicy:
    """
    Representation of exit policy summaries.
    """

    def __init__(self, accept_policy: Set[int] = None, reject_policy: Set[int] = None):
        """
        Instantiate `ExitPolicy` object.

        :param accept_policy: Range of ports to accept.
        :param reject_policy: Range of ports to reject.
        """
        if accept_policy is None:
            accept_policy = set()

        if reject_policy is None:
            reject_policy = set()

        self.accept_policy = accept_policy
        self.reject_poilcy = reject_policy

    @classmethod
    def from_json(cls, json: dict):
        """
        Instantiate exit policy with JSON response from the API.

        :param json: Raw JSON response.
        """

        def _parse_policy(policy):
            port_range = set()
            for entry in policy:
                chunks = [int(chunk) for chunk in entry.split("-") if chunk]
                if len(chunks) == 1:
                    port_range.add(chunks[0])
                else:
                    port_range.update(set(range(chunks[0], chunks[1])))
            return port_range

        accept_policy = None
        reject_policy = None

        if (array := json.get("accept")) :
            accept_policy = _parse_policy(array)
        if (array := json.get("reject")) :
            reject_policy = _parse_policy(array)

        return cls(accept_policy, reject_policy)

    def __repr__(self):
        return self.__class__.__name__


@dataclass
class RelaySummary(Deserialisable):
    """
    Representation of the `relay summary document <https://metrics.torproject.org/onionoo.html#summary_relay>`_.

    :param nickname: Relay nickname consisting of 1–19 alphanumerical
        characters.
    :param fingerprint: Relay fingerprint consisting of 40 upper-case
        hexadecimal characters.
    :param addresses: Array of IPv4 or IPv6 addresses where the relay accepts
        onion-routing connections or which the relay used to exit to the
        Internet in the past 24 hours. The first address is the primary
        onion-routing address that the relay used to register in the network,
        subsequent addresses are in arbitrary order.
    :param running: Boolean field saying whether this relay was listed as
        running in the last relay network status consensus.
    """

    nickname: str
    fingerprint: str
    addresses: List[str]
    running: bool

    @classmethod
    def from_json(cls, json: dict):
        """
        Instantiate a summary document with JSON response from the API.

        :param json: Raw JSON response.
        :rtype: RelaySummary
        """
        return cls(
            nickname=json["n"],
            fingerprint=json["f"],
            addresses=json["a"],
            running=json["r"],
        )


@dataclass
class BridgeSummary(Deserialisable):
    """
    Representation of the `bridge summary document <https://metrics.torproject.org/onionoo.html#summary_bridge>`_.

    :param nickname: Bridge nickname consisting of 1–19 alphanumerical
        characters.
    :param hashed_fingerprint: SHA-1 hash of the bridge fingerprint consisting
        of 40 upper-case hexadecimal characters.
    :param running: Boolean field saying whether this bridge was listed as
        running in the last bridge network status.
    """

    nickname: str
    hashed_fingerprint: str
    running: bool

    @classmethod
    def from_json(cls, json: dict):
        """
        Instantiate a summary document with JSON response from the API.

        :param json: Raw JSON response.
        """
        print(json)
        return cls(nickname=json["n"], hashed_fingerprint=json["h"], running=json["r"])


@dataclass
class RelayDetailsBase(Deserialisable):
    """
    Representation of the `relay details document <https://metrics.torproject.org/onionoo.html#details_relay>`_.

    :param nickname: Potential relay nickname consisting of 1–19
        alphanumerical characters.
    :param fingerprint: Potential relay fingerprint consisting of 40
        upper-case hexadecimal characters.
    :param or_addresses: Potential array of IPv4 or IPv6 addresses and TCP
        ports or port lists where the relay accepts onion-routing connections.
        The first address is the primary onion-routing address that the relay
        used to register in the network, subsequent addresses are in arbitrary order.
    :param last_seen: Potential UTC timestamp when this relay was last seen in
        a network status consensus.
    :param last_changed_address_or_port: Potential UTC timestamp when this
        relay last stopped announcing an IPv4 or IPv6 address or TCP port
        where it previously accepted onion-routing or directory connections.
    :param first_seen: Potential UTC timestamp when this relay was first seen
        in a network status consensus.
    :param running: Potential boolean field saying whether this relay was
        listed as running in the last relay network status consensus.
    :param consensus_weight: Potential weight assigned to this relay by the
        directory authorities that clients use in their path selection algorithm.
    :param exit_addresses: Array of IPv4 addresses that the relay used to exit
        to the Internet in the past 24 hours. :class:`py:None` if array is
        empty.
    :param dir_address: IPv4 address and TCP port where the relay accepts
        directory connections. :class:`py:None` if the relay does not accept
        directory connections.
    :param hibernating: Boolean field saying whether this relay indicated that
        it is hibernating in its last known server descriptor. :class:`py:None`
        if either the relay is not hibernating, or if no information is
        available about the hibernation status of the relay.
    :param flags: Array of relay flags that the directory authorities assigned
        to this relay. May be omitted if empty.
    :param country: Two-letter lower-case country code as found in a GeoIP
        database by resolving the relay's first onion-routing IP address.
        :class:`py:None` if the relay IP address could not be found in the
        GeoIP database.
    :param country_name: Country name as found in a GeoIP database by
        resolving the relay's first onion-routing IP address. :class:`py:None`
        if the relay IP address could not be found in the GeoIP database, or
        if the GeoIP database did not contain a country name.
    :param region_name: Region name as found in a GeoIP database by resolving
        the relay's first onion-routing IP address. :class:`py:None` if the
        relay IP address could not be found in the GeoIP database, or if the
        GeoIP database did not contain a region name.
    :param city_name: City name as found in a GeoIP database by resolving the
        relay's first onion-routing IP address. :class:`py:None` if the relay IP
        address could not be found in the GeoIP database, or if the GeoIP
        database did not contain a city name.
    :param latitude: Latitude as found in a GeoIP database by resolving the
        relay's first onion-routing IP address. :class:`py:None` if the relay
        IP address could not be found in the GeoIP database.
    :param longitude: Longitude as found in a GeoIP database by resolving the
        relay's first onion-routing IP address. :class:`py:None` if the relay
        IP address could not be found in the GeoIP database.
    :param as_: AS number as found in an AS database by resolving the relay's
        first onion-routing IP address. AS number strings start with "AS",
        followed directly by the AS number. :class:`py:None` if the relay IP
        address could not be found in the AS
        database.
    :param as_name: AS name as found in an AS database by resolving the
        relay's first onion-routing IP address. :class:`py:None` if the relay IP
        address could not be found in the AS database.
    :param verified_host_names: Host names as found in a reverse DNS lookup of
        the relay's primary IP address for which a matching A record was also
        found. This field is updated at most once in 12 hours, unless the
        relay IP address changes. :class:`py:None` if the relay IP address was
        not looked up, if no lookup request was successful yet, or if no A
        records were found matching the PTR records.
    :param unverified_host_names: Host names as found in a reverse DNS lookup
        of the relay's primary IP address that for which a matching A record
        was not found. This field is updated at most once in 12 hours, unless
        the relay IP address changes. :class:`py:None` if the relay IP address
        was not looked up, if no lookup request was successful yet, or if A
        records were found matching all PTR records.
    :param last_restarted: UTC timestamp when the relay was last (re-)started.
        :class:`py:None` if router descriptor containing this information
        cannot be found.
    :param bandwidth_rate: Average bandwidth in bytes per second that this
        relay is willing to sustain over long periods. :class:`py:None` if
        router descriptor containing this information cannot be found.
    :param bandwidth_burst: Bandwidth in bytes per second that this relay is
        willing to sustain in very short intervals. :class:`py:None` if router
        descriptor containing this information cannot be found.
    :param observed_bandwidth: Bandwidth estimate in bytes per second of the
        capacity this relay can handle. :class:`py:None` if router descriptor
        containing this information cannot be found.
    :param advertised_bandwidth: Bandwidth in bytes per second that this relay
        is willing and capable to provide. :class:`py:None` if router
        descriptor containing this information cannot be found.
    :param exit_policy: Array of exit-policy lines. :class:`py:None` if router
        descriptor containing this information cannot be found.
    :param exit_policy_summary: Summary version of the relay's exit policy.
    :param exit_policy_v6_summary: Summary version of the relay's IPv6 exit
        policy.
    :param contact: Contact address of the relay operator. :class:`py:None` if
        empty or if descriptor containing this information cannot be found.
    :param platform: Platform string containing operating system and Tor
        version details. :class:`py:None` if empty or if descriptor containing
        this information cannot be found.
    :param version: Tor software version without leading "Tor" as reported by
        the directory authorities in the "v" line of the consensus. :class:`py
        None` if either the directory authorities or the relay did not report
        which version the relay runs or if the relay runs an alternative Tor
        implementation.
    :param recommended_version: Boolean field saying whether the Tor software
        version of this relay is recommended by the directory authorities or
        not. :class:`py:None` if either the directory authorities did not
        recommend versions, or the relay did not report which version it runs.
    :param version_status: Status of the Tor software version of the relay
        based on the versions recommended by the directory authorities.
        Possible version statuses are:
            - "recommended" if a version is listed as recommended;
            - "experimental" if a version is newer than every recommended
              version;
            - "obsolete" if a version is older than every recommended version;
            - "new in series" if a version has other recommended versions with
              the same first three components, and the version is newer than
              all such recommended versions, but it is not newer than every
              recommended version;
            - "unrecommended" if none of the above conditions hold.
        :class:`python:None` if either the directory authorities did not
        recommend versions, or the bridge did not report which version it runs.
    :param effective_family: Array of fingerprints of relays that are in an
        effective, mutual family relationship with this relay. These relays
        are part of this relay's family and they consider this relay to be
        part of their family. Always contains the relay's own fingerprint.
        class:`py:None` if the descriptor containing this information cannot be
        found.
    :param alleged_family: Array of fingerprints of relays that are not in an
        effective, mutual family relationship with this relay. These relays
        are part of this relay's family but they don't consider this relay to
        be part of their family. :class:`py:None` if empty or if descriptor
        containing
        this information cannot be found.
    :param indirect_family: Array of fingerprints of relays that are not in an
        effective, mutual family relationship with this relay but that can be
        reached by following effective, mutual family relationships starting
        at this relay. :class:`py:None` if empty or if descriptor containing
        this information cannot be found.
    :param consensus_weight_fraction: Fraction of this relay's consensus
        weight compared to the sum of all consensus weights in the network.
        This fraction is a very rough approximation of the probability of this
        relay to be selected by clients. :class:`py:None` if the relay is not
        running.
    :param guard_probability: Probability of this relay to be selected for the
        guard position. :class:`py:None` if the relay is not running, or the
        consensus does not contain bandwidth weights.
    :param middle_probability: Probability of this relay to be selected for
        the middle position. :class:`py:None` if the relay is not running, or
        the consensus does not contain bandwidth weights.
    :param exit_probability: Probability of this relay to be selected for the
        exit position. :class:`py:None` if the relay is not running, or the
        consensus does not contain bandwidth weights.
    :param measured: Boolean field saying whether the consensus weight of this
        relay is based on a threshold of 3 or more measurements by Tor
        bandwidth authorities. :class:`py:None` if the network status consensus
        containing this relay does not contain measurement information.
    :param unreachable_or_addresses: Array of IPv4 or IPv6 addresses and TCP
        ports or port lists where the relay claims in its descriptor to accept
        onion-routing connections but that the directory authorities failed to
        confirm as reachable. Contains only additional addresses of a relay
        that are found unreachable and only as long as a minority of directory
        authorities performs reachability tests on these additional addresses.
        Relays with an unreachable primary address are not included in the
        network status consensus and excluded entirely. Likewise, relays with
        unreachable additional addresses tested by a majority of directory
        authorities are not included in the network status consensus and
        excluded here, too. If at any point network status votes will be added
        to the processing, relays with unreachable addresses will be included
        here. Addresses are in arbitrary order. IPv6 hex characters are all
        lower-case. :class:`py:None` if empty.
    """

    nickname: None
    fingerprint: None
    or_addresses: None
    last_seen: None
    last_changed_address_or_port: None
    first_seen: None
    running: None
    consensus_weight: None
    exit_addresses: Optional[List[str]] = None
    dir_address: Optional[str] = None
    hibernating: Optional[bool] = None
    flags: Optional[List[Flag]] = None
    country: Optional[str] = None
    country_name: Optional[str] = None
    region_name: Optional[str] = None
    city_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    as_: Optional[str] = None
    as_name: Optional[str] = None
    verified_host_names: Optional[List[str]] = None
    unverified_host_names: Optional[List[str]] = None
    last_restarted: Optional[dt.datetime] = None
    bandwidth_rate: Optional[int] = None
    bandwidth_burst: Optional[int] = None
    observed_bandwidth: Optional[int] = None
    advertised_bandwidth: Optional[int] = None
    exit_policy: Optional[List[str]] = None
    exit_policy_summary: Optional[ExitPolicy] = None
    exit_policy_v6_summary: Optional[ExitPolicy] = None
    contact: Optional[str] = None
    platform: Optional[str] = None
    version: Optional[str] = None
    recommended_version: Optional[bool] = None
    version_status: Optional[str] = None
    effective_family: Optional[List[str]] = None
    alleged_family: Optional[List[str]] = None
    indirect_family: Optional[List[str]] = None
    consensus_weight_fraction: Optional[int] = None
    guard_probability: Optional[float] = None
    middle_probability: Optional[float] = None
    exit_probability: Optional[float] = None
    measured: Optional[bool] = None
    unreachable_or_addresses: Optional[List[str]] = None


@dataclass
class RelayDetails(RelayDetailsBase):
    """
    :class:`RelayDetails` specialisation where all fields had been requested.

    :param nickname: Relay nickname consisting of 1–19 alphanumerical
        characters.
    :param fingerprint: Relay fingerprint consisting of 40 upper-case
        hexadecimal characters.
    :param or_addresses: Array of IPv4 or IPv6 addresses and TCP ports or port
        lists where the relay accepts onion-routing connections. The first
        address is the primary onion-routing address that the relay used to
        register in the network, subsequent addresses are in arbitrary order.
    :param last_seen: UTC timestamp when this relay was last seen in a network
        status consensus.
    :param last_changed_address_or_port: UTC timestamp when this relay last
        stopped announcing an IPv4 or IPv6 address or TCP port where it
        previously accepted onion-routing or directory connections.
    :param first_seen: UTC timestamp when this relay was first seen in a
        network status consensus.
    :param running: Boolean field saying whether this relay was listed as
        running in the last relay network status consensus.
    :param consensus_weight: Weight assigned to this relay by the directory
        authorities that clients use in their path selection algorithm.
    """

    nickname: str
    fingerprint: str
    or_addresses: List[str]
    last_seen: dt.datetime
    last_changed_address_or_port: dt.datetime
    first_seen: dt.datetime
    running: bool
    consensus_weight: int

    @classmethod
    def from_json(cls, json: dict):
        """
        Instantiate a relay details document with JSON response from the API.

        :param json: Raw JSON response.
        """
        json["as_"] = json.pop("as", None)
        json["last_seen"] = utils.decode_utc(json.pop("last_seen"))
        json["last_changed_address_or_port"] = utils.decode_utc(
            json.pop("last_changed_address_or_port")
        )
        json["first_seen"] = utils.decode_utc(json.pop("first_seen"))
        json["last_restarted"] = utils.decode_utc(json.pop("last_restarted"))
        json["exit_policy_summary"] = ExitPolicy.from_json(
            json.pop("exit_policy_summary")
        )
        json["exit_policy_v6_summary"] = ExitPolicy.from_json(
            json.pop("exit_policy_v6_summary")
        )
        return cls(**json)


@dataclass
class PartialRelayDetails(RelayDetailsBase):
    """
    :class:`RelayDetails` specialisation where only specific fields had been
    requested.

    :param or_addresses: Potential array of IPv4 or IPv6 addresses and TCP
        ports or port lists where the relay accepts onion-routing connections.
        The first address is the primary onion-routing address that the relay
        used to register in the network, subsequent addresses are in arbitrary order.
    :param last_seen: Potential UTC timestamp when this relay was last seen in
        a network status consensus.
    :param last_changed_address_or_port: Potential UTC timestamp when this
        relay last stopped announcing an IPv4 or IPv6 address or TCP port
        where it previously accepted onion-routing or directory connections.
    :param first_seen: Potential UTC timestamp when this relay was first seen
        in a network status consensus.
    :param running: Potential boolean field saying whether this relay was
        listed as running in the last relay network status consensus.
    :param consensus_weight: Potential weight assigned to this relay by the
        directory authorities that clients use in their path selection algorithm.
    """

    nickname: Optional[str] = None
    fingerprint: Optional[str] = None
    or_addresses: Optional[List[str]] = None
    last_seen: Optional[dt.datetime] = None
    last_changed_address_or_port: Optional[dt.datetime] = None
    first_seen: Optional[dt.datetime] = None
    running: Optional[bool] = None
    consensus_weight: Optional[int] = None

    @classmethod
    def from_json(cls, json: dict):
        """
        Instantiate a relay details document with JSON response from the API.

        :param json: Raw JSON response.
        """
        if "as_" in json:
            json["as_"] = json.pop("as", None)
        if "last_seen" in json:
            json["last_seen"] = utils.decode_utc(json.pop("last_seen"))
        if "last_changed_address_or_port" in json:
            json["last_changed_address_or_port"] = utils.decode_utc(
                json.pop("last_changed_address_or_port")
            )
        if "last_seen" in json:
            json["first_seen"] = utils.decode_utc(json.pop("first_seen"))
        if "last_restarted" in json:
            json["last_restarted"] = utils.decode_utc(json.pop("last_restarted"))
        if "exit_policy_summary" in json:
            json["exit_policy_summary"] = ExitPolicy.from_json(
                json.pop("exit_policy_summary")
            )
        if "exit_policy_v6_summary" in json:
            json["exit_policy_v6_summary"] = ExitPolicy.from_json(
                json.pop("exit_policy_v6_summary")
            )
        return cls(**json)


@dataclass
class BridgeDetailsBase(Deserialisable):
    """
    Representation of the `bridge details document <https://metrics.torproject.org/onionoo.html#details_bridge>`_.

    :param nickname: Bridge nickname consisting of 1–19 alphanumerical
        characters.
    :param hashed_fingerprint: SHA-1 hash of the bridge fingerprint consisting
        of 40 upper-case hexadecimal characters.
    :param or_addresses: Array of sanitized IPv4 or IPv6 addresses and TCP
        ports or port lists where the bridge accepts onion-routing connections.
        The first address is the primary onion-routing address that the bridge
        used to register in the network, subsequent addresses are in arbitrary
        order.
    :param last_seen: UTC timestamp when the bridge was last seen in a bridge
        network status.
    :param first_seen: UTC timestamp when the bridge was first seen in a
        bridge network status.
    :param running: Boolean field saying whether the bridge was listed as
        running in the last bridge network status.
    :param flags: Array of relay flags that the bridge authority assigned to
        the bridge. :class:`python:None` if empty.
    :param last_restarted: UTC timestamp when the bridge was last
        (re-)started. :class:`python:None` if router descriptor containing
        this information cannot be found.
    :param advertised_bandwidth: Bandwidth in bytes per second that the
        bridge is willing and capable to provide. The bandwidth value is the
        minimum of `bandwidth_rate`, `bandwidth_burst`, and
        `observed_bandwidth`. :class:`python:None` if router descriptor
        containing this information cannot be found.
    :param platform: Platform string containing operating system and Tor
        version details. :class:`python:None` if not provided by the bridge or
        if descriptor containing this information cannot be found.
    :param version: Tor software version without leading "Tor" as reported by
        the bridge in the "platform" line of its server descriptor.
        :class:`python:None` if not provided by the bridge, if the descriptor
        containing this information cannot be found, or if the bridge runs an
        alternative Tor implementation.
    :param recommended_version: Boolean field saying whether the Tor software
        version of the bridge is recommended by the directory authorities or
        not. :class:`python:None` if either the directory authorities did not
        recommend versions, or the bridge did not report which version it runs.
    :param version_status: Status of the Tor software version of the bridge
        based on the versions recommended by the directory authorities.
        Possible version statuses are:
            - "recommended" if a version is listed as recommended;
            - "experimental" if a version is newer than every recommended
              version;
            - "obsolete" if a version is older than every recommended version;
            - "new in series" if a version has other recommended versions with
              the same first three components, and the version is newer than
              all such recommended versions, but it is not newer than every
              recommended version;
            - "unrecommended" if none of the above conditions hold.
        :class:`python:None` if either the directory authorities did not
        recommend versions, or the bridge did not report which version it runs.
    :param transports: Array of (pluggable) transport names supported by the
        bridge.
    :param bridgedb_distributor: BridgeDB distributor that the bridge is
        currently assigned to.
    """

    nickname: str
    hashed_fingerprint: str
    or_addresses: List[str]
    last_seen: dt.datetime
    first_seen: dt.datetime
    running: bool
    flags: Optional[List[Flag]] = None
    last_restarted: Optional[dt.datetime] = None
    advertised_bandwidth: Optional[int] = None
    platform: Optional[str] = None
    version: Optional[str] = None
    recommended_version: Optional[bool] = None
    version_status: Optional[str] = None
    transports: Optional[List[str]] = None
    bridgedb_distribtor: Optional[str] = None

    @classmethod
    def from_json(cls, json: dict):
        """
        Instantiate a bridge details document with JSON response from the API.

        :param json: Raw JSON response.
        """
        json["last_seen"] = utils.decode_utc(json["last_seen"])
        json["first_seen"] = utils.decode_utc(json["first_seen"])
        if "last_restarted" in json:
            json["last_restarted"] = utils.decode_utc(json["last_restarted"])
        return cls(**json)


@dataclass
class PartialBridgeDetails:
    """
    Representation of the `bridge details document <https://metrics.torproject.org/onionoo.html#details_bridge>`_
    where only specific fields had been requested.
    """

    nickname: Optional[str] = None
    hashed_fingerprint: Optional[str] = None
    or_addresses: Optional[List[str]] = None
    last_seen: Optional[dt.datetime] = None
    first_seen: Optional[dt.datetime] = None

    @classmethod
    def from_json(cls, json: dict):
        """
        Instantiate a bridge details document with JSON response from the API.

        :param json: Raw JSON response.
        """
        if "last_seen" in json:
            json["last_seen"] = utils.decode_utc(json["last_seen"])
        if "first_seen" in json:
            json["first_seen"] = utils.decode_utc(json["first_seen"])
        if "last_restarted" in json:
            json["last_restarted"] = utils.decode_utc(json["last_restarted"])
        return cls(**json)


@dataclass
class BridgeDetails:
    """
    Representation of the `bridge details document <https://metrics.torproject.org/onionoo.html#details_bridge>`_
    where only specific fields had been requested.
    """

    nickname: str
    hashed_fingerprint: str
    or_addresses: str
    last_seen: dt.datetime
    first_seen: dt.datetime


class GraphHistory(Deserialisable):
    """
    Representation of the `graph history document <https://metrics.torproject.org/onionoo.html#history_graph>`_.
    """

    def __init__(
        self,
        first: dt.datetime,
        last: dt.datetime,
        interval: int,
        factor: float,
        values: List[int],
        count: Optional[int] = None,
    ):
        """
        :param first: UTC timestamp of the interval midpoint of the first interval.
        :param last: UTC timestamp of the interval midpoint of the last interval.
        :param interval: Time interval between two datapoints in seconds.
        :param factor: Factor by which subsequent data values need to be multiplied
            to obtain original values.
        :param count: Number of provided data points.
        :param values: Array of normalized values between 0 and 999. May contain
            null values. Contains at least two subsequent non-null values to
            enable drawling of line graphs.
        """
        self.first = first
        self.last = last
        self.interval = interval
        self.factor = factor
        self.values = values
        self.count = count

    def denormalise(self) -> None:
        """
        Denormalise values, in place, by multiplyling each value by
        :py:attr:`self.factor`.
        """
        self.values = [value * self.factor for value in self.values]

    @classmethod
    def from_json(cls, json: dict):
        """
        Instantiate graph history document with JSON response from the API.

        :param json: Raw JSON response.
        :returns: the :class:`GraphHistory` instance.
        """
        json["first"] = utils.decode_utc(json.pop("first"))
        json["last"] = utils.decode_utc(json.pop("last"))
        obj = GraphHistory(**json)
        return obj

    def __repr__(self):
        return "{0.__class__.__name__}<{0.__dict__}>".format(self)


IntervaledHistory = Dict[str, GraphHistory]


def intervaled_history_from_json(json: dict) -> IntervaledHistory:
    """
    Instantiate intervaled history with JSON response from the API.

    :param json: Raw JSON response.
    """
    return {period: GraphHistory.from_json(value) for period, value in json.items()}


class BandwidthBase(Deserialisable):
    """
    Representation of the `bandwidth document <https://metrics.torproject.org/onionoo.html#bandwidth>`_.
    """

    def __init__(
        self,
        fingerprint: str,
        write_history: Optional[IntervaledHistory] = None,
        read_history: Optional[IntervaledHistory] = None,
    ):
        self.fingerprint = fingerprint
        self.write_history = write_history
        self.read_history = read_history

    def __repr__(self):
        return "{0.__class__.__name__}<{0.__dict__}>".format(self)


class RelayBandwidth(BandwidthBase):
    """
    Representation of the `bridge bandwidth document <https://metrics.torproject.org/onionoo.html#bandwidth_relay>`_.

    :param fingerprint: Relay fingerprint consisting of 40 upper-case
        hexadecimal characters.
    :param write_history: Historical observation of the relay's written bytes
        per second. :class:`python:None` if the relay did not provide bandwidth
        histories on the required level of detail.
    :param read_history: Historical observation of the relay's read bytes per
        second. :class:`python:None` if the relay did not provide bandwidth
        histories on the required level of detail.
    """

    @classmethod
    def from_json(cls, json: dict):
        """
        Instantiate :class:`RelayBandwidth` with JSON response from the API.

        :param json: Raw JSON response.
        :rtype: RelayBandwidth
        """
        write_history = intervaled_history_from_json(json["write_history"])
        read_history = intervaled_history_from_json(json["read_history"])
        return cls(
            fingerprint=json["fingerprint"],
            write_history=write_history,
            read_history=read_history,
        )


class BridgeBandwidth(BandwidthBase):
    """
    Representation of the `bridge bandwidth document <https://metrics.torproject.org/onionoo.html#bandwidth_bridge>`_.

    :param fingerprint: SHA-1 hash of the bridge fingerprint consisting of 40
        upper-case hexadecimal characters.
    :param write_history: Historical observation of the bridge's written bytes.
        :class:`python:None` if the relay did not provide bandwidth histories
        on the required level of detail.
    :param read_history: Historical observation of the bridges's read bytes.
        :class:`python:None` if the relay did not provide bandwidth histories
        on the required level of detail.
    """

    @classmethod
    def from_json(cls, json: dict):
        """
        Instantiate :class:`BridgeBandwidth` with JSON response from the API.

        :param json: Raw JSON response.
        :rtype: BridgeBandwidth
        """
        write_history = intervaled_history_from_json(json["write_history"])
        read_history = intervaled_history_from_json(json["read_history"])
        return cls(
            fingerprint=json["fingerprint"],
            write_history=write_history,
            read_history=read_history,
        )


@dataclass
class RelayWeight(Deserialisable):
    """
    Representation of the `relay weight document <https://metrics.torproject.org/onionoo.html#weights_relay>`_.
    """

    def __init__(
        self,
        fingerprint: str,
        consensus_weight_fraction: Optional[IntervaledHistory] = None,
        guard_probability: Optional[IntervaledHistory] = None,
        middle_probability: Optional[IntervaledHistory] = None,
        exit_probability: Optional[IntervaledHistory] = None,
        consensus_weight: Optional[IntervaledHistory] = None,
    ):
        """
        :param fingerprint: Relay fingerprint consisting of 40 upper-case
            hexadecimal characters.
        :param consensus_weight_fraction: Historical observation of the relay's
            consensus weight compared to the sum of all consensus weights in the network.
        :param guard_probability: Historical observation of the the relay's
            probability to be selected for guard position.
        :param middle_probability: Historical observation of the the relay's
            probability to be selected for middle position.
        :param exit_probability: Historical observation of the the relay's
            probability to be selected for exit position.
        :param consensus_weight: Historical observation of the absolute consensus
            weight of the relay.
        """
        self.fingerprint = fingerprint
        self.consensus_weight_fraction = consensus_weight_fraction
        self.guard_probability = guard_probability
        self.middle_probability = middle_probability
        self.exit_probability = exit_probability
        self.consensus_weight = consensus_weight

    @classmethod
    def from_json(cls, json: dict):
        """
        Instantiate a weight document with JSON response from the API.

        :param json: Raw JSON response.
        :returns: :class:`RelayWeight` instance.
        """
        consensus_weight_frac = intervaled_history_from_json(
            json["consensus_weight_fraction"]
        )
        guard_prob = intervaled_history_from_json(json["guard_probability"])
        middle_prob = intervaled_history_from_json(json["middle_probability"])
        exit_prob = intervaled_history_from_json(json["exit_probability"])
        consensus_weight = intervaled_history_from_json(json["consensus_weight"])

        return cls(
            fingerprint=json["fingerprint"],
            consensus_weight_fraction=consensus_weight_frac,
            guard_probability=guard_prob,
            middle_probability=middle_prob,
            exit_probability=exit_prob,
            consensus_weight=consensus_weight,
        )

    def __repr__(self):
        return "{0.__class__.__name__}<{0.__dict__}>".format(self)


class BridgeClients(Deserialisable):
    """
    Representation of the `bridge clients document <https://metrics.torproject.org/onionoo.html#clients_bridge>`_.
    """

    def __init__(
        self, fingerprint: str, average_clients: Optional[IntervaledHistory] = None
    ):
        """
        :param fingerprint: SHA-1 hash of the bridge fingerprint consisting of 40
            upper-case hexadecimal characters.
        :param average_clients: Historical observation of average number of
            clients connecting to the bridge.
        """
        self.fingerprint = fingerprint
        self.average_clients = average_clients

    @classmethod
    def from_json(cls, json: dict):
        """
        Instantiate a clients document with JSON response from the API.

        :param json: Raw JSON response.
        :rtype: BridgeClients
        """
        average_clients = intervaled_history_from_json(json["average_clients"])
        return cls(fingerprint=json["fingerprint"], average_clients=average_clients)


class RelayUptime(Deserialisable):
    """
    Representation of the `relay uptime document <https://metrics.torproject.org/onionoo.html#uptime_relay>`_.

    :param fingerprint: Relay fingerprint consisting of 40 upper-case
        hexadecimal characters.
    :param uptime: Historical observation of fractional uptime of the relay.
    :param flags: Historical observation of flag assignment.
    """

    fingerprint: str
    uptime: Optional[IntervaledHistory] = None
    flags: Optional[List[Flag]] = None

    @classmethod
    def from_json(cls, json: dict):
        """
        Instantiate a relay uptime document with JSON response from the API.

        :param json: Raw JSON response.
        :rtype: RelayUptime
        """

        uptime = intervaled_history_from_json(json["uptime"])
        flags = {
            Flag(flag): intervaled_history_from_json(history)
            for flag, history in json["flags"].items()
        }
        return cls(fingerprint=json["fingerprint"], uptime=uptime, flags=flags)

    def __repr__(self):
        return "{0.__class__.__name__}<{0.__dict__}>".format(self)


@dataclass
class BridgeUptime(Deserialisable):
    """
    Representation of the `bridge uptime document <https://metrics.torproject.org/onionoo.html#uptime_bridge>`_.

    :param fingerprint: SHA-1 hash of the bridge fingerprint consisting of 40
        upper-case hexadecimal characters.
    :param uptime: Historical observation of the fractional uptime of the relay.
    """

    fingerprint: str
    uptime: Optional[IntervaledHistory] = None

    @classmethod
    def from_json(cls, json: dict):
        """
        Instantiate a relay uptime document with JSON response from the API.

        :param json: Raw JSON response.
        :rtype: RelayUptime
        """

        uptime = intervaled_history_from_json(json["uptime"])
        return cls(fingerprint=json["fingerprint"], uptime=uptime)

    def __repr__(self):
        return "{0.__class__.__name__}<{0.__dict__}>".format(self)


RelayDescriptor = Union[
    RelaySummary,
    PartialRelayDetails,
    RelayDetails,
    RelayBandwidth,
    RelayWeight,
    RelayUptime,
]

BridgeDescriptor = Union[
    BridgeSummary,
    PartialBridgeDetails,
    BridgeDetails,
    BridgeBandwidth,
    BridgeClients,
    BridgeUptime,
]


@dataclass
class ResponseBase:
    """
    Representation of the API `response <https://metrics.torproject.org/onionoo.html#responses>`_.

    :param version: Onionoo protocol version string.
    :param next_major_version_scheduled: UTC date when the next major protocol
        version is scheduled to be deployed. :class:`python:None` if no major
        protocol changes are planned.
    :param build_revision: Git revision of the Onionoo instance's software
        used to write the response. :class:`python:None` if unknown.
    :param relays_published: UTC timestamp when the last known relay network
        status consensus started being valid.
    :param relays_skipped: Number of skipped relays as requested by a positive
        "offset" parameter value.
    :param relays: Potentially deserialised :class:`RelayDescriptor` objects.
    :param relays_truncated: Number of truncated relays as requested by a
        positive "limit" parameter value.
    :param bridges_skipped: Number of skipped bridges as requested by a
        positive "offset" parameter value.
    :param bridges: Potentially deserialised :class:`BridgeDescriptor` objects.
    :param bridges_truncated: Number of truncated bridges as requested by a
        positive "limit" parameter value.
    """

    version: str
    relays_published: dt.datetime
    bridges_published: dt.datetime
    relays: None
    bridges: None
    next_major_version_scheduled: Optional[dt.datetime] = None
    build_revision: Optional[str] = None
    relays_skipped: int = 0
    relays_truncated: int = 0
    bridges_skipped: int = 0
    bridges_truncated: int = 0


@dataclass
class PartialRawResponse(ResponseBase):
    """
    :class:`ResponseBase` specialisation with serialised `relays` and
    `bridges`.

    :param relays: Serialised relay documents.
    :param bridges: Serialised bridge documents.
    """

    relays: List[dict]
    bridges: List[dict]


@dataclass
class Response(ResponseBase):
    """
    :class:`ResponseBase` specialisation with deserialised `relays` and
    `bridges`.

    :param relays: Deserialised relay documents.
    :type relays: RelayDescriptor
    :param bridges: Deserialised bridge documents.
    :type bridges: BridgeDescriptor
    """

    relays: List[RelayDescriptor]
    bridges: List[BridgeDescriptor]
