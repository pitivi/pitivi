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

#include "pitivi-debug.h"
#include "pitivi-globalbin.h"

/*
  New global GstBin for PLAYING/VIEWING/RECORDING/CAPTURING/TRANSCODING

  Global Properties :
    * Number of raw media streams (Central) (In fact just using 1 audio and 1 video)
    * If we're viewing or not
    * If we're rendering to a file or not

  Source(s) : GstElement with one or more "raw media" pads
  The only thing that interests us is the number of pads.
  The number/type of usable pads is limited by the bin's global settings

  Tee(s) : 
    Always linked to the source pads.
    Linked to the threads depending on the viewing/render modes

  VideoOut/AudioOut : (VisualisationThreads)
    Thread to handle visualisation (Audio or Video)

  EncodingThreads : (VEncThread and AEncThread)
    Threads to handle the encoding of a raw media stream

  Muxer :
    Should be able to receive the number/type of encoded streams

  FileSink :
    Puts the encoded multiplexed streams into a file

  =====================================================================
  Example for Pitivi's Global Thread (1 audio + 1 video)

                       --{ Q--VideoOut }
		      /
  [     Video-]---[Tee]--{ Q--VideoEncoder--Q }--[-Video ]
  [ Timeline  ]                                  [ Muxer-]--[FileSink]
  [	Audio-]---[Tee]--{ Q--AudioEncoder--Q }--[-Audio ]
		      \
		       --{ Q--AudioOut }
 
  =====================================================================
*/

#define GLOBALBIN_CLASS(gbin) PITIVI_GLOBALBIN_CLASS (G_OBJECT_GET_CLASS (gbin))

enum {
  ARG_0,
  ARG_PREVIEW,
  ARG_RENDER,
  ARG_ENCODEDFILE,
  ARG_VIDEOOUT,
  ARG_AUDIOOUT,
  ARG_VENCODER,
  ARG_AENCODER,
  ARG_MUXER
};

static     GstBinClass *parent_class;

struct _PitiviGlobalBinPrivate
{
  /* instance private members */
  gboolean	dispose_has_run;
  
  GstElement	*vtee;
  GstElement	*atee;

  GstElement	*vsinkthread;
  GstElement	*videoqueue;
  gboolean	vsinkeos;
  gulong		vsinkeossignal;

  GstElement	*asinkthread;
  GstElement	*audioqueue;
  gboolean	asinkeos;
  gulong		asinkeossignal;

  GstElement	*vencbin;
  GstElement	*vencthread;
  GstElement	*vencinqueue;
  GstElement	*videoconvert;

  GstElement	*aencbin;
  GstElement	*aencthread;
  GstElement	*aencinqueue;
  GstElement	*audioconvert;

  GstElement	*muxthread;
  GstElement	*vencoutqueue, *aencoutqueue;
  GstElement	*filesink;
  gboolean	filesinkeos;
  gulong		filesinkeossignal;
};

#define ADD_WEAK_POINTER(object) \
 g_object_add_weak_pointer (G_OBJECT(object), (gpointer *) &(object))

#define REMOVE_WEAK_POINTER(object) \
 g_object_remove_weak_pointer (G_OBJECT(object), (gpointer *) &(object))

/*
 * forward definitions
 */

/*
 * Insert "added-value" functions here
 */

/* static void */
/* sink_eos_cb	(GstElement *element, PitiviGlobalBin *gbin) */
/* { */

/*   PITIVI_WARNING ("Sink EOS"); */

/*   if (element == gbin->videoout) */
/*     gbin->private->vsinkeos = TRUE; */
/*   else if (element == gbin->audioout) */
/*     gbin->private->asinkeos = TRUE; */
/*   else if (element == gbin->private->filesink) */
/*     gbin->private->filesinkeos = TRUE; */

