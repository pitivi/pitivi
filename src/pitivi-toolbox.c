/* 
 * PiTiVi
 * Copyright (C) <2004> Bloch Stephan <bloch_s@epita.fr>
 *                      Carbon Julien <carbon_j@epita.fr>
 *                      Dubart Loic <dubart_l@epita.fr>
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
#include "pitivi-toolbox.h"
#include "pitivi-stockicons.h"
#include "pitivi-timelinewindow.h"

static PitiviWindowsClass	*parent_class = NULL;

struct _PitiviToolboxPrivate
{
  /* instance private members */
  gboolean	dispose_has_run;
  GtkWidget	*button[4];
  GSList	*group_button;
  PitiviMainApp	*mainapp;
};

/*
 * forward definitions
 */

/*
 * Insert "added-value" functions here
 */

#define mask_width 32
#define mask_height 32
#define mask_x_hot 8
#define mask_y_hot 8
#define width 32
#define height 32
#define x_hot 8
#define y_hot 8

/*
 * CALLBACKS
 */

void
load_cursor (GdkWindow *win, PitiviCursor *pitivi_cursor, PitiviCursorType PiCursorType)
{
  GdkPixmap	*pixmap;
  GdkPixmap	*mask;
  GdkColor fg = { 0, 20000, 20000, 20000 }; /* Grey */
  GdkColor bg = { 0, 65535, 65535, 65535 }; /* White */  
  
  switch (PiCursorType)
    {
    case PITIVI_CURSOR_SELECT:
      pixmap = gdk_bitmap_create_from_data (NULL, pointer_bits, width, height);
      mask = gdk_bitmap_create_from_data (NULL, pointer_mask_bits, mask_width, mask_height);
      break;
    case PITIVI_CURSOR_CUT:
      pixmap = gdk_bitmap_create_from_data (NULL, cut_bits, width, height);
      mask = gdk_bitmap_create_from_data (NULL, cut_mask_bits, mask_width, mask_height);
      break;
    case  PITIVI_CURSOR_HAND:
      pixmap = gdk_bitmap_create_from_data (NULL, hand_1_bits, width, height);
      mask = gdk_bitmap_create_from_data (NULL, hand_1_mask_bits, mask_width, mask_height);
      break;
    case  PITIVI_CURSOR_ZOOM:
      pixmap = gdk_bitmap_create_from_data (NULL, zoom_bits, width, height);
      mask = gdk_bitmap_create_from_data (NULL, zoom_mask_bits, mask_width, mask_height);
      break;
    case  PITIVI_CURSOR_RESIZE:
      pixmap = gdk_bitmap_create_from_data (NULL, resize_h_bits, width, height);
      mask = gdk_bitmap_create_from_data (NULL, resize_h_mask_bits, mask_width, mask_height);
      break;
    default:
      pixmap = gdk_bitmap_create_from_data (NULL, pointer_bits, width, height);
      mask = gdk_bitmap_create_from_data (NULL, pointer_mask_bits, mask_width, mask_height);
      break;
    }
  
  pitivi_cursor->cursor = gdk_cursor_new_from_pixmap (pixmap, mask, &fg, &bg, mask_x_hot, mask_y_hot);
  pitivi_cursor->type = PiCursorType;
  gdk_pixmap_unref (pixmap);
  gdk_pixmap_unref (mask);
  gdk_window_set_cursor(GDK_WINDOW (win), pitivi_cursor->cursor);
}

void
cursor_change_select(GtkRadioToolButton *radiobutton, PitiviToolbox *self)
{
  PitiviTimelineWindow	*timelinewin = (PitiviTimelineWindow *) pitivi_mainapp_get_timelinewin(self->private->mainapp);
  GtkWidget		*main_vbox_right;

  if (!timelinewin)
    return;
  main_vbox_right = (GtkWidget *) pitivi_timelinewindow_get_main_vbox_right(timelinewin);
  if (gtk_toggle_tool_button_get_active(GTK_TOGGLE_TOOL_BUTTON(radiobutton)))
    {
      load_cursor (GDK_WINDOW(GTK_WIDGET(main_vbox_right)->window), self->pitivi_cursor, PITIVI_CURSOR_SELECT);
      gdk_cursor_unref (self->pitivi_cursor->cursor);
    }
}

void
cursor_change_cut(GtkRadioToolButton *radiobutton, PitiviToolbox *self)
{
  PitiviTimelineWindow *timelinewin = (PitiviTimelineWindow *) pitivi_mainapp_get_timelinewin(self->private->mainapp);
  GtkWidget		*main_vbox_right;
  
  if (!timelinewin)
    return;
  main_vbox_right = (GtkWidget *) pitivi_timelinewindow_get_main_vbox_right(timelinewin);
  if (gtk_toggle_tool_button_get_active(GTK_TOGGLE_TOOL_BUTTON(radiobutton)))
    {
      load_cursor (GDK_WINDOW(GTK_WIDGET(main_vbox_right)->window), self->pitivi_cursor, PITIVI_CURSOR_CUT);
      gdk_cursor_unref (self->pitivi_cursor->cursor);
    }
}

