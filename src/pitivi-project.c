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

#include "pitivi.h"
#include "pitivi-project.h"

struct _PitiviProjectPrivate
{
  /* instance private members */
  gboolean dispose_has_run;

  GstElement	*videoout;
  GstElement	*audioout;
  GstElement	*videoqueue;
  GstElement	*audioqueue;

  GstElement	*videoblank;
  GstElement	*audioblank;
  gboolean	vblankconn;
  gboolean	ablankconn;

  GstElement	*vsinkthread;
  GstElement	*asinkthread;
  gboolean	vst, ast;	// TRUE if the *sinkthread is in the pipeline
  GstElement	*source;
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

  project = (PitiviProject *) g_object_new (PITIVI_PROJECT_TYPE, NULL);
  g_assert (project != NULL);

  project->settings = settings;

  project->sources = pitivi_projectsourcelist_new();

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
  xmlDocPtr doc;
  xmlNodePtr field, cur;
  xmlNsPtr ns;
  PitiviProject *project = NULL;

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
    if (!strcmp (field->name, "project") && (field->ns == ns)) {
      /* found the PitiviProject */
      project = (PitiviProject *) g_object_new (PITIVI_PROJECT_TYPE, NULL);
      pitivi_project_restore_thyself(project, field);
      continue;
    }
  
  project->filename = g_strdup(filename);
  
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
  PitiviProjectSourceList *sourcelist;

