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

#include <sys/types.h>
#include <sys/stat.h>
#include <dirent.h>
#include <unistd.h>
#include <gtk/gtk.h>
#include <gst/gst.h>
#include "pitivi.h"
#include "pitivi-sourcelistwindow.h"
#include "pitivi-projectsourcelist.h"
#include "pitivi-timelinewindow.h"
#include "pitivi-settings.h"
#include "pitivi-stockicons.h"
#include "pitivi-dragdrop.h"
#include "pitivi-mainapp.h"
#include "pitivi-viewerwindow.h"
#include "pitivi-menu.h"
#include "pitivi-debug.h"
#include "pitivi-lplayerwindow.h"
/*#include "pitivi-progressbar.h"*/

static	GdkPixbuf *window_icon = NULL;
static PitiviProjectWindowsClass *parent_class = NULL;

struct _PitiviListStore
{
  GtkListStore	*liststore;
  GSList	*child;
};

struct _PitiviListElm
{
  gchar	*name;
  gchar	*type;	// could be "audio", "video", "none"
  gchar	*category;	// could be "filereader", "demuxer", "parser", etc...
};

struct _PitiviSourceListWindowPrivate
{
  /* instance private members */
  gboolean	dispose_has_run;
  GtkWidget	*hpaned;
  GtkWidget	*selectfile;
  GtkWidget	*selectfolder;
  GtkWidget	*treeview;
  GtkWidget	*listview;
  GtkWidget	*listmenu;
  GtkWidget	*treemenu;
  GtkWidget	*timelinewin;
  GSList	*liststore;
  GtkTreeStore	*treestore;
  guint		nbrchutier;

  /* Property of the media */
  
  gchar		*treepath;
  gchar		*listpath;

  gchar		*filepath;
  gchar		*folderpath;
  
  /* Signals variable */
  guint		newfile_signal_id;
  guint		newfolder_signal_id;

  /* drag'n'drop variables */
  
  PitiviSourceFile *dndsf;
  gchar		*dndtreepath;
  gint		 dndfilepos;

  /* Progress bar */
  
  /*  PitiviProgressBar *bar; */
};

/*
 * forward definitions
 */

void		OnTimelineFirstInsert (gpointer data, gint action, GtkWidget *widget);
void		OnNewBin(gpointer data, gint action, GtkWidget *widget);
void		OnImportFile(gpointer data, gint action, GtkWidget *widget);
void		OnImportFolder(gpointer data, gint action, GtkWidget *widget);
void		OnRemoveItem(gpointer data, gint action, GtkWidget *widget);
void		OnRemoveBin(gpointer data, gint action, GtkWidget *widget);
void		OnImportProject(void);
void		OnFind(void);
void		OnOptionProject(void);
void		new_file(GtkWidget *widget, gpointer data);
gboolean	my_popup_handler(gpointer data, GdkEvent *event, gpointer userdata);
gboolean	on_row_selected(GtkTreeView *view, GtkTreeModel *model,
				GtkTreePath *path, gboolean path_current, 
				gpointer user_data);

void		on_row_activated (GtkTreeView        *treeview,
				  GtkTreePath        *path,
				  GtkTreeViewColumn  *col,
				  gpointer            userdata);
gint		OnSelectItem(PitiviSourceListWindow *self, GtkTreeIter *iter,
			     GtkListStore **liststore, void **sMediaType, 
			     guint type, gint *item_select, gint *folder_select);
PitiviSourceFile *pitivi_sourcelistwindow_get_file(PitiviSourceListWindow *self);

enum
  {
    BMP_COLUMN,
    TEXT_TREECOLUMN,
    N_TREECOLUMN
  };

enum
  {
    BMP_LISTCOLUMN1,
    TEXT_LISTCOLUMN2,
    TEXT_LISTCOLUMN3,
    TEXT_LISTCOLUMN4,
    TEXT_LISTCOLUMN5,
    TEXT_LISTCOLUMN6,
    POINTER_LISTCOLUMN7,
    N_LISTCOLOUMN
  };

enum
  {
    FILEIMPORT_SIGNAL,
    FOLDERIMPORT_SIGNAL,
    LAST_SIGNAL
  };

static guint pitivi_sourcelistwindow_signal[LAST_SIGNAL] = { 0 };

/* static gint projectview_signals[LAST_SIGNAL] = {0}; */

static GtkItemFactoryEntry	TreePopup[] = {
  {"/New bin...", NULL, OnNewBin, 1, "<Item>", NULL},
  {"/Import", NULL, NULL, 0, "<Branch>", NULL},
  {"/Import/File", NULL, OnImportFile, 1, "<Item>", NULL},
  {"/Import/Folder", NULL, OnImportFolder, 1, "<Item>", NULL}
/*   {"/Import/Project", NULL, OnImportProject, 0, "<Item>", NULL}, */
/*   {"/Sep1", NULL, NULL, 0, "<Separator>"},  */
/*   {"/Find...", NULL, OnFind, 0, "<Item>", NULL}, */
/*   {"/Sep2", NULL, NULL, 0, "<Separator>"}, */
/*   {"/Project Window Options...", NULL, OnOptionProject, 0, "<Item>", NULL} */
};

static gint	iNbTreePopup = sizeof(TreePopup)/sizeof(TreePopup[0]);

static GtkItemFactoryEntry	ListPopup[] = {
  {"/New", NULL, NULL, 0, "<Branch>", NULL},
  {"/New/Bin...", NULL, OnNewBin, 1, "<Item>", NULL},
/*   {"/New/Storyboard", NULL, NULL, 0, "<Item>", NULL}, */
/*   {"/New/Sep1", NULL, NULL, 0, "<Separator>"}, */
/*   {"/New/Title", NULL, NULL, 0, "<Item>", NULL}, */
/*   {"/New/Sep2", NULL, NULL, 0, "<Separator>"}, */
/*   {"/New/Offline file", NULL, NULL, 0, "<Item>", NULL}, */
  {"/Import", NULL, NULL, 0, "<Branch>", NULL},
  {"/Import/File", NULL, OnImportFile, 1, "<Item>", NULL},
  {"/Import/Folder", NULL, OnImportFolder, 1, "<Item>", NULL},
/*   {"/Import/Project", NULL, NULL, 0, "<Item>", NULL}, */
  {"/Sep3", NULL, NULL, 0, "<Separator>"},
  {"/Remove Unused Clips", NULL, NULL, 0, "<Item>", NULL}
/*   {"/Replace Clips...", NULL, NULL, 0, "<Item>", NULL}, */
/*   {"/Sep4", NULL, NULL, 0, "<Separator>"}, */
/*   {"/Automate to Timeline", NULL, NULL, 0, "<Item>", NULL}, */
/*   {"/Find...", NULL, NULL, 0, "<Item>", NULL}, */
/*   {"/Sep5", NULL, NULL, 0, "<Separator>"}, */
/*   {"/Project Window Options...", NULL, NULL, 0, "<Item>", NULL} */
};

static gint	iNbListPopup = sizeof(ListPopup)/sizeof(ListPopup[0]);

static GtkItemFactoryEntry	ItemPopup[] = {
  {"/Cut", NULL, NULL, 0, "<Item>", NULL},
  {"/Copy", NULL, NULL, 0, "<Item>", NULL},
  {"/Clear", NULL, OnRemoveItem, 1, "<Item>", NULL},
  {"/Sep1", NULL, NULL, 0, "<Separator>"},
  {"/Properties", NULL, NULL, 0, "<Item>", NULL}
/*   {"/Set Clip Name Alias", NULL, NULL, 0, "<Item>", NULL}, */
/*   {"/Sep2", NULL, NULL, 0, "<Separator>"}, */
/*   {"/Insert in TimeLine", NULL, OnTimelineFirstInsert, 1, "<Item>", NULL}, */
/*   {"/Insert at Edit Line", NULL, OnNewBin, 1, "<Item>", NULL}, */
/*   {"/Overlay at Edit Line", NULL, NULL, 0, "<Item>", NULL}, */
/*   {"/Sep3", NULL, NULL, 0, "<Separator>"}, */
/*   {"/Duration...", NULL, NULL, 0, "<Item>", NULL}, */
/*   {"/Speed...", NULL, NULL, 0, "<Item>", NULL}, */
/*   {"/Sep4", NULL, NULL, 0, "<Separator>"}, */
/*   {"/Open in Clip Window", NULL, NULL, 0, "<Item>", NULL}, */
/*   {"/Duplicate Clip...", NULL, NULL, 0, "<Item>", NULL}, */
/*   {"/Sep5", NULL, NULL, 0, "<Separator>"}, */
/*   {"/Project Windows Options...", NULL, NULL, 0, "<Item>"} */
};

