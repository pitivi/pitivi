/* 
 * PiTiVi
 * Copyright (C) <2004> Edward G. Hervey <hervey_e@epita.fr>
 *                      
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

#include <gnl/gnlsource.h>
#include <gnl/gnlcomposition.h>
#include "pitivi.h"
#include "pitivi-debug.h"
#include "pitivi-project.h"

struct _PitiviProjectPrivate
{
  /* instance private members */
  gboolean dispose_has_run;

  GnlTimeline	*timeline;
  GstElement	*thread;
};

enum {
  ARG_0,
  ARG_PROJECTSETTINGS,
  ARG_FILENAME
};

/*
 * forward definitions
 */

/*
 * Insert "added-value" functions here
 */


/**
 * pitivi_project_new: 
 * @PitiviProjectSettings: The object containing the project's settings 
 *
 * Create an object for the new project
 *
 * Returns: The PitiviProject
 */

PitiviProject *
pitivi_project_new (PitiviProjectSettings *settings)
{
  PitiviProject *project;

  project = (PitiviProject *) g_object_new (PITIVI_PROJECT_TYPE, 
					    "projectsettings", settings,
					    NULL);
  g_assert (project != NULL);

  return project;
}

/**
 * pitivi_project_from_file: 
 * @const gchar: The filename of the file to be loaded  
 *
 * Loads a PitiviProject from the given file filename
 *
 * Returns: The loaded PitiviProject, or NULL if there's a problem
 */

PitiviProject *
pitivi_project_new_from_file (const gchar *filename)
{
  PitiviProject *project = NULL;

  if (filename == NULL)
    return NULL;

  project = (PitiviProject *) g_object_new (PITIVI_PROJECT_TYPE,
					    "filename", filename,
					    NULL);
  g_assert (project != NULL);
  if (!project->bin) {
    g_object_unref (G_OBJECT (project));
    return NULL;
  }

  return project;
}

gboolean
pitivi_project_seek (PitiviProject *project, GstClockTime seekvalue)
{
  GstElementState	pstate;
  gboolean		res = TRUE;
  
  if (GST_CLOCK_TIME_IS_VALID (seekvalue)) {
    
    /* PAUSE timeline bin if necessary */
    PITIVI_INFO ("Pausing elements");
    pstate = gst_element_get_state (GST_ELEMENT (project->bin));
    if (pstate == GST_STATE_PLAYING)
      gst_element_set_state (GST_ELEMENT (project->bin), GST_STATE_PAUSED);
    
    PITIVI_INFO ("Seeking to %" GST_TIME_FORMAT " in project thread",
		 GST_TIME_ARGS (seekvalue));
    res = gst_element_send_event (GST_ELEMENT (project->bin), 
				  gst_event_new_seek(GST_FORMAT_TIME | GST_SEEK_METHOD_SET | GST_SEEK_FLAG_FLUSH , 
						     seekvalue));
    PITIVI_INFO ("Seek finished");
    if (!gst_element_set_state (GST_ELEMENT (project->bin), GST_STATE_PLAYING))
      PITIVI_WARNING ("Couldn't set bin to playing !!!");
    
    /* UN-PAUSE timeline bin if necessary */
    PITIVI_INFO ("Un-pausing elements");
    if (pstate == GST_STATE_PLAYING)
      gst_element_set_state (GST_ELEMENT (project->bin), pstate);
    
  }
  return res;
}

static PitiviProject *
pitivi_project_internal_restore_file (PitiviProject *project)
{
  xmlDocPtr doc;
  xmlNodePtr field, cur;
  xmlNsPtr ns;

  doc = xmlParseFile (project->filename);

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
    if (!strcmp (field->name, "project") && (field->ns == ns)) {
      /* found the PitiviProject */
/*       project = (PitiviProject *) g_object_new (PITIVI_PROJECT_TYPE, NULL); */
      pitivi_project_restore_thyself(project, field);
      continue;
    }
  return project;
}

/**
 * pitivi_project_restore_thyself: 
 * @PitiviProject: A PitiviProject
 * @xmlNodePtr: A pointer on the xml file associated with the PitiviProject
 *
 * Restore the other properties of the PitiviProject
 *
 * Returns: Void
 */

void
pitivi_project_restore_thyself(PitiviProject *project, xmlNodePtr self)
{
  xmlNodePtr	child;
  PitiviProjectSettings	*settings;
/*   PitiviProjectSourceList *sourcelist; */

  for (child = self->xmlChildrenNode; child; child = child->next) {
    if (!strcmp(child->name, "projectsettings")) {
      settings = (PitiviProjectSettings *) g_object_new (PITIVI_PROJECTSETTINGS_TYPE, NULL);
      pitivi_projectsettings_restore_thyself(settings, child);
      project->settings = settings;
      project->bin = pitivi_timelinebin_new (project->timeline,
					     project->audiogroup,
					     project->videogroup,
					     project->settings);
    }
    if (!strcmp(child->name, "projectsourcelist")) {
/*       sourcelist = (PitiviProjectSourceList *) g_object_new( PITIVI_PROJECTSOURCELIST_TYPE, NULL); */
      pitivi_projectsourcelist_restore_thyself(project->sources, child);
/*       project->sources = sourcelist; */
    }
  }
}

