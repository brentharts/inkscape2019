#!/usr/bin/env python3
import os, sys, subprocess

if '--install' in sys.argv:
	#if 'fedora' in os.uname().nodename:  ## this breaks when connected to internet DHCP :(
	if os.path.isfile('/usr/bin/dnf'):
		cmd = 'sudo dnf install libsoup-devel gsl-devel pango-devel cairo-devel double-conversion-devel gc-devel potrace-devel gtkmm3.0-devel libgdl-devel gtkspell3-devel boost-devel libxslt-devel'
	else:
		cmd = 'sudo apt-get install libmagick++-dev libaspell-dev libgraphicsmagick1-dev libgtkspell3-3-dev libcdr-dev libvisio-dev libwpg-dev libwpd-dev libsoup2.4-dev libxslt-dev libboost-all-dev liblcms2-dev libgc-dev libdouble-conversion-dev libpotrace-dev libpangomm-2.48-dev libcairomm-1.16-dev libgtkmm-3.0-dev libgdl-3-dev libpoppler-dev libpoppler-glib-dev mm-common'
	print(cmd)
	subprocess.check_call(cmd.split())


_thisdir = os.path.split(os.path.abspath(__file__))[0]
_buildir = os.path.join(_thisdir, 'build')
if not os.path.isdir(_buildir):
	os.mkdir(_buildir)


## from inkscape 1.3.2 2023/11/25
SP_MARSHAL_LIST = '''
# SPDX-License-Identifier: GPL-2.0-or-later
# marshallers for inkscape
VOID:POINTER,UINT
BOOLEAN:POINTER
BOOLEAN:POINTER,UINT
BOOLEAN:POINTER,POINTER
INT:POINTER,POINTER
DOUBLE:POINTER,UINT
VOID:INT,INT
VOID:STRING,STRING
'''
_helpers = os.path.join(_thisdir,'src/helper')
open( os.path.join(_helpers, 'sp-marshal.list'), 'w').write(SP_MARSHAL_LIST)


cmd = ['cmake', os.path.abspath(_thisdir), '-DENABLE_POPPLER=0', '-DENABLE_POPPLER_CAIRO=0']
print(cmd)
subprocess.check_call(cmd, cwd=_buildir)

subprocess.check_call(['make'], cwd=_buildir)