static gint	iNbItemPopup = sizeof(ItemPopup)/sizeof(ItemPopup[0]);

static GtkItemFactoryEntry	BinPopup[] = {
  {"/New", NULL, NULL, 0, "<Branch>", NULL},
  {"/New/Bin...", NULL, OnNewBin, 1, "<Item>", NULL},
/*   {"/New/Storyboard", NULL, NULL, 0, "<Item>", NULL}, */
/*   {"/New/Sep1", NULL, NULL, 0, "<Separator>"}, */
/*   {"/New/Title", NULL, NULL, 0, "<Item>", NULL}, */
  {"/Remove", NULL, OnRemoveBin, 1, "<Item>", NULL}
};

static gint	iNbBinPopup = sizeof(BinPopup)/sizeof(BinPopup[0]);

/*
 * insert "added-value" functions here
 */

static GtkTargetEntry TargetEntries[] =
{
  { "pitivi/sourcefile", GTK_TARGET_SAME_APP, DND_TARGET_SOURCEFILEWIN }
};

static gint iNbTargetEntries = G_N_ELEMENTS (TargetEntries);

gint	get_selected_row(gchar *path, gint *depth)
{
  gchar	*tmp;
  gchar *tmp2;
 
 *depth = 0;
  tmp = tmp2 = path;
 
  while (*tmp != 0)
    {
      if (*tmp == ':')
	{
	  tmp2 = tmp;
	  tmp2++;
	  *depth++;
	}
      tmp++;
    }
/*   g_printf("tmp2 ==> %s\n", tmp2); */
/*   g_printf("path ==> %s\n", path); */
  return (atoi(tmp2));
}

void	add_liststore_for_bin(PitiviSourceListWindow *self, 
			      GtkListStore *liststore)
{
  PitiviListStore *pitiviliststore;
  PitiviListStore *new;
  GSList	*list;
  gchar		*tmp;
  gchar		*tmp2;
  gchar		*save;
  guint		row;
  gint		i;

  tmp = g_strdup(self->private->treepath);

  save = tmp2 = tmp;

  list = self->private->liststore;

  pitiviliststore = NULL;
  
  while (*tmp != 0)
    {
      if (*tmp == ':')
	{
	  *tmp = 0;
	  row = atoi(tmp2);
	  for (i = 0; i < row; i++)
	    list = list->next;
	  pitiviliststore = (PitiviListStore*)list->data;
	  list = pitiviliststore->child;
	  *tmp++;
	  tmp2 = tmp;
	}
      *tmp++;
    }

  new = g_new0(PitiviListStore, 1);
  new->liststore = liststore;
  new->child = NULL;
  list = g_slist_append(list, new);

  /* need to link the first element to the list */
  if (self->private->liststore == NULL)
    self->private->liststore = list;

  if (pitiviliststore != NULL)
    {
      if (pitiviliststore->child == NULL)
	pitiviliststore->child = list;
    }
  g_free(save);
}

GtkListStore	*get_liststore_for_bin(PitiviSourceListWindow *self,
				       guint bin_pos)
{
  PitiviListStore *pitiviliststore;
  GSList	*list;
  gchar		*tmp;
  gchar		*tmp2;
  gchar		*save;
  guint		row;
  gint		i;

  list = self->private->liststore;
  
  tmp = g_strdup(self->private->treepath);
  
  save = tmp2 = tmp;

  pitiviliststore = NULL;
  
  while (*tmp != 0)
    {
      if (*tmp == ':')
	{
	  *tmp = 0;
	  row = atoi(tmp2);
	  for (i = 0; i < row; i++)
	    list = list->next;
	  pitiviliststore = (PitiviListStore*)list->data;
	  list = pitiviliststore->child;
	  *tmp++;
	  tmp2 = tmp;
	}
      *tmp++;
    }

  row = atoi(tmp2);

  for (i = 0; i < row; i++)
    list = list->next;
  
  pitiviliststore = (PitiviListStore*)list->data;

  g_free(save);

  return pitiviliststore->liststore;
}

gpointer	get_data_for_bin(PitiviSourceListWindow *self)
{
  PitiviListStore *pitiviliststore;
  GSList	*list;
  gchar		*tmp;
  gchar		*tmp2;
  gchar		*save;
  guint		row;
  gint		i;

  list = self->private->liststore;

  tmp = g_strdup(self->private->treepath);
  
  save = tmp2 = tmp;

  while (*tmp != 0)
    {
      if (*tmp == ':')
	{
	  *tmp = 0;
	  row = atoi(tmp2);
	  for (i = 0; i < row; i++)
	    list = list->next;
	  pitiviliststore = (PitiviListStore*)list->data;
	  list = pitiviliststore->child;
	  *tmp++;
	  tmp2 = tmp;
	}
      *tmp++;
    }

  row = atoi(tmp2);
  for (i = 0; i < row; i++)
    list = list->next;
  
  g_free(save);

  return list->data;
}

void	remove_liststore_for_bin(PitiviSourceListWindow *self,
				 guint bin_pos)
{
  PitiviListStore *pitiviliststore;
  GSList	*list;
  gpointer	data;
  gchar		*tmp;
  gchar		*tmp2;
  gchar		*save;
  guint		row;
  gint		i;

  data = get_data_for_bin(self);
  
  list = self->private->liststore;

  tmp = g_strdup(self->private->treepath);
  
  save = tmp2 = tmp;

  pitiviliststore = NULL;

  while (*tmp != 0)
    {
      if (*tmp == ':')
	{
	  *tmp = 0;
	  row = atoi(tmp2);
	  for (i = 0; i < row; i++)
	    list = list->next;
	  pitiviliststore = (PitiviListStore*)list->data;
	  list = pitiviliststore->child;
	  *tmp++;
	  tmp2 = tmp;
	}
      *tmp++;
    }

  list = g_slist_remove(list, data);

  /* handle the case the first element is removed */
  if (pitiviliststore == NULL)
    self->private->liststore = list;
  else
    pitiviliststore->child = list;

  g_free(save);
}

void	show_file_in_current_bin(PitiviSourceListWindow *self)
{
  GtkListStore	*liststore;
  gint	selected_row;
  gint	depth;

  selected_row = get_selected_row(self->private->treepath, &depth);

  liststore = get_liststore_for_bin(self, selected_row);

  gtk_tree_view_set_model(GTK_TREE_VIEW(self->private->listview), 
			  GTK_TREE_MODEL(liststore));

  /* pitivi_projectsourcelist_showfile(((PitiviProjectWindows*)self)->project->sources, self->private->treepath); */
}

char	*my_strcat(char *dst, char *src)
{
  char	*res;
  char	*tmp_res;
  int	dst_len;
  int	src_len;

  dst_len = strlen(dst);
  src_len = strlen(src);

  res = malloc(dst_len+src_len+1);
  tmp_res = res;

  while (*dst)
    *tmp_res++ = *dst++;

  while (*src)
    *tmp_res++ = *src++;

  *tmp_res = 0;
  return res;
}
void	retrieve_file_from_folder(PitiviSourceListWindow *self)
{
  DIR	*dir;
  struct dirent *entry;
  struct stat	stat_buf;
  gchar	*folderpath;
  gchar	*fullpathname;
  
  dir = opendir(self->private->folderpath);

  folderpath = g_strdup(self->private->folderpath); 
  strcat(folderpath, "/");
  
  while ((entry = readdir(dir)))
    {
      
      fullpathname = my_strcat(folderpath, entry->d_name);
      stat(fullpathname, &stat_buf);
      if (stat_buf.st_mode & S_IFREG)
	{
	  self->private->filepath = fullpathname;
	  g_printf("retrieve ==> %s\n", fullpathname);
	  new_file(NULL, self);
	}
      else
	g_free(fullpathname);
    }

  closedir(dir);
}

