import binascii
import logging
import socket

from .client import Client

CMD_SET_POWER_STATE = b'\x18'
CMD_GET_POWER_STATE = b'\x19'
CMD_SET_VOLUME = b'\x44'
CMD_GET_VOLUME = b'\x45'
CMD_SET_INPUT_SOURCE = b'\xAC'
CMD_GET_INPUT_SOURCE = b'\xAD'
CMD_GET_INFO = b'\xA1'
CMD_GET_VERSION = b'\xA2'
CMD_IR = b'\xDB'

MODEL_INFO_MODEL_NUMBER = b'\x00'
MODEL_INFO_FW_VERSION = b'\x01'
MODEL_INFO_BUILD_DATE = b'\x02'

VERSION_INFO_OTSC_IMPLEMENTATION_VERSION = b'\x00'
VERSION_INFO_PLATFORM_LABEL = b'\x01'
VERSION_INFO_PLATFORM_VERSION = b'\x02'

VAL_POWER_OFF = b'\x01'
VAL_POWER_ON = b'\x02'

IR_POWER = b'\xA0'
IR_MENU = b'\xA1'
IR_INPUT = b'\xA2'
IR_VOL_UP = b'\xA3'
IR_VOL_DOWN = b'\xA4'
IR_MUTE = b'\xA5'
IR_CURSOR_UP = b'\xA6'
IR_CURSOR_DOWN = b'\xA7'
IR_CURSOR_LEFT = b'\xA8'
IR_CURSOR_RIGHT = b'\xA9'
IR_OK = b'\xB1'
IR_RETURN = b'\xB2'
IR_RED = b'\xC1'
IR_GREEN = b'\xC2'
IR_YELLOW = b'\xC3'
IR_BLUE = b'\xC4'
IR_FORMAT = b'\xD1'
IR_INFO = b'\xD2'
IR_BTN_0 = b'\x00'
IR_BTN_1 = b'\x01'
IR_BTN_2 = b'\x02'
IR_BTN_3 = b'\x03'
IR_BTN_4 = b'\x04'
IR_BTN_5 = b'\x05'
IR_BTN_6 = b'\x06'
IR_BTN_7 = b'\x07'
IR_BTN_8 = b'\x08'
IR_BTN_9 = b'\x09'

INPUT_SOURCES = {
    "HDMI 1": 0x0D,
    "HDMI 2": 0x06,
    "HDMI 3": 0x0F,
    "HDMI 4": 0x19,

    "Display Port 1": 0x0A,
    "Display Port 2": 0x07,
    "Display Port": 0x01,

    "USB 1": 0x0C,
    "USB 2": 0x08,

    "VIDEO": 0x00,
    "S-VIDEO": 0x02,
    "COMPONENT": 0x03,
    "VGA": 0x05,
    "DVI-D": 0x0E,

    "Card DVI-D": 0x09,
    "Card OPS": 0x0B,

    "BROWSER": 0x10,
    "SMARTCMS": 0x11,
    "INTERNAL STORAGE": 0x13,
    "Media Player": 0x16,
    "PDF Player": 0x17,
    "DMS (Digital Media Server)": 0x12,
    "Reserved": 0x14,
    "Custom": 0x18,
}


class Commands:

    def __init__(self, client: Client, id=b'\x01'):
        self._logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__qualname__}")
        self._client = client
        self._id = id

    def get_power_state(self):
        self._logger.debug("get_power_state")
        try:
            result = self._client.send(self._id, CMD_GET_POWER_STATE)
            match result:
                case b'\x01':
                    return False
                case b'\x02':
                    return True
                case None:
                    self._logger.warning("No power state retrieved.")
                    return None
                case _:
                    self._logger.warning("Unknown power state: %s" % binascii.hexlify(result))
                    return None
        except socket.error:
            return None

    def set_power_state(self, state: bool):
        self._logger.debug("set_power_state(%s)" % state)
        self._client.send(self._id, CMD_SET_POWER_STATE, VAL_POWER_ON if state else VAL_POWER_OFF)

    def get_volume(self):
        self._logger.debug("get_volume")
        response = self._client.send(self._id, CMD_GET_VOLUME)
        if response:
            return [b for b in response]

    def set_volume(self, volume=None, output_volume=None):
        self._logger.debug("set_volume(%s, %s)" % (volume, output_volume))
        if volume is None:
            volume = output_volume
        if output_volume is None:
            output_volume = volume
        if output_volume is None or volume is None:
            raise CommandException("Volume or output volume must be set.")
        self._client.send(self._id, CMD_SET_VOLUME, bytearray([volume, output_volume]))

    def get_input_source(self):
        self._logger.debug("get_input_source")
        response = self._client.send(self._id, CMD_GET_INPUT_SOURCE)
        if response:
            return [b for b in response]

    def set_input_source(self, input_type=0, input_number=0, osd_style=0, reserved=0):
        self._logger.debug("set_input_source(%s, %s, %s, %s)" % (input_type, input_number, osd_style, reserved))
        self._client.send(self._id, CMD_SET_INPUT_SOURCE, bytearray([input_type, input_number, osd_style, reserved]))

    def get_osc_implementation_version(self):
        self._logger.debug("get_osc_implementation_version")
        return self._get_string(CMD_GET_VERSION, bytes(VERSION_INFO_OTSC_IMPLEMENTATION_VERSION))

    def get_platform_label(self):
        self._logger.debug("get_platform_label")
        return self._get_string(CMD_GET_VERSION, bytes(VERSION_INFO_PLATFORM_LABEL))

    def get_platform_version(self):
        self._logger.debug("get_platform_version")
        return self._get_string(CMD_GET_VERSION, bytes(VERSION_INFO_PLATFORM_VERSION))

    def get_model_number(self):
        self._logger.debug("get_model_number")
        return self._get_string(CMD_GET_INFO, bytes(MODEL_INFO_MODEL_NUMBER))

    def get_fw_version(self):
        self._logger.debug("get_fw_version")
        return self._client.send(CMD_GET_INFO, bytes(MODEL_INFO_FW_VERSION))

    def get_build_date(self):
        self._logger.debug("get_build_date")
        return self._client.send(CMD_GET_INFO, bytes(MODEL_INFO_BUILD_DATE))

    def _get_string(self, cmd, data):
        response = self._client.send(self._id, cmd, data)
        if response:
            return response.decode('utf-8')

    def ir_command(self, code):
        self._logger.debug("ir_command(%s)" % binascii.hexlify(code))
        self._client.send(self._id, CMD_IR, code)

    def disconnect(self):
        self._client.close()


class CommandException(Exception):
    pass
