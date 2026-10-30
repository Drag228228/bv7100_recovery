#!/usr/bin/env python3
"""Print shell commands that unset OrangeFox variables which the current
bootable/recovery/orangefox.mk rejects as obsolete (and export the replacement
it suggests). Usage:  eval "$(python3 fox_vars_fix.py bootable/recovery/orangefox.mk)"
"""
import os, re, sys

lines = open(sys.argv[1], errors='replace').read().splitlines()
for var in sorted(k for k in os.environ if re.match(r'^(OF|FOX)_[A-Z0-9_]+$', k)):
    pat = re.compile(r'(?<![A-Z0-9_])%s(?![A-Z0-9_])' % var)
    for i, l in enumerate(lines):
        if not pat.search(l):
            continue
        window = ' '.join(lines[i:i + 3])
        if 'obsolete' not in window.lower():
            continue
        print('unset %s' % var)
        msg = 'obsolete variable %s dropped' % var
        m = re.search(r'export\s+((?:OF|FOX)_[A-Z0-9_]+)=([^\s"\')]+)', window)
        if m and m.group(1) != var:
            if m.group(1) not in os.environ:
                print('export %s=%s' % (m.group(1), m.group(2)))
            msg += ', using %s=%s' % (m.group(1), m.group(2))
        print('echo "::warning title=fox vars::%s"' % msg)
        break
