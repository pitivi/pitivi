/* 
 * PiTiVi
 * Copyright (C) <2004>		Guillaume Casanova <casano_g@epita.fr>
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
#include "pitivi-sourcefile.h"
#include "pitivi-settings.h"
#include "pitivi-mainapp.h"
#include "pitivi-debug.h"

static  GObjectClass *parent_class;

static enum {
  IS_AUDIO = 1,
  IS_VIDEO,
  IS_AUDIO_VIDEO
} outputtype;

struct _PitiviSourceFilePrivate
{
  /* instance private members */
  gboolean	dispose_has_run;

  /* List of exported bins */
  GSList	*bins;

  /* GST variable */
  GstElement	*decode;

  GstPad	*audiopad;
  GstElement	*audioout;
  GstPad	*videopad;
  GstElement	*videoout;

  GstElementFactory	*factory;

  /* audio video properties */
  int	vwidth, vheight;
  gdouble	framerate;
  int	awidth, arate, achanns;

  gint		lastsinkid;
  /* MainApp */
  PitiviMainApp *mainapp;
};

typedef struct  _bindata {
  GstElement	*bin;
  gboolean	ready;
  PitiviSourceFile	*sf;
  gint		bintype;
  gboolean	audioready;
  gboolean	videoready;
}		bindata;

/*
 * forward definitions
 */

/*
 * Insert "added-value" functions here
 */

enum
  {
    PROP_FILENAME = 1,
    PROP_MAINAPP,
  };

int
get_pad_type (GstPad *pad)
{
  GstStructure	*struc;

  if (!(struc = gst_caps_get_structure(gst_pad_get_caps (pad), 0)))
    return 0;
  if (!g_ascii_strncasecmp("audio", gst_structure_get_name(struc), 5))
    return IS_AUDIO;
  if (!g_ascii_strncasecmp("video", gst_structure_get_name(struc), 5))
    return IS_VIDEO;
  return 0;
}

void
cache_audio_video (PitiviSourceFile *sf)
{
  if (!gst_element_seek (sf->private->decode, GST_FORMAT_BYTES | GST_SEEK_METHOD_SET | GST_SEEK_FLAG_FLUSH, 0))
    g_printf("ERROR SEEKING BACK TO 0!!!!\n");

  if (sf->haveaudio) { /* TODO : Cache audio */
    
  }
  if (sf->havevideo) { /* TODO : Cache video */

  }
}

/* bin_new_pad_cb , callback used by outgoing bins when there's a new pad */

void
bin_new_pad_cb (GstElement * element, GstPad * pad, gboolean last, gpointer udata)
{
  gint	type;
  bindata	*data = (bindata *) udata;
  char		*tmp;
  GstElement	*sink;
  
  type = get_pad_type (pad);
  if (!type)
    return;
  g_printf("Adding pad type[%d]->[%d] : %s:%s\n", type, data->bintype, GST_DEBUG_PAD_NAME(pad));
  /* Connect (adapters and) ghost pads */
  if (type == IS_AUDIO) {
    if (data->bintype != IS_VIDEO) {
      /* TODO : Add the adapters */
      if (data->bintype == IS_AUDIO_VIDEO) {
	gst_element_add_ghost_pad (data->bin, pad, "asrc");
      } else {
	gst_element_add_ghost_pad (data->bin, pad, "src");
      }
    } else {
      tmp = g_strdup_printf("fakesink%d", data->sf->private->lastsinkid++);
      sink = gst_element_factory_make ("fakesink", tmp);
      g_free(tmp);
      gst_bin_add(GST_BIN (data->bin), sink);
      if (!(gst_pad_link(pad, gst_element_get_pad(sink, "sink"))))
	g_printf("Error linking decodebin pad to fakesink !!!");
    }
    data->audioready = TRUE;
  } else if (type == IS_VIDEO) {
    if (data->bintype != IS_AUDIO) {
      /* TODO : Add the adapter */
      if (data->bintype == IS_AUDIO_VIDEO) {
	gst_element_add_ghost_pad (data->bin, pad, "vsrc");
      } else {
	gst_element_add_ghost_pad (data->bin, pad, "src");
      }
    } else {
      tmp = g_strdup_printf("fakesink%d", data->sf->private->lastsinkid++);
      sink = gst_element_factory_make ("fakesink", tmp);
      g_free(tmp);
      gst_bin_add(GST_BIN (data->bin), sink);
      if (!(gst_pad_link(pad, gst_element_get_pad(sink, "sink"))))
	g_printf("Error linking decodebin pad to fakesink !!!");
    }
    data->videoready = TRUE;
  }
  /* update ready flag */
  if ((data->sf->haveaudio && data->sf->havevideo) && data->audioready && data->videoready)
    data->ready = TRUE;
  if (data->sf->haveaudio && data->audioready)
    data->ready = TRUE;
  if (data->sf->havevideo && data->videoready)
    data->ready = TRUE;
}

