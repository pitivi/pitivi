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

  GstElement	*timelinepipe;
  GnlGroup	*audiogroup;
  GnlGroup	*videogroup;
};

/*
 * forward definitions
 */

/*
 * Insert "added-value" functions here
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

/*
  pitivi_project_new_from_file

  loads a PitiviProject from the given file filename

  Returns the loaded PitiviProject, or NULL if there's a problem
*/

PitiviProject *
pitivi_project_new_from_file (const gchar *filename)
{
  xmlDocPtr doc;
  xmlNodePtr field, cur, child;
  xmlNsPtr ns;
  PitiviProject *project;

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
  /*
    TODO

    restore the other properties of the PitiviProject
  */
}

/*
  pitivi_project_save_thyself

  Returns a pointer to the XMLDocument filled with the contents of the PitiviProject
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

/*
  pitivi_project_save_to_file

  Saves the given project to the file filename

  Returns TRUE if the file was saved properly, FALSE otherwise
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


/*
  pitivi_project_set_source_element

  Sets a GstElement as the source of the project's pipeline
  The element's pad must be named accordingly:
  "vsrc" for the video source
  "asrc" for the audio source

  Returns TRUE if the source was correctly added
*/

gboolean
pitivi_project_set_source_element(PitiviProject *project, GstElement *source)
{
  
  g_printf("setting source element\n");
  gst_element_set_state(project->pipeline, GST_STATE_PAUSED);

  /* Remove previous source */
  if (project->private->source) {
    gst_element_unlink_pads(project->private->source, "vsrc",
			    project->private->videoqueue, "sink");
    gst_bin_remove(GST_BIN(project->pipeline), project->private->source);
    project->private->source = NULL;
  } else if (project->private->vblankconn) {
    /* disconnect and remove blankvideo conn */
    g_printf("removing vblank\n");
    gst_element_unlink(project->private->videoblank, project->private->videoqueue);
    gst_bin_remove(GST_BIN(project->pipeline), project->private->videoblank);
    project->private->vblankconn = FALSE;
  }

  /* add source to pipeline, connect vsrc to vsinkthread and asrc to asinkthread*/
  g_printf("adding source to pipeline\n");
  gst_bin_add(GST_BIN(project->pipeline), source);
  project->private->source = source;

  if (gst_element_get_pad(source, "vsrc")) {
    if (!project->private->vst) {
      g_printf("Adding video sink thread\n");
      gst_bin_add(GST_BIN(project->pipeline), project->private->vsinkthread);
    }
    g_printf("linking source to video sink thread\n");
    project->private->vst = TRUE;
    gst_element_link_pads(source, "vsrc", project->private->videoqueue, "sink");
  } else if (project->private->vst) {
    g_printf("Removing video sink thread\n");
    gst_bin_remove(GST_BIN(project->pipeline), project->private->vsinkthread);
    project->private->vst = FALSE;
  }

  /* if (gst_element_get_pad(source, "asrc")) { */
/*     if (!project->private->ast) */
/*       gst_bin_add(GST_BIN(project->pipeline), project->private->asinkthread); */
/*     project->private->ast = TRUE; */
/*     gst_element_link_pads(source, "asrc", project->private->audioqueue, "sink"); */
/*   } else if (project->private->ast) { */
/*     gst_bin_remove(GST_BIN(project->pipeline), project->private->asinkthread); */
/*     project->private->ast = FALSE; */
/*   } */

 /*  gst_element_set_state(project->pipeline, GST_STATE_PLAYING); */

  return TRUE;
}

/*
  pitivi_project_blank_source

  If there's a source, removes it and Sets the blank sources 
  for the project's pipeline
*/