/*   if (((gbin->render && gbin->private->filesinkeos) || !gbin->render) */
/*       && ((gbin->preview && gbin->videoout && gbin->private->vsinkeos) || !(gbin->preview && gbin->videoout)) */
/*       && ((gbin->preview && gbin->audioout && gbin->private->asinkeos) || !(gbin->preview && gbin->audioout))) { */
/*     gbin->eos = TRUE; */
/*     gst_element_set_eos (GST_ELEMENT (gbin)); */
/*     /\*     if (!gst_element_set_state (GST_ELEMENT (gbin), GST_STATE_READY)) *\/ */
/*     /\*       PITIVI_WARNING ("ACHTUNG, Can't set the timelinebin to READY !!!"); *\/ */
/*     /\*     else *\/ */
/*     /\*       PITIVI_WARNING ("TimelineBin was put to READY"); *\/ */
/*   } */
/* } */

void
pitivi_globalbin_set_video_output (PitiviGlobalBin *gbin, GstElement *videoout)
{
/*   PITIVI_WARNING ("set_video_output"); */
  if (GST_STATE(GST_ELEMENT(gbin)) > GST_STATE_READY)
    return;
  if (gbin->videoout) {
    /* unlink and remove existing videoout */
    REMOVE_WEAK_POINTER (gbin->videoout);
    gst_element_unlink (gbin->private->videoqueue, gbin->videoout);
/*     g_signal_handler_disconnect (gbin->videoout, gbin->private->vsinkeossignal); */
    gst_bin_remove (GST_BIN (gbin->private->vsinkthread),
		    gbin->videoout);
  }
  gbin->videoout = videoout;
  ADD_WEAK_POINTER (gbin->videoout);
/*   gbin->private->vsinkeossignal =  */
/*     g_signal_connect (G_OBJECT (gbin->videoout), "eos", G_CALLBACK (sink_eos_cb), gbin); */
  gst_bin_add (GST_BIN(gbin->private->vsinkthread),
	       gbin->videoout);
  if (!(gst_element_link (gbin->private->videoqueue, gbin->videoout)))
    PITIVI_WARNING ("Couldn't link videoqueue to videoout\n");
}

void
pitivi_globalbin_set_audio_output (PitiviGlobalBin *gbin, GstElement *audioout)
{
/*   PITIVI_WARNING ("set_audio_output"); */
  if (GST_STATE(GST_ELEMENT(gbin)) > GST_STATE_READY)
    return;
  if (gbin->audioout) {
    /* unlink and remove existing audioout */
    REMOVE_WEAK_POINTER (gbin->audioout);
    gst_element_unlink (gbin->private->audioqueue, gbin->audioout);
/*     g_signal_handler_disconnect (gbin->audioout, gbin->private->asinkeossignal); */
    gst_bin_remove (GST_BIN (gbin->private->asinkthread),
		    gbin->audioout);
  }
  gbin->audioout = audioout;
  ADD_WEAK_POINTER (gbin->audioout);
/*   gbin->private->asinkeossignal =  */
/*     g_signal_connect (G_OBJECT (gbin->audioout), "eos", G_CALLBACK (sink_eos_cb), gbin); */
  gst_bin_add (GST_BIN(gbin->private->asinkthread),
	       gbin->audioout);
  if (!(gst_element_link (gbin->private->audioqueue, gbin->audioout)))
    PITIVI_WARNING ("Couldn't link audioqueue to audioout\n");
}

static void
pitivi_globalbin_set_video_encoder (PitiviGlobalBin *gbin, GstElement *vencoder)
{
/*   PITIVI_WARNING ("Set Video Encoder"); */
  if (GST_STATE(GST_ELEMENT(gbin)) > GST_STATE_READY)
    return;
  if (gbin->vencoder) {
    REMOVE_WEAK_POINTER (gbin->vencoder);
    gst_element_unlink_many (gbin->private->vencinqueue,
			     gbin->vencoder,
			     gbin->private->vencoutqueue,
			     NULL);
    gst_bin_remove (GST_BIN(gbin->private->vencthread),
		    gbin->vencoder);
  }
  gbin->vencoder = vencoder;
  ADD_WEAK_POINTER (gbin->vencoder);
  gst_bin_add (GST_BIN(gbin->private->vencthread),
	       gbin->vencoder);
  gst_element_set_state (gbin->vencoder, GST_STATE_READY);
  if (!(gst_element_link_many (gbin->private->vencinqueue,
			       gbin->vencoder,
			       gbin->private->vencoutqueue,
			       NULL)))
    PITIVI_WARNING ("Couldn't link video encoder and queues\n");
}

