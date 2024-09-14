#!/usr/bin/env python3
import os, sys, subprocess, xml.dom.minidom, ctypes, atexit

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
	open('/tmp/__inkscape__.toolbar.inc','w').write(INKSCAPE_TOOLBAR)
	open('/tmp/__inkscape__.header.inc','w').write(INKSCAPE_HEADER)
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
	tools = 'ToolRect ToolArc ToolPencil ToolPen ToolCalligraphic ToolText ToolEraser ToolPaintBucket ToolSelector ToolNode'.split()
	#tools.append('PythonScript')  ## rather than hook into inkscape actions api, we can just generate simple C++ .inc files
	for act in tools:
		a = doc.createElement('toolitem')
		tb.appendChild(a)
		a.setAttribute('action', act)
	print(ui.toprettyxml())
	return ui.toprettyxml()


def ensure_user_config( minimal=True, menu=True ):
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

	if menu:
		open(os.path.join(iui, 'menus.xml'), 'w').write(open('./share/ui/menus.xml').read())

	def cleanup():
		## this is required so that OS packaged inkscape is able to run
		## otherwise it will read these config files and crash
		os.unlink(os.path.join(iui, 'menus.xml'))
		os.unlink(os.path.join(iui, 'toolbar-tool.ui'))

	atexit.register(cleanup)

INKSCAPE_HEADER = '''
#include "io/sys.h"
SPDocument *__doc__;
extern "C" void inkscape_new_document(){
	__doc__ = SPDocument::createNewDoc(nullptr, true, true, nullptr);	
}
extern "C" SPDocument* inkscape_get_document(){
	return __doc__;
}

int __inkstate__ = 0;
extern "C" int inkscape_get_state(){ return __inkstate__; }
extern "C" int inkscape_poll_state(){
	int ret = __inkstate__;
	__inkstate__=0;
	return ret;
}


static void test_button(GtkWidget *widget, gpointer   data) {
	std::cout << "clicked OK" << std::endl;
	Inkscape::XML::Node *repr = __doc__->getReprRoot();
	__inkstate__=0;
	// see src/inkscape.cpp
	FILE *file = Inkscape::IO::fopen_utf8name("/tmp/__inkscape__.svg", "w");
	gchar *errortext = nullptr;
	if (file) {
		sp_repr_save_stream(repr->document(), file, SP_SVG_NS_URI);
		fclose(file);
		__inkstate__ = 1;
	} else {
		__inkstate__ = -1;
	}
}

'''

INKSCAPE_TOOLBAR = '''
        //auto split = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
        auto grid = gtk_grid_new();
        //auto btn = gtk_widget_new(GTK_TYPE_BUTTON, "hi");//new Gtk::Button();
        auto btn = gtk_button_new_with_label("blender");
        //btn->set_label("hello");
        //split->pack_start(*btn);
        //split->pack_start(*Glib::wrap(dtw->tool_toolbox), false, true);
        gtk_grid_attach(GTK_GRID(grid), btn, 0, 0, 1, 1);
        gtk_grid_attach(GTK_GRID(grid), dtw->tool_toolbox, 0, 1, 1, 1);
        dtw->_hbox->pack_start(*Glib::wrap(grid), false, true);
        g_signal_connect(btn, "clicked", G_CALLBACK(test_button), NULL);


'''

#SPDocument *SPDocument::createNewDoc(gchar const *document_uri, bool keepalive, bool make_new, SPDocument *parent)

INKSCAPE_MODULE_PRE = '''
#include "document.h"
SPDocument *__doc__ = nullptr;

'''

INKSCAPE_MODULE = '''
#include "inkscape-application.h"
#include "inkscape.h"             // Inkscape::Application

extern "C" void inkscape_new_document();
extern "C" SPDocument* inkscape_get_document();


ConcreteInkscapeApplication<Gtk::Application> *app;
InkscapeWindow *win;
SPDocument *__doc__ = nullptr;

extern "C" void inkscape_init(){
	std::cout << "inkscape_init()" << std::endl;
	//app = ConcreteInkscapeApplication<Gtk::Application>::get_instance_pointer();
	app = &(ConcreteInkscapeApplication<Gtk::Application>::get_instance());
	std::cout << app << std::endl;
	Inkscape::Application::create(true);
}
extern "C" void inkscape_window_open(){
	std::cout << "new SPDoc" << std::endl;
	//__doc__ = SPDocument::createNewDoc(nullptr, true, true, nullptr);
	// CAPI
	inkscape_new_document();
	__doc__ = inkscape_get_document();
	app->document_add(__doc__);
	std::cout << "window_open" << std::endl;
	win = app->window_open(__doc__);
	std::cout << "window_open OK" << std::endl;
}


extern "C" void inkscape_gtk_update(){
	while (gtk_events_pending()) gtk_main_iteration();
}
'''


