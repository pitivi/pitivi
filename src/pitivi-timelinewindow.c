/* 
 * PiTiVi
 * Copyright (C) <2004> Guillaume Casanova <casano_g@epita.fr>
 *			Stephan Bloch <bloch_s@epitech.net> 
 *                      
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

#include "pitivi.h"
#include "pitivi-debug.h"
#include "pitivi-windows.h"
#include "pitivi-timelinewindow.h"
#include "pitivi-menu.h"
#include "pitivi-stockicons.h"
#include "pitivi-timelinecellrenderer.h"
#include "pitivi-newprojectwindow.h"
#include "pitivi-settingswindow.h"
#include "pitivi-controller.h"
#include "pitivi-drawing.h"
#include "pitivi-mediatrackinfo.h"
#include "pitivi-menu-actions.h"
#include "pitivi-encodewindow.h"

#include "../pixmaps/bg.xpm"
#include "../pixmaps/bg_audio.xpm"
#include "../pixmaps/bg_video.xpm"
#include "../pixmaps/bg_effects.xpm"
#include "../pixmaps/bg_trans.xpm"

static  PitiviWindowsClass *parent_class = NULL;

enum {  
  PROP_VIEWER_WINDOW = 1,
};

/*
 **********************************************************
 * Private Structure  			                  *
 *							  *
 **********************************************************
*/

typedef struct _PitiviDefaultTracks
{
  guint track_nb;
  guint	track_type;
  gchar *track_name;
  guint track_linked;
} PitiviDefaultTracks;

struct _PitiviTimelineWindowPrivate
{
  /* Instance private members */
  
  gboolean	dispose_has_run;
  PitiviMenu	*ui_menus;
  GtkWidget	*menu_dock;
  GtkWidget	*main_vbox;
  GtkWidget	*timer;
  GtkWidget	*layout_container;
  GtkWidget	*info_container;
  GtkWidget	*hpaned;
  
  GdkWindow     *event_window;
  GdkCursor     *cursor;
  
  /* Toolbox */
  
  PitiviMainApp		*mainapp;
  GtkWidget		*viewer;
  GtkWidget		*toolcontainer;
  PitiviController	*controller;
  GtkComboBox		*unitcombobox;
  GtkComboBox		*scalecombobox;

  /* WinSettings */
  
  PitiviSettingsWindow	*WinSettings;
};


/*
 * forward definitions
 */

static PitiviDefaultTracks gtab_tracks[]=
  {
    {0, PITIVI_VIDEO_TRACK, "Video A", 5},
    {1, PITIVI_EFFECTS_TRACK, "Fx A",  0},
    {2, PITIVI_TRANSITION_TRACK, "Transition", -1},
    {3, PITIVI_EFFECTS_TRACK, "Fx B",  4},
    {4, PITIVI_VIDEO_TRACK, "Video B", 6},
    {5, PITIVI_AUDIO_TRACK, "Audio A", 0},
    {6, PITIVI_AUDIO_TRACK, "Audio B", 4},
  };

/*
 **********************************************************
 * Columns  					          *
 *							  *
 **********************************************************
*/

#define PITIVI_MAX_PISTE 6

enum {
    PITIVI_CAT_LAYER_COLUMN = 0,
    PITIVI_LAYER_COLUMN,
    PITIVI_NB_COLUMN,
};

/*
 **********************************************************
 * Signals  					          *
 *							  *
 **********************************************************
*/


enum {
  ACTIVATE_SIGNAL = 0,
  DEACTIVATE_SIGNAL,
  DESELECT_SIGNAL,
  COPY_SIGNAL,
  DELETE_SIGNAL,
  DRAG_SOURCE_BEGIN_SIGNAL,
  DRAG_SOURCE_END_SIGNAL,
  DBK_SOURCE_SIGNAL,
  ZOOM_CHANGED_SIGNAL,
  SELECT_SOURCE_SIGNAL,
  LAST_SIGNAL
};

static  guint signals[LAST_SIGNAL];

/* ********* */
/* Callbacks */
/* ********* */

gboolean
pitivi_callb_window_close (GtkWidget *win, GdkEvent *event, PitiviTimelineWindow *self);

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

void
pitivi_callb_menufile_sourcelistwindow_toggle ( GtkAction *action, PitiviTimelineWindow *self);

void
pitivi_callb_menufile_viewerwindow_toggle ( GtkAction *action, PitiviTimelineWindow *self);

gboolean
pitivi_timelinewindow_callb_key_press (PitiviTimelineWindow * widget, GdkEventKey* event, gpointer data);

void
pitivi_callb_controller_record (PitiviController *controller, PitiviTimelineWindow *self);

/*
 **********************************************************
 * MenuItems  					          *
 *							  *
 **********************************************************
*/

static GtkActionEntry file_entries[] = {
  { "FileMenu",     NULL, "_File" },
  { "WindowsMenu",  NULL, "_Windows" },
  { "FileNew",      PITIVI_STOCK_NEW_PROJECT, "Ne_w", "<control>N", "New File", G_CALLBACK (pitivi_callb_menufile_new) },
  { "FileOpen",     GTK_STOCK_OPEN, "_Open", "<control>O", "Open a file",  G_CALLBACK (pitivi_callb_menufile_open) },
  { "FileSave",     GTK_STOCK_SAVE, "_Save", "<control>S", "Save a file", G_CALLBACK (pitivi_callb_menufile_save) },
  { "FileSaveAs",   GTK_STOCK_SAVE_AS, "Save _As", "<control><alt>S", "Save a file", G_CALLBACK (pitivi_callb_menufile_saveas) },
  { "FileSettings", PITIVI_STOCK_TOOLS, "_Settings", "<control><alt>P", "Settings",  G_CALLBACK (pitivi_callb_menufile_settings) },
  { "FileExit",     GTK_STOCK_QUIT, "_Exit", "<control>Q", "Exit Application", G_CALLBACK (pitivi_callb_menufile_exit) },
};

static GtkActionEntry recent_entry[]= {
  { "FileRecent",   GTK_STOCK_OPEN, "_Open Recent File", "<control>R", "Open a recent file",  G_CALLBACK (pitivi_callb_menufile_open) },
};

static GtkToggleActionEntry windows_entries[] ={
  { "EffectWindows", PITIVI_STOCK_TOOLS, "E_ffects", "<Ctrl><Alt>E", "Toggle the effects window", G_CALLBACK (pitivi_callb_menufile_effectswindow_toggle), TRUE},
  { "SourceListWindows",PITIVI_STOCK_TOOLS, "S_ourceList", "<Ctrl><Alt>F", "Toggle the source list window", G_CALLBACK (pitivi_callb_menufile_sourcelistwindow_toggle), TRUE},
  { "ViewerWindows", PITIVI_STOCK_TOOLS, "V_iewer", "<Ctrl>V", "Toggle the viewer window", G_CALLBACK (pitivi_callb_menufile_viewerwindow_toggle), TRUE},
};


/*
 * Insert "added-value" functions here
 */

/**
 * pitivi_timelinewindow_new:
 * @PitiviMainApp: The object containing all references of the application
 *
 * Create a new window for the timeline
 *
 * Returns: An element PitiviTimelineWindow contening the timeline
 */

