/* 
 * PiTiVi
 * Copyright (C) <2004> Edward G. Hervey <hervey_e@epita.fr>
 *                      Guillaume Casanova <casano_g@epita.fr>
 *                      Raphael Pralat <pralat_r@epita.fr>
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
#include "pitivi-effectswindowproperties.h"
#include "pitivi-settings.h"

static	GtkWindowClass *parent_class = NULL;

enum {
  PROP_ITEM_PROPERTY = 1,
};

struct _PitiviEffectsWindowPropertiesPrivate
{
  PitiviSourceItem *item;
  /* instance private members */
  gboolean	dispose_has_run;

  PitiviSettingsIoElement *io;
  PitiviGstElementSettings *widget_element;
  GstElement	*effect;
};

/*
 * forward definitions
 */

/*
 * Insert "added-value" functions here
 */

PitiviEffectsWindowProperties *
pitivi_effectswindowproperties_new (PitiviSourceItem *effect)
{
  PitiviEffectsWindowProperties	*effectswindowproperties;

  effectswindowproperties = (PitiviEffectsWindowProperties *) g_object_new(PITIVI_EFFECTSWINDOWPROPERTIES_TYPE, 
									   "effectitem",
									   effect,
									   NULL);
  g_assert(effectswindowproperties != NULL);
  return effectswindowproperties;
}

static void
pitivi_set_effectproperties(PitiviSettingsIoElement *io, GstElement *effect)
{
  gint	i;
  i = 0;

  PITIVI_DEBUG ("OK %s", gst_element_get_name(effect));

  while (i < io->n_param)
    {
      PITIVI_DEBUG ("OK %s", io->params[i].name);
      g_object_set_property(G_OBJECT(effect),
			    g_strdup(io->params[i].name),
			    &io->params[i].value);
      i++;
    }
}

static void 
pitivi_effects_ok (GtkWidget *widget, GObject *obj)
{
  PitiviEffectsWindowProperties *self;

  PITIVI_DEBUG ("PitiviEffectsWindowProperties  OK");
  /* TODO : The effect GstElement is self->private->effect !!! */

  self = PITIVI_EFFECTSWINDOWPROPERTIES (obj);
  /* On reutilise la variable pour une economie de mem */
  self->private->io = pitivi_gstelementsettings_get_settings_elem (self->private->widget_element);
  pitivi_set_effectproperties(self->private->io, self->private->effect);

  PITIVI_DEBUG ("Pitivi_ok_destroy  OK");
  gtk_object_destroy(GTK_OBJECT(obj));
}

static void 
pitivi_effects_apply (GtkWidget *widget, GObject *obj)
{
  PitiviEffectsWindowProperties *self;
  PitiviSettingsIoElement	*new_io;

  PITIVI_DEBUG ("PitiviEffectsWindowProperties  APPLY");
  /* TODO : The effect GstElement is self->private->effect !!! */

  self = PITIVI_EFFECTSWINDOWPROPERTIES (obj);
  new_io = pitivi_gstelementsettings_get_settings_elem (self->private->widget_element);
  pitivi_set_effectproperties(new_io, self->private->effect);
}


static void 
pitivi_effects_cancel (GtkWidget *widget, GObject *obj)
{
  PitiviEffectsWindowProperties *self;

  PITIVI_DEBUG ("PitiviEffectsWindowProperties  CANCEL");
  /* TODO : The effect GstElement is self->private->effect !!! */

  self = PITIVI_EFFECTSWINDOWPROPERTIES (obj);
  pitivi_set_effectproperties(self->private->io, self->private->effect);

  PITIVI_DEBUG ("Pitivi_ok_destroy  OK");
  gtk_object_destroy(GTK_OBJECT(obj));
}




static GObject *
pitivi_effectswindowproperties_constructor (GType type,
					    guint n_construct_properties,
					    GObjectConstructParam * construct_properties)
{
  PitiviEffectsWindowPropertiesClass *klass;
  GObject *obj;
  GtkWidget *main_vbox;
  GObjectClass *parent_class;
  GtkWidget *hbox;
  GtkWidget *button_ok;
  GtkWidget *button_apply;
  GtkWidget *button_cancel;
  PitiviEffectsWindowProperties *self;

  /* Invoke parent constructor. */
  
  klass = PITIVI_EFFECTSWINDOWPROPERTIES_CLASS (g_type_class_peek (PITIVI_EFFECTSWINDOWPROPERTIES_TYPE));
  parent_class = G_OBJECT_CLASS (g_type_class_peek_parent (klass));
  obj = parent_class->constructor (type, n_construct_properties,
				   construct_properties);
  self = (PitiviEffectsWindowProperties *) obj;
  
  /* do stuff. */
  
  gtk_window_set_position (GTK_WINDOW (self), GTK_WIN_POS_CENTER);
  gtk_window_set_modal (GTK_WINDOW(self), TRUE);
  
  main_vbox = gtk_vbox_new (FALSE, 0);
  gtk_container_add  (GTK_CONTAINER (self), main_vbox);
  self->private->effect = g_object_get_data (G_OBJECT (GNL_OPERATION (self->private->item->gnlobject)->element), "effect");
  self->private->io = pitivi_settings_new_io_element_with_element (self->private->effect);
  self->private->widget_element = pitivi_gstelementsettings_new (self->private->io, 1);
  gtk_box_pack_start (GTK_BOX (main_vbox), GTK_WIDGET (self->private->widget_element), FALSE, FALSE, 0);
  
  /* OK Cancel Buttons*/
  hbox = gtk_hbox_new (FALSE, FALSE);
  gtk_box_pack_start (GTK_BOX (main_vbox), GTK_WIDGET (hbox), FALSE, FALSE, 0);

  button_ok = gtk_button_new_from_stock(GTK_STOCK_OK);
  gtk_box_pack_start (GTK_BOX (hbox), GTK_WIDGET (button_ok), TRUE, FALSE, 5);
  gtk_signal_connect (GTK_OBJECT (button_ok), "released",
  		      GTK_SIGNAL_FUNC (pitivi_effects_ok), obj); 

  button_apply = gtk_button_new_from_stock(GTK_STOCK_APPLY);
  gtk_box_pack_start (GTK_BOX (hbox), GTK_WIDGET (button_apply), TRUE, FALSE, 5);
  gtk_signal_connect (GTK_OBJECT (button_apply), "released",
  		      GTK_SIGNAL_FUNC (pitivi_effects_apply), obj); 

  button_cancel = gtk_button_new_from_stock(GTK_STOCK_CANCEL);
  gtk_box_pack_start (GTK_BOX (hbox), GTK_WIDGET (button_cancel), TRUE, FALSE, 5);
  gtk_signal_connect (GTK_OBJECT (button_cancel), "released",
  		      GTK_SIGNAL_FUNC (pitivi_effects_cancel), obj); 

  gtk_window_set_modal(GTK_WINDOW(self), FALSE);

  return obj;
}