def get_inkscape_includes():
	cmd = [
		'-I./src/include', '-I./src', '-I/usr/include/glib-2.0',
		#'-I/usr/include/giomm-2.68', ## gtk4
		'-I/usr/include/giomm-2.4', ## gtk3
		#'-I/usr/include/gdkmm-2.4',
		'-I/usr/include/gdkmm-3.0',
		#'-I/usr/include/pangomm-2.48', ## gtk4
		'-I/usr/include/pangomm-1.4', ## gtk3
		'-I/usr/include/pango-1.0',
		'-I/usr/include/harfbuzz', 
		#'-I/usr/include/cairomm-1.16',  ## gtk4?
		'-I/usr/include/cairomm-1.0',
		'-I/usr/include/cairo', 
		'-I/usr/include/freetype2',
		'-I/usr/include/gtk-3.0',
		'-I/usr/include/gdk-pixbuf-2.0',
		'-I/usr/include/atkmm-1.6',
		'-I/usr/include/atk-1.0',
		'-I/usr/include/gtkmm-3.0/', 
		#'-I/usr/include/gtkmm-2.4/', ## old gtk2
		#'-I/usr/include/glibmm-2.68', 
		'-I/usr/include/glibmm-2.4', 
		'-I/usr/include/sigc++-2.0/', 
	]
	if os.path.isdir('/usr/lib/x86_64-linux-gnu'):
		sdir = '/usr/lib/x86_64-linux-gnu' ## debian based
	else:
		sdir = '/usr/lib64'  ## fedora based
	cmd += [
		#'-I/usr/lib/x86_64-linux-gnu/glibmm-2.68/include', 
		'-I%s/glibmm-2.4/include' % sdir, 
		'-I%s/glib-2.0/include' % sdir,
		'-I%s/sigc++-2.0/include' % sdir,
		'-I%s/giomm-2.4/include' % sdir,

		#'-I/usr/lib/x86_64-linux-gnu/gdkmm-2.4/include',
		'-I%s/gdkmm-3.0/include' % sdir,

		'-I%s/pangomm-1.4/include' % sdir,

		'-I%s/cairomm-1.0/include' % sdir,
		#'-I/usr/lib/x86_64-linux-gnu/cairomm-1.16/include',

		'-I%s/gtkmm-3.0/include' % sdir,
		'-I%s/atkmm-1.6/include' % sdir,
		]
	return cmd

def inkscape_python():
	so  = '/tmp/libinkscape.so'
	tmp = '/tmp/libinkscape.c++'
	open(tmp,'w').write(INKSCAPE_MODULE)
	cmd = [
		'g++', 
		'-shared', '-fPIC',
		'-o', so, tmp, 
		'-L', os.path.join(_buildir,'lib'),
		'-l', 'inkscape_base',   ## this is actually: libinkscape_base.so
		'-l', 'gtk-3',
	] + get_inkscape_includes()

	print(cmd)
	subprocess.check_call(cmd)


	if False:
		tmp = '/tmp/libinkscape.pre.c++'
		sopre = '/tmp/libinkscape.pre.so'
		open(tmp,'w').write(INKSCAPE_MODULE_PRE)
		cmd = [
			'g++', 
			'-shared', '-fPIC',
			'-o', sopre, tmp, 
			#'-L', os.path.join(_buildir,'lib'),
			#'-l', 'inkscape_base',   ## this is actually: libinkscape_base.so
			#'-l', 'gtk-3',
		] + get_inkscape_includes()
		print(cmd)
		subprocess.check_call(cmd)

		print('loading:', sopre)
		libsopre = ctypes.CDLL(sopre)  ## must be loaded first
		print(libsopre._doc_)

	print('loading:', INKSCAPE_SO)
	libase = ctypes.CDLL(INKSCAPE_SO)  ## must be loaded first
	print(libase)
	print('loading:', so)
	lib = ctypes.CDLL(so)
	print(lib)
	print(lib.inkscape_init)
	lib.inkscape_init()
	lib.inkscape_gtk_update()
	lib.inkscape_window_open()
	while True:
		lib.inkscape_gtk_update()
		status = lib.inkscape_poll_state()
		if status < 0:
			print('inkscape CAPI error:', status)
			break
		elif status == 1:
			tmp = "/tmp/__inkscape__.svg"
			svg2blender = os.path.join(_thisdir,'svg2blender.py')
			cmd = ['python3', svg2blender, tmp, '--blender']
			print(cmd)
			subprocess.check_call(cmd)

if __name__=='__main__':
	if not os.path.isfile(INKSCAPE_EXE) or '--rebuild' in sys.argv:
		build()
	if not os.path.isdir('/usr/local/share/inkscape'):
		os.system('sudo mkdir /usr/local/share/inkscape')
		os.system('sudo cp -Rv ./share/pixmaps /usr/local/share/inkscape/.')
	if not os.path.isdir('/usr/local/share/inkscape/icons') and os.path.isdir('/usr/share/inkscape/icons'):  ## symlink icons from system installed inkscape
		cmd = 'sudo ln -s /usr/share/inkscape/icons /usr/local/share/inkscape/icons'
		print(cmd)
		os.system(cmd)

	ensure_user_config()
	if '--exe' in sys.argv:
		subprocess.check_call([INKSCAPE_EXE])
	else:
		inkscape_python()
