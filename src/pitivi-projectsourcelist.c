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

typedef struct _PitiviRestore
{
  gchar			*filename;
  GtkWidget		*entry;
}	PitiviRestore;
/*
 * forward definitions
 */
void			restore_moved_sourcefile(GtkWidget *button, PitiviRestore *restore);
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

PitiviSourceBin*
pitivi_projectsourcelist_get_child_by_name(PitiviSourceBin *bin, gchar *name)
{
  PitiviSourceBin	*child;
  GSList		*childlist;

  childlist = bin->child;
  while (childlist)
    {
      child = (PitiviSourceBin*)(childlist->data);
      if (!strcmp(child->bin_name, name))
	return child;
      child = pitivi_projectsourcelist_get_child_by_name(child, name);
      if (child)
	return child;
      childlist = childlist->next;
    }
  return NULL;
}

PitiviSourceBin*
pitivi_projectsourcelist_get_bin_by_name(PitiviProjectSourceList *self,
					 gchar *name)
{
  PitiviSourceBin	*bin;
  GSList		*bin_list;


  bin_list = self->private->bin_tree;

  while (bin_list)
    {
      bin = (PitiviSourceBin*)(bin_list->data);
      if (!strcmp(bin->bin_name, name))
	return bin;
      bin = pitivi_projectsourcelist_get_child_by_name(bin, name);
      if (bin)
	return bin;
      bin_list = bin_list->next;
    }

  return NULL;
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
      g_printf("length ==> %lld\n", ((signed long long int) ((PitiviSourceFile*)sourcelist->data)->length));

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
  PitiviSourceFile	*sf;
  GSList		*list;
  gpointer		data;
  gint			row;
  
  sourcebin = get_pitivisourcebin(self, treepath, &list, &bin, &row);

  data = pitivi_projectsourcelist_get_file_info(self, treepath, file_pos);

  sf = (PitiviSourceFile*)data;

  g_printf("== removing %s from source list ==\n", ((PitiviSourceFile*)data)->filename);
  
  sourcebin->source = g_slist_remove(sourcebin->source, data);
}


