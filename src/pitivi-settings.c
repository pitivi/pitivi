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



/*
 * A FAIRE : Dans dispose() g_free de la liste des elements 
 */



#include "pitivi.h"
#include "pitivi-settings.h"

static     GObjectClass *parent_class;


struct _PitiviSettingsPrivate
{
  /* instance private members */
  gboolean	dispose_has_run;
};

/*
 * forward definitions
 */








/*
 * Insert "added-value" functions here
 */



void		pitivi_settings_free_mime_type (PitiviSettingsMimeType *mime_type)
{
  g_free (mime_type->flux);
  g_list_free (mime_type->encoder);
  g_list_free (mime_type->decoder);
  g_free (mime_type);
  return ;
}


void		pitivi_settings_free_list_all (GList *list)
{
  GList		*tmp;

  for (tmp = list; list; list = list->next) {
    pitivi_settings_free_mime_type (list->data);
  }
  g_list_free (tmp);
  return ;
}


/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * */


/* 
   affiche les infos d un element
*/
void		pitivi_settings_aff_info_factory (GstElementFactory *factory)
{
  g_print ("%s\t%s\t%s\n", 
	   gst_plugin_feature_get_name (GST_PLUGIN_FEATURE(factory)),
	   gst_element_factory_get_longname (factory), 
	   gst_element_factory_get_klass (factory)
	   );
  return ;
}


/* 
   affiche la list des coder 
   (Encoder|Decoder)
*/
void		pitivi_settings_aff_coder (GList *list)
{
  for (; list; list = g_list_next (list)) {
    g_print ("    %s\n", (gchar *) list->data);
  }
  return ;
}


/* 
   affiche la structure d un flux
*/
void		pitivi_settings_aff_mime_type (PitiviSettingsMimeType *mime_type)
{
  g_print ("%s\n", mime_type->flux);
  g_print ("  Encoder:\n");
  pitivi_settings_aff_coder (mime_type->encoder);
  g_print ("  Decoder:\n");
  pitivi_settings_aff_coder (mime_type->decoder);
  return ;
}


/* 
   affiche le contenu de la list 
   (Container|Codec)
*/
void		pitivi_settings_aff_all_list (GList *list)
{
  for (; list; list = g_list_next (list)) {
    pitivi_settings_aff_mime_type ((PitiviSettingsMimeType *) list->data);
  }  
  return ;
}


/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * */


/* 
   initialise une nouvelle structure 
   pour un nouveau flux
*/
PitiviSettingsMimeType *
pitivi_settings_init_mime_type (gchar *flux)
{
  PitiviSettingsMimeType *new;

  new = g_malloc (sizeof (PitiviSettingsMimeType));
  new->flux = g_strdup (flux);
  new->encoder = 0;
  new->decoder = 0;
  return (new);
}


/* 
   retourne la structure assigne au flux
   si elle existe sinon retourne NULL
*/
PitiviSettingsMimeType *
pitivi_settings_search_flux (GList *list, gchar *flux)
{
  PitiviSettingsMimeType *tmp;
  
  for (; list; list = g_list_next (list)) {
    tmp = (PitiviSettingsMimeType *) list->data;
    if ((!strcmp(tmp->flux, flux))) {
      return (tmp);
    }
  }
  return (0);
}


/* 
   parcours la list 
   et retourne la list des coder demande
   (Encoder|Decoder) assigne au flux
   si le flux n existe pas retourne -1
   si la valeur de retour est NULL 
   c est que la list est vide
*/
GList *
pitivi_settings_get_flux_coder_list (GList *list, gchar *flux, gboolean LIST)
{
  PitiviSettingsMimeType *tmp;

  if ((tmp = pitivi_settings_search_flux (list, flux))) {
    if (LIST == DEC_LIST) {
      return (tmp->decoder);
    } else if (LIST == ENC_LIST) {
      return (tmp->encoder);
    } else {
      g_print ("Don't know this list\n");
    }
  }
  return (NULL);
}


