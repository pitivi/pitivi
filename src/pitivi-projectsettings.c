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

#include <glib/gprintf.h>
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
			     "framerate", G_TYPE_DOUBLE, (double) framerate,
			     NULL );
  return (caps);
}


/**************/
GstCaps *
pitivi_projectsettings_acaps_create (int rate, int channels, int depth)
{
  GstCaps	*caps;
  
  caps = gst_caps_new_simple(
			     "audio/x-raw-int",
			     "rate",  G_TYPE_INT, rate,
			     "channels", G_TYPE_INT, channels,
			     "depth", G_TYPE_INT, depth,
			     NULL );
  return (caps);
}

gboolean
pitivi_projectsettings_get_videosize (PitiviProjectSettings *ps, gint *width, gint *height)
{
  PitiviMediaSettings	*ms;

  ms = ps->media_settings->data;

  if (width)
    if (!(gst_structure_get_int(gst_caps_get_structure(ms->caps, 0), "width", width)))
      return FALSE;

  if (height)
    if (!(gst_structure_get_int(gst_caps_get_structure(ms->caps, 0), "height", width)))
      return FALSE;
  return TRUE;
}

gdouble
pitivi_projectsettings_get_videorate(PitiviProjectSettings *ps)
{
  gdouble	res;
  PitiviMediaSettings	*ms;
  
  ms = ps->media_settings->data;

  if (gst_structure_get_double(gst_caps_get_structure(ms->caps, 0), "framerate", &res))
    return res;
  return 0;
}

int
pitivi_projectsettings_get_audiodepth(PitiviProjectSettings *ps)
{
  int	res;
  GSList	*tmp;
  PitiviMediaSettings	*ms;
  
  tmp = g_slist_nth(ps->media_settings, 1);
  ms = tmp->data;

  if (gst_structure_get_int(gst_caps_get_structure(ms->caps, 0), "depth", &res))
    return res;
  return 0;
}

int
pitivi_projectsettings_get_audiorate(PitiviProjectSettings *ps)
{
  int	res;
  GSList	*tmp;
  PitiviMediaSettings	*ms;
  
  tmp = g_slist_nth(ps->media_settings, 1);
  ms = tmp->data;

  if (gst_structure_get_int(gst_caps_get_structure(ms->caps, 0), "rate", &res))
    return res;
  return 0;
}

/**************/
PitiviProjectSettings *
pitivi_projectsettings_new_with_name(gchar *name, gchar *desc)
{
  PitiviProjectSettings	*projectsettings;

  projectsettings = g_new0(PitiviProjectSettings, 1);
  projectsettings->name = g_strdup(name);
  projectsettings->description = g_strdup(desc);
  projectsettings->media_settings = NULL;

  return projectsettings;
}

