import base64
import meshtastic
import meshtastic.ble_interface
import meshtastic.serial_interface
import meshtastic.tcp_interface
from pubsub import pub
import logging
from typing import Optional, Any
import google.protobuf.json_format
import datetime

from .resources import Channel, Packet, PacketInfoType
from .resources import DeviceMetrics, LocalStats, EnvironmentMetrics, Position, Routing, NodeInfo, Message, Traceroute

logger = logging.getLogger(__name__)


class MeshtasticDevice:
    def __init__(self, packets_callback:Any, include_local:bool=False):
        self._interface = None
        self._local_board_id: str = ""
        self._channels = []
        self.packets_callback = packets_callback
        self.include_local = include_local
        self._nodes = None

    def get_channels(self) -> list:
        """Get the current channel settings from the node."""
        if self._interface is None:
            return []

        self._channels = []
        try:
            for channel in self._interface.localNode.channels:
                if channel.role != meshtastic.channel_pb2.Channel.Role.DISABLED:
                    self._channels.append(
                        Channel(
                            index=channel.index,
                            role=meshtastic.channel_pb2.Channel.Role.Name(channel.role),
                            name=channel.settings.name,
                            psk=base64.b64encode(
                                channel.settings.psk).decode('utf-8'),
                        )
                    )
        except Exception as e:
            logger.warning(f"Failed to get channels: {str(e)}")

    def connect_device(self, uri:str) -> bool:
        res = False
        if self._interface is not None:
            return res
        
        if uri.startswith("serial://"):
            uri = uri.replace("serial://", "")
            try:
                self._interface = meshtastic.serial_interface.SerialInterface(devPath=uri)
            except Exception as e:
                logger.warning(f"Failed to connect to Meshtastic device {uri}: {str(e)}")
                return False
        elif uri.startswith("ble://"):
            uri = uri.replace("ble://", "")
            try:
                self._interface = meshtastic.ble_interface.BLEInterface(uri)
            except Exception as e:
                logger.warning(f"Failed to connect to Meshtastic device {uri}: {str(e)}")
                return False
        elif uri.startswith("tcp://"):
            uri = uri.replace("tcp://", "")
            try:
                self._interface = meshtastic.tcp_interface.TCPInterface(hostname=uri)
            except Exception as e:
                logger.warning(f"Failed to connect to Meshtastic device {uri}: {str(e)}")
                return False
        else:
            logger.error(f"Not recognized. Device URI should start with either `serial://`, `ble://`, or `tcp://`.")
            return False

        pub.subscribe(self.on_receive, "meshtastic.receive")
        logger.info(f"Successfully connected to Meshtastic device {uri}")
        self.get_channels()
        node = self._interface.getMyNodeInfo()
        self._local_board_id = node["user"]["id"]
        logger.info(f"Local board id is {self._local_board_id}")
        res = True
        self._nodes = self._interface.nodesByNum
        return True

    def node_id_from_num(self, nodeNum) -> Optional[str]:
        """Convert node number to node ID"""
        node_id:Optional[str] = None
        
        if self._interface is None:
            return node_id

        for node in self._interface.nodesByNum.values():
            if node["num"] == nodeNum:
                node_id = node["user"]["id"]
                break
        if node_id is None: 
            node_id = f"!{nodeNum:08x}"
        return node_id

    def _extract_route_discovery(self, packet) -> list:
        route: list = []
        routeDiscovery = meshtastic.mesh_pb2.RouteDiscovery()
        try:
            routeDiscovery.ParseFromString(packet["decoded"]["payload"])
            asDict = google.protobuf.json_format.MessageToDict(routeDiscovery)
            route: list = [self._node_id_from_num(packet["to"])]
            if "route" in asDict:
                for nodeNum in asDict["route"]:
                    route.append(self._node_id_from_num(nodeNum))
            route.append(self.node_id_from_num(packet["from"]))
        except Exception as e:
            logging.warning(f"Could not extract route discovery {e}")

        return route

    def on_receive(self, packet, interface):
        node_id = self.node_id_from_num(packet["from"])

        if node_id == self._local_board_id and self.include_local is False:
            return

        is_packet_encrypted:bool=False
        try:
            decoded = packet['decoded']
        except KeyError:
            # encrypted packet
            decoded = {} 
            decoded["payload"] = "encrypted"
            decoded["portnum"] = "ENCRYPTED"
            is_packet_encrypted = True

        node = self._nodes.get(packet['from'], None)
        short_name, long_name = None, None
        try:
            short_name = node["user"]["shortName"]
            long_name = node["user"]["longName"]
        except Exception:
            pass

        received_packet = Packet(
            date=datetime.datetime.now(),
            pid=packet["id"],
            long_name=long_name,
            short_name=short_name,
            from_id=self.node_id_from_num(packet['from']),
            to_id=self.node_id_from_num(packet['to']),
            payload=decoded['payload'],
            port_num=decoded["portnum"],
            snr=packet["rxSnr"] if "rxSnr" in packet else None,
            rssi=packet["rxRssi"] if "rxRssi" in packet else None,
            hop_limit=packet["hopLimit"] if "hopLimit" in packet else None,
            hop_start=packet["hopStart"] if "hopStart" in packet else None,
            priority=packet["priority"] if "priority" in packet else None,
            relay_node=f"{packet['relayNode']:0x}" if "relayNode" in packet else None,
            next_hop=packet["nextHop"] if "nextHop" in packet else None,
        )
        if received_packet.hop_limit is not None and received_packet.hop_start is not None:
            received_packet.hopsaway = received_packet.hop_start - received_packet.hop_limit

        if not is_packet_encrypted:
            received_packet.channel_index=packet["channel"] if "channel" in packet else 0

            # decode payload
            decoded_payload = None
            if decoded["portnum"] == PacketInfoType.PCK_TELEMETRY_APP.value:
                env = meshtastic.telemetry_pb2.Telemetry()
                try:
                    env.ParseFromString(decoded["payload"])
                except Exception as e:
                    pass
                else:
                    if env.HasField("device_metrics"):
                        decoded_payload = DeviceMetrics()
                        decoded_payload.txairutil = round(env.device_metrics.air_util_tx, 2)
                        decoded_payload.battery_level = round(env.device_metrics.battery_level)
                        decoded_payload.channel_utilization = round(env.device_metrics.channel_utilization, 2)
                        decoded_payload.voltage = round(env.device_metrics.voltage, 2)
                        decoded_payload.uptime = env.device_metrics.uptime_seconds

                    if env.HasField("local_stats"):
                        decoded_payload = LocalStats()
                        decoded_payload.num_packets_tx = env.local_stats.num_packets_tx
                        decoded_payload.num_tx_relay = env.local_stats.num_tx_relay
                        decoded_payload.num_tx_relay_canceled = env.local_stats.num_tx_relay_canceled

                    if env.HasField("environment_metrics"):
                        decoded_payload = EnvironmentMetrics()
                        decoded_payload.temperature = env.environment_metrics.temperature
                        decoded_payload.relative_humidity = env.environment_metrics.relative_humidity
                        decoded_payload.barometric_pressure = env.environment_metrics.barometric_pressure

            if decoded["portnum"] == PacketInfoType.PCK_POSITION_APP.value:
                position = meshtastic.mesh_pb2.Position()
                try:
                    position.ParseFromString(decoded["payload"])

                except Exception as e:
                    pass
                else:
                    decoded_payload = Position()
                    if position.latitude_i != 0 and position.longitude_i != 0:
                        decoded_payload.lat = str(
                            round(position.latitude_i * 1e-7, 7))
                        decoded_payload.lon = str(
                            round(position.longitude_i * 1e-7, 7))
                        decoded_payload.alt = str(position.altitude)

            if decoded["portnum"] == PacketInfoType.PCK_ROUTING_APP.value:
                decoded_payload = Routing()
                decoded_payload.ack_label = decoded["routing"]["errorReason"]
                decoded_payload.message_id_acked = decoded["requestId"]
                decoded_payload.ack_by = packet['fromId']

            if decoded["portnum"] == PacketInfoType.PCK_TRACEROUTE_APP.value:
                decoded_payload = Traceroute()
                decoded_payload.route = self._extract_route_discovery(packet)

            if decoded["portnum"] == PacketInfoType.PCK_NODEINFO_APP.value:
                info = meshtastic.mesh_pb2.User()
                try:
                    info.ParseFromString(decoded["payload"])
                except Exception as e:
                    pass
                else:
                    decoded_payload = NodeInfo()
                    decoded_payload.long_name = info.long_name
                    decoded_payload.short_name = info.short_name
                    decoded_payload.hardware = meshtastic.mesh_pb2.HardwareModel.Name(info.hw_model)
                    decoded_payload.role = meshtastic.config_pb2.Config.DeviceConfig.Role.Name(info.role)
                    decoded_payload.public_key = str(info.public_key)

            if decoded["portnum"] == PacketInfoType.PCK_TEXT_MESSAGE_APP.value:
                data = decoded['payload']
                try:
                    current_message = data.decode('utf-8').strip()
                except UnicodeDecodeError:
                    logger.warning(f"Received non-text payload: {decoded['payload']}")
                else:
                    if len(current_message) > 0:
                        decoded_payload = Message()
                        decoded_payload.content = current_message
            
            received_packet.decoded = decoded_payload

        if self.packets_callback:
            self.packets_callback(received_packet)
