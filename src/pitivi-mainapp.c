/* 
 * PiTiVi
 * Copyright (C) <2004> Edward Hervey <hervey_e@epita.fr>
 *                      Bloch Stephan <bloch_s@epita.fr>
 *                      Carbon Julien <carbon_j@epita.fr>
 *                      Dubart Loic <dubart_l@epita.fr>
 *			Guillaume Casanova <casano_g@epita.fr>
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

/* Recuperation des caps */
/*   pad_sink = gst_element_get_pad(element, "sink"); */
/*   media_setting->caps = gst_pad_get_caps(pad_sink); */
/*   g_print("Caps Sink:\n%s.\n", gst_caps_to_string (media_setting->caps)); */
/*   pad_src = gst_element_get_pad(element, "src"); */
/*   media_setting->caps = gst_pad_get_caps(pad_src); */
/*   g_print("Caps Src:\n%s.\n", gst_caps_to_string (media_setting->caps)); */
/*   media_setting->caps = gst_caps_new_simple ("my_caps", "audio/wav",  */
/* 					     NULL); */

/* 
   - Affichage des champs des Settings lorsqu'on clique sur un reglage de la liste
   - Modifier un reglage
   - Supprimer un reglage de la liste de PitiviProjectSettings
*/

#include <gst/gst.h>
#include "pitivi.h"
#include "pitivi-mainapp.h"
#include "pitivi-toolboxwindow.h"
#include "pitivi-newprojectwindow.h"
#include "pitivi-projectsettings.h"
#include "pitivi-settings.h"


struct _PitiviMainAppPrivate
{
  /* instance private members */
  gboolean			dispose_has_run;
  GSList			*project_settings_list;
  PitiviToolboxWindow		*tbxwin;
  PitiviNewProjectWindow	*win_new_project;
  PitiviSettings		*global_settings;
};


/*
 * forward definitions
 */
void			pitivi_mainapp_destroy			(GtkWidget *pWidget, gpointer pData);
void			pitivi_mainapp_add_newcategory		( PitiviMainApp *self, const gchar *cat_name);
void			pitivi_mainapp_add_newsetting		( PitiviMainApp *self, PitiviProjectSettings *new_setting, gint *position );

/*
 * Insert "added-value" functions here
 */

PitiviSettings *
pitivi_mainapp_settings(PitiviMainApp *self) {
  return self->private->global_settings;
}

void
pitivi_mainapp_destroy(GtkWidget *pWidget, gpointer pData)
{
  gtk_main_quit();
}

/* 
   Add 'new_category' into the project_category_list when 
   the Add_category is clicked in the PitiviNewProjectWindow
*/
void
pitivi_mainapp_add_newcategory (PitiviMainApp *self, 
				const gchar *cat_name)
{
  PitiviCategorieSettings	*new_category;
  
  new_category = pitivi_projectsettings_categorie_new( (gchar *) cat_name, NULL );
  self->private->project_settings_list = 
    g_slist_append( self->private->project_settings_list, (gpointer) new_category );
}

/* 
   Add 'new_setting' into the project_settings_list when 
   the Add_button is clicked in the PitiviNewProjectWindow
*/
void
pitivi_mainapp_add_newsetting( PitiviMainApp *self, 
			       PitiviProjectSettings *new_setting,
			       gint *position )
{
  PitiviCategorieSettings	*category;
  PitiviProjectSettings		*reglage;
  
  category = (PitiviCategorieSettings *) g_slist_nth_data(self->private->project_settings_list, position[0] );
  category->list_settings = g_slist_append( category->list_settings, (gpointer) new_setting );
}

/*
    Return The category selected in the GtkTreeStore
*/
PitiviCategorieSettings *
pitivi_mainapp_get_selected_category( PitiviMainApp *self, gint *position )
{
  PitiviCategorieSettings	*selected_category;

  selected_category = (PitiviCategorieSettings *) 
    g_slist_nth_data(self->private->project_settings_list, 
		     position[0]);
  return (selected_category);
}

/* 
   Return the GSList of PitiviCategorySettings
*/
GSList *
pitivi_mainapp_project_settings(PitiviMainApp *self)
{
  return ( self->private->project_settings_list );
}

void
pitivi_mainapp_create_wintools (PitiviMainApp *self)
{
  
  /* Source List Window */
  
  if (!GTK_IS_WIDGET (self->timelinewin))
    {
      self->timelinewin = pitivi_timelinewindow_new();
      gtk_widget_show_all (GTK_WIDGET (self->timelinewin) );
      gtk_window_move (GTK_WINDOW (self->timelinewin), 110, 450);
    }

  /* Source List Window */
  
  if (!GTK_IS_WIDGET (self->srclistwin))
    {
      self->srclistwin = pitivi_sourcelistwindow_new(self);
      gtk_widget_show_all (GTK_WIDGET (self->srclistwin) );
      gtk_window_move (GTK_WINDOW (self->srclistwin), 110, 100);
    }
  
  /* Effects Window */
  
  if (!GTK_IS_WIDGET (self->effectswin))
    {
      self->effectswin = pitivi_effectswindow_new();
      gtk_widget_show_all (GTK_WIDGET (self->effectswin) );
      gtk_window_move (GTK_WINDOW (self->effectswin), 720, 450);
    }
  
  if (!GTK_IS_WIDGET (self->viewerwin))
    {
      self->viewerwin = pitivi_viewerwindow_new();
      gtk_window_move (GTK_WINDOW (self->viewerwin), 720, 100);
    }
  gtk_window_move (GTK_WINDOW (self->private->tbxwin), 20, 450);
}


