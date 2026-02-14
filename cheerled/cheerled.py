#!/usr/bin/env python3

import sys
import os
import serial

all_address = (0xFF * 0x100) + 0xFF

options = {
  'colour' : {
    'red'             : 0xB0,
    'light_red'       : 0xB1,
    'orange'          : 0xB2,
    'light_orange'    : 0xB3,
    'yellow'          : 0xB4,
    'light_yellow'    : 0xB5,
    'green'           : 0xB6,
    'light_green'     : 0xB7,
    'rainbow'         : 0xB8,
    'light_rainbow'   : 0xB9,
    'vertical'        : 0xBA,
    'sawtooth'        : 0xBB,
    'green_red'       : 0xBC,
    'red_green'       : 0xBD,
    'orange_red'      : 0xBE,
    'yellow_green'    : 0xBF,
  },
  'font' : {
    'short'           : 0xA0,
    'short_wide'      : 0xA1,
    'default'         : 0xA2,
    'wide'            : 0xA3,
    'wider'           : 0xA4,
    'extra_wide'      : 0xA5,
    'small'           : 0xA6,
  },
  'beep' : {
    'alarm'           : 0xE0,
    'fire'            : 0xE1,
    'beep'            : 0xE2,
  },
  'speed' : {
    '0'               : 0xC0,
    '1'               : 0xC1,
    '2'               : 0xC2,
    '3'               : 0xC3,
    '4'               : 0xC4,
    '5'               : 0xC5,
    '6'               : 0xC6,
    '7'               : 0xC7,
  },
  'delay' : {
    'none'            : 0xC8,
    '1'               : 0xC9,
    '2'               : 0xCA,
    '3'               : 0xCB,
    '4'               : 0xCC,
    '5'               : 0xCD,
    '6'               : 0xCE,
    '7'               : 0xCF,
  },
  'animation' : {
    'cyclic'          : 0x01,
    'immediate'       : 0x02,
    'scroll_right'    : 0x03,
    'scroll_left'     : 0x04,
    'scroll_center'   : 0x05,
    'scroll_sides'    : 0x06,
    'cover_center'    : 0x07,
    'cover_right'     : 0x08,
    'cover_left'      : 0x09,
    'cover_sides'     : 0x0A,
    'scroll_up'       : 0x0B,
    'scroll_down'     : 0x0C,
    'interlace'       : 0x0D,
    'interlace_cover' : 0x0E,
    'cover_up'        : 0x0F,
    'cover_down'      : 0x10,
    'scanline'        : 0x11,
    'explode'         : 0x12,
    'pacman'          : 0x13,
    'fall'            : 0x14,
    'shoot'           : 0x15,
    'flash'           : 0x16,
    'random'          : 0x17,
    'slidein'         : 0x18,
    'auto'            : 0x19,
  },
}

coded = [ 'colour', 'font', 'speed', 'delay', 'beep' ]
option_order = [ 'animation', 'colour', 'font', 'speed', 'delay', 'beep' ]

sections = {
  'init'      : 0x0B,
  'message'   : 0x01,
  'special'   : 0x02,
  'alarm_opt' : 0x04,
  'hourly'    : 0x05,
  'auto_on'   : 0x06,
  'auto_off'  : 0x07,
  'set_time'  : 0x08,
  'set_image' : 0x0A,
}

weekdays = {
  'sunday'    : 0x01,
  'monday'    : 0x02,
  'tuesday'   : 0x04,
  'wednesday' : 0x08,
  'thursday'  : 0x10,
  'friday'    : 0x20,
  'saturday'  : 0x40,
  'all'       : 0x7F,
}


