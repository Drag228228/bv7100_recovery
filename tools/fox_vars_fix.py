#!/usr/bin/env python3
# Unset OF_/FOX_ variables that OrangeFox declares obsolete (it aborts the build on them).
# Strict: the variable must be the SUBJECT of "<VAR> is obsolete" - a line that merely
# names it as the replacement ("... obsolete. Use FOX_AB_DEVICE") must not drop it.
import os, re, sys
text = open(sys.argv[1], errors='replace').read()
lines = text.splitlines()
for var in sorted(k for k in os.environ if re.match(r'^(OF|FOX)_[A-Z0-9_]+$', k)):
    subj = re.compile(r'''(?<![A-Z0-9_])['"]?%s['"]?\s+is\s+(?:now\s+)?obsolete''' % var, re.I)
    for i, l in enumerate(lines):
        if not subj.search(l):
            continue
        print('unset %s' % var)
        msg = 'obsolete variable %s dropped' % var
        window = ' '.join(lines[i:i + 3])
        m = re.search(r'export\s+((?:OF|FOX)_[A-Z0-9_]+)=([^\s"\')]+)', window)
        if m and m.group(1) != var:
            if m.group(1) not in os.environ:
                print('export %s=%s' % (m.group(1), m.group(2)))
            msg += ', using %s=%s' % (m.group(1), m.group(2))
        print('echo "::warning title=fox vars::%s [line %d]"' % (msg, i + 1))
        break
