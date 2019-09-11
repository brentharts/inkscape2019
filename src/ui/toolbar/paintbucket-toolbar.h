// SPDX-License-Identifier: GPL-2.0-or-later
#ifndef SEEN_PAINTBUCKET_TOOLBAR_H
#define SEEN_PAINTBUCKET_TOOLBAR_H

/**
 * @file
 * Paintbucket aux toolbar
 */
/* Authors:
 *   MenTaLguY <mental@rydia.net>
 *   Lauris Kaplinski <lauris@kaplinski.com>
 *   bulia byak <buliabyak@users.sf.net>
 *   Frank Felfe <innerspace@iname.com>
 *   John Cliff <simarilius@yahoo.com>
 *   David Turner <novalis@gnu.org>
 *   Josh Andler <scislac@scislac.com>
 *   Jon A. Cruz <jon@joncruz.org>
 *   Maximilian Albert <maximilian.albert@gmail.com>
 *   Tavmjong Bah <tavmjong@free.fr>
 *   Abhishek Sharma
 *   Kris De Gussem <Kris.DeGussem@gmail.com>
 *
 * Copyright (C) 2004 David Turner
 * Copyright (C) 2003 MenTaLguY
 * Copyright (C) 1999-2011 authors
 * Copyright (C) 2001-2002 Ximian, Inc.
 *
 * Released under GNU GPL v2+, read the file 'COPYING' for more information.
 */

#include "toolbar.h"

#include <gtkmm/adjustment.h>

class SPDesktop;

namespace Gtk {
class ComboBoxText;
}

namespace Inkscape {
namespace UI {
namespace Widget {
class UnitTracker;
}

namespace Toolbar {
class PaintbucketToolbar : public Toolbar {
private:
    Gtk::ComboBoxText *_channels_cbt;
    Gtk::ComboBoxText *_autogap_cbt;

    Glib::RefPtr<Gtk::Adjustment> _threshold_adj;
    Glib::RefPtr<Gtk::Adjustment> _offset_adj;

    UI::Widget::UnitTracker *_tracker;

    void channels_changed();
    void threshold_changed();
    void offset_changed();
    void autogap_changed();
    void defaults();

protected:
    PaintbucketToolbar(SPDesktop *desktop);

public:
    static GtkWidget * create(SPDesktop *desktop);
};

}
}
}

#endif /* !SEEN_PAINTBUCKET_TOOLBAR_H */