/**
 * pitivi_project_save_thyself: 
 * @PitiviProject: A PitiviProject
 *
 * Save the current project in a XMLDocument format
 *
 * Returns: Returns a pointer xmlDocPtr to the XMLDocument filled with the contents of the PitiviProject
 */

xmlDocPtr
pitivi_project_save_thyself(PitiviProject *project)
{
  xmlDocPtr doc;
  xmlNodePtr projectnode;
  xmlNsPtr ns;

  doc = xmlNewDoc ("1.0");

  doc->xmlRootNode = xmlNewDocNode (doc, NULL, "pitivi", NULL);

  ns = xmlNewNs (doc->xmlRootNode, "http://pitivi.org/pitivi-core/0.1/", "pitivi");

  projectnode = xmlNewChild (doc->xmlRootNode, ns, "project", NULL);

  if (project->settings)
    pitivi_projectsettings_save_thyself ( project->settings , projectnode);

  pitivi_projectsourcelist_save_thyself(project->sources, projectnode);

  return doc;  
}

/**
 * pitivi_project_save_to_file:
 * @PitiviProject: A PitiviProject
 * @const gchar: The filename of the file to save 
 *
 * Saves the given project to the file filename
 *
 * Returns: Returns TRUE if the file was saved properly, FALSE otherwise
 */

