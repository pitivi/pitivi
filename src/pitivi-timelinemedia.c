/* 
 * PiTiVi
 * Copyright (C) <2004> Guillaume Casanova <casano_g@epita.fr>
 *                      Raphael Pralat <pralat_r@epita.fr>
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

#include <gnl/gnloperation.h>
#include <gnl/gnlsource.h>
#include "pitivi.h"
#include "pitivi-effectswindowproperties.h"
#include "pitivi-timelinemedia.h"
#include "pitivi-menu.h"
#include "pitivi-cursor.h"
#include "pitivi-effectswindow.h"
#include "pitivi-dragdrop.h"
#include "pitivi-sourceitem.h"
#include "pitivi-stockicons.h"
#include "pitivi-drawing.h"
#include "pitivi-thumbs.h"

static	GtkWidgetClass	*parent_class = NULL;

/*
 **********************************************************
 * Headers  					          *
 *							  *
 **********************************************************
*/

/* drawing */

void
draw_media (GtkWidget *widget);
void 
draw_media_expose (GtkWidget *widget);
void
draw_selection (GtkWidget *widget, int width, char **dash);
void
draw_slide (GtkWidget *widget, int start, int end);

/* Timeline Media Callback  */

void
pitivi_timelinemedia_callb_associate_effect (PitiviTimelineMedia *this, gpointer data);

// Properties Enumaration

typedef enum {
  PROP_MEDIA_TYPE = 1, 
  PROP_MEDIA_WIDTH, 
  PROP_SOURCEFILE,
  PROP_TRACK
} PitiviMediaProperty;

/*
 **********************************************************
 * Signals  					          *
 *							  *
 **********************************************************
*/

enum
  {
    MEDIA_DRAG_GET_SIGNAL,
    MEDIA_DRAG_MOTION_SIGNAL,
    MEDIA_DRAG_LEAVE_SIGNAL,
    MEDIA_DRAG_DROP_SIGNAL,
    MEDIA_DRAG_RECEIVED_SIGNAL,
    MEDIA_DESELECT_SIGNAL,
    MEDIA_SELECT_SIGNAL,
    MEDIA_DISSOCIATE_SIGNAL,
    MEDIA_ASSOCIATE_EFEFCT_SIGNAL,
    MEDIA_SNAPPED_EFEFCT_SIGNAL,
    LAST_SIGNAL
  };

static guint	      media_signals[LAST_SIGNAL] = {0};


/*
 **********************************************************
 * Source drag 'n drop on a widget		          *
 *							  *
 **********************************************************
*/

static GtkTargetEntry TargetSameEntry[] =
  {
    { "pitivi/media/sourceeffect", GTK_TARGET_SAME_APP,  DND_TARGET_EFFECTSWIN },
    { "pitivi/sourcetimeline", GTK_TARGET_SAME_APP, DND_TARGET_TIMELINEWIN }
  };

static gint iNbTargetSameEntry = G_N_ELEMENTS (TargetSameEntry);


/*
 **********************************************************
 * Popup  					          *
 *							  *
 **********************************************************
*/

/* headers */

void	pitivi_timelinemedia_callb_cut (PitiviTimelineMedia *this, gpointer data);
void	pitivi_timelinemedia_callb_copied (PitiviTimelineMedia *this, gpointer data);
void	pitivi_timelinemedia_callb_dissociate (PitiviTimelineMedia *this, gpointer data);
void	pitivi_timelinemedia_callb_properties (PitiviTimelineMedia *this, gpointer data);


static GtkItemFactoryEntry  TimeItemPopup[] = {
  {"/Dissociate", NULL, pitivi_timelinemedia_callb_dissociate, 0, "<Item>", NULL},
  {"/Delete", NULL, pitivi_timelinemedia_callb_destroy, 1, "<Item>", NULL},
  {"/Sep1", NULL, NULL, 0, "<Separator>"},
  {"/Copy", NULL, pitivi_timelinemedia_callb_copied, 0, "<Item>", NULL},
  {"/Cut", NULL, pitivi_timelinemedia_callb_cut, 0, "<Item>", NULL},
  {"/Sep1", NULL, NULL, 0, "<Separator>"},
  {"/Properties", NULL,  pitivi_timelinemedia_callb_properties, 0, "<Item>", NULL},
};

static gint	iNbTimeItemPopup = sizeof(TimeItemPopup)/sizeof(TimeItemPopup[0]);


/*
 **********************************************************
 * Private Structure 				          *
 * used for internals variables and operations		  *
 **********************************************************
*/

struct _PitiviTimelineMediaPrivate
{
  /* instance private members */
  
  PitiviCursorType cursor_type;
  PitiviTimelineCellRenderer *cell;
  PitiviSourceFile *sf;
  GdkGC		   **gcs;
  
  /* Popup */
  GtkWidget	   *menu;
  GtkTooltips	   *tooltips;
  
  /* Media */
  int		   width;
  int 		   media_type;
  guint64	   original_width;
  guint64	   original_height;
  gboolean	   dispose_has_run;
  
  // Caching Operation
  PitiviThumbTab   **thumbs;
  GdkPixmap	   *pixmapcache;
  GdkPixbuf	   *pixbuf;
};

/**
 * pitivi_timelinemedia_new:
 * @PitiviSourceFile: the file source
 * @int: the width of the source file
 * @PitiviTimelineCellRenderer: the track to put the media into
 *
 * Creates a new element media
 *
 * Returns: An element PitiviTimelineMedia contening the media
 */

