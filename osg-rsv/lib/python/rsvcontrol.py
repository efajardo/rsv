#!/usr/bin/env python
# rsvcontrol.py
# Marco Mambelli <marco@hep.uchicago.edu>

import os 
import sys
import time
import socket
from optparse import OptionParser, OptionGroup

import osgrsv
import table

try:
    import logging
    rootlog = logging.getLogger('osgrsv.rsvcontrol')
    # create console handler and set level to warning
    # --verbose will set the console handler level to INFO
    ch = logging.StreamHandler()
    formatter = logging.Formatter("%(levelname)s: %(message)s")
    ch.setFormatter(formatter)
    ch.setLevel(logging.ERROR)
    rootlog.addHandler(ch)
    
    # create file handler (in log dir)
    #osg-rsv/logs there is logrotate
    #TODO: add log dir in VDT installation?
    hdlr = logging.FileHandler('/tmp/rsvcontrol.%s.log' % os.getuid())
    #formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)-8s %(message)s')
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    hdlr.setFormatter(formatter)
    hdlr.setLevel(logging.INFO)
    rootlog.addHandler(hdlr)
    # set general level to DEBUG so that handlers can set the level
    rootlog.setLevel(logging.DEBUG)
    log = rootlog    

    #TODO: ideally extend the logger class adding the method
    def set_console_logging_level(level):
        """Set console logging level.
        Level can be a number or one of the strings: DEBUG, INFO, WARNING, ERROR, CRITICAL
        """
        handlers = [i for i in log.handlers if isinstance(i, logging.StreamHandler)]
        l_level = level
        if level == 'DEBUG':
            l_level = logging.DEBUG
        elif level == 'INFO':
            l_level = logging.INFO
        elif level == 'WARNING':
            l_level = logging.WARNING
        elif level == 'ERROR':
            l_level = logging.ERROR
        elif level == 'CRITICAL':
            l_level = logging.CRITICAL
        for i in handlers:
            i.setLevel(l_level)
            
except ImportError:
    # logging available starting python 2.3
    import altlogging
    log = altlogging.LogFake()    
    set_console_logging_level = altlogging.set_console_logging_level


SUBMISSION_LIST_FORMATS = ['brief', 'long', 'full', 'log', 'out', 'err']
LIST_FORMATS = ['local'] + SUBMISSION_LIST_FORMATS

_cacheHostName = None
def getLocalHostName():
    global _cacheHostName
    if not _cacheHostName:
       try:
            _cacheHostName = os.environ.get('HOSTNAME', socket.gethostname())
       except:
            _cacheHostName = 'localhost'
    return _cacheHostName