static void
pitivi_globalbin_set_audio_encoder (PitiviGlobalBin *gbin, GstElement *aencoder)
{
/*   PITIVI_WARNING ("Set Audio Encoder"); */
  if (GST_STATE(GST_ELEMENT(gbin)) > GST_STATE_READY)
    return;
  if (gbin->aencoder) {
    REMOVE_WEAK_POINTER (gbin->aencoder);
    gst_element_unlink_many (gbin->private->aencinqueue,
			     gbin->private->audioconvert,
			     gbin->aencoder,
			     gbin->private->aencoutqueue,
			     NULL);
    gst_bin_remove (GST_BIN(gbin->private->aencthread),
		    gbin->aencoder);
  }
  gbin->aencoder = aencoder;
  ADD_WEAK_POINTER (gbin->aencoder);
  gst_bin_add (GST_BIN(gbin->private->aencthread),
	       gbin->aencoder);
  gst_element_set_state (gbin->aencoder, GST_STATE_READY);
  if (!(gst_element_link_many (gbin->private->aencinqueue,
			       gbin->private->audioconvert,
			       gbin->aencoder,
			       gbin->private->aencoutqueue,
			       NULL)))
    PITIVI_WARNING ("Couldn't link audio encoder and queues\n");
}

static void
pitivi_globalbin_set_muxer (PitiviGlobalBin *gbin, GstElement *muxer)
{
/*   PITIVI_WARNING ("Set Muxer"); */
  if (GST_STATE(GST_ELEMENT(gbin)) > GST_STATE_READY)
    return;
  if (gbin->muxer) {
    /* TODO : shouldn't we unlink it from encoding threads and filesink ?? */
    REMOVE_WEAK_POINTER (gbin->muxer);
    gst_bin_remove (GST_BIN (gbin->private->muxthread), gbin->muxer);
  }
  gbin->muxer = muxer;
  ADD_WEAK_POINTER (gbin->muxer);
  gst_bin_add (GST_BIN (gbin->private->muxthread), gbin->muxer);
  gst_element_set_state (gbin->muxer, GST_STATE_READY);
}

void
pitivi_globalbin_set_encoded_file (PitiviGlobalBin *gbin, const gchar *filename)
{
/*   PITIVI_WARNING ("Set Encoded file"); */
  if (GST_STATE(GST_ELEMENT(gbin)) > GST_STATE_READY)
    return;
  if (gbin->encodedfile)
    g_free (gbin->encodedfile);
  gbin->encodedfile = g_strdup(filename);

  if (!gbin->private->filesink) {
    gbin->private->filesink = gst_element_factory_make ("filesink", "encodedfilesink");
/*     gbin->private->filesinkeossignal =  */
/*       g_signal_connect (G_OBJECT (gbin->private->filesink), "eos", G_CALLBACK (sink_eos_cb), gbin); */
    gst_bin_add (GST_BIN (gbin->private->muxthread), gbin->private->filesink);
  }

  g_object_set (G_OBJECT (gbin->private->filesink),
		"location", gbin->encodedfile,
		NULL);
}

static void
threads_state_change (GstElement *element, GstElementState pstate, GstElementState state, PitiviGlobalBin *gbin)
{
  PITIVI_WARNING ("threads_state_change %s => %s for %s", 
		  gst_element_state_get_name(pstate),
		  gst_element_state_get_name(state),
		  (element == gbin->private->vsinkthread) ? "vsinkthread" :
		  (element == gbin->private->asinkthread) ? "asinkthread" :
		  (element == gbin->private->vencthread) ? "vencthread" :
		  (element == gbin->private->aencthread) ? "aencthread" :
		  (element == gbin->private->muxthread) ? "muxthread" :
		  (element == gbin->vtee) ? "vtee" :
		  (element == gbin->atee) ? "atee" : "unknown");
}

