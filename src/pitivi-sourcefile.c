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

static  GObjectClass *parent_class;

typedef struct _PitiviListElm
{
  gchar	*name;
  gchar	*type;
  gchar	*category;
}		PitiviListElm;

struct _PitiviSourceFilePrivate
{
  /* instance private members */
  gboolean	dispose_has_run;

  /* GST variable */
  
  GstElement	*mainpipeline;
  GstCaps	*mediacaps;
  GSList       	*padlist;
  GSList	*elmlist;
  
  /* Property of the media */
  
  gchar		*mainmediatype;
  gboolean	havepad;

  /* MainApp */
  PitiviMainApp *mainapp;
};

/*
 * forward definitions
 */

static gchar	*BaseMediaType[] = 
  {
    "video/x-raw-rgb", 
    "video/x-raw-yuv", 
    "audio/x-raw-float",
    "audio/x-raw-int",
    0
  };

/*
 * Insert "added-value" functions here
 */

enum
  {
    PROP_FILENAME = 1,
    PROP_MAINAPP,
  };


void	pitivi_sourcefile_eof (GstElement *src)
{
  g_printf("== have eos ==\n");
}

void	pitivi_sourcefile_new_pad_created(GstElement *parse, GstPad *pad, gpointer data)
{
  PitiviSourceFile *this = (PitiviSourceFile*)data;
  
  gchar	*padname;
  PitiviSettings	*settings;
  gchar	*tmp;

  //g_printf("a new pad %s was created\n", gst_pad_get_name(pad));
  //g_printf("caps is ==> %s\n", gst_caps_to_string(gst_pad_get_caps(pad)));
  this->private->padlist = g_slist_append(this->private->padlist, pad);  
}

void	pitivi_sourcefile_add_elm_to_list(PitiviSourceFile *this, gchar *name, gchar *type,
					  gchar *category)
{
  PitiviListElm	*elm_list;

  elm_list = g_new0(PitiviListElm, 1);
  elm_list->name = g_strdup(name);
  elm_list->type = g_strdup(type);
  elm_list->category = g_strdup(category);

  this->private->elmlist = g_slist_append(this->private->elmlist, elm_list);
}



void	pitivi_sourcefile_have_type_handler(GstElement *typefind, guint probability,
					    const GstCaps *caps, gpointer data)
{
  PitiviSourceFile *this = (PitiviSourceFile*)data;
  gchar *caps_str;
  gchar *tmp_str;

  this->private->mediacaps = gst_caps_copy(caps);
  caps_str = gst_caps_to_string(caps);

  tmp_str = caps_str;
  /* basic parsing */
  while (*tmp_str != 0)
    {
      if (*tmp_str == ',')
	{
	  *tmp_str = 0;
	  break;
	}
      tmp_str++;
    }

  this->mediatype = caps_str;
}


void	       pitivi_sourcefile_get_length (PitiviSourceFile *this, GstElement *lastelm)
{
  GstElement	*fakesink;
  GstFormat	format;
  gint64	value;

  gst_element_set_state(this->private->mainpipeline, GST_STATE_PLAYING);
  format = GST_FORMAT_TIME;
  if (gst_element_query(lastelm, GST_QUERY_TOTAL, &format, &value)) {
    g_printf("format ==> %d\ntime ==> %lld\n", format, value);
    if (!this->length)
      this->length = value;
  }
  else
    g_printf("Couldn't perform requested query\n");
}


void	
pitivi_sourcefile_set_media_property (PitiviSourceFile *this,
				      gchar *caps_str)
{
  gchar	**property;
  gchar	*tmpstring;
  gchar	*savstring;
  gchar	*value;
  gint	nbentry;
  gint	i;
  gint	j;

  
  nbentry = 1;

  tmpstring = caps_str;
  while (*tmpstring)
    {
      if (*tmpstring == ',')
	nbentry++;
      tmpstring++;
    }
     
 
  property = g_malloc((nbentry + 1) * sizeof(gchar *));

  /* cut the string */
  tmpstring = g_strdup(caps_str);
  savstring = tmpstring;

  i = 0;
  
  while (*tmpstring)
    {
      if (*tmpstring == ',')
	{
	  *tmpstring = 0;
	  property[i] = savstring;
	  i++;
	  tmpstring++;
	  /* for space */
	  tmpstring++;
	  savstring = tmpstring;
	}
      tmpstring++;
    }
  property[i] = savstring;
  property[i+1] = NULL;

  if (strstr(caps_str, "video"))
    {
      this->havevideo = TRUE;
      j = 0;
      if (property[j])
	{
	  this->infovideo = g_strdup(property[j]);
	}
    }
  if (strstr(caps_str, "audio"))
    {
      this->haveaudio = TRUE;
      j = 0;
      if (property[j])
	{
	  this->infoaudio = property[j];
	}
    }
}