gchar*
pitivi_sourcelistwindow_set_folder(PitiviSourceListWindow *self, 
				   GtkTreeIter *itertest)
{
  GtkTreeSelection *selection;
  GtkListStore	*liststore;
  GdkPixbuf	*pixbufa;
  GtkTreeIter	iter;
  gchar		*sMediaType;
  gchar		*name;

  sMediaType = g_malloc(12);
    
  sprintf(sMediaType, "Bin");
  
  pixbufa = gtk_widget_render_icon(self->private->listview, GTK_STOCK_OPEN,
				   GTK_ICON_SIZE_MENU, NULL);

  /* Creation de la nouvelle ligne dans la listview */
  liststore = get_liststore_for_bin(self, 0);
  gtk_list_store_append(liststore, &iter);

  name = strrchr(self->private->folderpath, '/');
  if (name)
    name++;
  else
    name = self->private->folderpath;

  /* Mise a jour des donnees */
  gtk_list_store_set(liststore,
		     &iter, 
		     BMP_LISTCOLUMN1, pixbufa,
		     TEXT_LISTCOLUMN2, name,
		     TEXT_LISTCOLUMN3, sMediaType,
		     TEXT_LISTCOLUMN4, "",
		     TEXT_LISTCOLUMN5, "",
		     TEXT_LISTCOLUMN6, "",
		     POINTER_LISTCOLUMN7, "", -1);
    
  g_free(sMediaType);

  gtk_tree_model_get_iter_from_string(GTK_TREE_MODEL(self->private->treestore),
				      &iter, self->private->treepath);

  
  /* Creation de la nouvelle ligne enfant dans la treeview */
  gtk_tree_store_append(self->private->treestore, itertest/* &iter2 */, &iter);
  
  
  /* Mise a jour des donnees */
  gtk_tree_store_set(self->private->treestore, itertest/* &iter2 */, BMP_COLUMN,
		     pixbufa, TEXT_TREECOLUMN, name, -1);
  
  /* a fake path for add folder at the right place */
  strcat(self->private->treepath, ":0");
  
  liststore = gtk_list_store_new(N_LISTCOLOUMN, GDK_TYPE_PIXBUF,
				 G_TYPE_STRING, G_TYPE_STRING,
				 G_TYPE_STRING, G_TYPE_STRING,
				 G_TYPE_STRING, G_TYPE_POINTER);
  
  add_liststore_for_bin(self, liststore);

  self->private->treepath[strlen(self->private->treepath) - 2] = 0;
  selection = gtk_tree_view_get_selection(GTK_TREE_VIEW(self->private->treeview));
  gtk_tree_selection_select_iter(selection, &iter);  
  g_object_unref(pixbufa);

  return name;
}

void	new_folder(GtkWidget *widget, gpointer data)
{
  PitiviSourceListWindow *self = (PitiviSourceListWindow*)data;
  GtkTreePath	*treepath;
  GtkTreeIter	iter2;
  gchar		*save;
  gchar		*name;
  guint		selected_row;
  guint		depth;

  selected_row = get_selected_row(self->private->treepath, &depth);

  name = pitivi_sourcelistwindow_set_folder(self, &iter2);
  pitivi_projectsourcelist_add_folder_to_bin(((PitiviProjectWindows*)self)->project->sources,
					     self->private->treepath, name);

  /* retrieve GtkTreepath for current folder */
  treepath = gtk_tree_model_get_path(GTK_TREE_MODEL(self->private->treestore),
				     &iter2);

  /*set to current treepath */
  save = self->private->treepath;
  self->private->treepath = gtk_tree_path_to_string(treepath);

  /* retrieve all files from current folder path */
  retrieve_file_from_folder(self);
  
  /* restore original treepath */
  g_free(self->private->treepath);
  self->private->treepath = save;
}

PitiviSourceFile *	pitivi_sourcelistwindow_set_file(PitiviSourceListWindow *self)
{
  GtkTreeIter	pIter;
  PitiviSourceFile *sf;
  GtkListStore	*liststore;
  GdkPixbuf	*pixbufa = NULL;
  gchar		*name = NULL;
  gint		selected_row;
  gint		depth;
  gint		i;

  selected_row = 0;
  if (self->private->treepath != NULL)
    selected_row = get_selected_row(self->private->treepath, &depth);
   
  /* use gstreamer to check the file type */
  
  if ( self->private->filepath ) {
    if (!(sf = pitivi_sourcefile_new (self->private->filepath, ((PitiviWindows *) self)->mainapp)))
      return NULL;
  }
  else
    return NULL;
  
  if (sf && sf->mediatype == NULL)
    {
      /* do not add file to sourcelist */
      g_free(self->private->filepath);
      G_OBJECT_CLASS (sf)->finalize (G_OBJECT(sf));
      return NULL;
    }
  
  /*  pitivi_progressbar_set_infos (self->private->bar, sf->filename); */
  pixbufa = pitivi_sourcefile_get_first_thumb (sf);
  if (!pixbufa)
    {
      if (sf->havevideo && sf->haveaudio) 
	pixbufa = gtk_widget_render_icon(self->private->listview,  
					 PITIVI_STOCK_EFFECT_SOUNDTV, 
					 GTK_ICON_SIZE_MENU, NULL); 
      else if (sf->havevideo)
	pixbufa = gtk_widget_render_icon(self->private->listview, 
					 PITIVI_STOCK_EFFECT_TV,
					 GTK_ICON_SIZE_MENU, NULL);
      else
	pixbufa = gtk_widget_render_icon(self->private->listview, 
					 PITIVI_STOCK_EFFECT_SOUND,
					 GTK_ICON_SIZE_MENU, NULL);
    }
  /* Creation de la nouvelle ligne */
  
  liststore = get_liststore_for_bin(self, selected_row);
  gtk_list_store_append(liststore, &pIter);   
  name = strrchr(self->private->filepath, '/');
  name++;
  
    
  i = gtk_tree_model_iter_n_children(GTK_TREE_MODEL(liststore), NULL) - 1;
  pitivi_projectsourcelist_add_file_to_bin(((PitiviProjectWindows*)self)->project->sources, 
					   self->private->treepath,
					   sf->filename,
					   sf->mediatype,
					   sf->infovideo,
					   sf->infoaudio,
					   sf->length,
					   sf->pipeline);
  gtk_list_store_set(liststore,
		     &pIter, 
		     BMP_LISTCOLUMN1,  pixbufa,
		     TEXT_LISTCOLUMN2, name,
		     TEXT_LISTCOLUMN3, sf->mediatype,
		     TEXT_LISTCOLUMN4, g_strdup_printf("%llds", (signed long long int) (sf->length / GST_SECOND)),
		     TEXT_LISTCOLUMN5, sf->infovideo,
		     TEXT_LISTCOLUMN6, sf->infoaudio,
		     POINTER_LISTCOLUMN7, (gpointer)sf, -1);
  return sf;
}

void	new_file(GtkWidget *widget, gpointer data)
{
  PitiviSourceListWindow *self = (PitiviSourceListWindow*)data;
  
  if (!pitivi_sourcelistwindow_set_file(self))
    return;
}

void
pitivi_sourcelistwindow_set_bin(PitiviSourceListWindow *self, gchar *bin_name)
{
  GtkTreeSelection *selection;
  GdkPixbuf	*pixbufa;
  GtkTreeIter	iter;
  GtkListStore	*liststore;

  pixbufa = gtk_widget_render_icon(self->private->treeview, GTK_STOCK_OPEN, 
				   GTK_ICON_SIZE_MENU, NULL);
  /* Insertion des elements */
  
  gtk_tree_store_append(self->private->treestore, &iter, NULL);
      
  /* Creation de la nouvelle ligne */
  gtk_tree_store_set(self->private->treestore, &iter, BMP_COLUMN, pixbufa,
		     TEXT_TREECOLUMN, bin_name, -1);

  /* Creation du model pour le nouveau bin */
  liststore = gtk_list_store_new(N_LISTCOLOUMN, GDK_TYPE_PIXBUF,
				 G_TYPE_STRING, G_TYPE_STRING,
				 G_TYPE_STRING, G_TYPE_STRING,
				 G_TYPE_STRING, G_TYPE_POINTER);
  
  gtk_tree_view_set_model(GTK_TREE_VIEW(self->private->listview),
			  GTK_TREE_MODEL(liststore));
 
  
  strcpy(self->private->treepath, "0");
  add_liststore_for_bin(self, liststore);
  selection = gtk_tree_view_get_selection(GTK_TREE_VIEW(self->private->treeview));
  gtk_tree_selection_select_iter(selection, &iter);
  g_object_unref(pixbufa);
}

