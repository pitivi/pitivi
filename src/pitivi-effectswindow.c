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
#include "pitivi-effectswindow.h"

static GtkWindowClass *parent_class = NULL;

gchar* labels[PITIVI_EFFECT_NBCAT_TYPE+1]={
  
  PITIVI_VIDEO_EFFECT_LABEL,
  PITIVI_AUDIO_EFFECT_LABEL,
  PITIVI_TRANSITION_EFFECT_LABEL,
  0
};

struct _PitiviEffectsWindowPrivate
{
  /* instance private members */
  gboolean		dispose_has_run;
  guint			notebook_id;
  GtkWidget		*notebook;
  PitiviEffectsTree	trees[PITIVI_EFFECT_NBCAT_TYPE];
  GtkWidget		*statusbar;
};

/*
 * forward definitions
 */

enum {
    PITIVI_ICON_COLUMN,
    PITIVI_TEXT_COLUMN,
    PITIVI_BG_COLOR_COLUMN,
    PITIVI_FG_COLOR_COLUMN,
    PITIVI_NB_COLUMN
};

/*
 * Insert "added-value" functions here
 */

PitiviEffectsWindow *
pitivi_effectswindow_new(void)
{
  PitiviEffectsWindow	*effectswindow;

  effectswindow = (PitiviEffectsWindow *) g_object_new(PITIVI_EFFECTSWINDOW_TYPE, NULL);
  g_assert(effectswindow != NULL);  
  return effectswindow;
}

