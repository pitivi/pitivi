/* 
 * PiTiVi
 * Copyright (C) <2004> Edward G. Hervey <hervey_e@epita.fr>
 *                      Guillaume Casanova <casano_g@epita.fr>
 *			Stephan Bloch <bloch_s@epitech.net> 
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
#include <gdk/gdkkeysyms.h>
#include "pitivi.h"
#include "pitivi-types.h"
#include "pitivi-projectwindows.h"
#include "pitivi-toolbox.h"
#include "pitivi-units.h"
#include "pitivi-ruler.h"

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
#define PITIVI_TIMELINE_LOGO "../pixmaps/pitivi-logo3.png"
#define PITIVI_MENU_TIMELINE_FILE "../ui/pitivi-timeline.xml"

#define PITIVI_TIMELINE_DF_WIN_WIDTH  1000
#define PITIVI_TIMELINE_DF_WIN_HEIGHT 300

#define LEFT_PANED_SIZE 80

#define SEPARATOR_WIDTH  3

#define TOTAL_SECOND_TIME  7200
#define PIXEL_PER_SECOND      1

typedef struct _PitiviTimelineWindowPrivate PitiviTimelineWindowPrivate;

enum {
  EA_DEFAULT_FILE,
  EA_RECENT_FILE,
  EA_WINDOWMENU_FILE,
  EA_LAST_ACTION
};

struct _PitiviTimelineWindow
{
  PitiviProjectWindows parent;

  /* instance public members */
  
  PitiviToolbox	       *toolbox;
  GtkWidget	       *current_time;
  GtkWidget		*hruler;
  int			unit;
  int			zoom;
  GtkAdjustment		*hscrollbar;
  
  /* nb_added */
  gint64		nb_added[1];

  /* Backgrounds fro tracks */
  GdkPixmap		*bgs[5];
  
  /* copy */
  GtkWidget		*copy;

  /* actions menu */
  
  GtkActionGroup *actions_group[EA_LAST_ACTION];
  
  /* private */
  PitiviTimelineWindowPrivate *private;
};

struct _PitiviTimelineWindowClass
{
  PitiviProjectWindowsClass parent;
 
  /* class members */
  
  void (* activate)     (PitiviTimelineWindow *timew);
  void (* deactivate)   (PitiviTimelineWindow  *timew);
  void (* deselect)     (PitiviTimelineWindow  *timew);
  void (* zoom_changed) (PitiviTimelineWindow  *timew);
  void (* copy)         (PitiviTimelineWindow  *timew, gpointer data);
  void (* delete)       (PitiviTimelineWindow  *timew, gpointer data);
  void (* dbk_source)         (PitiviTimelineWindow *timew, gpointer data);
  void (* drag_source_begin)  (PitiviTimelineWindow *timew, gpointer data);
  void (* drag_source_end)    (PitiviTimelineWindow *timew, gpointer data);
  void (* selected_source)    (PitiviTimelineWindow *timew, gpointer data);
  void (* associate_effect)   (PitiviTimelineWindow *timew, gpointer data);
};

/* used by PITIVI_TIMELINEWINDOW_TYPE */
GType pitivi_timelinewindow_get_type (void);

/*
 * Method definitions.
 */

PitiviTimelineWindow	*pitivi_timelinewindow_new (PitiviMainApp *mainapp);
PitiviMainApp		*pitivi_timelinewindow_get_mainApp (PitiviTimelineWindow	*timelinewindow);
GtkWidget		*pitivi_timelinewindow_get_container (PitiviTimelineWindow *self);
void			pitivi_timelinewindow_windows_set_action (PitiviTimelineWindow *self, gchar *name,
								  gboolean status);
/* ********* */
/* Utils     */
/* ********* */

void
pitivi_timelinewindow_deactivate (PitiviTimelineWindow *self);

void
pitivi_timelinewindow_activate (PitiviTimelineWindow *self);

void
pitivi_timelinewindow_zoom_changed (PitiviTimelineWindow *self);

gboolean
pitivi_timelinewindow_configure_event (GtkWidget *widget);

void
pitivi_timelinewindow_update_time (PitiviTimelineWindow *self, gint64 ntime);

void
pitivi_timelinewindow_stop (PitiviTimelineWindow *self);

#endif
