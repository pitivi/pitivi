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
#include "pitivi-cursorbits.h"
#include "pitivi-toolbox.h"
#include "pitivi-stockicons.h"
#include "pitivi-timelinewindow.h"

/* static PitiviWindowsClass	*parent_class = NULL; */

struct _PitiviToolboxPrivate
{
  /* instance private members */
  gboolean	dispose_has_run;
  GtkWidget	*button[5];
  GSList	*group_button;
  PitiviMainApp	*mainapp;
};

/*
 * forward definitions
 */

/*
 * Insert "added-value" functions here
 */

void cursor_change_select  (GtkRadioToolButton *radiobutton, PitiviToolbox *self);
void cursor_change_cut     (GtkRadioToolButton *radiobutton, PitiviToolbox *self);
void cursor_change_hand    (GtkRadioToolButton *radiobutton, PitiviToolbox *self);
void cursor_change_zoom    (GtkRadioToolButton *radiobutton, PitiviToolbox *self);
void cursor_change_resize  (GtkRadioToolButton *radiobutton, PitiviToolbox *self);

typedef struct _InfoBox
{
  gchar *image;
  gchar *tooltip;
  void (*callback)  (GtkRadioToolButton *radiobutton, PitiviToolbox *self);
}	       InfoBox;


InfoBox button_info [] = {
  {PITIVI_STOCK_POINTER, "pointer", cursor_change_select},
  {PITIVI_STOCK_CUT, "cut", cursor_change_cut},
  {PITIVI_STOCK_HAND, "hand", cursor_change_hand},
  {PITIVI_STOCK_ZOOM, "zoom", cursor_change_zoom},
  {PITIVI_STOCK_RESIZE, "resize", cursor_change_resize},
  {0, 0, NULL}
};


/*
 * CALLBACKS
 */

void
load_cursor(GdkWindow *win,
		  PitiviCursor *pitivi_cursor,
		  PitiviCursorType PiCursorType)
{
     int width;
     int height;
     int hot_x;
     int hot_y;

  GdkPixmap	*pixmap;
  GdkPixmap	*mask;
  GdkColor fg = { 0, 20000, 20000, 20000 }; /* Grey */
  GdkColor bg = { 0, 65535, 65535, 65535 }; /* White */
  
  width = CST_WIDTH;
  height = CST_HEIGHT;

  switch (PiCursorType)
    {
    case PITIVI_CURSOR_SELECT:
      pixmap = gdk_bitmap_create_from_data (NULL, pointer_bits, width, height);
      mask = gdk_bitmap_create_from_data (NULL, pointer_mask_bits, width, height);
      hot_x = CST_X_HOT + 2;
      hot_y = CST_Y_HOT + 2;
      break;
    case PITIVI_CURSOR_CUT:
      pixmap = gdk_bitmap_create_from_data (NULL, cut_bits, width, height);
      mask = gdk_bitmap_create_from_data (NULL, cut_mask_bits, width, height);
      hot_x = CST_X_HOT + 1;
      hot_y = CST_Y_HOT + 1;
      break;
    case  PITIVI_CURSOR_HAND:
      pixmap = gdk_bitmap_create_from_data (NULL, hand_1_bits, width, height);
      mask = gdk_bitmap_create_from_data (NULL, hand_1_mask_bits, width, height);
      hot_x = CST_X_HOT + 4;
      hot_y = CST_Y_HOT + 4;
      break;
    case PITIVI_CURSOR_ZOOM:
    case PITIVI_CURSOR_ZOOM_INC:
    case PITIVI_CURSOR_ZOOM_DEC:
      pixmap = gdk_bitmap_create_from_data (NULL, zoom_bits, width, height);
      mask = gdk_bitmap_create_from_data (NULL, zoom_mask_bits, width, height);
      hot_x = CST_X_HOT + 1;
      hot_y = CST_Y_HOT + 1;
      break;
    case  PITIVI_CURSOR_RESIZE:
      pixmap = gdk_bitmap_create_from_data (NULL, resize_bits, width, height);
      mask = gdk_bitmap_create_from_data (NULL, resize_mask_bits, width, height);
      hot_x = 0;
      hot_y = height/2;
      break;
    case PITIVI_CURSOR_NOALLOW:
      pixmap = gdk_bitmap_create_from_data (NULL, zoom_bits, width, height);
      mask = gdk_bitmap_create_from_data (NULL, zoom_mask_bits, width, height);
      hot_x = CST_X_HOT;
      hot_y = CST_Y_HOT;
      break;
    default:
      pixmap = gdk_bitmap_create_from_data (NULL, pointer_bits, width, height);
      mask = gdk_bitmap_create_from_data (NULL, pointer_mask_bits, width, height);
      hot_x = CST_X_HOT;
      hot_y = CST_Y_HOT;
      break;
    }
  
  pitivi_cursor->cursor = gdk_cursor_new_from_pixmap (pixmap, mask, &fg, &bg, hot_x, hot_y);
  pitivi_cursor->type = PiCursorType;
  pitivi_cursor->height = height;
  pitivi_cursor->width = width;
  pitivi_cursor->hot_x = hot_x;
  pitivi_cursor->hot_y = hot_y;
  gdk_pixmap_unref (pixmap);
  gdk_pixmap_unref (mask);
  if (win)
    gdk_window_set_cursor(GDK_WINDOW (win), pitivi_cursor->cursor);
}

