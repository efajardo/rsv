#!/usr/bin/env python

# System libraries
import os 
import re
import sys
import time
from optparse import OptionParser

# Custom RSV libraries
import RSV
import rc_metric


SUBMISSION_LIST_FORMATS = ['brief', 'long', 'full', 'log', 'out', 'err']
LIST_FORMATS = ['local'] + SUBMISSION_LIST_FORMATS


def process_options(arguments=None):
    usage = """usage: rsv-control [ --verbose ] 
      --help | -h 
      --version
      --list [ --wide | -w ] [ --all ] [ --format <format> ] [ <pattern> ]
      --on      [METRIC ...]
      --off     [METRIC ...]
      --enable  [--user <user>] --host <host-name> METRIC [METRIC ...]
      --disable --host <host-name> METRIC [METRIC ...]
    """

    version = "rsv-control 0.14"
    description = """This script is used to manage and test the RSV monitoring software."""

    parser = OptionParser(usage=usage, description=description, version=version)
    parser.add_option("--vdt-location", dest="vdt_location", default=None,
                      help="Root directory of the OSG installation", metavar="DIR")
    parser.add_option("-v", "--verbose", dest="verbose", default=1, type="int",
                      help="Verbosity level (0-3). [Default=%default]")
    parser.add_option("-l", "--list", action="store_true", dest="rsvctrl_list", default=False,
                      help="List metric information.  If <pattern> is supplied, only metrics matching the regular expression pattern will be displayed")
    parser.add_option("-w", "--wide", action="store_true", dest="list_wide", default=False,
                      help="Wide list display to avoid truncation in metric listing")
    parser.add_option("--all", action="store_true", dest="list_all", default=False,
                      help="Display all metrics, including metrics not enabled on any host.")
    parser.add_option("--format", dest="list_format", choices=tuple(LIST_FORMATS), default='local',
                      help="Specify the list format (%s; default: %%default)" % (LIST_FORMATS,))
    parser.add_option("--on", action="store_true", dest="rsvctrl_on", default=False,
                      help="Turn on all enabled metrics.  If a metric is specified, turn on only that metric.")
    parser.add_option("--off", action="store_true", dest="rsvctrl_off", default=False,
                      help="Turn off all running metrics.  If a metric is specified, turn off only that metric.")
    parser.add_option("--enable", action="store_true", dest="rsvctrl_enable", default=False,
                      help="Enable metric. May be specified multiple times.")
    parser.add_option("--disable", action="store_true", dest="rsvctrl_disable", default=False,
                      help="Disable metric. May be specified multiple times.")

    if arguments == None:
        (options, args) = parser.parse_args()
    else:
        (options, args) = parser.parse_args(arguments)

    #
    # Validate options
    #

    # Check for VDT_LOCATION
    if not options.vdt_location:
        options.vdt_location = RSV.get_osg_location()
    if not options.vdt_location:
        parser.error("VDT_LOCATION is not set.\nEither set this environment variable, or " +
                     "pass the --vdt-location command line option.")

    # Check that we got exactly one command
    number_of_commands = len([i for i in [options.rsvctrl_enable, options.rsvctrl_disable,
                                          options.rsvctrl_on, options.rsvctrl_off,
                                          options.rsvctrl_list] if i])
    if number_of_commands > 1:
        parser.error("You can use only one of list, enable, disable, on, or off.")
    if number_of_commands == 0:
        parser.error("Invalid syntax. You must specify one command.")

    return args, options




def main_rsv_control():
    """ Drive the program """

    # Process the command line
    args, options = process_options()

    rsv = RSV.RSV(options.vdt_location, options.verbose)

    # List the metrics
    if options.rsvctrl_list:
        if not args:
            return rc_metric.list_metrics(rsv, options, "")
        else:
            return rc_metric.list_metrics(rsv, options, args[0])



    
if __name__ == "__main__":
    progname = os.path.basename(sys.argv[0])
    if progname == 'rsv-control' or progname == 'rsv-control.py':
        if not main_rsv_control():
            sys.exit(1)
        else:
            sys.exit(0)
    else:
        print "Wrong invocation!"
        sys.exit(1)
