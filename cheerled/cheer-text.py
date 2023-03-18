#!/usr/bin/python
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
import os
from cheerled import SlcDevice

options = {
  '-c' : 'colour',
  '-a' : 'animation',
  '-f' : 'font',
  '-s' : 'speed',
  '-b' : 'beep',
  '-d' : 'delay',
}


def usage():
    """Print the usage of the tool"""
    return """
Usage:

  %s [DEVICE] [OPTIONS] Text Message

  Options:
    -c     - Colour
    -s     - Speed
    -f     - Font
    -a     - Animation
    -b     - Beep
    -d     - Delay
    -n     - New Frame
    --file - File Number
""" % sys.argv[0]


def invalid_option(name, value, default=None, options=None):
    """Print a warning about an invalid option"""
    sys.stderr.write("Invalid %s Option: '%s'" % (name.title(), value))
    if default:
        sys.stderr.write(" using '%s' instead" % default)
    sys.stderr.write("\n")
    if options:
        opts = "', '".join(options)
        sys.stderr.write("\n  Possible Values: '%s'\n\n" % (opts))


def set_text_messages(device, inputs):
    """Sets messages to the device"""
    args = {
        'animation' : 'immediate',
        'colour'    : 'yellow',
        'font'      : 'default',
    }
    set_file = False
    file = 1
    option = None
    for input in inputs:
        if set_file:
            file = int(input)
            continue
        if option != None:
            input = input.lower()
            if device.has_option(option, input):
                args[option] = input
            else:
                opts = device.option_values(option)
                invalid_option(option, input, args[option], opts)
            option = None
        elif options.has_key(input):
            option = options[input]
        elif input == '-n':
            device.new_text_frame()
        elif '--file' in input:
            if '=' in input:
                tag, value = input.split('=')
                file = int(value)
            else:
                set_file = True
        elif option == None:
            if "\n" in input:
                parts = input.split('\n')
                for part in parts:
                    device.text(part, **args)
                    device.new_text_frame()
            else:
                device.text(input, **args)
    device.send_message(file)


if len(sys.argv) < 3:
    print usage()
else:
    device = SlcDevice( sys.argv[1] )
    if device:
        set_text_messages(device, sys.argv[2:])


