/* Gnonlin
 * Copyright (C) <2001> Wim Taymans <wim.taymans@chello.be>
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Library General Public
 * License as published by the Free Software Foundation; either
 * version 2 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Library General Public License for more details.
 *
 * You should have received a copy of the GNU Library General Public
 * License along with this library; if not, write to the
 * Free Software Foundation, Inc., 59 Temple Place - Suite 330,
 * Boston, MA 02111-1307, USA.
 */

#include <string.h>
#include "config.h"
#include "gnlsource.h"
#include "gnlmarshal.h"

GstElementDetails gnl_source_details = GST_ELEMENT_DETAILS
(
  "GNL Source",
  "Filter/Editor",
  "Manages source elements",
  "Wim Taymans <wim.taymans@chello.be>"
);

struct _GnlSourcePrivate {
  gboolean	dispose_has_run;
  gint64	seek_start;
  gint64	seek_stop;
};

enum {
  ARG_0,
  ARG_ELEMENT,
};

enum
{
  GET_PAD_FOR_STREAM_ACTION,
  LAST_SIGNAL
};

static void		gnl_source_base_init		(gpointer g_class);
static void 		gnl_source_class_init 		(GnlSourceClass *klass);
static void 		gnl_source_init 		(GnlSource *source);
static void 		gnl_source_dispose 		(GObject *object);
static void 		gnl_source_finalize 		(GObject *object);

static void		gnl_source_set_property 	(GObject *object, guint prop_id,
							 const GValue *value, GParamSpec *pspec);
static void		gnl_source_get_property 	(GObject *object, guint prop_id, GValue *value,
		                                         GParamSpec *pspec);

static GstPad*	 	gnl_source_request_new_pad 	(GstElement *element, GstPadTemplate *templ, 
							 const gchar *unused);

static gboolean 	gnl_source_prepare 		(GnlObject *object, GstEvent *event);

static GstElementStateReturn
			gnl_source_change_state 	(GstElement *element);


static GstData* 	source_getfunction 		(GstPad *pad);
static void 		source_chainfunction 		(GstPad *pad, GstData *buffer);

typedef struct 
{
  GnlSource *source;
  const gchar *padname;
  GstPad *target;
} LinkData;

static void		source_element_new_pad	 	(GstElement *element, 
							 GstPad *pad, 
							 LinkData *data);

static GnlObjectClass *parent_class = NULL;
static guint gnl_source_signals[LAST_SIGNAL] = { 0 };

typedef struct {
  GSList *queue;
  GstPad *srcpad,
         *sinkpad;
  gboolean active;
  GstProbe	*probe;
} SourcePadPrivate;

#define CLASS(source)  GNL_SOURCE_CLASS (G_OBJECT_GET_CLASS (source))

GType
gnl_source_get_type (void)
{
  static GType source_type = 0;

  if (!source_type) {
    static const GTypeInfo source_info = {
      sizeof (GnlSourceClass),
      (GBaseInitFunc) gnl_source_base_init,
      NULL,
      (GClassInitFunc) gnl_source_class_init,
      NULL,
      NULL,
      sizeof (GnlSource),
      32,
      (GInstanceInitFunc) gnl_source_init,
    };
    source_type = g_type_register_static (GNL_TYPE_OBJECT, "GnlSource", &source_info, 0);
  }
  return source_type;
}

static void
gnl_source_base_init (gpointer g_class)
{
  GstElementClass *gstclass = GST_ELEMENT_CLASS (g_class);

  gst_element_class_set_details (gstclass, &gnl_object_details);
  
  /*  gst_element_class_add_pad_template (gstclass,
				      gst_pad_template_new ("src", GST_PAD_SRC,
							    GST_PAD_REQUEST, NULL)
							    );*/
}