void	new_bin(PitiviSourceListWindow *self, gchar *bin_name)
{

  pitivi_projectsourcelist_new_bin(((PitiviProjectWindows*)self)->project->sources, bin_name);
  pitivi_sourcelistwindow_set_bin(self, bin_name);
}

/*
 *********************************************************
 * Drag and Drop					 *
 * Prepare PitiviSourceFile to be sent to TimelineWindow *
 *********************************************************
*/

void
slide_info (PitiviSourceListWindow *self, gint64 length, gchar *path)
{
  struct _Pslide
  {
    gint64 length;
    gchar  *path;
  } slide;

  slide.length = length;
  slide.path = path;
  g_signal_emit_by_name (self->private->timelinewin, "drag-source-begin", &slide);
}

static void
drag_begin_cb (GtkWidget          *widget,
	       GdkDragContext     *context,
	       gpointer		user_data)
{
  PitiviSourceListWindow	*self = (PitiviSourceListWindow *) user_data;
  GtkTreeView		*listview = (GtkTreeView *) widget;
  GtkTreeModel		*model;
  GtkTreeSelection	*selection;
  GtkTreeIter		iter;
  GtkTreeIter		iternext;
  gint			selected_list_row;
  gint			item_select;
  gint			folder_select;
  gint			i;
  PitiviSourceFile	*sf;
  gchar			*tmpMediaType;
  
  /* find treepath */
  selection = gtk_tree_view_get_selection(GTK_TREE_VIEW(self->private->treeview));
  if (!gtk_tree_selection_get_selected (selection, &model, &iter)) {
    g_warning("No elements selected!");
    return;
  }
  self->private->dndtreepath = g_strdup(gtk_tree_model_get_string_from_iter(model, &iter));
  
  /* find pos in listview */
  selection = gtk_tree_view_get_selection(listview);
  if (!gtk_tree_selection_get_selected (selection, &model, &iter)) {
    g_warning("No elements selected!");
    return;
  }
 
  self->private->dndfilepos = atoi(gtk_tree_model_get_string_from_iter(model, &iter));

  gtk_tree_model_get_iter_first(model, &iternext);
  selected_list_row = self->private->dndfilepos;
  item_select = 0;
  folder_select = 0;
  self->private->dndsf = NULL;
  for (i = 0; i < selected_list_row+1; i++)
    {
      gtk_tree_model_get (model, &iternext, TEXT_LISTCOLUMN3, &tmpMediaType, -1);
      gtk_tree_model_get (model, &iternext, POINTER_LISTCOLUMN7, &sf, -1);
      if (!strcmp(tmpMediaType, "Bin"))
	folder_select++;
      else
	item_select++;
      gtk_tree_model_iter_next(model, &iternext);
    }
  self->private->dndfilepos = item_select;  
  if (sf && sf->length)
    {
      self->private->dndsf = sf;
      slide_info (self, sf->length, tmpMediaType);
    }
}

static void
drag_end_cb (GtkWidget          *widget,
	     GdkDragContext     *context,
	     gpointer		user_data)
{
  PitiviSourceListWindow	*self = PITIVI_SOURCELISTWINDOW(user_data);
  
  if (self->private->dndtreepath) {
    g_free(self->private->dndtreepath);
    self->private->dndtreepath = NULL;
    self->private->dndfilepos = 0;
  }
}

static void
drag_data_get_cb (GtkWidget          *widget,
		  GdkDragContext     *context,
		  GtkSelectionData   *selection_data,
		  guint               info,
		  guint32             time,
		  gpointer	      editor)
{
  PitiviSourceListWindow *self = PITIVI_SOURCELISTWINDOW(editor);
  PitiviSourceFile	 *sf;
  
  if ( GTK_IS_TREE_VIEW (widget))
    {
      if ( !self->private->dndsf )
	{
	  self->private->dndsf = pitivi_projectsourcelist_get_sourcefile(
									 PITIVI_PROJECTWINDOWS(self)->project->sources,
									 self->private->dndtreepath,
									 self->private->dndfilepos
									 );
	  if ( !self->private->dndsf )
	    return ;
	}
      sf = self->private->dndsf;
      gtk_selection_data_set (selection_data, 
			      selection_data->target, 
			      8, 
			      (void *) &sf,
			      sizeof (PitiviSourceFile *));
    }
}

/*
 *********************************************************
 * ListView Creation right view on GUI			 *
 * Displaying file information				 *
 *********************************************************
*/


GtkWidget	*create_listview(PitiviSourceListWindow *self)
{
  GdkPixbuf             *pixbuf;
  GtkWidget		*pListView;
  GtkWidget		*pScrollbar;
  GtkTreeViewColumn	*pColumn;
  GtkCellRenderer      	*pCellRenderer;

  /* Creation de la vue */
  pListView = gtk_tree_view_new();
  
  gtk_drag_source_set(pListView, 
		      GDK_BUTTON1_MASK,
		      TargetEntries, iNbTargetEntries, 
		      GDK_ACTION_COPY);
  
  g_signal_connect (pListView, "drag_data_get",	      
		    G_CALLBACK (drag_data_get_cb), self);
  g_signal_connect (pListView, "drag_end",	      
		    G_CALLBACK (drag_end_cb), self);
  g_signal_connect (pListView, "drag_begin",	      
		    G_CALLBACK (drag_begin_cb), self);
  
  pixbuf = gtk_widget_render_icon(pListView, PITIVI_STOCK_HAND, GTK_ICON_SIZE_DND, NULL);
  gtk_drag_source_set_icon_pixbuf (pListView, pixbuf);
  self->private->listview = pListView;

  /* Creation du menu popup */
  self->private->listmenu = pitivi_create_menupopup(GTK_WIDGET (self), ListPopup, iNbListPopup);

  g_signal_connect_swapped(G_OBJECT(pListView), "button_press_event",
			   G_CALLBACK(my_popup_handler), 
			   GTK_OBJECT(self));
  g_signal_connect(G_OBJECT(pListView), "row-activated", 
		   (GCallback) on_row_activated, GTK_OBJECT(self));


  /* Creation de la premiere colonne */
  pCellRenderer = gtk_cell_renderer_pixbuf_new();
  pColumn = gtk_tree_view_column_new_with_attributes("Icon", pCellRenderer,
						     "pixbuf", BMP_LISTCOLUMN1,
						     NULL);
  
  /* Ajout de la colonne a la vue */
  gtk_tree_view_append_column(GTK_TREE_VIEW(pListView), pColumn);

  /* Creation de la deuxieme colonne */
  pCellRenderer = gtk_cell_renderer_text_new();
  pColumn = gtk_tree_view_column_new_with_attributes("Filename", pCellRenderer,
						     "text", TEXT_LISTCOLUMN2,
						     NULL);
  
  /* Ajout de la colonne a la vue */
  gtk_tree_view_append_column(GTK_TREE_VIEW(pListView), pColumn);

  /* Creation de la troisieme colonne */
  pCellRenderer = gtk_cell_renderer_text_new();
  pColumn = gtk_tree_view_column_new_with_attributes("Media Type",
						     pCellRenderer,
						     "text", TEXT_LISTCOLUMN3,
						     NULL);
  
  /* Ajout de la colonne a la vue */
  gtk_tree_view_append_column(GTK_TREE_VIEW(pListView), pColumn);

  /* Creation de la quatrieme colonne */
  pCellRenderer = gtk_cell_renderer_text_new();
  pColumn = gtk_tree_view_column_new_with_attributes("Length", pCellRenderer,
						     "text", TEXT_LISTCOLUMN4,
						     NULL);
  
  /* Ajout de la colonne a la vue */
  gtk_tree_view_append_column(GTK_TREE_VIEW(pListView), pColumn);

  /* Creation de la cinquieme colonne */
  pCellRenderer = gtk_cell_renderer_text_new();
  pColumn = gtk_tree_view_column_new_with_attributes("Video",
						     pCellRenderer,
						     "text", TEXT_LISTCOLUMN5,
						     NULL);
  
  /* Ajout de la colonne a la vue */
  gtk_tree_view_append_column(GTK_TREE_VIEW(pListView), pColumn);

  /* Creation de la sixieme colonne */
  pCellRenderer = gtk_cell_renderer_text_new();
  pColumn = gtk_tree_view_column_new_with_attributes("Audio",
						     pCellRenderer,
						     "text", TEXT_LISTCOLUMN6,
						     NULL);
  
  /* Ajout de la colonne a la vue */
  gtk_tree_view_append_column(GTK_TREE_VIEW(pListView), pColumn);
  
  /* Ajout de la vue a la fenetre */
  pScrollbar = gtk_scrolled_window_new(NULL, NULL);
  gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(pScrollbar),
				 GTK_POLICY_AUTOMATIC, GTK_POLICY_AUTOMATIC);
  gtk_container_add(GTK_CONTAINER(pScrollbar), pListView);
  
  return pScrollbar;
}

