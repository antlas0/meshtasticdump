
import logging
from .resources import FormatterKind, Packet

logger = logging.getLogger(__name__)


class Formatter:
    def __init__(self, kind: FormatterKind):
        self.kind = kind

    def format(self, packet:Packet) -> str:
        if self.kind == FormatterKind.RAW: return self.format_raw(packet)
        if self.kind == FormatterKind.CSV: return self.format_csv(packet)

    def format_csv(self, packet:Packet) -> str:
        return "NYI"

    def format_raw(self, packet:Packet) -> str:
        strl = []
        packet.date2str()
        for key in ["date", "pid", "long_name", "short_name", "from_id", "to_id", "channel_index", "port_num", "snr", "rssi", "hopsaway", "relay_node", "next_hop", "decoded"]:
            strl.append(str(getattr(packet, key)))
        return " | ".join(strl)
    
    def quit(self) -> None:
        pass

