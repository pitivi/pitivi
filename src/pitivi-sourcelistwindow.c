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
#include "pitivi-settings.h"
#include "pitivi-stockicons.h"
#include "pitivi-dragdrop.h"
#include "pitivi-mainapp.h"
#include "pitivi-viewerwindow.h"
#include "../pixmaps/bg.xpm"
#include "pitivi-toolboxwindow.h"
#include "pitivi-toolbox.h"

static PitiviProjectWindowsClass *parent_class = NULL;

struct _PitiviListStore
{
  GtkListStore	*liststore;
  GSList	*child;
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
  GSList	*liststore;
  GtkTreeStore	*treestore;
  guint		nbrchutier;
  /* GST variable */
  GstElement	*mainpipeline;
  GstElement	*pipeline;
  GstCaps	*mediacaps;
  GSList       	*padlist;

  /* Property of the media */
  gchar		*mainmediatype;
  gchar		*mediatype;
  gchar		*infovideo;
  gchar		*infoaudio;
  gint64       	length;

  gboolean	havevideo;
  gboolean	haveaudio;

  gchar		*treepath;
  gchar		*listpath;

  gchar		*filepath;
  gchar		*folderpath;
  /* Signals variable */
  guint		newfile_signal_id;
  guint		newfolder_signal_id;

  /* drag'n'drop variables */
  gchar		 *dndtreepath;
  gint		 dndfilepos;
  /* Main App */
  PitiviMainApp  *mainapp;
};

/*
 * forward definitions
 */

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
PitiviSourceFile *
pitivi_sourcelistwindow_get_file(PitiviSourceListWindow *self);

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
    TEXT_LISTCOLUMN7,
    N_LISTCOLOUMN
  };

enum
  {
    FILEIMPORT_SIGNAL,
    FOLDERIMPORT_SIGNAL,
    LAST_SIGNAL
  };

static guint pitivi_sourcelistwindow_signal[LAST_SIGNAL] = { 0 };

static gint projectview_signals[LAST_SIGNAL] = {0};

static GtkItemFactoryEntry	TreePopup[] = {
  {"/New bin...", NULL, OnNewBin, 1, "<Item>", NULL},
  {"/Import", NULL, NULL, 0, "<Branch>", NULL},
  {"/Import/File", NULL, OnImportFile, 1, "<Item>", NULL},
  {"/Import/Folder", NULL, OnImportFolder, 1, "<Item>", NULL},
  {"/Import/Project", NULL, OnImportProject, 0, "<Item>", NULL},
  {"/Sep1", NULL, NULL, 0, "<Separator>"}, 
  {"/Find...", NULL, OnFind, 0, "<Item>", NULL},
  {"/Sep2", NULL, NULL, 0, "<Separator>"},
  {"/Project Window Options...", NULL, OnOptionProject, 0, "<Item>", NULL}
};

static gint	iNbTreePopup = sizeof(TreePopup)/sizeof(TreePopup[0]);

static GtkItemFactoryEntry	ListPopup[] = {
  {"/New", NULL, NULL, 0, "<Branch>", NULL},
  {"/New/Bin...", NULL, OnNewBin, 1, "<Item>", NULL},
  {"/New/Storyboard", NULL, NULL, 0, "<Item>", NULL},
  {"/New/Sep1", NULL, NULL, 0, "<Separator>"},
  {"/New/Title", NULL, NULL, 0, "<Item>", NULL},
  {"/New/Sep2", NULL, NULL, 0, "<Separator>"},
  {"/New/Offline file", NULL, NULL, 0, "<Item>", NULL},
  {"/Import", NULL, NULL, 0, "<Branch>", NULL},
  {"/Import/File", NULL, OnImportFile, 1, "<Item>", NULL},
  {"/Import/Folder", NULL, OnImportFolder, 1, "<Item>", NULL},
  {"/Import/Project", NULL, NULL, 0, "<Item>", NULL},
  {"/Sep3", NULL, NULL, 0, "<Separator>"},
  {"/Remove Unused Clips", NULL, NULL, 0, "<Item>", NULL},
  {"/Replace Clips...", NULL, NULL, 0, "<Item>", NULL},
  {"/Sep4", NULL, NULL, 0, "<Separator>"},
  {"/Automate to Timeline", NULL, NULL, 0, "<Item>", NULL},
  {"/Find...", NULL, NULL, 0, "<Item>", NULL},
  {"/Sep5", NULL, NULL, 0, "<Separator>"},
  {"/Project Window Options...", NULL, NULL, 0, "<Item>", NULL}
};

static gint	iNbListPopup = sizeof(ListPopup)/sizeof(ListPopup[0]);

static GtkItemFactoryEntry	ItemPopup[] = {
  {"/Cut", NULL, NULL, 0, "<Item>", NULL},
  {"/Copy", NULL, NULL, 0, "<Item>", NULL},
  {"/Clear", NULL, OnRemoveItem, 1, "<Item>", NULL},
  {"/Sep1", NULL, NULL, 0, "<Separator>"},
  {"/Properties", NULL, NULL, 0, "<Item>", NULL},
  {"/Set Clip Name Alias", NULL, NULL, 0, "<Item>", NULL},
  {"/Sep2", NULL, NULL, 0, "<Separator>"},
  {"/Insert at Edit Line", NULL, OnNewBin, 1, "<Item>", NULL},
  {"/Overlay at Edit Line", NULL, NULL, 0, "<Item>", NULL},
  {"/Sep3", NULL, NULL, 0, "<Separator>"},
  {"/Duration...", NULL, NULL, 0, "<Item>", NULL},
  {"/Speed...", NULL, NULL, 0, "<Item>", NULL},
  {"/Sep4", NULL, NULL, 0, "<Separator>"},
  {"/Open in Clip Window", NULL, NULL, 0, "<Item>", NULL},
  {"/Duplicate Clip...", NULL, NULL, 0, "<Item>", NULL},
  {"/Sep5", NULL, NULL, 0, "<Separator>"},
  {"/Project Windows Options...", NULL, NULL, 0, "<Item>"}
};

static gint	iNbItemPopup = sizeof(ItemPopup)/sizeof(ItemPopup[0]);

static GtkItemFactoryEntry	BinPopup[] = {
  {"/New", NULL, NULL, 0, "<Branch>", NULL},
  {"/New/Bin...", NULL, OnNewBin, 1, "<Item>", NULL},
  {"/New/Storyboard", NULL, NULL, 0, "<Item>", NULL},
  {"/New/Sep1", NULL, NULL, 0, "<Separator>"},
  {"/New/Title", NULL, NULL, 0, "<Item>", NULL},
  {"/Remove", NULL, OnRemoveBin, 1, "<Item>", NULL}
};

static gint	iNbBinPopup = sizeof(BinPopup)/sizeof(BinPopup[0]);