GstElement *
create_new_bin (PitiviSourceFile *self, int type)
{
  GstElement	*container, *pipeline, *decode, *src;
  gchar		*tmp;
  GError	*error = NULL;
  gint		i;
  bindata	*data;


  tmp = g_strdup_printf ("( filesrc name=src location=\"%s\" ! decodebin name=dbin )",
			 self->filename);
  pipeline = gst_parse_launch (tmp, &error);
  g_assert (pipeline != NULL);
  g_assert (error == NULL);
  g_free(tmp);

  container = gst_pipeline_new ("container");
  gst_bin_add (GST_BIN (container), pipeline);

  data = g_new0(bindata, 1);
  data->bin = pipeline;
  data->sf = self;
  data->bintype = type;
  decode = gst_bin_get_by_name (GST_BIN (pipeline), "dbin");
  g_signal_connect (decode, "new-decoded-pad", G_CALLBACK (bin_new_pad_cb), data);

  if (!(gst_element_set_state (container, GST_STATE_PLAYING))) return NULL;
  
  for (i = 1000; i--; ) {
    if (!(gst_bin_iterate(GST_BIN(container))))
      break;
    if (data->ready)
      break;
  }

  if (!gst_element_seek (decode, GST_FORMAT_BYTES | GST_SEEK_METHOD_SET | GST_SEEK_FLAG_FLUSH, 0))
    g_printf("ERROR SEEKING BACK TO 0!!!!\n");
  pitivi_printf_element(pipeline);
  gst_element_set_state (container, GST_STATE_PAUSED);
  gst_object_ref(GST_OBJECT(pipeline));
  gst_bin_remove (GST_BIN (container), pipeline);
  g_printf("Created the pipeline %p\n", container);
  return pipeline;
}

/*
  pretty_caps_to_string

  Returns a nicely formatted version of the caps (for audio or video)
*/

char *
pretty_caps_to_string (GstCaps *caps)
{
  GstStructure	*struc;

  if (!(struc = gst_caps_get_structure(caps, 0)))
    return NULL;
  if (!gst_caps_is_fixed(caps))
    return g_strdup("Not fixed");

  if (!g_ascii_strncasecmp("video", gst_structure_get_name(struc), 5)) {
    gint	width, height;
    gdouble	framerate;
    
    gst_structure_get_int(struc, "width", &width);
    gst_structure_get_int(struc, "height", &height);
    gst_structure_get_double(struc, "framerate", &framerate);
    return g_strdup_printf("%dx%d@%gfps", width, height, framerate);
  }
  if (!g_ascii_strncasecmp("audio", gst_structure_get_name(struc), 5)) {
    gint	width, rate, channels;
    
    gst_structure_get_int(struc, "width", &width);
    gst_structure_get_int(struc, "rate", &rate);
    gst_structure_get_int(struc, "channels", &channels);
    return g_strdup_printf("%d x %dHz@%dbit", channels, rate, width);
  }
  return g_strdup("Unknown");
}

void
record_pad_info (PitiviSourceFile *self, int type, GstPad *pad)
{
  char	**info;
  GstStructure	*struc;
  
  if (type == IS_VIDEO)
    info = &self->infovideo;
  else if (type == IS_AUDIO)
    info = &self->infoaudio;
  *info = pretty_caps_to_string(gst_pad_get_caps(pad));

  if (!(struc = gst_caps_get_structure(gst_pad_get_caps(pad), 0)))
    return;
  if (type == IS_VIDEO) {
    gst_structure_get_int(struc, "width", &(self->private->vwidth));
    gst_structure_get_int(struc, "height", &(self->private->vheight));
    gst_structure_get_double(struc, "framerate", &(self->private->framerate));
  } else if (type == IS_AUDIO) {
    gst_structure_get_int(struc, "width", &(self->private->awidth));
    gst_structure_get_int(struc, "rate", &(self->private->arate));
    gst_structure_get_int(struc, "channels", &(self->private->achanns));
  }
}

