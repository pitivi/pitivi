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

#include "pitivi-timelinewindow.h"
#include "pitivi-checkbox.h"
#include "pitivi-menu.h"
#include "pitivi-stockicons.h"
#include "pitivi-timelinecellrenderer.h"

static	GdkPixbuf *window_icon = NULL;
static  PitiviWindowsClass *parent_class = NULL;

typedef struct _PitiviMediaInfo
{
  GtkWidget	 *hbox;
  PitiviCheckBox *boxes[3];
  GtkLabel	 *label;
  int		 number;
} PitiviMediaInfo;

struct _PitiviTimelineWindowPrivate
{
  /* Instance private members */
  
  gboolean	dispose_has_run;
  PitiviMenu	*ui_menus;
  GtkWidget	*menu_dock;
  GtkWidget	*main_vbox;
  
  GtkWidget	 *hpaned;
  
  /* StatusBar */

  GtkWidget	*dock_statusbar;
  GtkWidget	*statusbar_properties;
  GtkWidget	*statusbar_frame;
  GtkWidget	*statusbar_message;
  
  GdkWindow     *event_window;
  GdkCursor     *cursor;
  GList         *operations;  
};


/*
 * forward definitions
 */

enum {
  EA_DEFAULT_FILE,
  EA_RECENT_FILE,
  EA_LAST_ACTION
};

enum {
	LAST_SIGNAL
};

enum {
	DND_TYPE_TEXT
};

enum {
    PITIVI_CAT_LAYER_COLUMN = 0,
    PITIVI_LAYER_COLUMN,
    PITIVI_NB_COLUMN,
};

static  GtkActionGroup *actions_group[EA_LAST_ACTION];
static  guint signals[LAST_SIGNAL];


/*
 * Insert "added-value" functions here
 */


static void
statusbar_set_frames (GtkWidget *statusbar,
		      PitiviTimelineWindow *window,
		      gchar *msg)
{
  gchar *display;

  display = g_strdup_printf ("%s", msg);
  gtk_statusbar_pop (GTK_STATUSBAR (statusbar), 0);
  gtk_statusbar_push (GTK_STATUSBAR (statusbar), 0, display);
  g_free (display);
}


PitiviTimelineWindow *
pitivi_timelinewindow_new (PitiviMainApp *mainapp, PitiviProject *project)
{
  PitiviTimelineWindow		*timelinewindow;
  PitiviTimelineWindowPrivate	*priv;
  
  timelinewindow = (PitiviTimelineWindow *) g_object_new(PITIVI_TIMELINEWINDOW_TYPE, 
							 "mainapp", mainapp,
							 "project", project, NULL);
  g_assert(timelinewindow != NULL);
  return timelinewindow;
}

static GObject *
pitivi_timelinewindow_constructor (GType type,
			     guint n_construct_properties,
			     GObjectConstructParam * construct_properties)
{
  GObject *obj;
  {
    /* Invoke parent constructor. */
    
    PitiviTimelineWindowClass *klass;
    GObjectClass *parent_class;
    klass = PITIVI_TIMELINEWINDOW_CLASS (g_type_class_peek (PITIVI_TIMELINEWINDOW_TYPE));
    parent_class = G_OBJECT_CLASS (g_type_class_peek_parent (klass));
    obj = parent_class->constructor (type, n_construct_properties,
				     construct_properties);
  }

  /* do stuff. */

  return obj;
}


 
static void
pitivi_callb_menufile_exit (GtkAction *action, PitiviTimelineWindow *self )
{
  gtk_widget_destroy (GTK_WIDGET(self));
}


static void
pitivi_callb_menufile_new ( GtkAction *action, PitiviTimelineWindow *self )
{  
  
}

static void
pitivi_callb_menufile_open ( GtkAction *action, PitiviTimelineWindow *self )
{

}

static void
pitivi_callb_menufile_save ( GtkAction *action, PitiviTimelineWindow *self )
{
  
}


static void
pitivi_callb_menufile_saveas ( GtkAction *action, PitiviTimelineWindow *self)
{
  
}