PitiviTimelineWindow *
pitivi_timelinewindow_new (PitiviMainApp *mainapp)
{
  PitiviTimelineWindow		*timelinewindow;
  
  timelinewindow = (PitiviTimelineWindow *) g_object_new(PITIVI_TIMELINEWINDOW_TYPE, 
							 "mainapp", mainapp,
							 NULL);
  timelinewindow->private->mainapp = mainapp;
  g_assert(timelinewindow != NULL);
  
  return timelinewindow;
}


void   
create_timeline_menu (PitiviTimelineWindow *self)
{
  PitiviMenu	*menumgr;
  gchar		*filemenu;
  int		count,pa,pv;
  
  /* Putting Menu to timeline */
  
  self->private->menu_dock = gtk_vbox_new (FALSE, 0);
  gtk_widget_show (self->private->menu_dock);
  gtk_box_pack_start (GTK_BOX (self->private->main_vbox), self->private->menu_dock,
		      FALSE, TRUE, 0);
  
  self->actions_group[EA_DEFAULT_FILE] = gtk_action_group_new ("MenuFile");
  gtk_action_group_add_actions (self->actions_group[EA_DEFAULT_FILE], file_entries\
				, G_N_ELEMENTS (file_entries), self);
  self->actions_group[EA_RECENT_FILE] = gtk_action_group_new ("MenuFileRecent");
  gtk_action_group_add_actions (self->actions_group[EA_DEFAULT_FILE], file_entries\
				, G_N_ELEMENTS (recent_entry), self);
  
  self->actions_group[EA_WINDOWMENU_FILE] = gtk_action_group_new ("WindowsMenu");
  gtk_action_group_add_toggle_actions (self->actions_group[EA_WINDOWMENU_FILE], windows_entries\
				       , G_N_ELEMENTS (windows_entries), self);
  
  gtk_action_group_set_sensitive (self->actions_group[EA_WINDOWMENU_FILE], FALSE);

  filemenu = pitivi_file (PITIVI_MENU_TIMELINE_FILE);
  if (filemenu)
    {
      menumgr = pitivi_menu_new (GTK_WIDGET (self), filemenu);
      gtk_window_add_accel_group (GTK_WINDOW (self), menumgr->accel_group);
      for (pa = 0, pv = 0, count = 0; count < EA_LAST_ACTION; count++)
	if (self->actions_group[count])
	  gtk_ui_manager_insert_action_group (menumgr->ui, self->actions_group[count], 0);
  
      PITIVI_MENU_GET_CLASS(menumgr)->configure (menumgr);
    
      // Menu Docking
  
      gtk_box_pack_start (GTK_BOX (self->private->menu_dock), menumgr->menu,
			  FALSE, TRUE, 0);
    }
}


GtkAction *
pitivi_timelinewindow_get_action_by_idx_name (PitiviTimelineWindow *self, int idx, gchar *name)
{
  GtkAction *action = gtk_action_group_get_action  (self->actions_group[idx], name);
  return action; 
}


void
pitivi_timelinewindow_file_set_action (PitiviTimelineWindow *self, gchar *name, gboolean status)
{
  GtkAction *action = pitivi_timelinewindow_get_action_by_idx_name (self, (int)EA_DEFAULT_FILE, name );
  g_object_set(G_OBJECT(action),
	       "sensitive", status, NULL);

}


void
pitivi_timelinewindow_windows_set_action (PitiviTimelineWindow *self, gchar *name, gboolean status)
{
  GtkAction *action = pitivi_timelinewindow_get_action_by_idx_name (self, (int)EA_WINDOWMENU_FILE, name );
  gtk_toggle_action_set_active (((GtkToggleAction *)action), status);
}

gboolean
pitivi_timelinewindow_windows_get_action (PitiviTimelineWindow *self, gchar *name)
{
  gboolean status;

  GtkAction *action = pitivi_timelinewindow_get_action_by_idx_name (self, (int)EA_WINDOWMENU_FILE, name );
  status = gtk_toggle_action_get_active ((GtkToggleAction *)action);
  return status;
}


void
unit_combobox_cb(GtkWidget *cbox, gpointer data)
{
  int	*tab;
  int	value;
  PitiviTimelineWindow	*tw = data;
  
  tab = gtk_object_get_data(GTK_OBJECT(cbox), "list");
  value = tab[gtk_combo_box_get_active(GTK_COMBO_BOX(cbox))];
  if (tw->unit != value) {
    tw->unit = value;
    pitivi_ruler_set_zoom_metric (GTK_RULER (tw->hruler), tw->unit, tw->zoom);
    g_signal_emit_by_name (GTK_OBJECT (tw), "zoom-changed");
  }
}

void
scale_combobox_cb(GtkWidget *cbox, gpointer data)
{
  int	*tab;
  int	value;
  PitiviTimelineWindow	*tw = data;

  tab = gtk_object_get_data(GTK_OBJECT(cbox), "list");
  value = tab[gtk_combo_box_get_active(GTK_COMBO_BOX(cbox))];
  if (tw->zoom != value) {
    tw->zoom = value;
    pitivi_ruler_set_zoom_metric (GTK_RULER (tw->hruler), tw->unit, tw->zoom);
    g_signal_emit_by_name (GTK_OBJECT (tw), "zoom-changed");
  }
}

void
create_unitscale_combobox(PitiviTimelineWindow *self, GtkWidget *parentbox)
{
  static int	unittab[2] = {PITIVI_SECONDS, PITIVI_FRAMES};
  static int	scaletab[5] = {1, 2, 4, 8, 16};

  self->private->unitcombobox = (GtkComboBox *) gtk_combo_box_new_text();

  gtk_combo_box_append_text(self->private->unitcombobox, UNITS_SECOND_TEXT);
  gtk_combo_box_append_text(self->private->unitcombobox, UNITS_FRAME_TEXT);

  gtk_object_set_data(GTK_OBJECT(self->private->unitcombobox),
		      "list", &unittab);
  g_signal_connect(self->private->unitcombobox, "changed", G_CALLBACK(unit_combobox_cb), self);
  gtk_combo_box_set_active(self->private->unitcombobox, 0);

  self->private->scalecombobox = (GtkComboBox *) gtk_combo_box_new_text();

  gtk_combo_box_append_text(self->private->scalecombobox, ZOOM_LEVEL_1);
  gtk_combo_box_append_text(self->private->scalecombobox, ZOOM_LEVEL_2);
  gtk_combo_box_append_text(self->private->scalecombobox, ZOOM_LEVEL_4);
  gtk_combo_box_append_text(self->private->scalecombobox, ZOOM_LEVEL_8);
  gtk_combo_box_append_text(self->private->scalecombobox, ZOOM_LEVEL_16);

  gtk_object_set_data(GTK_OBJECT(self->private->scalecombobox),
		      "list", &scaletab);
  g_signal_connect(self->private->scalecombobox, "changed", G_CALLBACK(scale_combobox_cb), self);
  gtk_combo_box_set_active(self->private->scalecombobox, 0);

  gtk_box_pack_start(GTK_BOX(parentbox), gtk_label_new("Unit:"),
		     FALSE, TRUE, 2);
  gtk_box_pack_start(GTK_BOX (parentbox), GTK_WIDGET(self->private->unitcombobox),
		     FALSE, TRUE, 2);
  gtk_box_pack_start(GTK_BOX(parentbox), gtk_label_new("Zoom:"),
		     FALSE, TRUE, 2);
  gtk_box_pack_start(GTK_BOX (parentbox), GTK_WIDGET(self->private->scalecombobox),
		     FALSE, TRUE, 2);
}