void
establish_length (PitiviSourceFile *self)
{
  guint64	lena = 0, lenv = 0;
  GstFormat	format = GST_FORMAT_TIME;
  GstElement	*elt;
  
  if (self->haveaudio)
    if (!(gst_pad_query(GST_PAD (GST_PAD_REALIZE (self->private->audiopad)),
			GST_QUERY_TOTAL, &format, &lena)))
      lena = 0;
  format = GST_FORMAT_TIME;
  if (self->havevideo)
    if (!(gst_pad_query(GST_PAD (GST_PAD_REALIZE (self->private->videopad)),
			GST_QUERY_TOTAL, &format, &lenv)))
      lenv = 0;
  self->length = MAX(lena, lenv);
}

int
pitivi_sourcefile_store_pad (PitiviSourceFile *sf, GstPad *pad)
{
  GstCaps	*caps;
  GstStructure	*struc;
  gint		type;
  
  type = get_pad_type (pad);
  if (!type)
    return 0;
  if (type == IS_AUDIO) {
    sf->private->audiopad = pad;
    return IS_AUDIO;
  }
  if (type == IS_VIDEO) {
    sf->private->videopad = pad;
    return IS_VIDEO;
  }
  return 0;
}

void
new_decoded_pad_cb (GstElement * element, GstPad * pad, gboolean last, gpointer udata)
{
  PitiviSourceFile	*sf = PITIVI_SOURCEFILE (udata);
  GstElement	*sink;
  char	*tmp;
  int	type;

  if (!(type = pitivi_sourcefile_store_pad (sf, pad)))
    return;
  /* Stick a fakesink to the pad */
  /* TODO : Should stick the correct converters/cache sink */

  tmp = g_strdup_printf("fakesink%d", sf->private->lastsinkid++);
  sink = gst_element_factory_make ("fakesink", tmp);
  g_free(tmp);
  gst_bin_add(GST_BIN (sf->pipeline), sink);
  gst_element_link(element, sink);
  if (type == IS_AUDIO)
    sf->private->audioout = sink;
  else
    sf->private->videoout = sink;
}

void
unknown_type_cb (GstElement * element, GstCaps *caps, gpointer udata)
{
  g_printf("Unknown pad : %s\n", gst_caps_to_string(caps));
}

/*
  _get_info

  Creates the ->pipeline with the corresponding filesrc, outputs, etc...
*/