static GObject *
pitivi_effectswindow_constructor (GType type,
			     guint n_construct_properties,
			     GObjectConstructParam * construct_properties)
{
  GObject *obj;
  {
    /* Invoke parent constructor. */
    PitiviEffectsWindowClass *klass;
    GObjectClass *parent_class;
    klass = PITIVI_EFFECTSWINDOW_CLASS (g_type_class_peek (PITIVI_EFFECTSWINDOW_TYPE));
    parent_class = G_OBJECT_CLASS (g_type_class_peek_parent (klass));
    obj = parent_class->constructor (type, n_construct_properties,
				     construct_properties);
  }

  /* do stuff. */
  
  return obj;
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

static void
pitivi_effectswindow_instance_init (GTypeInstance * instance, gpointer g_class)
{
  int  count;
  GtkWidget *main_vbox;

  PitiviEffectsWindow *self = (PitiviEffectsWindow *) instance;
  self->private = g_new0(PitiviEffectsWindowPrivate, 1);
  
  /* initialize all public and private members to reasonable default values. */ 
  
  self->private->dispose_has_run = FALSE;
  
  /* If you need specific consruction properties to complete initialization, 
   * delay initialization completion until the property is set. 
   */
  
  main_vbox = gtk_vbox_new (FALSE, 0);
  self->private->notebook = gtk_notebook_new ();
  self->private->statusbar = gtk_statusbar_new ();
  gtk_widget_set_usize (main_vbox, PITIVI_EFFECTS_WIN_SIZEX, PITIVI_EFFECTS_WIN_SIZEY);
  gtk_box_pack_start (GTK_BOX (main_vbox), self->private->notebook, TRUE, TRUE, 0);
  gtk_container_add (GTK_CONTAINER (self), main_vbox);
  gtk_box_pack_start (GTK_BOX (main_vbox), self->private->statusbar, FALSE, FALSE, 0);

  for (count = 0; count < PITIVI_EFFECT_NBCAT_TYPE - 1; count++)
    {
      self->private->trees[count].window = GTK_WIDGET (self);
      self->private->trees[count].label = gtk_label_new (labels[count]);
      self->private->trees[count].treeview = gtk_tree_view_new ();
      self->private->trees[count].scroll = gtk_scrolled_window_new (NULL, NULL);
      self->private->trees[count].order = count;
      pitivi_effectstree_set_gst (&self->private->trees[count], count+1);
      pitivi_effectswindow_insert_newtab (GTK_NOTEBOOK (self->private->notebook), &self->private->trees[count]);
    }
}

void
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
pitivi_effectstree_col (GtkTreeView *treeview, 
			GtkTreeIter *TreeIter, 
			GtkTreePath *arg2, 
			gpointer data)
{
  pitivi_effects_action_on_colexp (treeview, TreeIter, PITIVI_STOCK_EFFECT_CAT, data);
}


void
pitivi_effectstree_exp (GtkTreeView *treeview,
			GtkTreeIter *TreeIter,
			GtkTreePath *arg2, 
			gpointer data)
{
  pitivi_effects_action_on_colexp (treeview, TreeIter, PITIVI_STOCK_EFFECT_CAT_OPEN, data);
}

void
pitivi_effectstree_insert_child (PitiviEffectsTree *tree_effect,
				 GtkTreeIter *child,
				 GtkTreeIter *parent,
				 const gchar *name,
				 gchar *icon)
{
  GdkPixbuf *pixbuf;

  pixbuf = gtk_widget_render_icon(tree_effect->window, icon, GTK_ICON_SIZE_MENU, NULL);
  gtk_tree_store_append (tree_effect->model, child, parent);
  gtk_tree_store_set(tree_effect->model, child,
		     PITIVI_ICON_COLUMN, pixbuf,
		     PITIVI_TEXT_COLUMN, name,
		     PITIVI_BG_COLOR_COLUMN, NULL,
		     PITIVI_FG_COLOR_COLUMN, NULL,
		     -1);
  tree_effect->pixbuf = pixbuf;
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

void
pitivi_effectstree_cursor_move (GtkTreeView *treeview,
				GtkMovementStep arg1, 
				gint arg2, 
				gpointer user_data)
{
  
}

void
pitivi_effectstree_set_gst (PitiviEffectsTree *tree_effect, PitiviEffectsTypeEnum eneffects)
{
  int			count;  
  GtkCellRenderer	*pCellRenderer;
  GtkTreeViewColumn     *pColumn;
  GdkPixbuf		*pixbuf;
  const GList		*elements;
  const gchar		*effectname;
  const gchar		*desc;
  const gchar		*klass;
  GstElementFactory	*factory;
  GtkTreeIter		Tv_iter;
  GtkTreeIter		Video_iter;

  gtk_tree_view_set_headers_visible (GTK_TREE_VIEW (tree_effect->treeview), FALSE);
  tree_effect->model = gtk_tree_store_new ( PITIVI_NB_COLUMN,
					    GDK_TYPE_PIXBUF,
					    G_TYPE_STRING,
					    GDK_TYPE_COLOR,
					    GDK_TYPE_COLOR,
					    -1);
  pitivi_effectstree_insert_child (tree_effect, 
				&tree_effect->treeiter,
				NULL,
				"Simple Effects",
				PITIVI_STOCK_EFFECT_CAT);
  switch (eneffects)
    {
    case PITIVI_EFFECT_VIDEO_TYPE:
      pitivi_effectstree_insert_child (tree_effect, 
				    &Tv_iter,
				    NULL,
				    "Tv Effects",
				    PITIVI_STOCK_EFFECT_CAT);
      pitivi_effectstree_insert_child (tree_effect, 
				     &Video_iter,
				     NULL,
				     "Video Effects",
				     PITIVI_STOCK_EFFECT_CAT);
      break;
    }
  elements = gst_registry_pool_feature_list (GST_TYPE_ELEMENT_FACTORY);    
  for (count = 0; elements != 0; count++)
    {
      GtkTreeIter child;
      
      factory = (GstElementFactory *) elements->data;
      klass = gst_element_factory_get_klass (factory);
      effectname = gst_element_factory_get_longname (factory);
      desc = gst_element_factory_get_description (factory);
      switch (eneffects)
	{
	case PITIVI_EFFECT_VIDEO_TYPE:
	  if (!strncmp (klass, "Filter/Effect/Video", 19))
	    {
	      gchar *idx;
	      
	      if ((idx = strstr (effectname, "TV")))
		{
		  *idx = '\0';
		  pitivi_effectstree_insert_child (tree_effect,
						&child,
						&Tv_iter,
						effectname,
						PITIVI_STOCK_EFFECT_TV);
		  
		}
	      else if ((idx = strstr (effectname, "ideo")))
		{
		  pitivi_effectstree_insert_child (tree_effect,
						&child,
						&Video_iter,
						effectname + 6,
						PITIVI_STOCK_EFFECT_TV);
		}
	      else
		{
		  pitivi_effectstree_insert_child (tree_effect, 
						&child,
						&tree_effect->treeiter,
						effectname,
						PITIVI_STOCK_EFFECT_TV);
		}
	    }
	  break;
	case PITIVI_EFFECT_AUDIO_TYPE:
	  if (!strncmp (klass, "Filter/Effect/Audio", 19))
	    {
	      pitivi_effectstree_insert_child (tree_effect,
					       &child,
					       &tree_effect->treeiter,
					       effectname,
					       PITIVI_STOCK_EFFECT_SOUND);
	    }
	  break;
	case PITIVI_EFFECT_TRANSITION_TYPE:
	  if (strstr (klass, "smpte"))
	    pitivi_effectstree_insert_child (tree_effect,
					     &child,
					     &tree_effect->treeiter,
					     effectname,
					     PITIVI_STOCK_EFFECT_TV);
	  break;
	}
      elements = elements->next;
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
  
  g_signal_connect (tree_effect->treeview, "cursor-changed", G_CALLBACK(pitivi_effectstree_selected_color), \
		    (gpointer) tree_effect);
  g_signal_connect (tree_effect->treeview, "row-expanded", G_CALLBACK(pitivi_effectstree_exp),\
		    (gpointer) tree_effect);
  g_signal_connect (tree_effect->treeview, "row-collapsed", G_CALLBACK(pitivi_effectstree_col),\
		    (gpointer) tree_effect);
  g_signal_connect (tree_effect->treeview, "move-cursor", G_CALLBACK(pitivi_effectstree_cursor_move),\
		    (gpointer) tree_effect);
  gtk_tree_view_append_column(GTK_TREE_VIEW(tree_effect->treeview), pColumn);
}

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
      /*   case PITIVI_EFFECTSWINDOW_PROPERTY: { */
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
pitivi_effectswindow_get_property (GObject * object,
			      guint property_id,
			      GValue * value, GParamSpec * pspec)
{
  PitiviEffectsWindow *self = (PitiviEffectsWindow *) object;

  switch (property_id)
    {
      /*  case PITIVI_EFFECTSWINDOW_PROPERTY: { */
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
      type = g_type_register_static (GTK_TYPE_WINDOW,
				     "PitiviEffectsWindowType", &info, 0);
    }
  return type;
}