/*
  _setup()

  Called when going from READY -> PAUSED
  (de)activate the necessary elements
  Should link all the elements correctly
*/

static gboolean
pitivi_globalbin_setup (PitiviGlobalBin *gbin)
{
  PitiviGlobalBinClass	*gbin_class = GLOBALBIN_CLASS (gbin);

  gbin->private->vsinkeos = FALSE;
  gbin->private->asinkeos = FALSE;
  gbin->private->filesinkeos = FALSE;
  gbin->eos = FALSE;
/*   PITIVI_WARNING ("pitivi_globalbin_setup"); */
  if (!(gbin_class->connect_source)) {
    PITIVI_WARNING ("No connect_source() implemented");
    return FALSE;
  }
  /* Connect the source to the tees */
  if (!(gbin_class->connect_source(gbin)))
    return FALSE;

  if (gbin->preview && (gbin->videoout || gbin->audioout)) {
    if (gbin->videoout) {
      if (!(gst_element_link (gbin->vtee, gbin->private->videoqueue)))
	return FALSE;
    } else
      GST_FLAG_SET (gbin->private->vsinkthread, GST_ELEMENT_LOCKED_STATE);
    if (gbin->audioout) {
      if (!(gst_element_link (gbin->atee, gbin->private->audioqueue)))
	return FALSE;
    } else
      GST_FLAG_SET (gbin->private->asinkthread, GST_ELEMENT_LOCKED_STATE);
  } else { /* Don't want preview or no output elements */
/*     PITIVI_WARNING ("locking vsinkthread and asinkthread"); */
    GST_FLAG_SET (gbin->private->vsinkthread, GST_ELEMENT_LOCKED_STATE);
    GST_FLAG_SET (gbin->private->asinkthread, GST_ELEMENT_LOCKED_STATE);
  }
  
  if (gbin->render && (gbin->vencoder || gbin->aencoder) && gbin->muxer && gbin->private->filesink) {
/*     PITIVI_WARNING ("Unlocking muxthread"); */
    GST_FLAG_UNSET (gbin->private->muxthread, GST_ELEMENT_LOCKED_STATE);
    if (gbin->vencoder) {
/*       PITIVI_WARNING ("unlocking vencbin"); */
      GST_FLAG_UNSET (gbin->private->vencbin, GST_ELEMENT_LOCKED_STATE);
      if (!(gst_element_link (gbin->vtee, gbin->private->vencinqueue)))
	return FALSE;
      if (!(gst_element_link (gbin->private->vencoutqueue, gbin->muxer)))
	return FALSE;
    } else {
/*       PITIVI_WARNING ("Locking vencbin"); */
      GST_FLAG_SET (gbin->private->vencbin, GST_ELEMENT_LOCKED_STATE);
    }
    if (gbin->aencoder) {
/*       PITIVI_WARNING ("unlocking aencbin"); */
      GST_FLAG_UNSET (gbin->private->aencbin, GST_ELEMENT_LOCKED_STATE);
      if (!(gst_element_link (gbin->atee, gbin->private->aencinqueue)))
	return FALSE;
      if (!(gst_element_link (gbin->private->aencoutqueue, gbin->muxer)))
	return FALSE;
    } else {
/*       PITIVI_WARNING ("Locking aencbin"); */
      GST_FLAG_SET (gbin->private->aencbin, GST_ELEMENT_LOCKED_STATE);
    }
    if (!(gst_element_link (gbin->muxer, gbin->private->filesink)))
      return FALSE;
  } else {
/*     PITIVI_WARNING ("Locking encoding thread"); */
    GST_FLAG_SET (gbin->private->muxthread, GST_ELEMENT_LOCKED_STATE);
  }
  return TRUE;
}

