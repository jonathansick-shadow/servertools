#! /usr/bin/env python
#
import os, sys, re
import eups
from eups import distrib

baseURL = re.sub(r'\|.*$', '', os.environ.get('EUPS_PKGROOT'))

eupsenv = eups.Eups()
repos = distrib.Repository(eupsenv, baseURL)

current = repos.listPackages(tag='current', flavor='generic', queryServer=True)

for prod, version, flavor in current:
    installed = eupsenv.findProduct(prod, version)
    if not installed:
        # print >> sys.stderr, "Current product not installed:", prod, version
        continue
    if not installed.isTagged("current"):
        print >> sys.stderr, "Synchronizing product:", prod, version
        eupsenv.assignTag('current', prod, version)

print >> sys.stderr, "Stack is synchronized with tag=current on server."