static gchar	*BaseMediaType[] = 
  {
    "video/x-raw-rgb", 
    "video/x-raw-yuv", 
    "audio/x-raw-float",
    "audio/x-raw-int",
    0
  };

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
  gpointer	data;
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

  pitivi_projectsourcelist_showfile(((PitiviProjectWindows*)self)->project->sources, self->private->treepath);
}
void	
pitivi_sourcelistwindow_set_media_property(PitiviSourceListWindow *self,
					   gchar *caps_str)
{
  gchar	**property;
  gchar	*tmpstring;
  gchar	*savstring;
  gchar	*value;
  gint	nbentry;
  gint	i;
  gint	j;

  
  nbentry = 1;

  tmpstring = caps_str;
  while (*tmpstring)
    {
      if (*tmpstring == ',')
	nbentry++;
      tmpstring++;
    }
     
 
  property = g_malloc((nbentry + 1) * sizeof(gchar *));

  /* cut the string */
  tmpstring = g_strdup(caps_str);
  savstring = tmpstring;

  i = 0;
  
  while (*tmpstring)
    {
      if (*tmpstring == ',')
	{
	  *tmpstring = 0;
	  property[i] = savstring;
	  i++;
	  tmpstring++;
	  /* for space */
	  tmpstring++;
	  savstring = tmpstring;
	}
      tmpstring++;
    }
  property[i] = savstring;
  property[i+1] = NULL;

  if (strstr(caps_str, "video"))
    {
      self->private->havevideo = TRUE;
      j = 0;
      if (property[j])
	{
	  self->private->infovideo = g_strdup(property[j]);
	}
    }
  if (strstr(caps_str, "audio"))
    {
      self->private->haveaudio = TRUE;
      j = 0;
      if (property[j])
	{
	  self->private->infoaudio = property[j];
	}
    }
}

gboolean
pitivi_sourcelistwindow_check_for_base_type(gchar *mediatype)
{
  gint	i;

  i = 0;
/*   g_printf("mediatype to match ==> %s\n", mediatype); */

  while (BaseMediaType[i])
    {
     /*  g_printf("Base Media Type ==> %s\n", BaseMediaType[i]); */
      if (strstr(mediatype, BaseMediaType[i]))
	return FALSE;
      i++;
    }
  return TRUE;
}

void	have_type_handler(GstElement *typefind, guint probability,
			  const GstCaps *caps, gpointer data)
{
  PitiviSourceListWindow *self = (PitiviSourceListWindow*)data;
  gchar *caps_str;
  gchar *tmp_str;

  self->private->mediacaps = gst_caps_copy(caps);
  caps_str = gst_caps_to_string(caps);

  tmp_str = caps_str;
  /* basic parsing */
  while (*tmp_str != 0)
    {
      if (*tmp_str == ',')
	{
	  *tmp_str = 0;
	  break;
	}
      tmp_str++;
    }

  self->private->mediatype = caps_str;
}

void	eof(GstElement *src)
{
  //g_printf("== have eos ==\n");
}

void	new_pad_created(GstElement *parse, GstPad *pad, gpointer data)
{
  PitiviSourceListWindow *self = (PitiviSourceListWindow*)data;
  
  gchar	*padname;
  PitiviSettings	*settings;
  gchar	*tmp;

  //g_printf("a new pad %s was created\n", gst_pad_get_name(pad));

  //g_printf("caps is ==> %s\n", gst_caps_to_string(gst_pad_get_caps(pad)));

  self->private->padlist = g_slist_append(self->private->padlist, pad);  
}

void
pitivi_sourcelistwindow_get_pad_list(GstElement *elm)
{

}

void	test_video_length(PitiviSourceListWindow *self, GstElement *lastelm);

GstElement*	
pitivi_sourcelistwindow_add_decoder(PitiviSourceListWindow *self, gchar *filename)
{
  PitiviMainApp	*mainapp = ((PitiviWindows *) self)->mainapp;
  GstElement	*demuxer;
  GstElement	*thread;
  GstElement	*queue;
  GstElement	*decoder;
  GstElement	*parser;
  GstElement	*lastelement;
  GstPad	*pad;
  GstCaps	*caps;
  GList       	*decoderlist;
  GSList	*padlist;
  GList		*parserlist;
  gchar		*caps_str;
  gchar		*name;
  static gint	thread_number = 0;
  gboolean	flag;

  g_printf("pitivi_sourcelistwindow_add_decoder start\n");
  gst_element_set_state(GST_ELEMENT(self->private->pipeline), GST_STATE_PLAYING);
  padlist = self->private->padlist;
  while (padlist)
    {
      g_printf("iterate from padlist\n");
      thread = NULL;
      flag = FALSE;
      pad = (GstPad*)padlist->data;

      caps = gst_pad_get_caps(pad);
  
      caps_str = gst_caps_to_string(caps);
      
      self->private->mediatype = caps_str;
      
      thread = decoder = parser = lastelement = NULL;
      g_printf("caps to search for %s\n", gst_caps_to_string(caps));
      while (pitivi_sourcelistwindow_check_for_base_type(self->private->mediatype))
	{
	  g_printf("caps ==> %s\n", gst_caps_to_string(caps));
	  decoderlist = pitivi_settings_get_flux_codec_list (G_OBJECT(pitivi_mainapp_settings( mainapp )), caps, DEC_LIST);
	  
	  flag = FALSE;
	  if (decoderlist)
	    {
	      if (!thread)
		{
		  flag = TRUE;
		  name = g_strdup_printf("thread%d", thread_number);
		  
		  /* create a thread for the decoder pipeline */
		  thread = gst_thread_new(name);
		  g_assert(thread != NULL);
		   
		  g_free(name);
		}
	      g_printf("adding decoder [%s] after demux\n", decoderlist->data);

	      /* choose the first decoder */
	      name = g_strdup_printf("decoder%d", thread_number);
	      decoder = gst_element_factory_make((gchar*)decoderlist->data, name);

	      g_assert(decoder != NULL);
	      g_free(name);
	      
	      
	      self->private->mediatype = gst_caps_to_string(gst_pad_get_caps(gst_element_get_pad(decoder, "src")));
	      self->private->mediacaps = gst_pad_get_caps(gst_element_get_pad(decoder, "src"));
	       
	      /* g_printf("ouput caps ==> %s\n", self->private->mediatype); */
	      pitivi_sourcelistwindow_get_pad_list(decoder);
	      if (flag)
		{
		  /* create a queue for link the pipeline with the thread */
		  
		  name = g_strdup_printf("queue%d", thread_number);
		  queue = gst_element_factory_make("queue", name);
		  g_assert(queue != NULL);
		  g_free(name);
		  
		  /* add the elements to the thread */
		  gst_bin_add_many(GST_BIN(thread), queue, decoder, NULL);
		  // gst_element_add_ghost_pad(thread, gst_element_get_pad(queue, "sink"), "sink");
		  /* link the elements */
		  gst_element_link(queue, decoder);
		  
		  /* add the thread to the main pipeline */
		  gst_bin_add(GST_BIN(self->private->pipeline), thread);
		  
		  /* link the pad to the sink pad of the thread */
		  gst_pad_link(pad, gst_element_get_pad(queue, "sink"));
		  
		}
	      else
		{
		  gst_bin_add(GST_BIN(thread), decoder);	       
		  
		  /* link the elements */
		  gst_element_link(parser, decoder);
		}
	      
	      lastelement = decoder;
	    }
	  else
	    {
	      parserlist = pitivi_settings_get_flux_parser_list(G_OBJECT(pitivi_mainapp_settings( mainapp )), caps, DEC_LIST);
	      
	      flag = FALSE;
	      
	      if (parserlist)
		{
		
		  if (!thread)
		    {
		      flag = TRUE;
		      name = g_strdup_printf("thread%d", thread_number);
		  
		      /* create a thread for the decoder pipeline */
		      thread = gst_thread_new(name);
		      g_assert(thread != NULL);
		  
		      g_free(name);
		    }
		 

		  g_printf("adding parser [%s] after demux ==> %s\n", (gchar*)parserlist->data);
		  name = g_strdup_printf("parser_%s", filename);
		  parser = gst_element_factory_make((gchar*)parserlist->data, name);
		  g_free(name);
		  g_assert(parser != NULL);
		  
		  self->private->mediatype = gst_caps_to_string(gst_pad_get_caps(gst_element_get_pad(parser, "src")));
		  self->private->mediacaps = gst_pad_get_caps(gst_element_get_pad(parser, "src"));
/* 		  g_printf("ouput caps ==> %s\n", self->private->mediatype); */
		  pitivi_sourcelistwindow_get_pad_list(parser);
		  //g_printf("parser media type ==> %s\n", self->private->mediatype);
		  caps = self->private->mediacaps;

		  if (flag)
		    {
		      /* create a queue for link the pipeline with the thread */
		      
		      name = g_strdup_printf("queue%d", thread_number);
		      queue = gst_element_factory_make("queue", name);
		      g_assert(queue != NULL);
		      g_free(name);
		      
		      /* add the elements to the thread */
		      gst_bin_add_many(GST_BIN(thread), queue, parser, NULL);
		      /*
		      gst_element_add_ghost_pad(thread, gst_element_get_pad(queue,
									"sink"),
						"sink");
		      */
		      /* link the elements */
		      gst_element_link(queue, parser);
		  
		      /* add the thread to the main pipeline */
		      gst_bin_add(GST_BIN(self->private->pipeline), thread);
		  
		      /* link the pad to the sink pad of the thread */
		      gst_pad_link(pad, gst_element_get_pad(queue, "sink"));
		      
		    }
		  else
		    {
		      gst_bin_add(GST_BIN(thread), parser);
		      		      
		      gst_element_link(decoder, parser);

		    }
		  lastelement = parser;
		  
		} 
	    }
	}
      //g_printf("setting to READY state\n");
      pitivi_sourcelistwindow_set_media_property(self, caps_str);

      if (lastelement)
	{
	  GstPad	*temppad;
	 
	  if (strstr(caps_str, "video")) /* video*/
	    {
	      GstElement	*sink;
	      temppad = gst_element_add_ghost_pad(self->private->pipeline, gst_element_get_pad(lastelement, "src"),
				    "vsrc");
	      g_assert(temppad != NULL);
	      g_printf("adding ghost pad for video\n");
	      test_video_length(self, lastelement);
	    }
	  else /* audio */
	    {
	      temppad = gst_element_add_ghost_pad(self->private->pipeline, gst_element_get_pad(lastelement, "src"),
						  "asrc");
	      g_assert(temppad != NULL);
	      g_printf("adding ghost pad for audio\n");
	    }
	}
      if (thread)
	{
	  gst_element_set_state(GST_ELEMENT(thread), GST_STATE_READY);
	  thread_number++;
	}
      else /* we have a raw data pad */
	{
	  GstPad	*temppad;
	  
	  if (strstr(caps_str, "video")) /* video*/
	    {
	      temppad = gst_element_add_ghost_pad(self->private->pipeline, pad,
						  "vsrc");
	      g_assert(temppad != NULL);
	      g_printf("linking raw pad to vsrc\n");
	    }
	  else
	    {
	      temppad = gst_element_add_ghost_pad(self->private->pipeline, pad,
						  "asrc");
	      g_assert(temppad != NULL);
	      g_printf("linking raw pad to asrc\n");
	    }
	}
      
      padlist = padlist->next;
    }
 
  gst_element_set_state(GST_ELEMENT(self->private->pipeline), GST_STATE_PAUSED);
  return lastelement;
}