void
cursor_change_hand(GtkRadioToolButton *radiobutton, PitiviToolbox *self)
{
  PitiviTimelineWindow *timelinewin = (PitiviTimelineWindow *) pitivi_mainapp_get_timelinewin(self->private->mainapp);
  GtkWidget		*main_vbox_right;

  if (!timelinewin)
    return;
  main_vbox_right = (GtkWidget *) pitivi_timelinewindow_get_main_vbox_right(timelinewin);
  if (gtk_toggle_tool_button_get_active(GTK_TOGGLE_TOOL_BUTTON(radiobutton)))
    {
      load_cursor (GDK_WINDOW(GTK_WIDGET(main_vbox_right)->window), self->pitivi_cursor, PITIVI_CURSOR_HAND);
      gdk_cursor_unref (self->pitivi_cursor->cursor);
    }
}

void
cursor_change_zoom (GtkRadioToolButton *radiobutton, PitiviToolbox *self)
{
  PitiviTimelineWindow *timelinewin = (PitiviTimelineWindow *) pitivi_mainapp_get_timelinewin(self->private->mainapp);
  GtkWidget		*main_vbox_right;

  if (!timelinewin)
    return;
  main_vbox_right = (GtkWidget *) pitivi_timelinewindow_get_main_vbox_right(timelinewin);
  if (gtk_toggle_tool_button_get_active(GTK_TOGGLE_TOOL_BUTTON(radiobutton)))
   {
     load_cursor (GDK_WINDOW(GTK_WIDGET(main_vbox_right)->window), self->pitivi_cursor, PITIVI_CURSOR_ZOOM);
     gdk_cursor_unref (self->pitivi_cursor->cursor);
   }
}


/*
 * Standard GObject functions
 */

PitiviToolbox *
pitivi_toolbox_new (PitiviMainApp *mainapp)
{
  PitiviToolbox *toolbox;

  toolbox = (PitiviToolbox *) g_object_new (PITIVI_TOOLBOX_TYPE, NULL);
  g_assert (toolbox != NULL);
  toolbox->private->mainapp = mainapp;
  return toolbox;
}

static GObject *
pitivi_toolbox_constructor (GType type,
			    guint n_construct_properties,
			    GObjectConstructParam * construct_properties)
{
  GObject *obj;
  {
    /* Invoke parent constructor. */
    PitiviToolboxClass *klass;
    GObjectClass *parent_class;
    klass = PITIVI_TOOLBOX_CLASS (g_type_class_peek (PITIVI_TOOLBOX_TYPE));
    parent_class = G_OBJECT_CLASS (g_type_class_peek_parent (klass));
    obj = parent_class->constructor (type, n_construct_properties,
				     construct_properties);
  }

  /* do stuff. */

  return obj;
}

