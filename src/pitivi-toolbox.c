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

#include "pitivi.h"
#include "pitivi-toolbox.h"

struct _PitiviToolboxPrivate
{
  /* instance private members */
  gboolean dispose_has_run;
  GtkWidget *button[4];
  GSList *group_button;
};

/*
 * forward definitions
 */

/*
 * Insert "added-value" functions here
 */

/*
 * CALLBACKS
 */

void
cursor_change_select (GtkRadioButton * radiobutton, gpointer window)
{
  GdkCursor *cursor;

  if (gtk_toggle_tool_button_get_active
      (GTK_TOGGLE_TOOL_BUTTON (radiobutton)))
    {
      cursor = gdk_cursor_new (GDK_TOP_LEFT_ARROW);
      gdk_window_set_cursor (GDK_WINDOW (GTK_WIDGET (window)->window),
			     cursor);
      gdk_cursor_unref (cursor);
    }
}
void
cursor_change_cut (GtkRadioButton * radiobutton, gpointer window)
{
  GdkCursor *cursor;

  if (gtk_toggle_tool_button_get_active
      (GTK_TOGGLE_TOOL_BUTTON (radiobutton)))
    {
      cursor = gdk_cursor_new (GDK_BOGOSITY);
      gdk_window_set_cursor (GDK_WINDOW (GTK_WIDGET (window)->window),
			     cursor);
      gdk_cursor_unref (cursor);
    }
}

void
cursor_change_hand (GtkRadioButton * radiobutton, gpointer window)
{
  GdkCursor *cursor;

  if (gtk_toggle_tool_button_get_active
      (GTK_TOGGLE_TOOL_BUTTON (radiobutton)))
    {
      cursor = gdk_cursor_new (GDK_HAND2);
      gdk_window_set_cursor (GDK_WINDOW (GTK_WIDGET (window)->window),
			     cursor);
      gdk_cursor_unref (cursor);
    }
}


/*
 * Standard GObject functions
 */

PitiviToolbox *
pitivi_toolbox_new (void)
{
  PitiviToolbox *toolbox;

  g_printf ("pitivi_toolbox_new()\n");

  toolbox = (PitiviToolbox *) g_object_new (PITIVI_TOOLBOX_TYPE, NULL);
  g_assert (toolbox != NULL);
  return toolbox;
}

static GObject *
pitivi_toolbox_constructor (GType type,
			    guint n_construct_properties,
			    GObjectConstructParam * construct_properties)
{
  g_printf ("pitivi_toolbox_constructor()\n");

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
  PitiviToolbox *self = (PitiviToolbox *) instance;
  GtkToolbar *tbar = GTK_TOOLBAR (instance);

  g_printf ("pitivi_toolbox_instance_init()\n");

  self->private = g_new0 (PitiviToolboxPrivate, 1);
  self->private->group_button = g_new0 (GSList, 1);

  /* initialize all public and private members to reasonable default values. */

  self->private->dispose_has_run = FALSE;

  /* If you need specific consruction properties to complete initialization, 
   * delay initialization completion until the property is set. 
   */

  self->private->button[0] =
    GTK_WIDGET (gtk_radio_tool_button_new_from_stock
		(NULL, GTK_STOCK_COLOR_PICKER));
  self->private->group_button =
    gtk_radio_tool_button_get_group (GTK_RADIO_TOOL_BUTTON
				     (self->private->button[0]));
  self->private->button[1] =
    GTK_WIDGET (gtk_radio_tool_button_new_from_stock
		(self->private->group_button, GTK_STOCK_CUT));
  self->private->group_button =
    gtk_radio_tool_button_get_group (GTK_RADIO_TOOL_BUTTON
				     (self->private->button[0]));
  self->private->button[2] =
    GTK_WIDGET (gtk_radio_tool_button_new_from_stock
		(self->private->group_button, GTK_STOCK_INDEX));
  self->private->group_button =
    gtk_radio_tool_button_get_group (GTK_RADIO_TOOL_BUTTON
				     (self->private->button[0]));
  self->private->button[3] =
    GTK_WIDGET (gtk_radio_tool_button_new_from_stock
		(self->private->group_button, GTK_STOCK_ZOOM_IN));

  /*
   * We'll have to modify these functions so that they set the cursor
   * to work in the good window (i.e: PitiviTimelineWindow)
   */

  g_signal_connect (G_OBJECT (self->private->button[0]), "toggled",
		    G_CALLBACK (cursor_change_select), (gpointer) self);
  g_signal_connect (G_OBJECT (self->private->button[1]), "toggled",
		    G_CALLBACK (cursor_change_cut), (gpointer) self);
  g_signal_connect (G_OBJECT (self->private->button[2]), "toggled",
		    G_CALLBACK (cursor_change_hand), (gpointer) self);
/*   g_signal_connect(G_OBJECT(self->private->button[3]), "toggled", */
/* 		   G_CALLBACK(cursor_change_zoom), (gpointer)self) ; */

  gtk_toolbar_set_orientation (tbar, GTK_ORIENTATION_VERTICAL);
  gtk_toolbar_set_show_arrow (tbar, FALSE);
  gtk_toolbar_set_style (tbar, GTK_TOOLBAR_ICONS);
  gtk_toolbar_insert (tbar, GTK_TOOL_ITEM (self->private->button[0]), 0);
  gtk_toolbar_insert (tbar, GTK_TOOL_ITEM (self->private->button[1]), 1);
  gtk_toolbar_insert (tbar, GTK_TOOL_ITEM (self->private->button[2]), 2);
  gtk_toolbar_insert (tbar, GTK_TOOL_ITEM (self->private->button[3]), 3);

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

  g_printf ("pitivi_main_class_init()\n");

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

  g_printf ("pitivi_main_get_type()\n");

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