PitiviMainApp *
pitivi_mainapp_new (void)
{
  PitiviMainApp *mainapp;
  
  mainapp = (PitiviMainApp *) g_object_new (PITIVI_MAINAPP_TYPE, NULL);
  g_assert (mainapp != NULL);

  return mainapp;
}

static GObject *
pitivi_mainapp_constructor (GType type,
			    guint n_construct_properties,
			    GObjectConstructParam * construct_properties)
{
  PitiviMainApp	*self;
  GObject	*obj;
  {
    /* Invoke parent constructor. */
    PitiviMainAppClass *klass;
    GObjectClass *parent_class;
    klass = PITIVI_MAINAPP_CLASS (g_type_class_peek (PITIVI_MAINAPP_TYPE));
    parent_class = G_OBJECT_CLASS (g_type_class_peek_parent (klass));
    obj = parent_class->constructor (type, n_construct_properties,
				     construct_properties);
  }

  /* do stuff. */

  self = (PitiviMainApp *) obj;
  /* Enregistrement des Icones */
  pitivi_stockicons_register ();
  /* Creation de la liste des settings par default */
  self->private->project_settings_list = pitivi_projectsettings_list_make();
  /* Creation de la toolboxwindow */
  self->private->tbxwin = pitivi_toolboxwindow_new(self);
  /* Creation des settings globaux */
  self->private->global_settings = pitivi_settings_new();
  /* Connection des Signaux */
  g_signal_connect(G_OBJECT(self->private->tbxwin), "delete_event",
		   G_CALLBACK(pitivi_mainapp_destroy), NULL);
  gtk_widget_show_all (GTK_WIDGET (self->private->tbxwin));

  return obj;
}

static void
pitivi_mainapp_instance_init (GTypeInstance * instance, gpointer g_class)
{
  PitiviMainApp			*self = (PitiviMainApp *) instance;
  PitiviSourceListWindow	*sourcelist;

  self->private = g_new0 (PitiviMainAppPrivate, 1);

  /* initialize all public and private members to reasonable default values. */

  self->private->dispose_has_run = FALSE;

  /* If you need specific consruction properties to complete initialization, 
   * delay initialization completion until the property is set. 
   */
}

static void
pitivi_mainapp_dispose (GObject * object)
{
  PitiviMainApp *self = PITIVI_MAINAPP (object);

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
pitivi_mainapp_finalize (GObject * object)
{
  PitiviMainApp *self = PITIVI_MAINAPP (object);

  /* 
   * Here, complete object destruction. 
   * You might not need to do much... 
   */
  
  g_object_unref (self->private->tbxwin);
  g_object_unref (self->private->win_new_project);
  g_free (self->private);
}

static void
pitivi_mainapp_set_property (GObject * object,
			     guint property_id,
			     const GValue * value, GParamSpec * pspec)
{
  PitiviMainApp *self = (PitiviMainApp *) object;

  switch (property_id)
    {
      /*   case PITIVI_MAINAPP_PROPERTY: { */
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
pitivi_mainapp_get_property (GObject * object,
			     guint property_id,
			     GValue * value, GParamSpec * pspec)
{
  PitiviMainApp *self = (PitiviMainApp *) object;

  switch (property_id)
    {
      /*  case PITIVI_MAINAPP_PROPERTY: { */
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
pitivi_mainapp_class_init (gpointer g_class, gpointer g_class_data)
{
  GObjectClass *gobject_class = G_OBJECT_CLASS (g_class);
  PitiviMainAppClass *klass = PITIVI_MAINAPP_CLASS (g_class);

  gobject_class->constructor = pitivi_mainapp_constructor;
  gobject_class->dispose = pitivi_mainapp_dispose;
  gobject_class->finalize = pitivi_mainapp_finalize;

  gobject_class->set_property = pitivi_mainapp_set_property;
  gobject_class->get_property = pitivi_mainapp_get_property;

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
pitivi_mainapp_get_type (void)
{
  static GType type = 0;

  if (type == 0)
    {
      static const GTypeInfo info = {
	sizeof (PitiviMainAppClass),
	NULL,				/* base_init */
	NULL,				/* base_finalize */
	pitivi_mainapp_class_init,	/* class_init */
	NULL,				/* class_finalize */
	NULL,				/* class_data */
	sizeof (PitiviMainApp),
	0,				/* n_preallocs */
	pitivi_mainapp_instance_init	/* instance_init */
      };
      type = g_type_register_static (G_TYPE_OBJECT,
				     "PitiviMainAppType", &info, 0);
    }

  return type;
}