void	test_audio_length(PitiviSourceListWindow *self, GstElement *lastelm)
{
  GstElement	*fakesink;
  GstFormat	format;
  gint64	value;

  gst_element_set_state(self->private->mainpipeline, GST_STATE_PLAYING);
  format = GST_FORMAT_DEFAULT;
  if (gst_element_query(lastelm, GST_QUERY_TOTAL, &format, &value))
    g_printf("format ==> %d\ntime ==> %lld\n", format, value);
  else
    g_printf("Couldn't perform requested query\n");

  gst_element_set_state(self->private->mainpipeline, GST_STATE_PAUSED);
}

void	test_video_length(PitiviSourceListWindow *self, GstElement *lastelm)
{
  GstFormat	format;
  gint64	value;

  gst_element_set_state(self->private->mainpipeline, GST_STATE_PLAYING);
  format = GST_FORMAT_BYTES;
  if (gst_element_query(lastelm, GST_QUERY_TOTAL, &format, &value))
    g_printf("format ==> %d\ntime ==> %lld\n", format, value);
  else
    g_printf("Couldn't perform requested query\n");

  gst_element_set_state(self->private->mainpipeline, GST_STATE_PAUSED);
}

gboolean	build_pipeline_by_mime(PitiviSourceListWindow *self, gchar *filename)
{
  GList *elements;
  GstElementFactory *factory;
  GList	*plugins;
  GstEvent	*event;
  GstFormat	format;
  gint64	value;
  GstElement	*src;
  GstElement	*demux;
  GstElement	*decoder;
  GstElement	*parser;
  GstElement	*thread;
  GstElement	*lastelement;

  GList		*demuxlist;
  GList		*decoderlist;
  GList		*parserlist;
  GstCaps	*caps;
  GstCaps	*caps_sav;
  gchar		*tmpname;
  guint16	id;
  gint		i;
  gboolean	element_found;
  PitiviMainApp	*mainapp = ((PitiviWindows *) self)->mainapp;
  

  /* Init some variables */
  demux = decoder = parser = lastelement = NULL;
  self->private->padlist = NULL;

  /* create a pipeline */
  tmpname = g_strdup_printf("pipeline_%s", filename);
  self->private->mainpipeline = gst_pipeline_new(tmpname);
  g_free(tmpname);
  g_assert(self->private->mainpipeline != NULL);

  tmpname = g_strdup_printf("bin_%s", filename);
  self->private->pipeline = gst_bin_new(tmpname);
  g_free(tmpname);

  gst_bin_add(GST_BIN(self->private->mainpipeline), self->private->pipeline);
  /* create a file reader */
  tmpname = g_strdup_printf("src_%s", filename);
  src = gst_element_factory_make("filesrc", tmpname);
  g_free(tmpname);
  
  g_object_set(G_OBJECT(src), "location", filename, NULL);

  /* add the file reader to the pipeline */
  gst_bin_add(GST_BIN(self->private->pipeline), src);

  g_signal_connect(G_OBJECT(src), "eos",
		   G_CALLBACK(eof), NULL);

  element_found = FALSE;
  /* loop until we found a base type */
  while (pitivi_sourcelistwindow_check_for_base_type(self->private->mediatype) && !element_found)
    {
      /* test if it's a container */
      demuxlist = pitivi_settings_get_flux_container_list (G_OBJECT(pitivi_mainapp_settings( mainapp )),
							   self->private->mediacaps, DEC_LIST);
      /* create a demuxer if it's a container */
      if (demuxlist)
	{
	  /* choose the first demuxer */
	  g_printf("adding demuxer [%s]\n", demuxlist->data);
	  tmpname = g_strdup_printf("demux_%s", filename);
	  demux = gst_element_factory_make((gchar*)demuxlist->data, tmpname);
	  g_free(tmpname);
	  g_assert(demux != NULL);
	  
	  /* add the demuxer to the main pipeline */
	  gst_bin_add(GST_BIN(self->private->pipeline), demux);
	  
	  g_signal_connect(G_OBJECT(demux), "new_pad",
			   G_CALLBACK(new_pad_created), self);
	  
	  /* link element */
	  if (parser)
	    gst_element_link(parser, demux);
	  else
	    gst_element_link(src, demux);
	  element_found = TRUE;

	  /* we need to run this part only for a demuxer */

	  gst_element_set_state(GST_ELEMENT(self->private->mainpipeline), GST_STATE_PLAYING);
  
	  for (i = 0; i < 50; i++)
	    {
	      gst_bin_iterate(GST_BIN(self->private->mainpipeline));
	      //g_printf("iterate pipeline\n");
	    }
	  
	  pitivi_sourcelistwindow_add_decoder(self, filename);
	  

	  gst_element_set_state(GST_ELEMENT(self->private->mainpipeline), 
 				GST_STATE_PAUSED);
	  
	  /* we have already set all ghost pad here */
	  lastelement = NULL;
	}
      else /* search for a decoder */
	{
	  decoderlist = pitivi_settings_get_flux_codec_list (G_OBJECT(pitivi_mainapp_settings( mainapp )),
							     self->private->mediacaps, DEC_LIST);
	  if (decoderlist)
	    {
	      /* choose the first decoder */
	      g_printf("adding a decoder [%s] for this caps ==> %s\n", 
		       decoderlist->data,
		       gst_caps_to_string(self->private->mediacaps));
	      tmpname = g_strdup_printf("decoder_%s", filename);
	      decoder = gst_element_factory_make((gchar*)decoderlist->data, tmpname);
	      g_free(tmpname);
	      g_assert(decoder != NULL);
	      
/* 	      add the decoder to the main pipeline */
	      gst_bin_add(GST_BIN(self->private->pipeline), decoder);
	      
	      gst_element_link(src, decoder);
	  
	      self->private->mediatype = gst_caps_to_string(gst_pad_get_caps(gst_element_get_pad(decoder, "src")));
	      self->private->mediacaps = gst_pad_get_caps(gst_element_get_pad(decoder, "src"));
	      
	      pitivi_sourcelistwindow_set_media_property(self, self->private->mainmediatype);

	      format = GST_FORMAT_TIME;
	      gst_element_query(decoder, GST_FORMAT_TIME, &format, &value);
	      g_printf("format ==> %d\ntime ==> %lld\n", format, (value / GST_SECOND) / 60);
	      element_found = TRUE;
	      lastelement = decoder;
	    }
	  else /* search for parser */
	    {
	      parserlist = pitivi_settings_get_flux_parser_list(G_OBJECT(pitivi_mainapp_settings( mainapp )), self->private->mediacaps, DEC_LIST);
	      
	      if (parserlist)
		{
		  g_printf("adding parser [%s] for this caps ==> %s\n", 
			   parserlist->data, 
			   gst_caps_to_string(self->private->mediacaps));
		  tmpname = g_strdup_printf("parser_%s", filename);
		  parser = gst_element_factory_make((gchar*)parserlist->data, tmpname);
		  g_free(tmpname);
		  g_assert(parser != NULL);

/* 		  add the parser to the main pipeline */
		  gst_bin_add(GST_BIN(self->private->pipeline), parser);

		  gst_element_link(src, parser);
		  
		  self->private->mediatype = gst_caps_to_string(gst_pad_get_caps(gst_element_get_pad(parser, "src")));
		  self->private->mediacaps = gst_pad_get_caps(gst_element_get_pad(parser, "src"));
		  
		  pitivi_sourcelistwindow_set_media_property(self, self->private->mainmediatype);
		  lastelement = parser;
		}
	      else
		g_printf("no parser found\n");
	    }
	} 
  
    }
  if (lastelement)
    {
      GstPad *temppad;

      if (strstr(self->private->mediatype, "video"))
	{
	  temppad = gst_element_add_ghost_pad(self->private->pipeline, 
					      gst_element_get_pad(lastelement, "src"),
					      "vsrc");
	  g_assert(temppad != NULL);

	  g_printf("adding ghost pad video in the main pipeline\n");
	}
      else /* audio */
	{
	  temppad = gst_element_add_ghost_pad(self->private->pipeline, 
					      gst_element_get_pad(lastelement, "src"),
					      "asrc");
	  g_assert(temppad != NULL);

	  g_printf("adding ghost pad audio in the main pipeline\n");
	}
    }
  /* adding fakesink */
  if (self->private->haveaudio && src)
    test_audio_length(self, src);
  else if (self->private->havevideo)
    test_video_length(self, src);
  /* need to do this */
  gst_object_ref(GST_OBJECT(self->private->pipeline));
  gst_bin_remove(GST_BIN(self->private->mainpipeline), self->private->pipeline);
  gst_object_unref( (GstObject *) self->private->mainpipeline);
}

