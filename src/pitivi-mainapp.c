/* 
 * PiTiVi
 * Copyright (C) <2004> Edward G. Hervey <hervey_e@epita.fr>
 *                      Bloch Stephan <bloch_s@epita.fr>
 *                      Carbon Julien <carbon_j@epita.fr>
 *                      Dubart Loic <dubart_l@epita.fr>
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
#include "pitivi-mainapp.h"
#include "pitivi-toolboxwindow.h"
#include "pitivi-sourcelistwindow.h"
#include "pitivi-newprojectwindow.h"
#include "pitivi-projectsettings.h"


struct _PitiviMainAppPrivate
{
  /* instance private members */
  gboolean			dispose_has_run;
  GSList			*project_settings_list;
  PitiviToolboxWindow		*tbxwin;
  PitiviSourceListWindow	*srclistwin;
  PitiviNewProjectWindow	*win_new_project;
};

/*
 * forward definitions
 */
GSList			*pitivi_mainapp_project_settings	( PitiviMainApp *self );
PitiviCategorieSettings	*pitivi_create_new_categorie		( gchar *name, GSList *list_settings);

/*
 * Insert "added-value" functions here
 */

void
pitivi_mainapp_destroy(GtkWidget *pWidget, gpointer pData)
{
  gtk_main_quit();
}

PitiviMediaSettings *
pitivi_list_settings_make(gchar *codec_factory_name)
{
  
  return ;
}

PitiviSettingsValue *
pitivi_list_media_settings_make(gchar *codec_factory_name)
{
  
  return ;
}

PitiviCategorieSettings *
pitivi_create_new_categorie(gchar *name, GSList *list_settings)
{
  PitiviCategorieSettings	*categorie;
  PitiviProjectSettings		*setting;
  
  categorie = g_new0(PitiviCategorieSettings, 1);
  categorie->list_settings = NULL;

  categorie->name = g_strdup(name);
  categorie->list_settings = list_settings;
  return (categorie);
}

GSList *
pitivi_projectsettings_list_make()
{
  GSList			*list_categories;
  GSList			*list_reglage;
  GSList			*list_media_settings;
  GSList			*list_settings;

/* Initialisation du debut de la liste des categories */
  list_categories = NULL;
  list_reglage = NULL;
  list_settings = NULL;
  list_media_settings = NULL;
  
/* Categorie 1 */
  
/*   list_media_settings = g_slist_append(list_media_settings, (gpointer) pitivi_list_media_settings_make("6Codec", "Y4mEncode") ); */
/*   list_media_settings = g_slist_append(list_media_settings, (gpointer) pitivi_list_media_settings_make("Y4mEncode", 720, 576) ); */
/*   list_settings = g_slist_append(list_settings, (gpointer) list_settings_make() ); */
  
  list_reglage = g_slist_append(list_reglage, (gpointer) pitivi_projectsettings_new_with_name("Standard 32kHz", "Description") );
  list_reglage = g_slist_append(list_reglage, (gpointer) pitivi_projectsettings_new_with_name("Standard 48kHz", "Description") );
  list_reglage = g_slist_append(list_reglage, (gpointer) pitivi_projectsettings_new_with_name("Widescreen 32kHz", "Description") );
  list_reglage = g_slist_append(list_reglage, (gpointer) pitivi_projectsettings_new_with_name("Widescreen 48kHz", "Description") );
  list_categories = g_slist_append(list_categories, (gpointer) pitivi_create_new_categorie("DV - NTSC", list_reglage) );
  /***************/
  
/* Categorie 2 */
  list_reglage = NULL;
  list_reglage = g_slist_append(list_reglage, (gpointer) pitivi_projectsettings_new_with_name("Standard 32kHz", "Description") );
  list_reglage = g_slist_append(list_reglage, (gpointer) pitivi_projectsettings_new_with_name("Standard 48kHz", "Description") );
  list_reglage = g_slist_append(list_reglage, (gpointer) pitivi_projectsettings_new_with_name("Widescreen 32kHz", "Description") );
  list_reglage = g_slist_append(list_reglage, (gpointer) pitivi_projectsettings_new_with_name("Widescreen 48kHz", "Description") );
  list_categories = g_slist_append(list_categories, (gpointer) pitivi_create_new_categorie("DV - PAL", list_reglage) );
/***************/

/* Categorie 3 */
  list_reglage = NULL;
  list_reglage = g_slist_append(list_reglage, (gpointer) pitivi_projectsettings_new_with_name("Multimedia Video", "Description") );
  list_reglage = g_slist_append(list_reglage, (gpointer) pitivi_projectsettings_new_with_name("Quicktime for Web", "Description") );
  list_reglage = g_slist_append(list_reglage, (gpointer) pitivi_projectsettings_new_with_name("Petit test", "Description") );
  list_categories = g_slist_append(list_categories, (gpointer) pitivi_create_new_categorie("Custom Settings", list_reglage) );
/***************/

/* Categorie 4 */
  list_reglage = NULL;
  list_categories = g_slist_append(list_categories, (gpointer) pitivi_create_new_categorie("Personnal Settings", list_reglage) );

  return (list_categories);
}

GSList *
pitivi_mainapp_project_settings(PitiviMainApp *self)
{
  return ( self->private->project_settings_list );
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
  /* Creation de la liste des settings */
  self->private->project_settings_list = pitivi_projectsettings_list_make();
  /* Creation de la toolboxwindow */
  self->private->tbxwin = pitivi_toolboxwindow_new(self);
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
