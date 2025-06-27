#!/usr/bin/env python3

import re
import enum
import datetime
from dataclasses import dataclass, fields
from typing import Optional

BROADCAST_NAME = "^all"
BROADCAST_ADDR = "!ffffffff"
TIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f"
MAX_FILE_BYTES = 5*1024*1024

class FormatterKind(enum.Enum):
    UNKNOWN=0
    RAW=1
    CSV=2

class ExporterKind(enum.Enum):
    UNKNOWN=0
    STDOUT=1
    FILE=2

class ConnectionKind(enum.Enum):
    UNKNOWN=0
    SERIAL=1
    TCP=2
    BLE=3

@dataclass
class DateExporter:
    def date2str(self, time_format: str = TIME_FORMAT) -> None:
        """convert all fields of class to str format"""
        for f in fields(self):
            if isinstance(getattr(self, f.name), datetime.datetime):
                setattr(
                    self, f.name, getattr(self, f.name).strftime(time_format))

# FIXME: PORT_NUM retrived from packet is a str, not an integer thus 
# cannot compare with meshtastic.portnums_pb2.*
class PacketInfoType(enum.Enum):
    """
    Meshtastic packet type
    """
    PCK_TELEMETRY_APP = "TELEMETRY_APP"
    PCK_POSITION_APP = "POSITION_APP"
    PCK_TEXT_MESSAGE_APP = "TEXT_MESSAGE_APP"
    PCK_ROUTING_APP = "ROUTING_APP"
    PCK_TRACEROUTE_APP = "TRACEROUTE_APP"
    PCK_STORE_FORWARD_APP = "STORE_FORWARD_APP"
    PCK_NODEINFO_APP = "NODEINFO_APP"
    PCK_ADMIN_APP = "ADMIN_APP"
    PCK_RANGE_TEST_APP = "RANGE_TEST_APP"
    PCK_UNKNOWN = ""

@dataclass
class Channel:
    index: Optional[int] = None
    name: Optional[str] = None
    role: Optional[str] = None
    psk: Optional[str] = None

@dataclass
class DecodedPayload:
    def __repr__(self) -> str:
        strl = []
        for field in fields(self):
            strl.append(str(field))
        return " - ".join(strl)

@dataclass
class Packet(DateExporter):
    date: Optional[datetime.datetime]=None
    pid: Optional[str]=None
    long_name: Optional[str]=None
    short_name: Optional[str]=None
    from_id: Optional[str]=None
    to_id: Optional[str]=None
    channel_index: Optional[int]=None
    port_num: Optional[str]=None
    payload: Optional[bytes]=None
    snr: Optional[float] = None
    rssi: Optional[float] = None
    hop_limit: Optional[int] = None
    hop_start: Optional[int] = None
    hopsaway: Optional[int] = None
    relay_node: Optional[str] = None
    next_hop: Optional[str] = None
    decoded: Optional[DecodedPayload] = None
    priority: Optional[str] = None

@dataclass
class DeviceMetrics(DecodedPayload):
    txairutil: Optional[float]=None
    battery_level: Optional[float]=None
    channel_utilization: Optional[float]=None
    voltage: Optional[float]=None
    uptime: Optional[int]=None

@dataclass
class LocalStats(DecodedPayload):
    num_packets_tx: Optional[int]=None
    num_tx_relay: Optional[int]=None
    num_tx_relay_canceled: Optional[int]=None

@dataclass
class EnvironmentMetrics(DecodedPayload):
    temperature: Optional[float]=None
    relative_humidity: Optional[float]=None
    barometric_pressure: Optional[float]=None

@dataclass
class Position(DecodedPayload):
    lat: Optional[float]=None
    lon: Optional[float]=None
    altitude: Optional[float]=None

@dataclass
class NodeInfo(DecodedPayload):
    long_name: Optional[str]=None
    short_name: Optional[str]=None
    hardware: Optional[str]=None
    role: Optional[str]=None
    public_key: Optional[str]=None

@dataclass
class Message(DecodedPayload):
    content: Optional[str]=None

@dataclass
class Routing(DecodedPayload):
    ack_by: Optional[str]=None
    ack_label: Optional[str]=None
    message_id_acked: Optional[str]=None

@dataclass
class Traceroute(DecodedPayload):
    route: Optional[str]=None


