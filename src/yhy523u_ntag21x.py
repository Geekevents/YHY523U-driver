#!/usr/bin/python

import datetime
import os, sys, struct, serial


# Command header
HEADER = '\xAA\xBB'
# \x00\x00 according to API reference but only works with YHY632
# \xFF\xFF works for both.
RESERVED = '\xFF\xFF'



# Serial commands
CMD_SET_BAUDRATE = 0x0101
CMD_SET_NODE_NUMBER = 0x0102
CMD_READ_NODE_NUMBER = 0x0103
CMD_READ_FW_VERSION = 0x0104
CMD_BEEP = 0x0106
CMD_LED = 0x0107
CMD_RFU = 0x0108 # Unused according to API reference
CMD_WORKING_STATUS = 0x0108 # Unused according to API reference
CMD_ANTENNA_POWER = 0x010C


# NTAG command specification
CMD_NTAG_GET_VERSION = 0x60
CMD_NTAG_REQA = 0x26
CMD_NTAG_ANTICOLLISION_CL1 = 0x9320
CMD_NTAG_SELECT_CL1 = 0x9370
CMD_NTAG_ANTICOLLISION_CL2 = 0x9520
CMD_NTAG_SELECT_CL2 = 0x9570
CMD_NTAG_ANTICOLLISION = 0x9520
CMD_NTAG_SELECT = 0x9570
CMD_NTAG_WUPA = 0x52
CMD_NTAG_READ = 0x30
CMD_NTAG_FAST_READ = 0x3A
CMD_NTAG_WRITE = 0xA2
CMD_NTAG_COMPABILITY_WRITE = 0xA0
CMD_NTAG_READ_CNT = 0x39 # 0x02 == NFC counter address
CMD_NTAG_PWD_AUTH = 0x1B
CMD_NTAG_READ_SIG = 0x3C



# Error codes
ERR_BAUD_RATE = 1
ERR_PORT_OR_DISCONNECT = 2
ERR_GENERAL = 10
ERR_UNDEFINED = 11
ERR_COMMAND_PARAMETER = 12
ERR_NO_CARD = 13
ERR_REQUEST_FAILURE = 20
ERR_RESET_FAILURE = 21
ERR_AUTHENTICATE_FAILURE = 22
ERR_READ_BLOCK_FAILURE = 23
ERR_WRITE_BLOCK_FAILURE = 24
ERR_READ_ADDRESS_FAILURE = 25
ERR_WRITE_ADDRESS_FAILURE = 26

TYPE_NTAG_213 = 17408




class YHY523U:
    """Driver for Ehuoyan's YHY523U module"""
        
    def __init__(self, port='/dev/ttyUSB0', baudrate=115200):
        self.port = port
        self.baudrate = baudrate
        self.ser = serial.Serial(self.port, baudrate=self.baudrate)

    def build_command(self, cmd, data):
        """Build a serial command.

        Keyword arguments:
        cmd -- the serial command
        data -- the argument of the command

        """
        length = 2 + 2 + 1 + len(data)

        body_raw = RESERVED + struct.pack('<H', cmd) + data
        body = ''
        for b in body_raw:
            body += b
            if b == '\xAA':
                body += '\x00'

        body_int = map(ord, body)
        checksum = reduce(lambda x,y:  x^y, body_int)

        return HEADER + struct.pack('<H', length) + body + struct.pack('B', checksum)

    def get_n_bytes(self, n, handle_AA=False):
        """Read n bytes from the device.

        Keyword arguments:
        n -- the number of bytes to read
        handle_AA -- True to handle \xAA byte differently, False otherwise

        """
        buffer = ''
        while 1:
            received = self.ser.read()
            if handle_AA:
                if received.find('\xAA\x00') >= 0:
                    received = received.replace('\xAA\x00','\xAA')
                if received[0] == '\x00' and buffer[-1] == '\xAA':
                    received = received[1:]
            buffer += received

            if len(buffer) >= n:
                return buffer

    def send_command(self, cmd, data):
        """Send a serial command to the device.

        Keyword arguments:
        cmd -- the serial command
        data -- the argument of the command

        """
        buffer = self.build_command(cmd, data)
        self.ser.write(buffer)
        self.ser.flush()

    def receive_data(self):
        """Receive data from the device."""
        buffer = ''

        # Receive junk bytes
        prev_byte = '\x00'
        while 1:
            cur_byte = self.ser.read(1)
            if prev_byte + cur_byte == HEADER:
                # Header found, breaking
                break
            prev_byte = cur_byte

        length = struct.unpack('<H', self.get_n_bytes(2))[0]
        packet = self.get_n_bytes(length, True)

        reserved, command = struct.unpack('<HH', packet[:4])
        data = packet[4:-1]
        checksum = ord(packet[-1])

        packet_int = map(ord, packet[:-1])
        checksum_calc = reduce(lambda x,y: x^y, packet_int)
        if data[0] == '\x00':
            if checksum != checksum_calc:
                raise Exception, "bad checksum"
        return command, data

    def send_receive(self, cmd, data):
        """Send a serial command to the device and receive the answer.

        Keyword arguments:
        cmd -- the serial command
        data -- the argument of the command

        """
        self.send_command(cmd, data)
        cmd_received, data_received = self.receive_data()
        if cmd_received != cmd:
            raise Exception, "the command in answer is bad!"
        else:
            return ord(data_received[0]), data_received[1:]


    def select(self):
        """
        Select a NTAG card, returns the type and serial of the NTAG card.
        (Required to run before reading/writing to the card)
        """
        status, card_type = self.send_receive(CMD_NTAG_REQA, '')
        if status != 0:
            raise Exception, "No card found"

        status, serial = self.send_receive(CMD_NTAG_ANTICOLLISION, '')
        if status != 0:
            raise Exception, "Error in anticollision"

        card_type = struct.unpack('>H', card_type)[0]
        
        # No spacial caes that we need to handle that we know of at this point in time...

        self.send_receive(CMD_NTAG_SELECT, serial)

        # Need to continue to implement according to NTAG & YH523U spec..


        