void	pitivi_sourcefile_new_video_pad_created (GstElement *parse, GstPad *pad, gpointer data)
{
  PitiviSourceFile *this = (PitiviSourceFile*)data;
  PitiviListElm	*elm_list;
  GSList	*list;
  GstElement	*decoder;
  GstCaps	*caps;
  gchar		*caps_str;
  gboolean	flag;
  GstPad	*temppad;

  g_printf("a new pad [%s] was created\n", gst_pad_get_name(pad));
  caps = gst_pad_get_caps(pad);
  caps_str = gst_caps_to_string(caps);
  flag = FALSE;
  gst_element_set_state(this->private->mainpipeline, GST_STATE_PAUSED);
  if (strstr(caps_str, "video"))
    {
      list = this->private->elmlist;
      while (list)
	{
	  elm_list = (PitiviListElm*)list->data;
	  if (!strncmp(elm_list->type, "video", 5))
	    {
	      if (!strncmp(elm_list->category, "decoder", 6))
		{
		  flag = TRUE;
		  this->private->havepad = TRUE;
		  g_printf("create decoder [%s]\n", elm_list->name);
		  decoder = gst_element_factory_make(elm_list->name, "decoder_video");
		  gst_bin_add(GST_BIN(this->pipeline_video), decoder);
		  gst_pad_link(pad, gst_element_get_pad(decoder, "sink"));
		  temppad = gst_element_add_ghost_pad(this->pipeline_video, 
						      gst_element_get_pad(decoder, "src"),
						      "vsrc");
		  g_assert(temppad != NULL);
		  g_printf("adding ghost pad vsrc\n");
		}
	    }
	  list = g_slist_next(list);
	}
      if (!flag) /* adding raw ghost pad */
	{
	  this->private->havepad = TRUE;
	  g_printf("adding raw ghost pad\n");
	  temppad = gst_element_add_ghost_pad(this->pipeline_audio, pad,
					      "vsrc");
	  g_assert(temppad != NULL);
	  g_printf("linking raw pad to vsrc\n");
	}
    }
  gst_element_set_state(this->private->mainpipeline, GST_STATE_PLAYING);
}

void	pitivi_sourcefile_make_init_video_pipeline(PitiviSourceFile *this, GstElement *src,
						   gchar *filename)
{
  gchar	*tmpname;

    /* create a pipeline */
  tmpname = g_strdup_printf("video_pipeline_%s", filename);
  this->private->mainpipeline = gst_pipeline_new(tmpname);
  g_free(tmpname);
  g_assert(this->private->mainpipeline != NULL);
  
  /* create a bin */
  tmpname = g_strdup_printf("bin_video_%s", filename);
  this->pipeline_video = gst_bin_new(tmpname);
  g_free(tmpname);

  gst_bin_add(GST_BIN(this->private->mainpipeline), this->pipeline_video);
  
  g_object_set(G_OBJECT(src), "location", filename, NULL);

  /* add the file reader to the pipeline */
  gst_bin_add(GST_BIN(this->pipeline_video), src);
  g_signal_connect(G_OBJECT(src), "eos",
		   G_CALLBACK(pitivi_sourcefile_eof), NULL);
}

void	pitivi_sourcefile_make_parser_pipeline (GstElement *pipeline_media, 
						GstElement *parser, GstElement *last)
{
  g_printf("make video or audio parser\n");
  gst_bin_add(GST_BIN (pipeline_media), parser);
  gst_element_link(last, parser);
}

void	pitivi_sourcefile_make_demuxer_video_pipeline (PitiviSourceFile *this, GstElement *demux, 
						       GstElement *last)
{
  gint	i;

  /* add the demuxer to the main pipeline */
  gst_bin_add(GST_BIN(this->pipeline_video), demux);
	  
  g_signal_connect(G_OBJECT(demux), "new_pad",
		   G_CALLBACK(pitivi_sourcefile_new_video_pad_created), this);
	  
  /* link element */
  gst_element_link(last, demux);
  
  /* we need to run this part only for a demuxer */

  gst_element_set_state(GST_ELEMENT(this->private->mainpipeline), GST_STATE_PLAYING);
  this->private->havepad = FALSE;

  for (i = 0; i < 50; i++)
    {
      gst_bin_iterate(GST_BIN(this->private->mainpipeline));
      if (this->private->havepad)
	{
	  g_printf("found video pad at [%d]\n", i);
	  break;
	}
    }
  gst_element_set_state(GST_ELEMENT(this->private->mainpipeline), 
			GST_STATE_PAUSED);
  gst_object_ref(GST_OBJECT(this->pipeline_video));
  gst_bin_remove(GST_BIN(this->private->mainpipeline), 
		 this->pipeline_video);
  gst_object_unref( (GstObject *) this->private->mainpipeline);
}