static void
gnl_source_class_init (GnlSourceClass *klass)
{
  GObjectClass 		*gobject_class;
  GstElementClass 	*gstelement_class;
  GnlObjectClass 	*gnlobject_class;

  gobject_class = 	(GObjectClass*)klass;
  gstelement_class = 	(GstElementClass*)klass;
  gnlobject_class = 	(GnlObjectClass*)klass;

  parent_class = g_type_class_ref (GNL_TYPE_OBJECT);

  gobject_class->set_property = GST_DEBUG_FUNCPTR (gnl_source_set_property);
  gobject_class->get_property = GST_DEBUG_FUNCPTR (gnl_source_get_property);
  gobject_class->dispose      = GST_DEBUG_FUNCPTR (gnl_source_dispose);
  gobject_class->finalize     = GST_DEBUG_FUNCPTR (gnl_source_finalize);

  g_object_class_install_property (G_OBJECT_CLASS (klass), ARG_ELEMENT,
    g_param_spec_object ("element", "Element", "The element to manage",
                         GST_TYPE_ELEMENT, G_PARAM_READWRITE));

  gnl_source_signals[GET_PAD_FOR_STREAM_ACTION] =
    g_signal_new("get_pad_for_stream",
                 G_TYPE_FROM_CLASS(klass),
		 G_SIGNAL_RUN_LAST | G_SIGNAL_ACTION,
                 G_STRUCT_OFFSET (GnlSourceClass, get_pad_for_stream),
                 NULL, NULL,
                 gnl_marshal_OBJECT__STRING,
                 GST_TYPE_PAD, 1, G_TYPE_STRING);

  gstelement_class->change_state 	= gnl_source_change_state;
  gstelement_class->request_new_pad 	= gnl_source_request_new_pad;

  gnlobject_class->prepare 		= gnl_source_prepare;

  klass->get_pad_for_stream		= gnl_source_get_pad_for_stream;
}


static void
gnl_source_init (GnlSource *source)
{
  source->element_added = FALSE;
  GST_FLAG_SET (source, GST_ELEMENT_DECOUPLED);
  GST_FLAG_SET (source, GST_ELEMENT_EVENT_AWARE);

  source->bin = gst_pipeline_new ("pipeline");
  source->element = 0;
  source->linked_pads = 0;
  source->total_pads = 0;
  source->links = NULL;
  source->pending_seek = NULL;
  source->private = g_new0(GnlSourcePrivate, 1);
}

static void
gnl_source_dispose (GObject *object)
{
  GnlSource *source = GNL_SOURCE (object);
  GSList	*pads = source->links;
  SourcePadPrivate	*priv;

  if (source->private->dispose_has_run)
    return;

  GST_INFO("dispose");
  source->private->dispose_has_run = TRUE;

  
  while (pads) {
    priv = (SourcePadPrivate *) pads->data;

    g_slist_free (priv->queue);
    gst_pad_remove_probe(GST_PAD (priv->srcpad), 
			 priv->probe);
/*     gst_object_unref (GST_OBJECT (priv->srcpad)); */
/*     gst_object_unref (GST_OBJECT (priv->sinkpad)); */

    pads = g_slist_next (pads);
  }

  if (source->element) {
    gst_bin_remove (GST_BIN (source->bin), source->element);
    gst_object_unref (GST_OBJECT (source->element));
  }

  gst_object_unref (GST_OBJECT (source->bin));
  
  G_OBJECT_CLASS (parent_class)->dispose (object);
  GST_INFO("dispose END");
}

static void
gnl_source_finalize (GObject *object)
{
  GnlSource *source = GNL_SOURCE (object);

  GST_INFO("finalize");
  g_free (source->private);
  g_slist_free (source->links);
  
  G_OBJECT_CLASS (parent_class)->finalize (object);
}

/** 
 * gnl_source_new:
 * @name: The name of the new #GnlSource
 * @element: The element managed by this source
 *
 * Creates a new source object with the given name. The
 * source will manage the given GstElement
 *
 * Returns: a new #GnlSource object or NULL in case of
 * an error.
 */
GnlSource*
gnl_source_new (const gchar *name, GstElement *element)
{
  GnlSource *source;
  /*  GstElementClass *sclass;*/

  GST_INFO ("name[%s], element[%s]", name,
	    gst_element_get_name( element ) );
 
  g_return_val_if_fail (name != NULL, NULL);
  g_return_val_if_fail (element != NULL, NULL);

  /* source = GNL_SOURCE (gst_element_factory_make ("gnlsource", name)); */
  source = g_object_new(GNL_TYPE_SOURCE, NULL);
		  
  //source = g_object_new (GNL_TYPE_SOURCE,
  
  gst_object_set_name(GST_OBJECT(source), name);
  gnl_source_set_element(source, element);

  GST_INFO("sched source[%p] bin[%p]", 
	   GST_ELEMENT_SCHED(source),
	   GST_ELEMENT_SCHED(source->bin));

  /*  g_object_set (G_OBJECT (source),
		         "name", name, 
			 "element", element, 
			 NULL);
  */
/*   sclass = GST_ELEMENT_GET_CLASS (source); */
/*   if (sclass->padtemplates == NULL) { */
/*     sclass->padtemplates = g_list_prepend (sclass->padtemplates,  */
/* 		           gnl_source_src_factory()); */
/*     sclass->numpadtemplates = 1; */
/*   } */

  return source;
}

