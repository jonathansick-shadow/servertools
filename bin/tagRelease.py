#! /usr/bin/env python
#
from __future__ import with_statement
import os, sys, re, optparse, shutil

prog = os.path.basename(sys.argv[0])
# defserverdir = os.path.join(os.environ['HOME'], 'softstack/pkgs/test/w12a')
tag = 'current'
tmpdir = '/tmp'

lsstMarkerRe = re.compile(r"^\s*#\s*lsst", re.IGNORECASE)

def options():
    usage="%prog -d DIR product version tag [ tag ... ]"
    parser = optparse.OptionParser(usage=usage)
    parser.add_option("-d", "--server-directory", dest="sdir", action="store",
                      metavar="DIR", help="the root directory for the server")
    parser.add_option("-D", "--output-directory", dest="outdir",
                      action="store",metavar="DIR", 
                      help="save output files in given directory (rather than overwrite)")

    import lsstdistrib.config as config
    import lsstdistrib.utils  as utils
    try:
        configfile = os.path.join(os.environ['DEVENV_SERVERTOOLS_DIR'], "conf",
                                  "common_conf.py")
        utils.loadConfigfile(configfile)
    except Exception, ex:
        print >> sys.stderr, "Warning: unable to load system config file:", str(ex)
    
    opts, args = parser.parse_args()

    if not opts.sdir and config.serverdir:
        opts.sdir = config.serverdir

    return (opts, args)

class AmongLSSTEntries(object):
    def __init__(self):        self.v =  1
    def no(self):       return self.v != 0
    def yes(self):      return self.v == 0
    def notyet(self):   return self.v > 0
    def done(self):     return self.v < 0
    def setDone(self):         self.v = -1
    def setYes(self):          self.v =  0
    def __repr__(self): return str(self.yes())
    
def main():
    (opts, args) = options()

    if len(args) < 2:
        raise RuntimeError("Missing product and version")
    if len(args) < 3:
        raise RuntimeError("Missing tag name(s) to assign")

    prodname = args.pop(0)
    version  = args.pop(0)

    if not os.path.isdir(opts.sdir):
        print >> sys.stderr, "%s: server directory does not exist: %s" % \
                             (prog, opts.sdir)
        sys.exit(1)

    outdir = opts.outdir
    if not outdir:
        outdir = tmpdir

    prodre=re.compile(r"^\s*%s\s" % prodname)
    failures=[]
    for tag in args:
        tagfile = os.path.join(opts.sdir, "%s.list" % tag)
        if not os.path.exists(tagfile):
            print >> sys.stderr, "%s: tag file missing for tag=%s" % \
                                 (prog, tagfile)
            failures.append(tag)
            continue

        ntagfile = os.path.join(outdir, "%s.list" % tag)

        if opts.outdir:
            print "Writing %s to %s" % (tag, ntagfile)
        else:
            print "Updating %s" % tagfile

        fmt = None
        with open(tagfile) as tf:
            with open(ntagfile, 'w') as ntf:
                amonglsstentries = AmongLSSTEntries()
                for line in tf:
                    line = line.strip("\n")
                    if line.startswith("#---"):
                        cols = line.strip().split()
                        widths = map(lambda c: len(c), cols)
                        while len(widths) < 5:
                            widths.append(10)
                        fmt = "%%-%ds  %%-%ds  %%-%ds  %%-%ds  %%-%ds" % \
                              tuple(widths)
                    mat = prodre.match(line)
                    if amonglsstentries.notyet() and \
                       (line.startswith('afw') or lsstMarkerRe.match(line)):
                        amonglsstentries.setYes()
                    if mat:
                        cols = line.strip().split()
                        while len(cols) < 5:
                            cols.append('')
                        cols[2] = version
                        line = fmt % tuple(cols)
                        amonglsstentries.setDone()
                    elif amonglsstentries.yes() and not line.startswith('#') \
                         and cmp(prodname, line) < 0:
                        cols = [prodname, "generic", version, '', '']
                        print >> ntf, fmt % tuple(cols)
                        amonglsstentries.setDone()
                    print >> ntf, line

        if not opts.outdir:
            try:
                shutil.move(ntagfile, tagfile)
            except OSError, ex:
                print >> sys.stderr, \
                      "%s: Failed to replace original tagfile (%s): %s" \
                      % (prog, tagfile, str(ex))

    if len(failures) > 0:
        raise RuntimeError("Tags not updated: " + ", ".join(failures))
        
if __name__ == "__main__":
    main()

