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
#include "pitivi-codecconfwindow.h"

static GtkWindowClass *parent_class = NULL;

struct _PitiviCodecConfWindowPrivate
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

PitiviCodecConfWindow *
pitivi_codecconfwindow_new(void)
{
  PitiviCodecConfWindow	*codecconfwindow;

  codecconfwindow = (PitiviCodecConfWindow *) g_object_new(PITIVI_CODECCONFWINDOW_TYPE, NULL);
  g_assert(codecconfwindow != NULL);
  return codecconfwindow;
}

static GObject *
pitivi_codecconfwindow_constructor (GType type,
			     guint n_construct_properties,
			     GObjectConstructParam * construct_properties)
{
  GObject *obj;
  {
    /* Invoke parent constructor. */
    PitiviCodecConfWindowClass *klass;
    GObjectClass *parent_class;
    klass = PITIVI_CODECCONFWINDOW_CLASS (g_type_class_peek (PITIVI_CODECCONFWINDOW_TYPE));
    parent_class = G_OBJECT_CLASS (g_type_class_peek_parent (klass));
    obj = parent_class->constructor (type, n_construct_properties,
				     construct_properties);
  }

  /* do stuff. */

  return obj;
}

static void
pitivi_codecconfwindow_instance_init (GTypeInstance * instance, gpointer g_class)
{
  PitiviCodecConfWindow *self = (PitiviCodecConfWindow *) instance;

  self->private = g_new0(PitiviCodecConfWindowPrivate, 1);
  
  /* initialize all public and private members to reasonable default values. */ 
  
  self->private->dispose_has_run = FALSE;
  
  /* If you need specific consruction properties to complete initialization, 
   * delay initialization completion until the property is set. 
   */
  
}

static void
pitivi_codecconfwindow_dispose (GObject *object)
{
  PitiviCodecConfWindow	*self = PITIVI_CODECCONFWINDOW(object);

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
pitivi_codecconfwindow_finalize (GObject *object)
{
  PitiviCodecConfWindow	*self = PITIVI_CODECCONFWINDOW(object);

  /* 
   * Here, complete object destruction. 
   * You might not need to do much... 
   */

  g_free (self->private);
  G_OBJECT_CLASS (parent_class)->finalize (object);
}

static void
pitivi_codecconfwindow_set_property (GObject * object,
			      guint property_id,
			      const GValue * value, GParamSpec * pspec)
{
  PitiviCodecConfWindow *self = (PitiviCodecConfWindow *) object;

  switch (property_id)
    {
      /*   case PITIVI_CODECCONFWINDOW_PROPERTY: { */
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
pitivi_codecconfwindow_get_property (GObject * object,
			      guint property_id,
			      GValue * value, GParamSpec * pspec)
{
  PitiviCodecConfWindow *self = (PitiviCodecConfWindow *) object;

  switch (property_id)
    {
      /*  case PITIVI_CODECCONFWINDOW_PROPERTY: { */
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
pitivi_codecconfwindow_class_init (gpointer g_class, gpointer g_class_data)
{
  GObjectClass *gobject_class = G_OBJECT_CLASS (g_class);
  PitiviCodecConfWindowClass *klass = PITIVI_CODECCONFWINDOW_CLASS (g_class);

  parent_class = g_type_class_peek_parent (g_class);

  gobject_class->constructor = pitivi_codecconfwindow_constructor;
  gobject_class->dispose = pitivi_codecconfwindow_dispose;
  gobject_class->finalize = pitivi_codecconfwindow_finalize;

  gobject_class->set_property = pitivi_codecconfwindow_set_property;
  gobject_class->get_property = pitivi_codecconfwindow_get_property;

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
pitivi_codecconfwindow_get_type (void)
{
  static GType type = 0;
 
  if (type == 0)
    {
      static const GTypeInfo info = {
	sizeof (PitiviCodecConfWindowClass),
	NULL,			/* base_init */
	NULL,			/* base_finalize */
	pitivi_codecconfwindow_class_init,	/* class_init */
	NULL,			/* class_finalize */
	NULL,			/* class_data */
	sizeof (PitiviCodecConfWindow),
	0,			/* n_preallocs */
	pitivi_codecconfwindow_instance_init	/* instance_init */
      };
      type = g_type_register_static (GTK_TYPE_WINDOW,
				     "PitiviCodecConfWindowType", &info, 0);
    }

  return type;
}