PitiviTimelineMedia *
pitivi_timelinemedia_new ( PitiviSourceFile *sf, int width, PitiviTimelineCellRenderer *track )
{
  PitiviTimelineMedia	*this;
  PitiviLayerType	type;
 
  g_printf("PitiviTimelineMedia new, sf = %p\n", sf);
  type = PITIVI_NO_TRACK;
  if (sf)
    type = pitivi_check_media_type (sf);
  
  this = (PitiviTimelineMedia *) g_object_new(PITIVI_TIMELINEMEDIA_TYPE,
						       "source_file",
						       sf,
						       "media_type",
						       type,
						       "width",
						       width,
						       "track",
						       track,
						       NULL);
  track->nb_added[0] += 1; 
  return this;
}

void
pitivi_timelinemedia_update_tooltip (PitiviTimelineMedia *this)
{
  char			*str;
  GnlObject		*obj = this->sourceitem->gnlobject;

  /* Make the string */
  str = g_strdup_printf("%s\nposition : %4lld:%3lld->%4lld:%3lld\nMedia : %4lld:%3lld->%4lld:%3lld\nPriority : %d\n",
			gst_element_get_name(GST_ELEMENT (obj)),
			(signed long long int) (obj->start / GST_SECOND),
			(signed long long int) ((obj->start % GST_SECOND) / GST_MSECOND),
			(signed long long int) (obj->stop / GST_SECOND), 
			(signed long long int) ((obj->stop % GST_SECOND) / GST_MSECOND),
			(signed long long int) (obj->media_start / GST_SECOND), 
			(signed long long int) ((obj->media_start % GST_SECOND) / GST_MSECOND),
			(signed long long int) (obj->media_stop / GST_SECOND), 
			(signed long long int) ((obj->media_stop % GST_SECOND) / GST_MSECOND),
			obj->priority);
  gtk_tooltips_set_tip (this->private->tooltips, GTK_WIDGET(this),
			str, NULL);
  g_free(str);
}

/**
 * pitivi_timelinemedia_get_start_stop:
 * @PitiviTimelineMedia: the media
 * @gint64: the begining of the media
 * @gint64: the end of the media
 *
 * Get the begining and the end of a media in the timeline
 *
 */

void
pitivi_timelinemedia_get_start_stop (PitiviTimelineMedia *media, gint64 *start, gint64 *stop)
{
  gnl_object_get_start_stop(media->sourceitem->gnlobject, start, stop);
}

/**
 * pitivi_timelinemedia_set_start_stop:
 * @PitiviTimelineMedia: the media
 * @gint64: the begining of the media
 * @gint64: the end of the media
 *
 * Set the begining and the end of a media in a timeline
 *
 */

void
pitivi_timelinemedia_set_start_stop (PitiviTimelineMedia *media, gint64 start, gint64 stop)
{
  gnl_object_set_start_stop (media->sourceitem->gnlobject, start, stop);
  pitivi_timelinemedia_update_tooltip(media);
}

/**
 * pitivi_timelinemedia_put:
 * @PitiviTimelineMedia: the media
 * @gint64: the begining of the media
 *
 * Place the media in the timeline
 *
 */

void
pitivi_timelinemedia_put (PitiviTimelineMedia *media, gint64 start)
{
  gint64 mstart, mstop;

  // check the size of the widget !!!
  gnl_object_get_media_start_stop (media->sourceitem->gnlobject, &mstart, &mstop);
  gnl_object_set_start_stop (media->sourceitem->gnlobject, start, start + mstop - mstart);
  pitivi_timelinemedia_update_tooltip(media);
}

/**
 * pitivi_timelinemedia_get_media_start_stop:
 * @PitiviTimelineMedia: the media
 * @gint64: the begining of the media
 * @gint64: the end of the media
 *
 * Get media between the begining and the end selected
 *
 */

void
pitivi_timelinemedia_get_media_start_stop (PitiviTimelineMedia *media, gint64 *start, gint64 *stop)
{
  gnl_object_get_media_start_stop (media->sourceitem->gnlobject, start, stop);
}

/**
 * pitivi_timelinemedia_set_media_start_stop:
 * @PitiviTimelineMedia: the media
 * @gint64: the begining of the media
 * @gint64: the end of the media
 *
 * Set media between the begining and the end selected
 *
 */

void
pitivi_timelinemedia_set_media_start_stop (PitiviTimelineMedia *media, gint64 start, gint64 stop)
{
  gnl_object_set_media_start_stop (media->sourceitem->gnlobject, start, stop);
  pitivi_timelinemedia_update_tooltip(media);
}

/**
 * pitivi_timelinemedia_set_media_start_stop:
 * @PitiviTimelineMedia: the media
 * @gint: the priority
 *
 * Set the media priority
 *
 */

void
pitivi_timelinemedia_set_priority (PitiviTimelineMedia *media, gint priority)
{
  gnl_object_set_priority (media->sourceitem->gnlobject, priority);
  pitivi_timelinemedia_update_tooltip (media);
}

/**
 * pitivi_timelinemedia_get_track:
 * @PitiviTimelineMedia: the media
 *
 * Get the track where the media is in
 *
 * Returns: A media widget
 */

GtkWidget *
pitivi_timelinemedia_get_track (PitiviTimelineMedia *media)
{
  return GTK_WIDGET (media->private->cell);
}


