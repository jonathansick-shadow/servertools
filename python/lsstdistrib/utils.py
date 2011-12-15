"""
utility functions, including configuration control
"""

def loadConfigfile(file):
    from lsstdistrib import config
    
    _globals = {}
    for key in filter(lambda k: k.startswith('__'), globals().keys()):
        _globals[key] = globals()[key]
    del key
        
    execfile(file, _globals, locals())