void	pitivi_sourcelistwindow_type_find(PitiviSourceListWindow *self)
{
  GstElement	*pipeline;
  GstElement	*source;
  GstElement	*typefind;
  gchar		*filename;

  filename = self->private->filepath;

  pipeline = gst_pipeline_new(NULL);
  source = gst_element_factory_make("filesrc", "source");
  g_assert(GST_IS_ELEMENT(source));

  typefind = gst_element_factory_make("typefind", "typefind");
  g_assert(GST_IS_ELEMENT(typefind));

  gst_bin_add_many(GST_BIN(pipeline), source, typefind, NULL);
  gst_element_link(source, typefind);

  g_signal_connect(G_OBJECT(typefind), "have-type",
		   G_CALLBACK(have_type_handler), self);

  gst_element_set_state(GST_ELEMENT(pipeline), GST_STATE_NULL);
  g_object_set(source, "location", filename, NULL);
  gst_element_set_state(GST_ELEMENT(pipeline), GST_STATE_PLAYING);

  g_printf("preparing to iterate pipeline\n");

  while (self->private->mediatype == NULL)
    gst_bin_iterate(GST_BIN(pipeline));

  g_printf("finish iteration on pipeline\n");

  gst_element_set_state(GST_ELEMENT(pipeline), GST_STATE_NULL);

  if (!strstr(self->private->mediatype, "video") 
      && !strstr(self->private->mediatype, "audio")
      && !strstr(self->private->mediatype, "application/ogg")
      && !strstr(self->private->mediatype, "application/x-id3") )
    {
 /*      g_printf("media type ==> %s\n", self->private->mediatype); */
      self->private->mediatype = NULL;
    }

  g_object_unref(pipeline);

  if (self->private->mediatype == NULL)
    return;

  self->private->infovideo = NULL;
  self->private->infoaudio = NULL;
  self->private->length = 0;
  self->private->havevideo = FALSE;
  self->private->haveaudio = FALSE;

  /*   save main stream */
  self->private->mainmediatype = self->private->mediatype;

  build_pipeline_by_mime(self, filename);

  /* restore main mime type */
  /* g_printf("mediatype ==> %p\n", self->private->mediatype); */
  g_free(self->private->mediatype);
  self->private->mediatype = NULL;

/*   g_printf("havevideo ==> %d\n", self->private->havevideo); */
/*   g_printf("haveaudio ==> %d\n", self->private->haveaudio); */

  if (self->private->havevideo && !self->private->haveaudio)
    self->private->mediatype = g_strdup("video");
  if (self->private->haveaudio && self->private->havevideo)
    {
      self->private->mediatype = g_strdup("video/audio");
    }
  if (self->private->haveaudio && !self->private->havevideo)
    self->private->mediatype = g_strdup("audio");

/*   g_printf("mediatype ==> %p\n", self->private->mediatype); */
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
  gchar	*filename;
  
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
  GtkTreeIter	iter2;
  GtkTreeIter	*ret_iter;
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
		     &iter, BMP_LISTCOLUMN1, pixbufa,
		     TEXT_LISTCOLUMN2, name,
		     TEXT_LISTCOLUMN3, sMediaType,
		     TEXT_LISTCOLUMN4, "",
		     TEXT_LISTCOLUMN5, "",
		     TEXT_LISTCOLUMN6, "",
		     TEXT_LISTCOLUMN7, "",
		     -1);
    
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
				 G_TYPE_STRING, G_TYPE_STRING);

  
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

  g_printf("adding a new folder\n");

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

