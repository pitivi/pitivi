/* 
 * PiTiVi
 * Copyright (C) <2004> Guillaume Casanova <casano_g@epita.fr>
 *                      
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
#include "pitivi-effectswindow.h"
#include "pitivi-dragdrop.h"
#include "pitivi-effects_cat.h"

static GtkWindowClass *parent_class = NULL;

gchar* labels[PITIVI_EFFECT_NBCAT_TYPE+1]={
  
  PITIVI_TRANSITION_EFFECT_LABEL,
  PITIVI_VIDEO_EFFECT_LABEL,
  PITIVI_AUDIO_EFFECT_LABEL,
  0
};

struct _PitiviEffectsWindowPrivate
{
  /* instance private members */
  gboolean		dispose_has_run;
  guint			notebook_id;
  GtkWidget		*notebook;
  PitiviEffectsTree	*trees[PITIVI_EFFECT_NBCAT_TYPE];
  PitiviSourceFile	*dndse;
  GtkWidget		*timelinewin;
  
  /* selected media */
  
  GtkWidget	        *selected_media;
};

/*
 * forward definitions
 */

enum {
    PITIVI_ICON_COLUMN,
    PITIVI_TEXT_COLUMN,
    PITIVI_BG_COLOR_COLUMN,
    PITIVI_FG_COLOR_COLUMN,
    PITIVI_POINTER_COLUMN,
    PITIVI_NB_COLUMN
};

static GtkTargetEntry TargetEntries[] =
{
  { "pitivi/sourceeffect", GTK_TARGET_SAME_APP, DND_TARGET_EFFECTSWIN }
};

static gint iNbTargetEntries = G_N_ELEMENTS (TargetEntries);

/*
 **********************************************************
 * Signals  					          *
 *							  *
 **********************************************************
*/

enum
  {
    SELECT_MEDIA_SOURCE_SIGNAL,
    LAST_SIGNAL
  };

static guint	      effects_signals[LAST_SIGNAL] = {0};

/*
 * Insert "added-value" functions here
 */

PitiviEffectsWindow *
pitivi_effectswindow_new (PitiviMainApp *mainapp)
{
  PitiviEffectsWindow	*effectswindow;

  effectswindow = (PitiviEffectsWindow *) g_object_new(PITIVI_EFFECTSWINDOW_TYPE, 
						       "mainapp", mainapp, NULL);
  g_assert(effectswindow != NULL);  
  return effectswindow;
}

static void
pitivi_effectswindow_insert_newtab (GtkNotebook *notebook, PitiviEffectsTree *tree)
{
  GtkWidget *widget;
  
  gtk_container_add (GTK_CONTAINER (notebook), tree->scroll);
  gtk_container_add (GTK_CONTAINER (tree->scroll), tree->treeview);
  widget = gtk_notebook_get_nth_page (GTK_NOTEBOOK (notebook), tree->order);
  gtk_notebook_set_tab_label (GTK_NOTEBOOK ( notebook ), widget, GTK_WIDGET (tree->label));
  gtk_label_set_justify (GTK_LABEL ( tree->label ), GTK_JUSTIFY_LEFT);
  gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW (tree->scroll),
				 GTK_POLICY_AUTOMATIC, GTK_POLICY_AUTOMATIC);
}