void
draw_video_thumbs (PitiviTimelineMedia	*this, GdkPixbuf **pixs, int nb, int width)
{
  GdkPixbuf*  scale;
  int count, i = 0;

  for (i=0,count=0; i < nb; i++, count+=width)
    {
      if (pixs[i] && GDK_IS_PIXBUF (pixs[i]))
	{
	  scale = gdk_pixbuf_scale_simple
	    (GDK_PIXBUF (pixs[i]),
	     width,
	     GTK_WIDGET (this->track)->allocation.height,
	     GDK_INTERP_NEAREST);
	  
	  gdk_draw_pixbuf( this->private->pixmapcache, GTK_WIDGET(this)->style->white_gc, 
			   scale, 
			   0, 0,
			   count+1, 0,
			   width,
			   GTK_WIDGET (this->track)->allocation.height,
			   GDK_RGB_DITHER_MAX, 0, 0);
	  
	  gdk_draw_line (this->private->pixmapcache,
			 GTK_WIDGET(this)->style->white_gc,
			 count, 0, count, GTK_WIDGET (this->track)->allocation.height);
	  g_free (scale);
	}
    }
}

void
show_video_media (GtkWidget *widget)
{
  PitiviTimelineMedia	*this = PITIVI_TIMELINEMEDIA (widget);
  GdkPixbuf *pixs[this->sourceitem->srcfile->nbthumbs+1];
  int pix_width, width, i,j, nb_img = 0;
  
  if (GTK_IS_WIDGET ( widget ) )
    {
      if (this->private->thumbs && this->private->thumbs[0])
	{
	  pix_width = gdk_pixbuf_get_width ( this->private->thumbs[0]->pixbuf );
	  for (i=0; i<this->sourceitem->srcfile->nbthumbs; i++) pixs[i] = NULL;
	  if (widget->allocation.width < pix_width)
	    {
	      pixs[0] = this->private->thumbs[0]->pixbuf;
	      draw_video_thumbs (this, pixs, 1, widget->allocation.width);
	    }
	  else
	    {
	      nb_img = widget->allocation.width / pix_width;
	      if ( nb_img < this->sourceitem->srcfile->nbthumbs)
		{
		  j = 0;
		  for (i=0; i<this->sourceitem->srcfile->nbthumbs && j < nb_img; i++)
		    {
		      pixs[j] = this->private->thumbs[i]->pixbuf;
		      j++;
		    }
		  pixs[nb_img] = this->private->thumbs[this->sourceitem->srcfile->nbthumbs-1]->pixbuf;
		  draw_video_thumbs (this, pixs, nb_img,  widget->allocation.width / nb_img);
		}
	      else
		{
		  if (this->sourceitem->srcfile->nbthumbs)
		    width = widget->allocation.width / this->sourceitem->srcfile->nbthumbs;
		  else
		    width = widget->allocation.width;
		  for (i=0; i<this->sourceitem->srcfile->nbthumbs; i++) pixs[i] = this->private->thumbs[i]->pixbuf;
		  draw_video_thumbs (this, pixs, this->sourceitem->srcfile->nbthumbs, width);
		}
	    }
	}
    }
}

void
draw_media_expose (GtkWidget *widget)
{
  GdkRectangle rect;

  draw_media ( widget );
  /* Send Expose Event */
  rect.x = 0;
  rect.y = 0;
  rect.width  = widget->allocation.width;
  rect.height = widget->allocation.height;
  gdk_window_invalidate_rect (widget->window, &rect, FALSE);
  /* End Sending Expose Event */
}

void
show_effects_media (GtkWidget *widget)
{
  PitiviTimelineMedia	*this = PITIVI_TIMELINEMEDIA (widget);
  int count, pix_width, width = 0;
  
  if (GTK_IS_WIDGET ( widget ))
    {
      width = widget->allocation.width;
      if (width <= 1)
	width = this->private->width;
      if ( this->sourceitem->srcfile->thumbs_effect )
	{
	  pix_width = gdk_pixbuf_get_width (this->sourceitem->srcfile->thumbs_effect);
	  for (count = 0; count < width; count+= pix_width )
	    gdk_draw_pixbuf( this->private->pixmapcache, NULL, GDK_PIXBUF 
			     (  this->sourceitem->srcfile->thumbs_effect  ), 0, 0, count, 0, -1, -1,
			     GDK_RGB_DITHER_MAX, 0, 0);
	}
    }
}

void
show_audio_media (GtkWidget *widget)
{
  PitiviTimelineMedia	*this = PITIVI_TIMELINEMEDIA (widget);

  if ( this->sourceitem->srcfile->thumbs_audio  )
    gdk_draw_pixbuf( this->private->pixmapcache, NULL, GDK_PIXBUF 
		     ( this->sourceitem->srcfile->thumbs_audio ), 0, 0, 1, 1, 
		     -1, 
		     -1, 
		     GDK_RGB_DITHER_MAX, 0, 0);
  else
    { 
      gdk_draw_line ( this->private->pixmapcache,
		     widget->style->black_gc,
		     0,  GTK_WIDGET (this->track)->allocation.height/2, 
		     widget->allocation.width, GTK_WIDGET (this->track)->allocation.height/2);
    }
}

void
draw_media (GtkWidget *widget)
{
  PitiviTimelineMedia *this = (PitiviTimelineMedia *)widget;
  
  if (GDK_IS_PIXMAP ( this->private->pixmapcache ))
    {
      gdk_draw_rectangle ( this->private->pixmapcache, 
			   widget->style->white_gc,
			   TRUE, 0, 0,
			   -1, -1);
      switch (((PitiviTimelineCellRenderer *)this->track)->track_type)
	{
	case PITIVI_AUDIO_TRACK:
	  show_audio_media (widget);
	  break;
	case PITIVI_VIDEO_TRACK:
	  show_video_media (widget);
	  break;
	case PITIVI_EFFECTS_TRACK:
	case PITIVI_TRANSITION_TRACK:
	  show_effects_media (widget);
	  break;
	default:
	  break;
	}
        
      if (this->selected)
	{
	  GdkColor selection = {1, 65535, 0, 0};
	  draw_selection_dash (widget, this->private->pixmapcache, &selection, 2);
	}        
      gdk_draw_rectangle ( this->private->pixmapcache, 
			   widget->style->black_gc,
			   FALSE, 0, 0,
			   widget->allocation.width-1,  widget->allocation.height-1);
    }
}

