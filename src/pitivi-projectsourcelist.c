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
  gboolean		dispose_has_run;
  GSList		*bin_tree;
};

/*
 * forward definitions
 */

/*
 * Insert "added-value" functions here
 */

PitiviSourceBin	*get_pitivisourcebin(PitiviProjectSourceList *self, gchar *treepath,
				     GSList **list, PitiviSourceBin **bin, gint *row)
{
  gchar			*tmp;
  gchar			*tmp2;
  gchar			*save;
  gint			i;

  tmp = g_strdup(treepath);
  
  save = tmp2 = tmp;

  *list = self->private->bin_tree;

  *bin = NULL;

  while (*tmp != 0)
    {
      if (*tmp == ':')
	{
	  *tmp = 0;
	  *row = atoi(tmp2);
	  for (i = 0; i < *row; i++)
	    *list = (*list)->next;
	  *bin = (*list)->data;
	  *list = (*bin)->child;
	  *tmp++;
	  tmp2 = tmp;
	}
      *tmp++;
    }

  *row = atoi(tmp2);

  for (i = 0; i < *row; i++)
    *list = (*list)->next;
  g_free(save);

  return (*list)->data;
}

void
pitivi_projectsourcelist_showfile(PitiviProjectSourceList *self,
				  gchar *treepath)
{
  PitiviSourceBin	*sourcebin;
  PitiviSourceBin	*bin;
  GSList		*list;
  GSList		*sourcelist;
  GSList		*childlist;
  gint			row;

  g_printf("== projectsourcelist showfile ==\n");

  sourcebin = get_pitivisourcebin(self, treepath, &list, &bin, &row);
  if (sourcebin == NULL)
    return;
  sourcelist = sourcebin->source;
  while (sourcelist != NULL)
    {
      g_printf("filename ==> %s\n", ((PitiviSourceFile*)sourcelist->data)->filename);
      g_printf("mediatype ==> %s\n", ((PitiviSourceFile*)sourcelist->data)->mediatype);
      g_printf("info video ==> %s\n", ((PitiviSourceFile*)sourcelist->data)->infovideo);
      g_printf("info audio ==> %s\n", ((PitiviSourceFile*)sourcelist->data)->infoaudio);
      g_printf("length ==> %lld\n", ((PitiviSourceFile*)sourcelist->data)->length);

      sourcelist = sourcelist->next;
    }
  childlist = sourcebin->child;
  while (childlist != NULL)
    {
      g_printf("folder ==> %s\n", ((PitiviSourceBin*)childlist->data)->bin_name);
      childlist = childlist->next;
    }
  g_printf("== end of projectsourcelist showfile ==\n");
}

gpointer
pitivi_projectsourcelist_get_folder_info(PitiviProjectSourceList *self,
				       gchar *treepath, guint folder_pos)
{
  PitiviSourceBin	*sourcebin;
  PitiviSourceBin	*bin;
  GSList		*childlist;
  GSList		*list;
  gint			row;

  sourcebin = get_pitivisourcebin(self, treepath, &list, &bin, &row);
  childlist = sourcebin->child;
  if (!childlist)
    return NULL;

  while (folder_pos--)
    {
      childlist = childlist->next;
      if (!childlist)
	return NULL;
    }
  return childlist->data; 
}