static GObject *
pitivi_effectswindow_constructor (GType type,
			     guint n_construct_properties,
			     GObjectConstructParam * construct_properties)
{
  GObject *obj;
  int  count;
  GtkWidget *main_vbox;

    /* Invoke parent constructor. */
  PitiviEffectsWindowClass *klass;
  PitiviEffectsWindow	   *self;

  GObjectClass *parent_class;
  klass = PITIVI_EFFECTSWINDOW_CLASS (g_type_class_peek (PITIVI_EFFECTSWINDOW_TYPE));
  parent_class = G_OBJECT_CLASS (g_type_class_peek_parent (klass));
  obj = parent_class->constructor (type, n_construct_properties,
				   construct_properties);
  self = (PitiviEffectsWindow *) obj;

  /* do stuff. */
  
  main_vbox = gtk_vbox_new (FALSE, 0);
  self->private->notebook = gtk_notebook_new ();
  gtk_widget_set_usize (main_vbox, PITIVI_EFFECTS_WIN_SIZEX, PITIVI_EFFECTS_WIN_SIZEY);
  gtk_box_pack_start (GTK_BOX (main_vbox), self->private->notebook, TRUE, TRUE, 0);
  gtk_container_add (GTK_CONTAINER (self), main_vbox);
  
  for (count = 0; count < PITIVI_EFFECT_NBCAT_TYPE - 1; count++)
    {
      self->private->trees[count] = g_new0 (PitiviEffectsTree, 1);
      self->private->trees[count]->window = GTK_WIDGET (self);
      self->private->trees[count]->label = gtk_label_new (labels[count]);
      self->private->trees[count]->treeview = gtk_tree_view_new ();
      self->private->trees[count]->scroll = gtk_scrolled_window_new (NULL, NULL);
      self->private->trees[count]->order = count;
      pitivi_effectstree_set_gst (self->private->trees[count], 
				  count+1, 
				  ((PitiviWindows *)self)->mainapp->global_settings);
      pitivi_effectswindow_insert_newtab (GTK_NOTEBOOK (self->private->notebook), self->private->trees[count]);
      gtk_tree_view_expand_all (GTK_TREE_VIEW (self->private->trees[count]->treeview));
    }
  self->private->timelinewin = (GtkWidget *) pitivi_mainapp_get_timelinewin (((PitiviWindows *)self)->mainapp);
  return obj;
}


static void
pitivi_effectswindow_instance_init (GTypeInstance * instance, gpointer g_class)
{
  PitiviEffectsWindow *self = (PitiviEffectsWindow *) instance;
  self->private = g_new0(PitiviEffectsWindowPrivate, 1);
  self->private->dispose_has_run = FALSE;
  gtk_window_set_title (GTK_WINDOW (self), PITIVI_EFFECTS_DF_TITLE);
}

pitivi_effects_action_on_colexp (GtkTreeView *treeview, 
				 GtkTreeIter *TreeIter, 
				 gchar *icon, 
				 gpointer data)
{
  GdkPixbuf           *pixbuf;
  GtkTreeModel	      *model;
  PitiviEffectsTree   *effectstree;
  gchar		      *name;
   
  effectstree = (PitiviEffectsTree *) data;
  model = gtk_tree_view_get_model (GTK_TREE_VIEW (treeview));
  pixbuf = gtk_widget_render_icon(effectstree->window, icon, GTK_ICON_SIZE_MENU, NULL);  
  gtk_tree_model_get (GTK_TREE_MODEL (model), TreeIter, PITIVI_TEXT_COLUMN, &name, -1);
  gtk_tree_store_set(GTK_TREE_STORE (model), TreeIter,
		     PITIVI_ICON_COLUMN, pixbuf,
		     -1);
}

void
effectstree_on_row_activated (GtkTreeView        *treeview,
			      GtkTreePath        *path,
			      GtkTreeViewColumn  *col,
			      gpointer            data)
{
  PitiviEffectsWindow *self;
  GtkTreeModel	      *model;
  PitiviSourceFile    *info;
  GtkTreeIter	      child;

  self = (PitiviEffectsWindow *) gtk_widget_get_toplevel (GTK_WIDGET (treeview));
  model = gtk_tree_view_get_model (GTK_TREE_VIEW (treeview));
  gtk_tree_model_get (GTK_TREE_MODEL (model), &child, PITIVI_POINTER_COLUMN, &info, -1);
  if ( data && info )
    {
      g_signal_emit_by_name (GTK_OBJECT (pitivi_mainapp_get_timelinewin(((PitiviWindows *)self)->mainapp)), 
			     "associate-effect-to-media", info);
      self->private->selected_media = NULL;
   }
}

void
effectstree_on_row_collapsed (GtkTreeView *treeview, 
			      GtkTreeIter *TreeIter, 
			      GtkTreePath *arg2, 
			      gpointer data)
{
  pitivi_effects_action_on_colexp (treeview, TreeIter, PITIVI_STOCK_EFFECT_CAT, data);
}


void
effectstree_on_row_expanded (GtkTreeView *treeview,
			     GtkTreeIter *TreeIter,
			     GtkTreePath *arg2, 
			     gpointer data)
{
  pitivi_effects_action_on_colexp (treeview, TreeIter, PITIVI_STOCK_EFFECT_CAT_OPEN, data);
}

