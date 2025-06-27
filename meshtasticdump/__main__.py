import logging
import argparse

from .listener import Listener

logging.basicConfig(format='%(message)s')
logging.getLogger().setLevel(logging.INFO)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Meshtastic packets dumper"
    )

    parser.add_argument("-d", "--device", action="store", default=None, help="URI to device. serial:///dev/ttyUBS0 or ble://AA:BB:CC:DD:EE:FF",type=str,)
    parser.add_argument("-l", "--include-local", action="store_true", default=False, help="Include local packets from local device",)
    parser.add_argument("-f", "--formatter", action="store", default="raw", help="Choose formatter, raw or csv, default raw.",)
    parser.add_argument("-o", "--output-file", action="store", default=None, help="Write logs to file")

    args = parser.parse_args()
    l = Listener(args)
    if l.setup():
        l.run()


if __name__ == "__main__":
    main()
