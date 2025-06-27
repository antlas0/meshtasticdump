import logging
from logging.handlers import RotatingFileHandler
from .resources import ExporterKind, MAX_FILE_BYTES


logger = logging.getLogger(__name__)


class StdoutExporter:
    def __init__(self):
        pass

    def export(self, data:str) -> bool:
        logger.info(data)
        return True
    
    def quit(self) -> None:
        pass


class FileExporter:
    def __init__(self):
        self.export_logger = logging.getLogger("FileExporter")
        self.export_logger.setLevel(logging.DEBUG)
        self.export_logger.propagate = False
        self.handler = None

    def set_file_path(self, path) -> bool:
        self.handler = RotatingFileHandler(path, maxBytes=MAX_FILE_BYTES, backupCount=3)
        self.handler.setLevel(logging.DEBUG)
        self.handler.setFormatter(logging.Formatter("%(message)s"))
        self.export_logger.addHandler(self.handler)

    def export(self, data:str) -> bool:
        self.export_logger.debug(data)
    
    def quit(self) -> None:
        if self.file is not None:
            self.file.close()

class Exporter:
    def __new__(cls, kind):
        if kind == ExporterKind.STDOUT: return StdoutExporter()
        if kind == ExporterKind.FILE: return FileExporter()
        return Exporter()