def processoptions(arguments=None):
    # usage = """usage: \%prog [ --verbose ] 
    usage = """usage: rsv-control [ --verbose ] 
      --help | -h 
      --version
      --setup  NOT IMPLEMENTED ... COMING SOON
      --list [ --wide | -w | --full-width] [ --format <format> ] [ all | <probeID>]
      --enable    [--user <user>] --metric  <metric-name>  --host <host-name>
      --enable    [--user <user>] --service <service-name> --host <host-name>
      --disable   [--user <user>] --metric  <metric-name>  --host <host-name>
      --disable   [--user <user>] --service <service-name> --host <host-name>
      --full-test [--user <user>] --metric <metric-name>   --host <host-name>
      --test      [--user <user>] --metric <metric-name>   --host <host-name>
    """
    version = "rsv-control 0.13"
    description = """This script is used to control or verify a probe."""
    parser = OptionParser(usage=usage, description=description, version=version)
    #parser.add_option("-v", "--version", action="store_true", dest="verbose", default=False,
    parser.add_option("-p", "--vdt-location", "--vdt-install", dest="vdtlocation", default=None,
                      help="Root directory of the OSG or VDT installation (prefer --vdt-location)", metavar="DIR")
    #parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False,
    #parser.add_option("--verbose-output", action="store_true", dest="verbose", default=False,
    parser.add_option("--verbose", action="store_true", dest="verbose", default=False,
                      help="Verbose output")
    parser.add_option("-l", "--list", action="store_true", dest="rsvctrl_list", default=False,
                      help="List probe information")
    parser.add_option("-w", "--wide", action="store_true", dest="list_wide", default=False,
                      help="Wide list display")
    parser.add_option("--full-width", action="store_true", dest="list_fullwidth", default=False,
                      help="To avoid truncation in probe listing")
    parser.add_option("-f", "--format", dest="list_format", choices=tuple(LIST_FORMATS), default='local',
                      help="Specify the list format (%s; default: %%default)" % (LIST_FORMATS,))
    parser.add_option("--test", action="store_true", dest="rsvctrl_test", default=False,
                      help="Run a probe and return its output.")
    parser.add_option("--full-test", action="store_true", dest="rsvctrl_full_test", default=False,
                      help="Test a probe within OSG-RSV. Probe is executed only once, immediately.")
    parser.add_option("-e", "--enable", action="store_true", dest="rsvctrl_enable", default=False,
                      help="Enable probe")
    parser.add_option("-d", "--disable", action="store_true", dest="rsvctrl_disable", default=False,
                      help="Disable probe")
    parser.add_option("--setup", action="store_true", dest="rsvctrl_setup", default=False,
                      help="NOT READY... COMING SOON: Setup the RSV installation (change file permissions, start Condor, ...)")
    # Preferred: prog --enable [metric] <metric>
    #   prog --enable service <service>
    # In theory I should be able to distinguish between services and metrics
    parser.add_option("--user", dest="user", default=None,
                      help="Specify the user to run OSG-RSV probes")
    parser.add_option("--metric", dest="metric", default=None,
                      help="Specify the metric to enable/disable (e.g. org.osg.general.ping-host)")
    parser.add_option("--service", dest="service", default=None,
                      help="Specify the service to enable/disable (e.g. OSG-CE)")
    #parser.add_option("-u", "--uri", dest="uri", default=None,
    parser.add_option("--host", dest="uri", default=None,
                      help="Specify the host FQDN and optionally the port to be used by the probe (e.g. host or host:port)")
    #group = OptionGroup(parser, "Gratia Options",
    #                    "Enable and configure the upload to the RSV collector in Gratia")
    #group.add_option("--gratia", action="store_true", dest="gratia", default=False, 
    #                 help="Enable Gratia output (default: %default)")
    #parser.add_option_group(group)
    #parser.add_option("-v", "--verbose",
    #                  action="store_true", dest="probe_verbose", default=None,
    #                  help="Pass the --verbose flag to all probes")
    #parser.add_option("-t", "--time", dest="crontime", default=None,
    #                  help="Set the cron TIME to repeat the probe (format min-hour-day-mon-wday, e.g. '%s')" % (OPTIONS_DEFAULT.crontime,), metavar="TIME") 
    #parser.add_option("--vo-name", dest="probe_voname", default=None,
    #                  help="Pass supplied argument with --virtual-organization flag to the probes")
    #parser.add_option("--print-local-time", dest="probe_localtime", default=None,
    #                  help="Pass the --print-local-time flag to all probes")
    #group = OptionGroup(parser, "Condor Options",
    #                    "Options to alter Condor submission parameters")
    #group.add_option("--condor-universe", dest="jobuniverse", default='local', 
    #                 help="Condor universe for the condor_cron jobs (default: %default)")
    #parser.add_option_group(group)


    #parser.disable_interspersed_args()
    #default: (options, args) = parser.parse_args(sys.argv[1:]) - alt args possible
    if arguments==None:
        (options, args) = parser.parse_args()
    else:
        (options, args) = parser.parse_args(arguments)

    # Check options consistency
    # parser.error() prints the message and exits with ec 2
    if not options.vdtlocation:
        options.vdtlocation = osgrsv.findPathOSG()
    if not options.vdtlocation:
        ## TODO check also that VDT_LOCATION exist? or set it in the environment?
        parser.error("ERROR: VDT_LOCATION is not set.\nEither set this environment variable, or pass the --vdt-location command line option.")
        #print "ERROR: VDT_LOCATION is not set.\n"
        #print "Either set this environment variable, or pass the --vdt-install command line option.\n"
        #exit(1)
    # Ownership problem:
    # - probes should not be submittted to condor as root
    # - enable/disable/test require ownership of the directory tree
    tmp_fname = os.path.join(options.vdtlocation, osgrsv.OSGRSV_NAME)
    file_uid = os.stat(tmp_fname)[4]   # stat.ST_UID=4
    user_id = os.getuid()
    number_of_commands = len([i for i in [options.rsvctrl_enable, options.rsvctrl_disable, 
                                          options.rsvctrl_test, options.rsvctrl_full_test, options.rsvctrl_list,
                                          options.rsvctrl_setup] if i])
    if number_of_commands > 1:
        parser.error("Commands are mutially exclusive, you can use only one of list, test, enable, disable.")
    if number_of_commands == 0:
        parser.error("Invalid syntax. You must specify one command.")
    # rsvctrl_test is OK since it is not touching the files in the RSV directory
    if options.rsvctrl_enable or options.rsvctrl_disable or options.rsvctrl_full_test:       
        if not file_uid==user_id:
            parser.error("Operation not possible. You ar not the owner of the installtion in: %s\nUse --setup to change ownership and fix that." % (tmp_fname))            #print "Operation not possible. You ar not the owner of the installtion in: %s" % (tmp_fname)
            #log.error("Use --setup to change ownership and fix that.")
            #exit(2)
        # root cannot submit jobs
        # root can disable jobs of other users
        if user_id==0 and not options.user and not options.rsvctrl_disable: 
            #running as root
            log.error('You cannot run the jobs as root, use "--user <username>" to submit the jobs as a different user.')
            tmp_fname = os.path.join(options.vdtlocation, "osg/etc/config.ini")
            if os.path.isfile(tmp_fname):
                tmp_user = osgrsv.getConfigOSG(tmp_fname).get("RSV", "rsv_user")
                log.error("The user in osg/etc/config.ini is %s." % (tmp_user,))
            parser.error("Run with --user <user>") # parser.exit(2) - available in Python 2.5
    return args, options