/*
 **********************************************************
 * Creation of tracks / Timer Label / Toolbar             *
 * 							  *
 **********************************************************
*/

void
create_toolbox (PitiviTimelineWindow *self, GtkWidget *container)
{
  PitiviMainApp	*mainapp;
  GtkWidget	*sep;

  mainapp = ((PitiviWindows *) self)->mainapp;
  self->toolbox = pitivi_toolbox_new (mainapp);
  gtk_toolbar_set_icon_size (GTK_TOOLBAR (self->toolbox), GTK_ICON_SIZE_MENU );
  sep = gtk_hseparator_new ();
  gtk_box_pack_start (GTK_BOX (container), GTK_WIDGET (self->toolbox), FALSE, FALSE, 0);
  gtk_box_pack_start (GTK_BOX (container), sep, FALSE, FALSE, 0);
}

void
create_timeline_toolbar (PitiviTimelineWindow *self)
{
  GtkWidget	*sep;
  GtkWidget	*hbox;

  hbox = gtk_hbox_new (FALSE, 0);
  
  /* Docking Toolbox */
  
  create_toolbox (self, GTK_WIDGET (hbox));
  
  /* Separator */
  
  sep = gtk_vseparator_new ();
  gtk_box_pack_start (GTK_BOX (hbox), GTK_WIDGET(sep),
		      FALSE, FALSE, 0);
  
  /* Play Controller */
  
  self->private->controller = pitivi_controller_new ();
  gtk_box_pack_start (GTK_BOX (hbox), GTK_WIDGET(self->private->controller),
		      FALSE, TRUE, 0);
  g_signal_connect (G_OBJECT (self->private->controller),
		    "record", G_CALLBACK(pitivi_callb_controller_record), self);
    
  /* Separator */
  
  sep = gtk_vseparator_new ();
  gtk_box_pack_start (GTK_BOX (hbox), GTK_WIDGET(sep),
		      FALSE, FALSE, 0);
  
  /* Unit/Scale Selector */

  create_unitscale_combobox(self, hbox);
  
  gtk_box_pack_start (GTK_BOX (self->private->main_vbox), GTK_WIDGET(hbox),
		      FALSE, TRUE, 0);
  
  self->private->toolcontainer = GTK_WIDGET(hbox);
}


void
check_track (GtkWidget *widget, PitiviTimelineCellRenderer *cells)
{
  gboolean activate;
  GList	*childlist;
  GList *childwidget;
  
  activate = gtk_toggle_button_get_active(GTK_TOGGLE_BUTTON(widget));
  childwidget = gtk_container_get_children (GTK_CONTAINER (cells));
  for (childlist = childwidget; childlist; childlist = childlist->next )
    {
      if (activate)
	gtk_widget_hide (GTK_WIDGET (childlist->data));
      else
	gtk_widget_show (GTK_WIDGET (childlist->data));
    }
}

void
create_ruler (PitiviTimelineWindow *self)
{  
  self->hruler = pitivi_ruler_new (self->unit);
  pitivi_ruler_set_metric (GTK_RULER (self->hruler), PITIVI_RSECONDS);
  gtk_ruler_set_range (GTK_RULER (self->hruler), 0, TOTAL_SECOND_TIME, 0, TOTAL_SECOND_TIME);
  gtk_widget_set_size_request (self->hruler, TOTAL_SECOND_TIME * PIXEL_PER_SECOND, 25);
  g_signal_connect_swapped (G_OBJECT (self->private->main_vbox), "motion_notify_event",
			    G_CALLBACK (EVENT_METHOD (self->hruler, motion_notify_event)),
			    G_OBJECT (self->hruler));
}

void
create_tracks_links (GtkWidget **wcells)
{
  PitiviTimelineCellRenderer **cells;
  int   len;
  int	i, j;
  
  cells = (PitiviTimelineCellRenderer **)wcells;
  len = (sizeof (gtab_tracks)/sizeof(PitiviDefaultTracks));
  for (i = 0; i < len; i++)
    {
      for (j = 0; j < len; j++)
	if (gtab_tracks[i].track_nb == gtab_tracks[j].track_linked)
	  {
	    if (cells[i])
	      {
		if ( gtab_tracks[j].track_type != PITIVI_EFFECTS_TRACK )
		  cells[i]->linked_track = GTK_WIDGET ( cells[j] );
		else /* Effects */
		  {
		    cells[i]->effects_track = GTK_WIDGET ( cells[j] );
		    PITIVI_TIMELINECELLRENDERER (cells[i]->effects_track)->linked_track = GTK_WIDGET ( cells[i] );
		  }
	      }
	  }
    }
}

void
create_timelabel (PitiviTimelineWindow *self, GtkWidget *container)
{
  GtkWidget *hbox;
  GtkWidget *label;
  
  hbox = gtk_hbox_new (FALSE, 0); 
  label =  gtk_label_new ("Time :");
  pitivi_widget_changefont (label, "helvetica 9");
  gtk_box_pack_start (GTK_BOX (hbox), label, FALSE, TRUE, 4);
  self->private->timer = gtk_label_new ("--:--:--");
  pitivi_widget_changefont (self->private->timer, "helvetica 10");
  gtk_box_pack_start (GTK_BOX (hbox), self->private->timer, FALSE, TRUE, 4);
  gtk_box_pack_start (GTK_BOX (container), hbox, FALSE, TRUE, 4);  
}