gboolean
pitivi_project_save_to_file(PitiviProject *project, const gchar *filename)
{
  xmlDocPtr		cur;
  xmlOutputBufferPtr	buf;
  const char		*encoding;
  xmlCharEncodingHandlerPtr handler = NULL;
  int			indent;
  gboolean		ret;
  FILE			*out;

  cur = pitivi_project_save_thyself (project);
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

/**
 * pitivi_project_set_video_output:
 * ONLY TO BE USED TO CHANGE THE VIDEO OUTPUT SINKS ! ! !
 * @PitiviProject: A PitiviProject
 * @GstElement: A Gstreamer element 
 *
 * Sets/Replaces the video output for the pipeline\n
 *
 * Returns: Void
 */

void
pitivi_project_set_video_output(PitiviProject *project, GstElement *output) 
{
  pitivi_globalbin_set_video_output (PITIVI_GLOBALBIN(project->bin), output);
}

/**
 * pitivi_project_set_video_output:
 * ONLY TO BE USED TO CHANGE THE AUDIO OUTPUT SINKS ! ! !
 * @PitiviProject: A PitiviProject
 * @GstElement: A Gstreamer element 
 *
 * Sets/Replaces the audio output for the pipeline\n
 *
 * Returns: Void
 */

void
pitivi_project_set_audio_output(PitiviProject *project, GstElement *output) 
{
  pitivi_globalbin_set_audio_output (PITIVI_GLOBALBIN (project->bin), output);
}


void
pitivi_project_set_file_to_encode (PitiviProject *project, gchar *filename)
{
  pitivi_globalbin_set_encoded_file (PITIVI_GLOBALBIN (project->bin), (const gchar *) filename);
}

static void
bin_state_change (GstElement *element, GstElementState pstate, GstElementState state, PitiviProject *project)
{
  PitiviGlobalBin	*gbin = PITIVI_GLOBALBIN (element);

  if ((pstate == GST_STATE_PLAYING) && (state == GST_STATE_PAUSED) && gbin->eos)
    gst_element_set_state (element, GST_STATE_READY);
}

static GObject *
pitivi_project_constructor (GType type,
			    guint n_construct_properties,
			    GObjectConstructParam * construct_properties)
{
  PitiviProject	*project;
  GnlSource	*ablanksource, *vblanksource;
  GstElement	*ablank, *vblank;
  GObject *obj;
  {
    /* Invoke parent constructor. */
    PitiviProjectClass *klass;
    GObjectClass *parent_class;
    klass = PITIVI_PROJECT_CLASS (g_type_class_peek (PITIVI_PROJECT_TYPE));
    parent_class = G_OBJECT_CLASS (g_type_class_peek_parent (klass));
    obj = parent_class->constructor (type, n_construct_properties,
				     construct_properties);
  }

  project = (PitiviProject *) obj;

  project->pipeline = project->private->thread = gst_thread_new("project-thread");

  project->audiogroup = gnl_group_new("audiogroup");
  project->videogroup = gnl_group_new("videogroup");
  
  project->timeline = gnl_timeline_new("project-timeline");
  
  gnl_timeline_add_group(project->timeline, project->audiogroup);
  gnl_timeline_add_group(project->timeline, project->videogroup);

  /* Adding blank audio/video elements */
  vblank = gst_element_factory_make ("videotestsrc", "vblank");
  g_object_set (G_OBJECT (vblank), "pattern", 2, 
		"sync", FALSE, NULL);
  vblanksource = gnl_source_new ("vblanksource", vblank);
  gnl_composition_set_default_source (GNL_COMPOSITION (project->videogroup), vblanksource);

  ablank = gst_element_factory_make ("silence", "silence");
  ablanksource = gnl_source_new ("ablanksource", ablank);
  gnl_composition_set_default_source (GNL_COMPOSITION (project->audiogroup), ablanksource);
  
  if (project->filename) {
    if (!(pitivi_project_internal_restore_file (project))) {
      PITIVI_WARNING ("Error restoring from file !!!");
      project->bin = NULL;
    }
  } else
    project->bin = pitivi_timelinebin_new (project->timeline,
					   project->audiogroup,
					   project->videogroup,
					   project->settings);
  
  /* add timeline and sink threads to timeline pipe */
  if (project->bin) {
    g_signal_connect (G_OBJECT (project->bin), "state_change", G_CALLBACK (bin_state_change), project);
/*     g_signal_connect (G_OBJECT (project->pipeline), "iterate", G_CALLBACK (bin_iterate), project); */
    gst_bin_add_many (GST_BIN(project->private->thread),
		      GST_ELEMENT(project->bin),
		      NULL);
    gst_element_set_state(project->pipeline, GST_STATE_READY);
  }
  return obj;
}

static void
pitivi_project_instance_init (GTypeInstance * instance, gpointer g_class)
{
  PitiviProject *self = (PitiviProject *) instance;

  self->private = g_new0 (PitiviProjectPrivate, 1);

  /* initialize all public and private members to reasonable default values. */

  self->private->dispose_has_run = FALSE;

  /* If you need specific consruction properties to complete initialization, 
   * delay initialization completion until the property is set. 
   */
  self->sources = pitivi_projectsourcelist_new();
}

static void
pitivi_project_set_property (GObject *object, guint property_id,
			     const GValue *value, GParamSpec *pspec)
{
  PitiviProject *self = PITIVI_PROJECT (object);

  switch (property_id) {
  case ARG_PROJECTSETTINGS:
    self->settings = g_value_get_pointer (value);
    break;
  case ARG_FILENAME:
    if (self->filename)
      g_free(self->filename);
    self->filename = g_strdup(g_value_get_string(value));
    break;
  default:
    G_OBJECT_WARN_INVALID_PROPERTY_ID (object, property_id, pspec);
    break;
  }
}


static void
pitivi_project_get_property (GObject *object, guint property_id,
			     GValue *value, GParamSpec *pspec)
{
  PitiviProject *self = PITIVI_PROJECT (object);

  switch (property_id) {
  case ARG_PROJECTSETTINGS:
    g_value_set_pointer (value, self->settings);
    break;
  case ARG_FILENAME:
    g_value_set_string (value, self->filename);
    break;
  default:
    G_OBJECT_WARN_INVALID_PROPERTY_ID (object, property_id, pspec);
    break;
  }
}


static void
pitivi_project_dispose (GObject * object)
{
  PitiviProject *self = PITIVI_PROJECT (object);

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
pitivi_project_finalize (GObject * object)
{
  PitiviProject *self = PITIVI_PROJECT (object);

  /* 
   * Here, complete object destruction. 
   * You might not need to do much... 
   */

  g_free (self->private);
}

static void
pitivi_project_class_init (gpointer g_class, gpointer g_class_data)
{
  GObjectClass *gobject_class = G_OBJECT_CLASS (g_class);

  gobject_class->constructor = pitivi_project_constructor;
  gobject_class->dispose = pitivi_project_dispose;
  gobject_class->finalize = pitivi_project_finalize;

  gobject_class->set_property = pitivi_project_set_property;
  gobject_class->get_property = pitivi_project_get_property;  

  g_object_class_install_property (gobject_class, ARG_PROJECTSETTINGS,
    g_param_spec_pointer("projectsettings", "Project Settings", "The project's settings",
			 G_PARAM_READWRITE | G_PARAM_CONSTRUCT ));
  
  g_object_class_install_property (gobject_class, ARG_FILENAME,
    g_param_spec_string("filename", "Filename", "The file to save/load the project",
			 NULL, G_PARAM_READWRITE | G_PARAM_CONSTRUCT ));
  
}

GType
pitivi_project_get_type (void)
{
  static GType type = 0;

  if (type == 0)
    {
      static const GTypeInfo info = {
	sizeof (PitiviProjectClass),
	NULL,			/* base_init */
	NULL,			/* base_finalize */
	pitivi_project_class_init,	/* class_init */
	NULL,			/* class_finalize */
	NULL,			/* class_data */
	sizeof (PitiviProject),
	0,			/* n_preallocs */
	pitivi_project_instance_init	/* instance_init */
      };
      type = g_type_register_static (G_TYPE_OBJECT,
				     "PitiviProjectType", &info, 0);
    }

  return type;
}