/*
  _reset()

  Called when going from PAUSED->READY
  Unlock all threads/elements
  unlink all elements that need to be disconnected
*/

static gboolean
pitivi_globalbin_reset (PitiviGlobalBin *gbin)
{
  PitiviGlobalBinClass	*gbin_class = GLOBALBIN_CLASS (gbin);

  PITIVI_WARNING ("pitivi_globalbin_reset");
  /* disconnect source, handled by derivate classes */
  if (!(gbin_class->disconnect_source))
    return FALSE;
  if (!(gbin_class->disconnect_source(gbin)))
    return FALSE;

  if (gbin->preview && (gbin->videoout || gbin->audioout)) {
    if (gbin->videoout)
      gst_element_unlink (gbin->vtee, gbin->private->videoqueue);
    if (gbin->audioout)
      gst_element_unlink (gbin->atee, gbin->private->audioqueue);
  } else {
/*     PITIVI_WARNING ("Unlocking output threads"); */
    GST_FLAG_UNSET (gbin->private->vsinkthread, GST_ELEMENT_LOCKED_STATE);
    GST_FLAG_UNSET (gbin->private->asinkthread, GST_ELEMENT_LOCKED_STATE);
  }

  if (gbin->render && (gbin->vencoder || gbin->aencoder) && gbin->muxer && gbin->private->filesink) {
    if (gbin->vencoder) {
      gst_element_unlink (gbin->vtee, gbin->private->vencinqueue);
      gst_element_unlink (gbin->private->vencoutqueue, gbin->muxer);
    }
    if (gbin->aencoder) {
      gst_element_unlink (gbin->atee, gbin->private->aencinqueue);
      gst_element_unlink (gbin->private->aencoutqueue, gbin->muxer);
    }
    gst_element_unlink (gbin->muxer, gbin->private->filesink);
  } else {
/*     PITIVI_WARNING ("Unlocking encoding threads/bins"); */
    GST_FLAG_UNSET (gbin->private->vencbin, GST_ELEMENT_LOCKED_STATE);
    GST_FLAG_UNSET (gbin->private->aencbin, GST_ELEMENT_LOCKED_STATE);
    GST_FLAG_UNSET (gbin->private->muxthread, GST_ELEMENT_LOCKED_STATE);
  }
/*   PITIVI_WARNING ("pitivi_globalbin_reseted"); */
  gbin->eos = FALSE;
  return TRUE;
}

static GstElementStateReturn
pitivi_globalbin_change_state (GstElement *element)
{
  PitiviGlobalBin	*gbin = PITIVI_GLOBALBIN (element);
  GstElementStateReturn	res = GST_STATE_SUCCESS;
  
  PITIVI_WARNING ("pitivi_globalbin_change_state");
  
  switch (GST_STATE_TRANSITION (element)) {
  case GST_STATE_READY_TO_PAUSED:
    if (!(pitivi_globalbin_setup (PITIVI_GLOBALBIN(element))))
      return GST_STATE_FAILURE;
    break;
  case GST_STATE_PAUSED_TO_READY:
    if (!(pitivi_globalbin_reset (PITIVI_GLOBALBIN(element))))
      return GST_STATE_FAILURE;
    break;
  default:
    break;
  }

  PITIVI_WARNING ("pitivi_globalbin_change_state END");

  if (GST_ELEMENT_CLASS (parent_class)->change_state)
    res = GST_ELEMENT_CLASS (parent_class)->change_state (element);
  PITIVI_INFO ("Returned from parent_class->change_state");
  if (!res)
    return GST_STATE_FAILURE;

  PITIVI_INFO ("Now checking if we're in GST_STATE_PLAYING_TO_PAUSED");
  if ( (GST_STATE_TRANSITION (element) == GST_STATE_PLAYING_TO_PAUSED)
       && ((gbin->render && gbin->private->filesinkeos) || !gbin->render)
       && ((gbin->preview && gbin->videoout && gbin->private->vsinkeos) || !(gbin->preview && gbin->videoout))
       && ((gbin->preview && gbin->audioout && gbin->private->asinkeos) || !(gbin->preview && gbin->audioout))) {
    PITIVI_WARNING ("Global EOS, setting to READY");
    gbin->eos = TRUE;
    gst_element_set_eos (GST_ELEMENT (gbin));
  }
  return res;
}