/*
 *********************************************************
 * TreeView Creation left view on GUI			 *
 *							 *
 *********************************************************
*/

GtkWidget	*create_treeview(PitiviSourceListWindow *self)
{
  GtkWidget		*pTreeView;
  GtkTreeViewColumn	*pColumn;
  GtkCellRenderer	*pCellRenderer;
  GtkTreeSelection	*selection;
  GtkWidget		*pScrollbar;

  /* Creation du modele */
  self->private->treestore = gtk_tree_store_new(N_TREECOLUMN, GDK_TYPE_PIXBUF, 
						G_TYPE_STRING);  

  /* Creation de la vue */
  pTreeView = gtk_tree_view_new_with_model(GTK_TREE_MODEL(self->private->treestore));

  self->private->treeview = pTreeView;

  /* Creation du menu popup */
  self->private->treemenu = pitivi_create_menupopup (GTK_WIDGET (self), TreePopup, iNbTreePopup);

  //g_printf("connect signal treeview 0x%x\n", pTreeView);

  g_signal_connect_swapped(G_OBJECT(pTreeView), "button_press_event",
			   G_CALLBACK(my_popup_handler), GTK_OBJECT(self));

  selection = gtk_tree_view_get_selection(GTK_TREE_VIEW(self->private->treeview));

  gtk_tree_selection_set_select_function(selection, (GtkTreeSelectionFunc)on_row_selected, self, NULL);

  
  /* Creation de la premiere colonne */
  pCellRenderer = gtk_cell_renderer_pixbuf_new();
  pColumn = gtk_tree_view_column_new_with_attributes("Images", pCellRenderer,
						     "pixbuf", BMP_COLUMN,
						     NULL);

  /* Ajout de la colonne a la vue */
  gtk_tree_view_append_column(GTK_TREE_VIEW(pTreeView), pColumn);

  /* Creation de la deuxieme colonne */
  pCellRenderer = gtk_cell_renderer_text_new();
  pColumn = gtk_tree_view_column_new_with_attributes("Label", pCellRenderer,
						      "text", TEXT_TREECOLUMN,
						      NULL);
  
  /* Ajout de la colonne a la vue */
  gtk_tree_view_append_column(GTK_TREE_VIEW(pTreeView), pColumn);
						      
  /* Ajout de la vue a la fenetre */
  pScrollbar = gtk_scrolled_window_new(NULL, NULL);
  gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(pScrollbar),
				 GTK_POLICY_AUTOMATIC, GTK_POLICY_AUTOMATIC);
  gtk_container_add(GTK_CONTAINER(pScrollbar), pTreeView);

  return pScrollbar;
}

gboolean	on_row_selected(GtkTreeView *view, GtkTreeModel *model,
				GtkTreePath *treepath, gboolean path_current, 
				gpointer user_data)
{
  PitiviSourceListWindow *self = (PitiviSourceListWindow*)user_data;
  GtkTreeIter	iter;

  if (gtk_tree_model_get_iter(model, &iter, treepath))
    {
      gchar	*name;
      
      gtk_tree_model_get(model, &iter, TEXT_TREECOLUMN, &name, -1);
      
      if (!path_current)
	{
	  if (self->private->treepath != NULL)
	    g_free(self->private->treepath);
	  
	  self->private->treepath = gtk_tree_path_to_string(treepath);
	  
	  /* show all file in current bin */
 	  show_file_in_current_bin(self);
	  g_free(name);
	}
    }
  return TRUE;
}

gboolean	select_folder_from_listview(PitiviSourceListWindow *self,
					    gint folder_select)
{
  char	*folder;
  GtkTreeIter	iter;
  GtkTreePath	*path;
  GtkTreeSelection	*selection;

  g_printf("you select a bin\n");
  /* we need to select the corresponding bin in the treeview */
  selection = gtk_tree_view_get_selection(GTK_TREE_VIEW(self->private->treeview));
  
  folder = g_strdup_printf(":%d", folder_select);
  strcat(self->private->treepath, folder);
  g_free(folder);
  
  g_printf("with the following path [%s]\n", self->private->treepath);
  path = gtk_tree_path_new_from_string(self->private->treepath);
  /* path = gtk_tree_path_new_from_string("1"); */
  if (!path)
    {
      g_printf("path is not valid\n");
      return FALSE;
    }
  gtk_tree_model_get_iter(GTK_TREE_MODEL(self->private->treestore),
			  &iter, path);
  gtk_tree_view_expand_to_path(GTK_TREE_VIEW(self->private->treeview), 
			       path);
  gtk_tree_selection_select_iter(selection, &iter);  
  if (gtk_tree_selection_iter_is_selected(selection, &iter))
    {
      g_printf("the item is currently selected\n");
      return TRUE;
    }
  else
    {
      g_printf("the item is not selected\n");
      return FALSE;
    }
  
}

void	on_row_activated (GtkTreeView        *listview,
			  GtkTreePath        *path,
			  GtkTreeViewColumn  *col,
			  gpointer            userdata)
{
  PitiviSourceListWindow *self = (PitiviSourceListWindow*)userdata;
  PitiviSourceFile *sf = NULL;
  PitiviLPlayerWindow *lplayerwin;
  GtkListStore	*liststore;
  GtkTreeIter	iter;
  gint	item_select;
  gint	folder_select;
  gchar	*sMediaType;
  
  /* set the lispath */
  self->private->listpath = gtk_tree_path_to_string(path);
  OnSelectItem(self, &iter, &liststore, (void **) &sf, POINTER_LISTCOLUMN7, &item_select, &folder_select);
  if (!sf && OnSelectItem(self, &iter, &liststore, (void **) &sMediaType, TEXT_LISTCOLUMN3, &item_select, &folder_select))
    {
      if (!strcmp(sMediaType, "Bin"))
	select_folder_from_listview(self, folder_select);
      return;
    }
  lplayerwin = pitivi_lplayerwindow_new (sf->filename);
}

gboolean	my_popup_handler(gpointer data, GdkEvent *event,
				 gpointer user_data)
{
  PitiviSourceListWindow *self = (PitiviSourceListWindow*)data;
  GtkMenu		*pMenu;
  GdkEventButton	*event_button;

  /* The "widget" is the menu that was supplied when
   * g_signal_connect_swapped() was called.
   */

  
  if (event->type == GDK_BUTTON_PRESS)
    {
      event_button = (GdkEventButton *)event;
      if (event_button->button == 3)
	{
	  GtkTreeSelection *selection;

	  selection = gtk_tree_view_get_selection(GTK_TREE_VIEW(user_data));

	  if (gtk_tree_selection_count_selected_rows(selection) <= 1)
	    {
	      GtkTreePath *path;

	      if (gtk_tree_view_get_path_at_pos(GTK_TREE_VIEW(user_data),
						event_button->x, 
						event_button->y,
						&path, NULL, NULL, NULL))
		{
		  gtk_tree_selection_unselect_all(selection);
		  gtk_tree_selection_select_path(selection, path);
		  if (self->private->listview == user_data)
		    {
		      if (self->private->listpath != NULL)
			g_free(self->private->listpath);
		      self->private->listpath = gtk_tree_path_to_string(path);
		      gtk_tree_path_free(path);
		      
		      /* create menu for popup */
		 
		      pMenu = GTK_MENU(pitivi_create_menupopup (GTK_WIDGET (self), ItemPopup, 
							 iNbItemPopup));
		    }
		  else
		    pMenu = GTK_MENU(pitivi_create_menupopup (GTK_WIDGET (self), BinPopup,
						       iNbBinPopup));
		}
	      else
		{
		  if (self->private->listview == user_data)
		    pMenu = GTK_MENU(self->private->listmenu);
		  else
		    pMenu = GTK_MENU(self->private->treemenu);
		}
	      gtk_menu_popup(pMenu, NULL, NULL, NULL, NULL,
			     event_button->button, event_button->time);
	    }
	  return TRUE;
	}
    }

  return FALSE;
}