void	
create_tracks (PitiviTimelineWindow *self)
{
  int len = (sizeof (gtab_tracks)/sizeof(PitiviDefaultTracks));
  GtkWidget *cell[len];
  GtkWidget *nfo;
  GtkWidget *vbox_right, *vbox_left;
  int count = 0;
  GtkWidget * pHScrollbarRight;
  
  self->private->hpaned = gtk_hpaned_new();
  vbox_left = gtk_vbox_new (FALSE, 0); 

  create_timelabel (self, vbox_left);
  
  gtk_paned_set_position(GTK_PANED(self->private->hpaned), (80));
  vbox_right = gtk_vbox_new (FALSE, 0);
  
  /* Docking Ruler */
  
  create_ruler (self);
  gtk_box_pack_start (GTK_BOX (vbox_right), self->hruler, FALSE, FALSE, 0);     

  self->private->layout_container = gtk_table_new ( len, 1, FALSE );
  self->private->info_container = gtk_table_new ( len, 1, FALSE );
  gtk_box_pack_start (GTK_BOX (vbox_right), self->private->layout_container, FALSE, FALSE, 0);
  gtk_box_pack_start (GTK_BOX (vbox_left),  self->private->info_container,   FALSE, FALSE, 0);
  
  // Creating Tracks
  for (count = 0; count < len; count++)
    {
      if (gtab_tracks[count].track_type != -1)
	{
	  cell[count] = pitivi_timelinecellrenderer_new (gtab_tracks[count].track_nb, gtab_tracks[count].track_type, self);
	  nfo = (GtkWidget *) pitivi_mediatrackinfo_new (((PitiviTimelineCellRenderer *)cell[count]), gtab_tracks[count].track_name);	  
	  gtk_table_attach (GTK_TABLE (self->private->layout_container), 
			    cell[count],
			    0, 1, count, count+1,
			    GTK_EXPAND | GTK_FILL,
			    GTK_EXPAND | GTK_FILL,
			    0, SEPARATOR_WIDTH);
	  
	  gtk_table_attach (GTK_TABLE (self->private->info_container), 
			    nfo,
			    0, 1, count, count+1,
			    GTK_EXPAND | GTK_FILL,
			    GTK_EXPAND | GTK_FILL,
			    0, SEPARATOR_WIDTH);
	  g_signal_connect_swapped (G_OBJECT (GTK_LAYOUT (cell[count])), "motion_notify_event",
				    G_CALLBACK (EVENT_METHOD (self->hruler, motion_notify_event)),
				    G_OBJECT (self->hruler));
	}
    }
  create_tracks_links (cell);
  gtk_box_pack_start (GTK_BOX (self->private->main_vbox), self->private->hpaned, FALSE, FALSE, 0);
  
  // Left Scrollbar
  gtk_paned_pack1 (GTK_PANED(self->private->hpaned), vbox_left, FALSE, FALSE);
  // Right HScrollbar
  pHScrollbarRight = gtk_scrolled_window_new (NULL, NULL);
  gtk_scrolled_window_set_policy (GTK_SCROLLED_WINDOW (pHScrollbarRight),
  			  GTK_POLICY_ALWAYS, GTK_POLICY_NEVER);
  gtk_scrolled_window_add_with_viewport (GTK_SCROLLED_WINDOW (pHScrollbarRight),
  				 GTK_WIDGET (vbox_right));
  self->hscrollbar = gtk_scrolled_window_get_hadjustment(GTK_SCROLLED_WINDOW(pHScrollbarRight));
  gtk_paned_pack2 (GTK_PANED(self->private->hpaned), pHScrollbarRight, FALSE, FALSE);
  
  // Configure Event
  gtk_signal_connect (GTK_OBJECT (self), "configure_event"\
		      , GTK_SIGNAL_FUNC ( pitivi_timelinewindow_configure_event ), self->private->hpaned);
}

static GObject *
pitivi_timelinewindow_constructor (GType type,
				   guint n_construct_properties,
				   GObjectConstructParam * construct_properties)
{ 
  PitiviTimelineWindowClass *klass;
  GObjectClass *parent_class;
  PitiviTimelineWindow *self;
  GObject	*object;
  

  /* Invoke parent constructor. */
  
  klass = PITIVI_TIMELINEWINDOW_CLASS (g_type_class_peek (PITIVI_TIMELINEWINDOW_TYPE));
  parent_class = G_OBJECT_CLASS (g_type_class_peek_parent (klass));
  object = parent_class->constructor (type, n_construct_properties,
				      construct_properties);
  /* Getting MainApp */
  
  self = (PitiviTimelineWindow *) object;
  self->private->main_vbox = gtk_vbox_new (FALSE, 0);
  gtk_widget_show (self->private->main_vbox);
  gtk_container_add  (GTK_CONTAINER (self), self->private->main_vbox);

  self->unit = PITIVI_SECONDS;
  self->zoom = 1;
  /* Timeline Menu */
  create_timeline_menu (self);
  /* Timeline Toolbox */
  create_timeline_toolbar (self);
  /* Create Tracks */
  create_tracks (self);
  /* Desactivation */
  pitivi_timelinewindow_deactivate (self);

  g_signal_connect (G_OBJECT (self), "delete-event",
		    G_CALLBACK (pitivi_callb_window_close),
		    self);

  return object;
}

static void
pitivi_timelinewindow_instance_init (GTypeInstance * instance, gpointer g_class)
{
  
  PitiviTimelineWindow *self = (PitiviTimelineWindow *) instance;
  self->private = g_new0(PitiviTimelineWindowPrivate, 1);
  
  /* initialize all public and private members to reasonable default values. */ 
  
  self->private->dispose_has_run = FALSE;
  
  /* Main Window : Setting default Size */
  
  gtk_window_set_title (GTK_WINDOW (self), PITIVI_TIMELINE_DF_TITLE);
  gtk_window_set_default_size (GTK_WINDOW (self), PITIVI_TIMELINE_DF_WIN_WIDTH, PITIVI_TIMELINE_DF_WIN_HEIGHT); 
  
  /* Initialising Pixmaps Background */
  
  self->bgs[PITIVI_VIDEO_TRACK] = pitivi_drawing_getpixmap (GTK_WIDGET (self), bg_video_xpm );
  self->bgs[PITIVI_AUDIO_TRACK] = pitivi_drawing_getpixmap (GTK_WIDGET (self), bg_audio_xpm );
  self->bgs[PITIVI_TRANSITION_TRACK] = pitivi_drawing_getpixmap (GTK_WIDGET (self), bg_trans_xpm );
  self->bgs[PITIVI_EFFECTS_TRACK] = pitivi_drawing_getpixmap (GTK_WIDGET (self), bg_effects_xpm );
  self->bgs[PITIVI_LAST_TRACK] = pitivi_drawing_getpixmap (GTK_WIDGET (self), bg_xpm );
 
  /* Key events */
  g_signal_connect (GTK_WIDGET (self), "key_release_event",
		    G_CALLBACK (pitivi_timelinewindow_callb_key_press), NULL);
  
  self->nb_added[0] = 0;
}

static void
pitivi_timelinewindow_dispose (GObject *object)
{
  PitiviTimelineWindow	*self = PITIVI_TIMELINEWINDOW(object);

  /* If dispose did already run, return. */
  if (self->private->dispose_has_run)
    return;
  
  /* Make sure dispose does not run twice. */
  self->private->dispose_has_run = TRUE;	

  /* 
   * In dispose, you are supposed to free all types referenced from this 
   * object which might themselves hold a reference to self. Generally, 
   * the most simple solution is to unref all members on which you own a 
   * reference. 
   */
  G_OBJECT_CLASS (parent_class)->dispose (object);
}

static void
pitivi_timelinewindow_finalize (GObject *object)
{
  PitiviTimelineWindow	*self = PITIVI_TIMELINEWINDOW(object);

  /* 
   * Here, complete object destruction. 
   * You might not need to do much... 
   */

  g_free (self->private);
  G_OBJECT_CLASS (parent_class)->finalize (object);
}

