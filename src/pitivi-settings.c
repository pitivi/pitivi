/* 
 * PiTiVi
 * Copyright (C) <2004> Edward G. Hervey <hervey_e@epita.fr>
 *			Delettrez Marc <delett_m@epita.fr>
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
  g_print ("%s\n", gst_caps_to_string (mime_type->flux));
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
0*/
PitiviSettingsMimeType *
pitivi_settings_init_mime_type (GstCaps *flux)
{
  PitiviSettingsMimeType *new;

  new = g_malloc (sizeof (PitiviSettingsMimeType));
  new->flux = gst_caps_copy (flux);
  new->encoder = NULL;
  new->decoder = NULL;
  return (new);
}


/* 
   retourne la structure assigne au flux
   si elle existe sinon retourne NULL
*/
PitiviSettingsMimeType *
pitivi_settings_search_flux (GList *list, GstCaps *flux)
{
  PitiviSettingsMimeType *tmp;
  
  for (; list; list = g_list_next (list)) {
    tmp = (PitiviSettingsMimeType *) list->data;
    if (gst_caps_is_equal (tmp->flux, flux)) {
      return (tmp);
    }
  }
  return (NULL);
}

PitiviSettingsMimeType *
pitivi_settings_search_compatible_flux (GList *list, GstCaps *flux)
{
  PitiviSettingsMimeType *tmp;

  for (; list; list = g_list_next (list)) {
    tmp = (PitiviSettingsMimeType *) list->data;
    if (gst_caps_is_always_compatible (flux, tmp->flux)) {
      return (tmp);
    }
  }
  return (NULL);
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
pitivi_settings_get_flux_coder_list (GList *list, GstCaps *flux, gboolean LIST)
{
  PitiviSettingsMimeType *tmp;

  if ((tmp = pitivi_settings_search_compatible_flux (list, flux))) {
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

gboolean
my_list_find(gchar *txt, GList *list)
{
  while (list) {
    if ((list->data) && (!strcmp(txt, (gchar *) list->data)))
      return TRUE;
    list = list->next;
  }
  return FALSE;
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
    if (!my_list_find(element, tmp->encoder))
      tmp->encoder = g_list_append (tmp->encoder, (gpointer) element);
  } else if (MY_PAD == GST_PAD_SINK) {
    if (!my_list_find(element, tmp->decoder))
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
	GstCaps *tmp_caps;

	tmp_caps = (GstCaps *) padtemplate->caps;
	PitiviSettingsMimeType *tmp_mime;
	
	if (!gst_caps_is_any (tmp_caps)) {
	  if ((tmp_mime = pitivi_settings_search_flux (list, tmp_caps))) {
	    tmp_mime = pitivi_settings_ajout_factory_element (tmp_mime, 
							      (gchar *) gst_plugin_feature_get_name (GST_PLUGIN_FEATURE(factory)), 
							      MY_PAD);
	    
	  } else {
	    tmp_mime = pitivi_settings_init_mime_type (tmp_caps);
	    tmp_mime = pitivi_settings_ajout_factory_element (tmp_mime, 
							      (gchar *) gst_plugin_feature_get_name (GST_PLUGIN_FEATURE(factory)), 
							      MY_PAD);
	    list = g_list_append (list, (gpointer) tmp_mime);
	    
	  }
	}
	/*
	  for (j = 0; j < padtemplate->caps->structs->len; j++) {
	  PitiviSettingsMimeType *tmp;
	  
	  
	  if ((tmp = pitivi_settings_search_flux (list, gst_structure_to_string (gst_caps_get_structure (padtemplate->caps, j))))) {
	  tmp = pitivi_settings_ajout_factory_element (tmp, 
	  (gchar *) gst_plugin_feature_get_name (GST_PLUGIN_FEATURE(factory)), 
	  MY_PAD);
	  } else {
	  
	  tmp = pitivi_settings_init_mime_type (gst_structure_to_string (gst_caps_get_structure (padtemplate->caps, j)));
	  tmp = pitivi_settings_ajout_factory_element (tmp, 
	  (gchar *) gst_plugin_feature_get_name (GST_PLUGIN_FEATURE(factory)), 
	  MY_PAD);
	  list = g_list_append (list, (gpointer) tmp);
	  }
	  }
	*/
	
      }      
    }
  }
  return (list);
}

/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * */


GList *
pitivi_settings_get_flux_codec_list (GObject *object, GstCaps *flux, gboolean LIST)
{
  PitiviSettings *self = (PitiviSettings *) object;

  return (pitivi_settings_get_flux_coder_list (self->codec, flux, LIST));
}


