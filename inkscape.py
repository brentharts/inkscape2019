#!/usr/bin/env python3
import os, sys, subprocess, xml.dom.minidom, ctypes, atexit, json, time
import hashlib

if '--install' in sys.argv:
	#if 'fedora' in os.uname().nodename:  ## this breaks when connected to internet DHCP :(
	if os.path.isfile('/usr/bin/dnf'):
		cmd = 'sudo dnf install python3-gobject libsoup-devel gsl-devel pango-devel cairo-devel double-conversion-devel gc-devel potrace-devel gtkmm3.0-devel libgdl-devel gtkspell3-devel boost-devel libxslt-devel'
	else:
		cmd = 'sudo apt-get install python3-gi libharfbuzz-dev libmagick++-dev libaspell-dev libgraphicsmagick1-dev libgtkspell3-3-dev libcdr-dev libvisio-dev libwpg-dev libwpd-dev libsoup2.4-dev libxslt-dev libboost-all-dev liblcms2-dev libgc-dev libdouble-conversion-dev libpotrace-dev libpangomm-2.48-dev libcairomm-1.16-dev libgtkmm-3.0-dev libgdl-3-dev libpoppler-dev libpoppler-glib-dev mm-common'
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

def build(use_swatches=False):
	open('/tmp/__inkscape__.toolbar.inc','w').write(INKSCAPE_TOOLBAR)
	open('/tmp/__inkscape__.header.inc','w').write(INKSCAPE_HEADER)
	open('/tmp/__inkscape__.exit.inc','w').write(INKSCAPE_EXIT)

	open('/tmp/__inkscape__.dock.inc','w').write(INKSCAPE_DOCK)
	open('/tmp/__inkscape__.dockh.inc','w').write(INKSCAPE_DOCKH)
	open('/tmp/__inkscape__.dockh.public.inc','w').write(INKSCAPE_DOCKH_PUBLIC)

	if use_swatches:
		open('/tmp/__inkscape__.swatch.inc','w').write(INKSCAPE_SWATCH)
	else:
		open('/tmp/__inkscape__.swatch.inc','w').write('')

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


INKSCAPE_DOCK = '''
	this->blender_preview_image = new Gtk::Image();
	//auto lab = new Gtk::Label();
	//lab->set_label("my custom dock");
	//_filler.pack_start( *lab );
	_filler.pack_start( *this->blender_preview_image );

	Glib::signal_timeout().connect([&]()->bool{
		if (__inkstate__ < 0) return false;
		if (file_exists("/tmp/__ink3d__.png")) {
			this->blender_preview_image->set("/tmp/__ink3d__.png");
			remove("/tmp/__ink3d__.png");
		} else {
			//std::cout << "File /tmp/__ink3d__.png does not exist." << std::endl;
			__inkstate__=2;
		}
		return true;
	}, 1000);
'''

INKSCAPE_DOCKH = '''
#include <gtkmm/label.h>
#include <gtkmm/image.h>
#include <glibmm/timer.h>
#include <glibmm.h>
#include <stdio.h>  // for old C `remove`

extern "C" int __inkstate__;

#include <sys/stat.h>
static bool file_exists(const std::string& filename) {
	struct stat buffer;
	return (stat(filename.c_str(), &buffer) == 0);
}
'''

INKSCAPE_DOCKH_PUBLIC = '''
	Gtk::Image *blender_preview_image;
'''

#dtw->_panels = new Inkscape::UI::Dialog::SwatchesPanel("/embedded/swatches");
#dtw->_panels->set_vexpand(false);
INKSCAPE_SWATCH = '''
	dtw->_vbox->pack_end(*dtw->_panels, false, true);
'''

INKSCAPE_EXIT = '''
	std::cout << "user clicked exit button" << std::endl;
	__inkstate__ = -1;

'''

