/* 
 * PiTiVi
 * Copyright (C) <2004> Edward G. Hervey <hervey_e@epita.fr>
 *                      Guillaume Casanova <casano_g@epita.fr>
 *
 * This software has been written in EPITECH <http://www.epitech.net>
 * EPITECH is a computer science school in Paris - FRANCE -
 * under the direction of Flavien Astraud and Jerome Landrieu.
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public
 * License as published by the Free Software Foundation; either
 * version 2 of the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * General Public License for more details.
 *
 * You should have received a copy of the GNU General Public
 * License along with this program; if not, write to the
 * Free Software Foundation, Inc., 59 Temple Place - Suite 330,
 * Boston, MA 02111-1307, USA.
 */

#ifndef PITIVI_PROJECTSETTINGSWINDOW_H
#define PITIVI_PROJECTSETTINGSWINDOW_H


/*
 * Potentially, include other headers on which this header depends.
 */

#include "pitivi-types.h"
#include "pitivi-projectwindows.h"

/*
 * Type macros.
 */

#define PITIVI_PROJECTSETTINGSWINDOW_TYPE (pitivi_projectsettingswindow_get_type ())
#define PITIVI_PROJECTSETTINGSWINDOW(obj) (G_TYPE_CHECK_INSTANCE_CAST ((obj), PITIVI_PROJECTSETTINGSWINDOW_TYPE, PitiviProjectSettingsWindow))
#define PITIVI_PROJECTSETTINGSWINDOW_CLASS(klass) (G_TYPE_CHECK_CLASS_CAST ((klass), PITIVI_PROJECTSETTINGSWINDOW_TYPE, PitiviProjectSettingsWindowClass))
#define PITIVI_IS_PROJECTSETTINGSWINDOW(obj) (G_TYPE_CHECK_TYPE ((obj), PITIVI_PROJECTSETTINGSWINDOW_TYPE))
#define PITIVI_IS_PROJECTSETTINGSWINDOW_CLASS(klass) (G_TYPE_CHECK_CLASS_TYPE ((klass), PITIVI_PROJECTSETTINGSWINDOW_TYPE))
#define PITIVI_PROJECTSETTINGSWINDOW_GET_CLASS(obj) (G_TYPE_INSTANCE_GET_CLASS ((obj), PITIVI_PROJECTSETTINGSWINDOW_TYPE, PitiviProjectSettingsWindowClass))

typedef struct _PitiviProjectSettingsWindowPrivate PitiviProjectSettingsWindowPrivate;

struct _PitiviProjectSettingsWindow
{
  PitiviProjectWindows parent;

  /* instance public members */

  /* private */
  PitiviProjectSettingsWindowPrivate *private;
};

struct _PitiviProjectSettingsWindowClass
{
  PitiviProjectWindowsClass parent;
  /* class members */
};

/* used by PITIVI_PROJECTSETTINGSWINDOW_TYPE */
GType pitivi_projectsettingswindow_get_type (void);

/*
 * Method definitions.
 */

PitiviProjectSettingsWindow	*pitivi_projectsettingswindow_new(PitiviMainApp *mainapp, PitiviProject *project);

#endif