/** 
 * gnl_source_get_element:
 * @source: The source element to get the element of
 *
 * Get the element managed by this source.
 *
 * Returns: The element managed by this source.
 */
GstElement*
gnl_source_get_element (GnlSource *source)
{
  g_return_val_if_fail (GNL_IS_SOURCE (source), NULL);

  return source->element;
}

/** 
 * gnl_source_set_element:
 * @source: The source element to set the element on
 * @element: The element that should be managed by the source
 *
 * Set the given element on the given source. If the source
 * was managing another element, it will be removed first.
 */
void
gnl_source_set_element (GnlSource *source, GstElement *element)
{
  g_return_if_fail (GNL_IS_SOURCE (source));
  g_return_if_fail (GST_IS_ELEMENT (element));

  GST_INFO ("Source[%s] Element[%s] sched[%p]",
	    gst_element_get_name(GST_ELEMENT(source)),
	    gst_element_get_name(element),
	    GST_ELEMENT_SCHED(element));

  if (source->element) {
    gst_bin_remove (GST_BIN (source->bin), source->element);
    gst_object_unref (GST_OBJECT (source->element));
  }

  //  gst_object_ref (GST_OBJECT (element));

  source->element = element;
  source->linked_pads = 0;
  source->total_pads = 0;
  source->links = NULL;
  source->pending_seek = NULL;
  source->private->seek_start = GST_CLOCK_TIME_NONE;
  source->private->seek_stop = GST_CLOCK_TIME_NONE;

  gst_bin_add (GST_BIN (source->bin), source->element);
}

static GstCaps *source_getcaps (GstPad *pad)
{
  GstPad *otherpad;
  SourcePadPrivate *private;

  private = gst_pad_get_element_private (pad);
  
  otherpad = (GST_PAD_IS_SRC (pad)? private->sinkpad : private->srcpad);

  return gst_pad_get_allowed_caps (otherpad);
}

static GstPadLinkReturn
source_link (GstPad *pad, const GstCaps *caps)
{
  GstPad *otherpad;
  SourcePadPrivate *private;

  GST_INFO("linking");
  private = gst_pad_get_element_private (pad);
  
  otherpad = (GST_PAD_IS_SRC (pad)? private->sinkpad : private->srcpad);

  return gst_pad_try_set_caps (otherpad, caps);
}

void
source_unlink (GstPad *pad)
{
  GST_INFO("unlinking !!!");
}

/*
  source_probe

  Checks if the data coming out of the source's element is not after the seek_stop position
  If it is, it sets the source's element to EOS and discards the data
*/

gboolean
source_probe (GstProbe *probe, GstData **data, gpointer udata)
{
  GnlSource *source = GNL_SOURCE(udata);
  
  GST_INFO("source probe %s --> %lld  object[%lld]->[%lld]  media[%lld]->[%lld] seek[%lld]->[%lld]",
	   gst_element_get_name(GST_ELEMENT(source)),
	   (long long int) GST_BUFFER_TIMESTAMP(*data),
	   GNL_OBJECT(source)->start,
	   GNL_OBJECT(source)->stop,
	   GNL_OBJECT(source)->media_start,
	   GNL_OBJECT(source)->media_stop,
	   source->private->seek_start,
	   source->private->seek_stop);

  if (GST_IS_BUFFER (*data) 
      && GST_CLOCK_TIME_IS_VALID(source->private->seek_stop)
      && (GST_BUFFER_TIMESTAMP(*data) >= source->private->seek_stop)) {
    GST_INFO("buffer is older than seek_stop, sending EOS on GnlSourceElement");
    /* The data is after the end of seek , set the source element to EOS */
    gst_element_set_eos(source->element);
    gnl_object_set_active(GNL_OBJECT(source), FALSE);
    return FALSE; /* We don't want this data to carry on */
  }
  
  return TRUE;
}