static void
pitivi_effectswindowproperties_instance_init (GTypeInstance * instance, gpointer g_class)
{
  PitiviEffectsWindowProperties *self = (PitiviEffectsWindowProperties *) instance;

  self->private = g_new0(PitiviEffectsWindowPropertiesPrivate, 1);
  self->private->dispose_has_run = FALSE;
}

static void
pitivi_effectswindowproperties_dispose (GObject *object)
{
  PitiviEffectsWindowProperties	*self = PITIVI_EFFECTSWINDOWPROPERTIES(object);

  /* If dispose did already run, return. */
  if (self->private->dispose_has_run)
    return;
  
  /* Make sure dispose does not run twice. */
  self->private->dispose_has_run = TRUE;	
  G_OBJECT_CLASS (parent_class)->dispose (object);
}

static void
pitivi_effectswindowproperties_finalize (GObject *object)
{
  PitiviEffectsWindowProperties	*self = PITIVI_EFFECTSWINDOWPROPERTIES(object);
  g_free (self->private);
  G_OBJECT_CLASS (parent_class)->finalize (object);
}

static void
pitivi_effectswindowproperties_set_property (GObject * object,
					     guint property_id,
					     const GValue * value, GParamSpec * pspec)
{
  PitiviEffectsWindowProperties	*self = PITIVI_EFFECTSWINDOWPROPERTIES(object);
  
  switch (property_id)
    {
    case PROP_ITEM_PROPERTY:
      self->private->item = g_value_get_pointer (value);
      break;
    default:
      g_assert (FALSE);
      break;
    }
}

static void
pitivi_effectswindowproperties_get_property (GObject * object,
					     guint property_id,
					     GValue * value, GParamSpec * pspec)
{
  PitiviEffectsWindowProperties	*self = PITIVI_EFFECTSWINDOWPROPERTIES(object);
  switch (property_id)
    {
    case PROP_ITEM_PROPERTY:
       g_value_set_pointer (value, self->private->item);
      break;
    default:
      g_assert (FALSE);
      break;
    }
}

static void
pitivi_effectswindowproperties_class_init (gpointer g_class, gpointer g_class_data)
{
  GObjectClass *gobject_class = G_OBJECT_CLASS (g_class);
  
  parent_class = g_type_class_peek_parent (g_class);
  gobject_class->constructor = pitivi_effectswindowproperties_constructor;
  gobject_class->dispose = pitivi_effectswindowproperties_dispose;
  gobject_class->finalize = pitivi_effectswindowproperties_finalize;

  gobject_class->set_property = pitivi_effectswindowproperties_set_property;
  gobject_class->get_property = pitivi_effectswindowproperties_get_property;

  g_object_class_install_property (G_OBJECT_CLASS (gobject_class), PROP_ITEM_PROPERTY,
				   g_param_spec_pointer ("effectitem","effectitem","effectitem",
							 G_PARAM_READWRITE | G_PARAM_CONSTRUCT));
  
}

GType
pitivi_effectswindowproperties_get_type (void)
{
  static GType type = 0;
 
  if (type == 0)
    {
      static const GTypeInfo info = {
	sizeof (PitiviEffectsWindowPropertiesClass),
	NULL,			/* base_init */
	NULL,			/* base_finalize */
	pitivi_effectswindowproperties_class_init,	/* class_init */
	NULL,			/* class_finalize */
	NULL,			/* class_data */
	sizeof (PitiviEffectsWindowProperties),
	0,			/* n_preallocs */
	pitivi_effectswindowproperties_instance_init	/* instance_init */
      };
      type = g_type_register_static (PITIVI_WINDOWS_TYPE,
				     "PitiviEffectsWindowPropertiesType", &info, 0);
    }

  return type;
}