/* 
   ajoute un l element factory name
   dans la list (encoder|decoder) 
   assignee au flux tmp->flux
   suivant son pad  (src|sink) 
*/
PitiviSettingsMimeType *
pitivi_settings_ajout_factory_element (PitiviSettingsMimeType *tmp, 
		       gchar *element, gboolean MY_PAD)
{

  if (MY_PAD == GST_PAD_SRC) {
    tmp->encoder = g_list_append (tmp->encoder, (gpointer) element);
  } else if (MY_PAD == GST_PAD_SINK) {
    tmp->decoder = g_list_append (tmp->decoder, (gpointer) element);
  } else {
    g_print ("ERROR in (ajout_factory_element) : MY_PAD \n");
  }

  return (tmp);
}


/* 
   recupere les flux gerer par l element
   si le flux existe dans la list
   ajoute un l element dans la structure de flux
   sinon cree la struct du flux et lui assigne l element
   
*/
GList *
pitivi_settings_ajout_element (GList *list, GstElementFactory *factory, gboolean MY_PAD)
{
  GstPadTemplate *padtemplate;

  if (factory->numpadtemplates) {
    gint i;
    const GList *pads;
    
    pads = factory->padtemplates;
    for (i = 0; pads; i++, pads = g_list_next (pads)) {
      padtemplate = (GstPadTemplate *) (pads->data);
      if (padtemplate->direction == MY_PAD) {
	gint j;
	
	for (j = 0; j < padtemplate->caps->structs->len; j++) {
	  PitiviSettingsMimeType *tmp;
	  
	  /* CHERCHE SI LE TYPE EST DEJA DEFINI */
	  if ((tmp = pitivi_settings_search_flux (list, gst_structure_to_string (gst_caps_get_structure (padtemplate->caps, j)))) &&
	      (padtemplate->caps != NULL))
	    {
	      tmp = pitivi_settings_ajout_factory_element (tmp, 
							   (gchar *) gst_plugin_feature_get_name (GST_PLUGIN_FEATURE(factory)), 
							   MY_PAD);
	    } 
	  else 
	    {
	      /* SINON L AJOUTE */
	      if (padtemplate->caps != NULL)
		{
		  tmp = pitivi_settings_init_mime_type (gst_structure_to_string (gst_caps_get_structure (padtemplate->caps, j)));
		  tmp = pitivi_settings_ajout_factory_element (tmp, 
							       (gchar *) gst_plugin_feature_get_name (GST_PLUGIN_FEATURE(factory)), 
							       MY_PAD);
		  list = g_list_append (list, (gpointer) tmp);
		}
	  }
	}
      }      
    }
  }
  return (list);
}

/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * */


GList			*pitivi_settings_get_flux_codec_list (GObject *object, gchar *flux, gboolean LIST)
{
  PitiviSettings *self = (PitiviSettings *) object;

  return (pitivi_settings_get_flux_coder_list (self->codec, flux, LIST));
}


GList			*pitivi_settings_get_flux_container_list (GObject *object, gchar *flux, gboolean LIST)
{
  PitiviSettings *self = (PitiviSettings *) object;

  return (pitivi_settings_get_flux_coder_list (self->container, flux, LIST));
}

/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * */

PitiviSettings *
pitivi_settings_new(void)
{
  PitiviSettings	*settings;

  settings = (PitiviSettings *) g_object_new(PITIVI_SETTINGS_TYPE, NULL);
  g_assert(settings != NULL);
  return settings;
}

static GObject *
pitivi_settings_constructor (GType type,
			     guint n_construct_properties,
			     GObjectConstructParam * construct_properties)
{
  GObject *obj;
  /* Invoke parent constructor. */
  obj = parent_class->constructor (type, n_construct_properties,
				   construct_properties);

  /* do stuff. */

  return obj;
}