gboolean	pitivi_sourcelistwindow_set_file(PitiviSourceListWindow *self)
{
  GtkTreeIter	pIter;
  GtkListStore	*liststore;
  GdkPixbuf	*pixbufa;
  gchar		*sTexte;
  gchar		*name;
  gchar		*sExempleTexte;
  gboolean	add;
  gint		selected_row;
  gint		depth;
  static int	i = 0;

  selected_row = 0;
  if (self->private->treepath != NULL)
    selected_row = get_selected_row(self->private->treepath, &depth);

  /* use gstreamer to check the file type */
  self->private->mediatype = NULL;
  pitivi_sourcelistwindow_type_find(self);

  if (self->private->mediatype == NULL)
    {
      /* do not add file to sourcelist */
      g_free(self->private->filepath);
      return FALSE;
    }

  sTexte = g_malloc(12);
  sExempleTexte = g_malloc(12);

  sprintf(sTexte, "Ligne %d\0", i);
  sprintf(sExempleTexte, "exemple %d\0", i);
  
 /*  if (self->private->havevideo && self->private->haveaudio) */
/*     pixbufa = gtk_widget_render_icon(self->private->listview,  */
/* 				     PITIVI_STOCK_EFFECT_SOUNDTV, */
/* 				     GTK_ICON_SIZE_MENU, NULL); */
/*   else */ 
  if (self->private->havevideo)
    pixbufa = gtk_widget_render_icon(self->private->listview, 
				     PITIVI_STOCK_EFFECT_TV,
				     GTK_ICON_SIZE_MENU, NULL);
  else
    pixbufa = gtk_widget_render_icon(self->private->listview, 
				     PITIVI_STOCK_EFFECT_SOUND,
				     GTK_ICON_SIZE_MENU, NULL);

  /* Creation de la nouvelle ligne */
  liststore = get_liststore_for_bin(self, selected_row);
  gtk_list_store_append(liststore, &pIter);
  
  name = strrchr(self->private->filepath, '/');
  name++;

  /* Mise a jour des donnees */
  gtk_list_store_set(liststore,
		     &pIter, BMP_LISTCOLUMN1, pixbufa,
		     TEXT_LISTCOLUMN2, name,
		     TEXT_LISTCOLUMN3, self->private->mediatype,
		     TEXT_LISTCOLUMN4, g_strdup_printf("%lld", self->private->length),
		     TEXT_LISTCOLUMN5, self->private->infovideo,
		     TEXT_LISTCOLUMN6, self->private->infoaudio,
		     TEXT_LISTCOLUMN7, sExempleTexte,
		     -1);
  i++;
  

  g_free(sTexte);
  g_free(sExempleTexte);

  g_object_unref(pixbufa);

  return TRUE;
}