void
cursor_change_select(GtkRadioToolButton *radiobutton, PitiviToolbox *self)
{
  PitiviTimelineWindow	*timelinewin = (PitiviTimelineWindow *) pitivi_mainapp_get_timelinewin(self->private->mainapp);
  GtkWidget		*container;

  if (!timelinewin)
    return;
  container = (GtkWidget *) pitivi_timelinewindow_get_container(timelinewin);
  if (gtk_toggle_tool_button_get_active(GTK_TOGGLE_TOOL_BUTTON(radiobutton)))
    {
      load_cursor (GDK_WINDOW(GTK_WIDGET(container)->window), self->pitivi_cursor, PITIVI_CURSOR_SELECT);
      gdk_cursor_unref (self->pitivi_cursor->cursor);
    }
}

void
cursor_change_cut(GtkRadioToolButton *radiobutton, PitiviToolbox *self)
{
  PitiviTimelineWindow *timelinewin = (PitiviTimelineWindow *) pitivi_mainapp_get_timelinewin(self->private->mainapp);
  GtkWidget		*container;
  
  if (!timelinewin)
    return;
  container = (GtkWidget *) pitivi_timelinewindow_get_container(timelinewin);
  if (gtk_toggle_tool_button_get_active(GTK_TOGGLE_TOOL_BUTTON(radiobutton)))
    {
      load_cursor (GDK_WINDOW(GTK_WIDGET(container)->window), self->pitivi_cursor, PITIVI_CURSOR_CUT);
      gdk_cursor_unref (self->pitivi_cursor->cursor);
    }
}

void
cursor_change_hand(GtkRadioToolButton *radiobutton, PitiviToolbox *self)
{
  PitiviTimelineWindow *timelinewin = (PitiviTimelineWindow *) pitivi_mainapp_get_timelinewin(self->private->mainapp);
  GtkWidget		*container;

  if (!timelinewin)
    return;
  container = (GtkWidget *) pitivi_timelinewindow_get_container(timelinewin);
  if (gtk_toggle_tool_button_get_active(GTK_TOGGLE_TOOL_BUTTON(radiobutton)))
    {
      load_cursor (GDK_WINDOW(GTK_WIDGET(container)->window), self->pitivi_cursor, PITIVI_CURSOR_HAND);
      gdk_cursor_unref (self->pitivi_cursor->cursor);
    }
}

void
cursor_change_zoom (GtkRadioToolButton *radiobutton, PitiviToolbox *self)
{
  PitiviTimelineWindow *timelinewin = (PitiviTimelineWindow *) pitivi_mainapp_get_timelinewin(self->private->mainapp);
  GtkWidget		*container;

  if (!timelinewin)
    return;
  container = (GtkWidget *) pitivi_timelinewindow_get_container(timelinewin);
  if (gtk_toggle_tool_button_get_active(GTK_TOGGLE_TOOL_BUTTON(radiobutton)))
   {
     load_cursor (GDK_WINDOW(GTK_WIDGET(container)->window), self->pitivi_cursor, PITIVI_CURSOR_ZOOM);
     gdk_cursor_unref (self->pitivi_cursor->cursor);
   }
}

