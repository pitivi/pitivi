/* 
 * PiTiVi
 * Copyright (C) <2004>		Edward Hervey <bilboed@bilboed.com>
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
#include "pitivi-sourcefilebin.h"

static gchar *
gst_event_get_name (GstEvent *event)
{
  switch (GST_EVENT_TYPE (event)) {
  case GST_EVENT_EOS:
    return "GST_EVENT_EOS";
  case GST_EVENT_FLUSH:
    return "GST_EVENT_FLUSH";
  case GST_EVENT_EMPTY:
    return "GST_EVENT_EMPTY";
  case GST_EVENT_DISCONTINUOUS:
    return "GST_EVENT_DISCONTINUOUS";
  case GST_EVENT_QOS:
    return "GST_EVENT_QOS";
  case GST_EVENT_SEEK:
    return "GST_EVENT_SEEK";
  case GST_EVENT_SEEK_SEGMENT:
    return "GST_EVENT_SEEK_SEGMENT";
  case GST_EVENT_SEGMENT_DONE:
    return "GST_EVENT_SEGMENT_DONE";
  case GST_EVENT_SIZE:
    return "GST_EVENT_SIZE";
  case GST_EVENT_RATE:
    return "GST_EVENT_RATE";
  case GST_EVENT_FILLER:
    return "GST_EVENT_FILLER";
  case GST_EVENT_TS_OFFSET:
    return "GST_EVENT_TS_OFFSET";
  case GST_EVENT_INTERRUPT:
    return "GST_EVENT_INTERRUPT";
  case GST_EVENT_NAVIGATION:
    return "GST_EVENT_NAVIGATION";
  case GST_EVENT_TAG:
    return "GST_EVENT_TAG";
  case GST_EVENT_UNKNOWN:
  default:
    return "GST_EVENT_UNKNOWN";
  };
  return "REALLY UNKNOWN EVENT";
}

gboolean
testprobe (GstProbe *probe, GstData **data, gpointer pad)
{
  if (GST_IS_EVENT(*data))
    g_printf ("Pad %s:%s got an event %s\n",
	      GST_DEBUG_PAD_NAME(GST_PAD(pad)),
	      gst_event_get_name(GST_EVENT(*data)));
  else
    g_printf ("Pad %s:%s got buffer %03lld:%02lld:%03lld\n",
	      GST_DEBUG_PAD_NAME(GST_PAD(pad)),
	      GST_M_S_M(GST_BUFFER_TIMESTAMP(*data)));
  return TRUE;
}

void
bin_notify (GObject *object, GParamSpec *param, gpointer data)
{
  g_printf ("Property %s changed in bin\n",
	    param->name);
}

GstElement *
bin_make_new_audiobin (gchar *name, GstCaps *caps)
{
  GstElement	*bin;
  GstElement	*arate, *aconv, *ident;

  bin = gst_bin_new (name);
  arate = gst_element_factory_make ("audioscale", NULL);
  aconv = gst_element_factory_make ("audioconvert", NULL);
  ident = gst_element_factory_make ("identity", NULL);

  gst_bin_add_many (GST_BIN(bin),
		    arate, aconv, ident, NULL);
  if (!(gst_element_link_many( aconv, arate, NULL)))
    PITIVI_WARNING ("Unable to link elements in audiobin");
  if (!(gst_element_link_filtered(arate, ident, caps)))
    PITIVI_WARNING ("Couldn't link audioconv to ident with caps!");
  gst_element_add_ghost_pad (GST_ELEMENT(bin),
			     gst_element_get_pad (aconv, "sink"),
			     "sink");
  gst_element_add_ghost_pad (GST_ELEMENT(bin),
			     gst_element_get_pad (ident, "src"),
			     "src");

  return bin;
}

GstElement *
bin_make_new_videobin (gchar *name, GstCaps *caps)
{
  GstElement	*bin;
  GstElement	*vscale, *cspace, *identity;
  GstElement	*vrate;
/*   GstProbe	*probe, *probe4; */

  /* dbin ! videorate ! videoscale ! ffmpegcolorspace ! videocaps ! identity ! */

  bin = gst_bin_new (name);
  vrate = gst_element_factory_make ("videorate", NULL);
  vscale = gst_element_factory_make ("videoscale", NULL);
  cspace = gst_element_factory_make ("ffmpegcolorspace", NULL);
  /* TODO : Think about moving from identity to queue */
  identity = gst_element_factory_make ("identity", NULL);

  g_signal_connect (G_OBJECT(bin), "notify", G_CALLBACK(bin_notify), NULL);

/*   probe = gst_probe_new (FALSE, testprobe, gst_element_get_pad(vrate, "sink")); */
/*   gst_pad_add_probe (gst_element_get_pad(vrate, "sink"), probe); */

