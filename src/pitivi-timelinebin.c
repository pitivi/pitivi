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

#include <gnl/gnltimeline.h>
#include "pitivi.h"
#include "pitivi-timelinebin.h"
#include "pitivi-projectsettings.h"
#include "pitivi-debug.h"

static     GObjectClass *parent_class;

enum {
  ARG_0,
  ARG_TIMELINE,
  ARG_VIDEOGROUP,
  ARG_AUDIOGROUP,
  ARG_PROJECTSETTINGS
};

struct _PitiviTimelineBinPrivate
{
  /* instance private members */
  gboolean	dispose_has_run;

  GnlGroup	*audiogroup;
  GnlGroup	*videogroup;
  PitiviProjectSettings	*psettings;
};

/*
 * forward definitions
 */

/*
 * Insert "added-value" functions here
 */

/* static void */
/* pitivi_timelinebin_output_file(PitiviTimelineBin *bin, gchar *filename) */
/* { */
/*   g_object_set (G_OBJECT(bin), "encodedfile", filename, NULL); */
/* } */

PitiviTimelineBin *
pitivi_timelinebin_new(GnlTimeline	*timeline,
		       GnlGroup	*audiogroup,
		       GnlGroup	*videogroup,
		       PitiviProjectSettings *psettings)
{
  PitiviTimelineBin	*timelinebin;

  timelinebin = (PitiviTimelineBin *) g_object_new(PITIVI_TIMELINEBIN_TYPE, 
						   "timeline", timeline,
						   "audiogroup", audiogroup,
						   "videogroup", videogroup,
						   "projectsettings", psettings,
						   "name", "timelinebin",
						   NULL);
  g_assert(timelinebin != NULL);
  return timelinebin;
}

static GObject *
pitivi_timelinebin_constructor (GType type,
			     guint n_construct_properties,
			     GObjectConstructParam * construct_properties)
{
  GObject *obj;
  PitiviTimelineBin	*self;
  /* Invoke parent constructor. */
  obj = parent_class->constructor (type, n_construct_properties,
				   construct_properties);
  self = PITIVI_TIMELINEBIN (obj);

  /* do stuff. */
  gst_bin_add (GST_BIN(obj), GST_ELEMENT (self->timeline));

  return obj;
}

static void
pitivi_timelinebin_instance_init (GTypeInstance * instance, gpointer g_class)
{
  PitiviTimelineBin *self = (PitiviTimelineBin *) instance;

  self->private = g_new0(PitiviTimelineBinPrivate, 1);
  
  /* initialize all public and private members to reasonable default values. */ 
  
  self->private->dispose_has_run = FALSE;
  
  /* Do only initialisation here */
  /* The construction of the object should be done in the Constructor
     So that properties set at instanciation can be set */
}

static void
pitivi_timelinebin_dispose (GObject *object)
{
  PitiviTimelineBin	*self = PITIVI_TIMELINEBIN(object);

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

  G_OBJECT_CLASS (parent_class)->dispose (object);
}

static void
pitivi_timelinebin_finalize (GObject *object)
{
  PitiviTimelineBin	*self = PITIVI_TIMELINEBIN(object);

  /* 
   * Here, complete object destruction. 
   * You might not need to do much... 
   */

  g_free (self->private);
  G_OBJECT_CLASS (parent_class)->finalize (object);
}

static gboolean
pitivi_timelinebin_connect_source (PitiviGlobalBin *gbin)
{
  PitiviTimelineBin	*self = PITIVI_TIMELINEBIN (gbin);
  GSList	*tmp;
  PitiviMediaSettings *ms;

  /* connect timeline's output to the tees */
  if (!gst_element_set_state(GST_ELEMENT (self->timeline), GST_STATE_PAUSED)) {
    PITIVI_WARNING ("wasn't able to set the timeline to PAUSED");
    return FALSE;
  }
  tmp = self->private->psettings->media_settings;
  ms = tmp->data;
  if (gbin->videoout)
    if (!(gst_pad_link_filtered(gnl_timeline_get_pad_for_group (self->timeline, self->private->videogroup),
				gst_element_get_pad (gbin->vtee, "sink"),
				ms->caps)))
      return FALSE;
  tmp = g_slist_next (tmp);
  ms = tmp->data;
  if (gbin->audioout)
    if (!(gst_pad_link_filtered(gnl_timeline_get_pad_for_group (self->timeline, self->private->audiogroup),
				gst_element_get_pad (gbin->atee, "sink"),
				ms->caps)))
      return FALSE;
  return TRUE;
}