static void
pitivi_toolbox_instance_init (GTypeInstance * instance, gpointer g_class)
{
  GtkTooltips	*tooltips;

  PitiviToolbox *self = (PitiviToolbox *) instance;
  GtkToolbar *tbar = GTK_TOOLBAR (instance);
  
  GdkPixmap	*pixmap;
  GdkPixmap	 *mask;
  GdkColor fg = { 0, 20000, 20000, 20000 }; /* Grey */
  GdkColor bg = { 0, 65535, 65535, 65535 }; /* White */  


  self->private = g_new0 (PitiviToolboxPrivate, 1);
  self->private->group_button = NULL;

  self->pitivi_cursor = g_new0 (PitiviCursor, 1);
  /* initialize all public and private members to reasonable default values. */

  self->private->dispose_has_run = FALSE;

  /* If you need specific consruction properties to complete initialization, 
   * delay initialization completion until the property is set. 
   */

  self->private->button[0] =
    GTK_WIDGET (gtk_radio_tool_button_new_from_stock
		(NULL, PITIVI_STOCK_POINTER));
  self->private->group_button =
    gtk_radio_tool_button_get_group (GTK_RADIO_TOOL_BUTTON
				     (self->private->button[0]));
  self->private->button[1] =
    GTK_WIDGET (gtk_radio_tool_button_new_from_stock
		(self->private->group_button, PITIVI_STOCK_CUT));
  self->private->group_button =
    gtk_radio_tool_button_get_group (GTK_RADIO_TOOL_BUTTON
				     (self->private->button[0]));
  self->private->button[2] =
    GTK_WIDGET (gtk_radio_tool_button_new_from_stock
		(self->private->group_button, PITIVI_STOCK_HAND));
  self->private->group_button =
    gtk_radio_tool_button_get_group (GTK_RADIO_TOOL_BUTTON
				     (self->private->button[0]));
  self->private->button[3] =
    GTK_WIDGET (gtk_radio_tool_button_new_from_stock
		(self->private->group_button, PITIVI_STOCK_ZOOM));

  tooltips = gtk_tooltips_new();
  gtk_tool_item_set_tooltip (GTK_TOOL_ITEM (self->private->button[0]), tooltips, "select", NULL);
  gtk_tool_item_set_tooltip (GTK_TOOL_ITEM (self->private->button[1]), tooltips, "cut", NULL);
  gtk_tool_item_set_tooltip (GTK_TOOL_ITEM (self->private->button[2]), tooltips, "move", NULL);
  gtk_tool_item_set_tooltip (GTK_TOOL_ITEM (self->private->button[3]), tooltips, "zoom", NULL);

  /*
   * We'll have to modify these functions so that they set the cursor
   * to work in the good window (i.e: PitiviTimelineWindow)
   */

  g_signal_connect (G_OBJECT (self->private->button[0]), "toggled",
		    G_CALLBACK (cursor_change_select), self);
  g_signal_connect (G_OBJECT (self->private->button[1]), "toggled",
		    G_CALLBACK (cursor_change_cut), self);
  g_signal_connect (G_OBJECT (self->private->button[2]), "toggled",
		    G_CALLBACK (cursor_change_hand), self);
  g_signal_connect(G_OBJECT(self->private->button[3]), "toggled",
		   G_CALLBACK(cursor_change_zoom), self) ;



  //gtk_toolbar_set_orientation (tbar, GTK_ORIENTATION_VERTICAL);
  gtk_toolbar_set_orientation (tbar, GTK_ORIENTATION_HORIZONTAL);
  gtk_toolbar_set_show_arrow (tbar, FALSE);
  gtk_toolbar_set_style (tbar, GTK_TOOLBAR_ICONS);
  gtk_toolbar_insert (tbar, GTK_TOOL_ITEM (self->private->button[0]), 0);
  gtk_toolbar_insert (tbar, GTK_TOOL_ITEM (self->private->button[1]), 1);
  gtk_toolbar_insert (tbar, GTK_TOOL_ITEM (self->private->button[2]), 2);
  gtk_toolbar_insert (tbar, GTK_TOOL_ITEM (self->private->button[3]), 3);

/*   Cursor initialisation */
  pixmap = gdk_bitmap_create_from_data (NULL, pointer_bits, width, height);
  mask = gdk_bitmap_create_from_data (NULL, pointer_mask_bits, mask_width, mask_height);
  self->pitivi_cursor->cursor = gdk_cursor_new_from_pixmap (pixmap, mask, &fg, &bg, mask_x_hot, mask_y_hot);
  self->pitivi_cursor->type = PITIVI_CURSOR_SELECT;
  gdk_pixmap_unref (pixmap);
  gdk_pixmap_unref (mask);
  gdk_cursor_unref (self->pitivi_cursor->cursor);

}

static void
pitivi_toolbox_dispose (GObject * object)
{
  PitiviToolbox *self = PITIVI_TOOLBOX (object);

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
pitivi_toolbox_finalize (GObject * object)
{
  PitiviToolbox *self = PITIVI_TOOLBOX (object);

  /* 
   * Here, complete object destruction. 
   * You might not need to do much... 
   */

  g_free (self->private);
}

static void
pitivi_toolbox_set_property (GObject * object,
			     guint property_id,
			     const GValue * value, GParamSpec * pspec)
{
  PitiviToolbox *self = (PitiviToolbox *) object;

  switch (property_id)
    {
      /*   case PITIVI_TOOLBOX_PROPERTY: { */
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
pitivi_toolbox_get_property (GObject * object,
			     guint property_id,
			     GValue * value, GParamSpec * pspec)
{
  PitiviToolbox *self = (PitiviToolbox *) object;

  switch (property_id)
    {
      /*  case PITIVI_TOOLBOX_PROPERTY: { */
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
pitivi_toolbox_class_init (gpointer g_class, gpointer g_class_data)
{
  GObjectClass *gobject_class = G_OBJECT_CLASS (g_class);
  PitiviToolboxClass *klass = PITIVI_TOOLBOX_CLASS (g_class);

  gobject_class->constructor = pitivi_toolbox_constructor;
  gobject_class->dispose = pitivi_toolbox_dispose;
  gobject_class->finalize = pitivi_toolbox_finalize;

  gobject_class->set_property = pitivi_toolbox_set_property;
  gobject_class->get_property = pitivi_toolbox_get_property;

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
pitivi_toolbox_get_type (void)
{
  static GType type = 0;

  if (type == 0)
    {
      static const GTypeInfo info = {
	sizeof (PitiviToolboxClass),
	NULL,			/* base_init */
	NULL,			/* base_finalize */
	pitivi_toolbox_class_init,	/* class_init */
	NULL,			/* class_finalize */
	NULL,			/* class_data */
	sizeof (PitiviToolbox),
	0,			/* n_preallocs */
	pitivi_toolbox_instance_init	/* instance_init */
      };
      type = g_type_register_static (GTK_TYPE_TOOLBAR,
				     "PitiviToolboxType", &info, 0);
    }

  return type;
}