  for (child = self->xmlChildrenNode; child; child = child->next) {
    if (!strcmp(child->name, "projectsettings")) {
      settings = (PitiviProjectSettings *) g_object_new (PITIVI_PROJECTSETTINGS_TYPE, NULL);
      pitivi_projectsettings_restore_thyself(settings, child);
      project->settings = settings;
    }
    if (!strcmp(child->name, "projectsourcelist")) {
      sourcelist = (PitiviProjectSourceList *) g_object_new( PITIVI_PROJECTSOURCELIST_TYPE, NULL);
      pitivi_projectsourcelist_restore_thyself(sourcelist, child);
      project->sources = sourcelist;
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
  /* link queue-output, add both to thread , link to timeline*/


  // if there was a video output, remove it first
  if (project->private->videoout) {
    // unlink and remove queue-output
    gst_element_unlink (project->private->videoqueue, project->private->videoout);
    gst_bin_remove_many (GST_BIN (project->private->vsinkthread), 
			 project->private->videoout,
			 project->private->videoqueue,
			 NULL);
    // unlink timeline-queue
    gst_pad_unlink (gnl_timeline_get_pad_for_group (project->timeline, project->videogroup),
			     gst_element_get_pad (project->private->videoqueue, "sink"));
  } else {
    // create and add queue
    project->private->videoqueue = gst_element_factory_make("queue", "queue");
    gst_bin_add (GST_BIN (project->private->vsinkthread),
		 project->private->videoqueue);
  }
  // add output, link it to queue
  project->private->videoout = output;
  gst_bin_add (GST_BIN(project->private->vsinkthread),
	       project->private->videoout);
  if (!gst_element_link(project->private->videoqueue, output))
    g_warning ("couldn't link the video output of the timeline to the video sink !!!");
  // link timeline-queue
  gst_pad_link (gnl_timeline_get_pad_for_group (project->timeline, project->videogroup),
		gst_element_get_pad (project->private->videoqueue, "sink"));
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
  /* link queue-output, add both to thread link to timeline*/

  // if there was a audio output, remove it first
  if (project->private->audioout) {
    // unlink and remove queue-output
    gst_element_unlink (project->private->audioqueue, project->private->audioout);
    gst_bin_remove_many (GST_BIN (project->private->asinkthread), 
			 project->private->audioout,
			 project->private->audioqueue,
			 NULL);
    // unlink timeline-queue
    gst_pad_unlink (gnl_timeline_get_pad_for_group (project->timeline, project->audiogroup),
		    gst_element_get_pad (project->private->audioqueue, "sink"));
    
  } else {
    // create and add queue
    project->private->audioqueue = gst_element_factory_make("queue", "queue");
    gst_bin_add (GST_BIN (project->private->asinkthread),
		 project->private->audioqueue);
  }
  // add output, link it to queue
  project->private->audioout = output;
  gst_bin_add (GST_BIN(project->private->asinkthread),
	       project->private->audioout);
  gst_element_link(project->private->audioqueue, output);
  // link timeline-queue
  g_printf("linking audiogroup to audioqueue\n");
  gst_pad_link (gnl_timeline_get_pad_for_group (project->timeline, project->audiogroup),
		gst_element_get_pad (project->private->audioqueue, "sink"));

}

static GObject *
pitivi_project_constructor (GType type,
			    guint n_construct_properties,
			    GObjectConstructParam * construct_properties)
{
  PitiviProject	*project;
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

  g_printf("project constructor \n");
  /*
    create container for timeline,
    Create audio&video groups and add them to the timeline
  */

  project->private->vsinkthread = gst_thread_new("vsinkthread");
  gst_object_ref(GST_OBJECT(project->private->vsinkthread));
  //  project->private->asinkthread = gst_thread_new("asinkthread");
  // gst_object_ref(GST_OBJECT(project->private->asinkthread));

  project->pipeline = gst_pipeline_new("timeline-pipe");
  gst_element_set_state(project->pipeline, GST_STATE_READY);
  
  project->audiogroup = gnl_group_new("audiogroup");
  project->videogroup = gnl_group_new("videogroup");

  project->timeline = gnl_timeline_new("project-timeline");

  //gnl_timeline_add_group(project->timeline, project->audiogroup);
  gnl_timeline_add_group(project->timeline, project->videogroup);

  /* add timeline and sink threads to timeline pipe */
  gst_bin_add_many (GST_BIN(project->pipeline),
		    GST_ELEMENT(project->timeline),
		    project->private->vsinkthread,
		    // project->private->asinkthread,
		    NULL);

  return obj;
}

static void
pitivi_project_instance_init (GTypeInstance * instance, gpointer g_class)
{
  PitiviProject *self = (PitiviProject *) instance;

  g_printf("project instance init\n");
  self->private = g_new0 (PitiviProjectPrivate, 1);

  /* initialize all public and private members to reasonable default values. */

  self->private->dispose_has_run = FALSE;

  /* If you need specific consruction properties to complete initialization, 
   * delay initialization completion until the property is set. 
   */

  self->settings = NULL;
  self->sources = NULL; 
  self->filename = NULL;
  self->pipeline = NULL;
  self->timeline = NULL;

  self->private->vst = FALSE;
  self->private->ast = FALSE;

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
pitivi_project_set_property (GObject * object,
			     guint property_id,
			     const GValue * value, GParamSpec * pspec)
{
/*   PitiviProject *self = (PitiviProject *) object; */

  switch (property_id)
    {
      /*   case PITIVI_PROJECT_PROPERTY: { */
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
pitivi_project_get_property (GObject * object,
			     guint property_id,
			     GValue * value, GParamSpec * pspec)
{
/*   PitiviProject *self = (PitiviProject *) object; */

  switch (property_id)
    {
      /*  case PITIVI_PROJECT_PROPERTY: { */
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
pitivi_project_class_init (gpointer g_class, gpointer g_class_data)
{
  GObjectClass *gobject_class = G_OBJECT_CLASS (g_class);
/*   PitiviProjectClass *klass = PITIVI_PROJECT_CLASS (g_class); */

  gobject_class->constructor = pitivi_project_constructor;
  gobject_class->dispose = pitivi_project_dispose;
  gobject_class->finalize = pitivi_project_finalize;

  gobject_class->set_property = pitivi_project_set_property;
  gobject_class->get_property = pitivi_project_get_property;

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