INKSCAPE_HEADER = '''
int __inkstate__ = 0;

#include "io/sys.h"
SPDocument *__doc__;
extern "C" void inkscape_new_document(){
	__doc__ = SPDocument::createNewDoc(nullptr, true, true, nullptr);	
}
extern "C" SPDocument* inkscape_get_document(){
	return __doc__;
}
extern "C" int inkscape_save_temp(){
	Inkscape::XML::Node *repr = __doc__->getReprRoot();
	// see src/inkscape.cpp
	FILE *file = Inkscape::IO::fopen_utf8name("/tmp/__inkscape__.svg", "w");
	gchar *errortext = nullptr;
	if (file) {
		sp_repr_save_stream(repr->document(), file, SP_SVG_NS_URI);
		fclose(file);
		return 1;
	} else {
		return -2;
	}	
}

extern "C" int inkscape_get_state(){ return __inkstate__; }
extern "C" int inkscape_poll_state(){
	int ret = __inkstate__;
	__inkstate__=0;
	return ret;
}
static void test_button(GtkWidget *widget, gpointer   data) {
	std::cout << "clicked OK" << std::endl;
	__inkstate__ = inkscape_save_temp();
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


extern "C" int inkscape_gtk_update(){
	int updates = 0;
	while (g_main_pending()) {
		g_main_context_iteration(NULL, FALSE);
		updates ++;
	}
	return updates;
}
'''

#/usr/include/glib-2.0/glib/deprecated/gmain.h:110:78: error: expected primary-expression before ‘)’ token
#  110 | #define g_main_iteration(may_block) g_main_context_iteration (NULL, may_block) GLIB_DEPRECATED_MACRO_IN_2_26_FOR(g_main_context_iteration)


## https://stackoverflow.com/questions/21271484/gtk-events-pending-returns-false-with-events-still-pending
#extern "C" int inkscape_gtk_update(){
#	int updates = 0;
#	while (gtk_events_pending()) { // just calling this updates events if required?
#		//gtk_main_iteration(); // so calling this is not even needed?
#		updates ++;
#	}
#	if (updates) std::cout << "c++ can see updates:" << updates << std::endl;
#	return updates;
#}



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

RENDER_PROC = None
def inkscape_python( force_rebuild=True ):
	global RENDER_PROC
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

	if not os.path.isfile(so) or force_rebuild:
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
	t = last_update = time.time()
	render_ready = False
	while True:
		if RENDER_PROC:
			time.sleep(0.1)
		gtkupdates = lib.inkscape_gtk_update()
		if gtkupdates > 1:
			#print('gtkupdates:', gtkupdates)
			last_update = time.time()
			render_ready = False
		else:
			idle = time.time() - last_update
			#print('idle for:', idle)
			if idle > 3:  ## wait 3 seconds
				render_ready = True
			if RENDER_PROC:
				time.sleep(0.1)

		status = lib.inkscape_poll_state()
		if status < 0:
			if status < -1:
				print('inkscape CAPI error:', status)
			sys.exit()  ## TODO proper exit
			break
		elif status == 1:
			tmp = "/tmp/__inkscape__.svg"
			svg2blender = os.path.join(_thisdir,'svg2blender.py')
			cmd = ['python3', svg2blender, tmp, '--blender']
			print(cmd)
			subprocess.check_call(cmd)
			if os.path.isfile('/tmp/__inkscape__.json'):
				changes = json.loads(open('/tmp/__inkscape__.json').read())
				print('changes from blender:', changes)
				os.unlink('/tmp/__inkscape__.json')
				#save_ink3d( tmp, changes)
				d = {
					'svg': open(tmp).read(),
					'changes' : changes,
				}
				win = SaveHelper(d)
				win.show_all()
				Gtk.main()
				print('clean exit Gtk.main')

		if render_ready and not os.path.isfile('/tmp/__ink3d__.png'):
			if RENDER_PROC:
				print(RENDER_PROC)
				if RENDER_PROC.poll() is None:
					print('waiting...')
				else:
					print('done')
					RENDER_PROC = None
			else:
				lib.inkscape_save_temp()
				tmp = "/tmp/__inkscape__.svg"
				if svg_is_updated(tmp):
					svg2blender = os.path.join(_thisdir,'svg2blender.py')
					cmd = ['python3', svg2blender, tmp, '--blender', '--render', '/tmp/__ink3d__.png']
					print(cmd)
					RENDER_PROC=subprocess.Popen(cmd)