/** 
 * gnl_source_get_pad_for_stream:
 * @source: The source element to query
 * @padname: The padname of the element managed by this source
 *
 * Get a handle to a pad that provides the data from the given pad
 * of the managed element.
 *
 * Returns: A pad 
 */
GstPad*
gnl_source_get_pad_for_stream (GnlSource *source, const gchar *padname)
{
  GstPad *srcpad, *sinkpad, *pad;
  SourcePadPrivate *private;
  gchar *ourpadname;

  g_return_val_if_fail (GNL_IS_SOURCE (source), NULL);
  g_return_val_if_fail (padname != NULL, NULL);

  GST_INFO("Source[%s] padname[%s] sched[%p] binsched[%p]",
	   gst_element_get_name(GST_ELEMENT(source)),
	   padname,
	   GST_ELEMENT_SCHED(source),
	   GST_ELEMENT_SCHED(source->bin));
  
  private = g_new0 (SourcePadPrivate, 1);

  srcpad = gst_pad_new (padname, GST_PAD_SRC);
  gst_element_add_pad (GST_ELEMENT (source), srcpad);
  gst_pad_set_element_private (srcpad, private);
  gst_pad_set_get_function (srcpad, source_getfunction);
  gst_pad_set_link_function (srcpad, source_link);
  gst_pad_set_getcaps_function (srcpad, source_getcaps);

  ourpadname = g_strdup_printf ("internal_sink_%s", padname);
  sinkpad = gst_pad_new (ourpadname, GST_PAD_SINK);
  g_free (ourpadname);
  gst_element_add_pad (GST_ELEMENT (source), sinkpad);
  gst_pad_set_element_private (sinkpad, private);
  gst_pad_set_chain_function (sinkpad, source_chainfunction);
  gst_pad_set_link_function (sinkpad, source_link);
  gst_pad_set_getcaps_function (sinkpad, source_getcaps);

  private->srcpad  = srcpad;
  private->sinkpad = sinkpad;

  source->links = g_slist_prepend (source->links, private);

  pad = gst_element_get_pad (source->element, padname);

  source->total_pads++;

  /* Adding probe to private->srcpad */
  private->probe = gst_probe_new (FALSE, source_probe, source);
  gst_pad_add_probe (private->srcpad, private->probe);

  if (pad) {
    GST_INFO("%s linked straight away with %s",
	     gst_element_get_name(GST_ELEMENT(source)),
	     gst_pad_get_name(sinkpad));
    gst_pad_link (pad, sinkpad);
    source->linked_pads++;
  }
  else {
    LinkData *data = g_new0 (LinkData, 1);

    GST_INFO("%s links with delay...",
	     gst_element_get_name(GST_ELEMENT(source)));

    data->source = source;
    data->padname = padname;
    data->target = sinkpad;
    
    g_signal_connect (G_OBJECT (source->element), 
		      "new_pad", 
		      G_CALLBACK (source_element_new_pad), 
		      data);
  }

  return srcpad;
}

static GstPad*
gnl_source_request_new_pad (GstElement *element, GstPadTemplate *templ, 
		 	    const gchar *name)
{
  
  GST_INFO("element[%s] Template[##] name[%s]",
	   gst_element_get_name(element),
	   name);

  return gnl_source_get_pad_for_stream (GNL_SOURCE (element), name);
}

static void
clear_queues (GnlSource *source)
{
  GSList *walk = source->links;

  GST_INFO("clear_queues %p", walk);
  while (walk) {
    SourcePadPrivate *private = (SourcePadPrivate *) walk->data;

    g_slist_free (private->queue);
    private->queue = NULL;
    
    walk = g_slist_next (walk);
  }
}

static gboolean
source_is_media_queued (GnlSource *source)
{
  const GList *pads = gst_element_get_pad_list (GST_ELEMENT (source));

  while (pads) {
    GstPad *pad = GST_PAD (pads->data);
    SourcePadPrivate *private = gst_pad_get_element_private (pad);

    if (!private->queue) {
      GST_WARNING("Pad %s hasn't any queue...",
	       gst_pad_get_name(pad));
      return FALSE;
    }
    pads = g_list_next (pads);
  }
  GST_INFO("Everything went ok");
  return TRUE;
}