static void
pitivi_timelinewindow_set_property (GObject * object,
			      guint property_id,
			      const GValue * value, GParamSpec * pspec)
{
  PitiviTimelineWindow *self = (PitiviTimelineWindow *) object;

  switch (property_id)
    {
    case PROP_VIEWER_WINDOW:
      self->private->viewer = g_value_get_pointer (value);
      break;
    default:
      g_assert (FALSE);
      break;
    }
}

static void
pitivi_timelinewindow_get_property (GObject * object,
				    guint property_id,
				    GValue * value, GParamSpec * pspec)
{
/*   PitiviTimelineWindow *self = (PitiviTimelineWindow *) object; */

  switch (property_id)
    {
    case PROP_VIEWER_WINDOW:
      break;
    default:
      g_assert (FALSE);
      break;
    }
}

/*
 **********************************************************
 * Callbacks Events / Signals				  *
 * From SourceListWindow / EffectsWindow	          *
 **********************************************************
*/

void
send_signal_to_childs (PitiviTimelineWindow *self, const gchar *signame, gpointer data)
{
  send_signal_to_childs_direct ( self->private->layout_container , signame, data);
  send_signal_to_childs_direct ( self->private->info_container , signame, data);
}

static void
pitivi_timelinewindow_deselect (PitiviTimelineWindow *self)
{
  send_signal_to_childs (self, "deselect", NULL);
}

static void
pitivi_timelinewindow_selected_source (PitiviTimelineWindow *self, gpointer data)
{
  GtkWidget	*receiver;

  receiver = ((GtkWidget *)pitivi_mainapp_get_effectswin ( self->private->mainapp ));
  if ( receiver )
    g_signal_emit_by_name (GTK_OBJECT (receiver), "selected-source", data);
}

static void
pitivi_timelinewindow_dblclick (PitiviTimelineWindow *self, gpointer data)
{
  PitiviTimelineCellRenderer *cell;
  guint		type;
  GList		*childlist;
  
  childlist = gtk_container_get_children (GTK_CONTAINER (self->private->layout_container));
  for (childlist = g_list_last ( childlist ); childlist; childlist = childlist->prev)
    if (GTK_IS_LAYOUT (childlist->data))
      {
	cell = childlist->data;
	type = pitivi_check_media_type (data);
	if ((cell->track_type == type) || 
	     ((cell->track_type == PITIVI_VIDEO_TRACK) 
	      && type == PITIVI_VIDEO_AUDIO_TRACK))
	  {
	    g_signal_emit_by_name (GTK_OBJECT (childlist->data), 
				   "double-click-source", 
				   data);
	    break;
	  }
      }
  g_list_free ( childlist );
}

static void
pitivi_timelinewindow_delete_sf (PitiviTimelineWindow *self, gpointer data)
{
  send_signal_to_childs (self, "delete-source", data);
}

static void
pitivi_timelinewindow_drag_source_begin (PitiviTimelineWindow *self, gpointer data)
{
  send_signal_to_childs (self, "drag-source-begin", data);
}

static void
pitivi_timelinewindow_drag_source_end (PitiviTimelineWindow *self, gpointer data)
{
  send_signal_to_childs (self, "drag-source-end", data);
}

static void
pitivi_timelinewindow_copy (PitiviTimelineWindow *self, gpointer data)
{
  self->copy = GTK_WIDGET (data);
}

static void
pitivi_timelinewindow_class_init (gpointer g_class, gpointer g_class_data)
{
  GObjectClass *gobject_class = G_OBJECT_CLASS (g_class);
  /*   GtkWidgetClass *gtkwidget_class = GTK_WIDGET_CLASS (g_class); */
  PitiviTimelineWindowClass *klass = PITIVI_TIMELINEWINDOW_CLASS (g_class);
  
  parent_class = g_type_class_peek_parent (g_class);
    
  gobject_class->constructor = pitivi_timelinewindow_constructor;
  gobject_class->dispose = pitivi_timelinewindow_dispose;
  gobject_class->finalize = pitivi_timelinewindow_finalize;

  gobject_class->set_property = pitivi_timelinewindow_set_property;
  gobject_class->get_property = pitivi_timelinewindow_get_property;

  g_object_class_install_property (G_OBJECT_CLASS (g_class), PROP_VIEWER_WINDOW,
				   g_param_spec_pointer ("viewer-window", "viewer-window", "viewer-window",
							 G_PARAM_WRITABLE));
  /* Signals */
  
  signals[ACTIVATE_SIGNAL] = g_signal_new ("activate",
					   G_TYPE_FROM_CLASS (g_class),
					   G_SIGNAL_RUN_FIRST | G_SIGNAL_ACTION,
					   G_STRUCT_OFFSET (PitiviTimelineWindowClass, activate),
					   NULL, 
					   NULL,                
					   g_cclosure_marshal_VOID__VOID,
					   G_TYPE_NONE, 0);
  
  signals[DEACTIVATE_SIGNAL] = g_signal_new ("deactivate",
					     G_TYPE_FROM_CLASS (g_class),
					     G_SIGNAL_RUN_FIRST | G_SIGNAL_ACTION,
					     G_STRUCT_OFFSET (PitiviTimelineWindowClass, deactivate),
					     NULL, 
					     NULL,                
					     g_cclosure_marshal_VOID__VOID,
					     G_TYPE_NONE, 0);
  
  signals[DESELECT_SIGNAL] = g_signal_new ("deselect",
					   G_TYPE_FROM_CLASS (g_class),
					   G_SIGNAL_RUN_FIRST | G_SIGNAL_ACTION,
					   G_STRUCT_OFFSET (PitiviTimelineWindowClass, deselect),
					   NULL, 
					   NULL,                
					   g_cclosure_marshal_VOID__VOID,
					   G_TYPE_NONE, 0);
  
  signals[SELECT_SOURCE_SIGNAL] = g_signal_new ("selected-source",
						G_TYPE_FROM_CLASS (g_class),
						G_SIGNAL_RUN_FIRST | G_SIGNAL_ACTION,
						G_STRUCT_OFFSET (PitiviTimelineWindowClass, selected_source),
						NULL, 
						NULL,                
						g_cclosure_marshal_VOID__POINTER,
						G_TYPE_NONE, 1, G_TYPE_POINTER);
  
  signals[COPY_SIGNAL] = g_signal_new ("copy-source",
				       G_TYPE_FROM_CLASS (g_class),
				       G_SIGNAL_RUN_FIRST | G_SIGNAL_ACTION,
				       G_STRUCT_OFFSET (PitiviTimelineWindowClass, copy),
				       NULL,
				       NULL,       
				       g_cclosure_marshal_VOID__POINTER,
				       G_TYPE_NONE, 1, G_TYPE_POINTER);
  
  signals[DELETE_SIGNAL] = g_signal_new ("delete-source",
					 G_TYPE_FROM_CLASS (g_class),
					 G_SIGNAL_RUN_FIRST | G_SIGNAL_ACTION,
					 G_STRUCT_OFFSET (PitiviTimelineWindowClass, delete),
					 NULL,
					 NULL,       
					 g_cclosure_marshal_VOID__POINTER,
					 G_TYPE_NONE, 1, G_TYPE_POINTER);
  
  signals[DRAG_SOURCE_BEGIN_SIGNAL] = g_signal_new ("drag-source-begin",
						    G_TYPE_FROM_CLASS (g_class),
						    G_SIGNAL_RUN_FIRST | G_SIGNAL_ACTION,
						    G_STRUCT_OFFSET (PitiviTimelineWindowClass, drag_source_begin),
						    NULL,
						    NULL,       
						    g_cclosure_marshal_VOID__POINTER,
						    G_TYPE_NONE, 1, G_TYPE_POINTER);
  
  signals[DRAG_SOURCE_END_SIGNAL] = g_signal_new ("drag-source-end",
						    G_TYPE_FROM_CLASS (g_class),
						    G_SIGNAL_RUN_FIRST | G_SIGNAL_ACTION,
						    G_STRUCT_OFFSET (PitiviTimelineWindowClass, drag_source_end),
						    NULL,
						    NULL,       
						    g_cclosure_marshal_VOID__POINTER,
						    G_TYPE_NONE, 1, G_TYPE_POINTER);
  
  signals[DBK_SOURCE_SIGNAL] = g_signal_new ("double-click-source",
					     G_TYPE_FROM_CLASS (g_class),
					     G_SIGNAL_RUN_FIRST | G_SIGNAL_ACTION,
					     G_STRUCT_OFFSET (PitiviTimelineWindowClass, dbk_source),
					     NULL,
					     NULL,       
					     g_cclosure_marshal_VOID__POINTER,
					     G_TYPE_NONE, 1, G_TYPE_POINTER);
  
  signals[ZOOM_CHANGED_SIGNAL] = g_signal_new ("zoom-changed",
					       G_TYPE_FROM_CLASS (g_class),
					       G_SIGNAL_RUN_FIRST | G_SIGNAL_ACTION,
					       G_STRUCT_OFFSET (PitiviTimelineWindowClass, zoom_changed),
					       NULL, 
					       NULL,                
					       g_cclosure_marshal_VOID__VOID,
					       G_TYPE_NONE, 0);

    g_signal_new ("associate-effect-to-media",
		  G_TYPE_FROM_CLASS (g_class),
		  G_SIGNAL_RUN_FIRST | G_SIGNAL_ACTION,
		  G_STRUCT_OFFSET (PitiviTimelineWindowClass, associate_effect),
		  NULL, 
		  NULL,                
		  g_cclosure_marshal_VOID__POINTER,
		  G_TYPE_NONE, 1, G_TYPE_POINTER);
    
    klass->activate = pitivi_timelinewindow_activate;
    klass->deactivate = pitivi_timelinewindow_deactivate;
    klass->deselect = pitivi_timelinewindow_deselect;
    klass->delete = pitivi_timelinewindow_delete_sf;
    klass->drag_source_begin = pitivi_timelinewindow_drag_source_begin;
    klass->drag_source_end = pitivi_timelinewindow_drag_source_end;
    klass->dbk_source = pitivi_timelinewindow_dblclick;
    klass->selected_source = pitivi_timelinewindow_selected_source;
    klass->zoom_changed = pitivi_timelinewindow_zoom_changed;
    klass->copy = pitivi_timelinewindow_copy;
}