GList *
pitivi_settings_get_flux_container_list (GObject *object, GstCaps *flux, gboolean LIST)
{
  PitiviSettings *self = (PitiviSettings *) object;

  return (pitivi_settings_get_flux_coder_list (self->container, flux, LIST));
}


GList *
pitivi_settings_get_flux_parser_list (GObject *object, GstCaps *flux, gboolean LIST)
{
  PitiviSettings *self = (PitiviSettings *) object;

  return (pitivi_settings_get_flux_coder_list (self->parser, flux, LIST));
}

/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * */

/*
  pitivi_settings_scan_registry

  Scan the GstRegistry and fills the PitiviSettings with the list of 
  (De)Coder, (De)Muxer and Parser
*/

void
pitivi_settings_scan_registry(PitiviSettings *self)
{
  GList			*sv;
  GstElementFactory	*factory;

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
    } else if (!strncmp (gst_element_factory_get_klass (factory), "Codec/Parser", 12) ||
	       !strncmp (gst_element_factory_get_klass (factory), "Codec/Parser/Audio", 18) ||
	       !strncmp (gst_element_factory_get_klass (factory), "Codec/Parser/Video", 18)
	       ) {
      self->parser = pitivi_settings_ajout_element (self->parser, factory, GST_PAD_SINK);      
    }
    sv = sv->next;
  }

  //pitivi_settings_aff_all_list (self->container);
  //pitivi_settings_aff_all_list (self->codec);
  //pitivi_settings_aff_all_list (self->parser);
}

GList *
pitivi_settings_get_xml_list(xmlNodePtr self)
{
  PitiviSettingsMimeType	*tmp;
  GList				*res;
  xmlNodePtr			child, children;
  
  for (res = NULL, child = self->xmlChildrenNode; child; child = child->next)
    if (!strcmp(child->name, "settingsmimetype")) {
      tmp = g_new0(PitiviSettingsMimeType, 1);
      for (children = child->xmlChildrenNode; children; children = children->next) {
	if (!strcmp(children->name, "caps"))
	  tmp->flux = gst_caps_from_string(xmlNodeGetContent(children));
	else if (!strcmp(children->name, "encoder")) {
	  tmp->encoder = NULL;
	  tmp->encoder = g_list_append(tmp->encoder, xmlNodeGetContent(children));
	} else if (!strcmp(children->name, "decoder")) {
	  tmp->decoder = NULL;
	  tmp->decoder = g_list_append(tmp->decoder, xmlNodeGetContent(children));
	}
      }
      res = g_list_append(res, tmp);
    }
  return res;
}

void
pitivi_settings_restore_thyself(PitiviSettings *settings, xmlNodePtr self)
{
  xmlNodePtr	child;
  

  for (child = self->xmlChildrenNode; child; child = child->next) {
    if (!strcmp(child->name, "container")) {
      settings->container = pitivi_settings_get_xml_list(child);
    } else if (!strcmp(child->name, "codec")) {
      settings->codec = pitivi_settings_get_xml_list(child);
    } else if (!strcmp(child->name, "parser")) {
      settings->parser = pitivi_settings_get_xml_list(child);
    }
  }
}

/*
  pitivi_settings_xml_epure_list

  Returns a xml formatted list with only the first elements of multiple lists
*/

void
pitivi_settings_xml_epure_list(GList *list, xmlNodePtr parent)
{
  GList	*res = NULL;
  xmlNodePtr	mime;
  PitiviSettingsMimeType	*tmp, *toadd;

  for (; list; list = list->next) {
    tmp = (PitiviSettingsMimeType *) list->data;
    if ((g_list_length(tmp->encoder) > 1) 
	|| (g_list_length(tmp->decoder) > 1)){
      /* Need to add one */
      mime = xmlNewChild(parent, NULL, "settingsmimetype", NULL);
      xmlNewChild (mime, NULL, "caps", gst_caps_to_string(tmp->flux));

      if (g_list_length(tmp->encoder) > 1)
	xmlNewChild (mime, NULL, "encoder", (char *) tmp->encoder->data);

      if (g_list_length(tmp->decoder) > 1)
	xmlNewChild (mime, NULL, "decoder", (char *) tmp->decoder->data);
    }
  }
}