void
pitivi_projectsourcelist_remove_bin(PitiviProjectSourceList *self,
				    gchar *treepath)
{
  PitiviSourceBin *bin;
  GSList	*list;
  gpointer	data;
  gint		row;


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

PitiviSourceBin*
pitivi_projectsourcelist_new_bin(PitiviProjectSourceList *self,
				 gchar *bin_name)
{
  PitiviSourceBin	*sourcebin;
  
  sourcebin = g_new0(PitiviSourceBin, 1);
  sourcebin->bin_name = g_strdup(bin_name);
  sourcebin->source = NULL;
  sourcebin->child = NULL;
  self->private->bin_tree = g_slist_append(self->private->bin_tree, sourcebin);

  return sourcebin;
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

void
pitivi_projectsourcelist_set_file_property_by_name(PitiviProjectSourceList *self,
						   gchar *parent_name,
						   gchar *filename,
						   gchar *mediatype,
						   gchar *infovideo,
						   gchar *infoaudio,
						   gint64 length,
						   GstElement *pipeline)
{
  PitiviSourceBin	*bin;
  PitiviSourceFile	*sourcefile;

  bin = pitivi_projectsourcelist_get_bin_by_name(self, parent_name);

  sourcefile = pitivi_projectsourcelist_get_sourcefile_by_name(bin, filename);

  if (!sourcefile)
    return;
  
/*   g_printf("filename in projectsourcelist ==> %s\n", sourcefile->filename); */
  sourcefile->mediatype = g_strdup(mediatype);
  sourcefile->infovideo = g_strdup(infovideo);
  sourcefile->infoaudio = g_strdup(infoaudio);
  sourcefile->length = length;
  sourcefile->pipeline = pipeline;
}

gboolean
pitivi_projectsourcelist_add_file_to_bin (PitiviProjectSourceList *self, 
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
pitivi_projectsourcelist_get_sourcefile_by_name(PitiviSourceBin *bin, 
						gchar *filename)
{
  PitiviSourceFile	*sourcefile;
  GSList		*sourcelist;

  sourcelist = bin->source;
  while (sourcelist)
    {
      sourcefile = (PitiviSourceFile*)(sourcelist->data);
      if (!strcmp(sourcefile->filename, filename))
	return sourcefile;
      sourcelist = sourcelist->next;
    }
  return NULL;
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
  g_printf ("----------------------------treepath:%s----------------------------------------------\n", treepath);
  sourcefile = (PitiviSourceFile*)pitivi_projectsourcelist_get_file_info(self,
									 treepath,
									 file_pos);
  if (!sourcefile)
    g_printf ("Problem getting the sourcefile !!!!!!\n");
  return sourcefile;
}

void
restore_moved_sourcefile(GtkWidget *button, PitiviRestore *restore)
{
  GtkWidget	*dialog;
  gchar		*filename;

  dialog = gtk_file_chooser_dialog_new ("Restore your source file(s)",
					NULL, GTK_FILE_CHOOSER_ACTION_SAVE,
					GTK_STOCK_CANCEL, GTK_RESPONSE_CANCEL,
					GTK_STOCK_SAVE, GTK_RESPONSE_ACCEPT,
					NULL);
  if (gtk_dialog_run (GTK_DIALOG (dialog)) == GTK_RESPONSE_ACCEPT) {
    filename = gtk_file_chooser_get_filename (GTK_FILE_CHOOSER (dialog));    
    gtk_entry_set_text (GTK_ENTRY (restore->entry), filename);
  }
  gtk_widget_destroy (dialog);
}

void	
pitivi_projectsourcelist_add_source_from_xml(PitiviSourceBin *sourcebin,
					     G_CONST_RETURN gchar *filename)
{
  PitiviSourceFile	*sourcefile;
  PitiviRestore		*restore;
  GtkWidget		*Dialog;
  GtkWidget		*dial_cancel;  
  GtkWidget		*dial_warning_text;
  GtkWidget		*dial_new_url;
  GtkWidget		*select_but;
  GtkWidget		*select_hbox;
  GtkWidget		*filename_to_restore;
  const gchar		*name;
  G_CONST_RETURN gchar	*select_filename;
  gint			result;

  dial_cancel = gtk_message_dialog_new (NULL,
					GTK_DIALOG_DESTROY_WITH_PARENT,
					GTK_MESSAGE_WARNING,
					GTK_BUTTONS_CLOSE,
					"You don't have restore all you source files.\nMaybe you should have some troubles.\n");
 
  sourcefile = g_new0(PitiviSourceFile, 1);
  restore = g_new0(PitiviRestore, 1);
  restore->entry = gtk_entry_new();
  if (g_file_test(filename, G_FILE_TEST_EXISTS))
    {
      sourcefile->filename = g_strdup(filename);
      sourcefile->mediatype = "";
      sourcefile->infovideo = "";
      sourcefile->infoaudio = "";
      sourcefile->length = 0;
      sourcefile->pipeline = NULL;
      sourcebin->source = g_slist_append(sourcebin->source, sourcefile);
    }
  else
    {
      Dialog = gtk_dialog_new ();
      name = g_strdup(filename);
      filename_to_restore =  gtk_label_new(name);
      dial_warning_text = gtk_label_new("The source file(s) have moved since the last time\nPlease enter a new url...\nPlease restore this file : ");
      dial_new_url = restore->entry;
      select_but = gtk_toggle_button_new_with_label ("Select");
      g_signal_connect (G_OBJECT (select_but), "toggled",
			G_CALLBACK (restore_moved_sourcefile), restore);
      select_hbox = gtk_hbox_new(FALSE, 0);

      gtk_box_pack_start(GTK_BOX(select_hbox), GTK_WIDGET(dial_new_url), TRUE, TRUE, 5);
      gtk_box_pack_start(GTK_BOX(select_hbox), GTK_WIDGET(select_but), TRUE, TRUE, 20);

      select_but = gtk_toggle_button_new_with_label ("Select");
      g_signal_connect (G_OBJECT (select_but), "toggled",
			G_CALLBACK (restore_moved_sourcefile), restore);
      gtk_window_set_title (GTK_WINDOW (Dialog), "Warning !!!");

      gtk_container_add (GTK_CONTAINER (GTK_DIALOG(Dialog)->vbox),
			 GTK_WIDGET(dial_warning_text));
      gtk_container_add (GTK_CONTAINER (GTK_DIALOG(Dialog)->vbox),
			 GTK_WIDGET(filename_to_restore));
      gtk_container_add (GTK_CONTAINER (GTK_DIALOG(Dialog)->vbox),
			 GTK_WIDGET(select_hbox));
      gtk_dialog_add_buttons (GTK_DIALOG(Dialog),
			      GTK_STOCK_OK,
			      GTK_RESPONSE_ACCEPT,
			      GTK_STOCK_CANCEL,
			      GTK_RESPONSE_REJECT,
			      NULL);
      gtk_widget_show_all (GTK_WIDGET (Dialog));
      result  = gtk_dialog_run (GTK_DIALOG (Dialog));

      select_filename = gtk_entry_get_text(GTK_ENTRY(restore->entry));

      switch (result)
	{
	case GTK_RESPONSE_ACCEPT:
	  /* g_print ("ACCEPT\nLe nouveau fichier est : %s\n", select_filename); */
	  pitivi_projectsourcelist_add_source_from_xml(sourcebin, select_filename);
	  break;
	default:
	  gtk_dialog_run (GTK_DIALOG (dial_cancel));
	  gtk_widget_destroy (dial_cancel);
	  break;
	}
      gtk_widget_destroy (Dialog);
    }
}


PitiviSourceBin*
pitivi_projectsourcelist_add_folder_from_xml(PitiviSourceBin *sourcebin,
					      gchar *foldername)
{
  PitiviSourceBin	*child;

  child = g_new0(PitiviSourceBin, 1);
  child->bin_name = g_strdup(foldername);
  child->source = NULL;
  child->child = NULL;
  
  sourcebin->child = g_slist_append(sourcebin->child, child);

  return child;
}

void
pitivi_projectsourcelist_restore_in_recurse_folder(PitiviSourceBin *bin, xmlNodePtr self)
{
  xmlNodePtr	children;
  PitiviSourceBin	*folder = NULL;

  if (!g_ascii_strcasecmp("file", self->name))
    {
      for (children = self->xmlChildrenNode; children; children = children->next)
	{
	  if (!strcmp("filename", children->name))
	    pitivi_projectsourcelist_add_source_from_xml(bin, xmlNodeGetContent(children));
	}
    }
  if (!g_ascii_strcasecmp("folder", self->name))
    {
      for (children = self->xmlChildrenNode; children; children = children->next)
	{
	  if (!strcmp("foldername", children->name))
	    folder = pitivi_projectsourcelist_add_folder_from_xml(bin, xmlNodeGetContent(children));
	  pitivi_projectsourcelist_restore_in_recurse_folder(folder, children);
	}
    }
}

void
pitivi_projectsourcelist_restore_thyself(PitiviProjectSourceList *tofill, xmlNodePtr self)
{
  xmlNodePtr	children, little;
  PitiviSourceBin	*bin = NULL;

  for (children = self->xmlChildrenNode; children; children = children->next) 
    {
      if (!strcmp("bin", children->name))
	for (little = children->xmlChildrenNode; little; little = little->next)
	  {
	    if (!strcmp("name", little->name))
	      bin = pitivi_projectsourcelist_new_bin(tofill, xmlNodeGetContent(little));
	    pitivi_projectsourcelist_restore_in_recurse_folder(bin, little);
	    while (gtk_events_pending())
	      gtk_main_iteration();
	  }
    }
/*   pitivi_projectsourcelist_showfile(tofill, "0"); */
}


void	pitivi_projectsourcelist_recurse_into_folder(PitiviSourceBin *sourcebin,
						     xmlNodePtr binptr)
{
  xmlNodePtr	 msetptr;
  GSList		*folderlist;
  GSList		*sourcelist;
  PitiviSourceFile	*sourcefile;
  PitiviSourceBin	*childbin;

  /* list of source */
  for (sourcelist = sourcebin->source; sourcelist; sourcelist = sourcelist->next)
    {
      msetptr = xmlNewChild(binptr, NULL, "file", NULL);
      sourcefile = (PitiviSourceFile*)sourcelist->data;
      xmlNewChild (msetptr, NULL, "filename", sourcefile->filename);
    }
  /* list of folder */
  for (folderlist = sourcebin->child; folderlist; folderlist = folderlist->next)
    {
      childbin = (PitiviSourceBin*)folderlist->data;
      msetptr = xmlNewChild(binptr, NULL, "folder", NULL);
      xmlNewChild (msetptr, NULL, "foldername", childbin->bin_name);
      pitivi_projectsourcelist_recurse_into_folder(childbin, msetptr);
    }
}

/*
  pitivi_project_save_thyself

  Returns a pointer to the XMLDocument filled with the contents of the PitiviProject
*/

xmlNodePtr
pitivi_projectsourcelist_save_thyself(PitiviProjectSourceList *self, xmlNodePtr parent)
{
  xmlNodePtr	selfptr,binptr;
  GSList	*binlist;
  PitiviSourceBin	*sourcebin;
  

  selfptr = xmlNewChild (parent, NULL, "projectsourcelist", NULL);

  for (binlist = self->private->bin_tree; binlist; binlist = binlist->next) 
    {
      sourcebin = (PitiviSourceBin*) binlist->data;

      binptr = xmlNewChild (selfptr, NULL, "bin", NULL);
      xmlNewChild (binptr, NULL, "name", sourcebin->bin_name);
      
      pitivi_projectsourcelist_recurse_into_folder(sourcebin, binptr); 
    }


  return parent;
}

GSList	*pitivi_projectsourcelist_get_file_list(PitiviProjectSourceList *self,
						gchar *parent_name)
{
  PitiviSourceBin *sourcebin;
  PitiviSourceFile *sourcefile;
  GSList	*sourcelist;
  GSList	*list;

  list = NULL;

  sourcebin = pitivi_projectsourcelist_get_bin_by_name(self, parent_name);
  
  if (!sourcebin)
    return list;

  sourcelist = sourcebin->source;

  while (sourcelist)
    {
      sourcefile = (PitiviSourceFile*)(sourcelist->data);
      list = g_slist_append(list, sourcefile->filename);
      sourcelist = sourcelist->next;
    }
  return list;
}

GSList*
pitivi_projectsourcelist_get_folder_list(PitiviProjectSourceList *self,
					 gchar *parent_name)
{
  PitiviSourceBin	*sourcebin;
  PitiviSourceBin	*childbin;
  GSList		*childlist;
  GSList		*list;

  list = NULL;
  sourcebin = pitivi_projectsourcelist_get_bin_by_name(self, parent_name);

  childlist = sourcebin->child;

  while (childlist)
    {
      childbin = (PitiviSourceBin*)(childlist->data);
      list = g_slist_append(list, childbin->bin_name);
      childlist = childlist->next;
    }
  return list;
}

GSList	*pitivi_projectsourcelist_get_bin_list(PitiviProjectSourceList *self)
{
  PitiviSourceBin *sourcebin;
  GSList	*bin_tree;
  GSList	*list;
  
  list = NULL;
  bin_tree = self->private->bin_tree;
  while (bin_tree)
    {
      sourcebin = (PitiviSourceBin*)(bin_tree->data);
      list = g_slist_append(list, sourcebin->bin_name);
      bin_tree = bin_tree->next;
    }

  return list;
}

gboolean
pitivi_projectsourcelist_test_bin_tree(PitiviProjectSourceList *self)
{
  if (self->private->bin_tree)
    return TRUE;
  return FALSE;
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
}

static void
pitivi_projectsourcelist_finalize (GObject *object)
{
  PitiviProjectSourceList	*self = PITIVI_PROJECTSOURCELIST(object);
  g_slist_free ( self->private->bin_tree );
  g_free (self->private);
}

static void
pitivi_projectsourcelist_class_init (gpointer g_class, gpointer g_class_data)
{
  GObjectClass *gobject_class = G_OBJECT_CLASS (g_class);
  
  gobject_class->constructor = pitivi_projectsourcelist_constructor;
  gobject_class->dispose = pitivi_projectsourcelist_dispose;
  gobject_class->finalize = pitivi_projectsourcelist_finalize;
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