static gboolean
source_send_seek (GnlSource *source, GstEvent *event)
{
  const GList *pads;
  gboolean	wasinplay = FALSE;

  /* ghost all pads */
  pads = gst_element_get_pad_list (source->element);

  if (!event)
    return FALSE;

  if (!pads)
    GST_WARNING("%s has no pads...",
	     gst_element_get_name (GST_ELEMENT (source->element)));

  source->private->seek_start = GST_EVENT_SEEK_OFFSET (event);
  source->private->seek_stop = GST_EVENT_SEEK_ENDOFFSET (event);

  GST_INFO("seek from %lld to %lld",
	   source->private->seek_start,
	   source->private->seek_stop);

  event = gst_event_new_seek(GST_FORMAT_TIME | GST_SEEK_METHOD_SET | GST_SEEK_FLAG_FLUSH,
			     source->private->seek_start);

  if (GST_STATE(source->bin) == GST_STATE_PLAYING)
    wasinplay = TRUE;
  if (!(gst_element_set_state(source->bin, GST_STATE_PAUSED)))
    GST_WARNING("couldn't set GnlSource's bin to PAUSED !!!");
  while (pads) {  
    GstPad *pad = GST_PAD (pads->data);
/*     GstEvent *event; */

/*     event = source->pending_seek; */
    gst_event_ref (event);

    GST_INFO ("%s: seeking to %lld", 
	      gst_element_get_name (GST_ELEMENT (source)), 
	      source->private->seek_start);
    
    if (!gst_pad_send_event (pad, event)) {
      g_warning ("%s: could not seek", 
		 gst_element_get_name (GST_ELEMENT (source)));
    }

    pads = g_list_next (pads);
  }
  if (wasinplay)
    gst_element_set_state(source->bin, GST_STATE_PLAYING);
/*   gst_event_unref (source->pending_seek); */
/*   source->pending_seek = NULL; */

  clear_queues (source);

  return TRUE;
}

static void
activate_internal_sinkpads (SourcePadPrivate *private, GnlSource *source)
{
  gst_pad_set_active (private->sinkpad, TRUE);
}

static void
deactivate_internal_sinkpads (SourcePadPrivate *private, GnlSource *source)
{
  gst_pad_set_active (private->sinkpad, FALSE);
}

static gboolean
source_queue_media (GnlSource *source)
{
  gboolean filled;

  GST_INFO("%s switching to PLAYING for media buffering", gst_element_get_name(GST_ELEMENT(source)));

  if (!gst_element_set_state (source->bin, GST_STATE_PLAYING)) {
    GST_WARNING("END : couldn't change bin to PLAYING");
    return FALSE;
  }
  g_slist_foreach (source->links, 
		   (GFunc) activate_internal_sinkpads,
		   source);

  source->queueing = TRUE;

  filled = FALSE;
  
  GST_INFO("about to iterate");
  while (!filled) {
    if (!gst_bin_iterate (GST_BIN (source->bin))) {
      break;
    }
    filled = source_is_media_queued (source);
  }
  GST_INFO("Finished iterating");

  source->queueing = FALSE;

  source_send_seek (source, source->pending_seek);

  gst_event_unref (source->pending_seek);
  source->pending_seek = NULL;
  
  g_slist_foreach (source->links, 
		   (GFunc) deactivate_internal_sinkpads,
		   source);

  GST_INFO("going back to PAUSED state after media buffering");
  if (!gst_element_set_state (source->bin, GST_STATE_PAUSED)) {
    GST_ERROR("error : couldn't put bin back to PAUSED");
    filled = FALSE;
  }

  GST_INFO("END : source media is queued [%d]",
	   filled);
  return filled;
}