static gint
pitivi_timelinemedia_expose (GtkWidget      *widget,
			     GdkEventExpose *event)
{
  PitiviTimelineMedia  *this = PITIVI_TIMELINEMEDIA (widget);
  
  gdk_draw_drawable (GDK_WINDOW (widget->window),
			 widget->style->bg_gc[GTK_WIDGET_STATE (widget)],
			 this->private->pixmapcache,
			 event->area.x, event->area.y,
			 event->area.x, event->area.y,
			 event->area.width, event->area.height);
  return FALSE;
}



static GObject *
pitivi_timelinemedia_constructor (GType type,
				  guint n_construct_properties,
				  GObjectConstructParam * construct_properties)
{
  GObject	*object;
  PitiviTimelineMedia *this;
  gchar		*name;
  GstElement	*bin;
  
  /* Constructor  */
  object = (* G_OBJECT_CLASS (parent_class)->constructor) 
    (type, n_construct_properties, construct_properties);
  
  this = (PitiviTimelineMedia *) object;
  
  /* Tooltip  */
  
  this->private->tooltips = gtk_tooltips_new();
  
  /* Source Item  */

  this->sourceitem = g_new0 (PitiviSourceItem, 1);
  this->sourceitem->srcfile = this->private->sf;
  this->sourceitem->id = this->track->nb_added[0];
  
  if (this->track->track_type == PITIVI_AUDIO_TRACK)
    this->sourceitem->isaudio = TRUE;

  if ( this->sourceitem->srcfile )
    {    
      name = g_strdup_printf ("%s_%s_%lld", this->sourceitem->srcfile->filename, 
			      this->sourceitem->srcfile->mediatype, (signed long long int) (this->sourceitem->id));
      if ( this->track->track_type == PITIVI_EFFECTS_TRACK ||  this->track->track_type == PITIVI_TRANSITION_TRACK )
	{
	  if (!(bin = pitivi_sourcefile_get_effect_bin(this->sourceitem->srcfile))) {
	    g_warning ("Coudn't get Sourcefile effect bin");
	    return NULL;
	  }
	  this->sourceitem->gnlobject = (GnlObject *)gnl_operation_new (name, bin);
	  if ( this->track->track_type == PITIVI_TRANSITION_TRACK ) /* please let the prority set here. Thank you */
	    pitivi_timelinemedia_set_priority (this, 1);
	}
      else if ( this->track->track_type == PITIVI_VIDEO_TRACK )
	{
	  if (!(bin = pitivi_sourcefile_get_video_bin(this->sourceitem->srcfile)))
	    return NULL;
	  this->sourceitem->gnlobject = (GnlObject *)gnl_source_new (name, bin);
	  this->private->thumbs = this->sourceitem->srcfile->thumbs;
	}
      else if ( this->track->track_type == PITIVI_AUDIO_TRACK )
	{
	  if (!(bin = pitivi_sourcefile_get_audio_bin(this->sourceitem->srcfile)))
	    return NULL;
	  this->sourceitem->gnlobject = (GnlObject *) gnl_source_new (name, bin);
	}
    }
  this->original_width = this->private->width;
  gtk_widget_set_size_request (GTK_WIDGET (this), this->private->width, GTK_WIDGET (this->track)->allocation.height);
  gtk_drawing_area_size (GTK_DRAWING_AREA (this), this->private->width, GTK_WIDGET (this->track)->allocation.height);
  /* Setting Tooltip */
  pitivi_timelinemedia_update_tooltip (this);
  g_printf("pitivi_timelinemedia_constructor END\n");
  return object;
}


static void
pitivi_timelinemedia_drag_get  (GtkWidget          *widget,
				GdkDragContext     *context,
				GtkSelectionData   *selection_data,
				guint               info,
				guint32             time,
				gpointer	    dragging)
{
  gtk_selection_data_set (selection_data, selection_data->target, 
			  8, (void *) widget, 
			  sizeof (*widget));
}

static void
pitivi_timelinemedia_drag_data_received (GObject *widget,
                                         GdkDragContext *dc,
                                         int x,
                                         int y,
                                         GtkSelectionData *selection,
                                         guint info,
                                         guint time,
                                         gpointer data)
{
  PitiviSourceFile **sf;
  GtkWidget *source;
  
  source = gtk_drag_get_source_widget(dc);
  sf = (PitiviSourceFile **) selection->data;
  if (PITIVI_IS_EFFECTSWINDOW (gtk_widget_get_toplevel (source)))
      pitivi_timelinemedia_callb_associate_effect (PITIVI_TIMELINEMEDIA (widget), *sf);
}

static gboolean
pitivi_timelinemedia_drag_drop (GtkWidget *widget, 
				GdkDragContext *dc, 
				gint x, 
				gint y, 
				guint time,
				gpointer data)
     
{
  g_printf ("dropping media ..\n");
  return FALSE;
}

