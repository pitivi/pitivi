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

#ifndef PITIVI_SOURCELISTWINDOW_H
#define PITIVI_SOURCELISTWINDOW_H

typedef struct _PitiviSourceListWindow PitiviSourceListWindow;

/*
 * Potentially, include other headers on which this header depends.
 */

#include "pitivi-projectwindows.h"

/*
 * Type macros.
 */

#define PITIVI_SOURCELISTWINDOW_TYPE (pitivi_sourcelistwindow_get_type ())
#define PITIVI_SOURCELISTWINDOW(obj) (G_TYPE_CHECK_INSTANCE_CAST ((obj), PITIVI_SOURCELISTWINDOW_TYPE, PitiviSourceListWindow))
#define PITIVI_SOURCELISTWINDOW_CLASS(klass) (G_TYPE_CHECK_CLASS_CAST ((klass), PITIVI_SOURCELISTWINDOW_TYPE, PitiviSourceListWindowClass))
#define PITIVI_IS_SOURCELISTWINDOW(obj) (G_TYPE_CHECK_TYPE ((obj), PITIVI_SOURCELISTWINDOW_TYPE))
#define PITIVI_IS_SOURCELISTWINDOW_CLASS(klass) (G_TYPE_CHECK_CLASS_TYPE ((klass), PITIVI_SOURCELISTWINDOW_TYPE))
#define PITIVI_SOURCELISTWINDOW_GET_CLASS(obj) (G_TYPE_INSTANCE_GET_CLASS ((obj), PITIVI_SOURCELISTWINDOW_TYPE, PitiviSourceListWindowClass))

typedef struct _PitiviSourceListWindowClass PitiviSourceListWindowClass;
typedef struct _PitiviSourceListWindowPrivate PitiviSourceListWindowPrivate;
typedef struct _PitiviListStore PitiviListStore;


struct _PitiviSourceListWindow
{
  PitiviProjectWindows parent;

  /* instance public members */

  /* private */
  PitiviSourceListWindowPrivate *private;
};

struct _PitiviSourceListWindowClass
{
  PitiviProjectWindowsClass parent;
  /* class members */
};

/* used by PITIVI_SOURCELISTWINDOW_TYPE */
GType pitivi_sourcelistwindow_get_type (void);

/*
 * Method definitions.
 */

PitiviSourceListWindow*
pitivi_sourcelistwindow_new(PitiviMainApp *mainapp, PitiviProject *project);

#endif
