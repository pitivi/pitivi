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
#include "pitivi-projectsettings.h"

struct _PitiviProjectSettingsPrivate
{
  /* instance private members */
  gboolean	dispose_has_run;
};

/*
 * forward definitions
 */

GstCaps			*pitivi_projectsettings_default_vcaps_create( );
GstCaps			*pitivi_projectsettings_default_acaps_create( );

/*
 * Insert "added-value" functions here
 */

/* Creation des GstCaps Audio et Video */
GstCaps *
pitivi_projectsettings_vcaps_create (int width, int height, int framerate)
{
  GstCaps	*caps;
  
  caps = gst_caps_new_simple(
			     "video/x-raw-yuv",
			     "width", G_TYPE_INT, width,
			     "height", G_TYPE_INT, height,
			     "framerate", G_TYPE_INT, framerate,
			     NULL );
  return (caps);
}


/**************/
GstCaps *
pitivi_projectsettings_acaps_create (int rate, int channels)
{
  GstCaps	*caps;
  
  caps = gst_caps_new_simple(
			     "audio/x-raw-int",
			     "rate",  G_TYPE_INT, rate,
			     "channels", G_TYPE_INT, channels,
			     NULL );
  return (caps);
}


/**************/
PitiviProjectSettings *
pitivi_projectsettings_new_with_name(gchar *name, gchar *desc, 
				     GSList *list_media_settings)
{
  PitiviProjectSettings	*projectsettings;
  PitiviMediaSettings	*media_temp;
  int			j;

  /* Creation du PitiviProjectSetting */
  projectsettings = pitivi_projectsettings_new();
  projectsettings->media_settings = NULL;
  
  /* Remplit les champs name, description */
  projectsettings->name = g_strdup(name);
  projectsettings->description = g_strdup(desc);

  /* Remplit la liste des Categorie envoyee en parametre */
  projectsettings->media_settings = NULL;
  for (j = 0; (media_temp = (PitiviMediaSettings *) g_slist_nth_data(list_media_settings, j) ); j++)
    projectsettings->media_settings = g_slist_append( projectsettings->media_settings, 
						      (gpointer) media_temp );
  return projectsettings;
}


/* Creation d'un PitiviCategorieSettings */
PitiviCategorieSettings *
pitivi_projectsettings_categorie_new(gchar *name, GSList *list_settings)
{
  PitiviCategorieSettings	*categorie;
  PitiviProjectSettings		*setting_temp;
  int				j;
  
  categorie = g_new0(PitiviCategorieSettings, 1);
  categorie->name = g_strdup(name);
  
  categorie->list_settings = NULL;
  for (j = 0; (setting_temp = (PitiviProjectSettings *) g_slist_nth_data(list_settings, j) ); j++)
    categorie->list_settings = g_slist_append( categorie->list_settings, (gpointer) setting_temp );
  
  return (categorie);
}


/*
  Creation d'un PitiviMediaSetting
*/
PitiviMediaSettings *
pitivi_projectsettings_media_new( gchar *codec_factory_name, GstCaps *caps, gint index )
{
  PitiviMediaSettings	*media_setting;
  PitiviSettingsValue	*setting_value;
  GstElementFactory	*factory;
  GstElement		*element;
  GParamSpec		**property_specs;
  gboolean		readable;
  gint			num_properties;
  gint			i;

  media_setting = g_new0(PitiviMediaSettings, 1);
  media_setting->codec_settings = g_new0(GSList, 1);
  
  media_setting->combo_box_codec_index = index;
  media_setting->codec_factory_name = g_strdup(codec_factory_name);

  /* Recuperation des proprietes*/
  factory = gst_element_factory_find( codec_factory_name );
  if (factory)
    {
      element = gst_element_factory_create(factory, media_setting->codec_factory_name);
      if (element)
	{
	  property_specs = g_object_class_list_properties(G_OBJECT_GET_CLASS (element), &num_properties);
	  for (i = 0; i < num_properties; i++)
	    {
	      GParamSpec *param = property_specs[i];
	  
	      readable = FALSE;
	      setting_value = g_new0( PitiviSettingsValue, 1);
	      g_value_init (&setting_value->value, param->value_type);
	  
	      if (param->flags & G_PARAM_READABLE)
		{
		  g_object_get_property (G_OBJECT (element), param->name, &setting_value->value);
		  readable = TRUE;
		}
	      setting_value->name = g_strdup (g_param_spec_get_nick (param));
	      media_setting->codec_settings = g_slist_append(media_setting->codec_settings, setting_value);
	    }
      
	  /* Creation du caps par default pour le reglage */
	  if ( caps != NULL )
	    {
	      media_setting->caps = g_new0(GstCaps, 1);
	      media_setting->caps = gst_caps_copy(caps);
	    }
	}
    }
  return (media_setting);
}

