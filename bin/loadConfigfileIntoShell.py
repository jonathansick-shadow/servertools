#! /usr/bin/env python
#
import lsstdistrib.utils
import lsstdistrib.config as config
import sys

if len(sys.argv) < 2:
    print >> sys.stderr, "loadConfigfileIntoShell: Missing config file name"
    print "false"
    sys.exit(1)
try:
    lsstdistrib.utils.loadConfigfile(sys.argv[1])
except Exception, e:
    print >> sys.stderr, "loadConfigfileIntoShell:", str(e)
    print "false"
    sys.exit(1)

for key in filter(lambda s: not s.startswith('_'), dir(config)):
    print 'config_%s="%s"' % (key, getattr(config, key))

sys.exit(0)