/* Insertion on Node */

void
pitivi_effectstree_insert_node (PitiviEffectsTree *tree_effect,
				 GtkTreeIter *child,
				 GtkTreeIter *parent,
				 const gchar *name,
				 gchar *icon,
				 gpointer data)
{
  GdkPixbuf *pixbuf;

  pixbuf = gtk_widget_render_icon(tree_effect->window, icon, GTK_ICON_SIZE_MENU, NULL);
  gtk_tree_store_append (tree_effect->model, child, parent);
  gtk_tree_store_set(tree_effect->model, child,
		     PITIVI_ICON_COLUMN, pixbuf,
		     PITIVI_TEXT_COLUMN, name,
		     PITIVI_BG_COLOR_COLUMN, NULL,
		     PITIVI_FG_COLOR_COLUMN, NULL,
		     PITIVI_POINTER_COLUMN, data,
		     -1);
  tree_effect->pixbuf = pixbuf;
}

PitiviSourceFile *
pitivi_create_effect_sourcefile (const gchar *name,
				 const gchar *mediatype,
				 GstElement *elm,
				 GdkPixbuf *pixbuf)
{
  PitiviSourceFile *se;
  
  se = g_new0 (PitiviSourceFile, 1);
  se->filename = g_strdup (name);
  se->thumbs_effect = pixbuf;
  se->mediatype = g_strdup (mediatype);
  se->pipeline = elm;
  se->length = 0LL;
  return se;
}

void
pitivi_effectstree_insert_effect (PitiviEffectsTree *tree_effect,
				  GtkTreeIter *child,
				  GtkTreeIter *parent,
				  const gchar *name,
				  const gchar *desc,
				  gchar *icon,
				  gpointer data)
{
  GdkPixbuf *pixbuf;
  GdkPixbuf *thumb;
  PitiviSourceFile *se;

  pixbuf = gtk_widget_render_icon(tree_effect->window, icon, GTK_ICON_SIZE_MENU, NULL);
  thumb = gtk_widget_render_icon(tree_effect->window, icon, GTK_ICON_SIZE_LARGE_TOOLBAR, NULL);
  se = pitivi_create_effect_sourcefile (name, desc, (GstElement *)data, thumb);
  gtk_tree_store_append (tree_effect->model, child, parent);
  gtk_tree_store_set(tree_effect->model, child,
		     PITIVI_ICON_COLUMN, pixbuf,
		     PITIVI_TEXT_COLUMN, name,
		     PITIVI_BG_COLOR_COLUMN, NULL,
		     PITIVI_FG_COLOR_COLUMN, NULL,
		     PITIVI_POINTER_COLUMN, se,
		     -1);
}

void
pitivi_effectstree_clear_old_selection (GtkTreeModel *model, GtkTreeIter *parent)
{
  int  count, nb = 0;
  gboolean    valid = TRUE;
  gchar	      *name;
  GdkColor    fg[1];
  GtkTreeIter child;
    
  fg[0].red = 0;
  fg[0].green = 0;
  fg[0].blue = 0;
  
  if (gtk_tree_model_iter_children (model, &child, parent))
    {
      while (valid)
	{
	  gtk_tree_model_get (model, &child, PITIVI_TEXT_COLUMN, &name, -1);
	  gtk_tree_store_set(GTK_TREE_STORE (model), &child,
			     PITIVI_FG_COLOR_COLUMN, fg,
			     -1);
	  pitivi_effectstree_clear_old_selection (model, &child);
	  valid = gtk_tree_model_iter_next (model, &child);
	}
    }
}

void
pitivi_effectstree_selected_color (GtkTreeView *treeview, gpointer user_data)
{
  PitiviEffectsTree	*effectstree;
  GtkTreeSelection	*selection;
  GtkTreeModel		*model;
  GtkTreeIter		TreeIter;
  GdkColor		fg[1];
  gchar			*name;
  
  fg[0].red = 65535;
  fg[0].green = 0;
  fg[0].blue = 0;
  
  effectstree = (PitiviEffectsTree *) user_data;  
  selection = gtk_tree_view_get_selection (GTK_TREE_VIEW (treeview));
  if (gtk_tree_selection_get_selected(selection, &model, &TreeIter))
    {      
      pitivi_effectstree_clear_old_selection (model, NULL);
      gtk_tree_model_get (model, &TreeIter, PITIVI_TEXT_COLUMN, &name, -1);
      gtk_tree_store_set(GTK_TREE_STORE (model), &TreeIter,
			 PITIVI_FG_COLOR_COLUMN, fg,
			 -1);
    }
}