static gboolean
pitivi_timelinebin_disconnect_source (PitiviGlobalBin *gbin)
{
  PitiviTimelineBin	*self = PITIVI_TIMELINEBIN (gbin);

  /* disconnect timeline's output from the tees */
  if (gbin->videoout)
    gst_pad_unlink (gnl_timeline_get_pad_for_group (self->timeline, self->private->videogroup),
		    gst_element_get_pad (gbin->vtee, "sink"));
  if (gbin->audioout)
    gst_pad_unlink (gnl_timeline_get_pad_for_group (self->timeline, self->private->audiogroup),
		    gst_element_get_pad (gbin->atee, "sink"));
  return TRUE;
}

static gboolean
pitivi_timelinebin_setup_encoding (PitiviTimelineBin *self)
{
  PitiviGlobalBin	*gbin = PITIVI_GLOBALBIN (self);
  PitiviMediaSettings	*ms;
  GSList	*tmp;
  GstElement	*vencoder, *aencoder, *muxer;

  PITIVI_DEBUG ("timelinebin_setup_encoding");
  if (!(gbin->render))
    return TRUE;
  if (!(gbin->encodedfile))
    return FALSE;

  /* Create the encoding and muxer element's */
  muxer = gst_element_factory_make (self->private->psettings->container_factory_name, "timeline-muxer");
  if (!muxer)
    return FALSE;

  tmp = self->private->psettings->media_settings;
  ms = tmp->data;
  
  vencoder = gst_element_factory_make (ms->codec_factory_name, "timeline-vencoder");
  if (!vencoder)
    return FALSE;

  tmp = g_slist_next (tmp);
  ms = tmp->data;

  aencoder = gst_element_factory_make (ms->codec_factory_name, "timeline-aencoder");
  if (!aencoder)
    return FALSE;

  g_object_set (G_OBJECT (self), 
		"muxer", muxer,
		"aencoder", aencoder,
		"vencoder", vencoder,
		NULL);
  return TRUE;
}

/* static gboolean */
/* pitivi_timelinebin_check_outputs (PitiviTimelineBin *self) */
/* { */
/*   PitiviGlobalBin	*gbin = PITIVI_GLOBALBIN(self); */

/*   g_warning ("checking outputs"); */
/*   if (gbin->videoout) */
/*     if (!(gst_element_set_state(gbin->videoout, GST_STATE_PLAYING))) { */
/*       g_warning ("Couldn't set Video Output to PLAYING !!!"); */
/*       return FALSE; */
/*     } */
/*   if (gbin->audioout) */
/*     if (!(gst_element_set_state(gbin->audioout, GST_STATE_PLAYING))) { */
/*       g_warning ("couldn't set Audio Output to PLAYING !!!"); */
/*       return FALSE; */
/*     } */
/*   return TRUE; */
/* } */

static GstElementStateReturn
pitivi_timelinebin_change_state (GstElement *element)
{
  switch (GST_STATE_TRANSITION (element)) {
  case GST_STATE_READY_TO_PAUSED:
    if (!(pitivi_timelinebin_setup_encoding (PITIVI_TIMELINEBIN(element))))
      return GST_STATE_FAILURE;
    break;
/*   case GST_STATE_PAUSED_TO_PLAYING: */
/*     if (!(pitivi_timelinebin_check_outputs (PITIVI_TIMELINEBIN(element)))) */
/*       return GST_STATE_FAILURE; */
/*     break; */
  default:
    break;
  }

  if (GST_ELEMENT_CLASS (parent_class)->change_state)
    return GST_ELEMENT_CLASS (parent_class)->change_state (element);

  return GST_STATE_SUCCESS;
}


