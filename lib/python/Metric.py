#!/usr/bin/env python

import os
import re
import sys
import ConfigParser

class Metric:
    rsv = None
    name = None
    host = None
    config = None
    conf_dir = None
    executable = None

    def __init__(self, metric, rsv, defaults=None, host=None):
        # Initialize vars
        self.name = metric
        self.rsv  = rsv
        self.conf_dir = os.path.join(rsv.rsv_location, "etc", "metrics")

        # Find executable
        self.executable = os.path.join(rsv.rsv_location, "bin", "metrics", metric)
        if not os.path.exists(self.executable):
            rsv.log("ERROR", "Metric does not exist at %s" % self.executable)
            sys.exit(1)

        if host:
            self.host = host

        self.config = ConfigParser.RawConfigParser()
        self.config.optionxform = str
        self.load_config(defaults)


    def load_config(self, defaults):

        if defaults:
            for section in defaults.keys():
                if not self.config.has_section(section):
                    self.config.add_section(section)
                    
                for item in defaults[section].keys():
                    self.config.set(section, item, defaults[section][item])

        # Load the metric's general configuration file
        file = os.path.join(self.conf_dir, self.name + ".conf")
        if not os.path.exists(file):
            self.rsv.log("ERROR", "Metric config file '%s' does not exist" % file)
            return
        else:
            self.config.read(file)

        # If this is for a specified host, load the metric/host config file
        if self.host:
            file = os.path.join(self.conf_dir, self.host, self.name + ".conf")
            if not os.path.exists(file):
                self.rsv.log("INFO", "Metric/host config file '%s' does not exist" % file)
            else:
                self.config.read(file)
        

    def get_type(self):
        """ Return the serviceType """

        try:
            return config.get(self.name, "service-type")
        except ConfigParser.NoOptionError:
            self.rsv.log("ERROR", "Metric '%s' missing serviceType" % self.name)
            return "UNKNOWN"


    def config_get(self, key):
        try:
            return self.config.get(self.name, key)
        except ConfigParser.NoOptionError:
            self.rsv.log("DEBUG", "metric.config_get - no key '%s'" % key)
            return None


    def config_val(self, key, value, case_sensitive=0):
        """ Check if key is in config, and if it equals val. """

        try:
            if case_sensitive == 0:
                if self.config.get(self.name, key).lower() == str(value).lower():
                    return True
            else:
                if self.config.get(self.name, key) == str(value):
                    return True
        except ConfigParser.NoOptionError:
            return False

        return False


    def get_environment(self):
        """ Return the environment configuration """

        env = {}
        try:
            section = self.name + " env"
            for var in self.config.options(section):
                setting = self.config.get(section, var)
                if setting.find("|") == -1:
                    self.rsv.log("WARNING", "invalid environment config setting in section '%s'" +
                                 "Invalid entry: %s = %s\n" +
                                 "Format must be VAR = ACTION | VALUE\n" % (section, var, setting))

                else:
                    (action, value) = re.split("\s*\|\s*", setting, 1)
                    valid_actions = ["SET", "UNSET", "APPEND", "PREPEND"]
                    if action.upper() in ("SET", "UNSET", "APPEND", "PREPEND"):
                        value = re.sub("!!VDT_LOCATION!!", self.rsv.vdt_location, value)
                        env[var] = [action, value]
                    else:
                        self.rsv.log("WARNING", "invalid environment config setting in section '%s'\n" +
                                     "Invalid entry: %s = %s\n" +
                                     "Format must be VAR = ACTION | VALUE\n" +
                                     "ACTION must be one of: %s" %
                                     (section, var, setting, " ".join(valid_actions)))

        except ConfigParser.NoSectionError:
            self.rsv.log("INFO", "No environment section in metric configuration", 4)

        return env


    def get_args_string(self):
        """ Build the custom parameters to the script based on the config file """
        
        self.rsv.log("INFO", "Forming args string")
        args_section = self.name + " args"
        args = ""
        try:
            for option in self.config.options(args_section):
                args += "--%s %s " % (option, self.config.get(args_section, option))
        except ConfigParser.NoSectionError:
            self.rsv.log("INFO", "No '%s' section found" % args_section, 4)

        return args