void
cursor_change_resize (GtkRadioToolButton *radiobutton, PitiviToolbox *self)
{
  PitiviTimelineWindow *timelinewin = (PitiviTimelineWindow *) pitivi_mainapp_get_timelinewin(self->private->mainapp);
  GtkWidget	       *container;

  if (!timelinewin)
    return;
  container = (GtkWidget *) pitivi_timelinewindow_get_container(timelinewin);
  if (gtk_toggle_tool_button_get_active(GTK_TOGGLE_TOOL_BUTTON(radiobutton)))
   {
     load_cursor (GDK_WINDOW(GTK_WIDGET(container)->window), self->pitivi_cursor, PITIVI_CURSOR_RESIZE);
     gdk_cursor_unref (self->pitivi_cursor->cursor);
   }
}
/*
 * Standard GObject functions
 */

/**
 * pitivi_toolbox_new: 
 * @PitiviMainApp: The object referencing the application
 *
 * Creates a new element PitiviToolbox, the toolbox
 *
 * Returns: A element PitiviToolbox
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
  int		count;
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
  self->pitivi_cursor->width = CST_MASK_WIDTH;
  self->pitivi_cursor->height = CST_MASK_HEIGHT;
  self->pitivi_cursor->hot_x = CST_X_HOT;
  self->pitivi_cursor->hot_y = CST_Y_HOT;
  self->pitivi_cursor->type =  PITIVI_CURSOR_SELECT;
  
  /* initialize all public and private members to reasonable default values. */

  self->private->dispose_has_run = FALSE;

  /* If you need specific consruction properties to complete initialization, 
   * delay initialization completion until the property is set. 
   */
    
  tooltips = gtk_tooltips_new();
  for (count = 0; button_info[count].image; count++)
    {
      self->private->button[count] =
	GTK_WIDGET (gtk_radio_tool_button_new_from_stock
		    (self->private->group_button, button_info[count].image));
      self->private->group_button = gtk_radio_tool_button_get_group (GTK_RADIO_TOOL_BUTTON
								     (self->private->button[0]));
      gtk_tool_item_set_tooltip (GTK_TOOL_ITEM (self->private->button[count]), tooltips, button_info[count].tooltip, NULL);
      gtk_toolbar_insert (tbar, GTK_TOOL_ITEM (self->private->button[count]), count);
      g_signal_connect (G_OBJECT (self->private->button[count]), "toggled",
			G_CALLBACK (button_info[count].callback), self);
    }
  gtk_toolbar_set_orientation (tbar, GTK_ORIENTATION_HORIZONTAL);
  gtk_toolbar_set_show_arrow (tbar, FALSE);
  gtk_toolbar_set_style (tbar, GTK_TOOLBAR_ICONS);
  
  /*   Cursor initialisation */
  
  pixmap = gdk_bitmap_create_from_data (NULL, pointer_bits, CST_WIDTH, CST_HEIGHT);
  mask = gdk_bitmap_create_from_data (NULL, pointer_mask_bits, CST_MASK_WIDTH, CST_MASK_HEIGHT);
  self->pitivi_cursor->cursor = gdk_cursor_new_from_pixmap (pixmap, mask, &fg, &bg,  CST_X_HOT, CST_Y_HOT);
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
}

static void
pitivi_toolbox_finalize (GObject * object)
{
  PitiviToolbox *self = PITIVI_TOOLBOX (object);
  g_free (self->private);
}

static void
pitivi_toolbox_class_init (gpointer g_class, gpointer g_class_data)
{
  GObjectClass *gobject_class = G_OBJECT_CLASS (g_class);
/*   PitiviToolboxClass *klass = PITIVI_TOOLBOX_CLASS (g_class); */

  gobject_class->constructor = pitivi_toolbox_constructor;
  gobject_class->dispose = pitivi_toolbox_dispose;
  gobject_class->finalize = pitivi_toolbox_finalize;
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