GType
pitivi_timelinewindow_get_type (void)
{
  static GType type = 0;
 
  if (type == 0)
    {
      static const GTypeInfo info = {
	sizeof (PitiviTimelineWindowClass),
	NULL,					/* base_init */
	NULL,					/* base_finalize */
	pitivi_timelinewindow_class_init,	/* class_init */
	NULL,					/* class_finalize */
	NULL,					/* class_data */
	sizeof (PitiviTimelineWindow),
	0,					/* n_preallocs */
	pitivi_timelinewindow_instance_init	/* instance_init */
      };
      type = g_type_register_static (PITIVI_PROJECTWINDOWS_TYPE,
				     "PitiviTimelineWindowType", &info, 0);
    }
  return type;
}


/*
 **********************************************************
 * Callbacks Menu File / Signals			  *
 *							  *
 **********************************************************
*/
 
/* Menu File */

void
pitivi_callb_menufile_new ( GtkAction *action, PitiviTimelineWindow *self )
{
  PitiviNewProjectWindow	*win_new_project;
  PitiviMainApp			*mainapp = ((PitiviWindows *) self)->mainapp;
  GtkWidget			*dialog_box;
  GtkWidget			*dialog_tmp;			
  gint				dialog_return;

  if (mainapp->project)
    {
      dialog_box = gtk_message_dialog_new (GTK_WINDOW(self),
					   GTK_DIALOG_DESTROY_WITH_PARENT,
					   GTK_MESSAGE_WARNING,
					   GTK_BUTTONS_YES_NO,
					   "Save, and start a new project");
      dialog_return = gtk_dialog_run (GTK_DIALOG (dialog_box));
      switch (dialog_return)
	{
	case GTK_RESPONSE_YES:
	  dialog_tmp = gtk_message_dialog_new (GTK_WINDOW(self),
				  GTK_DIALOG_DESTROY_WITH_PARENT,
				  GTK_MESSAGE_WARNING,
				  GTK_BUTTONS_OK,
				  "Function under development, sorry...");
	  if (gtk_dialog_run (GTK_DIALOG (dialog_tmp)) == GTK_RESPONSE_OK)
	    gtk_widget_destroy (dialog_tmp);
	  break;
	default:
	  break;
	}
      gtk_widget_destroy (dialog_box);
    }
  else
    {
      /* New Project window */
      win_new_project = pitivi_newprojectwindow_new( mainapp );
      gtk_widget_show_all ( GTK_WIDGET (win_new_project) );
      pitivi_npw_select_first_setting(win_new_project);
    }
}

void
pitivi_callb_menufile_open ( GtkAction *action, PitiviTimelineWindow *self )
{
  PitiviMainApp	*mainapp = ((PitiviWindows *) self)->mainapp;
  PitiviProject	*project;
  GtkWidget	*dialog;
  char		*utf8, *filename = NULL;
  
  dialog = gtk_file_chooser_dialog_new("Open a PiTiVi project",
				       GTK_WINDOW (self), GTK_FILE_CHOOSER_ACTION_OPEN,
				       GTK_STOCK_CANCEL, GTK_RESPONSE_CANCEL,
				       GTK_STOCK_OPEN, GTK_RESPONSE_ACCEPT,
				       NULL);
  if (gtk_dialog_run (GTK_DIALOG (dialog)) == GTK_RESPONSE_ACCEPT)
    filename = gtk_file_chooser_get_filename (GTK_FILE_CHOOSER (dialog));
  gtk_widget_destroy ( dialog );
  
  if (!filename) {
    PITIVI_WARNING("No file selected to open...");
    return;
  }
  
  project = pitivi_project_new_from_file (filename);
  if (!project)
    {
      g_free (filename);
      return;
    }
  
  utf8 = strrchr (filename, '/'); utf8++;
  utf8 = g_locale_to_utf8 (utf8, -1, NULL, NULL, NULL);
  dialog = gtk_message_dialog_new (GTK_WINDOW (self),
				   GTK_DIALOG_MODAL,
				   GTK_MESSAGE_INFO,
				   GTK_BUTTONS_NONE,
				   "\nPlease Wait loading Project ... \nProject : %s\n",
				   utf8 );
  gtk_widget_show ( dialog );
  if ((project != NULL) && (pitivi_mainapp_add_project( mainapp, project )))
    pitivi_mainapp_create_wintools( mainapp , project );
  if (dialog != NULL && GTK_IS_DIALOG (dialog))
    gtk_widget_destroy ( dialog );
  g_free (filename);
}

