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

#include <unistd.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>

#include "pitivi.h"
#include "pitivi-sourcefile.h"
#include "pitivi-sourcefilebin.h"
#include "pitivi-settings.h"
#include "pitivi-mainapp.h"
#include "pitivi-debug.h"

static  GObjectClass *parent_class;


typedef struct {
  gchar	*filename;
  gint64	time;
}	PitiviThumbCache;

struct _PitiviSourceFilePrivate
{
  /* instance private members */
  gboolean	dispose_has_run;

  /* List of exported bins */
  GSList	*bins;

  /* used during initial setup */
  GstElement	*decode;
  GstPad	*audiopad;
  GstElement	*audioout;
  GstPad	*videopad;
  GstElement	*videoout;
  GstElement	*videoscale;
  GstElement	*colorspace;
  GstElement	*pngenc;
  
  /* Used for "effect" sourcefile */
  GstElementFactory	*factory;

  /* audio video properties */
  int	vwidth, vheight;
  gdouble	framerate;
  int	awidth, arate, achanns;

  /* cache */
  gchar		*vthumb_path_root;
  PitiviThumbTab	**vthumb;
  PitiviThumbCache	**vcache;
  /* index of last frame captured */
  gint		cacheidx;

  /* transition */
  gint		transitionid;

  /* time of next frame/buf to cache */
  gint64	vlastcaptured;
  gint64	alastcaptured;

  gint		lastsinkid;

  PitiviMainApp *mainapp;
};


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
g_tablen (gchar **tab)
{
  int	i;

  for (i = 0; tab[i]; i++);
  return i;
}

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
    return g_strdup_printf("%dx%d\n%g fps", width, height, framerate);
  }
  if (!g_ascii_strncasecmp("audio", gst_structure_get_name(struc), 5)) {
    gint	width, rate, channels;
    
    gst_structure_get_int(struc, "width", &width);
    gst_structure_get_int(struc, "rate", &rate);
    gst_structure_get_int(struc, "channels", &channels);
    return g_strdup_printf("%d x %dHz\n%d bit", channels, rate, width);
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
  else
    return;
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
  
/*   if (self->haveaudio) */
  if (self->private->audiopad)
    if (!(gst_pad_query(GST_PAD (GST_PAD_REALIZE (self->private->audiopad)),
			GST_QUERY_TOTAL, &format, &lena)))
      lena = 0;
  format = GST_FORMAT_TIME;
/*   if (self->havevideo) */
  if (self->private->videopad)
    if (!(gst_pad_query(GST_PAD (GST_PAD_REALIZE (self->private->videopad)),
			GST_QUERY_TOTAL, &format, &lenv)))
      lenv = 0;
  self->length = MAX(lena, lenv);
}

int
pitivi_sourcefile_store_pad (PitiviSourceFile *sf, GstPad *pad)
{
  gint		type;
  
  type = get_pad_type (pad);
  if (!type)
    return 0;
  if (type == IS_AUDIO) {
    if (sf->private->audiopad) {
/*       g_warning ("More than one audiopad in %s", sf->filename); */
      return 0;
    }
    sf->private->audiopad = pad;
    return IS_AUDIO;
  }
  if (type == IS_VIDEO) {
    if (sf->private->videopad) {
/*       g_warning ("More than one videopad in %s", sf->filename); */
      return 0;
    }
    sf->private->videopad = pad;
    return IS_VIDEO;
  }
  return 0;
}

/* void */
/* audio_handoff_cb (GstElement *element, GstBuffer *buf, GstPad *pad, gpointer udata) */
/* { */
/*   g_printf ("audio_handoff_cb\n"); */
/* } */

