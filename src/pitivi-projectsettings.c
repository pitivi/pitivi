/* 
 * PiTiVi
 * Copyright (C) <2004> Edward G. Hervey <hervey_e@epita.fr>
 *                      Guillaume Casanova <casano_g@epita.fr>
 *			Stefan Bloch <bloch_s@epita.fr>
 *			Loic Dubart <dubart_l@epita.fr>
 *			Julien Carbonnier <carbon_j@epita.fr>
 *			Marc Delettrez <delett_m@epita.fr>
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
pitivi_projectsettings_new_with_name(gchar *name, gchar *desc/* , GSList *list_media_settings */)
{
  PitiviProjectSettings	*projectsettings;
  GSList		*list;
  GList			*list_prop;
  PitiviMediaSettings	*media_temp;
  PitiviMediaSettings	*media_new;
  PitiviSettingsValue	*prop_temp;
  PitiviSettingsValue	*prop_new;

  projectsettings = g_new0(PitiviProjectSettings, 1);
  projectsettings->name = g_strdup(name);
  projectsettings->description = g_strdup(desc);
  projectsettings->media_settings = NULL;

/*   for (list = list_media_settings; list; list = list->next) { */
/*     media_temp = (PitiviMediaSettings *) list->data; */
/*     media_new = g_new0(PitiviMediaSettings, 1); */
    
/*     media_new->codec_factory_name = g_strdup(media_temp->codec_factory_name); */
/*     media_new->codec_properties = NULL; */
    
/*     g_print("MEDIA NAME : %s.\n", media_new->codec_factory_name); */


/*     for (list_prop = media_temp->codec_properties; list_prop; list_prop = list_prop->next) { */
/*       prop_temp = (PitiviSettingsValue *) list_prop->data; */
/*       prop_new = g_new0(PitiviSettingsValue, 1); */
      
/*       prop_new->name = g_strdup(prop_temp->name); */
/*       g_value_init(&(prop_new->value), G_VALUE_TYPE(&(prop_temp->value))); */
/*       g_value_copy(&(prop_temp->value), &(prop_new->value)); */
      
/*       g_print("PROP NAME : %s.\nVALUE : \n\n", media_new->codec_factory_name); */
/*       media_new->codec_properties = g_list_append(media_new->codec_properties, prop_new); */
/*     } */
/*     media_new->caps = gst_caps_copy(media_temp->caps); */
/*     projectsettings->media_settings = g_slist_append( projectsettings->media_settings, (gpointer) media_new ); */
/*   } */

  pitivi_projectsettings_print(projectsettings);

  return projectsettings;
}

/* 
   Creation d'un PitiviCategorieSettings 
*/
PitiviCategorieSettings *
pitivi_projectsettings_categorie_new(gchar *name/* , GSList *list_settings */)
{
  PitiviCategorieSettings	*categorie;
  PitiviProjectSettings		*setting_temp;
  GSList			*list;
  int				j;
  
  categorie = g_new0(PitiviCategorieSettings, 1);
  categorie->name = g_strdup(name);
  categorie->list_settings = NULL;

  return (categorie);
}

