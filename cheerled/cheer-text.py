#!/usr/bin/env python3
#
# Copyright (C) 2009 Martin Owens
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

import sys
from cheerled import SlcDevice

options = {
  '-c' : 'colour',
  '-a' : 'animation',
  '-f' : 'font',
  '-s' : 'speed',
  '-b' : 'beep',
  '-d' : 'delay',
}

graphics = {
    "1": 1, "city": 1,
    "2": 2, "traffic": 2,
    "3": 3, "coffee": 3,
    "4": 4, "telephone": 4,
    "5": 5, "outdoors": 5,
    "6": 6, "boat": 6,
    "7": 7, "swimming": 7,
    "8": 8, "unknown": 8,
}

cartoons = {
    "1": 1, "christmas": 1,
    "2": 2, "newyears": 2,
    "3": 3, "july4th": 3,
    "4": 4, "easter": 4,
    "5": 5, "halloween": 5,
    "6": 6, "drinkanddrive": 6,
    "7": 7, "nosmoking": 7,
    "8": 8, "welcome": 8,
}


def usage():
    return f"""
Usage:

  {sys.argv[0]} [DEVICE] [OPTIONS] Text Message

Options:
  -c             Colour
  -s             Speed
  -f             Font
  -a             Animation
  -b             Beep
  -d             Delay
  -n             New Frame
  --file N       File Number

  --graphic N|name
        1|city
        2|traffic
        3|coffee
        4|telephone
        5|outdoors
        6|boat
        7|swimming
        8|unknown
  --cartoon N|name
        1|christmas
        2|newyears
        3|july4th
        4|easter
        5|halloween
        6|drinkanddrive
        7|nosmoking
        8|welcome
"""


def invalid_option(name, value):
    sys.stderr.write(f"Invalid {name}: '{value}'\n")


def set_text_messages(device, inputs):

    args = {
        'animation': 'immediate',
        'colour': 'yellow',
        'font': 'default',
    }

    set_file = False
    set_graphic = False
    set_cartoon = False

    file = 1
    option = None

    for input_value in inputs:

        if set_file:
            file = int(input_value)
            set_file = False
            continue

        if set_graphic:
            key = input_value.lower()
            if key in graphics:
                device.builtin_graphic(graphics[key])
            else:
                invalid_option("graphic", input_value)
            set_graphic = False
            continue

        if set_cartoon:
            key = input_value.lower()
            if key in cartoons:
                device.builtin_cartoon(cartoons[key])
            else:
                invalid_option("cartoon", input_value)
            set_cartoon = False
            continue

        if option is not None:
            input_value = input_value.lower()

            if device.has_option(option, input_value):
                args[option] = input_value
            else:
                invalid_option(option, input_value)

            option = None

        elif input_value in options:
            option = options[input_value]

        elif input_value == '-n':
            device.new_text_frame()

        elif input_value.startswith('--file'):
            if '=' in input_value:
                _, value = input_value.split('=', 1)
                file = int(value)
            else:
                set_file = True

        elif input_value == '--graphic':
            set_graphic = True

        elif input_value.startswith('--graphic='):
            value = input_value.split('=', 1)[1].lower()
            if value in graphics:
                device.builtin_graphic(graphics[value])
            else:
                invalid_option("graphic", value)

        elif input_value == '--cartoon':
            set_cartoon = True

        elif input_value.startswith('--cartoon='):
            value = input_value.split('=', 1)[1].lower()
            if value in cartoons:
                device.builtin_cartoon(cartoons[value])
            else:
                invalid_option("cartoon", value)

        else:
            if "\n" in input_value:
                for part in input_value.split('\n'):
                    device.text(part, **args)
                    device.new_text_frame()
            else:
                device.text(input_value, **args)

    device.send_message(file)


if len(sys.argv) < 3:
    print(usage())
else:
    device = SlcDevice(sys.argv[1])
    set_text_messages(device, sys.argv[2:])
