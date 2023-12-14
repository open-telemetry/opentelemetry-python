
# Copyright The OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# pylint: disable=too-many-lines

from enum import Enum

class NetworkAttributes:

    
    NETWORK_CARRIER_ICC = "network.carrier.icc"
    
    """
    The ISO 3166-1 alpha-2 2-character country code associated with the mobile carrier network.
    """

    
    NETWORK_CARRIER_MCC = "network.carrier.mcc"
    
    """
    The mobile carrier country code.
    """

    
    NETWORK_CARRIER_MNC = "network.carrier.mnc"
    
    """
    The mobile carrier network code.
    """

    
    NETWORK_CARRIER_NAME = "network.carrier.name"
    
    """
    The name of the mobile carrier.
    """

    
    NETWORK_CONNECTION_SUBTYPE = "network.connection.subtype"
    
    """
    This describes more details regarding the connection.type. It may be the type of cell technology connection, but it could be used for describing details about a wifi connection.
    """

    
    NETWORK_CONNECTION_TYPE = "network.connection.type"
    
    """
    The internet connection type.
    """
class NetworkConnectionSubtypeValues(Enum):
    GPRS = "gprs"
    """GPRS."""

    EDGE = "edge"
    """EDGE."""

    UMTS = "umts"
    """UMTS."""

    CDMA = "cdma"
    """CDMA."""

    EVDO_0 = "evdo_0"
    """EVDO Rel. 0."""

    EVDO_A = "evdo_a"
    """EVDO Rev. A."""

    CDMA2000_1XRTT = "cdma2000_1xrtt"
    """CDMA2000 1XRTT."""

    HSDPA = "hsdpa"
    """HSDPA."""

    HSUPA = "hsupa"
    """HSUPA."""

    HSPA = "hspa"
    """HSPA."""

    IDEN = "iden"
    """IDEN."""

    EVDO_B = "evdo_b"
    """EVDO Rev. B."""

    LTE = "lte"
    """LTE."""

    EHRPD = "ehrpd"
    """EHRPD."""

    HSPAP = "hspap"
    """HSPAP."""

    GSM = "gsm"
    """GSM."""

    TD_SCDMA = "td_scdma"
    """TD-SCDMA."""

    IWLAN = "iwlan"
    """IWLAN."""

    NR = "nr"
    """5G NR (New Radio)."""

    NRNSA = "nrnsa"
    """5G NRNSA (New Radio Non-Standalone)."""

    LTE_CA = "lte_ca"
    """LTE CA."""


class NetworkConnectionTypeValues(Enum):
    WIFI = "wifi"
    """wifi."""

    WIRED = "wired"
    """wired."""

    CELL = "cell"
    """cell."""

    UNAVAILABLE = "unavailable"
    """unavailable."""

    UNKNOWN = "unknown"
    """unknown."""