void	OnNewBin(gpointer data, gint action, GtkWidget *widget)
{
  PitiviSourceListWindow *self = (PitiviSourceListWindow*)data;
  GtkWidget *dialog;
  GtkWidget *label;
  GtkWidget *entry;
  GtkWidget	*hbox;
  gchar		*stexte;
  gchar		*sname;

  dialog = gtk_dialog_new_with_buttons("New Bin", GTK_WINDOW(self),
				       GTK_DIALOG_MODAL|GTK_DIALOG_NO_SEPARATOR,
				       GTK_STOCK_OK, GTK_RESPONSE_OK,
				       GTK_STOCK_CANCEL, GTK_RESPONSE_CANCEL,
				       NULL);
  
  hbox = gtk_hbox_new(FALSE, 0);
  label = gtk_label_new("Bin Name :");
  gtk_box_pack_start(GTK_BOX(hbox), label, TRUE, FALSE, 0);
 
  entry = gtk_entry_new();
  stexte = g_malloc(12);
  sprintf(stexte, "Bin %d", self->private->nbrchutier);
  gtk_entry_set_text(GTK_ENTRY(entry), stexte);

  gtk_box_pack_start(GTK_BOX(hbox), entry, TRUE, FALSE, 0);
  gtk_box_pack_start(GTK_BOX(GTK_DIALOG(dialog)->vbox), hbox, TRUE, FALSE, 0);
  gtk_widget_show_all(GTK_DIALOG(dialog)->vbox);
  
  switch (gtk_dialog_run(GTK_DIALOG(dialog)))
    {
    case GTK_RESPONSE_OK:
      sname = g_strdup(gtk_entry_get_text(GTK_ENTRY(entry)));
      new_bin(self, sname);
      self->private->nbrchutier++;
      break;
    case GTK_RESPONSE_CANCEL:
    case GTK_RESPONSE_NONE:
    default:
      break;
    }
  gtk_widget_destroy(dialog);
  g_free(stexte);
}

/* FIXME INPORT FOLDER coming soon */

void	import_from_gtkchooser (PitiviSourceListWindow *self, gchar *labelchooser, guint signal)
{
  GtkWidget	*dialog;
  gboolean	accept = FALSE;

  if (signal == FILEIMPORT_SIGNAL)
    dialog = gtk_file_chooser_dialog_new(labelchooser,
					 GTK_WINDOW(self), 
					 GTK_FILE_CHOOSER_ACTION_OPEN,
					 GTK_STOCK_CANCEL, GTK_RESPONSE_CANCEL,
					 GTK_STOCK_OPEN, GTK_RESPONSE_ACCEPT,
					 NULL);
  else
    dialog = gtk_file_chooser_dialog_new(labelchooser,
					 GTK_WINDOW(self), 
					 GTK_FILE_CHOOSER_ACTION_SELECT_FOLDER,
					 GTK_STOCK_CANCEL, GTK_RESPONSE_CANCEL,
					 GTK_STOCK_OPEN, GTK_RESPONSE_ACCEPT,
					 NULL);
  
  if (gtk_dialog_run(GTK_DIALOG(dialog)) == GTK_RESPONSE_ACCEPT)
    {
      accept = TRUE;
      if (signal == FILEIMPORT_SIGNAL)
	self->private->filepath = gtk_file_chooser_get_filename(GTK_FILE_CHOOSER(dialog));
      else
	self->private->folderpath = gtk_file_chooser_get_filename(GTK_FILE_CHOOSER(dialog));
    }
  gtk_widget_destroy(dialog);
  if (accept)
    g_signal_emit(self, pitivi_sourcelistwindow_signal[signal],
		  0 /* details */, 
		  NULL);
}

void	OnImportFile(gpointer data, gint action, GtkWidget *widget)
{
  PitiviSourceListWindow	*self = (PitiviSourceListWindow*)data;
  import_from_gtkchooser (self, "Import File", FILEIMPORT_SIGNAL);
}

void	OnImportFolder(gpointer data, gint action, GtkWidget *widget)
{
  PitiviSourceListWindow *self = (PitiviSourceListWindow*)data;
  import_from_gtkchooser (self, "Import Folder", FOLDERIMPORT_SIGNAL);
}

gint		OnSelectItem(PitiviSourceListWindow *self, GtkTreeIter *iter,
			     GtkListStore **liststore, void **sMediaType, 
			     guint type, gint *item_select, gint *folder_select)
{
  GtkTreeIter	iternext;
  GtkTreePath	*listpath;
  void		*tmpMediaType;
  gint		i;
  guint		selected_list_row;
  gint		depth;


  listpath = gtk_tree_path_new_from_string(self->private->listpath);
  
  selected_list_row = get_selected_row(self->private->listpath, &depth);
  *liststore = get_liststore_for_bin(self, selected_list_row);
  if (!gtk_tree_model_get_iter(GTK_TREE_MODEL(*liststore), iter, listpath))
    {
      gtk_tree_path_free(listpath);
      return FALSE;
    }
  
  gtk_tree_path_free(listpath);
  gtk_tree_model_get(GTK_TREE_MODEL(*liststore), iter, type, &(*sMediaType), -1);
  gtk_tree_model_get_iter_first(GTK_TREE_MODEL(*liststore), &iternext);
  
  *item_select = 0;
  *folder_select = 0;
  
  i = 0;
  while (i++ < selected_list_row)
    {
      gtk_tree_model_get(GTK_TREE_MODEL(*liststore), &iternext, type, &tmpMediaType, -1);
      if (!strcmp(tmpMediaType, "Bin"))
	(*folder_select)++;
      else
	(*item_select)++;
      gtk_tree_model_iter_next(GTK_TREE_MODEL(*liststore), &iternext);
    }
  return TRUE;
}

/*
 *********************************************************
 * Removing bins or items				 *
 * Called   on clear action (Contextuel Menu)	         *
 *********************************************************
*/

void
OnTimelineFirstInsert (gpointer data, gint action, GtkWidget *widget)
{
  
}

void		OnRemoveItem (gpointer data, gint action, GtkWidget *widget)
{
  PitiviSourceListWindow *self = (PitiviSourceListWindow*)data;
  GtkListStore	*liststore;
  GtkTreeIter	iter;
  gchar		*sMediaType;
  gint		item_select;
  gint		folder_select;

  if (!OnSelectItem(self, &iter, &liststore, (void **) &sMediaType, TEXT_LISTCOLUMN3, &item_select, 
		   &folder_select))
    return;
  
  if (!OnSelectItem(self, &iter, &liststore, (void **) &self->private->dndsf, POINTER_LISTCOLUMN7, &item_select, 
		   &folder_select))
    return;

  /* If the PitiviSourceFile is used , dialogbox "Can't delete" */
  if (self->private->dndsf->nbbins) {
    GtkWidget	*dialog;

    dialog = gtk_message_dialog_new (GTK_WINDOW (self),
				     GTK_DIALOG_DESTROY_WITH_PARENT,
				     GTK_MESSAGE_ERROR,
				     GTK_BUTTONS_CLOSE,
				     "This source is used %d times in the project\nYou must remove it from the timeline before deleting it",
				     self->private->dndsf->nbbins);
    gtk_dialog_run (GTK_DIALOG (dialog));
    gtk_widget_destroy (dialog);
    return;
  }

  if (strcmp(sMediaType, "Bin"))
    {
      if ( self->private->dndsf )
	g_signal_emit_by_name (GTK_OBJECT (self->private->timelinewin), "delete-source", self->private->dndsf);
      pitivi_projectsourcelist_remove_file_from_bin(((PitiviProjectWindows*)self)->project->sources, 
						    self->private->treepath,
						    item_select);
      gtk_list_store_remove(GTK_LIST_STORE(liststore), &iter);
      g_object_unref(self->private->dndsf);
    }
  else /* need to remove folder */
    {
      /* we need to set treepath too */
      self->private->treepath = g_strdup_printf("%s:%d", self->private->treepath, folder_select);
      OnRemoveBin(self, 0, NULL);
    }
}