void
pitivi_sourcefile_get_info (PitiviSourceFile *self)
{
  char	*tmp;
  GError	*error = NULL;
  gint	i;
  gulong	ndhandler, unhandler;

  tmp = g_strdup_printf ("filesrc name=src location=\"%s\" ! decodebin name=dbin",
			 self->filename);
  self->pipeline = gst_parse_launch (tmp, &error);
  g_assert (self->pipeline != NULL);
  g_assert (error == NULL);
  g_free(tmp);

  self->private->decode = gst_bin_get_by_name (GST_BIN(self->pipeline), "dbin");
  ndhandler = g_signal_connect(self->private->decode, "new-decoded-pad", G_CALLBACK (new_decoded_pad_cb), self);
  unhandler = g_signal_connect(self->private->decode, "unknown-type", G_CALLBACK (unknown_type_cb), self);

  if (!(gst_element_set_state (self->pipeline, GST_STATE_PLAYING))) return;
  
  for (i = 1000; i--; ) {
    if (!(gst_bin_iterate(GST_BIN(self->pipeline))))
      break;
    if (!(i % 5)) { /* Check every 5 iterations if we have fixed pads */
      if (self->private->audiopad)
	{
	  if (self->private->videopad) 
	    { /* audio and video */
	      if (gst_caps_is_fixed(gst_pad_get_caps(self->private->audiopad))
		  && gst_caps_is_fixed(gst_pad_get_caps(self->private->videopad)))
		break;
	    }
	  else /* audio only */
	    if (gst_caps_is_fixed(gst_pad_get_caps(self->private->audiopad))) 
	      break;
	}
      else  {/* video only */
	if (self->private->videopad && gst_caps_is_fixed(gst_pad_get_caps(self->private->videopad)))
	  break;
      }
    }
  }
  g_signal_handler_disconnect (self->private->decode, ndhandler);
  g_signal_handler_disconnect (self->private->decode, unhandler);
  if (self->private->videopad && gst_caps_is_fixed(gst_pad_get_caps(self->private->videopad))) {
    self->havevideo = TRUE;
    record_pad_info(self, IS_VIDEO, self->private->videopad);
  } 
  if (self->private->audiopad && gst_caps_is_fixed(gst_pad_get_caps(self->private->audiopad))) {
    self->haveaudio = TRUE;
    record_pad_info(self, IS_AUDIO, self->private->audiopad);
  }

  establish_length(self);

  /* Remove fakesinks */
  if (self->private->audioout) {
    gst_element_unlink(self->private->decode, self->private->audioout);
    gst_bin_remove(GST_BIN(self->pipeline), self->private->audioout);
    self->private->audioout = NULL;
  }
  if (self->private->videoout) {
    gst_element_unlink(self->private->decode, self->private->videoout);
    gst_bin_remove(GST_BIN(self->pipeline), self->private->videoout);
    self->private->videoout = NULL;
  }

  cache_audio_video (self);

  gst_element_set_state (self->pipeline, GST_STATE_READY);

  gst_object_unref (GST_OBJECT (self->pipeline));
  self->private->decode = NULL;
  self->pipeline = NULL;
}

void
pitivi_sourcefile_type_find (PitiviSourceFile *this)
{
  /* Discover file properties (audio props, video props, length) */
  pitivi_sourcefile_get_info (this);

  if (this->havevideo)
    if (this->haveaudio)
      this->mediatype = g_strdup("video/audio");
    else
      this->mediatype = g_strdup("video");
  else
    if (this->haveaudio)
      this->mediatype = g_strdup("audio");
}

void
bin_was_freed(gpointer udata, GObject *object)
{
  PitiviSourceFile	*self = PITIVI_SOURCEFILE(udata);

  self->private->bins = g_slist_remove(self->private->bins, object);
  self->nbbins--;
}

/**
 * pitivi_sourcefile_get_bin:
 * @sf: The #PitiviSourceFile to get a complete bin from
 *
 * Returns: A complete #GstBin from the given file, or NULL if it is an effect source
 */

GstElement *
pitivi_sourcefile_get_bin (PitiviSourceFile *sf)
{
  GstElement	*res;

  g_printf ("get_bin\n");
  if (sf->haveeffect)
    return NULL;
  res = create_new_bin (sf, IS_AUDIO_VIDEO);
  /* TODO : Reference the bin */
  g_object_weak_ref(G_OBJECT(res), bin_was_freed, sf);
  sf->private->bins = g_slist_append(sf->private->bins, res);
  sf->nbbins++;
  return res;
}

/**
 * pitivi_sourcefile_get_audio_bin:
 * @sf: The #PitiviSourceFile to get an audio-only bin from
 *
 * Returns: An audio-only #GstBin from the given file, or NULL if it doesn't contain audio
 */

GstElement *
pitivi_sourcefile_get_audio_bin (PitiviSourceFile *sf)
{
  GstElement	*res;

  g_printf ("get_audio_bin\n");
  if (!sf->haveaudio)
    return NULL;
  res = create_new_bin (sf, IS_AUDIO);
  /* TODO : Reference the bin */
  g_object_weak_ref(G_OBJECT(res), bin_was_freed, sf);
  sf->private->bins = g_slist_append(sf->private->bins, res);
  sf->nbbins++;
  return res;
}

/**
 * pitivi_sourcefile_get_video_bin:
 * @sf: The #PitiviSourceFile to get a video-only bin from
 *
 * Returns: A video-only #GstBin from the given file, or NULL if it doesn't contain video
 */