static void
connect_drag_and_drop (GtkWidget *widget)
{
  media_signals[MEDIA_DRAG_GET_SIGNAL] = g_signal_connect (G_OBJECT (widget), "drag_data_get",	      
							   G_CALLBACK (pitivi_timelinemedia_drag_get), NULL);
  media_signals[MEDIA_DRAG_RECEIVED_SIGNAL] = g_signal_connect (G_OBJECT (widget), "drag_data_received",\
								G_CALLBACK ( pitivi_timelinemedia_drag_data_received ), NULL);
  media_signals[MEDIA_DRAG_DROP_SIGNAL] = g_signal_connect (G_OBJECT (widget), "drag_drop",\
							    G_CALLBACK ( pitivi_timelinemedia_drag_drop ), NULL);
}

static void
pitivi_timelinemedia_size_request  (GtkWidget *widget,
				    GtkRequisition *requisition,
				    gpointer user_data)
{
  PitiviTimelineMedia *this = (PitiviTimelineMedia *) widget;
  
  if (this->track->track_type == PITIVI_EFFECTS_TRACK)
    show_effects_media (widget);
}

static void
pitivi_timelinemedia_instance_init (GTypeInstance * instance, gpointer g_class)
{
  GdkPixbuf *pixbuf;
  PitiviTimelineMedia *this = (PitiviTimelineMedia *) instance;
  
  gtk_widget_set_events (GTK_WIDGET (this), 
			 GDK_EXPOSURE_MASK
			 | GDK_ENTER_NOTIFY_MASK
                         | GDK_LEAVE_NOTIFY_MASK
                         | GDK_BUTTON_PRESS_MASK
                         | GDK_POINTER_MOTION_MASK
                         | GDK_POINTER_MOTION_HINT_MASK);

  this->private = g_new0(PitiviTimelineMediaPrivate, 1);
  
  /* initialize all public and private members to reasonable default values. */ 
  
  this->private->dispose_has_run = FALSE;
  
  /* Do only initialisation here */
  /* The construction of the object should be done in the Constructor
     So that properties set at instanciation can be set */
 
  this->effectschilds = NULL;
  this->selected = FALSE;
  this->copied = FALSE;
  
  gtk_drag_source_set  (GTK_WIDGET (this),
			GDK_BUTTON1_MASK|GDK_BUTTON3_MASK,
			TargetSameEntry, 
			iNbTargetSameEntry, 
			GDK_ACTION_COPY|GDK_ACTION_MOVE);
  
  gtk_drag_dest_set  (GTK_WIDGET (this), 
		      GTK_DEST_DEFAULT_DROP|
		      GTK_DEST_DEFAULT_HIGHLIGHT, 
		      TargetSameEntry,
		      iNbTargetSameEntry,
		      GDK_ACTION_COPY|GDK_ACTION_MOVE);
  
  pixbuf = gtk_widget_render_icon(GTK_WIDGET (this), PITIVI_STOCK_HAND, GTK_ICON_SIZE_DND, NULL);
  gtk_drag_source_set_icon_pixbuf (GTK_WIDGET (this), pixbuf);
  connect_drag_and_drop (GTK_WIDGET (this));
  gtk_signal_connect (GTK_OBJECT (this), "size_request"\
		      ,GTK_SIGNAL_FUNC ( pitivi_timelinemedia_size_request ), this);
  gtk_widget_show_all (GTK_WIDGET (this));
}


static void
pitivi_timelinemedia_set_property (GObject * object,
				   guint property_id,
				   const GValue * value, GParamSpec * pspec)
{
  PitiviTimelineMedia *this = (PitiviTimelineMedia *) object;

  switch (property_id)
    {
    case PROP_MEDIA_TYPE:
      this->private->media_type = g_value_get_int (value);
      break; 
    case PROP_MEDIA_WIDTH:
      this->private->width = g_value_get_int (value);
      break; 
    case PROP_SOURCEFILE:
      this->private->sf = g_value_get_pointer (value);
      break;
    case PROP_TRACK:
      this->track = g_value_get_pointer (value);
      break;
    default:
      g_assert (FALSE);
      break;
    }

}

static void
pitivi_timelinemedia_dispose (GObject *object)
{
  PitiviTimelineMedia	*this = PITIVI_TIMELINEMEDIA(object);

  /* If dispose did already run, return. */
  if (this->private->dispose_has_run)
    return;
  
  /* Make sure dispose does not run twice. */
  this->private->dispose_has_run = TRUE;	

  /* 
   * In dispose, you are supposed to free all types referenced from this 
   * object which might themselves hold a reference to this. Generally, 
   * the most simple solution is to unref all members on which you own a 
   * reference. 
   */

  G_OBJECT_CLASS (parent_class)->dispose (object);
}

static void
pitivi_timelinemedia_finalize (GObject *object)
{
  PitiviTimelineMedia	*this = PITIVI_TIMELINEMEDIA(object);

  /* 
   * Here, complete object destruction. 
   * You might not need to do much... 
   */

  g_free (this->private);
  G_OBJECT_CLASS (parent_class)->finalize (object);
}

static void
pitivi_timelinemedia_get_property (GObject * object,
				   guint property_id,
				   GValue * value, GParamSpec * pspec)
{
/*   PitiviTimelineMedia *this = (PitiviTimelineMedia *) object; */

  switch (property_id)
    {
    default:
      /* We don't have any other property... */
      g_assert (FALSE);
      break;
    }
}

static
gint pitivi_timelinemedia_motion_notify_event (GtkWidget        *widget,
					       GdkEventMotion   *event)
{
  // recalculer le x du event
  event->x += widget->allocation.x;
  return FALSE;
}


