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
 * Insert "added-value" functions here
 */

PitiviEffectsWindow *
pitivi_effectswindow_new(PitiviMainApp *mainapp)
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
  return obj;
}

static void
pitivi_effectswindow_instance_init (GTypeInstance * instance, gpointer g_class)
{
  PitiviEffectsWindow *self = (PitiviEffectsWindow *) instance;
  self->private = g_new0(PitiviEffectsWindowPrivate, 1);

  /* initialize all public and private members to reasonable default values. */ 
  
  self->private->dispose_has_run = FALSE;
  
  /* If you need specific consruction properties to complete initialization, 
   * delay initialization completion until the property is set. 
   */
 
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
  gchar		      *test;
   
  effectstree = (PitiviEffectsTree *) data;
  model = gtk_tree_view_get_model (GTK_TREE_VIEW (treeview));
  pixbuf = gtk_widget_render_icon(effectstree->window, icon, GTK_ICON_SIZE_MENU, NULL);  
  gtk_tree_model_get (GTK_TREE_MODEL (model), TreeIter, PITIVI_TEXT_COLUMN, &name, -1);
  gtk_tree_model_get (GTK_TREE_MODEL (model), TreeIter, PITIVI_POINTER_COLUMN, &test, -1);
  g_printf ("collpase %s %s\n", name, test);
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


static void
pitivi_effectswindow_drag_data_get (GtkWidget          *widget,
				    GdkDragContext     *context,
				    GtkSelectionData   *selection_data,
				    guint               info,
				    guint32             time,
				    gpointer user_data)
{
  gtk_selection_data_set (selection_data, 
			  selection_data->target, 
			  8, 
			  "effects", 
			  strlen ("effects"));
}

static void
pitivi_effectswindow_drag_end (GtkWidget          *widget,
			       GdkDragContext     *context,
			       gpointer		user_data)
{
}

static void
pitivi_effectswindow_drag_data_delete (GtkWidget          *widget,
				       GdkDragContext     *context,
				       gpointer editor)
{
}

static void
pitivi_effectswindow_drag_begin (GtkWidget		*widget,
				 GdkDragContext		*context,
				 gpointer		user_data)
{
}

GList	*
get_transition_effects_list (GstElementFactory		*factory)
{
  GstElementFactory		*trans_fact;
  const gchar			*intern_name;
  GParamSpec			**property_specs;
  GParamSpec			*param;
  GstElement			*element;
  gboolean			readable;
  GList				*fx_prop_list;
  gint				num_properties;
  gint				nb;
  gint				*enum_values;
  gint				i;

  trans_fact = factory;
  intern_name = "transition";
  fx_prop_list = NULL;
  if (trans_fact)
    {
      element = gst_element_factory_create(trans_fact, intern_name);  
      property_specs = g_object_class_list_properties(G_OBJECT_GET_CLASS (element), &num_properties);
      GValue value = { 0, };
      param = property_specs[1];
      readable = FALSE;
      
      g_value_init (&value, param->value_type);
      if (param->flags & G_PARAM_READABLE)
	{
	  g_object_get_property (G_OBJECT (element), param->name, &value);
	  readable = TRUE;
	}
      if (readable)
	{		      
	  if (G_IS_PARAM_SPEC_ENUM (param))
	    {    
	      GEnumClass *class = G_ENUM_CLASS (g_type_class_ref (param->value_type));
	      enum_values = g_new0 (gint, class->n_values);
	       
	      for (i=0; i < class->n_values; i++)
		{
		  GEnumValue *evalue = &class->values[i];		  
		  enum_values[i] = evalue->value;
		  fx_prop_list = g_list_append(fx_prop_list, evalue);
		}
	    }
	}
    }
  return(fx_prop_list);
}


void
insert_audio_effects_on_tree (PitiviEffectsTree *tree_effect, 
			      GtkTreeIter *child, 
			      PitiviSettings *settingslist)
{
  const gchar	*klass;
  const gchar	*effectname;
  const gchar	*desc;
  GList *fx_audio = NULL;

  pitivi_effectstree_insert_child (tree_effect, &tree_effect->treeiter,  NULL,  "Simple Effects",  PITIVI_STOCK_EFFECT_CAT, NULL);
  /* On recupere la liste des effets audio via la structure self */
  while ( settingslist->audio_effects )
    {
      fx_audio = g_list_append(fx_audio,  settingslist->audio_effects->data);
      settingslist->audio_effects = settingslist->audio_effects->next;
    }
  /* On insere les elements audio dans le tree pour le menu des effets */
  while ( fx_audio )
    {
      klass = gst_element_factory_get_klass (fx_audio->data);
      effectname = gst_element_factory_get_longname (fx_audio->data);
      desc = gst_element_factory_get_description (fx_audio->data);
      if (!strncmp (klass, "Filter/Effect/Audio", 19))
	{
	  pitivi_effectstree_insert_child (tree_effect, child, &tree_effect->treeiter,
					   effectname, PITIVI_STOCK_EFFECT_SOUND, NULL);
	}
      fx_audio = fx_audio->next;
    }
}

void
pitivi_effectstree_set_gst (PitiviEffectsTree *tree_effect, 
			    PitiviEffectsTypeEnum eneffects,  
			    PitiviSettings *self)
{
  int				count;  
  GtkCellRenderer		*pCellRenderer;
  GtkTreeViewColumn		*pColumn;
  GdkPixbuf			*pixbuf;
  const GList			*elements;
  GList				*fx_video;
  GList				*fx_audio;
  GList				*fx_transition;
  GList				*fx_transition_prop;
  GList				*smpte_trans_list;
  const gchar			*effectname;
  const gchar			*desc;
  const gchar			*klass;
  GtkTreeIter			Tv_iter;
  GtkTreeIter			Video_iter;
  GtkTreeIter			Trans_iter[18];
  int				i;
  gint				nb_tcat;
  GEnumValue			*trans_fact_data;
  PitiviTransProp		*transProp;
  gint				nb;

  fx_video = NULL;
  fx_audio = NULL;
  fx_transition = NULL;
  fx_transition_prop = NULL;

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
      pitivi_effectstree_insert_child (tree_effect, &tree_effect->treeiter,  NULL,  "Simple Effects",  PITIVI_STOCK_EFFECT_CAT, NULL);
      /* On recupere la liste des effets video via la structure self */
      while (self->video_effects)
	{
	  fx_video = g_list_append(fx_video, self->video_effects->data);
	  self->video_effects = self->video_effects->next;
	}
      /* On creer deux sous categories */
      pitivi_effectstree_insert_child (tree_effect, &Tv_iter, NULL,
				       "Tv Effects", PITIVI_STOCK_EFFECT_CAT, NULL);
      pitivi_effectstree_insert_child (tree_effect, &Video_iter, NULL,
				       "Video Effects", PITIVI_STOCK_EFFECT_CAT, NULL);
      /* On insere les elements video dans le tree pour le menu des effets */
      while (fx_video)
	{
	  klass = gst_element_factory_get_klass (fx_video->data);
	  effectname = gst_element_factory_get_longname (fx_video->data);
	  desc = gst_element_factory_get_description (fx_video->data);
	  g_printf ("video :%s %s\n", effectname, desc);
	  if (!strncmp (klass, "Filter/Effect/Video", 19))
	    {
	      gchar *idx;
	      
	      if ((idx = strstr (effectname, "TV")))
		{
		  *idx = '\0';
		  pitivi_effectstree_insert_child (tree_effect, &child, &Tv_iter,
						   effectname, PITIVI_STOCK_EFFECT_TV, NULL);
		}
	      else if ((idx = strstr (effectname, "ideo")))
		{
		  pitivi_effectstree_insert_child (tree_effect, &child, &Video_iter,
						   effectname + 6, PITIVI_STOCK_EFFECT_TV, NULL);
		}
	      else
		{
		  pitivi_effectstree_insert_child (tree_effect, &child, &tree_effect->treeiter,
						   effectname, PITIVI_STOCK_EFFECT_TV, NULL);
		} 
	    }
	  fx_video = fx_video->next;
	}
      break;

    case PITIVI_EFFECT_AUDIO_TYPE:
      insert_audio_effects_on_tree (tree_effect, &child, self);
      break;
    case PITIVI_EFFECT_TRANSITION_TYPE:
      /* On recupere la liste des effets de transition via la structure self */
      while (self->transition_effects)
	{
	  fx_transition = g_list_append(fx_transition, self->transition_effects->data);
	  self->transition_effects = self->transition_effects->next;
	}

      while ( fx_transition )
	{
	  klass = gst_element_factory_get_klass ( fx_transition->data );
	  effectname = gst_element_factory_get_longname (  fx_transition->data );
	  desc = gst_element_factory_get_description (  fx_transition->data );
	  g_printf ("transition :%s %s\n", effectname, desc);
	  fx_transition = fx_transition->next;
	}

      /* On creer 18 sous categories */
      for (nb_tcat = 0; nb_tcat < PITIVI_LAST_WIPE; nb_tcat++)
	{
	  pitivi_effectstree_insert_child (tree_effect, &Trans_iter[nb_tcat], NULL,
					   transition_cat[nb_tcat], PITIVI_STOCK_EFFECT_CAT, NULL);
	  for (nb = 0; nb < (sizeof (tab_category) / sizeof (PitiviTransProp)); nb++)
	    {
	      /* On test les elements du tableau et on les insere dans les differentes categories */
	      if (nb_tcat == tab_category[nb].id_categorie && tab_category[nb].name)
		{
		  pitivi_effectstree_insert_child (tree_effect, &child, &Trans_iter[nb_tcat],
						   tab_category[nb].name, tab_category[nb].image, NULL);
		}
	    }
	}
      pitivi_effectstree_insert_child (tree_effect, &tree_effect->treeiter,  NULL,  "Simple Effects",  PITIVI_STOCK_EFFECT_CAT, "toto");
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
  
  g_signal_connect (tree_effect->treeview, "cursor-changed", G_CALLBACK(pitivi_effectstree_selected_color), \
		    (gpointer) tree_effect);
  g_signal_connect (tree_effect->treeview, "row-expanded", G_CALLBACK(pitivi_effectstree_exp),\
		    (gpointer) tree_effect);
  g_signal_connect (tree_effect->treeview, "row-collapsed", G_CALLBACK(pitivi_effectstree_col),\
		    (gpointer) tree_effect);
  g_signal_connect (tree_effect->treeview, "move-cursor", G_CALLBACK(pitivi_effectstree_cursor_move),\
		    (gpointer) tree_effect);
  gtk_tree_view_append_column(GTK_TREE_VIEW (tree_effect->treeview), pColumn);
  
  // Drag 'n Drop Activation
  
  gtk_drag_source_set (GTK_WIDGET (tree_effect->treeview), 
		      GDK_BUTTON1_MASK,
		      TargetEntries, iNbTargetEntries, 
		      GDK_ACTION_COPY);

  g_signal_connect (tree_effect->treeview, "drag_data_get",	      
		    G_CALLBACK (pitivi_effectswindow_drag_data_get), tree_effect);
  g_signal_connect (tree_effect->treeview, "drag_end",	      
		    G_CALLBACK (pitivi_effectswindow_drag_end), tree_effect);
  g_signal_connect (tree_effect->treeview, "drag_begin",	      
		    G_CALLBACK (pitivi_effectswindow_drag_begin), tree_effect);
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
      type = g_type_register_static (PITIVI_WINDOWS_TYPE,
				     "PitiviEffectsWindowType", &info, 0);
    }
  return type;
}
