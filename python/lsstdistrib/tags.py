"""
a module for manifulating server-side tag files.  These files define
which products/versions are a assigned a particular tag by the project.
"""
from __future__ import absolute_import
from __future__ import with_statement

import sys, os, re, cStringIO

class TagDef(object):

    def __init__(self, tagfile):
        self.file = tagfile
        self.prod = {}
        self._load(tagfile)

    def _load(self, tagfile):
        with open(tagfile) as cf:
            parts = []
            for line in cf:
                line = line.strip()
                if line.startswith('#'):
                    continue

                parts = re.findall(r"\S+", line)
                if len(parts) > 2:
                    if len(parts) < 4:
                        parts.append('')
                self.prod[parts[0]] = parts

    def merge(self, tagfile):
        self.file = '+' + tagfile
        self._load(tagfile)

    def lookup(self, prodname):
        """return the tag data for a given product or None if does not exist"""
        return self.prod.get(prodname)

    def getVersion(self, prodname):
        data = self.lookup(prodname)
        if data:
            return data[2]
        return None

    bextRe = re.compile(r'[\+\-]\d+')
    
    def getVersionPath(self, prodname):
        data = self.lookup(prodname)
        if data:
            bext = None
            ver = data[2]
            bmat = self.bextRe.search(ver)
            if bmat:
                bext = bmat.group(0)
                ver = bextRe.sub('', ver)
           
            path = os.path.join(data[0], ver)
            if data[3]:
                os.path.join(path, data[3])
            return (data[2], path)
        return (None, None)