def main_list():
    #TODO: may be obsolete!!
    # list command
    
    args, options = processoptions()
        
    # init configuration

    # take care of RSV cert?
    rsv = osgrsv.OSGRSV(options.vdtlocation)

    rets = ""
    if not args or args[0]=='all':
        # list all probe status
        retlines = []
        probelist = rsv.getConfiguredProbes(options=options)
        for p in probelist:
            for u in p.urilist:
                if options.list_format=='local':
                    rets = p.status(u)
                elif options.list_format in SUBMISSION_LIST_FORMATS:
                    rets = p.submission_status(u, format=options.list_format)
                else:
                    rets = p.status(u)
                retlines.append(" %-90s : %s" % (p.getLocalUniqueName(u), rets))
        print '\n'.join(retlines)
        return
    else:
        # list probe
        if not rsv.isValidProbeID(args[0]):
            log.error("Invalid probe ID (should be hostName__fileName@metricName): %s" % (args[0],))
            return
        probe = rsv.getProbeByID(args[0])
        probe.describe()
        if options.list_format=='local':
            rets += probe.status(probe.urilist[0])
        elif options.list_format in SUBMISSION_LIST_FORMATS:
            rets += str(probe.submission_status(probe.urilist[0], format=options.list_format))
        else:
            rets += probe.status(probe.urilist[0])
    # printing output
    print rets
    

