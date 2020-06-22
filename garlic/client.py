"""
Implementation of :class:`Client`.

.. currentmodule:: garlic.client
"""

import dataclasses
import datetime as dt
import functools
import inspect

from enum import Enum
from typing import Set, NewType, Union

import asks

from garlic import utils
from garlic.types import (
    Deserialisable,
    Response,
    PartialRawResponse,
    RelayBandwidth,
    BridgeBandwidth,
    BridgeSummary,
    RelaySummary,
    RelayWeight,
    BridgeClients,
    BridgeUptime,
    RelayUptime,
    BridgeDetails,
    RelayDetails,
    PartialBridgeDetails,
    PartialRelayDetails,
)
from garlic.exc import (
    HTTPError,
    NotFound,
    BadRequest,
    InternalServerError,
    ServiceUnavailable,
)


@dataclasses.dataclass
class ContentNotChanged:
    """
    HTTP response for 403 occurence when If-Modified-Since header is set.

    :param response: HTTP response.
    """

    response: asks.response_objects.Response


APIResponse = Union[Response, PartialRawResponse, ContentNotChanged]


def deserialise_response(
    response: APIResponse,
    relay_obj: Deserialisable = None,
    bridge_obj: Deserialisable = None,
) -> Union[Response, asks.response_objects.Response]:
    """
    Deserialise API response using bridge/relay deserialisation objects.
    Optionally return raw http response if :class:`ContentNotChanged`.

    :param response: API response.
    :param relay_obj: Object to deserialise array of relay descriptors into.
    :param bridge_obj: Object to deserialise array of bridge descriptors into.
    :returns: Serialised response or raw HTTP response.
    """
    if isinstance(response, ContentNotChanged):
        return response.response

    internal = dataclasses.asdict(response)
    if relay_obj:
        internal["relays"] = [relay_obj.from_json(r) for r in internal["relays"]]
    if bridge_obj:
        internal["bridges"] = [bridge_obj.from_json(b) for b in internal["bridges"]]
    return Response(**internal)


def onionoo_parameterised(restrict: Set[str] = None):
    """
    Handle generic passing of parameters to direct API functions.
    """
    if restrict is None:
        restrict = set()

    def sanitise(f):
        @functools.wraps(f)
        async def wraps(*args, **kwargs):
            if restrict & kwargs.keys():
                raise TypeError(
                    f"the following arguments are not allowed: {', '.join(restrict)}"
                )

            if "order" in kwargs:
                kwargs["order"] = ",".join(kwargs["order"])
            elif "fields" in kwargs:
                kwargs["fields"] = ",".join(kwargs["fields"])
            elif "flag" in kwargs:
                kwargs["flag"] = kwargs["flag"].value

            return await f(*args, **kwargs)

        return wraps

    return sanitise


class Endpoint(Enum):
    """
    Representation of API endpoints.

    :cvar BASE: API base endpoint.
    :cvar SUMMARY: Summary document endpoint.
    :cvar DETAILS: Details document endpoint.
    :cvar BANDWIDTH: Bandwidth document endpoint.
    :cvar WEIGHTS: Weights document endpoint.
    :cvar CLIENTS: Clients document endpoint.
    :cvar UPTIME: Uptime document endpoint.
    """

    BASE = "https://onionoo.torproject.org"
    SUMMARY = "/summary"
    DETAILS = "/details"
    BANDWIDTH = "/bandwidth"
    WEIGHTS = "/weights"
    CLIENTS = "/clients"
    UPTIME = "/uptime"