void		pitivi_sourcefile_make_video_pipeline (PitiviSourceFile *this, gchar *filename)
{
  GSList	*list;
  PitiviListElm	*elm_list;
  gchar		*tmpname;
  GstElement	*elm, *lastelm;

  g_printf("make video pipeline\n");
  list = this->private->elmlist;
  lastelm = NULL;
  while (list)
    {
      elm_list = (PitiviListElm*)list->data;
      if (!strcmp(elm_list->type, "none"))
	{
	  g_printf("element type [%s]\n", elm_list->type);
	  g_printf("element name [%s]\n", elm_list->name);
	  tmpname = g_strdup_printf("src_video_[%s]_pipeline", elm_list->name);
	  elm = gst_element_factory_make(elm_list->name, tmpname);
	  if (!strcmp(elm_list->category, "filereader"))
	    {
	      g_printf("Make file reader\n");
	      pitivi_sourcefile_make_init_video_pipeline(this, elm, filename);
	    }
	  if (!strcmp(elm_list->category, "demuxer"))
	    {
	      g_printf("Make demuxer\n");
	      pitivi_sourcefile_make_demuxer_video_pipeline (this, elm, lastelm);
	    }
	  if (!strcmp(elm_list->category, "parser"))
	    {
	      g_printf("Make parser\n");
	      pitivi_sourcefile_make_parser_pipeline (this->pipeline_video, elm, lastelm);
	    }
	}
      else if (!strcmp(elm_list->type, "video"))
	{
	  g_printf("element type [%s]\n", elm_list->type);
	  g_printf("element [%s]\n", elm_list->name);
	  
	}
      lastelm = elm;
      list = g_slist_next(list);
    }
}

GstElement	*pitivi_sourcefile_add_decoder_for_demux(PitiviSourceFile *this,
							 GList *decoderlist, 
							 GstElement *parser,  
							 GstElement *thread, 
							 gint nb_thread, GstPad *pad,
							 GstElement **element)
{
  GstElement	*decoder;
  GstElement	*queue;
  gchar		*name;
  gboolean	flag;

  flag = FALSE;
  if (!thread)
    {
      flag = TRUE;
      name = g_strdup_printf("thread%d", nb_thread);
      
      /* create a thread for the decoder pipeline */
      // TODO : IS THREAD NECESSARY ??? thread = gst_thread_new(name);
      thread = gst_thread_new(name);
      g_assert(thread != NULL);
      
      g_free(name);
    }
  
  /* choose the first decoder */
  name = g_strdup_printf("decoder%d", nb_thread);
  decoder = gst_element_factory_make((gchar*)decoderlist->data, name);
  
  g_assert(decoder != NULL);
  g_free(name);
  
  this->mediatype = gst_caps_to_string(gst_pad_get_caps(gst_element_get_pad(decoder, "src")));
  this->private->mediacaps = gst_pad_get_caps(gst_element_get_pad(decoder, "src"));
  g_printf("mediatype for decoder ==> [%s]\n", this->mediatype);

  if (strstr(this->mediatype, "video"))
    {
      g_printf("adding video decoder elem [%s]\n", (gchar*)decoderlist->data);
      pitivi_sourcefile_add_elm_to_list(this, (gchar*)decoderlist->data, "video", "decoder");
    }
  else if (strstr(this->mediatype, "audio"))
    {
      g_printf("adding audio decoder elem [%s]\n", (gchar*)decoderlist->data);
      pitivi_sourcefile_add_elm_to_list(this, (gchar*)decoderlist->data, "audio", "decoder");
    }

  //pitivi_sourcelistwindow_get_pad_list(decoder);
  if (flag)
    {
      /* create a queue for link the pipeline with the thread */  
      name = g_strdup_printf("queue%d", nb_thread);
      queue = gst_element_factory_make("queue", name);
      g_assert(queue != NULL);
      g_free(name);
      
      /* add the elements to the thread */
      gst_bin_add_many(GST_BIN(thread), queue, decoder, NULL);
      gst_element_add_ghost_pad(thread, gst_element_get_pad(queue, "sink"), "sink");
      
      /* link the elements */
      gst_element_link(queue, decoder);
      
      /* add the thread to the main pipeline */
      gst_bin_add(GST_BIN(this->pipeline), thread);
      
      /* link the pad to the sink pad of the thread */
      gst_pad_link(pad, gst_element_get_pad(thread, "sink"));
    }
  else /* we already have a thread */
    {
      /* add decoder to the thread */
      gst_bin_add(GST_BIN(thread), decoder);	       
      /* link parser with the decoder */
      gst_element_link(parser, decoder);
    }
  
  *element = decoder;
  return thread;
}