void	new_file(GtkWidget *widget, gpointer data)
{
  PitiviSourceListWindow *self = (PitiviSourceListWindow*)data;

  if (!pitivi_sourcelistwindow_set_file(self))
    return;

 /*  pitivi_projectsourcelist_showfile(self->private->prjsrclist, selected_row); */
  /* call pitivi_projectsourcelist_add_file_to_bin */
  pitivi_projectsourcelist_add_file_to_bin(((PitiviProjectWindows*)self)->project->sources, 
						 self->private->treepath,
						 self->private->filepath,
						 self->private->mediatype,
						 self->private->infovideo,
						 self->private->infoaudio,
						 0 /* self->private->length */,
						 self->private->pipeline);
  
  g_free(self->private->mediatype);
  if (self->private->infovideo)
    g_free(self->private->infovideo);
  if (self->private->infoaudio)
    g_free(self->private->infoaudio);

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

  /* creation du model pour le nouveau bin */
  liststore = gtk_list_store_new(N_LISTCOLOUMN, GDK_TYPE_PIXBUF,
				 G_TYPE_STRING, G_TYPE_STRING,
				 G_TYPE_STRING, G_TYPE_STRING,
				 G_TYPE_STRING, G_TYPE_STRING);
  
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

GtkWidget	*create_menupopup(PitiviSourceListWindow *self, 
				  GtkItemFactoryEntry *pMenuItem, 
				  gint iNbMenuItem)
{
  GtkWidget		*pMenu;
  GtkItemFactory	*pItemFactory;
  GtkAccelGroup		*pAccel;

  pAccel = gtk_accel_group_new();

  /* Creation du menu */
  pItemFactory = gtk_item_factory_new(GTK_TYPE_MENU, "<menu>", NULL);
  
  /* Recuperation des elements du menu */
  gtk_item_factory_create_items(pItemFactory, iNbMenuItem, pMenuItem, self);

  /* Recuperation du widget pour l'affichage du menu */
  pMenu = gtk_item_factory_get_widget(pItemFactory, "<menu>");

  gtk_widget_show_all(pMenu);

  return pMenu;
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

  g_printf("filepos ==> %d\n", self->private->dndfilepos);
  gtk_tree_model_get_iter_first(model, &iternext);
  selected_list_row = self->private->dndfilepos;
  item_select = 0;
  folder_select = 0;
  
  i = 0;
  
  while (i++ < selected_list_row)
    {
      gtk_tree_model_get(model, &iternext, TEXT_LISTCOLUMN3, &tmpMediaType, -1);
      if (!strcmp(tmpMediaType, "Bin"))
	folder_select++;
      else
	item_select++;
      gtk_tree_model_iter_next(model, &iternext);
    }
  g_printf("real filepos is ==> %d\n", item_select);
  self->private->dndfilepos = item_select;
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
		  gpointer editor)
{
  PitiviSourceListWindow	*self = PITIVI_SOURCELISTWINDOW(editor);
  PitiviSourceFile	*sf;
  gchar			*tmp;

  sf = pitivi_projectsourcelist_get_sourcefile(PITIVI_PROJECTWINDOWS(self)->project->sources,
					       self->private->dndtreepath,
					       self->private->dndfilepos);
  if (!sf)
    return ;
  g_printf("sending pipeline ==> %p\n", sf->pipeline);
  /* convert the pointer to it's character represenation in long long int */
  gtk_selection_data_set (selection_data, selection_data->target, 8, (void *)sf , sizeof (PitiviSourceFile));
}

static void
drag_data_delete_cb (GtkWidget          *widget,
		     GdkDragContext     *context,
		     gpointer editor)
{

}



PitiviMainApp  *
pitivi_sourcelistwindow_get_mainApp (PitiviSourceListWindow	*source)
{
  return ( source->private->mainapp );
}

GtkWidget	*create_listview(PitiviSourceListWindow *self,
				 GtkWidget *pWindow)
{
  GtkWidget		*menupopup;
  GtkWidget		*pListView;
  GtkWidget		*pScrollbar;
  GtkTreeViewColumn	*pColumn;
  GtkCellRenderer      	*pCellRenderer;
  GdkColormap		*colormap;
  GdkPixmap		*pixmap;
  GdkBitmap		mask;

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
  g_signal_connect (pListView, "drag_data_delete",
		    G_CALLBACK (drag_data_delete_cb), self);

  /* Customizing Drag 'n Drop image on cursor better for customization 
   * Later user Transparency. 
   */

  colormap = gtk_widget_get_colormap (pListView);
  /*  pixmap = gdk_pixmap_colormap_create_from_xpm_d (pListView->window, 
						  colormap, 
						  NULL,  
						  NULL,
						  backward_xpm);
  gtk_drag_source_set_icon (pListView, colormap, pixmap, NULL);
  */
  self->private->listview = pListView;
  
  /* Creation du menu popup */
  self->private->listmenu = create_menupopup(self, ListPopup, iNbListPopup);

  g_signal_connect_swapped(G_OBJECT(pListView), "button_press_event",
			   G_CALLBACK(my_popup_handler), 
			   GTK_OBJECT(self));
  g_signal_connect(G_OBJECT(pListView), "row-activated", 
		   (GCallback) on_row_activated, GTK_OBJECT(self));



  /* Creation de la premiere colonne */
  pCellRenderer = gtk_cell_renderer_pixbuf_new();
  pColumn = gtk_tree_view_column_new_with_attributes("Elements", pCellRenderer,
						     "pixbuf", BMP_LISTCOLUMN1,
						     NULL);
  
  /* Ajout de la colonne a la vue */
  gtk_tree_view_append_column(GTK_TREE_VIEW(pListView), pColumn);

  /* Creation de la deuxieme colonne */
  pCellRenderer = gtk_cell_renderer_text_new();
  pColumn = gtk_tree_view_column_new_with_attributes("Nom", pCellRenderer,
						     "text", TEXT_LISTCOLUMN2,
						     NULL);
  
  /* Ajout de la colonne a la vue */
  gtk_tree_view_append_column(GTK_TREE_VIEW(pListView), pColumn);

  /* Creation de la troisieme colonne */
  pCellRenderer = gtk_cell_renderer_text_new();
  pColumn = gtk_tree_view_column_new_with_attributes("Type de media",
						     pCellRenderer,
						     "text", TEXT_LISTCOLUMN3,
						     NULL);
  
  /* Ajout de la colonne a la vue */
  gtk_tree_view_append_column(GTK_TREE_VIEW(pListView), pColumn);

  /* Creation de la quatrieme colonne */
  pCellRenderer = gtk_cell_renderer_text_new();
  pColumn = gtk_tree_view_column_new_with_attributes("Duree", pCellRenderer,
						     "text", TEXT_LISTCOLUMN4,
						     NULL);
  
  /* Ajout de la colonne a la vue */
  gtk_tree_view_append_column(GTK_TREE_VIEW(pListView), pColumn);

  /* Creation de la cinquieme colonne */
  pCellRenderer = gtk_cell_renderer_text_new();
  pColumn = gtk_tree_view_column_new_with_attributes("Info video",
						     pCellRenderer,
						     "text", TEXT_LISTCOLUMN5,
						     NULL);
  
  /* Ajout de la colonne a la vue */
  gtk_tree_view_append_column(GTK_TREE_VIEW(pListView), pColumn);

  /* Creation de la sixieme colonne */
  pCellRenderer = gtk_cell_renderer_text_new();
  pColumn = gtk_tree_view_column_new_with_attributes("Info audio",
						     pCellRenderer,
						     "text", TEXT_LISTCOLUMN6,
						     NULL);
  
  /* Ajout de la colonne a la vue */
  gtk_tree_view_append_column(GTK_TREE_VIEW(pListView), pColumn);

  /* Creation de la septieme colonne */
  pCellRenderer = gtk_cell_renderer_text_new();
  pColumn = gtk_tree_view_column_new_with_attributes("Commentaire",
						     pCellRenderer,
						     "text", TEXT_LISTCOLUMN7,
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

GtkWidget	*create_treeview(PitiviSourceListWindow *self,
				 GtkWidget *pScrollbar)
{
  GtkWidget		*pTreeView;
  GtkWidget		*menupopup;
  GtkTreeViewColumn	*pColumn;
  GtkCellRenderer	*pCellRenderer;
  GtkTreeSelection	*selection;

  /* Creation du modele */
  self->private->treestore = gtk_tree_store_new(N_TREECOLUMN, GDK_TYPE_PIXBUF, 
						G_TYPE_STRING);  

  /* Creation de la vue */
  pTreeView = gtk_tree_view_new_with_model(GTK_TREE_MODEL(self->private->treestore));

  self->private->treeview = pTreeView;

  /* Creation du menu popup */
  self->private->treemenu = create_menupopup(self, TreePopup, iNbTreePopup);

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
/*        else */
/* 	 { */
/* 	   //g_printf("cleanning %s\n", name); */
/* 	   /\* remove_all_row_from_listview(self); *\/ */
/* 	 } */
      
    }
  return TRUE;
}

void	on_row_activated (GtkTreeView        *listview,
			  GtkTreePath        *path,
			  GtkTreeViewColumn  *col,
			  gpointer            userdata)
{
  PitiviSourceListWindow *self = (PitiviSourceListWindow*)userdata;
  PitiviWindows *window = (PitiviWindows*)self;
  PitiviViewerWindow	*viewerwin;
  GtkListStore	*liststore;
  GtkTreeIter	iter;
  GtkTreeIter		iternext;
  gint			selected_list_row;
  gint			item_select;
  gint			folder_select;
  gint			i;
  gchar			*sMediaType;
  PitiviSourceFile	*sf;
  gboolean		flag;
  GtkTreeSelection	*selection;

  g_printf("you double click me\n");

  g_printf("with the following value ==> [%s]\n", gtk_tree_path_to_string(path));
  /* set the lispath */
  self->private->listpath = gtk_tree_path_to_string(path);
  sf = pitivi_sourcelistwindow_get_file(self);
  g_printf("ici %p\n", sf);
  if (!sf && OnSelectItem(self, &iter, &liststore, &sMediaType, &item_select, 
			  &folder_select))
    {
      if (!strcmp(sMediaType, "Bin"))
	{
	  char	*folder;
	  GtkTreePath	*path;

	  g_printf("you select a bin\n");
	  /* we need to select the corresponding bin in the treeview */
	  selection = gtk_tree_view_get_selection(GTK_TREE_VIEW(self->private->treeview));
	  
	  folder = g_strdup_printf(":%d", folder_select);
	  strcat(self->private->treepath, folder);
	  g_printf("with the following path [%s]\n", self->private->treepath);
	  path = gtk_tree_path_new_from_string(self->private->treepath);
	  /* path = gtk_tree_path_new_from_string("1"); */
	  if (!path)
	    g_printf("path is not valid\n");
	  gtk_tree_model_get_iter(GTK_TREE_MODEL(self->private->treestore),
				  &iter, path);
	  gtk_tree_view_expand_to_path(GTK_TREE_VIEW(self->private->treeview), 
				       path);
	  gtk_tree_selection_select_iter(selection, &iter);
	  
	  if (gtk_tree_selection_iter_is_selected(selection, &iter))
	    g_printf("the item is currently selected\n");
	  else
	    g_printf("the item is not selected\n");
	  
	}
	  
      return;
    }
  
  g_printf("get [%s]\n", sf->filename);
  viewerwin = (PitiviViewerWindow*)pitivi_mainapp_get_viewerwin(window->mainapp);
  pitivi_viewerwindow_set_source(viewerwin, sf);
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
		 
		      pMenu = GTK_MENU(create_menupopup(self, ItemPopup, 
							iNbItemPopup));
		    }
		  else
		    pMenu = GTK_MENU(create_menupopup(self, BinPopup,
						      iNbBinPopup));
		}
	      else
		{
		  if (self->private->listview == user_data)
		    pMenu = GTK_MENU(self->private->listmenu);
		  else
		    pMenu = GTK_MENU(self->private->treemenu);
		}
	    }
	  gtk_menu_popup(pMenu, NULL, NULL, NULL, NULL,
			 event_button->button, event_button->time);
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

