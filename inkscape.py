#!/usr/bin/env python3
import os, sys, subprocess, xml.dom.minidom, ctypes

if '--install' in sys.argv:
	#if 'fedora' in os.uname().nodename:  ## this breaks when connected to internet DHCP :(
	if os.path.isfile('/usr/bin/dnf'):
		cmd = 'sudo dnf install libsoup-devel gsl-devel pango-devel cairo-devel double-conversion-devel gc-devel potrace-devel gtkmm3.0-devel libgdl-devel gtkspell3-devel boost-devel libxslt-devel'
	else:
		cmd = 'sudo apt-get install libharfbuzz-dev libmagick++-dev libaspell-dev libgraphicsmagick1-dev libgtkspell3-3-dev libcdr-dev libvisio-dev libwpg-dev libwpd-dev libsoup2.4-dev libxslt-dev libboost-all-dev liblcms2-dev libgc-dev libdouble-conversion-dev libpotrace-dev libpangomm-2.48-dev libcairomm-1.16-dev libgtkmm-3.0-dev libgdl-3-dev libpoppler-dev libpoppler-glib-dev mm-common'
	print(cmd)
	subprocess.check_call(cmd.split())


_thisdir = os.path.split(os.path.abspath(__file__))[0]
_buildir = os.path.join(_thisdir, 'build')
if not os.path.isdir(_buildir):
	os.mkdir(_buildir)

INKSCAPE_EXE = os.path.join(_buildir,'bin/inkscape')
INKSCAPE_SO  = os.path.join(_buildir,'lib/libinkscape_base.so')

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
	cmd = ['cmake', os.path.abspath(_thisdir), '-DENABLE_POPPLER=0', '-DENABLE_POPPLER_CAIRO=0', '-DUSE_TRACE=1', '-DUSE_AUTOTRACE=1']
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

INKSCAPE_MODULE = '''
#include "inkscape-application.h"
InkscapeApplication *app

extern "C" int inkscape_init(){
	if (gtk_init_check(NULL, NULL)){
		app = new InkscapeApplication();
		return 1;
	} else {
		return 0;
	}
}
'''

def inkscape_python():
	so  = '/tmp/libinkscape.so'
	tmp = '/tmp/libinkscape.c++'
	open(tmp,'w').write(INKSCAPE_MODULE)
	cmd = [
		'g++', '-o', so, tmp, '-l', INKSCAPE_SO, 
		'-I./src/include', '-I./src', '-I/usr/include/glib-2.0',
		'-I/usr/include/giomm-2.4', 
		#'-I/usr/include/gdkmm-2.4',
		'-I/usr/include/gdkmm-3.0',
		'-I/usr/include/pangomm-2.48', '-I/usr/include/pango-1.0',
		'-I/usr/include/harfbuzz', '-I/usr/include/cairomm-1.16',
		'-I/usr/include/cairo', '-I/usr/include/freetype2',
		'-I/usr/include/gtk-3.0',
		'-I/usr/include/gdk-pixbuf-2.0',
		'-I/usr/include/atkmm-1.6',
		'-I/usr/include/atk-1.0',
	]
	cmd += [
		'-I/usr/include/gtkmm-3.0/', '-I/usr/include/glibmm-2.4', 
		'-I/usr/lib/x86_64-linux-gnu/glibmm-2.4/include', '-I/usr/lib/x86_64-linux-gnu/glib-2.0/include',
		'-I/usr/include/sigc++-2.0/', '-I/usr/lib/x86_64-linux-gnu/sigc++-2.0/include',
		'-I/usr/lib/x86_64-linux-gnu/giomm-2.4/include',

		#'-I/usr/lib/x86_64-linux-gnu/gdkmm-2.4/include',
		'-I/usr/lib/x86_64-linux-gnu/gdkmm-3.0/include',

		'-I/usr/lib/x86_64-linux-gnu/pangomm-2.48/include',
		'-I/usr/lib/x86_64-linux-gnu/cairomm-1.16/include',
		'-I/usr/lib/x86_64-linux-gnu/gtkmm-3.0/include',
		'-I/usr/lib/x86_64-linux-gnu/atkmm-1.6/include',
		]
	print(cmd)
	subprocess.check_call(cmd)
	lib = ctypes.CDLL(so)
	print(lib)

if __name__=='__main__':
	if not os.path.isfile(INKSCAPE_EXE) or '--rebuild' in sys.argv:
		build()
	if not os.path.isdir('/usr/local/share/inkscape'):
		os.system('sudo mkdir /usr/local/share/inkscape')
		os.system('sudo cp -Rv ./share/pixmaps /usr/local/share/inkscape/.')

	ensure_user_config()
	if '--exe' in sys.argv:
		subprocess.check_call([INKSCAPE_EXE])
	else:
		inkscape_python()
