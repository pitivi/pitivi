/* 
 * PiTiVi
 * Copyright (C) <2004> Delettrez Marc <delett_m@epita.fr>
 *                    	Pralat Raphael <pralat_r@epita.fr>  
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

#ifndef PITIVI_VIEWERWINDOW_H
#define PITIVI_VIEWERWINDOW_H

/*
 * Potentially, include other headers on which this header depends.
 */
#include "pitivi-projectwindows.h"

#include "../pixmaps/stop.xpm"
#include "../pixmaps/play.xpm"
#include "../pixmaps/pause.xpm"
#include "../pixmaps/forward.xpm"
#include "../pixmaps/backward.xpm"

/*
 * Type macros.
 */

#define PITIVI_VIEWERWINDOW_TYPE (pitivi_viewerwindow_get_type ())
#define PITIVI_VIEWERWINDOW(obj) (G_TYPE_CHECK_INSTANCE_CAST ((obj), PITIVI_VIEWERWINDOW_TYPE, PitiviViewerWindow))
#define PITIVI_VIEWERWINDOW_CLASS(klass) (G_TYPE_CHECK_CLASS_CAST ((klass), PITIVI_VIEWERWINDOW_TYPE, PitiviViewerWindowClass))
#define PITIVI_IS_VIEWERWINDOW(obj) (G_TYPE_CHECK_TYPE ((obj), PITIVI_VIEWERWINDOW_TYPE))
#define PITIVI_IS_VIEWERWINDOW_CLASS(klass) (G_TYPE_CHECK_CLASS_TYPE ((klass), PITIVI_VIEWERWINDOW_TYPE))
#define PITIVI_VIEWERWINDOW_GET_CLASS(obj) (G_TYPE_INSTANCE_GET_CLASS ((obj), PITIVI_VIEWERWINDOW_TYPE, PitiviViewerWindowClass))

#define PITIVI_VIEWER_DF_TITLE "Viewer"

typedef struct _PitiviViewerWindow PitiviViewerWindow;
typedef struct _PitiviViewerWindowClass PitiviViewerWindowClass;
typedef struct _PitiviViewerWindowPrivate PitiviViewerWindowPrivate;

struct _PitiviViewerWindow
{
  PitiviProjectWindows parent;

  /* instance public members */

  /* private */
  PitiviViewerWindowPrivate *private;
};

struct _PitiviViewerWindowClass
{
  PitiviProjectWindowsClass parent;
  /* class members */
};

/* used by PITIVI_VIEWERWINDOW_TYPE */
GType pitivi_viewerwindow_get_type (void);

/*
 * Method definitions.
 */

PitiviViewerWindow	*pitivi_viewerwindow_new();
void	pitivi_viewerwindow_set_source(PitiviViewerWindow *self, 
				       PitiviSourceFile *sf);

#endif