GstElement *pitivi_sourcefile_add_parser_for_demux(PitiviSourceFile *this, 
						   GList *parserlist, GstElement *thread,
						   gint nb_thread, GstPad *pad,
						   GstElement **element, 
						   GstElement * decoder)
{
  GstElement	*parser;
  GstElement	*queue;
  GstCaps	*caps;
  gchar		*name;
  gboolean	flag;


  flag = FALSE;
  if (!thread)
    {
      flag = TRUE;
      name = g_strdup_printf("thread%d", nb_thread);
      
      /* create a thread to add the parser in the pipeline */
      // TODO : CHECK THREAD thread = gst_thread_new(name);
      thread = gst_thread_new(name);
      g_assert(thread != NULL);
      
      g_free(name);
    }
  g_printf("adding parser [###ERROR HERE###] after demux ==> %s\n", (gchar*)parserlist->data);

  /* create the parser */
  name = g_strdup_printf("parser_%d", nb_thread);
  parser = gst_element_factory_make((gchar*)parserlist->data, name);
  

  g_free(name);
  g_assert(parser != NULL);
  
  /* set media property and caps */
  this->mediatype = gst_caps_to_string(gst_pad_get_caps(gst_element_get_pad(parser, "src")));
  this->private->mediacaps = gst_pad_get_caps(gst_element_get_pad(parser, "src"));
  g_printf("mediatype for parser ==> [%s]\n", this->mediatype);

  //pitivi_sourcelistwindow_get_pad_list(parser);
  
  if (strstr(this->mediatype, "video"))
    {
      g_printf("adding parser video elem [%s]\n", (gchar*)parserlist->data);
      pitivi_sourcefile_add_elm_to_list(this, (gchar*)parserlist->data, "video", "parser");
    }
  else if (strstr(this->mediatype, "audio"))
    {
      g_printf("adding parser audio elem [%s]\n", (gchar*)parserlist->data);
      pitivi_sourcefile_add_elm_to_list(this, (gchar*)parserlist->data, "audio", "parser");
    }
  
  caps = this->private->mediacaps;
  
  if (flag)
    {
      /* create a queue for link the pipeline with the thread */    
      name = g_strdup_printf("queue%d", nb_thread);
      queue = gst_element_factory_make("queue", name);
      g_assert(queue != NULL);
      g_free(name);
      
      /* add the elements to the thread */
      gst_bin_add_many(GST_BIN(thread), queue, parser, NULL);
      /* add ghost pad to the thread */
      gst_element_add_ghost_pad(thread, gst_element_get_pad(queue, "sink"), "sink");
      /* link the elements */
      gst_element_link(queue, parser);
      /* add the thread to the main pipeline */
      gst_bin_add(GST_BIN(this->pipeline), thread);
      /* link the pad to the sink pad of the thread */
      gst_pad_link(pad, gst_element_get_pad(thread, "sink"));
    }
  else /* we already have a thread */
    {
      /* add parser to it */
      gst_bin_add(GST_BIN(thread), parser);
      /* link the decoder with the parser */
      gst_element_link(decoder, parser);
    }
  *element = parser;
  return thread;
}

void	pitivi_sourcefile_create_thread_ghost_pad (PitiviSourceFile *this, GstElement *lastelement, gchar *caps_str)
{

  if (lastelement)
    {
      GstPad	*temppad;
      
      if (strstr(caps_str, "video")) /* video*/
	{
	  GstElement	*sink;
	  temppad = gst_element_add_ghost_pad(this->pipeline, gst_element_get_pad(lastelement, "src"),
					      "src");
	  g_assert(temppad != NULL);
	  g_printf("adding ghost pad for video\n");
	  pitivi_sourcefile_get_length (this, lastelement);
	  gst_element_set_state (this->private->mainpipeline, GST_STATE_PAUSED);
	}
      else /* audio */
	{
	  temppad = gst_element_add_ghost_pad(this->pipeline, gst_element_get_pad(lastelement, "src"),
					      "asrc");
	  g_assert(temppad != NULL);
	  g_printf("adding ghost pad for audio\n");
	  pitivi_sourcefile_get_length (this, lastelement);
	}
    }
}

void	pitivi_sourcefile_create_raw_ghost_pad (PitiviSourceFile *this, GstPad *pad, gchar *caps_str)
{
  GstPad	*temppad;
	  
  if (strstr(caps_str, "video")) /* video*/
    {
      temppad = gst_element_add_ghost_pad(this->pipeline, pad,
					  "vsrc");
      g_assert(temppad != NULL);
      g_printf("linking raw pad to vsrc\n");
    }
  else
    {
      temppad = gst_element_add_ghost_pad(this->pipeline, pad,
					  "asrc");
      g_assert(temppad != NULL);
      g_printf("linking raw pad to asrc\n");
    }
}


