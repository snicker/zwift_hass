"""Patch zwift protobuf module before any zwift imports."""

import sys

from . import zwift_messages_pb2

sys.modules["zwift.zwift_messages_pb2"] = zwift_messages_pb2