/* Creation d'un PitiviMediaSetting */
PitiviMediaSettings *
pitivi_projectsettings_media_new( gchar *codec_factory_name, GstCaps *caps, gint index )
{
  PitiviMediaSettings	*media_new;
  PitiviSettingsValue	*setting_value;
  GstElementFactory	*factory;
  GstElement		*element;
  GParamSpec		**property_specs;
  gboolean		readable;
  GList			*list;
  gint			num_properties;
  gint			i;

  g_print("MEDIA NEW, Index :%d\n", index);
  media_new = g_new0(PitiviMediaSettings, 1);
  media_new->codec_factory_name = g_strdup(codec_factory_name);
  media_new->combo_box_codec_index = index;
  media_new->codec_properties = NULL;

  media_new->caps = g_new0(GstCaps, 1);
  media_new->caps = gst_caps_copy(caps);

  /* Recuperation des proprietes*/
/*   factory = gst_element_factory_find( codec_factory_name ); */
/*   if (factory) */
/*     { */
/*       g_print("IF num 1\n"); */
/*       element = gst_element_factory_create(factory, media_new->codec_factory_name); */
/*       if (element) */
/* 	{ */
/* 	  g_print("IF num 2\n"); */
/* 	  property_specs = g_object_class_list_properties(G_OBJECT_GET_CLASS (element), &num_properties); */
/* 	  for (i = 0; i < num_properties; i++) */
/* 	    { */
/* 	      GParamSpec *param = property_specs[i]; */
	      
/* 	      readable = FALSE; */
/* 	      setting_value = g_new0( PitiviSettingsValue, 1); */
/* 	      g_value_init (&setting_value->value, param->value_type); */
	      
/* 	      if (param->flags & G_PARAM_READABLE) */
/* 		{ */
/* 		  g_object_get_property (G_OBJECT (element), param->name, &setting_value->value); */
/* 		  readable = TRUE; */
/* 		} */
/* 	      setting_value->name = g_strdup (g_param_spec_get_nick (param)); */
	  
	  
/*       for ( list = property; property; property = property->next ) */
/* 	{ */
/* 	  media_new->codec_properties = g_list_append(media_new->codec_properties, (gpointer) property); */
/* 	  g_print("Propertie Name : %s\n", ((PitiviSettingsValue *) media_new->codec_properties)->name ); */
/* 	} */
/*     } */
	  
	  /* Creation du caps par default pour le reglage */

/* 	} */
/*     } */
  return (media_new);
}

/* Creation de la liste des Reglages par default */
/* GSList * */
/* pitivi_projectsettings_list_make() */
/* { */
/*   GSList			*list_categories; */
/*   GSList			*list_reglage; */
/*   GSList			*list_media_settings; */
/*   PitiviMediaSettings		*media_setting; */
/*   GstCaps			*default_vcaps; */
/*   GstCaps			*default_acaps; */
  
/* Initialisation des caps par default */
/*   default_vcaps = pitivi_projectsettings_vcaps_create(720, 576, 25); */
/*   default_acaps = pitivi_projectsettings_acaps_create(48000, 1); */

/* /\* Initialisation du debut des liste *\/ */
/*   list_media_settings = NULL; */
/*   list_reglage = NULL; */
/*   list_categories = NULL; */

/* /\* Categorie 1 *\/ */
/*   list_media_settings = g_slist_append(list_media_settings, (gpointer) pitivi_projectsettings_media_new("rtjpegenc", default_vcaps, 0) ); */
/*   list_media_settings = g_slist_append(list_media_settings, (gpointer) pitivi_projectsettings_media_new("vorbisenc", default_acaps, 0) ); */
/*   list_reglage = g_slist_append(list_reglage, (gpointer) pitivi_projectsettings_new_with_name("Standard 32kHz", */
/* 											      "Description Standard 32kHz", */
/* 											      list_media_settings ) ); */
/*   list_reglage = g_slist_append(list_reglage, (gpointer) pitivi_projectsettings_new_with_name("Standard 48kHz", */
/* 											      "Description Standard 48kHz", */
/* 											      list_media_settings ) ); */
/*   list_reglage = g_slist_append(list_reglage, (gpointer) pitivi_projectsettings_new_with_name("Widescreen 32kHz", */
/* 											      "Description Widescreen 32kHz", */
/* 											      list_media_settings ) ); */
/*   list_reglage = g_slist_append(list_reglage, (gpointer) pitivi_projectsettings_new_with_name("Widescreen 48kHz", */
/* 											      "Description Widescreen 48kHz", */
/* 											      list_media_settings ) ); */
/*   list_categories = g_slist_append(list_categories, (gpointer) pitivi_projectsettings_categorie_new("DV - NTSC", list_reglage) ); */
  