/*   probe5 = gst_probe_new (FALSE, testprobe, gst_element_get_pad(vrate, "src")); */
/*   gst_pad_add_probe (gst_element_get_pad(vrate, "src"), probe5); */

/*   probe2 = gst_probe_new (FALSE, testprobe, gst_element_get_pad(vscale, "sink")); */
/*   gst_pad_add_probe (gst_element_get_pad(vscale, "sink"), probe2); */

/*   probe3 = gst_probe_new (FALSE, testprobe, gst_element_get_pad(cspace, "sink")); */
/*   gst_pad_add_probe (gst_element_get_pad(cspace, "sink"), probe3); */
  
/*   probe4 = gst_probe_new (FALSE, testprobe, gst_element_get_pad(identity, "src")); */
/*   gst_pad_add_probe (gst_element_get_pad(identity, "src"), probe4); */
  
  gst_bin_add_many (GST_BIN (bin),
		    vrate, vscale, cspace, identity,
		    NULL);
  if (!(gst_element_link_many (vrate, vscale, cspace, NULL)))
    PITIVI_WARNING("Error linking vrate, vscale and cspace");
  if (!(gst_element_link_filtered(cspace, identity, caps)))
    PITIVI_WARNING ("Couldn't link filtered colorspace->identity with caps %s",
	       gst_caps_to_string(caps));
  gst_element_add_ghost_pad (bin, gst_element_get_pad (identity, "src"), "src");
  gst_element_add_ghost_pad (bin, gst_element_get_pad (vrate, "sink"), "sink");

  return bin;
}

void
bin_add_audiobin (bindata *data)
{
  gchar	*tmp;
  PitiviMediaSettings *ms;
  GSList	*lst;

  if (data->audiobin)
    return;
  lst = g_slist_next(data->mainapp->project->settings->media_settings);
  ms = lst->data;
  tmp = g_strdup_printf ("audiobin_%s", data->sf->filename);
  data->audiobin = bin_make_new_audiobin (tmp, ms->caps);
  g_free(tmp);
  gst_bin_add (GST_BIN (data->bin), data->audiobin);

  if (data->bintype == IS_AUDIO_VIDEO) {
    if (!(gst_element_add_ghost_pad (data->bin,
				     gst_element_get_pad (data->audiobin, "src"), "asrc")))
      PITIVI_WARNING ("problem adding audio ghost pad to bin");
  } else {
    if (!(gst_element_add_ghost_pad (data->bin,
				     gst_element_get_pad (data->audiobin, "src"), "src")))
      PITIVI_WARNING ("problem adding audio ghost pad to bin");
  }
}

void
bin_add_videobin (bindata *data)
{
  if (!data->videobin) {
    gchar	*tmp;
    PitiviMediaSettings	*ms;
    
    ms = data->mainapp->project->settings->media_settings->data;
    tmp = g_strdup_printf ("videobin_%s", data->sf->filename);
    data->videobin = bin_make_new_videobin (tmp, ms->caps);
    g_free (tmp);
    gst_bin_add (GST_BIN (data->bin), data->videobin);

    if (data->bintype == IS_AUDIO_VIDEO) {
      if (!(gst_element_add_ghost_pad (data->bin, 
				       gst_element_get_pad(data->videobin, "src"), "vsrc")))
	PITIVI_WARNING ("problem adding video ghost pad to bin");
    } else {
      if (!(gst_element_add_ghost_pad (data->bin, 
				       gst_element_get_pad(data->videobin, "src"), "src")))
	PITIVI_WARNING ("problem adding video ghost pad to bin");
    }
  }
}

void
bin_new_pad_fake_output (GstPad *pad, bindata *data, int padtype)
{
  GstElement	*sink;
  char		*tmp;

  if (((padtype == IS_AUDIO) && (!data->audiofakesink))
      || ((padtype == IS_VIDEO) && (!data->videofakesink))) {
    tmp = g_strdup_printf("fakesink%d", data->lastsinkid++);
    sink = gst_element_factory_make ("fakesink", tmp);
    g_free(tmp);
    gst_bin_add(GST_BIN (data->bin), sink);
    if (padtype == IS_AUDIO)
      data->audiofakesink = sink;
    else
      data->videofakesink = sink;
  } else
    if (padtype == IS_AUDIO)
      sink = data->audiofakesink;
    else
      sink = data->videofakesink;

  if (!(gst_pad_link(pad, gst_element_get_pad(sink, "sink"))))
    PITIVI_WARNING("Error linking decodebin pad to fakesink !!!");
}