_PREV_HASH = None
def svg_is_updated(f):
	global _PREV_HASH
	dat = open(f,'rb').read()
	hash = hashlib.md5(dat).hexdigest()
	if hash != _PREV_HASH:
		_PREV_HASH = hash
		return True
	else:
		_PREV_HASH = hash
		return False
	#svg = xml.dom.minidom.parseString()  ## TODO check if empty drawing

def save_ink3d(svg, changes):
	import pickle
	d = {
		'svg': open(svg).read(),
		'changes' : changes,
	}
	open('/tmp/__inkscape__.ink3d', 'wb').write(pickle.dumps(d))

try:
	import gi
except:
	gi = None
	SaveHelper = None

if not gi:
	print('you should install python3-gi (ubuntu) or python3-gobject (fedora)')

if gi:
	gi.require_version('Gtk', '3.0')
	from gi.repository import Gtk

	def run_frontend():
		w = Ink3D()
		w.show_all()
		Gtk.main()

	class Ink3D(Gtk.Window):
		def __init__(self, project_dir=os.path.expanduser('~/Documents')):
			self.project_dir = project_dir
			super().__init__(title="InkScape3D")
			self.set_default_size(380, 200)
			vbox = Gtk.VBox(spacing=6)
			self.add(vbox)
			btn = Gtk.Button(label='New Drawing')
			btn.connect("clicked", self.on_new_drawing)

			vbox.pack_start(btn, False, False, 0)
			for file in os.listdir(self.project_dir):
				if file.endswith('.ink3d'):
					pth = os.path.join(self.project_dir,file)
					btn = Gtk.Button(label=pth)
					vbox.pack_start(btn, False, False, 0)
					btn.connect("clicked", lambda b, f=pth:self.on_open(f))

			self.connect("destroy", Gtk.main_quit)

		def on_open(self, file):
			view_ink3d(file)

		def on_new_drawing(self, btn):
			self.close()
			Gtk.main_quit()
			inkscape_python(force_rebuild='--dev' in sys.argv)


	class SaveHelper(Gtk.Window):
		def __init__(self, dump):
			super().__init__(title="Save Ink3D File")
			self.dump = dump
			self.set_default_size(380, 200)
			vbox = Gtk.VBox(spacing=6)
			self.add(vbox)
			label = Gtk.Label(label="Project Folder:")
			vbox.pack_start(label, False, False, 0)
			self.entry_prj = Gtk.Entry()
			self.entry_prj.set_text(os.path.expanduser('~/Documents'))
			vbox.pack_start(self.entry_prj, False, False, 0)

			label = Gtk.Label(label="Ink3D File Name:")
			vbox.pack_start(label, False, False, 0)
			self.entry_file = Gtk.Entry()
			self.entry_file.set_text('%s.ink3d' % time.time())
			vbox.pack_start(self.entry_file, False, False, 0)

			button = Gtk.Button(label="Save")
			button.connect("clicked", self.on_click)
			vbox.pack_start(button, False, False, 0)
			self.connect("destroy", Gtk.main_quit)

		def on_click(self, button):
			import pickle
			path = os.path.join( self.entry_prj.get_text(), self.entry_file.get_text() )
			if not path.endswith('.ink3d'): path += '.ink3d'
			print('saving path:', path)
			open(path, 'wb').write(pickle.dumps(self.dump))
			button.set_label('SAVED OK')
			self.close()
			Gtk.main_quit()

def view_ink3d(ink3d):
	import pickle
	d = pickle.loads(open(ink3d,'rb').read())
	tmp = "/tmp/__inkviewer__.svg"
	open(tmp,'w').write(d['svg'])
	tmpj = '/tmp/__inkviewer__.json'
	open(tmpj,'w').write( json.dumps(d['changes']) )
	svg2blender = os.path.join(_thisdir,'svg2blender.py')
	cmd = ['python3', svg2blender, tmp, '--blender', tmpj]
	print(cmd)
	subprocess.check_call(cmd)

def run_inkscape():
	for arg in sys.argv:
		if arg.endswith('.ink3d'):
			view_ink3d(arg)
			sys.exit()

	if '--exe' in sys.argv:
		subprocess.check_call([INKSCAPE_EXE])
	else:
		inkscape_python()

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

	if gi and '--no-frontend-ui' not in sys.argv:
		run_frontend()
	else:
		run_inkscape()