GstElement*	
pitivi_sourcefile_finalize_pipeline_for_demuxer(PitiviSourceFile *this, gchar *filename)
{
  PitiviMainApp	*mainapp = this->private->mainapp;
  GstElement	*thread;
  GstElement	*decoder;
  GstElement	*parser;
//GstElement	*queue;
  GstElement	*lastelement;
  GstPad	*pad;
  GstCaps	*caps;
  GList       	*decoderlist;
  GSList	*padlist;
  GList		*parserlist;
  gchar		*caps_str;
  static gint	thread_number = 0;
  
  gst_element_set_state(GST_ELEMENT(this->pipeline), GST_STATE_PAUSED);
  padlist = this->private->padlist;
  while (padlist)
    {
      thread = NULL;
      pad = (GstPad*)padlist->data;
      caps = gst_pad_get_caps(pad);
      caps_str = gst_caps_to_string(caps);
      this->mediatype = caps_str;
      thread = decoder = parser = lastelement = NULL;

      while (pitivi_sourcefile_check_for_base_type(this->mediatype))
	{
	  decoderlist = pitivi_settings_get_flux_codec_list (G_OBJECT(mainapp->global_settings ), caps, DEC_LIST);
	  if (decoderlist)
	    {
	      thread = pitivi_sourcefile_add_decoder_for_demux(this, decoderlist, parser,
							       thread, thread_number, 
							       pad, &lastelement);					      
	    }
	  else
	    {
	      parserlist = pitivi_settings_get_flux_parser_list(G_OBJECT(mainapp->global_settings), caps, DEC_LIST);
	      if (parserlist)
		{
		  thread = pitivi_sourcefile_add_parser_for_demux(this, parserlist, thread,
								  thread_number, pad, &lastelement, decoder); 
		}

	    }
	}
      
      pitivi_sourcefile_set_media_property (this, caps_str);
      pitivi_sourcefile_create_thread_ghost_pad(this, lastelement, caps_str);

      if (thread)
	{
	  gst_element_set_state(GST_ELEMENT(thread), GST_STATE_READY);
	  thread_number++;
	}
      else /* we have a raw data pad */
	pitivi_sourcefile_create_raw_ghost_pad (this, pad, caps_str);
      
      padlist = padlist->next;
    }
  
  gst_element_set_state(GST_ELEMENT(this->pipeline), GST_STATE_PAUSED);
  return lastelement;
}

gboolean	pitivi_sourcefile_demuxer_fct (PitiviSourceFile * this, GstElement *src,
					       GList *demuxlist, gchar *filename,
					       GstElement *parser)
{
  GstElement	*demux;
  gchar		*tmpname;
  gint		i;

  /* choose the first demuxer */
  g_printf("adding demuxer [%s]\n", demuxlist->data);
  tmpname = g_strdup_printf("demux_%s", filename);
  demux = gst_element_factory_make((gchar*)demuxlist->data, tmpname);

  /* add gst_element to the list */
  
  pitivi_sourcefile_add_elm_to_list(this, (gchar *)demuxlist->data, "none", "demuxer");

  g_free(tmpname);
  g_assert(demux != NULL);
	  
  /* add the demuxer to the main pipeline */
  gst_bin_add(GST_BIN(this->pipeline), demux);
	  
  g_signal_connect(G_OBJECT(demux), "new_pad",
		   G_CALLBACK(pitivi_sourcefile_new_pad_created), this);
	  
  /* link element */
  if (parser)
    gst_element_link(parser, demux);
  else
    gst_element_link(src, demux);
  
  /* we need to run this part only for a demuxer */
  gst_element_set_state(GST_ELEMENT(this->private->mainpipeline), GST_STATE_PLAYING);
  for (i = 0; i < 50; i++)
    {
      gst_bin_iterate(GST_BIN(this->private->mainpipeline));
    }
  pitivi_sourcefile_finalize_pipeline_for_demuxer(this, filename);
  gst_element_set_state(GST_ELEMENT(this->private->mainpipeline), 
			GST_STATE_PAUSED);
	  
  /* we have already set all ghost pad here */
  return TRUE;
}

GstElement     	*pitivi_sourcefile_parser_fct(PitiviSourceFile *this, GstElement *src,
					      GstElement **element, GList *parserlist, gchar *filename)
{
  GstElement	*parser;
  GstElement	*lastelement;
  gchar		*tmpname;

  lastelement = *element;
  g_printf("adding parser [%s] for this caps ==> %s\n", 
	   parserlist->data, gst_caps_to_string(this->private->mediacaps));
  tmpname = g_strdup_printf("parser_%s", filename);
  parser = gst_element_factory_make((gchar*)parserlist->data, tmpname);
  
  /* add gst_element to the list */
  pitivi_sourcefile_add_elm_to_list(this, (gchar*)parserlist->data, "none", "parser");

  g_free(tmpname);
  g_assert(parser != NULL);

  /*add the parser to the main pipeline */
  gst_bin_add(GST_BIN(this->pipeline), parser);
  gst_element_link(src, parser);
		  
  this->mediatype = gst_caps_to_string(gst_pad_get_caps(gst_element_get_pad(parser, "src")));
  this->private->mediacaps = gst_pad_get_caps(gst_element_get_pad(parser, "src"));
  pitivi_sourcefile_set_media_property(this, this->private->mainmediatype);
  lastelement = parser;
  return parser;
}

gboolean	pitivi_sourcefile_decoder_fct(PitiviSourceFile *this, GstElement *src, 
					      GstElement **element, GList *decoderlist, gchar *filename)
{
  GstElement	*decoder;
  gchar		*tmpname;
  GstEvent	*event;
  GstFormat	format;
  gint64	value;
  GstElement	*lastelement;
  gboolean	element_found;
  lastelement = *element;

  element_found = 0;
  /* choose the first decoder */
  g_printf("adding a decoder [%s] for this caps ==> %s\n", 
	    decoderlist->data, gst_caps_to_string(this->private->mediacaps));
  tmpname = g_strdup_printf("decoder_%s", filename);
  decoder = gst_element_factory_make((gchar*)decoderlist->data, tmpname);
  g_free(tmpname);
  g_assert(decoder != NULL);
	      
  /*add the decoder to the main pipeline */
  gst_bin_add(GST_BIN(this->pipeline), decoder);
  gst_element_link(src, decoder);
  this->mediatype = gst_caps_to_string(gst_pad_get_caps(gst_element_get_pad(decoder, "src")));
  this->private->mediacaps = gst_pad_get_caps(gst_element_get_pad(decoder, "src"));
  pitivi_sourcefile_set_media_property (this, this->private->mainmediatype);
  element_found = TRUE;
  lastelement = decoder;
  return element_found;
}