class Cache:
    def __init__(
        self, factory, enable_cache: bool = True, ttl: int = 3600, enable: bool = True
    ):
        self._factory = factory
        self._nested_call = False
        self.enable_cache = enable_cache
        self._ttl = dt.timedelta(seconds=ttl)
        self._cache = {}

    async def lookup(self, *args, **kwargs):
        if not self.enable_cache or self._nested_call:
            return None

        key = self.gen_key(*args, **kwargs)
        entry, timestamp = self._cache.get(key, (None, None))

        if entry is None:
            return None

        if timestamp + self._ttl < dt.datetime.utcnow():
            entry = await self.check_entry_lifetime(key, args, kwargs, timestamp)
        return entry

    def update(self, key, value):
        if not self.enable_cache:
            return
        self._cache[key] = (value, dt.datetime.utcnow() + self._ttl)

    async def check_entry_lifetime(self, key, args, kwargs, timestamp):
        value = await self._factory(
            *args,
            **kwargs,
            headers={"If-Modified-Since": timestamp.strftime(utils.UTC_FORMAT)},
        )
        if isinstance(value, ContentNotChanged):
            value = await self._factory(*args, **kwargs)

        self.update(key, value)
        return value

    def gen_key(self, *args, **kwargs):
        cache_key = [*args]

        def tuplise(mapping):
            items = []
            for key, value in mapping.items():
                if isinstance(value, dict):
                    items.extend((key, tuple(tuplise(value))))
                else:
                    items.append((key, value))
            return items

        cache_key.extend(tuplise(kwargs))
        return tuple(cache_key)