/* /\* /*   list_categories = g_slist_append(list_categories, (gpointer) pitivi_projectsettings_categorie_new("DV - PAL", list_reglage) ); */
  
/* /\* Categorie 3 *\/ */
/*   list_media_settings = NULL; */
/*   list_media_settings = g_slist_append(list_media_settings, (gpointer) pitivi_projectsettings_media_new("rtjpegenc", default_vcaps, 0 ) ); */
/*   list_media_settings = g_slist_append(list_media_settings, (gpointer) pitivi_projectsettings_media_new("vorbisenc", default_acaps, 0 ) ); */
  
/*   list_reglage = NULL; */
/*   list_reglage = g_slist_append(list_reglage, (gpointer) pitivi_projectsettings_new_with_name("Multimedia Video", */
/* 											      "Description Multimedia Video", */
/* 											      list_media_settings) ); */
/*   list_reglage = g_slist_append(list_reglage, (gpointer) pitivi_projectsettings_new_with_name("Quicktime for Web", */
/* 											      "Description Quicktime for Web", */
/* 											      list_media_settings) ); */
/*   list_reglage = g_slist_append(list_reglage, (gpointer) pitivi_projectsettings_new_with_name("Petit test", */
/* 											      "Description Petit test", */
/* 											      list_media_settings) ); */
/*   list_categories = g_slist_append(list_categories, (gpointer) pitivi_projectsettings_categorie_new("Custom Settings", list_reglage) ); */
  
/* /\* Categorie 4 *\/ */
/*   list_reglage = NULL; */
/*   list_categories = g_slist_append(list_categories, (gpointer) pitivi_projectsettings_categorie_new("Personnal Settings", list_reglage) ); */
  
/*   return (list_categories); */
/* } */

/*
  pitivi_projectsettings_print
*/

void
pitivi_projectsettings_print(PitiviProjectSettings *self)
{
  GSList		*t1;
  GList			*t2;
  PitiviMediaSettings	*mset;
  PitiviSettingsValue	*cset;
  gchar			*tmp;
  
  g_printf("ProjectSettings Name[%s] Description[%s]\n", 
	   self->name, 
	   self->description);
  for (t1 = self->media_settings; t1; t1 = t1->next) {
    mset = (PitiviMediaSettings *) t1->data;
    if (mset) {
      g_printf(" Media Settings Index[%d] Factory[%s] Caps[%s]\n", 
	       mset->combo_box_codec_index, 
	       mset->codec_factory_name, 
	       gst_caps_to_string(mset->caps));
      
      for (t2 = mset->codec_properties; t2; t2 = t2->next) {
	cset = (PitiviSettingsValue *) t2->data;
	
	if (cset) {
	  tmp = g_strdup_value_contents(&(cset->value));
	  g_printf("  Codec Settings [%s]:[%s]\n", cset->name, tmp);
	  g_free(tmp);
	} else
	  g_printf("empty codec settings...\n");
      }
    } else
      g_printf("Empty media settings...\n");
  }
}