/* Creation de la liste des Reglages par default */

GSList *
pitivi_projectsettings_list_make()
{
  GSList			*list_categories;
  GSList			*list_reglage;
  GSList			*list_media_settings;
  PitiviMediaSettings		*media_setting;
  GstCaps			*default_vcaps;
  GstCaps			*default_acaps;
  
/* Initialisation des caps par default */
  default_vcaps = pitivi_projectsettings_vcaps_create(720, 576, 25);
  default_acaps = pitivi_projectsettings_acaps_create(48000, 1);

/* Initialisation du debut des liste */
  list_media_settings = NULL;
  list_reglage = NULL;
  list_categories = NULL;

/* Categorie 1 */
  list_media_settings = g_slist_append(list_media_settings, (gpointer) pitivi_projectsettings_media_new("epitivovenc", default_vcaps, 0) );
  list_media_settings = g_slist_append(list_media_settings, (gpointer) pitivi_projectsettings_media_new("epitivoaenc", default_acaps, 0) );
  list_reglage = g_slist_append(list_reglage, (gpointer) pitivi_projectsettings_new_with_name("Standard 32kHz", 
											      "Description Standard 32kHz", 
											      list_media_settings ) );
  list_reglage = g_slist_append(list_reglage, (gpointer) pitivi_projectsettings_new_with_name("Standard 48kHz", 
											      "Description Standard 48kHz", 
											      list_media_settings ) );
  list_reglage = g_slist_append(list_reglage, (gpointer) pitivi_projectsettings_new_with_name("Widescreen 32kHz", 
											      "Description Widescreen 32kHz", 
											      list_media_settings ) );
  list_reglage = g_slist_append(list_reglage, (gpointer) pitivi_projectsettings_new_with_name("Widescreen 48kHz", 
											      "Description Widescreen 48kHz", 
											      list_media_settings ) );
  list_categories = g_slist_append(list_categories, (gpointer) pitivi_projectsettings_categorie_new("DV - NTSC", list_reglage) );
  
/* Categorie 2 */
  list_categories = g_slist_append(list_categories, (gpointer) pitivi_projectsettings_categorie_new("DV - PAL", list_reglage) );
  
/* Categorie 3 */
  list_media_settings = NULL;
  list_media_settings = g_slist_append(list_media_settings, (gpointer) pitivi_projectsettings_media_new("epitivovenc", default_vcaps, 0 ) );
  list_media_settings = g_slist_append(list_media_settings, (gpointer) pitivi_projectsettings_media_new("epitivoaenc", default_acaps, 0 ) );
  
  list_reglage = NULL;
  list_reglage = g_slist_append(list_reglage, (gpointer) pitivi_projectsettings_new_with_name("Multimedia Video", 
											      "Description Multimedia Video", 
											      list_media_settings) );
  list_reglage = g_slist_append(list_reglage, (gpointer) pitivi_projectsettings_new_with_name("Quicktime for Web", 
											      "Description Quicktime for Web", 
											      list_media_settings) );
  list_reglage = g_slist_append(list_reglage, (gpointer) pitivi_projectsettings_new_with_name("Petit test", 
											      "Description Petit test", 
											      list_media_settings) );
  list_categories = g_slist_append(list_categories, (gpointer) pitivi_projectsettings_categorie_new("Custom Settings", list_reglage) );
  
/* Categorie 4 */
  list_reglage = NULL;
  list_categories = g_slist_append(list_categories, (gpointer) pitivi_projectsettings_categorie_new("Personnal Settings", list_reglage) );
  
  return (list_categories);
}

