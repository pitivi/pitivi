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
#include "pitivi-template.h"

struct _PitiviTemplatePrivate
{
  /* instance private members */
  gboolean	dispose_has_run;
};

/*
 * forward definitions
 */

/*
 * Insert "added-value" functions here
 */

PitiviTemplate *
pitivi_temp_late_new(void)
{
  PitiviTemplate	*template;

  template = (PitiviTemplate *) g_object_new(PITIVI_TEMPLATE_TYPE, NULL);
  g_assert(template != NULL);
  return template;
}

static GObject *
pitivi_temp_late_constructor (GType type,
			     guint n_construct_properties,
			     GObjectConstructParam * construct_properties)
{
  GObject *obj;
  {
    /* Invoke parent constructor. */
    PitiviTemplateClass *klass;
    GObjectClass *parent_class;
    klass = PITIVI_TEMPLATE_CLASS (g_type_class_peek (PITIVI_TEMPLATE_TYPE));
    parent_class = G_OBJECT_CLASS (g_type_class_peek_parent (klass));
    obj = parent_class->constructor (type, n_construct_properties,
				     construct_properties);
  }

  /* do stuff. */

  return obj;
}

static void
pitivi_temp_late_instance_init (GTypeInstance * instance, gpointer g_class)
{
  PitiviTemplate *self = (PitiviTemplate *) instance;

  self->private = g_new0(PitiviTemplatePrivate, 1);
  
  /* initialize all public and private members to reasonable default values. */ 
  
  self->private->dispose_has_run = FALSE;
  
  /* If you need specific consruction properties to complete initialization, 
   * delay initialization completion until the property is set. 
   */
  
}

static void
pitivi_temp_late_dispose (GObject *object)
{
  PitiviTemplate	*self = PITIVI_TEMPLATE(object);

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
pitivi_temp_late_finalize (GObject *object)
{
  PitiviTemplate	*self = PITIVI_TEMPLATE(object);

  /* 
   * Here, complete object destruction. 
   * You might not need to do much... 
   */

  g_free (self->private);
}

static void
pitivi_temp_late_set_property (GObject * object,
			      guint property_id,
			      const GValue * value, GParamSpec * pspec)
{
  PitiviTemplate *self = (PitiviTemplate *) object;

  switch (property_id)
    {
      /*   case PITIVI_TEMPLATE_PROPERTY: { */
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
pitivi_temp_late_get_property (GObject * object,
			      guint property_id,
			      GValue * value, GParamSpec * pspec)
{
  PitiviTemplate *self = (PitiviTemplate *) object;

  switch (property_id)
    {
      /*  case PITIVI_TEMPLATE_PROPERTY: { */
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
pitivi_temp_late_class_init (gpointer g_class, gpointer g_class_data)
{
  GObjectClass *gobject_class = G_OBJECT_CLASS (g_class);
  PitiviTemplateClass *klass = PITIVI_TEMPLATE_CLASS (g_class);

  gobject_class->constructor = pitivi_temp_late_constructor;
  gobject_class->dispose = pitivi_temp_late_dispose;
  gobject_class->finalize = pitivi_temp_late_finalize;

  gobject_class->set_property = pitivi_temp_late_set_property;
  gobject_class->get_property = pitivi_temp_late_get_property;

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
pitivi_temp_late_get_type (void)
{
  static GType type = 0;
 
  if (type == 0)
    {
      static const GTypeInfo info = {
	sizeof (PitiviTemplateClass),
	NULL,			/* base_init */
	NULL,			/* base_finalize */
	pitivi_temp_late_class_init,	/* class_init */
	NULL,			/* class_finalize */
	NULL,			/* class_data */
	sizeof (PitiviTemplate),
	0,			/* n_preallocs */
	pitivi_temp_late_instance_init	/* instance_init */
      };
      type = g_type_register_static (G_TYPE_OBJECT,
				     "PitiviTemplateType", &info, 0);
    }

  return type;
}