static gint
pitivi_timelinemedia_configure_event (GtkWidget *widget, GdkEventConfigure *event)
{  
  PitiviCursor *cursor;
  PitiviTimelineMedia *this = PITIVI_TIMELINEMEDIA (widget);
  
  cursor = pitivi_getcursor_id (widget);
  this->private->cursor_type = cursor->type;
  
  /* Size and Pixmap Cache */

  if ( this->private->pixmapcache )
    g_object_unref (this->private->pixmapcache);
  
  this->private->pixmapcache = gdk_pixmap_new (GTK_WIDGET (this)->window,
					       widget->allocation.width,
					       widget->allocation.height,
					       -1);
  draw_media (widget);
 
  return FALSE;
}

static gint
pitivi_timelinemedia_button_press_event (GtkWidget      *widget,
					 GdkEventButton *event)
{
  PitiviCursor *cursor;

  PitiviTimelineMedia *this = PITIVI_TIMELINEMEDIA (widget);
  cursor = pitivi_getcursor_id (widget);
  if (cursor->type == PITIVI_CURSOR_SELECT)
    {
      if (event->button == 1)
	{
	  if (!this->selected)
	    {
	      GtkWidget *w = gtk_widget_get_toplevel (widget);
	      g_signal_emit_by_name (w, "deselect", NULL);
	      this->selected = TRUE;
	      if ( this->linked )
		((PitiviTimelineMedia *) this->linked)->selected = TRUE;
	    }
	  else
	    {
	      this->selected = FALSE;
	      if ( this->linked )
		((PitiviTimelineMedia *) this->linked)->selected = FALSE;
	    }
	  gtk_widget_grab_focus ( widget );
	  draw_media_expose (GTK_WIDGET (this));
	  if ( this->linked )
	    draw_media_expose ( this->linked );
	}
      else
	{
	  if (this->selected)
	    {
	      this->private->menu = GTK_WIDGET (pitivi_create_menupopup (widget, TimeItemPopup, iNbTimeItemPopup));
	      gtk_menu_popup(GTK_MENU (this->private->menu), NULL, NULL, NULL, NULL, event->button, event->time);
	    }
	}
    }
  return TRUE;
}

static gint
pitivi_timelinemedia_button_release_event (GtkWidget      *widget,
					   GdkEventButton *event)
{ 
  PitiviTimelineCellRenderer *container;
  gint x = event->x;

  PitiviCursor *cursor = pitivi_getcursor_id (widget);
  if (cursor->type == PITIVI_CURSOR_ZOOM || 
      cursor->type == PITIVI_CURSOR_ZOOM_INC ||
      cursor->type == PITIVI_CURSOR_ZOOM_DEC)
    return FALSE;
  if (cursor->type == PITIVI_CURSOR_CUT)
    {
      container = ((PitiviTimelineCellRenderer * )gtk_widget_get_parent (GTK_WIDGET (widget)));
      g_signal_emit_by_name ( container, "cut-source", x, widget );    
    }
  return TRUE;
}

void
pitivi_timelinemedia_callb_deselect (PitiviTimelineMedia *this)
{
  this->selected = FALSE;
  draw_media_expose (GTK_WIDGET (this));
}

void
pitivi_timelinemedia_callb_dissociate (PitiviTimelineMedia *this, gpointer data)
{
  if (PITIVI_IS_TIMELINEMEDIA (this) && this->linked)
    if (this->selected)
      {
	PITIVI_TIMELINEMEDIA (this->linked)->selected = FALSE;
	pitivi_send_expose_event (this->linked);
	PITIVI_TIMELINEMEDIA (this->linked)->linked = NULL;
	this->linked = NULL;
      }
}

void
pitivi_timelinemedia_callb_properties (PitiviTimelineMedia *this, gpointer data)
{
  GtkWidget *props_dialog;
  PitiviEffectsWindowProperties *propertieswindow;

  gchar *properties=NULL;
  
  if (strstr (this->sourceitem->srcfile->mediatype, "effect"))
    {
      propertieswindow = pitivi_effectswindowproperties_new ( this->sourceitem );
      gtk_widget_show_all (GTK_WIDGET (propertieswindow));
      return;
    }
  if (!strcmp (this->sourceitem->srcfile->mediatype, "video/audio")) 
    { 
      properties = g_strdup_printf("Properties:\n\nSource:%s\n\nType:%s\n\nInfos Video:%s\n\n Infos Audio:%s\n",
				   this->sourceitem->srcfile->filename,
				   this->sourceitem->srcfile->mediatype,
				   this->sourceitem->srcfile->infovideo,
				   this->sourceitem->srcfile->infoaudio);
    }
  else if (!strcmp (this->sourceitem->srcfile->mediatype, "video")) 
    { 
      properties = g_strdup_printf("Properties:\n\nSource:%s\n\nType:%s\n\nInfos Video:%s\n",
				   this->sourceitem->srcfile->filename,
				   this->sourceitem->srcfile->mediatype,
				   this->sourceitem->srcfile->infovideo); 
    }
  else if (!strcmp (this->sourceitem->srcfile->mediatype, "audio"))
    { 
      properties = g_strdup_printf("Properties:\n\nSource:%s\n\nType:%s\n\nInfos Audio:%s\n",
				   this->sourceitem->srcfile->filename,
				   this->sourceitem->srcfile->mediatype,
				   this->sourceitem->srcfile->infoaudio);
    }
  else
    properties = g_strdup_printf("Properties:\nType:Unknow\n");
  props_dialog = gtk_message_dialog_new (NULL, GTK_DIALOG_MODAL, 
					 GTK_MESSAGE_INFO, 
					 GTK_BUTTONS_NONE, 
					 properties, 
					 NULL);
  gtk_widget_show(props_dialog);
}