void		OnRemoveBin(gpointer data, gint action, GtkWidget *widget)
{
  PitiviSourceListWindow *self = (PitiviSourceListWindow*)data;
  GtkTreeModel	*model;
  GtkListStore	*liststore;
  GtkTreeIter	parent;
  GtkTreeIter	iter;
  GtkTreeIter	iternext;
  GtkTreeIter	listiter;
  GtkTreePath	*treepath;
  GtkTreeSelection *selection;
  gchar		*sTreepath;
  gchar		*sMediaType;
  gint		selected_tree_row = 0;
  gint		depth;
  gint		i;
  gint		folder_select;

  model = gtk_tree_view_get_model(GTK_TREE_VIEW(self->private->treeview));
  
  /* couldn't remove when he has only one */
  if (gtk_tree_model_iter_n_children(model, NULL) == 1)
    {
      gtk_tree_model_get_iter_first(model, &iter);
      if (gtk_tree_model_iter_n_children(model, &iter) == 0)
	{
	  //g_printf("we have only one bin\n");
	  return;
	}
    }
  
  treepath = gtk_tree_path_new_from_string(self->private->treepath);
    
  if (!gtk_tree_model_get_iter(model, &iter, treepath))
    {
      gtk_tree_path_free(treepath);
      return;
    }

  gtk_tree_path_free(treepath);

  iternext = iter;
  if (!gtk_tree_model_iter_next(model, &iternext))
    gtk_tree_model_get_iter_first(model, &iternext);
  
  /* need to remove this child from listview */
  if (gtk_tree_model_iter_parent(model, &parent, &iter))
    {
      selected_tree_row = get_selected_row(self->private->treepath, &depth);
     
      treepath = gtk_tree_model_get_path(model, &parent);

      /* save treepath */
      sTreepath = self->private->treepath;
      self->private->treepath = gtk_tree_path_to_string(treepath);

      liststore = get_liststore_for_bin(self, 0);
      gtk_tree_model_get_iter_first(GTK_TREE_MODEL(liststore), &listiter);

      i = folder_select = 0;
      
      selected_tree_row++;
      while (folder_select < selected_tree_row)
	{
	  gtk_tree_model_get(GTK_TREE_MODEL(liststore), &listiter, TEXT_LISTCOLUMN3, &sMediaType, -1);

	  if (!strcmp(sMediaType, "Bin"))
	    folder_select++;
	  if (folder_select == selected_tree_row)
	    break;
	  i++;
	  gtk_tree_model_iter_next(GTK_TREE_MODEL(liststore), &listiter);
	}
      
      gtk_list_store_remove(GTK_LIST_STORE(liststore), &listiter);

      /* restore treepath */
      g_free(self->private->treepath);
      self->private->treepath = sTreepath;

      gtk_tree_path_free(treepath);
    }
  
  gtk_tree_store_remove(GTK_TREE_STORE(model), &iter);
  remove_liststore_for_bin(self, selected_tree_row);
  
  pitivi_projectsourcelist_remove_bin(((PitiviProjectWindows*)self)->project->sources, 
				      self->private->treepath);

  /* need to select another bin */
  
  selection = gtk_tree_view_get_selection(GTK_TREE_VIEW(self->private->treeview));
  gtk_tree_selection_select_iter(selection, &iternext);

}

void	OnImportProject(void)
{
  printf("== Import Project ==\n");
}

void	OnFind(void)
{
  printf("== Find ==\n");
}

void	OnOptionProject(void)
{
  printf(" == Options Project ==\n");
}

PitiviSourceFile *
pitivi_sourcelistwindow_get_file(PitiviSourceListWindow *self)
{
  GtkTreeIter	iter;
  GtkListStore	*liststore;
  gchar		*sMediaType;
  gint		item_select;
  gint		folder_select;

  if (!OnSelectItem(self, &iter, &liststore, (void **) &sMediaType, TEXT_LISTCOLUMN3, &item_select,
		    &folder_select))
    return NULL;
  if (!strcmp(sMediaType, "Bin"))
    return NULL;
  
  return pitivi_projectsourcelist_get_sourcefile(((PitiviProjectWindows*)self)->project->sources, 
						 self->private->treepath,
						 item_select);
}

GtkWidget	*create_projectview(PitiviSourceListWindow *self)
{
  GtkWidget	*pScrollbar;
  GtkWidget	*pScrollbar2;
  GtkWidget	*pHpaned;

  pHpaned = gtk_hpaned_new();

  pScrollbar = create_treeview(self);
  pScrollbar2 = create_listview(self);
 
  g_signal_connect (G_OBJECT (self), "newfile",
                          (GCallback)new_file,
                          self);

  g_signal_connect (G_OBJECT (self), "newfolder",
                          (GCallback)new_folder,
                          self);

  gtk_paned_set_position(GTK_PANED(pHpaned), 200);
  gtk_paned_pack1(GTK_PANED(pHpaned), pScrollbar, FALSE, FALSE);
  gtk_paned_pack2(GTK_PANED(pHpaned), pScrollbar2, TRUE, FALSE);
  
  return pHpaned;
}
void	
pitivi_sourcelistwindow_recurse_into_folder(PitiviSourceListWindow *self, 
					    gchar *parent_name)
{
  PitiviSourceFile *sf;
  GSList	   *file_list;
  GSList	   *folder_list;
  GtkTreePath	   *treepath;
  GtkTreeIter	   iter;
  gchar		   *name;
  gchar		   *save;

  file_list = pitivi_projectsourcelist_get_file_list(((PitiviProjectWindows*)self)->project->sources, parent_name);
      
  while (file_list)
    {
      self->private->filepath = file_list->data;
      if ((sf = pitivi_sourcelistwindow_set_file(self)))
	pitivi_projectsourcelist_set_file_property_by_name(((PitiviProjectWindows*)self)->project->sources, 
							   parent_name, 
							   sf->filename, 
							   sf->mediatype, 
							   sf->infovideo, 
							   sf->infoaudio, 
							   sf->length,
							   sf->pipeline);
      file_list = file_list->next;
    }

  folder_list = pitivi_projectsourcelist_get_folder_list(((PitiviProjectWindows*)self)->project->sources, parent_name);
  
  while (folder_list)
    {
      self->private->folderpath = folder_list->data;
      name = pitivi_sourcelistwindow_set_folder(self, &iter);
      treepath = gtk_tree_model_get_path(GTK_TREE_MODEL(self->private->treestore),
				     &iter);

      /*set to current treepath */
      save = self->private->treepath;
      self->private->treepath = gtk_tree_path_to_string(treepath);
      
      pitivi_sourcelistwindow_recurse_into_folder(self, folder_list->data);

        /* restore original treepath */
      g_free(self->private->treepath);
      self->private->treepath = save;
  
      folder_list = folder_list->next;
    }

}

void	pitivi_sourcelistwindow_load_project(PitiviSourceListWindow *self)
{
  GSList	*bin_list;


  bin_list = pitivi_projectsourcelist_get_bin_list(((PitiviProjectWindows*)self)->project->sources);
  while (bin_list)
    {
      pitivi_sourcelistwindow_set_bin(self, bin_list->data);
      pitivi_sourcelistwindow_recurse_into_folder(self, bin_list->data);
      bin_list = bin_list->next;
    }
}


/*
 *********************************************************
 * Pitivi Source List Window Initialisation et creation  *
 *						         *
 *********************************************************
*/