def main_rsv_control():
    # list command
    
    args, options = processoptions()
    # processingoption is checking also for consistency and exit(1) if there are problems
        
    if options.verbose:
        set_console_logging_level(logging.INFO)
        log.info("%s: Executing rsvcontrol: %s" % (time.asctime(), sys.argv))
    # init configuration

    # take care of RSV cert?
    if options.user:
        rsv = osgrsv.OSGRSV(options.vdtlocation, user=options.user)
    else:        
        rsv = osgrsv.OSGRSV(options.vdtlocation)

    rets = ""
    if options.rsvctrl_list:
        if not args or args[0]=='all':
            # list all probe status
            log.info("Listing all probes... may take few seconds.")
            retlines = []
            probelist = rsv.getConfiguredProbes(options=options)
            if options.list_format=='local':
                table_ = table.Table((42, 15, 20))
                if options.list_fullwidth:
                    table_.truncate = False
                elif options.list_wide:
                    table_.setColumns(80, 20, 40)
                    table_.truncate_leftright = True
                else:
                    table_.truncate_leftright = True
                table_.makeFormat()
                table_.makeHeader('Metric', 'Service', 'Hostname')
                retlines.append(table_.getHeader())
                for p in probelist:
                    pmetric = p.metricName
                    ptype = p.getType()
                    ret_list_uri = []
                    ret_list_status = []
                    for u in p.urilist:
                        rets = p.status(u)
                        log.debug("Metric %s (%s): %s on %s" % (pmetric, ptype, rets, u))
                        if rets=="ENABLED":
                            ret_list_uri.append(u)
                        else:
                            if not rets in ret_list_status:
                                ret_list_status.append(rets)
                    if not ret_list_uri:
                        # should I just add DISABLED?
                        # if multiple status are appearing probably there is an error
                        for i in ret_list_status:
                            table_.addToBuffer(pmetric, ptype, i)
                        continue
                    for i in ret_list_uri:                        
                        table_.addToBuffer(pmetric, ptype, i)
                #after looping on all probes
                retlines += table_.formatBuffer()
            else:
                #list all probes, format != 'local'
                for p in probelist:
                    pkey = p.getKey()
                    retlines.append("%s" % (p.getKey(),))
                    for u in p.urilist:
                        if options.list_format in SUBMISSION_LIST_FORMATS:
                            rets = p.submission_status(u, format=options.list_format)
                        else:
                            rets = p.status(u)
                        retlines.append("               %-30s : %s" % (u, rets))
            if not probelist:
                log.error("No configured probes!")
            else:
                print '\n'.join(retlines)
            return
        else:
            # list probe 
            probe = None
            if rsv.isValidProbeID(args[0]):
                # Return correct metric and URI
                probe = rsv.getProbeByID(args[0])
            else:
                # Try to lookup the probe using the metrics name
                # There may be multiple URI, choodig the first one?
                log.info("Invalid probe ID (should be hostName__fileName@metricName): %s\nTrying metric name lookup...may teke few seconds." 
                         % (args[0],))
                probelist = rsv.getConfiguredProbes(options=options)
                for p in probelist:
                    if p.metricName == args[0]:
                        probe = p
                        log.info("Metric %s, URI %s" % (args[0], p.urilist[0]))
                        break
            if not probe:
                log.info("Unable to lookup probe by ID or metric name: %s." % (args[0],)) 
            #probe.describe()
            if options.list_format=='local':
                rets += probe.status(probe.urilist[0])
            elif options.list_format in SUBMISSION_LIST_FORMATS:
                if options.rsvctrl_test:
                    rets += str(probe.submission_status(probe.urilist[0], format=options.list_format, probe_test=True))
                else:
                    rets += str(probe.submission_status(probe.urilist[0], format=options.list_format))
            else:
                rets += probe.status(probe.urilist[0])
            # printing output
            print rets
            return
    elif options.rsvctrl_enable or options.rsvctrl_disable or options.rsvctrl_test or options.rsvctrl_full_test:
        if not options.service and not options.metric:
            log.error("Service or metric must be provided.")
            log.info("Entered values: metric %s, service %s." % (options.service, options.metric))
            return
        # retrieve all probes and restrict to the selected ones
        #TODO: getConfiguredProbes or getInstalledProbes?
        # how about installation of new probes?
        probes = rsv.getConfiguredProbes(options=options) # getInstalledProbes()
        if options.metric:
            # look for the probe with the given metric
            selprobes = []
            for i in probes:
                if i.metricName==options.metric:
                    selprobes = [i]
                    break
        elif options.service:
            # look for all the probes with a given service
            selprobes = [i for i in probes if i.getType()==options.service]
        if not selprobes:            
            log.error("No probe matching your selection (%s/%s). No action taken." % (options.metric, options.service))
            return
        if options.uri:
            uri = options.uri
        else:
            # get local host
            log.debug("No URI provided, assuming local probe (localost)")
            uri = getLocalHostName()
        # If disable, make sure that the probe with the right URI is selected
        # TODO:check implications, the uri is passed anyway
        if uri:
            tmp_sel = []
            for p in selprobes:
                for u in p.urilist:
                    if u==uri:
                        tmp_sel.append(p)
            if tmp_sel or options.rsvctrl_disable:
                selprobes = tmp_sel
        log.debug("%s probes selected. (e/d/t/ft: %s/%s/%s/%s)" % (len(selprobes), options.rsvctrl_enable, 
                                                                   options.rsvctrl_disable, options.rsvctrl_test,
                                                                   options.rsvctrl_full_test))
        if options.rsvctrl_disable:
            for p in selprobes:
                p.disable(uri)
                print "Metric disabled"
        elif options.rsvctrl_full_test:
            for p in selprobes:
                ec = p.full_test(uri)
                if ec==0:
                    print "Metric tested"
                else:
                    print "Metric test failed"
        elif options.rsvctrl_test:
            for p in selprobes:
                out = p.test(uri)
                print out
        else: # elif options.rsvctrl_enable:
            for p in selprobes:
                # Operation is idempotent. If probe is already enabled, no action is taken.
                if p.isEnabled(uri):
                    log.error("No action taken. Metric %s is already running against %s." % 
                              (p.getName(), uri))
                    log.error("If you changed some information and like to restart the probe, please disable the probe first and then enable it.")
                    continue
                p.enable(uri)
                print "Metric enabled"
        return
    elif options.rsvctrl_setup:
        log.error("Not yet implemented")
        return
    else:
        log.error("Unknown request")
    return
    
def main():
    print "Wrong invocation!"
    
if __name__ == "__main__":
    progname = os.path.basename(sys.argv[0])
    if progname=='probe-list':
        main_list()
    elif progname=='rsv-control' or progname=='rsvcontrol.py':
        main_rsv_control()
    elif progname=='probe':
        main2()
    else:
        main()