/* 
   Creation d'un PitiviCategorieSettings 
*/
PitiviCategorieSettings *
pitivi_projectsettings_categorie_new(gchar *name)
{
  PitiviCategorieSettings	*categorie;
  
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

  media_new = g_new0(PitiviMediaSettings, 1);
  media_new->codec_factory_name = g_strdup(codec_factory_name);
/*   media_new->combo_box_codec_index = index; */
  media_new->codec_properties = NULL;

  media_new->caps = g_new0(GstCaps, 1);
  media_new->caps = gst_caps_copy(caps);

  return (media_new);
}


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
  
  g_printf("ProjectSettings Name[%s] Description[%s] Container[%s]\n", 
	   self->name, 
	   self->description,
	   self->container_factory_name);
  for (t1 = self->media_settings; t1; t1 = t1->next) {
    mset = (PitiviMediaSettings *) t1->data;
    if (mset) {
      g_printf(" Media Settings Factory[%s] Caps[%s]\n", 
	       /* mset->combo_box_codec_index,  */
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
  xmlNodePtr		selfptr, msetptr, csetptr, containerptr;
  GSList		*mset;
  GList			*cset;
  PitiviMediaSettings	*cat1;
  PitiviSettingsValue	*cat2;
  char			*tmpstr;

  selfptr = xmlNewChild (parent, NULL, "projectsettings", NULL);

  xmlNewChild (selfptr, NULL, "name", self->name);
  xmlNewChild (selfptr, NULL, "description", self->description);
  if (self->container_factory_name) {
    xmlNewChild (selfptr, NULL, "container_factory", self->container_factory_name);
    
    if (self->container_properties) {
      containerptr = xmlNewChild (selfptr, NULL, "container_properties", NULL);
      for (cset = self->container_properties; cset; cset = cset->next) {
	cat2 = (PitiviSettingsValue *) cset->data;
	
	tmpstr = g_strdup_value_contents(&(cat2->value));
	xmlNewChild(containerptr, NULL, "name", cat2->name);
	xmlNewChild(containerptr, NULL, "value", tmpstr);
      }
    }
  }

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
    if (!g_ascii_strcasecmp("caps", children->name))
      tofill->caps = gst_caps_from_string(xmlNodeGetContent(children));
    else if (!g_ascii_strcasecmp("codec_factory_name", children->name))
      tofill->codec_factory_name = xmlNodeGetContent(children);
/*     else if (!g_ascii_strcasecmp("codec_properties", children->name)) { */
/*       g_warning("TODO : restore codec_properties from XML"); */
/*       /\* */

/* 	TODO Finish codec_properties restoration from XML */

/*       *\/ */
/*     } */
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
    if (!g_ascii_strcasecmp("name", children->name)) {
      tofill->name = xmlNodeGetContent(children);
    } else if (!g_ascii_strcasecmp("description", children->name)) {
      tofill->description = xmlNodeGetContent(children);
    } else if (!g_ascii_strcasecmp("container_factory", children->name)){
      tofill->container_factory_name = xmlNodeGetContent(children);
    } else if (!g_ascii_strcasecmp("container_properties", children->name)){
      /*g_warning("TODO : restore container codec_properties from XML");*/
    } else if (!g_ascii_strcasecmp("media_settings", children->name)) {
      mset = g_new0(PitiviMediaSettings, 1);
      pitivi_ps_mediasettings_restore_thyself(mset, children);
      tofill->media_settings = g_slist_append(tofill->media_settings, mset);
    }
  }
}

GList *
pitivi_settingsvalue_list_copy (GList *orig)
{
  GList	*res = NULL;
  GList	*tmp;
  PitiviSettingsValue *val1, *val2;
  
  for (tmp = orig; tmp; tmp = tmp->next) {
    val1 = (PitiviSettingsValue *) tmp->data;
    val2 = g_new0(PitiviSettingsValue, 1);
    
    val2->name = g_strdup(val1->name);
    g_value_init(&(val2->value), G_VALUE_TYPE(&(val1->value)));
    g_value_copy(&(val1->value), &(val2->value));
    res = g_list_append (res, val2);
  }
  return res;
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
  PitiviMediaSettings	*cat1, *cat2;

  if (self == NULL)
    return NULL;

/*   pitivi_projectsettings_print(self); */

  res = pitivi_projectsettings_new();
  res->name = g_strdup(self->name);
  res->description = g_strdup(self->description);
  res->container_factory_name = g_strdup (self->container_factory_name);
  res->container_properties = pitivi_settingsvalue_list_copy (self->container_properties);
  
  res->media_settings = NULL;
  
  for (mset = self->media_settings; mset; mset = mset->next) {
    cat1 = (PitiviMediaSettings *) mset->data;
    cat2 = g_new0(PitiviMediaSettings, 1);
    
    cat2->codec_factory_name = g_strdup(cat1->codec_factory_name);
    cat2->codec_properties = pitivi_settingsvalue_list_copy (cat1->codec_properties);
    cat2->caps = gst_caps_copy(cat1->caps);
    res->media_settings = g_slist_append(res->media_settings, cat2);
  }

/*   pitivi_projectsettings_print(res); */

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
pitivi_projectsettings_class_init (gpointer g_class, gpointer g_class_data)
{
  GObjectClass *gobject_class = G_OBJECT_CLASS (g_class);
/*   PitiviProjectSettingsClass *klass = PITIVI_PROJECTSETTINGS_CLASS (g_class); */

  gobject_class->constructor = pitivi_projectsettings_constructor;
  gobject_class->dispose = pitivi_projectsettings_dispose;
  gobject_class->finalize = pitivi_projectsettings_finalize;
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