static GtkActionEntry file_entries[] = {
  { "FileMenu", NULL, "_File" },
  { "FileNew", PITIVI_STOCK_NEW_PROJECT, "Ne_w", "<control>N", "New File", G_CALLBACK (pitivi_callb_menufile_new) },
  { "FileOpen", GTK_STOCK_OPEN, "_Open", "<control>O", "Open a file",  G_CALLBACK (pitivi_callb_menufile_open) },
  { "FileSave", GTK_STOCK_SAVE, "_Save", "<control>S", "Save a file", G_CALLBACK (pitivi_callb_menufile_save) },
  { "FileSaveAs", GTK_STOCK_SAVE_AS, "Save _As", "<control>A", "Save a file", G_CALLBACK (pitivi_callb_menufile_saveas) },
  { "FileExit", GTK_STOCK_QUIT, "_Close", "<control>Q", "Close Project", G_CALLBACK (pitivi_callb_menufile_exit) },
};

static GtkActionEntry recent_entry[]= {
  { "FileRecent", GTK_STOCK_OPEN, "_Open Recent File", "<control>R", "Open a recent file",  G_CALLBACK (pitivi_callb_menufile_open) },
};

static void
pitivi_timelinewindow_instance_init (GTypeInstance * instance, gpointer g_class)
{
  PitiviMenu		*menumgr;
  GtkWidget		*hbox[6];
  GtkWidget		*vbox_left[6];
  GtkWidget		*vbox_right[6];
  GtkWidget		*separators[6];
  GtkWidget		*separators_right[6];
  GtkWidget		*sw;
  int			count;
  int			max;
 
  max = 6;
  PitiviTimelineWindow *self = (PitiviTimelineWindow *) instance;
  self->private = g_new0(PitiviTimelineWindowPrivate, 1);
  
  /* initialize all public and private members to reasonable default values. */ 
  
  self->private->dispose_has_run = FALSE;
  
  /* If you need specific consruction properties to complete initialization, 
   * delay initialization completion until the property is set. 
   * statusbar_set_frames (self->private->statusbar_frame, self, (guint64) 0);
   */  
  
  /* Main Window : Setting default Size */
  
  gtk_window_set_title (GTK_WINDOW (self), PITIVI_TIMELINE_DF_TITLE);
  gtk_window_set_default_size (GTK_WINDOW (self), PITIVI_TIMELINE_DF_WIN_WIDTH\
			       , PITIVI_TIMELINE_DF_WIN_HEIGHT); 
  if (window_icon == NULL) {
    char *filename;
    
    filename = g_strdup(PITIVI_TIMELINE_LOGO);
    window_icon = gdk_pixbuf_new_from_file (filename, NULL);
    g_free (filename);
  }
  
  gtk_window_set_icon (GTK_WINDOW (self), window_icon);
  
  self->private->main_vbox = gtk_vbox_new (FALSE, 0);
  gtk_widget_show (self->private->main_vbox);
  gtk_container_add (GTK_CONTAINER (self), self->private->main_vbox);

  /* Putting Menu to timeline */
  
  self->private->menu_dock = gtk_vbox_new (FALSE, 0);
  gtk_widget_show (self->private->menu_dock);
  gtk_box_pack_start (GTK_BOX (self->private->main_vbox), self->private->menu_dock,
		      FALSE, TRUE, 0);
  
  /* Managing actions groups */
  
  actions_group[EA_DEFAULT_FILE] = gtk_action_group_new ("MenuFile");
  gtk_action_group_add_actions (actions_group[EA_DEFAULT_FILE], file_entries\
				, G_N_ELEMENTS (file_entries), self);
  actions_group[EA_RECENT_FILE] = gtk_action_group_new ("MenuFileRecent");
  gtk_action_group_add_actions (actions_group[EA_DEFAULT_FILE], file_entries\
				, G_N_ELEMENTS (recent_entry), self);
  menumgr = pitivi_menu_new (GTK_WIDGET (self), PITIVI_MENU_TIMELINE_FILE);
  
  for (count = 0; count < EA_LAST_ACTION; count++)
    if (actions_group[count])
      gtk_ui_manager_insert_action_group (menumgr->public->ui, actions_group[count], 0);
  
  
  PITIVI_MENU_GET_CLASS(menumgr)->public->configure (menumgr);

  gtk_box_pack_start (GTK_BOX (self->private->menu_dock), menumgr->public->menu,
		      FALSE, TRUE, 0);
  
  
  /* Timeline View */
  
  self->private->hpaned = gtk_hpaned_new();
  GtkWidget *main_vbox_left = gtk_vbox_new (FALSE, 0);
  
  GtkWidget * pScrollbarRight = gtk_scrolled_window_new(NULL, NULL);
  gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW (pScrollbarRight),
				 GTK_POLICY_AUTOMATIC, GTK_POLICY_AUTOMATIC);
  
  GtkWidget * pScrollbarLeft = gtk_scrolled_window_new(NULL, NULL);
  gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW (pScrollbarLeft),
				 GTK_POLICY_AUTOMATIC, GTK_POLICY_AUTOMATIC);

  gtk_paned_set_position(GTK_PANED(self->private->hpaned), (GTK_WIDGET(self)->allocation.width/4));
  GtkWidget *main_vbox_right = gtk_vbox_new (FALSE, 0);
  
  for (count = 0; count < max; count++)
    {
      // Left View

      vbox_left[count] = gtk_vbox_new (FALSE, 0);
      gtk_widget_set_usize (vbox_left[count], 100, 50);
      hbox[count] = gtk_hbox_new (FALSE, 0);
      
      gtk_box_pack_start (GTK_BOX (vbox_left[count]), hbox[count], TRUE, TRUE, 0);
      GtkWidget *check = (GtkWidget *) pitivi_checkbox_new ( CHECK_X );
      gtk_box_pack_start (GTK_BOX (hbox[count]), check, FALSE, FALSE, 0);
      GtkWidget *check2 =  (GtkWidget *) pitivi_checkbox_new ( CHECK_ANCHOR );
      gtk_box_pack_start (GTK_BOX (hbox[count]), check2, FALSE, FALSE, 0);
      
      if (count < (max/2))
	gtk_box_pack_start (GTK_BOX (hbox[count]), gtk_label_new ("Video"), FALSE, FALSE, 0);
      else
	gtk_box_pack_start (GTK_BOX (hbox[count]), gtk_label_new ("Audio"), FALSE, FALSE, 0);
      separators[count] = gtk_hseparator_new ();
      gtk_box_pack_start (GTK_BOX (vbox_left[count]), separators[count], FALSE, FALSE, 0);
      gtk_box_pack_start (GTK_BOX (main_vbox_left), vbox_left[count], FALSE, FALSE, 0);
      
      //Right View
      
      vbox_right[count] = gtk_vbox_new (FALSE, 0);
      gtk_widget_set_usize (vbox_right[count], 100, 50);
      gtk_box_pack_start (GTK_BOX (main_vbox_right), vbox_right[count], TRUE, TRUE, 0);
      separators_right[count] = gtk_hseparator_new ();
      GtkWidget *cell = pitivi_timelinecellrenderer_new ();
      gtk_box_pack_start (GTK_BOX (vbox_right[count]), cell, TRUE, TRUE, 0);
      gtk_box_pack_start (GTK_BOX (vbox_right[count]), separators_right[count], FALSE, FALSE, 0);
    }
  
  gtk_paned_pack1 (GTK_PANED(self->private->hpaned), main_vbox_left, FALSE, FALSE);  
  gtk_paned_pack2 (GTK_PANED(self->private->hpaned), main_vbox_right, FALSE, FALSE);
  gtk_box_pack_start (GTK_BOX (self->private->main_vbox), self->private->hpaned, FALSE, FALSE, 0);
  
  /* Main Window : StatusBar */
  
  self->private->dock_statusbar = gtk_hbox_new (FALSE, 0);
  gtk_box_pack_end (GTK_BOX (self->private->main_vbox), self->private->dock_statusbar, FALSE, FALSE, 0);
  
  self->private->statusbar_properties = gtk_statusbar_new ();
  gtk_statusbar_set_has_resize_grip (GTK_STATUSBAR (self->private->statusbar_properties), FALSE);
  gtk_box_pack_start (GTK_BOX (self->private->dock_statusbar), self->private->statusbar_properties, TRUE, TRUE, 0);
  
  self->private->statusbar_frame = gtk_statusbar_new ();
  gtk_statusbar_set_has_resize_grip (GTK_STATUSBAR (self->private->statusbar_frame), FALSE);
  gtk_box_pack_start (GTK_BOX (self->private->dock_statusbar), self->private->statusbar_frame, TRUE, TRUE, 0);  
  
  self->private->statusbar_message = gtk_statusbar_new ();
  gtk_statusbar_set_has_resize_grip (GTK_STATUSBAR (self->private->statusbar_message), TRUE);
  gtk_box_pack_start (GTK_BOX (self->private->dock_statusbar), self->private->statusbar_message, TRUE, TRUE, 0);
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
      /*   case PITIVI_TIMELINEWINDOW_PROPERTY: { */
      /*     g_free (self->private->name); */
      /*     self->private->name = g_value_dup_string (value); */
      /*     g_print ("maman: %s\n",self->private->name); */
      /*   } */
      /*     break; */
    default:
      /* We don't have any other property... */
      g_assert (FALSE);
      break;
    }
}

static void
pitivi_timelinewindow_get_property (GObject * object,
			      guint property_id,
			      GValue * value, GParamSpec * pspec)
{
  PitiviTimelineWindow *self = (PitiviTimelineWindow *) object;

  switch (property_id)
    {
      /*  case PITIVI_TIMELINEWINDOW_PROPERTY: { */
      /*     g_value_set_string (value, self->private->name); */
      /*   } */
      /*     break; */
    default:
      /* We don't have any other property... */
      g_assert (FALSE);
      break;
    }
}

static void
pitivi_timelinewindow_class_init (gpointer g_class, gpointer g_class_data)
{
  GObjectClass *gobject_class = G_OBJECT_CLASS (g_class);
  PitiviTimelineWindowClass *klass = PITIVI_TIMELINEWINDOW_CLASS (g_class);

  parent_class = g_type_class_peek_parent (g_class);
    
  gobject_class->constructor = pitivi_timelinewindow_constructor;
  gobject_class->dispose = pitivi_timelinewindow_dispose;
  gobject_class->finalize = pitivi_timelinewindow_finalize;

  gobject_class->set_property = pitivi_timelinewindow_set_property;
  gobject_class->get_property = pitivi_timelinewindow_get_property;

  /* Install the properties in the class here ! */
  /*   pspec = g_param_spec_string ("maman-name", */
  /*                                "Maman construct prop", */
  /*                                "Set maman's name", */
  /*                                "no-name-set" /\* default value *\/, */
  /*                                G_PARAM_CONSTRUCT_ONLY | G_PARAM_READWRITE); */
  /*   g_object_class_install_property (gobject_class, */
  /*                                    MAMAN_BAR_CONSTRUCT_NAME, */
  /*                                    pspec); */


}

GType
pitivi_timelinewindow_get_type (void)
{
  static GType type = 0;
 
  if (type == 0)
    {
      static const GTypeInfo info = {
	sizeof (PitiviTimelineWindowClass),
	NULL,			/* base_init */
	NULL,			/* base_finalize */
	pitivi_timelinewindow_class_init,	/* class_init */
	NULL,			/* class_finalize */
	NULL,			/* class_data */
	sizeof (PitiviTimelineWindow),
	0,			/* n_preallocs */
	pitivi_timelinewindow_instance_init	/* instance_init */
      };
      type = g_type_register_static (PITIVI_PROJECTWINDOWS_TYPE,
				     "PitiviTimelineWindowType", &info, 0);
    }

  return type;
}
