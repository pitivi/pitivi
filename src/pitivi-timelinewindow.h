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

#ifndef PITIVI_TIMELINEWINDOW_H
#define PITIVI_TIMELINEWINDOW_H

/*
 * Potentially, include other headers on which this header depends.
 */

#include "pitivi.h"
#include "pitivi-projectwindows.h"

/*
 * Type macros.
 */

#define PITIVI_TIMELINEWINDOW_TYPE (pitivi_timelinewindow_get_type ())
#define PITIVI_TIMELINEWINDOW(obj) (G_TYPE_CHECK_INSTANCE_CAST ((obj), PITIVI_TIMELINEWINDOW_TYPE, PitiviTimelineWindow))
#define PITIVI_TIMELINEWINDOW_CLASS(klass) (G_TYPE_CHECK_CLASS_CAST ((klass), PITIVI_TIMELINEWINDOW_TYPE, PitiviTimelineWindowClass))
#define PITIVI_IS_TIMELINEWINDOW(obj) (G_TYPE_CHECK_TYPE ((obj), PITIVI_TIMELINEWINDOW_TYPE))
#define PITIVI_IS_TIMELINEWINDOW_CLASS(klass) (G_TYPE_CHECK_CLASS_TYPE ((klass), PITIVI_TIMELINEWINDOW_TYPE))
#define PITIVI_TIMELINEWINDOW_GET_CLASS(obj) (G_TYPE_INSTANCE_GET_CLASS ((obj), PITIVI_TIMELINEWINDOW_TYPE, PitiviTimelineWindowClass))


#define PITIVI_TIMELINE_DF_TITLE "TimeLine Project"
#define PITIVI_TIMELINE_LOGO "../pixmaps/pitivi-logo48.png"
#define PITIVI_MENU_TIMELINE_FILE "../ui/pitivi-timeline.xml"
#define PITIVI_DF_RATE 60
#define PITIVI_TIMELINE_DF_WIN_WIDTH 600
#define PITIVI_TIMELINE_DF_WIN_HEIGHT 300


typedef struct _PitiviTimelineWindow PitiviTimelineWindow;
typedef struct _PitiviTimelineWindowClass PitiviTimelineWindowClass;
typedef struct _PitiviTimelineWindowPrivate PitiviTimelineWindowPrivate;

struct _PitiviTimelineWindow
{
  PitiviProjectWindows parent;

  /* instance public members */

  /* private */
  PitiviTimelineWindowPrivate *private;
};

struct _PitiviTimelineWindowClass
{
  PitiviProjectWindowsClass parent;
  /* class members */
};

/* used by PITIVI_TIMELINEWINDOW_TYPE */
GType pitivi_timelinewindow_get_type (void);

/*
 * Method definitions.
 */

PitiviTimelineWindow	*pitivi_timelinewindow_new(PitiviMainApp *mainapp, PitiviProject *project);

#endif