/*
  pitivi_projectsettings_save_thyself

  Enregistre les proprietes de self dans une structure XML fils de parent

  Renvoie la structure pere
*/

xmlNodePtr	
pitivi_projectsettings_save_thyself(PitiviProjectSettings *self, xmlNodePtr parent)
{
  xmlNodePtr	selfptr, msetptr;
  GSList	*mset;
  PitiviMediaSettings	*cat1;

  selfptr = xmlNewChild (parent, NULL, "projectsettings", NULL);

  xmlNewChild (selfptr, NULL, "name", self->name);
  xmlNewChild (selfptr, NULL, "description", self->description);
  
  for (mset = self->media_settings; mset; mset = mset->next) {
    cat1 = (PitiviMediaSettings *) mset->data;

    msetptr = xmlNewChild(selfptr, NULL, "media_settings", NULL);

    /* TODO : save the codec_settings */
    
    xmlNewChild(msetptr, NULL, "codec_factory_name", cat1->codec_factory_name);

    gst_caps_save_thyself(cat1->caps, msetptr);
  }

  return parent;
}

/*
  pitivi_projectsettings_restore_thyself

  Remplis l'objet tofill avec les donnes contenus dans self
*/

void
pitivi_projectsettings_restore_thyself(PitiviProjectSettings *tofill, xmlNodePtr self)
{
  xmlNodePtr children;

  for (children = self->xmlChildrenNode; children; children = children->next) {
    if (!strcmp("name", children->name)) {
      tofill->name = xmlNodeGetContent(children);
    } else if (!strcmp("description", xmlNodeGetContent(children))) {
      tofill->description = xmlNodeGetContent(children);
    }
    /*
      TODO

      Restore the rest of the settings
    */
  }
}

/*
  pitivi_projectsettings_copy

  Makes a copy of the given PitiviProjectSettings

  Returns the copy
*/

PitiviProjectSettings *
pitivi_projectsettings_copy(PitiviProjectSettings *self)
{
  PitiviProjectSettings	*res;
  GSList		*mset, *cset;
  PitiviMediaSettings	*cat1, *cat2;
  PitiviSettingsValue	*val1, *val2;

  if (self == NULL)
    return NULL;

  res = pitivi_projectsettings_new();
  res->name = g_strdup(self->name);
  res->description = g_strdup(self->description);
  res->media_settings = NULL;
  
  for (mset = res->media_settings; mset; mset = mset->next) {
    cat1 = (PitiviMediaSettings *) mset->data;
    cat2 = g_new0(PitiviMediaSettings, 1);

    cat2->codec_factory_name = g_strdup(cat1->codec_factory_name);
    cat2->codec_settings = NULL;

    for (cset = cat1->codec_settings; cset; cset = cset->next) {
      val1 = (PitiviSettingsValue *) cset->data;
      val2 = g_new0(PitiviSettingsValue, 1);
      
      val2->name = g_strdup(val1->name);
      g_value_init(&(val2->value), G_VALUE_TYPE(&(val1->value)));
      g_value_copy(&(val1->value), &(val2->value));
      
      cat2->codec_settings = g_slist_append(cat2->codec_settings, val2);
    }

    cat2->caps = gst_caps_copy(cat1->caps);
    res->media_settings = g_slist_append(res->media_settings, cat2);
  }

  return res;
}