class Client:
    """
    Object to request resources from the Onionoo API.
    """

    def __init__(
        self,
        max_retries: int = 5,
        timeout: int = 60,
        enable_cache: bool = False,
        cache_ttl: int = 3600,
    ):
        """
        Instantiate object.

        :param max_retries: Maximum number of requests to the API per resource
            before bailing.
        :param timeout: Timeout for each request before issuing another
            request.
        :param enable_cache: Enable request caching.
        :param cache_ttl: Lifetime of each cache entry (seconds).
        """
        self._max_retries = max_retries
        self._timeout = timeout
        self._cache = Cache(self._request, enable_cache, cache_ttl)
        self._default_headers = {"Accept-Encoding": "gzip"}

    async def _request(
        self, verb: str, url: str, *args, **kwargs
    ) -> PartialRawResponse:
        """
        Issue request to Onionoo API.

        :param verb: HTTP verb.
        :param url: Destination URL.
        """
        if (entry := await self._cache.lookup(verb, url, *args, **kwargs)) is not None:
            return entry

        http_handlers = {
            200: lambda r: PartialRawResponse(**r.json()),
            304: ContentNotChanged,
            400: BadRequest,
            404: NotFound,
            500: InternalServerError,
            503: ServiceUnavailable,
        }

        headers = kwargs.pop("headers", {})
        headers.update(self._default_headers)

        for retry in range(self._max_retries):
            try:
                response = await asks.request(
                    verb, url, *args, headers=headers, **kwargs, timeout=self._timeout,
                )
            except asks.errors.RequestTimeout:
                continue

            retn = http_handlers.get(response.status_code, HTTPError)(response)
            if isinstance(retn, Exception):
                raise retn

            self._cache.update(self._cache.gen_key(verb, url, *args, **kwargs), retn)
            return retn

        raise HTTPError("maximum retries exceeded, bailing")

    @onionoo_parameterised(
        restrict={"fields",}
    )
    async def get_summary(self, **kwargs) -> Response:
        """
        Get summary document from API.

        :param str type: Specify to return only "relay" or "bridge"
            descriptors.
        :param bool running: Return only `running` bridges/or relays.
        :param str lookup: Return only the relay with the parameter value
            matching
            the fingerprint or the bridge with the parameter value matching
            the hashed fingerprint.
        :param str country: Return only relays which are located in the given
            country as identified by a two-letter country code. Filtering by
            country code is case-insensitive. The special country code xz can
            be used for relays that were not found in the GeoIP database.
        :param str as_: Return only relays which are located in either one of
            the given autonomous systems (AS) as identified by AS number (with
            or without preceding "AS" part). Multiple AS numbers can be
            provided separated by commas. Filtering by AS number is case
            insensitive.  The special AS number 0 can be used for relays that
            were not found in the GeoIP database.
        :param str as_name: Return only relays with the parameter value
            matching part of) the autonomous system (AS) name they are located
            in. If the parameter value contains spaces, only relays are
            returned which contain all space-separated parts in their AS
            name.
        :param Flag flag: Return only relays which have the given relay flag
            assigned by the directory authorities.
        :param str first_seen_days: Return only relays or bridges which have
            first been seen during the given range of days ago. A parameter
            value "x-y" with x <= y returns relays or bridges that have first
            been seen at least x and at most y days ago. Accepted short forms
            are "x", "x-", and "-y" which are interpreted as "x-x",
            "x-infinity", and "0-y".
        :param str last_seen_days: Return only relays or bridges which have
            last been seen during the given range of days ago. A parameter
            value "x-y" with x <= y returns relays or bridges that have last
            been seen at least x and at most y days ago. Accepted short forms
            are "x", "x-", and "-y" which are interpreted as "x-x",
            "x-infinity", and "0-y".
        :param str contact: Return only relays with the parameter value matching
            (part of) the contact line. If the parameter value contains spaces,
            only relays are returned which contain all space-separated parts
            in their contact line.
        :param str family: Return only the relay whose fingerprint matches the
            parameter value and all relays that this relay has listed in its
            family by fingerprint and that in turn have listed this relay in
            their family by fingerprint.
        :param str version: Return only relays or bridges running either Tor
            version from a list or range given in the parameter value. Tor
            versions must be provided without the leading "Tor" part. Multiple
            versions can either be provided as a comma-separated list (","),
            as a range separated by two dots (".."), or as a list of
            ranges.
        :param str os: Return only relays or bridges running on an operating
            system that starts with the parameter value.
        :param str host_name: Return only relays with a domain name ending in the
            given (partial) host name. Searches for subdomains of a specific
            domain should ideally be prefixed with a period, for example:
            ".csail.mit.edu".
        :param bool recommended_version: Return only relays and bridges
            running a Tor software version that is recommended if
            `recommended_version`
        :param Tuple[str] order: Re-order results by a comma-separated list of
            fields in ascending or descending order. Results are first ordered
            by the first list element, then by the second, and so on. Possible
            fields for ordering are: consensus_weight and first_seen. Field
            names are case-insensitive. Ascending order is the default;
            descending order is selected by prepending fields with a minus
            sign (-). Field names can be listed at most once in either
            ascending or descending order. Relays or bridges which don't have
            any value for a field to be ordered by are always appended to the
            end, regardless or sorting order.
        :param int offset: Skip the given number of relays and/or bridges.
            Relays are skipped first, then bridges.
        :param int limit: Limit result to the given number of relays and/or
            bridges.
        """
        url = "{0.value}{1.value}".format(Endpoint.BASE, Endpoint.SUMMARY)
        response = await self._request("GET", url, params=kwargs)
        return deserialise_response(
            response, relay_obj=RelaySummary, bridge_obj=BridgeSummary
        )

    @onionoo_parameterised()
    async def get_details(self, **kwargs) -> Response:
        """
        Get (partial)details document from API. Partial details are returned
        if the `fields` argument is applied.

        :param str type: Specify to return only "relay" or "bridge"
            descriptors.
        :param bool running: Return only `running` bridges/or relays.
        :param str lookup: Return only the relay with the parameter value
            matching
            the fingerprint or the bridge with the parameter value matching
            the hashed fingerprint.
        :param str country: Return only relays which are located in the given
            country as identified by a two-letter country code. Filtering by
            country code is case-insensitive. The special country code xz can
            be used for relays that were not found in the GeoIP database.
        :param str as_: Return only relays which are located in either one of
            the given autonomous systems (AS) as identified by AS number (with
            or without preceding "AS" part). Multiple AS numbers can be
            provided separated by commas. Filtering by AS number is case
            insensitive.  The special AS number 0 can be used for relays that
            were not found in the GeoIP database.
        :param str as_name: Return only relays with the parameter value
            matching part of) the autonomous system (AS) name they are located
            in. If the parameter value contains spaces, only relays are
            returned which contain all space-separated parts in their AS
            name.
        :param Flag flag: Return only relays which have the given relay flag
            assigned by the directory authorities.
        :param str first_seen_days: Return only relays or bridges which have
            first been seen during the given range of days ago. A parameter
            value "x-y" with x <= y returns relays or bridges that have first
            been seen at least x and at most y days ago. Accepted short forms
            are "x", "x-", and "-y" which are interpreted as "x-x",
            "x-infinity", and "0-y".
        :param str last_seen_days: Return only relays or bridges which have
            last been seen during the given range of days ago. A parameter
            value "x-y" with x <= y returns relays or bridges that have last
            been seen at least x and at most y days ago. Accepted short forms
            are "x", "x-", and "-y" which are interpreted as "x-x",
            "x-infinity", and "0-y".
        :param str contact: Return only relays with the parameter value matching
            (part of) the contact line. If the parameter value contains spaces,
            only relays are returned which contain all space-separated parts
            in their contact line.
        :param str family: Return only the relay whose fingerprint matches the
            parameter value and all relays that this relay has listed in its
            family by fingerprint and that in turn have listed this relay in
            their family by fingerprint.
        :param str version: Return only relays or bridges running either Tor
            version from a list or range given in the parameter value. Tor
            versions must be provided without the leading "Tor" part. Multiple
            versions can either be provided as a comma-separated list (","),
            as a range separated by two dots (".."), or as a list of
            ranges.
        :param str os: Return only relays or bridges running on an operating
            system that starts with the parameter value.
        :param str host_name: Return only relays with a domain name ending in the
            given (partial) host name. Searches for subdomains of a specific
            domain should ideally be prefixed with a period, for example:
            ".csail.mit.edu".
        :param bool recommended_version: Return only relays and bridges
            running a Tor software version that is recommended if
            `recommended_version`
        :param Tuple[str] fields: Tuple of specific fields to return for each
            bridge/relay descriptor object.
        :param Tuple[str] order: Re-order results by a comma-separated list of
            fields in ascending or descending order. Results are first ordered
            by the first list element, then by the second, and so on. Possible
            fields for ordering are: consensus_weight and first_seen. Field
            names are case-insensitive. Ascending order is the default;
            descending order is selected by prepending fields with a minus
            sign (-). Field names can be listed at most once in either
            ascending or descending order. Relays or bridges which don't have
            any value for a field to be ordered by are always appended to the
            end, regardless or sorting order.
        :param int offset: Skip the given number of relays and/or bridges.
            Relays are skipped first, then bridges.
        :param int limit: Limit result to the given number of relays and/or
            bridges.
        """
        url = "{0.value}{1.value}".format(Endpoint.BASE, Endpoint.DETAILS)
        response = await self._request("GET", url, params=kwargs)

        relay_obj = RelayDetails
        bridge_obj = BridgeDetails

        if "fields" in kwargs:
            relay_obj = PartialRelayDetails
            bridge_obj = PartialBridgeDetails

        return deserialise_response(
            response, relay_obj=relay_obj, bridge_obj=bridge_obj
        )

    @onionoo_parameterised(
        restrict={"fields",}
    )
    async def get_bandwidth(self, **kwargs) -> Response:
        """
        Get bandwidth document from API.

        :param str type: Specify to return only "relay" or "bridge"
            descriptors.
        :param bool running: Return only `running` bridges/or relays.
        :param str lookup: Return only the relay with the parameter value
            matching
            the fingerprint or the bridge with the parameter value matching
            the hashed fingerprint.
        :param str country: Return only relays which are located in the given
            country as identified by a two-letter country code. Filtering by
            country code is case-insensitive. The special country code xz can
            be used for relays that were not found in the GeoIP database.
        :param str as_: Return only relays which are located in either one of
            the given autonomous systems (AS) as identified by AS number (with
            or without preceding "AS" part). Multiple AS numbers can be
            provided separated by commas. Filtering by AS number is case
            insensitive.  The special AS number 0 can be used for relays that
            were not found in the GeoIP database.
        :param str as_name: Return only relays with the parameter value
            matching part of) the autonomous system (AS) name they are located
            in. If the parameter value contains spaces, only relays are
            returned which contain all space-separated parts in their AS
            name.
        :param Flag flag: Return only relays which have the given relay flag
            assigned by the directory authorities.
        :param str first_seen_days: Return only relays or bridges which have
            first been seen during the given range of days ago. A parameter
            value "x-y" with x <= y returns relays or bridges that have first
            been seen at least x and at most y days ago. Accepted short forms
            are "x", "x-", and "-y" which are interpreted as "x-x",
            "x-infinity", and "0-y".
        :param str last_seen_days: Return only relays or bridges which have
            last been seen during the given range of days ago. A parameter
            value "x-y" with x <= y returns relays or bridges that have last
            been seen at least x and at most y days ago. Accepted short forms
            are "x", "x-", and "-y" which are interpreted as "x-x",
            "x-infinity", and "0-y".
        :param str contact: Return only relays with the parameter value matching
            (part of) the contact line. If the parameter value contains spaces,
            only relays are returned which contain all space-separated parts
            in their contact line.
        :param str family: Return only the relay whose fingerprint matches the
            parameter value and all relays that this relay has listed in its
            family by fingerprint and that in turn have listed this relay in
            their family by fingerprint.
        :param str version: Return only relays or bridges running either Tor
            version from a list or range given in the parameter value. Tor
            versions must be provided without the leading "Tor" part. Multiple
            versions can either be provided as a comma-separated list (","),
            as a range separated by two dots (".."), or as a list of
            ranges.
        :param str os: Return only relays or bridges running on an operating
            system that starts with the parameter value.
        :param str host_name: Return only relays with a domain name ending in the
            given (partial) host name. Searches for subdomains of a specific
            domain should ideally be prefixed with a period, for example:
            ".csail.mit.edu".
        :param bool recommended_version: Return only relays and bridges
            running a Tor software version that is recommended if
            `recommended_version`
        :param Tuple[str] order: Re-order results by a comma-separated list of
            fields in ascending or descending order. Results are first ordered
            by the first list element, then by the second, and so on. Possible
            fields for ordering are: consensus_weight and first_seen. Field
            names are case-insensitive. Ascending order is the default;
            descending order is selected by prepending fields with a minus
            sign (-). Field names can be listed at most once in either
            ascending or descending order. Relays or bridges which don't have
            any value for a field to be ordered by are always appended to the
            end, regardless or sorting order.
        :param int offset: Skip the given number of relays and/or bridges.
            Relays are skipped first, then bridges.
        :param int limit: Limit result to the given number of relays and/or
            bridges.
        """
        url = "{0.value}{1.value}".format(Endpoint.BASE, Endpoint.BANDWIDTH)
        response = await self._request("GET", url, params=kwargs)
        return deserialise_response(
            response, relay_obj=RelayBandwidth, bridge_obj=BridgeBandwidth
        )

    @onionoo_parameterised(
        restrict={"fields",}
    )
    async def get_weights(self, **kwargs) -> Response:
        """
        Get weights document from API.

        :param str type: Specify to return only "relay" or "bridge"
            descriptors.
        :param bool running: Return only `running` bridges/or relays.
        :param str lookup: Return only the relay with the parameter value
            matching
            the fingerprint or the bridge with the parameter value matching
            the hashed fingerprint.
        :param str country: Return only relays which are located in the given
            country as identified by a two-letter country code. Filtering by
            country code is case-insensitive. The special country code xz can
            be used for relays that were not found in the GeoIP database.
        :param str as_: Return only relays which are located in either one of
            the given autonomous systems (AS) as identified by AS number (with
            or without preceding "AS" part). Multiple AS numbers can be
            provided separated by commas. Filtering by AS number is case
            insensitive.  The special AS number 0 can be used for relays that
            were not found in the GeoIP database.
        :param str as_name: Return only relays with the parameter value
            matching part of) the autonomous system (AS) name they are located
            in. If the parameter value contains spaces, only relays are
            returned which contain all space-separated parts in their AS
            name.
        :param Flag flag: Return only relays which have the given relay flag
            assigned by the directory authorities.
        :param str first_seen_days: Return only relays or bridges which have
            first been seen during the given range of days ago. A parameter
            value "x-y" with x <= y returns relays or bridges that have first
            been seen at least x and at most y days ago. Accepted short forms
            are "x", "x-", and "-y" which are interpreted as "x-x",
            "x-infinity", and "0-y".
        :param str last_seen_days: Return only relays or bridges which have
            last been seen during the given range of days ago. A parameter
            value "x-y" with x <= y returns relays or bridges that have last
            been seen at least x and at most y days ago. Accepted short forms
            are "x", "x-", and "-y" which are interpreted as "x-x",
            "x-infinity", and "0-y".
        :param str contact: Return only relays with the parameter value matching
            (part of) the contact line. If the parameter value contains spaces,
            only relays are returned which contain all space-separated parts
            in their contact line.
        :param str family: Return only the relay whose fingerprint matches the
            parameter value and all relays that this relay has listed in its
            family by fingerprint and that in turn have listed this relay in
            their family by fingerprint.
        :param str version: Return only relays or bridges running either Tor
            version from a list or range given in the parameter value. Tor
            versions must be provided without the leading "Tor" part. Multiple
            versions can either be provided as a comma-separated list (","),
            as a range separated by two dots (".."), or as a list of
            ranges.
        :param str os: Return only relays or bridges running on an operating
            system that starts with the parameter value.
        :param str host_name: Return only relays with a domain name ending in the
            given (partial) host name. Searches for subdomains of a specific
            domain should ideally be prefixed with a period, for example:
            ".csail.mit.edu".
        :param bool recommended_version: Return only relays and bridges
            running a Tor software version that is recommended if
            `recommended_version`
        :param Tuple[str] order: Re-order results by a comma-separated list of
            fields in ascending or descending order. Results are first ordered
            by the first list element, then by the second, and so on. Possible
            fields for ordering are: consensus_weight and first_seen. Field
            names are case-insensitive. Ascending order is the default;
            descending order is selected by prepending fields with a minus
            sign (-). Field names can be listed at most once in either
            ascending or descending order. Relays or bridges which don't have
            any value for a field to be ordered by are always appended to the
            end, regardless or sorting order.
        :param int offset: Skip the given number of relays and/or bridges.
            Relays are skipped first, then bridges.
        :param int limit: Limit result to the given number of relays and/or
            bridges.
        """

        url = "{0.value}{1.value}".format(Endpoint.BASE, Endpoint.WEIGHTS)
        response = await self._request("GET", url, params=kwargs)
        return deserialise_response(response, relay_obj=RelayWeight)

    @onionoo_parameterised(
        restrict={"fields","host_name","country","family","flag","contact"}
    )
    async def get_clients(self, **kwargs) -> Response:
        """
        Get clients document from API.

        :param str type: Specify to return only "relay" or "bridge"
            descriptors.
        :param bool running: Return only `running` bridges/or relays.
        :param str lookup: Return only the relay with the parameter value
            matching
            the fingerprint or the bridge with the parameter value matching
            the hashed fingerprint.
        :param str as_: Return only relays which are located in either one of
            the given autonomous systems (AS) as identified by AS number (with
            or without preceding "AS" part). Multiple AS numbers can be
            provided separated by commas. Filtering by AS number is case
            insensitive.  The special AS number 0 can be used for relays that
            were not found in the GeoIP database.
        :param str as_name: Return only relays with the parameter value
            matching part of) the autonomous system (AS) name they are located
            in. If the parameter value contains spaces, only relays are
            returned which contain all space-separated parts in their AS
            name.
        :param str first_seen_days: Return only relays or bridges which have
            first been seen during the given range of days ago. A parameter
            value "x-y" with x <= y returns relays or bridges that have first
            been seen at least x and at most y days ago. Accepted short forms
            are "x", "x-", and "-y" which are interpreted as "x-x",
            "x-infinity", and "0-y".
        :param str last_seen_days: Return only relays or bridges which have
            last been seen during the given range of days ago. A parameter
            value "x-y" with x <= y returns relays or bridges that have last
            been seen at least x and at most y days ago. Accepted short forms
            are "x", "x-", and "-y" which are interpreted as "x-x",
            "x-infinity", and "0-y".
        :param str version: Return only relays or bridges running either Tor
            version from a list or range given in the parameter value. Tor
            versions must be provided without the leading "Tor" part. Multiple
            versions can either be provided as a comma-separated list (","),
            as a range separated by two dots (".."), or as a list of
            ranges.
        :param str os: Return only relays or bridges running on an operating
            system that starts with the parameter value.
        :param bool recommended_version: Return only relays and bridges
            running a Tor software version that is recommended if
            `recommended_version`
        :param Tuple[str] order: Re-order results by a comma-separated list of
            fields in ascending or descending order. Results are first ordered
            by the first list element, then by the second, and so on. Possible
            fields for ordering are: consensus_weight and first_seen. Field
            names are case-insensitive. Ascending order is the default;
            descending order is selected by prepending fields with a minus
            sign (-). Field names can be listed at most once in either
            ascending or descending order. Relays or bridges which don't have
            any value for a field to be ordered by are always appended to the
            end, regardless or sorting order.
        :param int offset: Skip the given number of relays and/or bridges.
            Relays are skipped first, then bridges.
        :param int limit: Limit result to the given number of relays and/or
            bridges.
        """
        url = "{0.value}{1.value}".format(Endpoint.BASE, Endpoint.CLIENTS)
        response = await self._request("GET", url, params=kwargs)
        return deserialise_response(response, bridge_obj=BridgeClients)

    @onionoo_parameterised(
        restrict={"fields",}
    )
    async def get_uptime(self, **kwargs) -> Response:
        """
        Get uptime document from API.

        :param str type: Specify to return only "relay" or "bridge"
            descriptors.
        :param bool running: Return only `running` bridges/or relays.
        :param str lookup: Return only the relay with the parameter value
            matching
            the fingerprint or the bridge with the parameter value matching
            the hashed fingerprint.
        :param str country: Return only relays which are located in the given
            country as identified by a two-letter country code. Filtering by
            country code is case-insensitive. The special country code xz can
            be used for relays that were not found in the GeoIP database.
        :param str as_: Return only relays which are located in either one of
            the given autonomous systems (AS) as identified by AS number (with
            or without preceding "AS" part). Multiple AS numbers can be
            provided separated by commas. Filtering by AS number is case
            insensitive.  The special AS number 0 can be used for relays that
            were not found in the GeoIP database.
        :param str as_name: Return only relays with the parameter value
            matching part of) the autonomous system (AS) name they are located
            in. If the parameter value contains spaces, only relays are
            returned which contain all space-separated parts in their AS
            name.
        :param Flag flag: Return only relays which have the given relay flag
            assigned by the directory authorities.
        :param str first_seen_days: Return only relays or bridges which have
            first been seen during the given range of days ago. A parameter
            value "x-y" with x <= y returns relays or bridges that have first
            been seen at least x and at most y days ago. Accepted short forms
            are "x", "x-", and "-y" which are interpreted as "x-x",
            "x-infinity", and "0-y".
        :param str last_seen_days: Return only relays or bridges which have
            last been seen during the given range of days ago. A parameter
            value "x-y" with x <= y returns relays or bridges that have last
            been seen at least x and at most y days ago. Accepted short forms
            are "x", "x-", and "-y" which are interpreted as "x-x",
            "x-infinity", and "0-y".
        :param str contact: Return only relays with the parameter value matching
            (part of) the contact line. If the parameter value contains spaces,
            only relays are returned which contain all space-separated parts
            in their contact line.
        :param str family: Return only the relay whose fingerprint matches the
            parameter value and all relays that this relay has listed in its
            family by fingerprint and that in turn have listed this relay in
            their family by fingerprint.
        :param str version: Return only relays or bridges running either Tor
            version from a list or range given in the parameter value. Tor
            versions must be provided without the leading "Tor" part. Multiple
            versions can either be provided as a comma-separated list (","),
            as a range separated by two dots (".."), or as a list of
            ranges.
        :param str os: Return only relays or bridges running on an operating
            system that starts with the parameter value.
        :param str host_name: Return only relays with a domain name ending in the
            given (partial) host name. Searches for subdomains of a specific
            domain should ideally be prefixed with a period, for example:
            ".csail.mit.edu".
        :param bool recommended_version: Return only relays and bridges
            running a Tor software version that is recommended if
            `recommended_version`
        :param Tuple[str] order: Re-order results by a comma-separated list of
            fields in ascending or descending order. Results are first ordered
            by the first list element, then by the second, and so on. Possible
            fields for ordering are: consensus_weight and first_seen. Field
            names are case-insensitive. Ascending order is the default;
            descending order is selected by prepending fields with a minus
            sign (-). Field names can be listed at most once in either
            ascending or descending order. Relays or bridges which don't have
            any value for a field to be ordered by are always appended to the
            end, regardless or sorting order.
        :param int offset: Skip the given number of relays and/or bridges.
            Relays are skipped first, then bridges.
        :param int limit: Limit result to the given number of relays and/or
            bridges.
        """
        url = "{0.value}{1.value}".format(Endpoint.BASE, Endpoint.UPTIME)
        response = await self._request("GET", url, params=kwargs)
        return deserialise_response(
            response, relay_obj=RelayUptime, bridge_obj=BridgeUptime
        )