/**************************************************************
 * Callbacks Signal Drag and Drop          		      *
 * This callbacks are used to motion get or delete  data from *
 * drag							      *
 **************************************************************/

void
slide_effects_info (PitiviEffectsWindow *self, gint64 length, gchar *path)
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
pitivi_effectswindow_drag_data_get (GtkWidget          *widget,
				    GdkDragContext     *context,
				    GtkSelectionData   *selection_data,
				    guint               info,
				    guint32             time,
				    gpointer user_data)
{
  PitiviEffectsWindow *self = (PitiviEffectsWindow *) gtk_widget_get_toplevel (widget);
  if (self && self->private->dndse)
    gtk_selection_data_set (selection_data, 
			    selection_data->target, 
			    8, 
			    (void *) self->private->dndse,
			    sizeof (PitiviSourceFile));
}

static void
pitivi_effectswindow_drag_begin (GtkWidget		*widget,
				 GdkDragContext		*context,
				 gpointer		user_data)
{
  PitiviEffectsWindow *self = (PitiviEffectsWindow *) gtk_widget_get_toplevel (widget);
  PitiviSourceFile    *se;
  GtkTreeSelection    *selection;
  GtkTreeModel	      *model;
  GtkTreeIter	      iter;
  gchar		      *name;
  gint64	      size;

  selection = gtk_tree_view_get_selection(GTK_TREE_VIEW(widget));
  if (!gtk_tree_selection_get_selected (selection, &model, &iter)) {
    g_warning("No elements selected!");
    return;
  }
  gtk_tree_model_get (model, &iter, PITIVI_POINTER_COLUMN, &se, -1);
  self->private->dndse = se;
  size = ((gint64)50000000000LL);
  slide_effects_info ( self, size, "transition" );
}

/**************************************************************
 * Effects Insertion					      *
 *							      *
 *							      *
 **************************************************************/

gchar	*get_icon_fx(G_CONST_RETURN gchar *name, gint type)
{
  gchar	*icon_fx;
  gint	id_tab;

  switch(type)
    {
    case 1:
      {
	id_tab = 0;
	while (video_effect_tab[id_tab].name)
	  {
	    if (!strcmp(video_effect_tab[id_tab].name, name))
	      {
		icon_fx = video_effect_tab[id_tab].image;
		return (icon_fx);
	      }
	    else
	      {
		icon_fx = PITIVI_STOCK_EFFECT_TV;
	      }
	    id_tab++;
	  }
      }
      break;
    case 2:
      {
/* 	id_tab = 0; */
/* 	while (audio_effect_tab[id_tab].name) */
/* 	  { */
/* 	    if (!strcmp(audio_effect_tab[id_tab].name, name)) */
/* 	      { */
/* 		icon_fx = audio_effect_tab[id_tab].image; */
/* 		return (icon_fx); */
/* 	      } */
/* 	    else */
/* 	      { */
/* 		icon_fx = PITIVI_STOCK_EFFECT_SOUND; */
/* 	      } */
/* 	    id_tab++; */
/* 	  } */
	icon_fx = PITIVI_STOCK_EFFECT_SOUND;
      }
      break;
    }
  return (icon_fx);
}

