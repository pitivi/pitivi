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
#include "pitivi-projectwindows.h"

static     PitiviWindowsClass *parent_class;

enum {
  PROP_0,
  PROP_PROJECT
};

struct _PitiviProjectWindowsPrivate
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

static GObject *
pitivi_projectwindows_constructor (GType type,
			     guint n_construct_properties,
			     GObjectConstructParam * construct_properties)
{
  GObject *obj;
  /* Invoke parent constructor. */
  obj = (G_OBJECT_CLASS(parent_class))->constructor (type, n_construct_properties,
				   construct_properties);

  /* do stuff. */

  return obj;
}

static void
pitivi_projectwindows_instance_init (GTypeInstance * instance, gpointer g_class)
{
  PitiviProjectWindows *self = (PitiviProjectWindows *) instance;

  self->private = g_new0(PitiviProjectWindowsPrivate, 1);
  
  /* initialize all public and private members to reasonable default values. */ 
  
  self->private->dispose_has_run = FALSE;
  
  /* Do only initialisation here */
  /* The construction of the object should be done in the Constructor
     So that properties set at instanciation can be set */
}

static void
pitivi_projectwindows_dispose (GObject *object)
{
  PitiviProjectWindows	*self = PITIVI_PROJECTWINDOWS(object);

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
pitivi_projectwindows_finalize (GObject *object)
{
  PitiviProjectWindows	*self = PITIVI_PROJECTWINDOWS(object);

  /* 
   * Here, complete object destruction. 
   * You might not need to do much... 
   */

  g_free (self->private);
  G_OBJECT_CLASS (parent_class)->finalize (object);
}

static void
pitivi_projectwindows_set_property (GObject * object,
			      guint property_id,
			      const GValue * value, GParamSpec * pspec)
{
  PitiviProjectWindows *self = (PitiviProjectWindows *) object;

  switch (property_id)
    {
    case PROP_PROJECT:
      self->project = g_value_get_pointer(value);
      break;
    default:
      g_assert (FALSE);
      break;
    }
}

static void
pitivi_projectwindows_get_property (GObject * object,
			      guint property_id,
			      GValue * value, GParamSpec * pspec)
{
  PitiviProjectWindows *self = (PitiviProjectWindows *) object;

  switch (property_id)
    {
    case PROP_PROJECT:
      g_value_set_pointer (value, self->project);
      break;
    default:
      g_assert (FALSE);
      break;
    }
}

static void
pitivi_projectwindows_class_init (gpointer g_class, gpointer g_class_data)
{
  GObjectClass *gobject_class = G_OBJECT_CLASS (g_class);
  parent_class = g_type_class_peek_parent (g_class);

  gobject_class->constructor = pitivi_projectwindows_constructor;
  gobject_class->dispose = pitivi_projectwindows_dispose;
  gobject_class->finalize = pitivi_projectwindows_finalize;

  gobject_class->set_property = pitivi_projectwindows_set_property;
  gobject_class->get_property = pitivi_projectwindows_get_property;
  g_object_class_install_property (gobject_class,
                                   PROP_PROJECT,
                                   g_param_spec_pointer ("project",
							 "project",
							 "Pointer on the PitiviProject instance",
							 G_PARAM_WRITABLE | G_PARAM_CONSTRUCT_ONLY) );


}

GType
pitivi_projectwindows_get_type (void)
{
  static GType type = 0;
 
  if (type == 0)
    {
      static const GTypeInfo info = {
	sizeof (PitiviProjectWindowsClass),
	NULL,			/* base_init */
	NULL,			/* base_finalize */
	pitivi_projectwindows_class_init,	/* class_init */
	NULL,			/* class_finalize */
	NULL,			/* class_data */
	sizeof (PitiviProjectWindows),
	0,			/* n_preallocs */
	pitivi_projectwindows_instance_init	/* instance_init */
      };
      type = g_type_register_static (PITIVI_WINDOWS_TYPE,
				     "PitiviProjectWindowsType", &info, 0);
    }

  return type;
}