class SlcDevice(object):
    """Object for a SLC16H-IR device"""

    def __init__(self, device_node):
        self.output = serial.Serial(device_node, 2400, timeout=1)
        self.frames = []
        self.text_frame = None

    def send_packet(self, data, address=all_address):
        addr1 = address // 256
        addr2 = address % 256

        self.output_binary(0x00, addr1, addr2, 0x00)
        self.output_binary(self.init_section())
        self.output_binary(data)
        self.output_binary([0xFF, 0x00])

    def set_timer(self, timer, start, end, files='1', days='all'):
        if int(timer) < 1 or int(timer) > 9:
            raise KeyError("Timer Id out of bounds: %d, 1-9" % int(timer))

        result = [int(timer)]

        wks = 0
        if not isinstance(days, list):
            days = days.split(',')

        if 'all' in days:
            wks = weekdays['all']
        else:
            for w in days:
                if w in weekdays:
                    wks |= weekdays[w]

        result.append(wks)

        for time in (start, end):
            if not isinstance(time, list):
                time = time.split(':')
            if len(time) < 2:
                raise KeyError("Unknown Time: %s" % time)
            result += self.str_number(time[0], 2)
            result += self.str_number(time[1], 2)

        if not isinstance(files, list):
            files = files.split(',')

        for file in files:
            result += self.file_number(file)

        self.send_packet(self.generate_section('special', result))

    def set_hourly(self, set_val):
        result = [1 if set_val else 0]
        self.send_packet(self.generate_section('hourly', result))

    def set_alarm(self, repeat=1, pause=10):
        result = [int(repeat), int(pause)]
        self.send_packet(self.generate_section('alarm_opt', result))

    def set_auto(self, mode, time):
        if not isinstance(time, list):
            time = time.split(':')

        result = []
        result += self.str_number(time[0], 2)
        result += self.str_number(time[1], 2)
        result += self.str_number(time[2], 2)

        self.send_packet(self.generate_section('auto_' + mode, result))

    def update_time(self, date, time):
        result = [1, 1]

        if not isinstance(time, list):
            time = time.split(':')
        if not isinstance(date, list):
            date = date.split('-')

        result += self.str_number(date[0], 2)
        result += self.str_number(date[1], 2)
        result += self.str_number(date[2], 2)
        result += self.str_number(time[0], 2)
        result += self.str_number(time[1], 2)
        result += self.str_number(time[2], 2)

        self.send_packet(self.generate_section('set_time', result))

    def send_message(self, file=1):
        result = []
        result += self.file_number(file)

        self.new_text_frame()
        result += self.frames

        self.send_packet(self.generate_section('message', result))
        self.frames = []

    def str_number(self, number, size=2):
        num = str(number).zfill(size)
        return self.pack_str(num)

    def pack_str(self, text):
        return [ord(letter) for letter in text]

    def init_section(self):
        chars = list(range(128))
        return self.generate_section('init', self.generate_frame(chars))

    def text(self, text, **args):
        if not self.text_frame:
            self.text_frame = []

        for name in option_order:
            if name in args:
                self.text_frame.append(self.option_code(name, args[name]))

        text = text.replace('%time', chr(0xEF) + chr(0x80))
        text = text.replace('%date', chr(0xEF) + chr(0x81))

        self.text_frame.append(self.pack_str(text))

    def new_text_frame(self):
        if self.text_frame:
            self.frames.append(self.generate_frame(self.text_frame))
            self.text_frame = None

    def graphic(self, graphic):
        self.frames.append(
            self.generate_frame([0xEF, int(graphic) + 0xD0])
        )

    def generate_section(self, section, data):
        return [sections[section], data]

    def generate_frame(self, data):
        data.append(0xFF)
        return data

    def file_number(self, num=1):
        return self.str_number(num, 2)

    def code(self, key):
        return [0xEF, key]

    def option_code(self, option, value):
        if option in coded:
            return self.code(options[option][value])
        return [options[option][value]]

    def has_option(self, option, value):
        return option in options and value in options[option]

    def option_values(self, option):
        return sorted(options[option], key=options[option].__getitem__)

    def user_image(self, i_image=0):
        return self.code(0xD0 + i_image)

    def output_binary(self, *parts):
        for part in parts:
            if isinstance(part, (list, tuple)):
                self.output_binary(*part)
            else:
                self.output.write(bytes([part]))
    def builtin_graphic(self, num):
        """Insert a built-in graphic (1–8) into the current frame"""
        if not self.text_frame:
            self.text_frame = []
        self.text_frame.append([0xEF, 0x97 + int(num)])


    def builtin_cartoon(self, num):
        """Insert a built-in animated cartoon (1–8) into the current frame"""
        if not self.text_frame:
            self.text_frame = []
        self.text_frame.append([0xEF, 0x8F + int(num)])