void		pitivi_sourcefile_finalize_pipeline (PitiviSourceFile *this, GstElement *src)
{
  /* adding fakesink */
  if (this->haveaudio && src)
    pitivi_sourcefile_get_length (this, src);
  else if (this->havevideo)
    {
      pitivi_sourcefile_get_length (this, src);
      gst_element_set_state (this->private->mainpipeline, GST_STATE_PAUSED);
    }
  /* need to do this */
  gst_object_ref(GST_OBJECT(this->pipeline));
  gst_bin_remove(GST_BIN(this->private->mainpipeline), this->pipeline);
  gst_object_unref( (GstObject *) this->private->mainpipeline);
}

void		pitivi_sourcefile_create_ghost_pad (PitiviSourceFile *this, GstElement *lastelement)
{
    GstPad *temppad;

    if (strstr(this->mediatype, "video"))
      {
	temppad = gst_element_add_ghost_pad(this->pipeline, 
					    gst_element_get_pad(lastelement, "src"),
					    "vsrc");
	g_assert(temppad != NULL);
	g_printf("adding ghost pad video in the bin pipeline\n");
      }
    else /* audio */
      {
	temppad = gst_element_add_ghost_pad(this->pipeline, 
					    gst_element_get_pad(lastelement, "src"),
					    "asrc");
	g_assert(temppad != NULL);
	g_printf("adding ghost pad audio in the bin pipeline\n");
      }
}

GstElement	*pitivi_sourcefile_init_pipeline(PitiviSourceFile *this, gchar *filename)
{
  GstElement	*src;
  gchar		*tmpname;

  /* create a pipeline */
  tmpname = g_strdup_printf("pipeline_%s", filename);
  this->private->mainpipeline = gst_pipeline_new(tmpname);
  g_free(tmpname);
  g_assert(this->private->mainpipeline != NULL);

  /* create a bin */
  tmpname = g_strdup_printf("bin_%s", filename);
  this->pipeline = gst_bin_new(tmpname);
  g_free(tmpname);
  gst_bin_add(GST_BIN(this->private->mainpipeline), this->pipeline);
  
  /* create a file reader */
  tmpname = g_strdup_printf("src_%s", filename);
  src = gst_element_factory_make("filesrc", tmpname);

  /* add gst_element to the list */
  pitivi_sourcefile_add_elm_to_list (this, "filesrc", "none", "filereader");

  g_free(tmpname);
  g_object_set(G_OBJECT(src), "location", filename, NULL);
  /* add the file reader to the pipeline */
  gst_bin_add(GST_BIN(this->pipeline), src);
  g_signal_connect(G_OBJECT(src), "eos",
		   G_CALLBACK(pitivi_sourcefile_eof), NULL);
  return src;
}

gboolean	pitivi_sourcefile_check_for_base_type (gchar *mediatype)
{
  gint	i;

  i = 0;
/*   g_printf("mediatype to match ==> %s\n", mediatype); */

  while (BaseMediaType[i])
    {
     /*  g_printf("Base Media Type ==> %s\n", BaseMediaType[i]); */
      if (strstr(mediatype, BaseMediaType[i]))
	return FALSE;
      i++;
    }
  return TRUE;
}

gboolean	pitivi_sourcefile_build_pipeline_by_mime (PitiviSourceFile *this, gchar *filename)
{
  GList *elements;
  GstElement	*src;
  GstElement	*parser;
  GstElement	*lastelement;

  /*list des different media de decompression*/
  GList		*demuxlist;
  GList		*decoderlist;
  GList		*parserlist;
  gboolean	element_found;
  PitiviMainApp	*mainapp = this->private->mainapp;
  
  /* Init some variables */
  parser = lastelement = NULL;
  this->private->padlist = NULL;
  this->private->elmlist = NULL;
  element_found = FALSE;
  
  // init global
  src = pitivi_sourcefile_init_pipeline(this, filename);
  
  /* loop until we found the base type */
  while ( pitivi_sourcefile_check_for_base_type (this->mediatype) && !element_found)
    {
      /* test if it's a container */
      demuxlist = pitivi_settings_get_flux_container_list (G_OBJECT(mainapp->global_settings),
							   this->private->mediacaps, DEC_LIST);
      /* create a demuxer if it's a container */
      if (demuxlist)
	element_found = pitivi_sourcefile_demuxer_fct(this, src, demuxlist, filename, parser);
      else /* search for a decoder */
	{
	  decoderlist = pitivi_settings_get_flux_codec_list (G_OBJECT(mainapp->global_settings), 
							     this->private->mediacaps, DEC_LIST);
	  if (decoderlist)
	    {
	      element_found = pitivi_sourcefile_decoder_fct(this, src, &lastelement, decoderlist, filename);  
	      
	    }
	  else /* search for parser */
	    {
	      parserlist = pitivi_settings_get_flux_parser_list(G_OBJECT(mainapp->global_settings), 
								this->private->mediacaps, DEC_LIST);
	      if (parserlist)
		{
		  parser = pitivi_sourcefile_parser_fct (this, src, &lastelement, parserlist, filename);
		  element_found = 0;
		}
	      else
		g_printf("no parser found\n");
	    }
	}
    }
  if (lastelement)
    pitivi_sourcefile_create_ghost_pad (this, lastelement);
  pitivi_sourcefile_finalize_pipeline(this, src);
}

