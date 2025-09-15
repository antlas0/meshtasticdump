import logging
import time
from .meshtastic_device import MeshtasticDevice
from .formatter import Formatter
from .exporter import Exporter
from .resources import FormatterKind
from .resources import ExporterKind

logger = logging.getLogger(__name__)


class Listener:
    def __init__(self, args:dict):
        formatkind = FormatterKind.RAW
        if args.formatter == "csv": formatkind = FormatterKind.CSV
        self.formatter = Formatter(formatkind)
        self.exporter = None
        if args.output_file is not None:
            self.exporter = Exporter(kind=ExporterKind.FILE)
            self.exporter.set_file_path(args.output_file)
        else:
            self.exporter = Exporter(kind=ExporterKind.STDOUT)

        self._md = MeshtasticDevice(packets_callback=self.handle_packet, include_local=args.include_local)
        self._device_uri = args.device

    def setup(self) -> bool:
        if self._device_uri is not None and self._device_uri:
            return self._md.connect_device(self._device_uri)
        return False

    def handle_packet(self, packet) -> None:
        formatted = self.formatter.format(packet)
        self.exporter.export(formatted)

    def run(self) -> None:
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.quit()
    
    def quit(self) -> None:
        self.formatter.quit()
        self.exporter.quit()