static GObject *
pitivi_globalbin_constructor (GType type,
			     guint n_construct_properties,
			     GObjectConstructParam * construct_properties)
{
  GObject *obj;
  /* Invoke parent constructor. */
  obj = G_OBJECT_CLASS(parent_class)->constructor (type, n_construct_properties,
						   construct_properties);

  /* do stuff. */

  return obj;
}

static void
pitivi_globalbin_instance_init (GTypeInstance * instance, gpointer g_class)
{
  PitiviGlobalBin *self = (PitiviGlobalBin *) instance;

  self->private = g_new0(PitiviGlobalBinPrivate, 1);
  
  /* initialize all public and private members to reasonable default values. */ 
  
  self->private->dispose_has_run = FALSE;
  
  /* Audio/Video tee(s) */

  self->vtee = gst_element_factory_make ("tee", "vtee");
  g_assert (self->vtee != NULL);
  self->atee = gst_element_factory_make ("tee", "atee");
  g_assert (self->atee != NULL);
  g_signal_connect (G_OBJECT(self->vtee),
		    "state-change", G_CALLBACK(threads_state_change), self);
  g_signal_connect (G_OBJECT(self->atee),
		    "state-change", G_CALLBACK(threads_state_change), self);

  /* Audio/Video visualisation threads */

  self->private->vsinkthread = gst_thread_new ("vsinkthread");
  self->private->asinkthread = gst_thread_new ("asinkthread");
  g_signal_connect (G_OBJECT(self->private->vsinkthread),
		    "state-change", G_CALLBACK(threads_state_change), self);
  g_signal_connect (G_OBJECT(self->private->asinkthread),
		    "state-change", G_CALLBACK(threads_state_change), self);

  self->private->videoqueue = gst_element_factory_make ("queue", "videoqueue");
  self->private->audioqueue = gst_element_factory_make ("queue", "audioqueue");

  gst_bin_add (GST_BIN (self->private->vsinkthread), self->private->videoqueue);
  gst_bin_add (GST_BIN (self->private->asinkthread), self->private->audioqueue);

  self->preview = TRUE;

  /* Encoding threads */

  self->private->vencthread = gst_thread_new ("vencthread");
  self->private->aencthread = gst_thread_new ("aencthread");
  self->private->muxthread = gst_thread_new ("muxthread");
  g_signal_connect (G_OBJECT(self->private->vencthread),
		    "state-change", G_CALLBACK(threads_state_change), self);
  g_signal_connect (G_OBJECT(self->private->aencthread),
		    "state-change", G_CALLBACK(threads_state_change), self);
  g_signal_connect (G_OBJECT(self->private->muxthread),
		    "state-change", G_CALLBACK(threads_state_change), self);

  self->private->vencbin = gst_bin_new ("vencbin");
  self->private->aencbin = gst_bin_new ("aencbin");

/*   self->private->videoconvert = gst_element_factory_make ("ffmpegcolorspace", "videoconvert"); */
  self->private->audioconvert = gst_element_factory_make ("audioconvert", "audioconvert");

  self->private->vencinqueue = gst_element_factory_make ("queue", "vencinqueue");
  gst_bin_add_many (GST_BIN (self->private->vencthread),
		    self->private->vencinqueue,
		    NULL);

  self->private->aencinqueue = gst_element_factory_make ("queue", "aencinqueue");
  gst_bin_add_many (GST_BIN (self->private->aencthread),
		    self->private->aencinqueue,
		    self->private->audioconvert,
		    NULL);

  self->private->vencoutqueue = gst_element_factory_make ("queue", "vencoutqueue");
  self->private->aencoutqueue = gst_element_factory_make ("queue", "aencoutqueue");

/*   g_object_set (G_OBJECT (self->private->vencoutqueue), */
/* 		"max-size-bytes", 300000000, */
/* 		"max-size-time", 10 * GST_SECOND, */
/* 		NULL); */

/*   g_object_set (G_OBJECT (self->private->aencoutqueue), */
/* 		"max-size-bytes", 300000000, */
/* 		"max-size-time", 10 * GST_SECOND, */
/* 		NULL); */

  gst_bin_add_many (GST_BIN (self->private->vencbin),
		    self->private->vencthread,
		    self->private->vencoutqueue,
		    NULL);
  gst_bin_add_many (GST_BIN (self->private->aencbin),
		    self->private->aencthread,
		    self->private->aencoutqueue,
		    NULL);

  gst_bin_add_many (GST_BIN (self->private->muxthread),
		    self->private->vencbin,
		    self->private->aencbin,
		    NULL);

  self->render = FALSE;
  GST_FLAG_SET (self->private->vencbin, GST_ELEMENT_LOCKED_STATE);
  GST_FLAG_SET (self->private->aencbin, GST_ELEMENT_LOCKED_STATE);
  GST_FLAG_SET (self->private->muxthread, GST_ELEMENT_LOCKED_STATE);

  gst_bin_add_many (GST_BIN (self),
		    self->vtee,
		    self->atee,
		    self->private->vsinkthread,
		    self->private->asinkthread,
		    self->private->muxthread,
		    NULL);
}