/**
 * pitivi_sourcelistwindow_new:
 * @PitiviMainApp: The object containing all references of the application
 * @PitiviProject: The object containing all references of the multimedia project
 *
 * Creates a new window stocking the multimedia's sources
 *
 * Returns: An element PitiviSourceListWindow, a window
 * containing a list a multimedia's sources
 */

PitiviSourceListWindow *
pitivi_sourcelistwindow_new(PitiviMainApp *mainapp, PitiviProject *project)
{
  PitiviSourceListWindow	*sourcelistwindow;
  
  sourcelistwindow = (PitiviSourceListWindow *) g_object_new(PITIVI_SOURCELISTWINDOW_TYPE,
							     "mainapp", mainapp,
							     "project", project,
							     NULL);
  g_assert(sourcelistwindow != NULL);
  return sourcelistwindow;
}

static GObject *
pitivi_sourcelistwindow_constructor (GType type,
			     guint n_construct_properties,
			     GObjectConstructParam * construct_properties)
{
  PitiviSourceListWindow  *sourcelistwindow;
  PitiviProject	*project;
  GObject *obj;
  
  /* Invoke parent constructor. */
  obj = G_OBJECT_CLASS (parent_class)->constructor (type, n_construct_properties,
						    construct_properties);
  
  project = ((PitiviProjectWindows *) obj)->project;
  sourcelistwindow = (PitiviSourceListWindow *) obj;
  if (pitivi_projectsourcelist_test_bin_tree(project->sources))
    {
      pitivi_sourcelistwindow_load_project((PitiviSourceListWindow*)obj);
    }
  else
    {
      new_bin((PitiviSourceListWindow*)obj, g_strdup("bin 1"));
      ((PitiviSourceListWindow*)obj)->private->nbrchutier++;
    }
  /* timeline access */
  sourcelistwindow->private->timelinewin = (GtkWidget *) pitivi_mainapp_get_timelinewin 
    (((PitiviWindows *)sourcelistwindow)->mainapp);
  return obj;
}

static void
pitivi_sourcelistwindow_instance_init (GTypeInstance * instance, gpointer g_class)
{
  PitiviSourceListWindow *self = (PitiviSourceListWindow *) instance;

  self->private = g_new0(PitiviSourceListWindowPrivate, 1);
  
  /* initialize all public and private members to reasonable default values. */ 
  
  self->private->dispose_has_run = FALSE;
  self->private->hpaned = create_projectview(self);
  self->private->liststore = NULL;
  self->private->treepath = g_strdup("0");
  gtk_window_set_title (GTK_WINDOW (self), PITIVI_SOURCELIST_DF_TITLE);

  gtk_window_set_default_size (GTK_WINDOW (self), PITIVI_SOURCELIST_DF_WIN_WIDTH, PITIVI_SOURCELIST_DF_WIN_HEIGHT); 
  
  if (window_icon == NULL) 
    {
      char *filename;
      
      filename = g_strdup(PITIVI_SOURCELIST_LOGO);
      window_icon = gdk_pixbuf_new_from_file (filename, NULL);
      g_free (filename);
    }
  gtk_window_set_icon (GTK_WINDOW (self), window_icon);

  gtk_window_set_default_size(GTK_WINDOW(self), PITIVI_SOURCELIST_DF_WIN_WIDTH, PITIVI_SOURCELIST_DF_WIN_HEIGHT);
  gtk_container_add(GTK_CONTAINER(self), self->private->hpaned);
  self->private->nbrchutier = 1;
  /* Progress bar */
  /*  self->private->bar = pitivi_progressbar_new (); */
}

static void
pitivi_sourcelistwindow_dispose (GObject *object)
{
  PitiviSourceListWindow	*self = PITIVI_SOURCELISTWINDOW(object);

  /* If dispose did already run, return. */
  if (self->private->dispose_has_run)
    return;
  
  /* Make sure dispose does not run twice. */
  self->private->dispose_has_run = TRUE;	
  G_OBJECT_CLASS (parent_class)->dispose (object);
}

static void
pitivi_sourcelistwindow_finalize (GObject *object)
{
  PitiviSourceListWindow	*self = PITIVI_SOURCELISTWINDOW(object);

  g_free (self->private);
  G_OBJECT_CLASS (parent_class)->finalize (object);
}

static void
pitivi_sourcelistwindow_set_property (GObject * object,
			      guint property_id,
			      const GValue * value, GParamSpec * pspec)
{
/*   PitiviSourceListWindow *self = (PitiviSourceListWindow *) object; */

  switch (property_id)
    {
    default:
      g_assert (FALSE);
      break;
    }
}

static void
pitivi_sourcelistwindow_get_property (GObject * object,
			      guint property_id,
			      GValue * value, GParamSpec * pspec)
{
/*   PitiviSourceListWindow *self = (PitiviSourceListWindow *) object; */

  switch (property_id)
    {
    default:
      g_assert (FALSE);
      break;
    }
}

static gboolean
pitivi_sourcelistwindow_delete_event ( GtkWidget  *widget,
				       GdkEventAny *event)
{
  g_return_val_if_fail (GTK_IS_WIDGET (widget), FALSE);
  gtk_widget_hide (widget);
  pitivi_timelinewindow_windows_set_action (pitivi_mainapp_get_timelinewin (((PitiviWindows *) widget)->mainapp), 
					    "SourceListWindows", FALSE);
  return TRUE;
}


static void
pitivi_sourcelistwindow_class_init (gpointer g_class, gpointer g_class_data)
{
  GObjectClass *gobject_class = G_OBJECT_CLASS (g_class);
  GtkWidgetClass *widget_class = GTK_WIDGET_CLASS (g_class);
/*   PitiviSourceListWindowClass *klass = PITIVI_SOURCELISTWINDOW_CLASS (g_class); */
  
  parent_class = g_type_class_peek_parent (g_class);

  gobject_class->constructor = pitivi_sourcelistwindow_constructor;
  gobject_class->dispose = pitivi_sourcelistwindow_dispose;
  gobject_class->finalize = pitivi_sourcelistwindow_finalize;
  
  gobject_class->set_property = pitivi_sourcelistwindow_set_property;
  gobject_class->get_property = pitivi_sourcelistwindow_get_property;

  widget_class->delete_event = pitivi_sourcelistwindow_delete_event;
  pitivi_sourcelistwindow_signal[FILEIMPORT_SIGNAL] = g_signal_newv("newfile",
								    G_TYPE_FROM_CLASS (g_class),
								    G_SIGNAL_RUN_LAST | G_SIGNAL_NO_RECURSE | G_SIGNAL_NO_HOOKS,
								    NULL /* class closure */,
								    NULL /* accumulator */,
								    NULL /* accu_data */,
								    g_cclosure_marshal_VOID__VOID,
								    G_TYPE_NONE /* return_type */,
								    0     /* n_params */,
								    NULL  /* param_types */);
  
  pitivi_sourcelistwindow_signal[FOLDERIMPORT_SIGNAL] = g_signal_newv("newfolder",
								      G_TYPE_FROM_CLASS (g_class),
								      G_SIGNAL_RUN_LAST | G_SIGNAL_NO_RECURSE | G_SIGNAL_NO_HOOKS,
								      NULL /* class closure */,
								      NULL /* accumulator */,
								      NULL /* accu_data */,
								      g_cclosure_marshal_VOID__VOID,
								      G_TYPE_NONE /* return_type */,
								      0     /* n_params */,
								      NULL  /* param_types */);
}

GType
pitivi_sourcelistwindow_get_type (void)
{
  static GType type = 0;
 
  if (type == 0)
    {
      static const GTypeInfo info = {
	sizeof (PitiviSourceListWindowClass),
	NULL,			/* base_init */
	NULL,			/* base_finalize */
	pitivi_sourcelistwindow_class_init,	/* class_init */
	NULL,			/* class_finalize */
	NULL,			/* class_data */
	sizeof (PitiviSourceListWindow),
	0,			/* n_preallocs */
	pitivi_sourcelistwindow_instance_init	/* instance_init */
      };
      type = g_type_register_static (PITIVI_PROJECTWINDOWS_TYPE,
				     "PitiviSourceListWindowType", &info, 0);
    }

  return type;
}