PitiviProjectSettings *
pitivi_projectsettings_new(void)
{
  PitiviProjectSettings	*projectsettings;

  projectsettings = (PitiviProjectSettings *) 
    g_object_new(PITIVI_PROJECTSETTINGS_TYPE, NULL);
  g_assert(projectsettings != NULL);
  return projectsettings;
}

static GObject *
pitivi_projectsettings_constructor (GType type, 
				    guint n_construct_properties,
				    GObjectConstructParam *construct_properties)
{
  GObject *obj;
  {
    /* Invoke parent constructor. */
    PitiviProjectSettingsClass	*klass;
    GObjectClass		*parent_class;
    klass = PITIVI_PROJECTSETTINGS_CLASS (g_type_class_peek (PITIVI_PROJECTSETTINGS_TYPE));
    parent_class = G_OBJECT_CLASS (g_type_class_peek_parent (klass));
    obj = parent_class->constructor (type, 
				     n_construct_properties,
				     construct_properties);
  }
  
  /* do stuff. */

  return obj;
}

static void
pitivi_projectsettings_instance_init (GTypeInstance * instance, gpointer g_class)
{
  PitiviProjectSettings *self = (PitiviProjectSettings *) instance;

  self->private = g_new0(PitiviProjectSettingsPrivate, 1);
  
  /* initialize all public and private members to reasonable default values. */ 
  
  self->private->dispose_has_run = FALSE;
  
  /* If you need specific consruction properties to complete initialization, 
   * delay initialization completion until the property is set. 
   */
}

static void
pitivi_projectsettings_dispose (GObject *object)
{
  PitiviProjectSettings	*self = PITIVI_PROJECTSETTINGS(object);

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
pitivi_projectsettings_finalize (GObject *object)
{
  PitiviProjectSettings	*self = PITIVI_PROJECTSETTINGS(object);

  /* 
   * Here, complete object destruction. 
   * You might not need to do much... 
   */

  g_free (self->private);
}

static void
pitivi_projectsettings_set_property (GObject * object,
			      guint property_id,
			      const GValue * value, GParamSpec * pspec)
{
  PitiviProjectSettings *self = (PitiviProjectSettings *) object;

  switch (property_id)
    {
      /*   case PITIVI_PROJECTSETTINGS_PROPERTY: { */
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
pitivi_projectsettings_get_property (GObject * object,
			      guint property_id,
			      GValue * value, GParamSpec * pspec)
{
  PitiviProjectSettings *self = (PitiviProjectSettings *) object;

  switch (property_id)
    {
      /*  case PITIVI_PROJECTSETTINGS_PROPERTY: { */
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
pitivi_projectsettings_class_init (gpointer g_class, gpointer g_class_data)
{
  GObjectClass *gobject_class = G_OBJECT_CLASS (g_class);
  PitiviProjectSettingsClass *klass = PITIVI_PROJECTSETTINGS_CLASS (g_class);

  gobject_class->constructor = pitivi_projectsettings_constructor;
  gobject_class->dispose = pitivi_projectsettings_dispose;
  gobject_class->finalize = pitivi_projectsettings_finalize;

  gobject_class->set_property = pitivi_projectsettings_set_property;
  gobject_class->get_property = pitivi_projectsettings_get_property;

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
pitivi_projectsettings_get_type (void)
{
  static GType type = 0;
 
  if (type == 0)
    {
      static const GTypeInfo info = {
	sizeof (PitiviProjectSettingsClass),
	NULL,			/* base_init */
	NULL,			/* base_finalize */
	pitivi_projectsettings_class_init,	/* class_init */
	NULL,			/* class_finalize */
	NULL,			/* class_data */
	sizeof (PitiviProjectSettings),
	0,			/* n_preallocs */
	pitivi_projectsettings_instance_init	/* instance_init */
      };
      type = g_type_register_static (G_TYPE_OBJECT,
				     "PitiviProjectSettingsType", &info, 0);
    }
  return type;
}