static void
pitivi_timelinebin_set_property (GObject * object,
			      guint property_id,
			      const GValue * value, GParamSpec * pspec)
{
  PitiviTimelineBin *self = (PitiviTimelineBin *) object;

  switch (property_id)
    {
    case ARG_TIMELINE:
      self->timeline = g_value_get_pointer (value);
      break;
    case ARG_VIDEOGROUP:
      self->private->videogroup = g_value_get_pointer (value);
      break;
    case ARG_AUDIOGROUP:
      self->private->audiogroup = g_value_get_pointer (value);
      break;
    case ARG_PROJECTSETTINGS:
      self->private->psettings = g_value_get_pointer (value);
      break;
    default:
      G_OBJECT_WARN_INVALID_PROPERTY_ID (object, property_id, pspec);
      break;
    }
}

static void
pitivi_timelinebin_get_property (GObject * object,
			      guint property_id,
			      GValue * value, GParamSpec * pspec)
{
  PitiviTimelineBin *self = (PitiviTimelineBin *) object;

  switch (property_id)
    {
    case ARG_TIMELINE:
      g_value_set_pointer(value, self->timeline);
      break;
    case ARG_VIDEOGROUP:
      g_value_set_pointer(value, self->private->videogroup);
      break;
    case ARG_AUDIOGROUP:
      g_value_set_pointer(value, self->private->audiogroup);
      break;
    case ARG_PROJECTSETTINGS:
      g_value_set_pointer(value, self->private->psettings);
      break;
    default:
      G_OBJECT_WARN_INVALID_PROPERTY_ID (object, property_id, pspec);
      break;
    }
}

static void
pitivi_timelinebin_class_init (gpointer g_class, gpointer g_class_data)
{
  GObjectClass *gobject_class = G_OBJECT_CLASS (g_class);
  PitiviGlobalBinClass	*gbin_class = PITIVI_GLOBALBIN_CLASS (g_class);
  GstElementClass	*gstelement_class = GST_ELEMENT_CLASS (g_class);

  parent_class = G_OBJECT_CLASS (g_type_class_peek_parent (g_class));

  gobject_class->constructor = pitivi_timelinebin_constructor;
  gobject_class->dispose = pitivi_timelinebin_dispose;
  gobject_class->finalize = pitivi_timelinebin_finalize;

  gobject_class->set_property = pitivi_timelinebin_set_property;
  gobject_class->get_property = pitivi_timelinebin_get_property;

  gstelement_class->change_state = pitivi_timelinebin_change_state;

  gbin_class->connect_source = pitivi_timelinebin_connect_source;
  gbin_class->disconnect_source = pitivi_timelinebin_disconnect_source;

  g_object_class_install_property (gobject_class, ARG_TIMELINE,
       g_param_spec_pointer ("timeline", "Timeline", "The GnlTimeline to use as source",
			     G_PARAM_READWRITE | G_PARAM_CONSTRUCT_ONLY));

  g_object_class_install_property (gobject_class, ARG_VIDEOGROUP,
       g_param_spec_pointer ("videogroup", "VideoGroup", "The GnlGroup of the timeline to use as video source",
			     G_PARAM_READWRITE | G_PARAM_CONSTRUCT_ONLY));

  g_object_class_install_property (gobject_class, ARG_AUDIOGROUP,
       g_param_spec_pointer ("audiogroup", "AudioGroup", "The GnlGroup of the timeline to use as audio source",
			     G_PARAM_READWRITE | G_PARAM_CONSTRUCT_ONLY));

  g_object_class_install_property (gobject_class, ARG_PROJECTSETTINGS,
       g_param_spec_pointer ("projectsettings", "Project Settings", "The project settings to use to set encoders",
			     G_PARAM_READWRITE | G_PARAM_CONSTRUCT_ONLY));

}

GType
pitivi_timelinebin_get_type (void)
{
  static GType type = 0;
 
  if (type == 0)
    {
      static const GTypeInfo info = {
	sizeof (PitiviTimelineBinClass),
	NULL,			/* base_init */
	NULL,			/* base_finalize */
	pitivi_timelinebin_class_init,	/* class_init */
	NULL,			/* class_finalize */
	NULL,			/* class_data */
	sizeof (PitiviTimelineBin),
	0,			/* n_preallocs */
	pitivi_timelinebin_instance_init	/* instance_init */
      };
      type = g_type_register_static (PITIVI_GLOBALBIN_TYPE,
				     "PitiviTimelineBin", &info, 0);
    }

  return type;
}