void
insert_video_effects_on_tree (PitiviEffectsTree *tree_effect, 
			      GtkTreeIter *child, 
			      GList *settingslist)
{
  const gchar		*klass;
  const gchar		*effectname;
  const gchar		*desc;
  GtkTreeIter		video_iter[2];
  GList			*fx_video = NULL;
  G_CONST_RETURN gchar	*name;
  gchar			*icon_fx;

  pitivi_effectstree_insert_node (tree_effect, 
				  &tree_effect->treeiter,  
				  NULL,  
				  "Simple Effects",  
				  PITIVI_STOCK_EFFECT_CAT, 
				  NULL);
  
  /* On recupere la liste des effets video via la structure self */
  while (settingslist)
    {
      fx_video = g_list_append (fx_video, settingslist->data);
      settingslist = settingslist->next;
    }
  
  /* On creer deux sous categories */
  pitivi_effectstree_insert_node (tree_effect, &video_iter[0], NULL,
				   "Tv Effects", PITIVI_STOCK_EFFECT_CAT, NULL);
  pitivi_effectstree_insert_node (tree_effect, &video_iter[1], NULL,
				   "Video Effects", PITIVI_STOCK_EFFECT_CAT, NULL);
  /* On insere les elements video dans le tree pour le menu des effets */
  while (fx_video)
    {
      name = gst_plugin_feature_get_name(GST_PLUGIN_FEATURE(fx_video->data));
      klass = gst_element_factory_get_klass (fx_video->data);
      effectname = gst_element_factory_get_longname (fx_video->data);
      desc = gst_element_factory_get_description (fx_video->data);
      if (!strncmp (klass, "Filter/Effect/Video", 19))
	{
	  gchar *idx;
	      
	  if ((idx = strstr (effectname, "TV")))
	    {
	      *idx = '\0';
	      icon_fx = get_icon_fx(name, 1);
	      pitivi_effectstree_insert_node (tree_effect,
					      child,
					      &video_iter[0],
					       effectname,
					      icon_fx,
					      NULL);
	    }
	  else if ((idx = strstr (effectname, "ideo")))
	    {
	      icon_fx = get_icon_fx(name, 1);
	      pitivi_effectstree_insert_effect (tree_effect, 
					       &video_iter[1],
					       &tree_effect->treeiter,
					       effectname + 6,
					       "video/effect", 
					       icon_fx, 
					       fx_video->data);
	    }
	  else
	    {
	      icon_fx = get_icon_fx(name, 1);
	      pitivi_effectstree_insert_effect (tree_effect, 
					       child,
					       &tree_effect->treeiter,
					       effectname,
					       "video/effect", 
					       icon_fx, 
					       fx_video->data);
	    } 
	}
      fx_video = fx_video->next;
    }
}

void
insert_audio_effects_on_tree (PitiviEffectsTree *tree_effect, 
			      GtkTreeIter *child, 
			      GList *settingslist)
{
  const gchar		*klass;
  const gchar		*effectname;
  const gchar		*desc;
  GList			*fx_audio = NULL;
  G_CONST_RETURN gchar	*name;
  gchar			*icon_fx;

  pitivi_effectstree_insert_node (tree_effect, 
				  &tree_effect->treeiter,  
				  NULL,  
				  "Simple Effects",  
				  PITIVI_STOCK_EFFECT_CAT, NULL);
  while ( settingslist )
    {
      fx_audio = g_list_append (fx_audio,  settingslist->data);
      settingslist = settingslist->next;
    }
  while ( fx_audio )
    {
      name = gst_plugin_feature_get_name(GST_PLUGIN_FEATURE(fx_audio->data));
      klass = gst_element_factory_get_klass (fx_audio->data);
      effectname = gst_element_factory_get_longname (fx_audio->data);
      desc = gst_element_factory_get_description (fx_audio->data);
      //g_printf ("description audio :%s ---> %s\n\n", effectname, desc);
      if (!strncmp (klass, "Filter/Effect/Audio", 19))
	{
	  icon_fx = get_icon_fx(name, 2);
	  pitivi_effectstree_insert_effect (tree_effect, 
					   child, 
					   &tree_effect->treeiter,
					   effectname,
					   "audio/effect", 
					   icon_fx, 
					   fx_audio->data);
	}
      fx_audio = fx_audio->next;
    }
}