void	pitivi_sourcefile_make_init_audio_pipeline(PitiviSourceFile *this, GstElement *src,
						   gchar *filename)
{
  gchar	*tmpname;

    /* create a pipeline */
  tmpname = g_strdup_printf("audio_pipeline_%s", filename);
  this->private->mainpipeline = gst_pipeline_new(tmpname);
  g_free(tmpname);
  g_assert(this->private->mainpipeline != NULL);

  /* create a bin */
  tmpname = g_strdup_printf("bin_audio_%s", filename);
  this->pipeline_audio = gst_bin_new(tmpname);
  g_free(tmpname);

  gst_bin_add(GST_BIN(this->private->mainpipeline), this->pipeline_audio);
  
  g_object_set(G_OBJECT(src), "location", filename, NULL);

  /* add the file reader to the pipeline */
  gst_bin_add(GST_BIN(this->pipeline_audio), src);
  g_signal_connect(G_OBJECT(src), "eos",
		   G_CALLBACK(pitivi_sourcefile_eof), NULL);
}

void	
pitivi_sourcefile_new_audio_pad_created (GstElement *parse, GstPad *pad, gpointer data)
{
  PitiviSourceFile *this = (PitiviSourceFile*)data;
  PitiviListElm	*elm_list;
  GSList	*list;
  GstElement	*decoder;
  GstCaps	*caps;
  gchar		*caps_str;
  gboolean	flag;
  GstPad	*temppad;

  g_printf("a new pad [%s] was created\n", gst_pad_get_name(pad));
  caps = gst_pad_get_caps(pad);
  caps_str = gst_caps_to_string(caps);
  
  flag = FALSE;
  gst_element_set_state(this->private->mainpipeline, GST_STATE_PAUSED);

  if (strstr(caps_str, "audio"))
    {
      list = this->private->elmlist;
      while (list)
	{
	  elm_list = (PitiviListElm*)list->data;
	  if (!strncmp(elm_list->type, "audio", 5))
	    {
	      if (!strncmp(elm_list->category, "decoder", 6))
		{
		  flag = TRUE;
		  this->private->havepad = TRUE;

		  g_printf("create audio decoder [%s]\n", elm_list->name);
		  decoder = gst_element_factory_make(elm_list->name, "decoder_audio");
		  gst_bin_add(GST_BIN(this->pipeline_audio), decoder);

		  gst_pad_link(pad, gst_element_get_pad(decoder, "sink"));
		  
		  temppad = gst_element_add_ghost_pad(this->pipeline_audio, 
						      gst_element_get_pad(decoder, "src"),
						      "asrc");
		  g_assert(temppad != NULL);
		  
		  g_printf("adding ghost pad asrc\n");
		}
	      }
	  list = g_slist_next(list);
	}
      if (!flag) 
	{
	  this->private->havepad = TRUE;
	  g_printf("adding audio raw ghost pad\n");
	  temppad = gst_element_add_ghost_pad(this->pipeline_audio, pad,
					      "asrc");
	  g_assert(temppad != NULL);
	  
	  g_printf("linking raw pad to asrc\n");
	}
    }

    gst_element_set_state(this->private->mainpipeline, GST_STATE_PLAYING);
}

void
pitivi_sourcefile_make_demuxer_audio_pipeline(PitiviSourceFile *this, GstElement *demux, 
					      GstElement *last)
{
  gint	i;

  /* add the demuxer to the main pipeline */
  gst_bin_add(GST_BIN(this->pipeline_audio), demux);
	  
  g_signal_connect(G_OBJECT(demux), "new_pad",
		   G_CALLBACK(pitivi_sourcefile_new_audio_pad_created), this);
	  
  /* link element */
  gst_element_link(last, demux);
  
  /* we need to run this part only for a demuxer */

  gst_element_set_state(GST_ELEMENT(this->private->mainpipeline), GST_STATE_PLAYING);

  this->private->havepad = FALSE;

  for (i = 0; i < 50; i++)
    {
      gst_bin_iterate(GST_BIN(this->private->mainpipeline));
      //g_printf("iterate audio pipeline\n");
      if (this->private->havepad)
	{
	  g_printf("found audio pad at [%d]\n", i);
	  break;
	}
    }
	  
  gst_element_set_state(GST_ELEMENT(this->private->mainpipeline), 
			GST_STATE_PAUSED);

  gst_object_ref(GST_OBJECT(this->pipeline_audio));

  gst_bin_remove(GST_BIN(this->private->mainpipeline), 
		 this->pipeline_audio);

  gst_object_unref( (GstObject *) this->private->mainpipeline);
}