void	OnImportFile(gpointer data, gint action, GtkWidget *widget)
{
  PitiviSourceListWindow	*self = (PitiviSourceListWindow*)data;
  GtkWidget	*dialog;

  dialog = gtk_file_chooser_dialog_new("Import File",
				       GTK_WINDOW(self), 
				       GTK_FILE_CHOOSER_ACTION_OPEN,
				       GTK_STOCK_CANCEL, GTK_RESPONSE_CANCEL,
				       GTK_STOCK_OPEN, GTK_RESPONSE_ACCEPT,
				       NULL);

  if (gtk_dialog_run(GTK_DIALOG(dialog)) == GTK_RESPONSE_ACCEPT)
    {
      self->private->filepath = gtk_file_chooser_get_filename(GTK_FILE_CHOOSER(dialog));
      g_signal_emit(self, pitivi_sourcelistwindow_signal[FILEIMPORT_SIGNAL],
		    0 /* details */, 
		    NULL);
    }

  gtk_widget_destroy(dialog);
}

void	OnImportFolder(gpointer data, gint action, GtkWidget *widget)
{
  PitiviSourceListWindow *self = (PitiviSourceListWindow*)data;

GtkWidget	*dialog;

  dialog = gtk_file_chooser_dialog_new("Import Folder",
				       GTK_WINDOW(self), 
				       GTK_FILE_CHOOSER_ACTION_SELECT_FOLDER,
				       GTK_STOCK_CANCEL, GTK_RESPONSE_CANCEL,
				       GTK_STOCK_OPEN, GTK_RESPONSE_ACCEPT,
				       NULL);

  if (gtk_dialog_run(GTK_DIALOG(dialog)) == GTK_RESPONSE_ACCEPT)
    {
      self->private->folderpath = gtk_file_chooser_get_filename(GTK_FILE_CHOOSER(dialog));
      g_signal_emit(self, pitivi_sourcelistwindow_signal[FOLDERIMPORT_SIGNAL],
		    0 /* details */, 
		    NULL);   
    }

  gtk_widget_destroy(dialog);


}

gint		OnSelectItem(PitiviSourceListWindow *self, GtkTreeIter *iter,
			     GtkListStore **liststore, gchar **sMediaType,
			     gint *item_select, gint *folder_select)
{
  GtkTreeIter	iternext;
  GtkTreePath	*listpath;
  gchar		*tmpMediaType;
  gint		i;
  gint		selected_tree_row;
  guint		selected_list_row;
  gint		depth;

  listpath = gtk_tree_path_new_from_string(self->private->listpath);
  
  selected_list_row = get_selected_row(self->private->listpath, &depth);
  *liststore = get_liststore_for_bin(self, selected_tree_row);
  if (!gtk_tree_model_get_iter(GTK_TREE_MODEL(*liststore), iter, listpath))
    {
      gtk_tree_path_free(listpath);
      return FALSE;
    }
  
  gtk_tree_path_free(listpath);
  
  gtk_tree_model_get(GTK_TREE_MODEL(*liststore), iter, TEXT_LISTCOLUMN3, &(*sMediaType), -1);

  gtk_tree_model_get_iter_first(GTK_TREE_MODEL(*liststore), &iternext);

  *item_select = 0;
  *folder_select = 0;
  
  i = 0;

  while (i++ < selected_list_row)
    {
      gtk_tree_model_get(GTK_TREE_MODEL(*liststore), &iternext, TEXT_LISTCOLUMN3, &tmpMediaType, -1);
      if (!strcmp(tmpMediaType, "Bin"))
	(*folder_select)++;
      else
	(*item_select)++;
      gtk_tree_model_iter_next(GTK_TREE_MODEL(*liststore), &iternext);
    }

  return TRUE;
}