void
pitivi_callb_menufile_sourcelistwindow_toggle ( GtkAction *action, PitiviTimelineWindow *self)
{
  PitiviMainApp	*mainapp = ((PitiviWindows *) self)->mainapp;
  
  pitivi_mainapp_activate_sourcelistwindow(mainapp,
					   gtk_toggle_action_get_active(GTK_TOGGLE_ACTION(action)));
}

void
pitivi_callb_menufile_effectswindow_toggle ( GtkAction *action, PitiviTimelineWindow *self)
{
  PitiviMainApp	*mainapp = ((PitiviWindows *) self)->mainapp;
  
  pitivi_mainapp_activate_effectswindow(mainapp,
					gtk_toggle_action_get_active(GTK_TOGGLE_ACTION(action)));
}

void
pitivi_callb_menufile_viewerwindow_toggle ( GtkAction *action, PitiviTimelineWindow *self)
{
  PitiviMainApp	*mainapp = ((PitiviWindows *) self)->mainapp;
  
  pitivi_mainapp_activate_viewerwindow(mainapp,
				       gtk_toggle_action_get_active(GTK_TOGGLE_ACTION(action)));
}

void
pitivi_callb_menufile_settings ( GtkAction *action, PitiviTimelineWindow *self )
{
  PitiviMainApp *mainapp = ((PitiviWindows *) self)->mainapp;
    
  /* Global Settings */

  if (!GTK_IS_WIDGET (self->private->WinSettings)) {
    self->private->WinSettings = pitivi_settingswindow_new (mainapp);
  }
  return ;
}

void
pitivi_callb_menufile_saveas ( GtkAction *action, PitiviTimelineWindow *self)
{
  GtkWidget			*dialog_box;
  PitiviProject	*project = ((PitiviProjectWindows *) self)->project;
  GtkWidget	*dialog;
  char		*filename = NULL;
  
  if (!project)
    {
      dialog_box = gtk_message_dialog_new (GTK_WINDOW(self),
					   GTK_DIALOG_DESTROY_WITH_PARENT,
					   GTK_MESSAGE_WARNING,
					   GTK_BUTTONS_OK,
					   "You have to create a new project before saving ...");
      if (gtk_dialog_run (GTK_DIALOG (dialog_box)) == GTK_RESPONSE_OK)
	gtk_widget_destroy (dialog_box);
    }
  else
    {
      /* Get the filename */
      dialog = gtk_file_chooser_dialog_new("Choose PiTiVi project file",
					   GTK_WINDOW (self), GTK_FILE_CHOOSER_ACTION_SAVE,
					   GTK_STOCK_CANCEL, GTK_RESPONSE_CANCEL,
					   GTK_STOCK_SAVE, GTK_RESPONSE_ACCEPT,
					   NULL);
      if (gtk_dialog_run (GTK_DIALOG (dialog)) == GTK_RESPONSE_ACCEPT)
	filename = gtk_file_chooser_get_filename (GTK_FILE_CHOOSER (dialog));

      gtk_widget_destroy ( dialog );

      if (filename != NULL) {
	project->filename = g_strdup(filename);
	pitivi_project_save_to_file(project, project->filename);
	g_free(filename);
      }
    }
}

void
pitivi_callb_menufile_save ( GtkAction *action, PitiviTimelineWindow *self )
{
  GtkWidget			*dialog_box;
  PitiviProject	*project = ((PitiviProjectWindows *) self)->project;

  if (!project)
    {
      dialog_box = gtk_message_dialog_new (GTK_WINDOW(self),
					   GTK_DIALOG_DESTROY_WITH_PARENT,
					   GTK_MESSAGE_WARNING,
					   GTK_BUTTONS_OK,
					   "You have to create a new project before saving ...");
      if (gtk_dialog_run (GTK_DIALOG (dialog_box)) == GTK_RESPONSE_OK)
	gtk_widget_destroy (dialog_box);
    }
  else
    {
      if (project->filename == NULL)
	pitivi_callb_menufile_saveas(action, self);
      else
	pitivi_project_save_to_file(project, project->filename);
    }
}

void 
pitivi_quit_application (PitiviTimelineWindow *self)
{
  GtkWidget *dialog;
  
  dialog = gtk_message_dialog_new (GTK_WINDOW(self),
				   GTK_DIALOG_DESTROY_WITH_PARENT,
				   GTK_MESSAGE_WARNING,
				   GTK_BUTTONS_YES_NO,
				   "Do you really want to quit Pitivi ? \n");
  
  if (gtk_dialog_run (GTK_DIALOG (dialog)) == GTK_RESPONSE_YES)
    pitivi_mainapp_destroy (GTK_WIDGET(self), NULL);
  gtk_widget_destroy (dialog);
}

gboolean
pitivi_callb_window_close (GtkWidget *win, GdkEvent *event, PitiviTimelineWindow *self)
{
  pitivi_quit_application  ( self );
  return TRUE;
}

void
pitivi_callb_menufile_exit (GtkAction *action, PitiviTimelineWindow *self )
{
  pitivi_quit_application  ( self );
}

void
pitivi_callb_controller_record (PitiviController *controller, PitiviTimelineWindow *self)
{
  PitiviProject	*project = ((PitiviProjectWindows *) self)->project;
  GtkWindow	*win;

  win = pitivi_encodewindow_new (project);
  gtk_widget_show_all (GTK_WIDGET (win));
}

/*
 * MainApp Stuff
 *
 */

/**
 * pitivi_timelinewindow_get_mainApp:
 * @PitiviTimelineWindow: The object referencing the timeline
 *
 * Get the object MainApp with all references  
 *
 * Returns: An element PitiviMainApp 
 */

PitiviMainApp  *
pitivi_timelinewindow_get_mainApp (PitiviTimelineWindow	*timelinewindow)
{
  return ( timelinewindow->private->mainapp );
}

/**
 * pitivi_timelinewindow_get_container:
 * @PitiviTimelineWindow: The object referencing the timeline
 *
 * Get the container
 *
 * Returns: A Widget with the container
 */


GtkWidget *pitivi_timelinewindow_get_container (PitiviTimelineWindow *self) {
  if (!self)
    return NULL;
  return self->private->layout_container;
}

/* Utils */

/*
 * Activate / Deactivate tracks
 *
 */

/**
 * pitivi_timelinewindow_configure_event: 
 * @GtkWidget: the widget containing the Hpaned
 * 
 * Set the position of the Hpaned
 *
 * Returns: A flag gboolean setted to FALSE
 */