void	pitivi_sourcefile_make_audio_pipeline (PitiviSourceFile *this, gchar *filename)
{
  GSList	*list;
  PitiviListElm	*elm_list;
  gchar		*tmpname;
  GstElement	*elm, *lastelm;

  g_printf("make audio pipeline\n");
  list = this->private->elmlist;
  while (list)
    {
      elm_list = (PitiviListElm*)list->data;
      if (!strcmp(elm_list->type, "none"))
	{
	  g_printf("element type [%s]\n", elm_list->type);
	  g_printf("element name [%s]\n", elm_list->name);
	  tmpname = g_strdup_printf("src_audio_[%s]_pipeline", elm_list->name);
	  elm = gst_element_factory_make(elm_list->name, tmpname);
	  if (!strcmp(elm_list->category, "filereader"))
	    {
	      g_printf("Make file reader\n");
	      pitivi_sourcefile_make_init_audio_pipeline(this, elm, filename);
	    }
	  if (!strcmp(elm_list->category, "demuxer"))
	    {
	      g_printf("Make demuxer\n");
	      pitivi_sourcefile_make_demuxer_audio_pipeline(this, elm, lastelm);
	    }
	  if (!strcmp(elm_list->category, "parser"))
	    {
	      g_printf("Make parser\n");
	      pitivi_sourcefile_make_parser_pipeline(this->pipeline_audio, elm, lastelm);
	    }
	}
      else if (!strcmp(elm_list->type, "audio"))
	{
	  g_printf("element type [%s]\n", elm_list->type);
	  g_printf("element [%s]\n", elm_list->name);
	}
      lastelm = elm;
      list = g_slist_next(list);
    }
}

void	pitivi_sourcefile_type_find (PitiviSourceFile *this)
{
  GstElement	*pipeline;
  GstElement	*source;
  GstElement	*typefind;
  gchar		*filename;

  filename = this->filename;

  pipeline = gst_pipeline_new (NULL);
  source = gst_element_factory_make("filesrc", "source");
  g_assert(GST_IS_ELEMENT(source));

  typefind = gst_element_factory_make("typefind", "typefind");
  g_assert(GST_IS_ELEMENT(typefind));

  gst_bin_add_many(GST_BIN(pipeline), source, typefind, NULL);
  gst_element_link(source, typefind);

  g_signal_connect(G_OBJECT(typefind), "have-type",
		   G_CALLBACK(pitivi_sourcefile_have_type_handler), this);

  gst_element_set_state(GST_ELEMENT(pipeline), GST_STATE_NULL);
  g_object_set(source, "location", filename, NULL);
  gst_element_set_state(GST_ELEMENT(pipeline), GST_STATE_PLAYING);

  while (this->mediatype == NULL) {
    gst_bin_iterate(GST_BIN(pipeline));
  }

  gst_element_set_state(GST_ELEMENT(pipeline), GST_STATE_NULL);

  if (!strstr(this->mediatype, "video") 
      && !strstr(this->mediatype, "audio")
      && !strstr(this->mediatype, "application/ogg")
      && !strstr(this->mediatype, "application/x-id3") )
    this->mediatype = NULL;
  
  g_object_unref(pipeline);

  if (this->mediatype == NULL)
    return;
  
  this->infovideo = NULL;
  this->infoaudio = NULL;
  this->length = 0;
  this->havevideo = FALSE;
  this->haveaudio = FALSE;
  
  /*   save main stream */
  this->private->mainmediatype = this->mediatype;
  
  pitivi_sourcefile_build_pipeline_by_mime (this, filename);
  
  /* restore main mime type */
  g_free(this->mediatype);
  this->mediatype = NULL;

  
  if (this->havevideo && !this->haveaudio)
    this->mediatype = g_strdup("video");
  if (this->haveaudio && this->havevideo)
    {
      this->mediatype = g_strdup("video/audio");
      pitivi_sourcefile_make_video_pipeline(this, filename);
      pitivi_sourcefile_make_audio_pipeline(this, filename);
    }
  if (this->haveaudio && !this->havevideo)
    this->mediatype = g_strdup("audio");
}


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
  return sourcefile;
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
  
  PitiviSourceFile	*this = PITIVI_SOURCEFILE(obj);
  pitivi_sourcefile_type_find (this);
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
  
  /* Make sure dispose does not run twice. */
  this->private->dispose_has_run = TRUE;	
  G_OBJECT_CLASS (parent_class)->dispose (object);
}

static void
pitivi_sourcefile_finalize (GObject *object)
{
  PitiviSourceFile	*this = PITIVI_SOURCEFILE(object);
  g_free (this->private);
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
							 G_PARAM_READWRITE | G_PARAM_CONSTRUCT));
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