void
video_handoff_cb (GstElement *element, GstBuffer *buf, GstPad *pad, gpointer udata)
{
  PitiviSourceFile	*sf = (PitiviSourceFile *) udata;

  /* Find out if we need to record this buffer */
  if (!sf->length) {
    establish_length (sf);
  }
  if ((GST_CLOCK_TIME_IS_VALID(GST_BUFFER_TIMESTAMP(buf))) 
      && (GST_BUFFER_TIMESTAMP(buf) >= sf->private->vlastcaptured) &&
      (GST_BUFFER_TIMESTAMP(buf) >= 0)) {
    gchar	*filename;
    int		fd;
    /* Use vthumb path root */
    filename = g_strdup_printf ("%s-%020lld.png",
				sf->private->vthumb_path_root,
				(signed long long int) GST_BUFFER_TIMESTAMP(buf));
/*     g_printf ("Recording video thumbnail to file %s\n", filename); */
    fd = open ((const char *) filename,
	       O_CREAT | O_RDWR | O_TRUNC,
	       S_IRUSR | S_IWUSR);
    if (fd == -1)
      g_error ("couldn't open file %s !!", filename);
    
    write (fd, GST_BUFFER_DATA(buf), GST_BUFFER_SIZE(buf));
    
    close (fd);
    sf->private->vlastcaptured += sf->vthumb_interval;

    if (!sf->private->vcache)
      sf->private->vcache = g_new0(PitiviThumbCache *, (int) (sf->length / sf->vthumb_interval) + 1);
    sf->private->vcache[sf->private->cacheidx] = g_new0(PitiviThumbCache, 1);
    sf->private->vcache[sf->private->cacheidx]->filename = filename;
    sf->private->vcache[sf->private->cacheidx]->time = GST_BUFFER_TIMESTAMP(buf);
    sf->private->cacheidx++;
  }
  /* If audio caps is not fixed, carry on normally */
  if (sf->private->audiopad && (gst_caps_is_fixed(gst_pad_get_caps(sf->private->audiopad))))
    if (sf->private->vlastcaptured < sf->length) {
      if (!(gst_element_seek (element, GST_FORMAT_TIME | GST_SEEK_METHOD_SET | GST_SEEK_FLAG_FLUSH,
			      sf->private->vlastcaptured)))
	g_warning ("Error seeking to %lld\n", (signed long long int) sf->private->vlastcaptured);
    }
}

void
new_decoded_pad_cb (GstElement * element, GstPad * pad, gboolean last, gpointer udata)
{
  PitiviSourceFile	*sf = PITIVI_SOURCEFILE (udata);
  GstElement	*sink;
  char	*tmp;
  int	type;

/*   g_printf ("new_decoded_pad, pad %s:%s caps=%s\n", */
/* 	    GST_DEBUG_PAD_NAME (pad), */
/* 	    gst_caps_to_string (gst_pad_get_caps(pad))); */
  if (!(type = pitivi_sourcefile_store_pad (sf, pad)))
    return;
  /* Stick a fakesink to the pad */
  /* TODO : Should stick the correct converters/cache sink */

  tmp = g_strdup_printf("fakesink%d", sf->private->lastsinkid++);
  sink = gst_element_factory_make ("fakesink", tmp);
  g_object_set (sink, "signal-handoffs", TRUE, NULL);

  gst_element_set_state(sf->pipeline, GST_STATE_PAUSED); 

  gst_bin_add(GST_BIN (sf->pipeline), sink);

  if (type == IS_AUDIO) 
    {
/*       g_signal_connect (sink, "handoff", G_CALLBACK (audio_handoff_cb), sf); */
      if (!(gst_element_link(element, sink)))
	g_warning ("Couldn't link fakesink...\n");
      sf->private->audioout = sink;
    } 
  else 
    {
      sf->private->colorspace = gst_element_factory_make ("ffcolorspace", "cspace");
      sf->private->videoscale = gst_element_factory_make ("videoscale", "vscale");
      sf->private->pngenc = gst_element_factory_make ("pngenc", "pngenc");
      g_object_set (sf->private->pngenc, "snapshot", FALSE, NULL);
      sf->private->cacheidx = 0;

      gst_bin_add_many (GST_BIN (sf->pipeline),
			sf->private->colorspace,
			sf->private->videoscale,
			sf->private->pngenc,
			NULL);
      gst_element_link_many (element, sf->private->colorspace , sf->private->videoscale, NULL);
      gst_element_link_filtered (sf->private->videoscale, sf->private->pngenc,
				 gst_caps_from_string ("video/x-raw-rgb,width=48,height=48"));
      gst_element_link (sf->private->pngenc, sink);

      g_signal_connect (sink, "handoff", G_CALLBACK (video_handoff_cb), sf);
      sf->private->videoout = sink;
    }
  gst_element_set_state(sf->pipeline, GST_STATE_PLAYING); 
  g_free(tmp);  
}

/* void */
/* unknown_type_cb (GstElement * element, GstCaps *caps, gpointer udata) */
/* { */
/*   g_printf("Unknown pad : %s\n", gst_caps_to_string(caps)); */
/* } */

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
  gulong	ndhandler;
/*   gulong	uhandler; */

  tmp = g_strdup_printf ("filesrc name=src location=\"%s\" ! decodebin name=dbin",
			 self->filename);
  self->pipeline = gst_parse_launch (tmp, &error);
  g_assert (self->pipeline != NULL);
  g_assert (error == NULL);
  g_free(tmp);

  self->private->decode = gst_bin_get_by_name (GST_BIN(self->pipeline), "dbin");
  ndhandler = g_signal_connect(self->private->decode, "new-decoded-pad", G_CALLBACK (new_decoded_pad_cb), self);
