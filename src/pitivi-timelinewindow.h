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

#include <gtk/gtk.h>
#include "pitivi.h"
#include "pitivi-projectwindows.h"
#include "pitivi-toolbox.h"

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

#define PITIVI_TIMELINE_DF_WIN_WIDTH  1000
#define PITIVI_TIMELINE_DF_WIN_HEIGHT 300

#define LEFT_PANED_SIZE 80

typedef struct _PitiviTimelineWindow PitiviTimelineWindow;
typedef struct _PitiviTimelineWindowClass PitiviTimelineWindowClass;
typedef struct _PitiviTimelineWindowPrivate PitiviTimelineWindowPrivate;

struct _PitiviTimelineWindow
{
  PitiviProjectWindows parent;

  /* instance public members */
  PitiviToolbox	       *toolbox;
  GtkWidget	       *hruler;
  GtkWidget	       *current_time;
  
  /* private */
  PitiviTimelineWindowPrivate *private;
};

struct _PitiviTimelineWindowClass
{
  PitiviProjectWindowsClass parent;
 
  /* class members */
  
  void (*drag_source_begin) (PitiviTimelineWindow *cell);
  void (* activate)   (PitiviTimelineWindow *timew);
  void (* deactivate) (PitiviTimelineWindow  *timew);
  void (* deselect)   (PitiviTimelineWindow  *timew);
  void (* delete)     (PitiviTimelineWindow  *timew, gpointer data);
};

/* used by PITIVI_TIMELINEWINDOW_TYPE */
GType pitivi_timelinewindow_get_type (void);

/*
 * Method definitions.
 */

PitiviTimelineWindow	*pitivi_timelinewindow_new (PitiviMainApp *mainapp);
PitiviMainApp		*pitivi_timelinewindow_get_mainApp (PitiviTimelineWindow	*timelinewindow);
GtkWidget		*pitivi_timelinewindow_get_right_view (PitiviTimelineWindow *self);


/* ********* */
/* Callbacks */
/* ********* */

void
pitivi_callb_menufile_exit (GtkAction *action, PitiviTimelineWindow *self );

void
pitivi_callb_menufile_exit (GtkAction *action, PitiviTimelineWindow *self );

void
pitivi_callb_menufile_new ( GtkAction *action, PitiviTimelineWindow *self );

void
pitivi_callb_menufile_open ( GtkAction *action, PitiviTimelineWindow *self );

void
pitivi_callb_menufile_saveas ( GtkAction *action, PitiviTimelineWindow *self);

void
pitivi_callb_menufile_save ( GtkAction *action, PitiviTimelineWindow *self );

void
pitivi_callb_menufile_settings ( GtkAction *action, PitiviTimelineWindow *self );

void
pitivi_callb_menufile_effectswindow_toggle ( GtkAction *action, PitiviTimelineWindow *self);

/* ********* */
/* Utils     */
/* ********* */

void
pitivi_timelinewindow_deactivate (PitiviTimelineWindow *self);

void
pitivi_timelinewindow_activate (PitiviTimelineWindow *self);

gboolean
pitivi_timelinewindow_configure_event (GtkWidget *widget, GdkEventConfigure *event, gpointer data);

#endif