void
pitivi_project_blank_source(PitiviProject *project)
{
  
  /* take off the source */
  if (project->private->source) {
    gst_bin_remove(GST_BIN(project->pipeline), project->private->source);
    project->private->source = NULL;
  }
  if (!project->private->vst) {
    gst_bin_add(GST_BIN(project->pipeline),
		project->private->vsinkthread);
    project->private->vst = TRUE;
  }
  if (project->private->ast) {
    gst_bin_remove(GST_BIN(project->pipeline),
		   project->private->asinkthread);
    project->private->ast = FALSE;
  }
  if (!project->private->vblankconn) {
    gst_bin_add(GST_BIN(project->pipeline),
		project->private->videoblank);
    gst_element_link(project->private->videoblank, project->private->videoqueue);
    project->private->vblankconn = TRUE;
  }
}

void
pitivi_project_set_video_output(PitiviProject *project, GstElement *output) 
{
  /* link queue-output, add both to thread */

  project->private->videoqueue = gst_element_factory_make("queue", "queue");
  project->private->videoout = output;
  gst_bin_add_many(GST_BIN(project->private->vsinkthread),
		   project->private->videoqueue,
		   project->private->videoout,
		   NULL);
  gst_element_link(project->private->videoqueue, output);
}

void
pitivi_project_set_audio_output(PitiviProject *project, GstElement *output) 
{
  /* link queue-output, add both to thread */

  project->private->audioqueue = gst_element_factory_make("queue", "queue");
  project->private->audioout = output;
  gst_element_link(project->private->audioqueue, output);
  gst_bin_add_many(GST_BIN(project->private->asinkthread), 
		   project->private->audioqueue,
		   project->private->audioout,
		   NULL);
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
  
  /*
    create container for timeline,
    Create audio&video groups and add them to the timeline
  */

  project->private->vsinkthread = gst_thread_new("vsinkthread");
  gst_object_ref(GST_OBJECT(project->private->vsinkthread));
  project->private->asinkthread = gst_thread_new("asinkthread");
  gst_object_ref(GST_OBJECT(project->private->asinkthread));

  project->private->timelinepipe = gst_pipeline_new("timeline-pipe");
  project->private->audiogroup = gnl_group_new("audiogroup");
  project->private->videogroup = gnl_group_new("videogroup");

  gnl_timeline_add_group(project->timeline, project->private->audiogroup);
  gnl_timeline_add_group(project->timeline, project->private->videogroup);

  /* add timeline to timeline pipe */
  gst_bin_add(GST_BIN(project->private->timelinepipe),
	      GST_ELEMENT(project->timeline));

  /* create timeline pipe's ghost pads for insertion in project's pipeline */
  gst_element_add_ghost_pad(project->private->timelinepipe,
			    gnl_timeline_get_pad_for_group(project->timeline, 
							   project->private->audiogroup),
			    "asrc");

  gst_element_add_ghost_pad(project->private->timelinepipe,
			    gnl_timeline_get_pad_for_group(project->timeline,
							   project->private->videogroup),
			    "vsrc");

  return obj;
}

static void
pitivi_project_instance_init (GTypeInstance * instance, gpointer g_class)
{
  PitiviProject *self = (PitiviProject *) instance;
  GstElement	*aq, *vq;
  GstPad	*apad, *vpad;

  self->private = g_new0 (PitiviProjectPrivate, 1);

  /* initialize all public and private members to reasonable default values. */

  self->private->dispose_has_run = FALSE;

  /* If you need specific consruction properties to complete initialization, 
   * delay initialization completion until the property is set. 
   */

  self->settings = NULL;
  self->sources = NULL; 
  self->filename = NULL;

  self->pipeline = gst_pipeline_new("project-pipeline");
  gst_element_set_state(self->pipeline, GST_STATE_READY);

  self->timeline = gnl_timeline_new("project-timeline");

  self->private->videoblank = gst_element_factory_make("videotestsrc", "videoblank");
  gst_object_ref(GST_OBJECT(self->private->videoblank));
  //self->private->audioblank = gst_element_factory_make("silence", "audioblank");
  //gst_object_ref(GST_OBJECT(self->private->audioblank));

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
  PitiviProject *self = (PitiviProject *) object;

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
  PitiviProject *self = (PitiviProject *) object;

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
  PitiviProjectClass *klass = PITIVI_PROJECT_CLASS (g_class);

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