static void
source_chainfunction (GstPad *pad, GstData *buf)
{
  SourcePadPrivate *private;
  GnlSource *source;
  GnlObject *object;
  GstClockTimeDiff intime;
  GstBuffer	*buffer = GST_BUFFER(buf);

  GST_INFO("chaining");

  private = gst_pad_get_element_private (pad);
  source = GNL_SOURCE (gst_pad_get_parent (pad));
  object = GNL_OBJECT (source);

  if (GST_IS_EVENT(buffer))
    GST_INFO("Chaining an event : %d",
	     GST_EVENT_TYPE(buffer));
  else
    GST_INFO("Chaining a buffer");
  if (GST_IS_BUFFER (buffer) && !source->queueing) {
    intime = GST_BUFFER_TIMESTAMP (buffer);

    if (intime < object->media_start) {
      GstFormat format = GST_FORMAT_TIME;
      gint64 value = 0;
      
      gst_pad_convert (GST_PAD_PEER (pad), 
		      GST_FORMAT_BYTES, GST_BUFFER_SIZE (buffer),
		      &format, &value);

      if (value + intime < object->media_start) {
        gst_buffer_unref (buffer);
        return;
      }
    }
    if (intime > object->media_stop) {
      gst_pad_set_active (pad, FALSE);
      gst_buffer_unref (buffer);
      buffer = GST_BUFFER (gst_event_new (GST_EVENT_EOS));
    }
  }
  
  private->queue = g_slist_append (private->queue, buffer);
  GST_INFO("end of chaining");
}

static GstData*
source_getfunction (GstPad *pad)
{
  GstBuffer *buffer;
  SourcePadPrivate *private;
  GnlSource *source;
  GnlObject *object;
  gboolean found = FALSE;

  private = gst_pad_get_element_private (pad);
  source = GNL_SOURCE (gst_pad_get_parent (pad));
  object = GNL_OBJECT (source);

  if (!GST_PAD_IS_ACTIVE (pad)) {
    GST_INFO("pad not active, creating EOS");
    found = TRUE;
    buffer = GST_BUFFER (gst_event_new (GST_EVENT_EOS));
  }

  while (!found) {
    /* No data in private queue, EOS */
    while (!private->queue) {
      if (!gst_bin_iterate (GST_BIN (source->bin))) {
	GST_INFO("Nothing more coming from %s",
		 gst_element_get_name(GST_ELEMENT(source->bin)));
        buffer = GST_BUFFER (gst_event_new (GST_EVENT_EOS));
	found = TRUE;
        break;
      }
      GST_INFO("while !private->queue %p", private->queue);
    }

    /* Data in private queue */
    if (private->queue) {
      buffer = GST_BUFFER (private->queue->data);

      
      /* if DATA is EOS, forward it*/ 
      if (GST_IS_EVENT (buffer)) {
	GST_INFO("Event Buffer type : %d", GST_EVENT_TYPE(buffer));
        if (GST_EVENT_TYPE (buffer) == GST_EVENT_EOS) {
          GST_INFO ("%s: EOS at %lld %lld %lld %lld / now:%lld", 
		    gst_element_get_name (GST_ELEMENT (source)), 
		    object->media_start,
		    object->media_stop,
		    object->start,
		    object->stop,
		    object->current_time);

          //object->current_time = object->media_start + object->start;
          object->current_time++;
	  gst_pad_set_active (pad, FALSE);
	  found = TRUE;
        }
      }
      else {
	/* If data is buffer */
        GstClockTimeDiff outtime, intime;

        intime = GST_BUFFER_TIMESTAMP (buffer);

	/* check if buffer is outside seek range */
	if ((GST_CLOCK_TIME_IS_VALID(source->private->seek_stop)
	     && (intime >= source->private->seek_stop))) {
	  GST_INFO("Data is after seek_stop, creating EOS");
	  gst_data_unref(GST_DATA(buffer));
	  buffer = GST_BUFFER (gst_event_new (GST_EVENT_EOS));
	}
	outtime = intime - object->media_start + object->start;
	
	object->current_time = outtime;
	
	GST_INFO ("%s: get %lld corrected to %lld", 
		  gst_element_get_name (GST_ELEMENT (source)), 
		  intime, 
		  outtime);
	
	GST_BUFFER_TIMESTAMP (buffer) = outtime;
	
        found = TRUE;
      }
      /* flush last element in queue */
      private->queue = g_slist_remove (private->queue, buffer);
    }
  }
  
  {
    GSList *walk;
    gboolean eos = TRUE;
    
    walk = source->links;
    while (walk) {
      SourcePadPrivate *test_priv = (SourcePadPrivate *) walk->data;

      if (GST_PAD_IS_ACTIVE (test_priv->srcpad)) {
	eos = FALSE;
	break;
      }
      walk = g_slist_next (walk);
    }
    if (eos) {
      GST_INFO("EOS on source");
      gst_element_set_eos (GST_ELEMENT (source));
      GST_INFO("End of EOS on source");
    }
  }
  GST_INFO("END");
  if (GST_IS_EVENT(buffer) && (GST_EVENT_TYPE (buffer) == GST_EVENT_EOS))
    gnl_object_set_active(object, FALSE);
  return (GstData *) buffer;
}