GstElement *
pitivi_sourcefile_get_video_bin (PitiviSourceFile *sf)
{
  GstElement	*res;

  g_printf ("get_video_bin\n");
  if (!sf->havevideo)
    return NULL;
  res = create_new_bin (sf, IS_VIDEO);
  /* TODO : Reference the bin */
  g_object_weak_ref(G_OBJECT(res), bin_was_freed, sf);
  sf->private->bins = g_slist_append(sf->private->bins, res);
  sf->nbbins++;
  return res;
}

/**
 * pitivi_sourcefile_get_effect_bin:
 * @sf: The #PitiviSourceFile to get an effect bin from
 *
 * Returns: An effect #GstElement from the given source, or NULL if it doesn't contain an effect
 */

GstElement *
pitivi_sourcefile_get_effect_bin (PitiviSourceFile *sf)
{
  GstElement	*res;
  gchar		*tmp;

  g_printf ("get_effect_bin\n");
  if (!sf->haveeffect)
    return NULL;
  tmp = g_strdup_printf ("%s-%s", sf->filename, sf->private->lastsinkid++);
  res = gst_element_factory_create (sf->private->factory, tmp);
  g_free (tmp);
  g_object_weak_ref(G_OBJECT(res), bin_was_freed, sf);
  sf->private->bins = g_slist_append(sf->private->bins, res);
  sf->nbbins++;
  return res;  
}

/**
 * pitivi_sourcefile_new:
 * @filename: The file to use
 * @mainapp: The #PitiviMainApp
 *
 * Returns: A newly-allocated #PitiviSourceFile
 */

PitiviSourceFile *
pitivi_sourcefile_new (gchar *filename, PitiviMainApp *mainapp)
{
  PitiviSourceFile	*sourcefile;

  sourcefile = (PitiviSourceFile *) g_object_new(PITIVI_SOURCEFILE_TYPE,
						 "filename",
						 filename,
						 "mainapp",
						 mainapp,
						 NULL);
  g_assert(sourcefile != NULL);
  pitivi_sourcefile_type_find (sourcefile);

  sourcefile->pipeline = create_new_bin (sourcefile, IS_AUDIO_VIDEO);
  if (sourcefile->haveaudio)
    sourcefile->pipeline_audio = create_new_bin (sourcefile, IS_AUDIO);
  if (sourcefile->havevideo)
    sourcefile->pipeline_video = create_new_bin (sourcefile, IS_VIDEO);
 
  g_printf("Created new PitiviSourceFile %p\n", sourcefile);
  return sourcefile;
}

/**
 * pitivi_sourcefile_new_effect:
 * @name: The name of the effect
 * @pipeline: The effect's #GstElement
 * @mainapp: The #PitiviMainApp
 *
 * Returns: A newly-allocated #PitiviSourceFile
 */

PitiviSourceFile *
pitivi_sourcefile_new_effect (gchar *name, GstElementFactory *factory, GdkPixbuf *pixbuf,
			      gchar *mediatype, PitiviMainApp *mainapp)
{
  PitiviSourceFile	*sf;

  sf = (PitiviSourceFile *) g_object_new(PITIVI_SOURCEFILE_TYPE,
					 "mainapp", mainapp,
					 NULL);
  g_assert (sf != NULL);
  /* TODO : Prepare the SourceFile for effects */
  sf->filename = g_strdup (name);
  sf->pipeline = NULL;
  sf->private->factory = factory;
  sf->mediatype = g_strdup (mediatype);
  sf->thumbs_effect = pixbuf;
  sf->length = 500000LL;
  sf->haveeffect = TRUE;
 
  return sf;
}