void
insert_transition_effects_on_tree (PitiviEffectsTree *tree_effect, 
				   GtkTreeIter *child, 
				   GList *settingslist)
{
  const gchar			*klass;
  const gchar			*effectname;
  const gchar			*desc;
  gint				nb, nb_tcat;
  GList				*fx_transition = NULL;
  GtkTreeIter			Trans_iter[18];

  /* On recupere la liste des effets de transition via la structure self */

  while (settingslist)
    {
      fx_transition = g_list_append(fx_transition, settingslist->data);
      settingslist = settingslist->next;
    }

  while ( fx_transition )
    {
      klass = gst_element_factory_get_klass ( fx_transition->data );
      effectname = gst_element_factory_get_longname (  fx_transition->data );
      desc = gst_element_factory_get_description (  fx_transition->data );
      if (strstr (effectname, "SMPTE"))
	break;
      fx_transition = fx_transition->next;
    }

  /* On creer 18 sous categories */
  
  for (nb_tcat = 0; nb_tcat < PITIVI_LAST_WIPE; nb_tcat++)
    {
      pitivi_effectstree_insert_node (tree_effect, &Trans_iter[nb_tcat], NULL,
				       transition_cat[nb_tcat], PITIVI_STOCK_EFFECT_CAT, NULL);
      for (nb = 0; nb < (sizeof (tab_category) / sizeof (PitiviTransProp)); nb++)
	{
	  /* On test les elements du tableau et on les insere dans les differentes categories */
	  
	  if (nb_tcat == tab_category[nb].id_categorie && tab_category[nb].name)
	    {
	      pitivi_effectstree_insert_effect (tree_effect, 
					       child, 
					       &Trans_iter[nb_tcat],
					       tab_category[nb].name,
					       "transition",
					       tab_category[nb].image,
					       fx_transition->data);
	    }
	}
    }
  
  pitivi_effectstree_insert_node (tree_effect, 
				  &tree_effect->treeiter,  
				  NULL,  
				  "Simple Effects",  
				  PITIVI_STOCK_EFFECT_CAT, 
				  "");
}

void
pitivi_effectstree_set_gst (PitiviEffectsTree *tree_effect,
			    PitiviEffectsTypeEnum eneffects,  
			    PitiviSettings *setting)
{
  GtkWidget			*self;
  GtkCellRenderer		*pCellRenderer;
  GtkTreeViewColumn		*pColumn;
  GdkPixbuf			*pixbuf;
  const GList			*elements;
  int				count, i =  0;
  
  gtk_tree_view_set_headers_visible (GTK_TREE_VIEW (tree_effect->treeview), FALSE);
  tree_effect->model = gtk_tree_store_new ( PITIVI_NB_COLUMN,
					    GDK_TYPE_PIXBUF,
					    G_TYPE_STRING,
					    GDK_TYPE_COLOR,
					    GDK_TYPE_COLOR,
					    G_TYPE_POINTER,
					    -1);
  
  /* On check le type d'effet a inserer (video/audio/transition) */

  switch (eneffects)
    {
      GtkTreeIter child;

    case PITIVI_EFFECT_VIDEO_TYPE:
      insert_video_effects_on_tree (tree_effect, &child, setting->video_effects);
      break;
    case PITIVI_EFFECT_AUDIO_TYPE:
      insert_audio_effects_on_tree (tree_effect, &child, setting->audio_effects);
      break;
    case PITIVI_EFFECT_TRANSITION_TYPE:
      insert_transition_effects_on_tree (tree_effect, &child, setting->transition_effects);
      break;
    }

  gtk_tree_view_set_model(GTK_TREE_VIEW(tree_effect->treeview), GTK_TREE_MODEL(tree_effect->model));
  pCellRenderer = gtk_cell_renderer_pixbuf_new();
  pColumn = gtk_tree_view_column_new_with_attributes("",
						     pCellRenderer,
						     "pixbuf",
						     PITIVI_ICON_COLUMN,
						     NULL);
  
  gtk_tree_view_append_column(GTK_TREE_VIEW(tree_effect->treeview), pColumn);
  
  pCellRenderer = gtk_cell_renderer_text_new();
  pColumn = gtk_tree_view_column_new_with_attributes("",
						     pCellRenderer,
						     "text",
						     PITIVI_TEXT_COLUMN,
						     "background-gdk",
						     PITIVI_BG_COLOR_COLUMN,
						     "foreground-gdk",
						     PITIVI_FG_COLOR_COLUMN,
						     NULL);
  
  g_signal_connect (tree_effect->treeview, "cursor-changed", G_CALLBACK ( pitivi_effectstree_selected_color ), \
		    (gpointer) tree_effect);
  g_signal_connect (tree_effect->treeview, "row-expanded", G_CALLBACK ( effectstree_on_row_expanded ),\
		    (gpointer) tree_effect);
  g_signal_connect (tree_effect->treeview, "row-collapsed", G_CALLBACK ( effectstree_on_row_collapsed ),\
		    (gpointer) tree_effect);
    
  gtk_tree_view_append_column(GTK_TREE_VIEW (tree_effect->treeview), pColumn);
  
  // Drag 'n Drop Activation
  
  gtk_drag_source_set (GTK_WIDGET (tree_effect->treeview), 
		      GDK_BUTTON1_MASK,
		      TargetEntries, iNbTargetEntries, 
		      GDK_ACTION_COPY);

  self = gtk_widget_get_toplevel (tree_effect->treeview);
  
  g_signal_connect (tree_effect->treeview, "drag_data_get",	      
		    G_CALLBACK (pitivi_effectswindow_drag_data_get), self);
  g_signal_connect (tree_effect->treeview, "drag_begin",	      
		    G_CALLBACK (pitivi_effectswindow_drag_begin), self);
  g_signal_connect (tree_effect->treeview, "row-activated", 
		    G_CALLBACK  ( effectstree_on_row_activated ), 
		    self);
}


