#!/usr/bin/env python3
import os, sys, subprocess, xml.dom.minidom

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

INKSCAPE_EXE = os.path.join(_buildir,'bin/inkscape')


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

def build():
	_helpers = os.path.join(_thisdir,'src/helper')
	open( os.path.join(_helpers, 'sp-marshal.list'), 'w').write(SP_MARSHAL_LIST)
	cmd = ['cmake', os.path.abspath(_thisdir), '-DENABLE_POPPLER=0', '-DENABLE_POPPLER_CAIRO=0']
	print(cmd)
	subprocess.check_call(cmd, cwd=_buildir)
	subprocess.check_call(['make'], cwd=_buildir)

def gen_min_toolbar_ui():
	doc = xml.dom.minidom.Document()
	ui = doc.createElement('ui')
	tb = doc.createElement('toolbar')
	tb.setAttribute('name', 'ToolToolbar')
	ui.appendChild(tb)
	for act in 'ToolSelector ToolNode ToolRect ToolArc ToolPencil ToolPen ToolCalligraphic ToolText ToolEraser ToolPaintBucket'.split():
		a = doc.createElement('toolitem')
		tb.appendChild(a)
		a.setAttribute('action', act)
	print(ui.toprettyxml())
	return ui.toprettyxml()


def ensure_user_config( minimal=True ):
	cfg = os.path.expanduser('~/.config')
	assert os.path.isdir(cfg)
	icfg = os.path.join(cfg, 'inkscape')
	if not os.path.isdir(icfg): os.mkdir(icfg)
	iui  = os.path.join(icfg, 'ui')
	if not os.path.isdir(iui): os.mkdir(iui)
	if minimal:
		open(os.path.join(iui, 'toolbar-tool.ui'), 'w').write(gen_min_toolbar_ui())
	else:
		open(os.path.join(iui, 'toolbar-tool.ui'), 'w').write(open('./share/ui/toolbar-tool.ui').read())

if __name__=='__main__':
	if not os.path.isfile(INKSCAPE_EXE):
		build()
	if not os.path.isdir('/usr/local/share/inkscape'):
		os.system('sudo mkdir /usr/local/share/inkscape')
		os.system('sudo cp -Rv ./share/pixmaps /usr/local/share/inkscape/.')

	ensure_user_config()
	subprocess.check_call([INKSCAPE_EXE])