static GObject *
pitivi_sourcefile_constructor (GType type,
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
pitivi_sourcefile_instance_init (GTypeInstance * instance, gpointer g_class)
{
  PitiviSourceFile *this = (PitiviSourceFile *) instance;

  this->private = g_new0(PitiviSourceFilePrivate, 1);
  /* initialize all public and private members to reasonable default values. */   
  this->private->dispose_has_run = FALSE;
}

static void
pitivi_sourcefile_dispose (GObject *object)
{
  PitiviSourceFile	*this = PITIVI_SOURCEFILE(object);

  /* If dispose did already run, return. */
  if (this->private->dispose_has_run)
    return;

  if (this->private->decode)
    gst_object_unref(GST_OBJECT(this->private->decode));
  if (this->private->audioout)
    gst_object_unref(GST_OBJECT(this->private->audioout));
  if (this->private->videoout)
    gst_object_unref(GST_OBJECT(this->private->videoout));
  if (this->pipeline)
    gst_object_unref(GST_OBJECT(this->pipeline));
  if (this->pipeline_audio)
    gst_object_unref(GST_OBJECT(this->pipeline_audio));
  if (this->pipeline_video)
    gst_object_unref(GST_OBJECT(this->pipeline_video));
  /* Make sure dispose does not run twice. */
  this->private->dispose_has_run = TRUE;	
  G_OBJECT_CLASS (parent_class)->dispose (object);
}

static void
pitivi_sourcefile_finalize (GObject *object)
{
  PitiviSourceFile	*this = PITIVI_SOURCEFILE(object);

  g_printf("pitivi_sourcefile_finalize\n");
  if (this->private->bins)
    g_slist_free(this->private->bins);
  g_free (this->private);
  if (this->filename)
    g_free(this->filename);
  if (this->mediatype)
    g_free(this->mediatype);
  if (this->infovideo)
    g_free(this->infovideo);
  if (this->infoaudio)
    g_free(this->infoaudio);
  if (this->thumbs_audio)
    g_free(this->thumbs_audio);
  if (this->thumbs_video)
    g_free(this->thumbs_video);
  if (this->thumbs_effect)
    g_free(this->thumbs_effect);
  G_OBJECT_CLASS (parent_class)->finalize (object);
}

static void
pitivi_sourcefile_set_property (GObject * object,
			      guint property_id,
			      const GValue * value, GParamSpec * pspec)
{
  PitiviSourceFile *this = (PitiviSourceFile *) object;

  switch (property_id)
    {
    case PROP_FILENAME:
      this->filename = g_value_get_pointer (value);
      break;
    case PROP_MAINAPP:
      this->private->mainapp = g_value_get_pointer (value);
      break;
    default:
      g_assert (FALSE);
      break;
    }
}

static void
pitivi_sourcefile_get_property (GObject * object,
			      guint property_id,
			      GValue * value, GParamSpec * pspec)
{
  PitiviSourceFile *this = (PitiviSourceFile *) object;

  switch (property_id)
    {
    default:
      g_assert (FALSE);
      break;
    }
}

static void
pitivi_sourcefile_class_init (gpointer g_class, gpointer g_class_data)
{
  GObjectClass *gobject_class = G_OBJECT_CLASS (g_class);
  PitiviSourceFileClass *sourcefile_class = PITIVI_SOURCEFILE_CLASS (g_class);

  parent_class = G_OBJECT_CLASS (g_type_class_peek_parent (g_class));

  gobject_class->constructor = pitivi_sourcefile_constructor;
  gobject_class->dispose = pitivi_sourcefile_dispose;
  gobject_class->finalize = pitivi_sourcefile_finalize;

  gobject_class->set_property = pitivi_sourcefile_set_property;
  gobject_class->get_property = pitivi_sourcefile_get_property;

  g_object_class_install_property (G_OBJECT_CLASS (gobject_class), PROP_FILENAME,
				   g_param_spec_pointer ("filename","filename","filename",
							 G_PARAM_READWRITE | G_PARAM_CONSTRUCT));
  
  g_object_class_install_property (G_OBJECT_CLASS (gobject_class), PROP_MAINAPP,
				   g_param_spec_pointer ("mainapp","mainapp","mainapp",
							 G_PARAM_WRITABLE | G_PARAM_CONSTRUCT));
}

GType
pitivi_sourcefile_get_type (void)
{
  static GType type = 0;
 
  if (type == 0)
    {
      static const GTypeInfo info = {
	sizeof (PitiviSourceFileClass),
	NULL,			/* base_init */
	NULL,			/* base_finalize */
	pitivi_sourcefile_class_init,	/* class_init */
	NULL,			/* class_finalize */
	NULL,			/* class_data */
	sizeof (PitiviSourceFile),
	0,			/* n_preallocs */
	pitivi_sourcefile_instance_init	/* instance_init */
      };
      type = g_type_register_static (G_TYPE_OBJECT,
				     "PitiviSourceFileType", &info, 0);
    }

  return type;
}