void		OnRemoveItem(gpointer data, gint action, GtkWidget *widget)
{
  PitiviSourceListWindow *self = (PitiviSourceListWindow*)data;
  GtkListStore	*liststore;
  GtkTreeIter	iter;
  gchar		*sMediaType;
  gint		item_select;
  gint		folder_select;

  if (!OnSelectItem(self, &iter, &liststore, &sMediaType, &item_select, 
		   &folder_select))
    return;

  gtk_list_store_remove(GTK_LIST_STORE(liststore), &iter);

  if (strcmp(sMediaType, "Bin"))
    pitivi_projectsourcelist_remove_file_from_bin(((PitiviProjectWindows*)self)->project->sources, 
						  self->private->treepath,
						  item_select);
  else /* need to remove folder */
    ;
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
  gint		selected_tree_row;
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

  if (!OnSelectItem(self, &iter, &liststore, &sMediaType, &item_select,
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
  GtkWidget	*pHBox;
  GtkWidget	*pHpaned;
  GtkWidget	*pVSeparator;
  GtkWidget	*pMenupopup;

  pHpaned = gtk_hpaned_new();

  pScrollbar = create_treeview(self, pScrollbar);
  pScrollbar2 = create_listview(self, pScrollbar2);
 
  g_signal_connect (G_OBJECT (self), "newfile",
                          (GCallback)new_file,
                          self);

  g_signal_connect (G_OBJECT (self), "newfolder",
                          (GCallback)new_folder,
                          self);

  gtk_paned_set_position(GTK_PANED(pHpaned), 200);
  gtk_paned_pack1(GTK_PANED(pHpaned), pScrollbar, TRUE, FALSE);
  gtk_paned_pack2(GTK_PANED(pHpaned), pScrollbar2, FALSE, FALSE);
  
  return pHpaned;
}
void	
pitivi_sourcelistwindow_recurse_into_folder(PitiviSourceListWindow *self, 
					    gchar *parent_name)
{
  GSList	*file_list;
  GSList	*folder_list;
  GtkTreePath	*treepath;
  GtkTreeIter	iter;
  gchar		*name;
  gchar		*save;

  file_list = pitivi_projectsourcelist_get_file_list(((PitiviProjectWindows*)self)->project->sources, parent_name);
      
  while (file_list)
    {
      g_printf("%s\n", file_list->data);
      self->private->filepath = file_list->data;
      if (pitivi_sourcelistwindow_set_file(self))
	pitivi_projectsourcelist_set_file_property_by_name(((PitiviProjectWindows*)self)->project->sources, parent_name, self->private->filepath, self->private->mediatype, self->private->infovideo, self->private->infoaudio, self->private->length, self->private->pipeline);
      file_list = file_list->next;
    }

  folder_list = pitivi_projectsourcelist_get_folder_list(((PitiviProjectWindows*)self)->project->sources, parent_name);
  
  while (folder_list)
    {
      g_printf("folder ==> %s\n", folder_list->data);
      self->private->folderpath = folder_list->data;
      name = pitivi_sourcelistwindow_set_folder(self, &iter);
      /* need to select the good treepath */
      /* retrieve GtkTreepath for current folder */
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
      g_printf("============\n");
      g_printf("%s\n", bin_list->data);
      pitivi_sourcelistwindow_set_bin(self, bin_list->data);

      
      pitivi_sourcelistwindow_recurse_into_folder(self, bin_list->data);

      bin_list = bin_list->next;
      g_printf("============\n");
    }
}

PitiviSourceListWindow *
pitivi_sourcelistwindow_new(PitiviMainApp *mainapp, PitiviProject *project)
{
  PitiviSourceListWindow	*sourcelistwindow;

  //g_printf("mainapp ==> %p\nproject ==> %p\n", mainapp, project);

  sourcelistwindow = (PitiviSourceListWindow *) g_object_new(PITIVI_SOURCELISTWINDOW_TYPE,
							     "mainapp", mainapp,
							     "project", project,
							     NULL);
 
  //g_printf("show class ==> %p\n", ((PitiviWindows*)sourcelistwindow));
  sourcelistwindow->private->mainapp = mainapp;
  g_assert(sourcelistwindow != NULL);
  return sourcelistwindow;
}

static GObject *
pitivi_sourcelistwindow_constructor (GType type,
			     guint n_construct_properties,
			     GObjectConstructParam * construct_properties)
{
  PitiviProject	*project;
  GObject *obj;
  {
    /* Invoke parent constructor. */
    obj = G_OBJECT_CLASS (parent_class)->constructor (type, n_construct_properties,
						      construct_properties);
  }

  /* do stuff. */
  project = ((PitiviProjectWindows *) obj)->project;
  
  if (pitivi_projectsourcelist_test_bin_tree(project->sources))
    {
      g_printf("we have loading a project\n");
      pitivi_sourcelistwindow_load_project((PitiviSourceListWindow*)obj);
    }
  else
    {
      new_bin((PitiviSourceListWindow*)obj, g_strdup("bin 1"));
      ((PitiviSourceListWindow*)obj)->private->nbrchutier++;
    }
  return obj;
}

static void
pitivi_sourcelistwindow_instance_init (GTypeInstance * instance, gpointer g_class)
{
  PitiviSourceListWindow *self = (PitiviSourceListWindow *) instance;
  GtkWidget	*hpaned;

  self->private = g_new0(PitiviSourceListWindowPrivate, 1);
  
  /* initialize all public and private members to reasonable default values. */ 
  
  self->private->dispose_has_run = FALSE;
  
  /* If you need specific consruction properties to complete initialization, 
   * delay initialization completion until the property is set. 
   */

  self->private->hpaned = create_projectview(self);
 
  self->private->liststore = NULL;

  /* add a bin to validate model of  list view */
  /* for the first bin we need to set treepath manually */
  self->private->treepath = g_strdup("0");
  
  gtk_window_set_default_size(GTK_WINDOW(self), 600, 200);

  gtk_container_add(GTK_CONTAINER(self), self->private->hpaned);
  
  self->private->nbrchutier = 1;
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

  /* 
   * In dispose, you are supposed to free all types referenced from this 
   * object which might themselves hold a reference to self. Generally, 
   * the most simple solution is to unref all members on which you own a 
   * reference. 
   */

  G_OBJECT_CLASS (parent_class)->dispose (object);
}

static void
pitivi_sourcelistwindow_finalize (GObject *object)
{
  PitiviSourceListWindow	*self = PITIVI_SOURCELISTWINDOW(object);

  /* 
   * Here, complete object destruction. 
   * You might not need to do much... 
   */

  g_free (self->private);
  G_OBJECT_CLASS (parent_class)->finalize (object);
}

static void
pitivi_sourcelistwindow_set_property (GObject * object,
			      guint property_id,
			      const GValue * value, GParamSpec * pspec)
{
  PitiviSourceListWindow *self = (PitiviSourceListWindow *) object;

  switch (property_id)
    {
      /*   case PITIVI_SOURCELISTWINDOW_PROPERTY: { */
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
pitivi_sourcelistwindow_get_property (GObject * object,
			      guint property_id,
			      GValue * value, GParamSpec * pspec)
{
  PitiviSourceListWindow *self = (PitiviSourceListWindow *) object;

  switch (property_id)
    {
      /*  case PITIVI_SOURCELISTWINDOW_PROPERTY: { */
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
pitivi_sourcelistwindow_class_init (gpointer g_class, gpointer g_class_data)
{
  GObjectClass *gobject_class = G_OBJECT_CLASS (g_class);
  PitiviSourceListWindowClass *klass = PITIVI_SOURCELISTWINDOW_CLASS (g_class);

  parent_class = g_type_class_peek_parent (g_class);

  gobject_class->constructor = pitivi_sourcelistwindow_constructor;
  gobject_class->dispose = pitivi_sourcelistwindow_dispose;
  gobject_class->finalize = pitivi_sourcelistwindow_finalize;

  gobject_class->set_property = pitivi_sourcelistwindow_set_property;
  gobject_class->get_property = pitivi_sourcelistwindow_get_property;

  /* Install the properties in the class here ! */
  /*   pspec = g_param_spec_string ("maman-name", */
  /*                                "Maman construct prop", */
  /*                                "Set maman's name", */
  /*                                "no-name-set" /\* default value *\/, */
  /*                                G_PARAM_CONSTRUCT_ONLY | G_PARAM_READWRITE); */
  /*   g_object_class_install_property (gobject_class, */
  /*                                    MAMAN_BAR_CONSTRUCT_NAME, */
  /*                                    pspec); */
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