xmlDocPtr
pitivi_settings_save_thyself(PitiviSettings *settings)
{
  xmlDocPtr doc;
  xmlNodePtr projectnode;
  xmlNodePtr container, codecs, parser;
  xmlNsPtr ns;

  doc = xmlNewDoc ("1.0");

  doc->xmlRootNode = xmlNewDocNode (doc, NULL, "pitivi", NULL);

  ns = xmlNewNs (doc->xmlRootNode, "http://pitivi.org/pitivi-core/0.1/", "pitivi");

  projectnode = xmlNewChild (doc->xmlRootNode, ns, "settings", NULL);

  container = xmlNewChild (projectnode, ns, "container", NULL);
  pitivi_settings_xml_epure_list (settings->container, container);

  codecs = xmlNewChild (projectnode, ns, "codec", NULL);
  pitivi_settings_xml_epure_list (settings->codec, codecs);
  
  parser = xmlNewChild (projectnode, ns, "parser", NULL);
  pitivi_settings_xml_epure_list (settings->parser, parser);
  
  return doc;    
}

/*
  pitivi_settings_load_from_file

  Creates a PitiviSettings from the settings contained in filename

  Returns the created PitiviSettings or NULL if there was a problem
*/

PitiviSettings *
pitivi_settings_load_from_file(const gchar *filename)
{
  xmlDocPtr	doc;
  xmlNodePtr	field, cur, child;
  xmlNsPtr	ns;
  PitiviSettings	*settings = NULL;

  if (filename == NULL)
    return NULL;

  doc = xmlParseFile (filename);

  if (!doc)
    return NULL;

  cur = xmlDocGetRootElement (doc);
  if (cur == NULL)
    return NULL;

  ns = xmlSearchNsByHref (doc, cur, "http://pitivi.org/pitivi-core/0.1/");
  if (ns == NULL)
    return NULL;

  if (strcmp (cur->name, "pitivi"))
    return NULL;

  /* Actually extract the contents */

  for (field = cur->xmlChildrenNode; field; field = field->next)
    if (!strcmp (field->name, "settings") && (field->ns == ns)) {
      /* found the PitiviSettings */
      settings = (PitiviSettings *) g_object_new (PITIVI_SETTINGS_TYPE, NULL);
      pitivi_settings_restore_thyself(settings, field);
      continue;
    }
  pitivi_settings_aff_all_list (settings->container);
  pitivi_settings_aff_all_list (settings->codec);
  pitivi_settings_aff_all_list (settings->parser);

  if (settings)
    pitivi_settings_scan_registry(settings);  
  
  return settings;
}

/*
  pitivi_settings_save_to_file

  Saves the PitiviSettings settings to the given file

  Returns TRUE if the settings were save to the file, FALSE otherwise
*/

gboolean
pitivi_settings_save_to_file(PitiviSettings *settings, const gchar *filename)
{
  xmlDocPtr		cur;
  xmlOutputBufferPtr	buf;
  const char		*encoding;
  xmlCharEncodingHandlerPtr handler = NULL;
  int			indent;
  gboolean		ret;
  FILE			*out;

  cur = pitivi_settings_save_thyself (settings);
  if (!cur)
    return FALSE;

  /* open the file */
  out = fopen(filename, "w+");
  if (out == NULL)
    return FALSE;

  encoding = (const char *) cur->encoding;

  if (encoding != NULL) {
    xmlCharEncoding enc;

    enc = xmlParseCharEncoding (encoding);

    if (cur->charset != XML_CHAR_ENCODING_UTF8) {
      xmlGenericError (xmlGenericErrorContext,
		       "xmlDocDump: document not in UTF8\n");
      return FALSE;
    }
    if (enc != XML_CHAR_ENCODING_UTF8) {
      handler = xmlFindCharEncodingHandler (encoding);
      if (handler == NULL) {
        xmlFree ((char *) cur->encoding);
        cur->encoding = NULL;
      }
    }
  }

  buf = xmlOutputBufferCreateFile (out, handler);

  indent = xmlIndentTreeOutput;
  xmlIndentTreeOutput = 1;
  ret = xmlSaveFormatFileTo (buf, cur, NULL, 1);
  xmlIndentTreeOutput = indent;

  /* close the file */
  fclose(out);

  return TRUE;
}

/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * */

PitiviSettings *
pitivi_settings_new(void)
{
  PitiviSettings	*settings;

  settings = (PitiviSettings *) g_object_new(PITIVI_SETTINGS_TYPE, NULL);
  pitivi_settings_scan_registry(settings);
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
  PitiviSettings *self = (PitiviSettings *) instance;

  self->private = g_new0(PitiviSettingsPrivate, 1);
  
  /* initialize all public and private members to reasonable default values. */ 
  
  self->private->dispose_has_run = FALSE;
  
  /* Do only initialisation here */
  /* The construction of the object should be done in the Constructor
     So that properties set at instanciation can be set */

  self->codec = NULL;
  self->container = NULL;
  self->parser = NULL;
  self->element = NULL;

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


