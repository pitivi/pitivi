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

#include <gtk/gtk.h>
#include "pitivi.h"
#include "pitivi-menu.h"
#include "pitivi-timelinewindow.h"

struct _PitiviTimelineWindowPrivate
{
  /* instance private members */
  gboolean	dispose_has_run;
  GtkWidget	*main_vbox;
  GtkWidget	*menu_dock;
  PitiviMenu	*ui_menus;
  GtkWidget	*hscrollbar;
  GtkWidget	*hruler;
  GtkWidget	*vruler;
  GtkWidget	*forms;
  GList		*popups;
  
  /* StatusBar */

  GtkWidget	*dock_statusbar;
  GtkWidget	*statusbar_properties;
  GtkWidget	*statusbar_frame;
  GtkWidget	*statusbar_message;
    
  GNode	        *subs;
  GdkWindow     *event_window;
  GdkCursor     *cursor;
  PosDisplay	pos_display;
  guint	        gpi_type;
  GList*        operations;
  
};

/*
 * forward definitions
 */

enum {
	LAST_SIGNAL
};

enum {
	DND_TYPE_TEXT
};


static GtkTargetEntry drop_types[] = {
	{ "text/uri-list", 0, DND_TYPE_TEXT }
};


GtkWindowClass *parent_class = NULL;
static	GdkPixbuf *window_icon = NULL;
static  guint signals[LAST_SIGNAL];
static  int num_drop_types = sizeof (drop_types) / sizeof (drop_types[0]);


/*
 * Insert "added-value" functions here
 */


static void
statusbar_set_frames (GtkWidget *statusbar,
		      PitiviTimelineWindow *window,
		      guint64 frames)
{
	guint64 ms;
	char *display = NULL;

	switch (window->private->pos_display) {
	case AS_FRAMES:
	  display = g_strdup_printf ("%llu", frames);
	  break;
	case AS_TIME_LONG:
	  /*ms = gpi_timeconv_frames_to_ms (frames, PITIVI_DF_RATE);
	  display = gpi_timeconv_ms_to_time_string (ms);
	  */
	  display = g_strdup_printf ("%15c%s", ' ', display);
	  break;
	case AS_SECONDS:
	  /*ms = gpi_timeconv_frames_to_ms (frames, PITIVI_DF_RATE);
	  display = g_strdup_printf ("%llu", ms / 1000);
	  */
	  break;
	default:
	  return;
	}
	
	gtk_statusbar_pop (GTK_STATUSBAR (statusbar), 0);
	gtk_statusbar_push (GTK_STATUSBAR (statusbar), 0, display);
	g_free (display);
}

static void
pitivi_callb_drag_data_received (GObject *object,
		    GdkDragContext *context,
		    int x,
		    int y,
		    GtkSelectionData *selection,
		    guint info,
		    guint time,
		    gpointer data)
{
	PitiviTimelineWindow *window;
	char *tmp, *filename, **filenames;
	int i;

	window = PITIVI_TIMELINEWINDOW (object);

	switch (info) {
	case DND_TYPE_TEXT:
		tmp = g_strndup (selection->data, selection->length);
		filenames = g_strsplit (tmp, "\n", 0);
		g_free (tmp);

		for (i = 0; filenames[i] != NULL; i++) {
			filename = g_strstrip (filenames[i]);

			if (filename[0] == 0) {
				continue;
			}
			
			/* action to do */
			g_free (filename);
		}

		g_free (filenames);
		break;

	default:
		break;
	}
}


PitiviTimelineWindow *
pitivi_timelinewindow_new(void)
{
  PitiviTimelineWindow	*timelinewindow;
  PitiviTimelineWindowPrivate	*priv;
  GtkWidget			*sw;
  
  timelinewindow = (PitiviTimelineWindow *) g_object_new(PITIVI_TIMELINEWINDOW_TYPE, NULL);
  g_assert(timelinewindow != NULL);
  priv = timelinewindow->private;
  
  /* Main Window : Setting default Size */
  
  gtk_window_set_title (GTK_WINDOW (timelinewindow), PITIVI_TIMELINE_DF_TITLE);
  gtk_window_set_default_size (GTK_WINDOW (timelinewindow), PITIVI_TIMELINE_DF_WIN_WIDTH\
			       , PITIVI_TIMELINE_DF_WIN_HEIGHT); 
  if (window_icon == NULL) {
    char *filename;
    
    filename = g_strdup(PITIVI_TIMELINE_LOGO);
    window_icon = gdk_pixbuf_new_from_file (filename, NULL);
    g_free (filename);
  }
  gtk_window_set_icon (GTK_WINDOW (timelinewindow), window_icon);
  
  /* Main Window : Drag And Drop */
  
  gtk_drag_dest_set (GTK_WIDGET (timelinewindow), GTK_DEST_DEFAULT_ALL,
		     drop_types, num_drop_types, GDK_ACTION_COPY);
  g_signal_connect (G_OBJECT (timelinewindow), "drag_data_received",
	 	    G_CALLBACK (pitivi_callb_drag_data_received), NULL);
  
  
  /* Timeline */
  
  priv->forms = gtk_table_new (3, 2, FALSE);
  gtk_box_pack_start (GTK_BOX (priv->main_vbox), priv->forms, TRUE, TRUE, 0);
  
  priv->vruler = gtk_vruler_new ();
  gtk_ruler_set_metric (GTK_RULER (priv->vruler), GTK_PIXELS);
  gtk_ruler_set_range (GTK_RULER (priv->vruler), 0, 3, 0, 3);
  gtk_ruler_draw_pos (GTK_RULER (priv->vruler));
  gtk_table_attach (GTK_TABLE (priv->forms), priv->vruler,
		    0, 1, 1, 2,
		    GTK_FILL,
		    GTK_FILL | GTK_EXPAND,
		    0, 0);
  
  priv->hruler = gtk_hruler_new ();
  gtk_ruler_set_metric (GTK_RULER (priv->hruler), GTK_PIXELS);
  gtk_ruler_set_range (GTK_RULER (priv->hruler), 0, 3, 0, 3);
  gtk_ruler_draw_pos (GTK_RULER (priv->hruler));
  gtk_table_attach (GTK_TABLE (priv->forms), priv->hruler,
		    1, 2, 0, 1,
		    GTK_FILL | GTK_EXPAND,
		    GTK_FILL,
		    0, 0);
  
    
  /* Main Window : Scrollbar */
  
  priv->hscrollbar = gtk_hscrollbar_new (NULL);
  sw = gtk_scrolled_window_new (GTK_RANGE (priv->hscrollbar)->adjustment, NULL);
  gtk_scrolled_window_set_policy (GTK_SCROLLED_WINDOW (sw),
				  GTK_POLICY_NEVER,
				  GTK_POLICY_NEVER);
  
  gtk_widget_set_scroll_adjustments (GTK_WIDGET (priv->hruler),
				     GTK_RANGE (priv->hscrollbar)->adjustment,
				     GTK_RANGE (GTK_SCROLLED_WINDOW (sw)->vscrollbar)->adjustment);
  
  gtk_widget_show_all (priv->forms);
  
  /* Main Window : StatusBar */
  
  priv->dock_statusbar = gtk_hbox_new (FALSE, 0);
  gtk_box_pack_end (GTK_BOX (priv->main_vbox), priv->dock_statusbar, FALSE, FALSE, 0);
  gtk_widget_show ( priv->dock_statusbar );
    
  priv->statusbar_properties = gtk_statusbar_new ();
  gtk_statusbar_set_has_resize_grip (GTK_STATUSBAR (priv->statusbar_properties), FALSE);
  gtk_box_pack_start (GTK_BOX (priv->dock_statusbar), priv->statusbar_properties, TRUE, TRUE, 0);
  priv->statusbar_frame = gtk_statusbar_new ();
  priv->pos_display = AS_TIME_LONG;
  statusbar_set_frames (priv->statusbar_frame, timelinewindow, (guint64) 0);
  gtk_statusbar_set_has_resize_grip (GTK_STATUSBAR (priv->statusbar_frame), FALSE);
  gtk_box_pack_start (GTK_BOX (priv->dock_statusbar), priv->statusbar_frame, TRUE, TRUE, 0);  

  priv->statusbar_message = gtk_statusbar_new ();
  gtk_statusbar_set_has_resize_grip (GTK_STATUSBAR (priv->statusbar_message), FALSE);
  gtk_box_pack_start (GTK_BOX (priv->dock_statusbar), priv->statusbar_message, TRUE, TRUE, 0);
  
  gtk_widget_show_all (priv->main_vbox);
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
pitivi_timelinewindow_instance_init (GTypeInstance * instance, gpointer g_class)
{
  GdkRectangle area;
  PitiviTimelineWindow *self = (PitiviTimelineWindow *) instance;
  
  self->private = g_new0(PitiviTimelineWindowPrivate, 1);
  
  /* initialize all public and private members to reasonable default values. */ 
  
  self->private->dispose_has_run = FALSE;
    
  /* If you need specific consruction properties to complete initialization, 
   * delay initialization completion until the property is set. 
   */  
    
  self->private->main_vbox = gtk_vbox_new (FALSE, 0);
  gtk_widget_show (self->private->main_vbox);
  gtk_container_add (GTK_CONTAINER (self), self->private->main_vbox);
  
  self->private->menu_dock = gtk_vbox_new (FALSE, 0);
  gtk_widget_show (self->private->menu_dock);
  gtk_box_pack_start (GTK_BOX (self->private->main_vbox), self->private->menu_dock,
		      FALSE, TRUE, 0);
  self->private->ui_menus = pitivi_menu_new (GTK_WIDGET (self), PITIVI_MENU_MANAGER_FILE);
  gtk_widget_show (self->private->ui_menus->public->menu);
  gtk_box_pack_start (GTK_BOX (self->private->menu_dock), self->private->ui_menus->public->menu,
		      FALSE, TRUE, 0);
  /* gtk_box_pack_start (GTK_BOX (self->private->menu_dock), self->public->ui_menus->toolbar,
		      FALSE, TRUE, 0);
  */
  self->private->operations = g_list_alloc ();
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
      type = g_type_register_static (GTK_TYPE_WINDOW,
				     "PitiviTimelineWindowType", &info, 0);
    }

  return type;
}