static gboolean
gnl_source_prepare (GnlObject *object, GstEvent *event)
{
  GnlSource *source = GNL_SOURCE (object);
  gboolean res = TRUE;

  GST_INFO("Object[%s] [%lld]->[%lld] State:%d",
	   gst_element_get_name(GST_ELEMENT(object)),
	   GST_EVENT_SEEK_OFFSET(event),
	   GST_EVENT_SEEK_ENDOFFSET(event),
	   gst_element_get_state (GST_ELEMENT(object)));

  source->pending_seek = event;

  if (gst_element_get_state (GST_ELEMENT (object)) >= GST_STATE_READY) {
    res = source_send_seek (source, source->pending_seek);
  }
  
  return res;
}


static void
source_element_new_pad (GstElement *element, GstPad *pad, LinkData *data)
{
  GST_INFO ("source %s new pad %s", GST_OBJECT_NAME (data->source), GST_PAD_NAME (pad));
  GST_INFO ("link %s new pad %s %d", data->padname, gst_pad_get_name (pad),
     					GST_PAD_IS_LINKED (data->target));

  if (!strcmp (gst_pad_get_name (pad), data->padname) && 
     !GST_PAD_IS_LINKED (data->target)) 
  {
     gst_pad_link (pad, data->target);
     gst_pad_set_active (data->target, TRUE);
  }
}

static GstElementStateReturn
gnl_source_change_state (GstElement *element)
{
  GnlSource *source = GNL_SOURCE (element);
  GstElementStateReturn	res = GST_STATE_SUCCESS;

  if (!GNL_OBJECT(source)->active)
    GST_WARNING("Trying to change state but Source %s is not active ! This might be normal...",
		gst_element_get_name(element));
  if (GNL_OBJECT(source)->active)
    switch (GST_STATE_TRANSITION (source)) {
    case GST_STATE_NULL_TO_READY:
      break;
    case GST_STATE_READY_TO_PAUSED:
      if (!source_queue_media (source))
	res = GST_STATE_FAILURE;
      break;
    case GST_STATE_PAUSED_TO_PLAYING:
      if (!gst_element_set_state (source->bin, GST_STATE_PLAYING))
	res = GST_STATE_FAILURE;
      break;
    case GST_STATE_PLAYING_TO_PAUSED:
      if (!gst_element_set_state (source->bin, GST_STATE_PAUSED))
	res = GST_STATE_FAILURE;
      break;
    case GST_STATE_PAUSED_TO_READY:
      break;
    case GST_STATE_READY_TO_NULL:
      break;
    default:
      break;
    }
  
  if (res == GST_STATE_SUCCESS)
    res = GST_ELEMENT_CLASS (parent_class)->change_state (element);
  else
    GST_WARNING("%s : something went wrong",
		gst_element_get_name(element));
  GST_INFO("%s : change_state returns %d",
	   gst_element_get_name(element),
	   res);
  return res;
}

static void
gnl_source_set_property (GObject *object, guint prop_id,
			 const GValue *value, GParamSpec *pspec)
{
  GnlSource *source;

  g_return_if_fail (GNL_IS_SOURCE (object));

  source = GNL_SOURCE (object);

  switch (prop_id) {
    case ARG_ELEMENT:
      gnl_source_set_element (source, GST_ELEMENT (g_value_get_object (value)));
      break;
    default:
      G_OBJECT_WARN_INVALID_PROPERTY_ID (object, prop_id, pspec);
      break;
  }
}

static void
gnl_source_get_property (GObject *object, guint prop_id, 
			 GValue *value, GParamSpec *pspec)
{
  GnlSource *source;
  
  g_return_if_fail (GNL_IS_SOURCE (object));

  source = GNL_SOURCE (object);

  switch (prop_id) {
    case ARG_ELEMENT:
      g_value_set_object (value, gnl_source_get_element (source));
      break;
    default:
      G_OBJECT_WARN_INVALID_PROPERTY_ID (object, prop_id, pspec);
      break;
  }
}
