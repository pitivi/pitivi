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
#include "pitivi-projectsourcelist.h"

struct _PitiviSourceBin
{
  gchar			*bin_name;
  GSList	       	*source;
  GSList		*child;
};

struct _PitiviProjectSourceListPrivate
{
  /* instance private members */
  gboolean	dispose_has_run;
  GSList		*bin_tree;
};

/*
 * forward definitions
 */

/*
 * Insert "added-value" functions here
 */

PitiviSourceBin	*get_pitivisourcebin(PitiviProjectSourceList *self, guint bin_pos)
{
  GSList		*bin_tree;

  bin_tree = self->private->bin_tree;
  while (bin_pos--)
    bin_tree = bin_tree->next;
  if (bin_tree)
    return (PitiviSourceBin*)bin_tree->data;
  else
    return NULL;
}

void
pitivi_projectsourcelist_showfile(PitiviProjectSourceList *self,
				  guint bin_pos)
{
  GSList	*sourcelist;
  PitiviSourceBin *sourcebin;

  sourcebin = get_pitivisourcebin(self, bin_pos);
  if (sourcebin == NULL)
    return;
  sourcelist = sourcebin->source;
  while (sourcelist != NULL)
    {
      g_printf("file ==> %s\n", sourcelist->data);
      sourcelist = sourcelist->next;
    }
}

gchar *
pitivi_projectsourcelist_get_file_info(PitiviProjectSourceList *self,
				       guint bin_pos, guint next_file)
{
  PitiviSourceBin	*sourcebin;
  GSList		*sourcelist;

  sourcebin = get_pitivisourcebin(self, bin_pos);
  sourcelist = sourcebin->source;
  if (!sourcelist)
    return NULL;

  while (next_file--)
    {
      sourcelist = sourcelist->next;
      if (!sourcelist)
	return NULL;
    }
  return sourcelist->data; 
}

gboolean
pitivi_projectsourcelist_add_file_to_bin(PitiviProjectSourceList *self, 
					 guint bin_pos, 
					 gchar *source)
{
  PitiviSourceBin	*sourcebin;

  sourcebin = get_pitivisourcebin(self, bin_pos);
  if (sourcebin)
    {
      sourcebin->source = g_slist_append(sourcebin->source, source);
      return TRUE;
    }
  else
    {
      g_printf("Unable to add file no bin found\n");
      return FALSE;
    }
}

void
pitivi_projectsourcelist_set_bin_name(PitiviProjectSourceList *self,
				      guint bin_pos,
				      gchar *bin_name)
{
  PitiviSourceBin	*sourcebin;

  sourcebin = get_pitivisourcebin(self, bin_pos);
  sourcebin->bin_name = g_strdup(bin_name);
}

void
pitivi_projectsourcelist_new_bin(PitiviProjectSourceList *self,
				 gchar *bin_name)
{
  PitiviSourceBin	*sourcebin;
  
  sourcebin = g_new0(PitiviSourceBin, 1);
  sourcebin->bin_name = g_strdup(bin_name);
  sourcebin->source = NULL;
  sourcebin->child = NULL;
  self->private->bin_tree = g_slist_append(self->private->bin_tree, sourcebin);
}

/* pas au point */
void
pitivi_projectsourcelist_add_child(PitiviProjectSourceList *self, 
				   guint bin_pos, 
				   gchar *child_name)
{
  PitiviSourceBin	*sourcebin;
  PitiviSourceBin	child;

  sourcebin = get_pitivisourcebin(self, bin_pos);

  child.bin_name = g_strdup(child_name);
  child.source = NULL;
  child.child = NULL;
  
  sourcebin->child = g_slist_append(sourcebin->child, &child);
}
					  
PitiviProjectSourceList *
pitivi_projectsourcelist_new(void)
{
  PitiviProjectSourceList	*projectsourcelist;

  projectsourcelist = (PitiviProjectSourceList *) g_object_new(PITIVI_PROJECTSOURCELIST_TYPE, NULL);
  g_assert(projectsourcelist != NULL);
  return projectsourcelist;
}

static GObject *
pitivi_projectsourcelist_constructor (GType type,
			     guint n_construct_properties,
			     GObjectConstructParam * construct_properties)
{
  GObject *obj;
  {
    /* Invoke parent constructor. */
    PitiviProjectSourceListClass *klass;
    GObjectClass *parent_class;
    klass = PITIVI_PROJECTSOURCELIST_CLASS (g_type_class_peek (PITIVI_PROJECTSOURCELIST_TYPE));
    parent_class = G_OBJECT_CLASS (g_type_class_peek_parent (klass));
    obj = parent_class->constructor (type, n_construct_properties,
				     construct_properties);
  }

  /* do stuff. */

  return obj;
}

static void
pitivi_projectsourcelist_instance_init (GTypeInstance * instance, gpointer g_class)
{
  PitiviProjectSourceList *self = (PitiviProjectSourceList *) instance;

  self->private = g_new0(PitiviProjectSourceListPrivate, 1);
  
  /* initialize all public and private members to reasonable default values. */ 
  
  self->private->dispose_has_run = FALSE;
  
  /* If you need specific consruction properties to complete initialization, 
   * delay initialization completion until the property is set. 
   */
  self->private->bin_tree = NULL;
}

static void
pitivi_projectsourcelist_dispose (GObject *object)
{
  PitiviProjectSourceList	*self = PITIVI_PROJECTSOURCELIST(object);

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
pitivi_projectsourcelist_finalize (GObject *object)
{
  PitiviProjectSourceList	*self = PITIVI_PROJECTSOURCELIST(object);

  /* 
   * Here, complete object destruction. 
   * You might not need to do much... 
   */

  g_free (self->private);
}

static void
pitivi_projectsourcelist_set_property (GObject * object,
			      guint property_id,
			      const GValue * value, GParamSpec * pspec)
{
  PitiviProjectSourceList *self = (PitiviProjectSourceList *) object;

  switch (property_id)
    {
      /*   case PITIVI_PROJECTSOURCELIST_PROPERTY: { */
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
pitivi_projectsourcelist_get_property (GObject * object,
			      guint property_id,
			      GValue * value, GParamSpec * pspec)
{
  PitiviProjectSourceList *self = (PitiviProjectSourceList *) object;

  switch (property_id)
    {
      /*  case PITIVI_PROJECTSOURCELIST_PROPERTY: { */
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
pitivi_projectsourcelist_class_init (gpointer g_class, gpointer g_class_data)
{
  GObjectClass *gobject_class = G_OBJECT_CLASS (g_class);
  PitiviProjectSourceListClass *klass = PITIVI_PROJECTSOURCELIST_CLASS (g_class);

  gobject_class->constructor = pitivi_projectsourcelist_constructor;
  gobject_class->dispose = pitivi_projectsourcelist_dispose;
  gobject_class->finalize = pitivi_projectsourcelist_finalize;

  gobject_class->set_property = pitivi_projectsourcelist_set_property;
  gobject_class->get_property = pitivi_projectsourcelist_get_property;

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
pitivi_projectsourcelist_get_type (void)
{
  static GType type = 0;
 
  if (type == 0)
    {
      static const GTypeInfo info = {
	sizeof (PitiviProjectSourceListClass),
	NULL,			/* base_init */
	NULL,			/* base_finalize */
	pitivi_projectsourcelist_class_init,	/* class_init */
	NULL,			/* class_finalize */
	NULL,			/* class_data */
	sizeof (PitiviProjectSourceList),
	0,			/* n_preallocs */
	pitivi_projectsourcelist_instance_init	/* instance_init */
      };
      type = g_type_register_static (G_TYPE_OBJECT,
				     "PitiviProjectSourceListType", &info, 0);
    }

  return type;
}
