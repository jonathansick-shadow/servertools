"""
functions related to manipulating versions
"""
import sys
import os
import re


class VersionCompare(object):
    """
    a functor for comparing LSST version strings.  For consistency, the 
    comparator configured into EUPS should be used.  This function is 
    appropriate for a limited set of version forms used by LSST for 
    released data products.  The example form is 1.2.3.4+18.  A more
    general BNF is implemented in order to allow unexpected forms to 
    be sorted:

       version    := tag [ release ]
       tag        := integer [ subtag ] 
       subtag     := fielddelim integer [ subtag ]
       fielddelim := '.'
       release    := qualifier version
       qualtype   := '+' | '-' 
       integer    := (any whole number)

    """
    qualRe = re.compile(r'[\+\-]')
    nonTagRe = re.compile(r'[^\d\.]+')
    releaseRe = re.compile(r'(\D*)(\d\S)')
    relDelimRe = re.compile(r'\D+')
    fieldDelimRe = re.compile(r'\.')

    def compare(self, v1, v2):
        (rel1, q1, b1) = splitToReleaseBuild(v1)
        (rel2, q2, b2) = splitToReleaseBuild(v2)

        # compare the tagged version component (prior to the +/-)
        comp = self._tagCompare(rel1, rel2)
        if comp != 0 or (not q1 and not q2):
            return comp

        # compare the release qualifiers:  + > - > anything else
        if q1 != q2:
            if q2 == '+' or not q1:
                return -1
            if q2 == '-' and q1 != '+':
                return -1
            if q1 == '+' or not q2:
                return +1
            if q1 == '-' and q2 != '+':
                return +1
            return cmp(q1, q2)

        # if either is missing a build number, consider the missing
        # one as earlier
        if not b1:
            if not b2:
                return 0
            return -1
        if not b2:
            return +1

        # compare release field (after +/-)
        return self.compare(b1, b2)

    def _tagCompare(self, v1, v2):
        parts1 = self.fieldDelimRe.split(v1)
        parts2 = self.fieldDelimRe.split(v2)

        while len(parts1) > 0 and len(parts2) > 0:
            comp = self._fldCompare(parts1[0], parts2[0])
            if comp != 0:
                return comp
            parts1.pop(0)
            parts2.pop(0)

        return 0

    def _fldCompare(self, f1, f2):
        # compare two version fields.  Normally these should be integers;
        # if so, compare them numerically.  If one is an integer and the
        # other is not, consider the integer as the lesser.  If neither
        # are integers, compare them lexically.
        try:
            f1 = int(f1)
            f2 = int(f2)
        except ValueError:
            pass
        return cmp(f1, f2)

    def __call__(self, v1, v2):
        return self.compare(v1, v2)

buildExtRe = re.compile(r'([^\d\.]+)(\d+)$')


def incrementBuild(v1, forcePlus=False):
    mat = buildExtRe.search(v1)
    if mat:
        q = mat.group(1)
        if forcePlus:
            return buildExtRe.sub("+1", v1)
        bnum = int(mat.group(0)[len(q):])
        return buildExtRe.sub(q+str(bnum+1), v1)
    elif v1.endswith('-'):
        if forcePlus:
            return v1[:-1] + "+1"
        else:
            return v1 + "1"
    elif v1.endswith('+'):
        return v1 + "1"
    else:
        return v1 + "+1"


def substituteBuild(v1, bnum, forcePlus=False):
    bnum = str(bnum)
    mat = buildExtRe.search(v1)
    if mat:
        q = mat.group(1)
        if forcePlus:
            q = "+"
        return buildExtRe.sub(q+bnum, v1)
    elif v1.endswith('-'):
        if forcePlus:
            return "%s+%s" % (v1[:-1], bnum)
        else:
            return v1 + bnum
    elif v1.endswith('+'):
        return v1 + bnum
    return "%s+%s" % (v1, bnum)


def splitToReleaseBuild(version):
    """
    split a version string into its base release version (i.e. as tagged in 
    SVN), a build qualifier, and a build number.  
    """
    mat = buildExtRe.search(version)
    if mat:
        return (version[:mat.start(0)], mat.group(1), mat.group(2))
    return (version, None, None)


def baseVersion(version):
    """
    strip off the build qualifier from the given version string
    """
    return splitToReleaseBuild(version)[0]


def buildNumber(version, default=None):
    """
    extract the build number given from the given version
    @param version   the input version string, which should include a build
                       number
    @param default   a value to return if the input version does not include
                       a build number
    @return str   the build number (as a string) or the default value if a build
                       number is not found in the input string.
    """
    out = splitToReleaseBuild(version)[2]
    if out is None:
        out = default
    return out

defaultVersionCompare = VersionCompare()