gpointer
pitivi_projectsourcelist_get_file_info(PitiviProjectSourceList *self,
				       gchar *treepath, guint next_file)
{
  PitiviSourceBin	*sourcebin;
  PitiviSourceBin	*bin;
  GSList		*sourcelist;
  GSList		*list;
  gint			row;

  sourcebin = get_pitivisourcebin(self, treepath, &list, &bin, &row);
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

void
pitivi_projectsourcelist_remove_folder_from_bin(PitiviProjectSourceList *self,
						gchar *treepath, guint folder_pos)
{
  PitiviSourceBin	*sourcebin;
  PitiviSourceBin	*bin;
  GSList		*childlist;
  GSList		*list;
  gpointer		data;
  gint			row;

  sourcebin = get_pitivisourcebin(self, treepath, &list, &bin, &row);
  childlist = sourcebin->child;

  data = pitivi_projectsourcelist_get_folder_info(self, treepath, folder_pos);

  g_printf("== removing %s from child list ==\n", ((PitiviSourceBin*)data)->bin_name);

  childlist = g_slist_remove(childlist, data);

  /* handle case the first folder is removed */
  sourcebin->child = childlist;

  g_free((PitiviSourceBin*)data);
}

void
pitivi_projectsourcelist_remove_file_from_bin(PitiviProjectSourceList *self,
					      gchar *treepath, guint file_pos)
{
  PitiviSourceBin	*sourcebin;
  PitiviSourceBin	*bin;
  GSList		*sourcelist;
  GSList		*list;
  gpointer		data;
  gint			row;

  sourcebin = get_pitivisourcebin(self, treepath, &list, &bin, &row);
  sourcelist = sourcebin->source;

  data = pitivi_projectsourcelist_get_file_info(self, treepath, file_pos);

  g_printf("== removing %s from source list ==\n", ((PitiviSourceFile*)data)->filename);

  sourcelist = g_slist_remove(sourcelist, data);
  
  /* handle case the first item is removed */
  sourcebin->source = sourcelist;

  g_object_unref(((PitiviSourceFile*)data)->pipeline);
  g_free((PitiviSourceFile*)data);
}


void
pitivi_projectsourcelist_remove_bin(PitiviProjectSourceList *self,
				    gchar *treepath)
{
  PitiviSourceBin *bin;
  GSList	*list;
  gpointer	data;
  gchar		*tmp;
  gchar		*tmp2;
  gchar		*save;
  gint		row;
  gint		i;


  data = get_pitivisourcebin(self, treepath, &list, &bin, &row);

  g_printf("removing %s from bin_tree\n", ((PitiviSourceBin*)data)->bin_name);

  if (bin == NULL)
    list = self->private->bin_tree;
  else
    list = bin->child;

  list = g_slist_remove(list, data);
  
  /* handle case the first item is removed */

  if (bin == NULL)
    self->private->bin_tree = list;
  else
    bin->child = list;
}

void
pitivi_projectsourcelist_set_bin_name(PitiviProjectSourceList *self,
				      gchar *treepath,
				      gchar *bin_name)
{
  PitiviSourceBin	*sourcebin;
  gint			row;

  sourcebin = get_pitivisourcebin(self, treepath, NULL, NULL, &row);
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

void
pitivi_projectsourcelist_add_folder_to_bin(PitiviProjectSourceList *self, 
					   gchar *treepath,
					   gchar *folder_name)
{
  PitiviSourceBin	*sourcebin;
  PitiviSourceBin	*child;
  PitiviSourceBin	*bin_tree;
  GSList		*bin;
  gint			row;

  sourcebin = get_pitivisourcebin(self, treepath, &bin, &bin_tree, &row);

  child = g_new0(PitiviSourceBin, 1);
  child->bin_name = g_strdup(folder_name);
  child->source = NULL;
  child->child = NULL;
  
  sourcebin->child = g_slist_append(sourcebin->child, child);
}

gboolean
pitivi_projectsourcelist_add_file_to_bin(PitiviProjectSourceList *self, 
					 gchar *treepath, gchar *filename,
					 gchar *mediatype, gchar *infovideo,
					 gchar *infoaudio, gint64 length,
					 GstElement *pipeline)
{
  PitiviSourceBin	*sourcebin;
  PitiviSourceBin	*bin;
  PitiviSourceFile	*sourcefile;
  GSList		*list;
  gint			row;

  sourcebin = get_pitivisourcebin(self, treepath, &list, &bin, &row);
  sourcefile = g_new0(PitiviSourceFile, 1);

  sourcefile->filename = g_strdup(filename);
  sourcefile->mediatype = g_strdup(mediatype);
  sourcefile->infovideo = g_strdup(infovideo);
  sourcefile->infoaudio = g_strdup(infoaudio);
  sourcefile->length = length;
  sourcefile->pipeline = pipeline;

  sourcebin->source = g_slist_append(sourcebin->source, sourcefile);
  
  return TRUE;
}

PitiviSourceFile*	
pitivi_projectsourcelist_get_sourcefile(PitiviProjectSourceList *self,
					gchar *treepath, gint file_pos)
{
  PitiviSourceBin	*sourcebin;
  PitiviSourceBin	*bin;
  PitiviSourceFile	*sourcefile;
  GSList		*list;
  gint			row;

  sourcebin = get_pitivisourcebin(self, treepath, &list, &bin, &row);
  
  sourcefile = (PitiviSourceFile*)pitivi_projectsourcelist_get_file_info(self,
									 treepath,
									 file_pos);

  return sourcefile;
}


void
pitivi_projectsourcelist_restore_thyself(PitiviProjectSourceList *SourceList, xmlNodePtr self)
{

}

/*
  pitivi_project_save_thyself

  Returns a pointer to the XMLDocument filled with the contents of the PitiviProject
*/

xmlNodePtr
pitivi_projectsourcelist_save_thyself(PitiviProjectSourceList *self, xmlNodePtr parent)
{
  xmlNodePtr	selfptr, msetptr, binptr;
  GSList	*sourcelist;
  GSList	*binlist;
  GSList	*folderlist;
  PitiviSourceBin	*sourcebin;
  PitiviSourceBin	*childbin;
  PitiviSourceFile	*sourcefile;
  

  selfptr = xmlNewChild (parent, NULL, "projectsourcelist", NULL);

  for (binlist = self->private->bin_tree; sourcelist; binlist = binlist->next) 
    {
      sourcebin = (PitiviSourceBin*) binlist->data;

      binptr = xmlNewChild (selfptr, NULL, "bin", NULL);
      xmlNewChild (binptr, NULL, "name", sourcebin->bin_name);
      
      
      /* list of source */
      for (sourcelist = sourcebin->source; sourcelist; sourcelist = sourcelist->next)
	{
	  msetptr = xmlNewChild(binptr, NULL, "file", NULL);
	  sourcefile = (PitiviSourceFile*)sourcelist->data;
	  xmlNewChild (msetptr, NULL, "filename", sourcefile->filename);
	}
      for (folderlist = sourcebin->child; folderlist; folderlist = folderlist->next)
	{
	  msetptr = xmlNewChild(binptr, NULL, "folder", NULL);
	  childbin = (PitiviSourceBin*)folderlist->data;
	  xmlNewChild (msetptr, NULL, "foldername", childbin->bin_name);
	}
    }


  return parent;
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