static void
pitivi_settings_instance_init (GTypeInstance * instance, gpointer g_class)
{
  GList			*sv;
  GstElementFactory	*factory;
  PitiviSettings *self = (PitiviSettings *) instance;

  self->private = g_new0(PitiviSettingsPrivate, 1);
  
  /* initialize all public and private members to reasonable default values. */ 
  
  self->private->dispose_has_run = FALSE;
  
  /* Do only initialisation here */
  /* The construction of the object should be done in the Constructor
     So that properties set at instanciation can be set */

  self->codec = 0;
  self->container = 0;
  self->element = 0;

  self->element = gst_registry_pool_feature_list (GST_TYPE_ELEMENT_FACTORY);
  sv = self->element;
  while (sv) {
    factory = (GstElementFactory *) sv->data;
    if (!strncmp (gst_element_factory_get_klass (factory), "Codec/Demuxer", 13)) {
      self->container = pitivi_settings_ajout_element (self->container, factory, GST_PAD_SINK);
    } else if (!strncmp (gst_element_factory_get_klass (factory), "Codec/Muxer", 11)) {
      self->container = pitivi_settings_ajout_element (self->container, factory, GST_PAD_SRC);
    } else if (!strncmp (gst_element_factory_get_klass (factory), "Codec/Encoder/Audio", 19) || 
	       !strncmp (gst_element_factory_get_klass (factory), "Codec/Audio/Encoder", 19) ||
	       !strncmp (gst_element_factory_get_klass (factory), "Codec/Video/Encoder", 19) ||
	       !strncmp (gst_element_factory_get_klass (factory), "Codec/Encoder/Video", 19)
	       ) {
      self->codec = pitivi_settings_ajout_element (self->codec, factory, GST_PAD_SRC);
    } else if (!strncmp (gst_element_factory_get_klass (factory), "Codec/Audio/Decoder", 19) ||
	       !strncmp (gst_element_factory_get_klass (factory), "Codec/Decoder/Audio", 19) ||
	       !strncmp (gst_element_factory_get_klass (factory), "Codec/Decoder/Video", 19) ||
	       !strncmp (gst_element_factory_get_klass (factory), "Codec/Video/Decoder", 19)
	       ) {
      self->codec = pitivi_settings_ajout_element (self->codec, factory, GST_PAD_SINK);      
    }
    sv = sv->next;
  }

/*   pitivi_settings_aff_all_list (self->codec); */
/*   pitivi_settings_aff_all_list (self->container); */

}

static void
pitivi_settings_dispose (GObject *object)
{
  PitiviSettings	*self = PITIVI_SETTINGS(object);

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

  pitivi_settings_free_list_all (self->codec);
  pitivi_settings_free_list_all (self->container);

  /*
  g_list_free (self->element);
  */

  G_OBJECT_CLASS (parent_class)->dispose (object);
}

static void
pitivi_settings_finalize (GObject *object)
{
  PitiviSettings	*self = PITIVI_SETTINGS(object);

  /* 
   * Here, complete object destruction. 
   * You might not need to do much... 
   */

  g_free (self->private);
  G_OBJECT_CLASS (parent_class)->finalize (object);
}

static void
pitivi_settings_set_property (GObject * object,
			      guint property_id,
			      const GValue * value, GParamSpec * pspec)
{
  PitiviSettings *self = (PitiviSettings *) object;

  switch (property_id)
    {
      /*   case PITIVI_SETTINGS_PROPERTY: { */
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
pitivi_settings_get_property (GObject * object,
			      guint property_id,
			      GValue * value, GParamSpec * pspec)
{
  PitiviSettings *self = (PitiviSettings *) object;

  switch (property_id)
    {
      /*  case PITIVI_SETTINGS_PROPERTY: { */
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
pitivi_settings_class_init (gpointer g_class, gpointer g_class_data)
{
  GObjectClass *gobject_class = G_OBJECT_CLASS (g_class);
  PitiviSettingsClass *klass = PITIVI_SETTINGS_CLASS (g_class);

  parent_class = G_OBJECT_CLASS (g_type_class_peek_parent (g_class));

  gobject_class->constructor = pitivi_settings_constructor;
  gobject_class->dispose = pitivi_settings_dispose;
  gobject_class->finalize = pitivi_settings_finalize;

  gobject_class->set_property = pitivi_settings_set_property;
  gobject_class->get_property = pitivi_settings_get_property;

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
pitivi_settings_get_type (void)
{
  static GType type = 0;
 
  if (type == 0)
    {
      static const GTypeInfo info = {
	sizeof (PitiviSettingsClass),
	NULL,			/* base_init */
	NULL,			/* base_finalize */
	pitivi_settings_class_init,	/* class_init */
	NULL,			/* class_finalize */
	NULL,			/* class_data */
	sizeof (PitiviSettings),
	0,			/* n_preallocs */
	pitivi_settings_instance_init	/* instance_init */
      };
      type = g_type_register_static (G_TYPE_OBJECT,
				     "PitiviSettingsType", &info, 0);
    }

  return type;
}

/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * */


