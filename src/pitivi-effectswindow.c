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

#include <gtk/gtk.h>
#include "pitivi.h"
#include "pitivi-effectswindow.h"

static GtkWindowClass *parent_class = NULL;

struct _PitiviEffectsWindowPrivate
{
  /* instance private members */
  gboolean	  dispose_has_run;
  guint		  notebook_id;
  GtkWidget	  *notebook;
  PitiviTreeModel *first;
  GList		  *compounds;
};

/*
 * forward definitions
 */

enum {
  TABTREE_ACTIVATE_SIGNAL = 1,
  TABTREE_LAST_SIGNAL
};

static guint tabtreeview_signals[TABTREE_LAST_SIGNAL] = { 0 };


enum {
  NOTEBOOK_LABELS = 1,
  NOTEBOOK_NEW_LABEL,
  NOTEBOOK_NEW_STYLE,
  LAST_ENUM_TABTREE,
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
pitivi_insert_newtabtree(PitiviEffectsWindow *self, PitiviTreeModel *tree)
{
  PitiviEffectsWindowPrivate *priv;
  GtkWidget *vbox_tree;

  g_return_if_fail (self);
  g_return_if_fail (tree);
  
  priv = self->private;
  vbox_tree = gtk_vbox_new (FALSE, 0);
  gtk_box_pack_start (GTK_BOX (vbox_tree), GTK_WIDGET(tree->treeview),
		      TRUE, TRUE, 0);
  gtk_notebook_append_page( GTK_NOTEBOOK (priv->notebook),
			    vbox_tree,
			    tree->label);
  gtk_label_set_justify (GTK_LABEL ( tree->label ), GTK_JUSTIFY_LEFT);
  gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(tree->scroll), GTK_POLICY_AUTOMATIC, GTK_POLICY_AUTOMATIC);
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
  gtk_window_set_default_size(GTK_WINDOW (self), 150, 100);
  self->private->notebook = gtk_notebook_new ();
  gtk_notebook_set_tab_pos (GTK_NOTEBOOK (self->private->notebook), GTK_POS_TOP);
  main_vbox = gtk_vbox_new (FALSE, 0);
  gtk_container_add (GTK_CONTAINER (self), main_vbox);
  gtk_box_pack_start (GTK_BOX (main_vbox), GTK_WIDGET(self->private->notebook),
		      TRUE, TRUE, 0);
  
  PitiviTreeModel *videotree = g_new0(PitiviTreeModel, 1);
  videotree->label = gtk_label_new ("Video");
  videotree->treeview = gtk_tree_view_new ();
  videotree->scroll = gtk_scrolled_window_new (NULL, NULL);
  pitivi_insert_newtabtree(self, videotree);
  
  PitiviTreeModel *audiotree = g_new0(PitiviTreeModel, 1);
  audiotree->label = gtk_label_new ("Audio");
  audiotree->treeview = gtk_tree_view_new ();
  audiotree->scroll = gtk_scrolled_window_new (NULL, NULL);
  pitivi_insert_newtabtree(self, audiotree);

  PitiviTreeModel *autretree = g_new0(PitiviTreeModel, 1);
  autretree->label = gtk_label_new ("Autre");  
  autretree->treeview = gtk_tree_view_new ();
  autretree->scroll = gtk_scrolled_window_new (NULL, NULL);
  pitivi_insert_newtabtree(self, autretree);
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