gboolean
pitivi_timelinewindow_configure_event (GtkWidget *widget) 
{
  PitiviTimelineWindow *self;

  self = (PitiviTimelineWindow *) widget;
  gtk_paned_set_position (GTK_PANED(self->private->hpaned), (LEFT_PANED_SIZE));
  return FALSE;
}

/**
 * pitivi_timelinewindow_deactivate: 
 * @PitiviTimelineWindow: The object referencing the timeline
 *
 * Deactivates the timeline
 *
 */

void
pitivi_timelinewindow_deactivate ( PitiviTimelineWindow *self )
{
  gtk_widget_set_sensitive (GTK_WIDGET(self->private->toolcontainer), FALSE);
  gtk_widget_set_sensitive (GTK_WIDGET(self->private->hpaned), FALSE);

  /* Loading X Cursor */
  
  load_cursor (GDK_WINDOW (GTK_WIDGET (self)->window), self->toolbox->pitivi_cursor, 
	       PITIVI_CURSOR_NOALLOW);

  /* Deactivate Windows Menu */
  gtk_action_group_set_sensitive (self->actions_group[EA_WINDOWMENU_FILE], FALSE);
  pitivi_timelinewindow_file_set_action (self, "FileSave", FALSE);
  pitivi_timelinewindow_file_set_action (self, "FileSaveAs", FALSE);
}

void
pitivi_timelinewindow_associate_effect (GtkWidget *widget, gpointer data)
{
  PitiviTimelineWindow *self = (PitiviTimelineWindow *) widget;
  PitiviTimelineCellRenderer *cell;
  GtkWidget	*media;
  GList		*childlist;
  
  childlist = gtk_container_get_children (GTK_CONTAINER (self->private->layout_container));
  for (childlist = g_list_last ( childlist ); childlist; childlist = childlist->prev)
    if (GTK_IS_LAYOUT (childlist->data))
      {
	cell = childlist->data;
	if ((media = pitivi_timelinecellrenderer_media_selected_ontrack (cell)))
	  {
	    g_signal_emit_by_name (media, "associate-effect-to-media", data);
	    break;
	  }
      }
  g_list_free ( childlist );
}

/**
 * pitivi_timelinewindow_activate: 
 * @PitiviTimelineWindow: The object referencing the timeline
 *
 * Activates the timeline
 *
 */

void
pitivi_timelinewindow_activate (PitiviTimelineWindow *self)
{ 
  GList *childlist; 
  PitiviProject *proj;
  gdouble videorate;
  GList *childwidget;
  /* Loading Select Cursor */
  
  load_cursor (GDK_WINDOW (GTK_WIDGET (self)->window), self->toolbox->pitivi_cursor, PITIVI_CURSOR_SELECT);
  
  /* Activating ruler */
  
  proj = PITIVI_WINDOWS(self)->mainapp->project;
  videorate = pitivi_projectsettings_get_videorate(proj->settings);
  g_object_set (self->hruler, "ruler-videorate", videorate, NULL);
  
  /* Activate Windows Menu */
  gtk_action_group_set_sensitive (self->actions_group[EA_WINDOWMENU_FILE], TRUE);
  pitivi_timelinewindow_file_set_action (self, "FileSave", TRUE);
  pitivi_timelinewindow_file_set_action (self, "FileSaveAs", TRUE);

  /* Activate childs */

  childwidget = gtk_container_get_children (GTK_CONTAINER (self->private->layout_container));
  for (childlist = childwidget; childlist; childlist = childlist->next )
    {
      if (GTK_IS_LAYOUT (childlist->data))
	g_signal_emit_by_name (GTK_OBJECT (childlist->data), "activate");
    }
  gtk_widget_set_sensitive (GTK_WIDGET(self->private->toolcontainer), TRUE);
  gtk_widget_set_sensitive (GTK_WIDGET(self->private->hpaned), TRUE);
  
  g_signal_connect (self, "associate-effect-to-media", G_CALLBACK (pitivi_timelinewindow_associate_effect), NULL);

    
  /* Viewer control  */
  
  self->private->viewer = ((GtkWidget *)pitivi_mainapp_get_viewerwin ( ((PitiviWindows *)self)->mainapp ));
  connect2viewer (self->private->controller, self->private->viewer);
}

/**
 * pitivi_timelinewindow_zoom_changed: 
 * @PitiviTimelineWindow: The object referencing the timeline
 *
 * Changes the zoom
 *
 */

void
pitivi_timelinewindow_zoom_changed (PitiviTimelineWindow *self)
{
  GList	*list, *tmp;

  // update zoom combobox
  switch (self->zoom) {
  case 1:
    gtk_combo_box_set_active(self->private->scalecombobox, 0);
    break;
  case 2:
    gtk_combo_box_set_active(self->private->scalecombobox, 1);
    break;
  case 4:
    gtk_combo_box_set_active(self->private->scalecombobox, 2);
    break;
  case 8:
    gtk_combo_box_set_active(self->private->scalecombobox, 3);
    break;
  case 16:
    gtk_combo_box_set_active(self->private->scalecombobox, 4);
    break;
  }
  switch (self->unit) {
  case PITIVI_SECONDS:
    gtk_combo_box_set_active(self->private->unitcombobox, 0);
    break;
  case PITIVI_FRAMES:
    gtk_combo_box_set_active(self->private->unitcombobox, 1);
    break;
  }
  list = gtk_container_get_children (GTK_CONTAINER (self->private->layout_container));
  for (tmp = list; tmp; tmp = tmp->next)
    if (GTK_IS_LAYOUT (tmp->data))
      g_signal_emit_by_name (GTK_OBJECT (tmp->data), "zoom-changed");
}

/**
 * pitivi_timelinewindow_update_time:
 * @self: The #PitiviTimelineWindow
 * @ntime: The new time
 *
 */


void
pitivi_timelinewindow_update_time (PitiviTimelineWindow *self, gint64 ntime)
{
  gchar	*tmp;
  gint64 pos;

  tmp = g_strdup_printf("%lld:%02lld:%03lld", GST_M_S_M(ntime));
  gtk_label_set_text (GTK_LABEL (self->private->timer),tmp);
  pos = ((gint64) ntime/GST_SECOND);
  if (!pos)
    {
      PITIVI_RULER (self->hruler)->time_pix = 0;
      g_signal_emit_by_name (self->hruler, "moving-play", &pos, NULL);
    }
  if (pos >  PITIVI_RULER (self->hruler)->time_pix)
    {
      PITIVI_RULER (self->hruler)->time_pix = pos;
      g_signal_emit_by_name (self->hruler, "moving-play", &pos, NULL);
    }
}

/*
 **********************************************************
 * Key events						  *
 * From keyboard				          *
 **********************************************************
*/

gboolean
pitivi_timelinewindow_callb_key_press (PitiviTimelineWindow *self, GdkEventKey* event, gpointer data) 
{
  switch(event->keyval) 
    {
    case GDK_Return:
      send_signal_to_childs (self, "rendering", NULL);
      break;
    case GDK_Delete:
      send_signal_to_childs (self, "key-delete-source", NULL);
      break;
    case GDK_Pause:
      g_signal_emit_by_name (self->private->controller, "pause", self);
      break;
    }
  return TRUE;
}