void
bin_new_pad_audio_output (GstPad *pad, bindata *data)
{
  /* TODO : Add the audio adapters */
  /* TODO : Make it in such a way that it re-uses existing data->audiobin */
  PITIVI_DEBUG ("New Pad Audio Output for pad %s:%s",
	    GST_DEBUG_PAD_NAME (pad));
  if (!(gst_pad_link (pad, gst_element_get_pad (data->audiobin, "sink"))))
    PITIVI_WARNING ("Couldn't link pad %s:%s to audiobin sink",
	       GST_DEBUG_PAD_NAME (pad));
/*   if (data->bintype == IS_AUDIO_VIDEO) */
/*     gst_element_add_ghost_pad (data->bin, pad, "asrc"); */
/*   else */
/*     gst_element_add_ghost_pad (data->bin, pad, "src"); */
}

void
bin_new_pad_video_output (GstPad *pad, bindata *data)
{  
  PITIVI_DEBUG ("New Pad Video Output for pad %s:%s",
		GST_DEBUG_PAD_NAME (pad));
  if (!(gst_pad_link (pad, gst_element_get_pad (data->videobin, "sink"))))
    PITIVI_WARNING ("Couldn't link pad %s:%s to videobin sink",
	       GST_DEBUG_PAD_NAME (pad));
}

/* bin_new_pad_cb , callback used by outgoing bins when there's a new pad */