void
pitivi_timelinemedia_callb_associate_effect (PitiviTimelineMedia *this, gpointer data)
{
  PitiviSourceFile *se =  (PitiviSourceFile *)data;
  PitiviTimelineMedia *neareffect, *effect;
  GList	*listeffects = NULL;
  int offset_currenteffect = 0;
  
  
  if ( this->track->effects_track)
    {
      se->length = this->sourceitem->srcfile->length;
      if ((strstr (se->mediatype, "audio") && this->track->track_type == PITIVI_AUDIO_TRACK)
	  ||
	  (strstr (se->mediatype, "video") && this->track->track_type == PITIVI_VIDEO_TRACK))
	{
	  if (this->effectschilds && g_list_length (this->effectschilds) > 0)
	    {
	      listeffects = g_list_last ( this->effectschilds );
	      neareffect = listeffects->data;
	      offset_currenteffect = GTK_WIDGET (neareffect)->allocation.x + GTK_WIDGET (neareffect)->allocation.width;
	      /* to do Recalculate Se */
	    }
	  /* Testing if place is left to insert effect on double click */
	  if ( offset_currenteffect < GTK_WIDGET (this)->allocation.x + GTK_WIDGET (this)->allocation.width ) 
	    {
	      effect = pitivi_timelinemedia_new ( se, GTK_WIDGET (this)->allocation.width, 
						  PITIVI_TIMELINECELLRENDERER (this->track->effects_track) );
	      this->effectschilds = g_list_append (this->effectschilds, effect);
	      this->effectschilds = g_list_sort (this->effectschilds, compare_littlechild);
	      pitivi_timelinemedia_set_start_stop(effect,
						  GNL_OBJECT(this->sourceitem->gnlobject)->start,
						  GNL_OBJECT(this->sourceitem->gnlobject)->stop);
	      pitivi_timelinemedia_set_media_start_stop(effect,
							GNL_OBJECT(this->sourceitem->gnlobject)->start,
							GNL_OBJECT(this->sourceitem->gnlobject)->stop);
	      pitivi_layout_put (GTK_LAYOUT (this->track->effects_track), 
				 GTK_WIDGET (effect), 
				 GTK_WIDGET (this)->allocation.x, 
				 0);
	      pitivi_layout_add_to_composition (PITIVI_TIMELINECELLRENDERER (this->track->effects_track),
						effect);
	      gtk_widget_show (GTK_WIDGET (effect));		
	    }
	  /* ----------------------------------------------------------- */
	}
    }
}


/**
 * pitivi_timelinemedia_callb_destroy:
 * @PitiviTimelineMedia: the media
 *
 * Destroy the media
 *
 */

void
pitivi_timelinemedia_callb_destroy (PitiviTimelineMedia *this, gpointer data)
{
  GtkWidget *track;
  
  g_printf("destroy media\n");
  if (this->selected)
    {
      if ( this->linked )
	{
	  gtk_container_remove (GTK_CONTAINER ( this->track->linked_track ), this->linked );
	  
	  gst_object_unref (GST_OBJECT (PITIVI_TIMELINEMEDIA (this->linked)->sourceitem->gnlobject));
	  pitivi_layout_remove_from_composition (PITIVI_TIMELINECELLRENDERER (this->track->linked_track),
						 PITIVI_TIMELINEMEDIA (this->linked));
	  pitivi_calculate_priorities ( this->track->linked_track );
	}
      track = &(*GTK_WIDGET (this->track));
      gtk_container_remove (GTK_CONTAINER ( track ), GTK_WIDGET (this) );
      pitivi_layout_remove_from_composition (PITIVI_TIMELINECELLRENDERER (this->track),
					     this);
      gst_object_unref (GST_OBJECT (this->sourceitem->gnlobject));
      pitivi_calculate_priorities ( track );
    }
}

static void
pitivi_timelinemedia_callb_snapped_effect (PitiviTimelineMedia *this, gpointer data)
{
  /* FIXME Deference pointer */
  g_object_unref (this->private->pixbuf);
  this->sourceitem->srcfile->thumbs_video = gdk_pixbuf_new_from_file (PITIVI_THUMBS(data)->output, NULL);
  this->private->pixbuf = gdk_pixbuf_copy (this->sourceitem->srcfile->thumbs_video);
  draw_media_expose (GTK_WIDGET (this));
  g_object_ref (this->private->pixbuf);
  G_OBJECT_GET_CLASS ((gpointer)data)->finalize ((gpointer)data);
}