/*   unhandler = g_signal_connect(self->private->decode, "unknown-type", G_CALLBACK (unknown_type_cb), self); */

  if (!(gst_element_set_state (self->pipeline, GST_STATE_PLAYING))) return;
  
  for (i = 1000; i--; ) {
    if (!(gst_bin_iterate(GST_BIN(self->pipeline))))
      break;
  }

  g_signal_handler_disconnect (self->private->decode, ndhandler);
/*   g_signal_handler_disconnect (self->private->decode, unhandler); */
  if (self->private->videopad && gst_caps_is_fixed(gst_pad_get_caps(self->private->videopad))) {
    self->havevideo = TRUE;
    record_pad_info(self, IS_VIDEO, self->private->videopad);
  } 
  if (self->private->audiopad && gst_caps_is_fixed(gst_pad_get_caps(self->private->audiopad))) {
    self->haveaudio = TRUE;
    record_pad_info(self, IS_AUDIO, self->private->audiopad);
  }

  /* remove elements from bin */
  if (self->private->audioout) {
    gst_element_unlink(self->private->decode, self->private->audioout);
    gst_bin_remove(GST_BIN(self->pipeline), self->private->audioout);
    self->private->audioout = NULL;
  }
  if (self->private->videoout) {
    gst_element_unlink_many (self->private->decode, self->private->videoout,
			     self->private->colorspace, self->private->videoscale,
			     self->private->pngenc, NULL);
    gst_bin_remove_many (GST_BIN(self->pipeline), self->private->videoout,
			 self->private->colorspace, self->private->videoscale,
			 self->private->pngenc, NULL);
    self->private->videoout = NULL;
  }

  self->private->vthumb = g_new0(PitiviThumbTab *, self->private->cacheidx);
  
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
  else if (this->haveaudio)
    this->mediatype = g_strdup("audio");
}

void
bin_was_freed(gpointer udata, GObject *object)
{
  PitiviSourceFile	*self = PITIVI_SOURCEFILE(udata);

/*   g_printf("!!BIN WAS FREED !!\n"); */
  self->private->bins = g_slist_remove(self->private->bins, object);
  self->nbbins--;
}

/**
 * pitivi_sourcefile_get_first_thumb:
 * @sf:
 *
 * Returns: The first thumbnail if it's available, NULL otherwise.
 */

GdkPixbuf *
pitivi_sourcefile_get_first_thumb (PitiviSourceFile *sf)
{
  return (pitivi_sourcefile_get_thumb_at (sf, 0));
}

GdkPixbuf *
pitivi_sourcefile_get_thumb_at (PitiviSourceFile *sf, gint nb)
{
  if (!sf->private->cacheidx || nb > sf->private->cacheidx)
    return NULL;
  if (!sf->private->vthumb[nb]) {
    sf->private->vthumb[nb] = g_new0(PitiviThumbTab, 1);
    sf->private->vthumb[nb]->time = sf->private->vcache[nb]->time;
    if (!(sf->private->vthumb[nb]->pixbuf = gdk_pixbuf_new_from_file(sf->private->vcache[nb]->filename, NULL)))
      g_warning ("Error getting file %s", sf->private->vcache[nb]->filename);
  }
  return sf->private->vthumb[nb]->pixbuf;
}

/**
 * pitivi_sourcefile_get_vthumb:
 * @sf: The #PitiviSourceFile
 * @start: The position from which we want thumbnails
 * @stop: The position to which we want thumbnails
 *
 * Returns: A table of #PitiviThumbTab pointers starting from @start. The table will
 * start with the first thumbnail AT or AFTER @start. The table is garanteed to have
 * PitiviThumbTab up to (but not including) stop. Returns NULL if there is no 
 * thumbnail (AT or AFTER start) AND (before stop).
 */