/*
  pitivi_projectsettings_save_thyself
  Enregistre les proprietes de self dans une structure XML fils de parent
  Renvoie la structure pere
*/
xmlNodePtr	
pitivi_projectsettings_save_thyself(PitiviProjectSettings *self, xmlNodePtr parent)
{
  xmlNodePtr		selfptr, msetptr, csetptr;
  GSList		*mset;
  GList			*cset;
  PitiviMediaSettings	*cat1;
  PitiviSettingsValue	*cat2;
  char			*tmpstr;

  selfptr = xmlNewChild (parent, NULL, "projectsettings", NULL);

  xmlNewChild (selfptr, NULL, "name", self->name);
  xmlNewChild (selfptr, NULL, "description", self->description);
  
  for (mset = self->media_settings; mset; mset = mset->next) {
    cat1 = (PitiviMediaSettings *) mset->data;

    msetptr = xmlNewChild(selfptr, NULL, "media_settings", NULL);

    xmlNewChild(msetptr, NULL, "codec_factory_name", cat1->codec_factory_name);
    xmlNewChild(msetptr, NULL, "caps", gst_caps_to_string(cat1->caps));
    csetptr = xmlNewChild(msetptr, NULL, "codec_properties", NULL);
    
    for (cset = cat1->codec_properties; cset; cset = cset->next) {
      cat2 = (PitiviSettingsValue *) cset->data;
      
      tmpstr = g_strdup_value_contents(&(cat2->value));

      xmlNewChild(csetptr, NULL, "name", cat2->name);
      xmlNewChild(csetptr, NULL, "value", tmpstr);
    }
  }

  return parent;
}

/*
  pitivi_ps_mediasettings_restore_thyself
  restores a PitiviMediaSettings from XML
*/
void
pitivi_ps_mediasettings_restore_thyself(PitiviMediaSettings *tofill, xmlNodePtr self) {
  xmlNodePtr	children;
  
  for (children = self->xmlChildrenNode; children; children = children->next) {
    if (!strcmp("caps", children->name))
      tofill->caps = gst_caps_from_string(xmlNodeGetContent(children));
    else if (!strcmp("codec_factory_name", children->name))
      tofill->codec_factory_name = xmlNodeGetContent(children);
    else if (!strcmp("codec_properties", children->name)) {
      g_warning("TODO : restore codec_properties from XML");
      /*
	TODO Finish codec_properties restoration from XML
      */
    }
  }
}

/*
  pitivi_projectsettings_restore_thyself
  Remplis l'objet tofill avec les donnes contenus dans self
*/
void
pitivi_projectsettings_restore_thyself(PitiviProjectSettings *tofill, xmlNodePtr self)
{
  xmlNodePtr children;
  PitiviMediaSettings	*mset;

  for (children = self->xmlChildrenNode; children; children = children->next) {
    if (!strcmp("name", children->name)) {
      tofill->name = xmlNodeGetContent(children);
    } else if (!strcmp("description", children->name)) {
      tofill->description = xmlNodeGetContent(children);
    } else if (!strcmp("media_settings", children->name)) {
      mset = g_new0(PitiviMediaSettings, 1);
      pitivi_ps_mediasettings_restore_thyself(mset, children);
      tofill->media_settings = g_slist_append(tofill->media_settings, mset);
    }
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
  GSList		*mset;
  GList			*cset;
  PitiviMediaSettings	*cat1, *cat2;
  PitiviSettingsValue	*val1, *val2;

  if (self == NULL)
    return NULL;

  pitivi_projectsettings_print(self);

  res = pitivi_projectsettings_new();
  res->name = g_strdup(self->name);
  res->description = g_strdup(self->description);
  res->media_settings = NULL;
  
  for (mset = self->media_settings; mset; mset = mset->next) {
    cat1 = (PitiviMediaSettings *) mset->data;
    cat2 = g_new0(PitiviMediaSettings, 1);
    
    cat2->codec_factory_name = g_strdup(cat1->codec_factory_name);
    cat2->codec_properties = NULL;

    for (cset = cat1->codec_properties; cset; cset = cset->next) {
      val1 = (PitiviSettingsValue *) cset->data;
      val2 = g_new0(PitiviSettingsValue, 1);
      
      val2->name = g_strdup(val1->name);
      g_value_init(&(val2->value), G_VALUE_TYPE(&(val1->value)));
      g_value_copy(&(val1->value), &(val2->value));
      
      cat2->codec_properties = g_list_append(cat2->codec_properties, val2);
    }

    cat2->caps = gst_caps_copy(cat1->caps);
    res->media_settings = g_slist_append(res->media_settings, cat2);
  }

  pitivi_projectsettings_print(res);

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