void
bin_new_pad_cb (GstElement * element, GstPad * pad, gboolean last, gpointer udata)
{
  gint	padtype;
  bindata	*data = (bindata *) udata;
  
  padtype = get_pad_type (pad);
  if (!padtype)
    return;
  PITIVI_DEBUG("Adding pad type[%d]->[%d] : %s:%s", padtype, data->bintype, GST_DEBUG_PAD_NAME(pad));

  /* Connect (adapters and) ghost pads */
  if (padtype == IS_AUDIO) {
    if (data->bintype != IS_VIDEO)
      bin_new_pad_audio_output (pad, data);
    else
      bin_new_pad_fake_output (pad, data, padtype);

    gst_bin_sync_children_state (GST_BIN(data->bin));
    data->audioready = TRUE;
  } else if (padtype == IS_VIDEO) {
    if (data->bintype != IS_AUDIO)
      bin_new_pad_video_output (pad, data);
    else
      bin_new_pad_fake_output (pad, data, padtype);

    gst_bin_sync_children_state (GST_BIN(data->bin));
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

void
bin_add_outputbins (bindata *data)
{
  /* Add audio outputbin */
  /* TODO implement */
  /* Add video outputbin */
  if ((data->sf->havevideo) && (data->bintype != IS_AUDIO))
    bin_add_videobin (data);
  if ((data->sf->haveaudio) && (data->bintype != IS_VIDEO))
    bin_add_audiobin (data);
}

void
bin_preroll (GstElement *container, bindata *data)
{
  gint	i = 1000;
  GstElement	*father;
  GstElement	*pipeline;
  GstElementState	pstate = GST_STATE_READY;
  gboolean	hadfather = FALSE;

  pipeline = gst_pipeline_new(NULL);
  pstate = gst_element_get_state (data->bin);
/*   PITIVI_DEBUG ("Element was in state %s", gst_element_state_get_name(pstate)); */
  if ((father = (GstElement *) gst_object_get_parent (GST_OBJECT(data->bin)))) {
    /* remove it from father */
    hadfather = TRUE;
    gst_object_ref (GST_OBJECT(data->bin));
    gst_bin_remove (GST_BIN (father), data->bin);
  }

  gst_bin_add (GST_BIN (pipeline), data->bin);

  data->ready = data->audioready = data->videoready = FALSE;
  
  if (!(gst_element_set_state (pipeline, GST_STATE_PLAYING)))
    PITIVI_WARNING ("couldn't set bin to PLAYING during pre_roll");
  
  while (i--) {
    if (!(gst_bin_iterate(GST_BIN(pipeline))))
      break;
    if (data->ready)
      break;
  }  

  if (!(gst_element_set_state (pipeline, pstate)))
    PITIVI_WARNING ("couldn't set bin to PLAYING during pre_roll");
  
  gst_object_ref (GST_OBJECT(data->bin));
  gst_bin_remove (GST_BIN (pipeline), data->bin);
  
/*   PITIVI_DEBUG ("Element after pre-roll is in state %s\n", */
/* 	    gst_element_state_get_name (gst_element_get_state (data->bin))); */
  gst_element_set_state (data->bin, pstate);
  if (hadfather) {
    gst_bin_add (GST_BIN(father), data->bin);
/*     gst_object_unref (GST_OBJECT(data->bin)); */
  }
}

/* void */
/* decodebin_change_state (GstElement *element, GstElementState pstate, GstElementState state, bindata *data) */
/* { */
/*   PITIVI_WARNING ("Bin for file %s went from state %d to state %d", */
/* 	     data->sf->filename, pstate, state); */
/*   if ((pstate == GST_STATE_READY) && (state == GST_STATE_PAUSED)) */
/*     bin_preroll(element, data); */
/*   /\* pre-roll data on READY->PAUSED *\/ */
/* } */

/* void */
/* decodebin_eos (GstElement *element, bindata *data) */
/* { */
/*   PITIVI_WARNING ("decodebin for file %s went EOS !", */
/* 	     data->sf->filename); */
/* } */

/* void */
/* decodebin_pad_removed (GstElement *element, GstPad *pad, bindata *data) */
/* { */
/*   PITIVI_WARNING ("pad %s:%s was removed !", */
/* 	     GST_DEBUG_PAD_NAME(pad)); */
/* } */


GstElement *
pitivi_sourcefile_bin_new (PitiviSourceFile *self, int type, PitiviMainApp *mainapp)
{
  GstElement	*pipeline, *decode;
  gchar		*tmp;
  GError	*error = NULL;
  bindata	*data;


  tmp = g_strdup_printf ("( filesrc name=src location=\"%s\" ! decodebin name=dbin )",
			 self->filename);
  pipeline = gst_parse_launch (tmp, &error);
  g_assert (pipeline != NULL);
  g_assert (error == NULL);
  g_free(tmp);

  tmp = g_strdup_printf ("sfbin_%s", self->filename);
  gst_element_set_name (pipeline, tmp);
  g_free (tmp);

  data = g_new0(bindata, 1);
  data->bin = pipeline;
  data->sf = self;
  data->bintype = type;
  data->mainapp = mainapp;
  decode = gst_bin_get_by_name (GST_BIN (pipeline), "dbin");
/*   g_signal_connect (pipeline, "state-change", G_CALLBACK (decodebin_change_state), data); */
/*   g_signal_connect (decode, "eos", G_CALLBACK (decodebin_eos), data); */
/*   g_signal_connect (decode, "pad-removed", G_CALLBACK (decodebin_pad_removed), data); */
  g_signal_connect (decode, "new-decoded-pad", G_CALLBACK (bin_new_pad_cb), data);

  bin_add_outputbins (data);

  gst_element_set_state (pipeline, GST_STATE_READY);

  return pipeline;
}

gboolean
pad_is_video_yuv(GstPad *pad)
{
  GstCaps	*caps;

  caps = gst_caps_from_string("video/x-raw-yuv,format=(fourcc)I420");
  if (gst_caps_is_always_compatible(caps, gst_pad_get_caps(pad))) {
    gst_caps_free (caps);
    return TRUE;
  }
  gst_caps_free (caps);
  return FALSE;
}

GstElement *
pitivi_sourcefile_bin_new_effect (PitiviSourceFile *self, GstElementFactory *factory)
{
  GstElement	*bin, *effect;
  GstElement	*inadapt, *outadapt;
  gchar		*tmp;

  tmp = g_strdup_printf ("sfbin-%s", self->filename);
  bin = gst_bin_new(tmp);
  g_free (tmp);

  effect = gst_element_factory_create (factory, self->filename);
  g_assert (effect != NULL);
  gst_bin_add (GST_BIN(bin), effect);
  g_object_set_data (G_OBJECT (bin), "effect", effect);

  if (!(pad_is_video_yuv(gst_element_get_pad(effect, "sink")))) {
    inadapt = gst_element_factory_make ("ffmpegcolorspace", "inadapt");
    gst_bin_add (GST_BIN(bin), inadapt);
    gst_element_add_ghost_pad (GST_ELEMENT(bin),
			       gst_element_get_pad (inadapt, "sink"),
			       "sink");
    if (!(gst_element_link (inadapt, effect)))
      PITIVI_WARNING ("Couldn't link input adapter to effect");
  } else {
    gst_element_add_ghost_pad (GST_ELEMENT(bin),
			       gst_element_get_pad (effect, "sink"),
			       "sink");
  }

  if (!(pad_is_video_yuv(gst_element_get_pad(effect, "src")))) {
    outadapt = gst_element_factory_make ("ffmpegcolorspace", "outadapt");
    gst_bin_add (GST_BIN(bin), outadapt);
    gst_element_add_ghost_pad (GST_ELEMENT(bin),
			       gst_element_get_pad (outadapt, "src"),
			       "src");
    if (!(gst_element_link (effect, outadapt)))
      PITIVI_WARNING ("Couldn't link output adapter to effect");
  } else {
    gst_element_add_ghost_pad (GST_ELEMENT(bin),
			       gst_element_get_pad (effect, "src"),
			       "src");
  }
  return bin;
}