static void
pitivi_timelinemedia_class_init (gpointer g_class, gpointer g_class_data)
{
  GObjectClass *gobject_class = G_OBJECT_CLASS (g_class);
  PitiviTimelineMediaClass *media_class = PITIVI_TIMELINEMEDIA_CLASS (g_class);
  
  GtkWidgetClass *widget_class = GTK_WIDGET_CLASS (g_class);
  parent_class = GTK_WIDGET_CLASS (g_type_class_peek_parent (g_class));

  gobject_class->constructor = pitivi_timelinemedia_constructor;
  gobject_class->dispose = pitivi_timelinemedia_dispose;
  gobject_class->finalize = pitivi_timelinemedia_finalize;

  gobject_class->set_property = pitivi_timelinemedia_set_property;
  gobject_class->get_property = pitivi_timelinemedia_get_property;

  widget_class->expose_event = pitivi_timelinemedia_expose;
  widget_class->motion_notify_event = pitivi_timelinemedia_motion_notify_event;
  widget_class->configure_event = pitivi_timelinemedia_configure_event;
  widget_class->button_release_event = pitivi_timelinemedia_button_release_event;
  widget_class->button_press_event = pitivi_timelinemedia_button_press_event;  
  
  g_object_class_install_property (G_OBJECT_CLASS (gobject_class), PROP_MEDIA_TYPE,
				   g_param_spec_int ("media_type","media_type","media_type",
						     G_MININT, G_MAXINT, 0, G_PARAM_READWRITE | G_PARAM_CONSTRUCT )); 
  
  g_object_class_install_property (G_OBJECT_CLASS (gobject_class), PROP_MEDIA_WIDTH,
				   g_param_spec_int ("width","width","width",
						     G_MININT, G_MAXINT, 0, G_PARAM_READWRITE | G_PARAM_CONSTRUCT )); 

  g_object_class_install_property (G_OBJECT_CLASS (gobject_class), PROP_SOURCEFILE,
				   g_param_spec_pointer ("source_file","source_file","source_file",
							 G_PARAM_READWRITE | G_PARAM_CONSTRUCT));
  
  g_object_class_install_property (G_OBJECT_CLASS (gobject_class), PROP_TRACK,
				   g_param_spec_pointer ("track","track","track",
							 G_PARAM_READWRITE | G_PARAM_CONSTRUCT ));
  
  media_signals[MEDIA_DESELECT_SIGNAL] =  g_signal_new ("deselect",
							G_TYPE_FROM_CLASS (g_class),
							G_SIGNAL_RUN_FIRST | G_SIGNAL_ACTION,
							G_STRUCT_OFFSET (PitiviTimelineMediaClass, deselect),
							NULL, 
							NULL,                
							g_cclosure_marshal_VOID__VOID,
							G_TYPE_NONE, 0);
  
  media_signals[MEDIA_DISSOCIATE_SIGNAL] = g_signal_new ("dissociate",
							 G_TYPE_FROM_CLASS (g_class),
							 G_SIGNAL_RUN_FIRST | G_SIGNAL_ACTION,
							 G_STRUCT_OFFSET (PitiviTimelineMediaClass, dissociate),
							 NULL, 
							 NULL,                
							 g_cclosure_marshal_VOID__POINTER,
							 G_TYPE_NONE, 1, G_TYPE_POINTER);
  
  media_signals[MEDIA_ASSOCIATE_EFEFCT_SIGNAL] = g_signal_new ("associate-effect-to-media",
							       G_TYPE_FROM_CLASS (g_class),
							       G_SIGNAL_RUN_FIRST | G_SIGNAL_ACTION,
							       G_STRUCT_OFFSET (PitiviTimelineMediaClass, associate_effect),
							       NULL, 
							       NULL,                
							       g_cclosure_marshal_VOID__POINTER,
							       G_TYPE_NONE, 1, G_TYPE_POINTER);
  
 media_signals[MEDIA_SNAPPED_EFEFCT_SIGNAL] = g_signal_new ("snapped",
							    G_TYPE_FROM_CLASS (g_class),
							    G_SIGNAL_RUN_FIRST | G_SIGNAL_ACTION,
							    G_STRUCT_OFFSET (PitiviTimelineMediaClass, snapped_effect),
							    NULL, 
							    NULL,                
							    g_cclosure_marshal_VOID__POINTER,
							    G_TYPE_NONE, 1, G_TYPE_POINTER);
 
  media_class->deselect = pitivi_timelinemedia_callb_deselect;
  media_class->dissociate = pitivi_timelinemedia_callb_dissociate;
  media_class->associate_effect = pitivi_timelinemedia_callb_associate_effect;
  media_class->snapped_effect = pitivi_timelinemedia_callb_snapped_effect;
}

GType
pitivi_timelinemedia_get_type (void)
{
  static GType type = 0;
 
  if (type == 0)
    {
      static const GTypeInfo info = {
	sizeof (PitiviTimelineMediaClass),
	NULL,			/* base_init */
	NULL,			/* base_finalize */
	pitivi_timelinemedia_class_init,	/* class_init */
	NULL,			/* class_finalize */
	NULL,			/* class_data */
	sizeof (PitiviTimelineMedia),
	0,			/* n_preallocs */
	pitivi_timelinemedia_instance_init	/* instance_init */
      };
      type = g_type_register_static (GTK_TYPE_DRAWING_AREA,
				     "PitiviTimelineMediaType", &info, 0);
    }

  return type;
}


/*
 **********************************************************
 * Callbacks Menu				          *
 *							  *
 **********************************************************
*/

/**
 * pitivi_timelinemedia_callb_cut:
 * @PitiviTimelineMedia: the media
 * @gpointer: data which can be attached
 * 
 * Cut the media 
 *
 */

void
pitivi_timelinemedia_callb_cut (PitiviTimelineMedia *this, gpointer data)
{
  if (!this->cutted)
    {
      this->cutted = TRUE;
      
      gtk_widget_hide (GTK_WIDGET(this));
      if (this->linked)
	gtk_widget_hide (this->linked);
  
      GtkWidget *w = gtk_widget_get_toplevel (GTK_WIDGET(this));
      g_signal_emit_by_name (w, "copy-source", this);
    }
  else
    this->cutted = FALSE;
}

void	pitivi_timelinemedia_callb_copied (PitiviTimelineMedia *this, gpointer data)
{
  if (!this->copied)
    {
      this->copied = TRUE;
      
      /* copy media */
      
      GtkWidget *w = gtk_widget_get_toplevel (GTK_WIDGET(this));
      g_signal_emit_by_name (w, "copy-source", this);
    }
  else
    this->copied = FALSE;
}