static void
pitivi_globalbin_dispose (GObject *object)
{
  PitiviGlobalBin	*self = PITIVI_GLOBALBIN(object);

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
pitivi_globalbin_finalize (GObject *object)
{
  PitiviGlobalBin	*self = PITIVI_GLOBALBIN(object);

  /* 
   * Here, complete object destruction. 
   * You might not need to do much... 
   */

  g_free (self->private);
  G_OBJECT_CLASS (parent_class)->finalize (object);
}

static void
pitivi_globalbin_set_property (GObject * object,
			      guint property_id,
			      const GValue * value, GParamSpec * pspec)
{
  PitiviGlobalBin *self = (PitiviGlobalBin *) object;

  switch (property_id)
    {
    case ARG_PREVIEW:
      self->preview = g_value_get_boolean(value);
      break;
    case ARG_RENDER:
      self->render = g_value_get_boolean(value);
      break;
    case ARG_ENCODEDFILE:
      pitivi_globalbin_set_encoded_file (self, g_value_get_string(value));
      break;
    case ARG_VIDEOOUT:
      pitivi_globalbin_set_video_output (self, g_value_get_pointer(value));
      break;
    case ARG_AUDIOOUT:
      pitivi_globalbin_set_audio_output (self, g_value_get_pointer(value));
      break;
    case ARG_VENCODER:
      pitivi_globalbin_set_video_encoder (self, g_value_get_pointer(value));
      break;
    case ARG_AENCODER:
      pitivi_globalbin_set_audio_encoder (self, g_value_get_pointer(value));
      break;
    case ARG_MUXER:
      pitivi_globalbin_set_muxer (self, g_value_get_pointer(value));
      break;

    default:
      G_OBJECT_WARN_INVALID_PROPERTY_ID (object, property_id, pspec);
      break;
    }
}

static void
pitivi_globalbin_get_property (GObject * object,
			      guint property_id,
			      GValue * value, GParamSpec * pspec)
{
  PitiviGlobalBin *self = (PitiviGlobalBin *) object;

  switch (property_id)
    {
    case ARG_PREVIEW:
      g_value_set_boolean(value, self->preview);
      break;
    case ARG_RENDER:
      g_value_set_boolean(value, self->render);
      break;
    case ARG_ENCODEDFILE:
      g_value_set_string(value, self->encodedfile);
      break;
    case ARG_VIDEOOUT:
      g_value_set_pointer(value, self->videoout);
      break;
    case ARG_AUDIOOUT:
      g_value_set_pointer(value, self->audioout);
      break;
    case ARG_VENCODER:
      g_value_set_pointer(value, self->vencoder);
      break;
    case ARG_AENCODER:
      g_value_set_pointer(value, self->aencoder);
      break;
    case ARG_MUXER:
      g_value_set_pointer(value, self->muxer);
      break;

    default:
      G_OBJECT_WARN_INVALID_PROPERTY_ID (object, property_id, pspec);
      break;
    }
}

static void
pitivi_globalbin_class_init (gpointer g_class, gpointer g_class_data)
{
  GObjectClass *gobject_class = G_OBJECT_CLASS (g_class);
  GstElementClass *gstelement_class = GST_ELEMENT_CLASS (g_class);
/*   PitiviGlobalBinClass *klass = PITIVI_GLOBALBIN_CLASS (g_class); */

  parent_class = GST_BIN_CLASS (g_type_class_peek_parent (g_class));

  gobject_class->constructor = pitivi_globalbin_constructor;
  gobject_class->dispose = pitivi_globalbin_dispose;
  gobject_class->finalize = pitivi_globalbin_finalize;

  gobject_class->set_property = pitivi_globalbin_set_property;
  gobject_class->get_property = pitivi_globalbin_get_property;

  gstelement_class->change_state = pitivi_globalbin_change_state;

  g_object_class_install_property (gobject_class, ARG_PREVIEW,
      g_param_spec_boolean("preview", "Preview", "Enables the audio/video preview of the graph",
			   TRUE, G_PARAM_READWRITE));

  g_object_class_install_property (gobject_class, ARG_RENDER,
      g_param_spec_boolean("render", "Render", "Renders/encodes the graph to a file",
			   FALSE, G_PARAM_READWRITE));

  g_object_class_install_property (gobject_class, ARG_ENCODEDFILE,
      g_param_spec_string("encodedfile", "Encoded File", "Location of the file to render/encode to",
			  NULL, G_PARAM_READWRITE));

  g_object_class_install_property (gobject_class, ARG_VIDEOOUT,
      g_param_spec_pointer("videoout", "Video Out", "Video Output/Preview GstElement",
			   G_PARAM_READWRITE));

  g_object_class_install_property (gobject_class, ARG_AUDIOOUT,
      g_param_spec_pointer("audioout", "Audio Out", "Audio Output/Preview GstElement",
			   G_PARAM_READWRITE));

  g_object_class_install_property (gobject_class, ARG_VENCODER,
      g_param_spec_pointer("vencoder", "Video Encoder", "Video encoding GstElement",
			   G_PARAM_READWRITE));

  g_object_class_install_property (gobject_class, ARG_AENCODER,
      g_param_spec_pointer("aencoder", "Audio Encoder", "Audio encoding GstElement",
			   G_PARAM_READWRITE));

  g_object_class_install_property (gobject_class, ARG_MUXER,
      g_param_spec_pointer("muxer", "Muxer", "Encoding muxer GstElement",
			   G_PARAM_READWRITE));

}

GType
pitivi_globalbin_get_type (void)
{
  static GType type = 0;
 
  if (type == 0)
    {
      static const GTypeInfo info = {
	sizeof (PitiviGlobalBinClass),
	NULL,			/* base_init */
	NULL,			/* base_finalize */
	pitivi_globalbin_class_init,	/* class_init */
	NULL,			/* class_finalize */
	NULL,			/* class_data */
	sizeof (PitiviGlobalBin),
	0,			/* n_preallocs */
	pitivi_globalbin_instance_init	/* instance_init */
      };
      type = g_type_register_static (GST_TYPE_BIN,
				     "PitiviGlobalBin", &info, 0);
    }

  return type;
}