PitiviThumbTab **
pitivi_sourcefile_get_vthumb (PitiviSourceFile *sf, gint64 start, gint64 stop)
{
  int	i = 0;
  PitiviThumbTab	**res = NULL;

  sf->nbthumbs = sf->private->cacheidx;
  if (stop > sf->length)
    stop = sf->length;
  while (i < sf->private->cacheidx && sf->private->vcache[i]) {
    if ((sf->private->vcache[i]->time >= start) && (sf->private->vcache[i]->time < stop)) {
      /* valid thumbnail */
      if (!sf->private->vthumb[i]) {
	sf->private->vthumb[i] = g_new0(PitiviThumbTab, 1);
	sf->private->vthumb[i]->time = sf->private->vcache[i]->time;
/* 	g_printf ("filename:%s\n", sf->private->vcache[i]->filename); */
	if (sf->private->vcache[i]->filename)
	  if (!(sf->private->vthumb[i]->pixbuf = gdk_pixbuf_new_from_file(sf->private->vcache[i]->filename, NULL)))
	    g_warning ("Error getting file %s", sf->private->vcache[i]->filename);
      }
      if (!res) /* Setting first one */
	res = &(sf->private->vthumb[i]);
    } else if (sf->private->vcache[i]->time >= stop)
      break; /* went too far */
    i++;
  }
  return res;
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

  if (sf->haveeffect)
    return NULL;
  res = pitivi_sourcefile_bin_new (sf, IS_AUDIO_VIDEO, sf->private->mainapp);
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

  if (!sf->haveaudio)
    return NULL;
  res = pitivi_sourcefile_bin_new (sf, IS_AUDIO, sf->private->mainapp);
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

  if (!sf->havevideo)
    return NULL;
  res = pitivi_sourcefile_bin_new (sf, IS_VIDEO, sf->private->mainapp);
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

  if (!sf->haveeffect)
    return NULL;
  tmp = g_strdup_printf ("%s-%d", sf->filename, sf->private->lastsinkid++);
  res = gst_element_factory_create (sf->private->factory, tmp);
  g_free (tmp);
  if (sf->private->transitionid)
    g_object_set (G_OBJECT (res), "type", sf->private->transitionid, NULL);
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
  gchar			**tab;

  sourcefile = (PitiviSourceFile *) g_object_new(PITIVI_SOURCEFILE_TYPE,
						 "filename",
						 filename,
						 "mainapp",
						 mainapp,
						 NULL);
  g_assert(sourcefile != NULL);

  tab = g_strsplit (filename, "/", 0);
  sourcefile->private->vthumb_path_root = g_strdup_printf ("/tmp/%s", tab[g_tablen(tab) - 1]);
  g_strfreev(tab);

  pitivi_sourcefile_type_find (sourcefile);
  
  if ((!sourcefile->haveaudio) && (!sourcefile->havevideo)) {
    g_object_unref (sourcefile);
    return NULL;
  }

  sourcefile->pipeline = pitivi_sourcefile_bin_new (sourcefile, IS_AUDIO_VIDEO, sourcefile->private->mainapp);
  sourcefile->thumbs = pitivi_sourcefile_get_vthumb (sourcefile, 0LL, sourcefile->length);
  return sourcefile;
}

/**
 * pitivi_sourcefile_new_transition:
 * @name: The name of the transition
 * @factory: The #GstElementFactory for the effect,
 * @pixbuf: The #GdkPixbuf used for this effect
 * mediatyp: The media type (transition or effect)
 * transitionid: The SMPTE id of the transition
 * @mainapp: The #PitiviMainApp
 *
 * Returns: A newly-allocated #PitiviSourceFile
 */

PitiviSourceFile *
pitivi_sourcefile_new_transition (gchar *name, GstElementFactory *factory, GdkPixbuf *pixbuf,
				  gchar *mediatype, gint transitionid, PitiviMainApp *mainapp)
{
  PitiviSourceFile	*sf;

  sf = (PitiviSourceFile *) g_object_new(PITIVI_SOURCEFILE_TYPE,
					 "mainapp", mainapp,
					 NULL);
  g_assert (sf != NULL);
  sf->filename = g_strdup (name);
  sf->pipeline = NULL;
  sf->private->factory = factory;
  sf->mediatype = g_strdup (mediatype);
  sf->thumbs_effect = pixbuf;
  sf->length = DEFAULT_EFFECT_LENGTH;
  sf->haveeffect = TRUE;
  sf->private->transitionid = transitionid;

  return sf;
}

/**
 * Pitivi_sourcefile_new_effect:
 * @name: The name of the effect
 * @factory: The #GstElementFactory for the effect,
 * @pixbuf: The #GdkPixbuf used for this effect
 * mediatyp: The media type (transition or effect)
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
  sf->length = DEFAULT_EFFECT_LENGTH;
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

  this->vthumb_interval = GST_SECOND;
  this->athumb_interval = GST_SECOND / 10;

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
  /* Make sure dispose does not run twice. */
  this->private->dispose_has_run = TRUE;	
  G_OBJECT_CLASS (parent_class)->dispose (object);
}

static void
pitivi_sourcefile_finalize (GObject *object)
{
  PitiviSourceFile	*this = PITIVI_SOURCEFILE(object);

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
    case PROP_FILENAME:
      g_value_set_pointer (value, this->filename);
      break;
    case PROP_MAINAPP:
      g_value_set_pointer (value, this->private->mainapp);
      break;
    default:
      g_assert (FALSE);
      break;
    }
}

static void
pitivi_sourcefile_class_init (gpointer g_class, gpointer g_class_data)
{
  GObjectClass *gobject_class = G_OBJECT_CLASS (g_class);
/*   PitiviSourceFileClass *sourcefile_class = PITIVI_SOURCEFILE_CLASS (g_class); */

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