static void
pitivi_effectswindow_selected_media (PitiviEffectsWindow *self, gpointer data)
{
  self->private->selected_media = &(*GTK_WIDGET (data));
}


/**************************************************************
 * Window Effects Initialization			      *
 * and Construction					      *
 *							      *
 **************************************************************/


static void
pitivi_effectswindow_dispose (GObject *object)
{
  PitiviEffectsWindow	*self = PITIVI_EFFECTSWINDOW(object);

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
pitivi_effectswindow_finalize (GObject *object)
{
  PitiviEffectsWindow	*self = PITIVI_EFFECTSWINDOW(object);

  /* 
   * Here, complete object destruction. 
   * You might not need to do much... 
   */

  g_free (self->private);
  G_OBJECT_CLASS (parent_class)->finalize (object);
}

static void
pitivi_effectswindow_set_property (GObject * object,
			      guint property_id,
			      const GValue * value, GParamSpec * pspec)
{
  PitiviEffectsWindow *self = (PitiviEffectsWindow *) object;

  switch (property_id)
    {
    default:
      g_assert (FALSE);
      break;
    }
}

static void
pitivi_effectswindow_get_property (GObject * object,
			      guint property_id,
			      GValue * value, GParamSpec * pspec)
{
  PitiviEffectsWindow *self = (PitiviEffectsWindow *) object;

  switch (property_id)
    {
    default:
      g_assert (FALSE);
      break;
    }
}

static void
pitivi_effectswindow_class_init (gpointer g_class, gpointer g_class_data)
{
  GObjectClass *gobject_class = G_OBJECT_CLASS (g_class);
  PitiviEffectsWindowClass *klass = PITIVI_EFFECTSWINDOW_CLASS (g_class);
  
  parent_class = g_type_class_peek_parent (g_class);
  
  gobject_class->constructor = pitivi_effectswindow_constructor;
  gobject_class->dispose = pitivi_effectswindow_dispose;
  gobject_class->finalize = pitivi_effectswindow_finalize;

  gobject_class->set_property = pitivi_effectswindow_set_property;
  gobject_class->get_property = pitivi_effectswindow_get_property;
  
  effects_signals[SELECT_MEDIA_SOURCE_SIGNAL] = g_signal_new ("selected-source",
							      G_TYPE_FROM_CLASS (g_class),
							      G_SIGNAL_RUN_FIRST | G_SIGNAL_ACTION,
							      G_STRUCT_OFFSET (PitiviEffectsWindowClass, selected_media),
							      NULL, 
							      NULL,                
							      g_cclosure_marshal_VOID__POINTER,
							      G_TYPE_NONE, 1, G_TYPE_POINTER);
  
  klass->selected_media = pitivi_effectswindow_selected_media;
}

GType
pitivi_effectswindow_get_type (void)
{
  static GType type = 0;
 
  if (type == 0)
    {
      static const GTypeInfo info = {
	sizeof (PitiviEffectsWindowClass),
	NULL,			/* base_init */
	NULL,			/* base_finalize */
	pitivi_effectswindow_class_init,	/* class_init */
	NULL,			/* class_finalize */
	NULL,			/* class_data */
	sizeof (PitiviEffectsWindow),
	0,			/* n_preallocs */
	pitivi_effectswindow_instance_init	/* instance_init */
      };
      type = g_type_register_static (PITIVI_WINDOWS_TYPE,
				     "PitiviEffectsWindowType", &info, 0);
    }
  return type;
}
