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
#include "pitivi-gstelementsettings.h"

static     GObjectClass *parent_class;


struct _PitiviGstElementSettingsPrivate
{
  /* instance private members */
  gboolean	dispose_has_run;

};

enum {
  PROP_0,
  PROP_ELM
};


/*
 * forward definitions
 */






/*
 * Insert "added-value" functions here
 */


void
pitivi_gstelementsettings_create_gui (PitiviGstElementSettings *self)
{
  GtkWidget *Label;

  Label = gtk_label_new (self->elm);
  gtk_container_add (GTK_CONTAINER (self), Label);
  gtk_widget_show_all (GTK_WIDGET (self));  
  return ;
}


/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * */

PitiviGstElementSettings *
pitivi_gstelementsettings_new(gchar *elm)
{
  PitiviGstElementSettings	*gstelementsettings;

  gstelementsettings = (PitiviGstElementSettings *) g_object_new(PITIVI_GSTELEMENTSETTINGS_TYPE,
								 "elm", elm,
								 NULL);
  g_assert(gstelementsettings != NULL);
  return gstelementsettings;
}

static GObject *
pitivi_gstelementsettings_constructor (GType type,
			     guint n_construct_properties,
			     GObjectConstructParam * construct_properties)
{
  GObject *obj;
  /* Invoke parent constructor. */
  obj =  G_OBJECT_CLASS (parent_class)->constructor (type, n_construct_properties,
						     construct_properties);

  /* do stuff. */
  PitiviGstElementSettings *self = (PitiviGstElementSettings *) obj;

  pitivi_gstelementsettings_create_gui (self);

  return obj;
}

static void
pitivi_gstelementsettings_instance_init (GTypeInstance * instance, gpointer g_class)
{
  PitiviGstElementSettings *self = (PitiviGstElementSettings *) instance;

  self->private = g_new0(PitiviGstElementSettingsPrivate, 1);
  
  /* initialize all public and private members to reasonable default values. */ 
  
  self->private->dispose_has_run = FALSE;
  
  /* Do only initialisation here */
  /* The construction of the object should be done in the Constructor
     So that properties set at instanciation can be set */
}

static void
pitivi_gstelementsettings_dispose (GObject *object)
{
  PitiviGstElementSettings	*self = PITIVI_GSTELEMENTSETTINGS(object);

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
pitivi_gstelementsettings_finalize (GObject *object)
{
  PitiviGstElementSettings	*self = PITIVI_GSTELEMENTSETTINGS(object);

  /* 
   * Here, complete object destruction. 
   * You might not need to do much... 
   */

  g_free (self->private);
  g_free (self->elm);
  G_OBJECT_CLASS (parent_class)->finalize (object);
}

static void
pitivi_gstelementsettings_set_property (GObject * object,
			      guint property_id,
			      const GValue * value, GParamSpec * pspec)
{
  PitiviGstElementSettings *self = (PitiviGstElementSettings *) object;

  switch (property_id)
    {
    case PROP_ELM:
      self->elm = g_value_dup_string (value);
      break;
    default:
      /* We don't have any other property... */
      g_assert (FALSE);
      break;
    }
}

static void
pitivi_gstelementsettings_get_property (GObject * object,
			      guint property_id,
			      GValue * value, GParamSpec * pspec)
{
  PitiviGstElementSettings *self = (PitiviGstElementSettings *) object;

  switch (property_id)
    {
    case PROP_ELM:
      g_value_set_string (value, self->elm);
      break;
    default:
      /* We don't have any other property... */
      g_assert (FALSE);
      break;
    }
}

static void
pitivi_gstelementsettings_class_init (gpointer g_class, gpointer g_class_data)
{
  GObjectClass *gobject_class = G_OBJECT_CLASS (g_class);
  PitiviGstElementSettingsClass *klass = PITIVI_GSTELEMENTSETTINGS_CLASS (g_class);

  parent_class = G_OBJECT_CLASS (g_type_class_peek_parent (g_class));

  gobject_class->constructor = pitivi_gstelementsettings_constructor;
  gobject_class->dispose = pitivi_gstelementsettings_dispose;
  gobject_class->finalize = pitivi_gstelementsettings_finalize;

  gobject_class->set_property = pitivi_gstelementsettings_set_property;
  gobject_class->get_property = pitivi_gstelementsettings_get_property;

  /* Install the properties in the class here ! */

  g_object_class_install_property (gobject_class,
				   PROP_ELM,
				   g_param_spec_string ("elm",
							"elm",
							"GstElement's name",
							NULL, 
							G_PARAM_CONSTRUCT_ONLY | G_PARAM_WRITABLE)
				   );


}

GType
pitivi_gstelementsettings_get_type (void)
{
  static GType type = 0;
 
  if (type == 0)
    {
      static const GTypeInfo info = {
	sizeof (PitiviGstElementSettingsClass),
	NULL,			/* base_init */
	NULL,			/* base_finalize */
	pitivi_gstelementsettings_class_init,	/* class_init */
	NULL,			/* class_finalize */
	NULL,			/* class_data */
	sizeof (PitiviGstElementSettings),
	0,			/* n_preallocs */
	pitivi_gstelementsettings_instance_init	/* instance_init */
      };
      type = g_type_register_static (GTK_TYPE_VBOX,
				     "PitiviGstElementSettingsType", &info, 0);
    }

  return type;
}
