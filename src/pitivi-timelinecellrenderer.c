/* 
 * PiTiVi
 * Copyright (C) <2004>	 Guillaume Casanova <casano_g@epita.fr>
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
#include "pitivi-effectswindow.h"
#include "pitivi-timelinewindow.h"
#include "pitivi-timelinecellrenderer.h"
#include "pitivi-timelinemedia.h"
#include "pitivi-dragdrop.h"
#include "pitivi-toolbox.h"
#include "pitivi-drawing.h"

#include "../pixmaps/bg.xpm"


// Parent Class
static GtkLayoutClass	    *parent_class = NULL;

// Caching Operation  
/* static GdkPixmap	    *pixmap = NULL; */

struct _PitiviTimelineCellRendererPrivate
{
  /* instance private members */
  
  gboolean	       dispose_has_run;
  
  PitiviTimelineWindow *timewin;
  gboolean	       selected;
    
  gint		       width;
  gint		       height;
  
  /* Slide */

  guint		       slide_width;
  gboolean	       slide_both;

  /* Backgrounds */
  
  GdkPixmap	       **bgs;

  /* Selection */

  GdkRectangle	       selection;
};


/*
 * forward definitions
 */
 
/*
 **********************************************************
 * Track informations  			                  *
 *							  *
 **********************************************************
*/

// Properties Enumaration

typedef enum {  
  PROP_LAYER_PROPERTY = 1,
  PROP_TYPE_LAYER_PROPERTY,
  PROP_TRACK_NB_PROPERTY,
  PROP_TIMELINEWINDOW
} PitiviLayerProperty;

static guint track_sizes[4][4] =
  {
    {PITIVI_VIDEO_TRACK,      7200, 50},
    {PITIVI_EFFECTS_TRACK,    7200, 25},
    {PITIVI_TRANSITION_TRACK, 7200, 25},
    {PITIVI_AUDIO_TRACK,      7200, 50},
  };


/*
 **********************************************************
 * Signals						  *
 *							  *
 **********************************************************
*/

enum {
  ACTIVATE_SIGNAL = 0,
  DEACTIVATE_SIGNAL,
  SELECT_SIGNAL,
  DESELECT_SIGNAL,
  DELETE_SIGNAL,
  DELETE_KEY_SIGNAL,
  CUT_SOURCE_SIGNAL,
  DRAG_SOURCE_BEGIN_SIGNAL,
  DRAG_SOURCE_END_SIGNAL,
  DBK_SOURCE_SIGNAL,
  ZOOM_CHANGED_SIGNAL,
  SELECT_SOURCE_SIGNAL,
  RENDERING_SIGNAL,
  LAST_SIGNAL
};

static  guint layoutsignals[LAST_SIGNAL] = {0};

/*
 **********************************************************
 * Drag and drop  			                  *
 *							  *
 **********************************************************
*/

// Destination Acception mime type for drah 'n drop

static GtkTargetEntry TargetEntries[] =
  {
    { "pitivi/timeline/sourceeffect", GTK_TARGET_SAME_APP, DND_TARGET_EFFECTSWIN },
    { "pitivi/sourcefile", GTK_TARGET_SAME_APP, DND_TARGET_SOURCEFILEWIN },
    { "pitivi/sourcetimeline", GTK_TARGET_SAME_APP, DND_TARGET_TIMELINEWIN },
    { "STRING", GTK_TARGET_SAME_APP, DND_TARGET_STRING },
    { "text/plain", GTK_TARGET_SAME_APP, DND_TARGET_URI },
  };

static gint iNbTargetEntries = G_N_ELEMENTS (TargetEntries);

/*
 * Insert "added-value" functions here
 */


/**
 * pitivi_timelinecellrenderer_new:
 * @guint: number of track
 * @PitiviLayerType: type of track
 * @PitiviTimelineWindow: the timeline window
 * 
 * Creates a new widget for an element TimelineCelleRenderer
 *
 * Returns: A widget containing an element PitiviTimelineCellRenderer
 */

GtkWidget *
pitivi_timelinecellrenderer_new (guint track_nb, PitiviLayerType track_type, PitiviTimelineWindow *tw)
{
  PitiviTimelineCellRenderer	*timelinecellrenderer;
  
  timelinecellrenderer = (PitiviTimelineCellRenderer *) 
    g_object_new (PITIVI_TIMELINECELLRENDERER_TYPE, 
		  "track_nb", 
		  track_nb, 
		  "track_type", 
		  track_type,
		  "timelinewindow",
		  tw,
		  NULL);  
  g_assert(timelinecellrenderer != NULL);
  return GTK_WIDGET ( timelinecellrenderer );
}

void
set_tracksize ( PitiviTimelineCellRenderer *self )
{
  int count;

  for (count = 0; count < (sizeof (track_sizes)/sizeof(guint)); count ++)
    if (self->track_type == track_sizes[count][0])
      {
	gtk_widget_set_size_request(GTK_WIDGET(self), 
				    convert_time_pix(self, track_sizes[count][1]),
				    track_sizes[count][2]);
	self->private->width = track_sizes[count][1];
	break;
      }
}

static gint
pitivi_timelinecellrenderer_expose (GtkWidget      *widget,
				    GdkEventExpose *event)
{
  PitiviTimelineCellRenderer	*self = PITIVI_TIMELINECELLRENDERER (widget);
  GtkLayout *layout;
  
  g_return_val_if_fail (GTK_IS_LAYOUT (widget), FALSE);
  layout = GTK_LAYOUT (widget);
  
  /* No track is activated */
  
  if (self->track_type != PITIVI_NO_TRACK)
    {
      gtk_paint_hline (widget->style,
		       layout->bin_window, 
		       GTK_STATE_NORMAL,
		       NULL, widget, "middle-line",
		       0, widget->allocation.width, widget->allocation.height/2);
    }
  if ( self->private->selected )
    pitivi_drawing_selection_area (widget, &self->private->selection, 0, NULL);
  if (event->window != layout->bin_window)
    return FALSE;
  return FALSE;
}

/**
 * pitivi_layout_add_to_composition:
 * @self: The #PitiviTimelineCellRenderer where we wish to add
 * @media: The #PitiviTimelineMedia to add
 *
 * Adds a #PitiviTimelineMedia to the underlying #GnlComposition
 */

void
pitivi_layout_add_to_composition(PitiviTimelineCellRenderer *self, PitiviTimelineMedia *media)
{
  PitiviProject       *project = PITIVI_WINDOWS (self->private->timewin)->mainapp->project;
  
  if ((self->track_type == PITIVI_VIDEO_TRACK) || (self->track_type == PITIVI_TRANSITION_TRACK)
      || (self->track_type == PITIVI_EFFECTS_TRACK))  /* Add to VideoGroup */
    gnl_composition_add_object (GNL_COMPOSITION(project->videogroup),
				media->sourceitem->gnlobject);
  else if ((self->track_type == PITIVI_AUDIO_TRACK))  /* Add to AudioGroup */
    gnl_composition_add_object (GNL_COMPOSITION(project->audiogroup),
				media->sourceitem->gnlobject);
}

/**
 * pitivi_layout_remove_from_composition:
 * @self: The #PitiviTimelineCellRenderer from which we want to remove
 * @media: The #PitiviTimelineMedia to remove
 *
 * Removes a #PitiviTimelineMedia from the underlying #GnlComposition
 */

void
pitivi_layout_remove_from_composition(PitiviTimelineCellRenderer *self, PitiviTimelineMedia *media)
{
  PitiviProject       *project = PITIVI_WINDOWS (self->private->timewin)->mainapp->project;
  
  if ((self->track_type == PITIVI_VIDEO_TRACK) || (self->track_type == PITIVI_TRANSITION_TRACK)
      || (self->track_type == PITIVI_EFFECTS_TRACK))   /* Add to VideoGroup */
    gnl_composition_remove_object (GNL_COMPOSITION(project->videogroup),
				media->sourceitem->gnlobject);
  else if ((self->track_type == PITIVI_AUDIO_TRACK))  /* Add to AudioGroup */
    gnl_composition_remove_object (GNL_COMPOSITION(project->audiogroup),
				media->sourceitem->gnlobject);
}

PitiviLayerType
pitivi_check_media_type_str (gchar *media)
{
  if (strstr  (media, "effect"))
    return (PITIVI_EFFECTS_TRACK);
  if (!g_strcasecmp  (media, "transition"))
    return (PITIVI_TRANSITION_TRACK);
  if (!g_strcasecmp  (media, "video")) 
    return (PITIVI_VIDEO_TRACK);
  else if (!g_strcasecmp (media, "audio"))
    return (PITIVI_AUDIO_TRACK);
  else if (!g_strcasecmp (media, "video/audio") 
	   || !g_strcasecmp (media, "audio/video"))
    return (PITIVI_VIDEO_AUDIO_TRACK);
  return (PITIVI_NO_TRACK);
}

/**
 * pitivi_check_media_type:
 * @PitiviSourceFilet: The list of media sources
 *
 * Check the type of the media
 *
 * Returns: The type of the media or PITIVI_NO_TRACK
 */

PitiviLayerType
pitivi_check_media_type (PitiviSourceFile *sf)
{
  PitiviLayerType layer;
  gchar *media;

  if (PITIVI_IS_SOURCEFILE (sf))
    {
      if (sf->mediatype)
	{
	  media = g_strdup (sf->mediatype);
	  layer = pitivi_check_media_type_str (media);
	  g_free (media);
	  return layer;
	}
    }
  return (PITIVI_NO_TRACK);
}

/**
 * pitivi_getcursor_id:
 * @GtkWidget: the parent widget to put the cursor into
 * 
 * Get the cursor by id
 *
 * Returns: An element PitiviCursor, the cursor
 */

PitiviCursor *
pitivi_getcursor_id (GtkWidget *widget)
{
  PitiviCursor          *cursor;
  GtkWidget		*parent;
  
  cursor = NULL;
  parent = gtk_widget_get_toplevel (GTK_WIDGET (widget));
  if ( GTK_IS_WINDOW (parent) )
    cursor = ((PitiviTimelineWindow *)parent)->toolbox->pitivi_cursor;
  return cursor;
}

static void
pitivi_timelinecellrenderer_callb_activate (PitiviTimelineCellRenderer *self)
{
  /* Activation of widget */
  gtk_widget_set_sensitive (GTK_WIDGET(self), TRUE);
  pitivi_setback_tracktype ( self );
}

static void
pitivi_timelinecellrenderer_callb_deactivate (PitiviTimelineCellRenderer *self)
{
  /* Desactivation of widget */
  gtk_widget_set_sensitive (GTK_WIDGET(self), FALSE);
}

void
get_selection_layout (GtkWidget *widget, GdkRectangle *selection, guint x)
{
  GList	*childlist = NULL;
  GList *before = NULL;
  GtkWidget *media;
  
  selection->x = 0;
  selection->y = 0;
  selection->height = widget->allocation.height;
  childlist = gtk_container_get_children (GTK_CONTAINER (widget));
  childlist = g_list_sort ( childlist, compare_littlechild );
  for (before = childlist; childlist; childlist = childlist->next)
    {
      media = childlist->data;
      if ( x > media->allocation.x + media->allocation.width && childlist->next == NULL)
	{
	  selection->x = media->allocation.x + media->allocation.width;
	  selection->width = widget->allocation.width;
	  break;
	}
      else if ( childlist->prev == NULL && x < media->allocation.x )
	{
	  selection->width = media->allocation.x;
	  break;
	}
      else if ( media->allocation.x + media->allocation.width < x 
		&& childlist->next 
		&& GTK_WIDGET ( childlist->next->data)->allocation.x > x)
	{
	  selection->x = media->allocation.x + media->allocation.width;
	  selection->width = GTK_WIDGET ( childlist->next->data)->allocation.x - selection->x;
	  break;
	}
    }
  g_list_free ( childlist );
}

static gint
pitivi_timelinecellrenderer_button_release_event (GtkWidget      *widget,
						  GdkEventButton *event)
{
  PitiviTimelineCellRenderer *self = (PitiviTimelineCellRenderer *) widget;
  GdkRectangle		selection;
  PitiviCursor		*cursor;
  gboolean		selected;
  

  cursor = self->private->timewin->toolbox->pitivi_cursor;
  if  (cursor->type == PITIVI_CURSOR_ZOOM
       || cursor->type == PITIVI_CURSOR_ZOOM_INC 
       || cursor->type == PITIVI_CURSOR_ZOOM_DEC)
    {
      if ( event->button == 1 )
	pitivi_timelinecellrenderer_button_zooming_x (self->private->timewin,
						      self, 
						      self->private->timewin->toolbox->pitivi_cursor);
      else if ( event->button == 2 )
	pitivi_timelinecellrenderer_button_zooming_unit (self->private->timewin,
							 self, 
							 self->private->timewin->toolbox->pitivi_cursor);;
    }
  if (cursor->type == PITIVI_CURSOR_SELECT && event->state != 0)
    {
      if ( event->button == 1 )
	{
	  selected = self->private->selected;
	  g_signal_emit_by_name (GTK_WIDGET (self->private->timewin), "deselect", NULL);
	  get_selection_layout  (widget, &selection, event->x);
	  if (!selected ||  (self->private->selection.x != selection.x && 
			     self->private->selection.width != selection.width))
	    {
	      self->private->selected = TRUE;
	      memcpy (&self->private->selection, &selection, sizeof (GdkRectangle));
	      pitivi_send_expose_event (widget);
	    }
	}
    }
  return FALSE;
}

static void
pitivi_timelinecellrenderer_dispose (GObject *object)
{
  PitiviTimelineCellRenderer	*self = PITIVI_TIMELINECELLRENDERER(object);

  /* If dispose did already run, return. */
  if (self->private->dispose_has_run)
    return;
  
  /* Make sure dispose does not run twice. */
  self->private->dispose_has_run = TRUE;	
}

static void
pitivi_timelinecellrenderer_finalize (GObject *object)
{
  PitiviTimelineCellRenderer	*self = PITIVI_TIMELINECELLRENDERER(object);
  g_free (self->private);
}

static void
pitivi_timelinecellrenderer_set_property (GObject * object,
					  guint property_id,
					  const GValue * value, GParamSpec * pspec)
{
  PitiviTimelineCellRenderer *self = (PitiviTimelineCellRenderer *) object;

  switch (property_id)
    {
    case PROP_TYPE_LAYER_PROPERTY:
      self->track_type = g_value_get_int (value);
      break;
    case PROP_TRACK_NB_PROPERTY:
      self->track_nb = g_value_get_int (value);
      break;
    case PROP_TIMELINEWINDOW:
      self->private->timewin = g_value_get_pointer (value);
      break;
    default:
      g_assert (FALSE);
      break;
    }
}

static void
pitivi_timelinecellrenderer_get_property (GObject * object,
					  guint property_id,
					  GValue * value, GParamSpec * pspec)
{
  PitiviTimelineCellRenderer *self = (PitiviTimelineCellRenderer *) object;

  switch (property_id)
    {
    case PROP_TYPE_LAYER_PROPERTY:
      g_value_set_int (value, self->track_type);
      break;
    case PROP_TRACK_NB_PROPERTY:
      g_value_set_int (value, self->track_nb);
      break;
    case PROP_TIMELINEWINDOW:
      g_value_set_pointer (value, self->private->timewin);
      break;
    default:
      g_assert (FALSE);
      break;
    }
}

/**************************************************************
 * Callbacks Signal Drag and Drop          		      *
 * This callbacks are used to motion get or delete  data from *
 * drag							      *
 **************************************************************/



void
pitivi_timelinecellrenderer_drag_data_received (GObject *object,
						GdkDragContext *dc,
						int x,
						int y,
						GtkSelectionData *selection,
						guint info,
						guint time,
						gpointer data)
{
  PitiviCursor *cursor;
  GtkWidget    *source;
  PitiviTimelineCellRenderer *self;

  self = PITIVI_TIMELINECELLRENDERER (object);
  if (!selection->data) {
    gtk_drag_finish (dc, FALSE, FALSE, time);
    return;
  }
  
  cursor = pitivi_getcursor_id (GTK_WIDGET(self));
  source = gtk_drag_get_source_widget(dc);
  if (cursor->type == PITIVI_CURSOR_SELECT || cursor->type == PITIVI_CURSOR_HAND)
    {  
      switch (info) 
	{
	case DND_TARGET_SOURCEFILEWIN:
	  pitivi_timelinecellrenderer_drag_on_source_file (self, selection, x, y);
	  gtk_drag_finish (dc, TRUE, TRUE, time);
	  break;
	case DND_TARGET_TIMELINEWIN:
	  x -= source->allocation.width/2;
	  if ( x < 0)
	    x = 0;
	  pitivi_timelinecellrenderer_drag_on_track (self, source, x, y);
	  gtk_drag_finish (dc, TRUE, TRUE, time);
	  break;
	case DND_TARGET_EFFECTSWIN:
	  if (self->track_type == PITIVI_TRANSITION_TRACK)
	    {
	      x -= self->private->slide_width/2;
	      if ( x < 0)
		x = 0;
	      pitivi_timelinecellrenderer_drag_on_transition (self, selection, x, y);
	    }
	  else if (self->track_type != PITIVI_EFFECTS_TRACK)
	    pitivi_timelinecellrenderer_drag_effects (self, selection->data, x, y);
	  break;
	default:
	  break;
	}
      g_signal_emit_by_name (self->private->timewin, "drag-source-end", NULL);
    }
}

gboolean
pitivi_timelinecellrenderer_drag_drop (GtkWidget *widget, 
				       GdkDragContext *dc, 
				       gint x, 
				       gint y, 
				       guint time,
				       gpointer data)
     
{
  PitiviTimelineCellRenderer *self = (PitiviTimelineCellRenderer *) widget;
  PitiviCursor *cursor;
  GtkWidget *source;
  
  cursor = pitivi_getcursor_id (widget);
  source = gtk_drag_get_source_widget(dc);
  if (cursor->type == PITIVI_CURSOR_RESIZE && PITIVI_IS_TIMELINEMEDIA (source))
    pitivi_timelinecellrenderer_resize ( self, PITIVI_TIMELINEMEDIA (source) );
  return FALSE;
}

void
pitivi_timelinecellrenderer_drag_leave (GtkWidget          *widget,
					GdkDragContext     *context,
					gpointer	    user_data)
{
  PitiviTimelineCellRenderer *self = (PitiviTimelineCellRenderer *) widget;
  if (self->linked_track)
    {
      gdk_window_clear (GTK_LAYOUT (self->linked_track)->bin_window);
      pitivi_send_expose_event (self->linked_track);
    }
}


void
create_media_video_audio_track (PitiviTimelineCellRenderer *cell, PitiviSourceFile *sf, int x)
{
  PitiviTimelineMedia *media[2];
  guint64 length = sf->length;
  int width = 0;
  
  if (!length)
    length = DEFAULT_MEDIA_SIZE;
  
  /* Creating widgets */
  
  width = convert_time_pix (cell, length);
  media[0] = pitivi_timelinemedia_new (sf, width, cell);  
  pitivi_timelinemedia_set_media_start_stop(media[0], 0, length);
  media[1] = pitivi_timelinemedia_new (sf, width, cell->linked_track);
  pitivi_timelinemedia_set_media_start_stop(media[1], 0, length);
  
  /* Putting on first Layout */
  
  pitivi_add_to_layout ( GTK_WIDGET (cell), GTK_WIDGET (media[0]), x, 0);
  pitivi_add_to_layout ( GTK_WIDGET (cell->linked_track), GTK_WIDGET (media[1]), x, 0);
  
  /* Linking widgets */
  
  link_widgets (media[0], media[1]);
  gtk_widget_show (GTK_WIDGET (media[0]));
  gtk_widget_show (GTK_WIDGET (media[1]));

  /* Add linked GnlObject to Corresponding MediaGroup */
  pitivi_layout_add_to_composition (cell, media[0]);
  pitivi_layout_add_to_composition (PITIVI_TIMELINECELLRENDERER (cell->linked_track), media[1]);
}

void
create_media_track (PitiviTimelineCellRenderer *self, 
		    PitiviSourceFile *sf, 
		    int x, 
		    gboolean invert)
{
  PitiviTimelineMedia *media;
  guint64 length = sf->length;
  int  width = 0;

  if (!length)
    length = DEFAULT_MEDIA_SIZE;
  
  width = convert_time_pix(self, length);
  media = pitivi_timelinemedia_new (sf, width, self);
  pitivi_timelinemedia_set_media_start_stop (media, 0, length);
  gtk_widget_show (GTK_WIDGET (media));
  if (invert) {
    pitivi_add_to_layout ( GTK_WIDGET (self->linked_track), GTK_WIDGET (media), x, 0);
    pitivi_layout_add_to_composition (PITIVI_TIMELINECELLRENDERER (self->linked_track), media);
  } else {
    pitivi_add_to_layout ( GTK_WIDGET (self), GTK_WIDGET (media), x, 0);
    pitivi_layout_add_to_composition (self, media);
  }
}

void
create_effect_on_track (PitiviTimelineCellRenderer *self, PitiviSourceFile *sf, int x)
{
  PitiviTimelineMedia *media;
  PitiviLayerType	type_track_cmp;

  type_track_cmp = pitivi_check_media_type (sf);
  if (self->track_type == type_track_cmp)
    {
      media = pitivi_timelinemedia_new (sf, self->private->slide_width, self);
      pitivi_timelinemedia_set_media_start_stop (media, 0, sf->length);
      pitivi_add_to_layout ( GTK_WIDGET (self), GTK_WIDGET (media), x, 0);
      pitivi_layout_add_to_composition (self, media);
    }
}

void
dispose_medias (PitiviTimelineCellRenderer *self, PitiviSourceFile *sf, int x)
{
  PitiviLayerType	type_track_cmp;

  if (self->track_type != PITIVI_EFFECTS_TRACK && self->track_type != PITIVI_TRANSITION_TRACK)
    {
      type_track_cmp = pitivi_check_media_type (sf);
      if (type_track_cmp == PITIVI_VIDEO_AUDIO_TRACK)
	create_media_video_audio_track (self, sf, x);
      else
	{
	  if (self->track_type == type_track_cmp)
	    create_media_track (self, sf, x, FALSE);
	  else if (self->track_type != type_track_cmp)
	    create_media_track (self, sf, x, TRUE);
	}
    }  
}

void
pitivi_timelinecellrenderer_drag_on_source_file (PitiviTimelineCellRenderer *self, 
						 GtkSelectionData *selection, 
						 int x, 
						 int y)
{
  PitiviSourceFile	**sf;
  
  x -= self->private->slide_width/2;
  if ( x < 0)
    x = 0;
  sf = (PitiviSourceFile **) selection->data;
  dispose_medias (self, (PitiviSourceFile *) *sf, x);
}

void
pitivi_timelinecellrenderer_drag_on_transition (PitiviTimelineCellRenderer *self,
						GtkSelectionData *selection,
						int x,
						int y)
{
  PitiviSourceFile  **sf = NULL;
  
  sf = (PitiviSourceFile **) selection->data;
  if (*sf)
    {
      if ((self->track_type == PITIVI_EFFECTS_TRACK || 
	   self->track_type == PITIVI_TRANSITION_TRACK))
	create_effect_on_track (self, (PitiviSourceFile *) *sf, x);
    }
}

void 
pitivi_timelinecellrenderer_drag_on_track (PitiviTimelineCellRenderer *self, 
					   GtkWidget *source,
					   int x,
					   int y)
{
  PitiviTimelineCellRenderer *parent;
  PitiviTimelineMedia	     *dragged;
  
  dragged = (PitiviTimelineMedia *) source;
  parent  = (PitiviTimelineCellRenderer *)gtk_widget_get_parent(GTK_WIDGET (dragged));
  
  /* Moving widget on same track */
  
  if (parent && self->track_type == parent->track_type)
    {
      if ( dragged->linked ) { /* Two widgets */
	if (parent == self)
	  {
	    move_child_on_layout (GTK_WIDGET (self), GTK_WIDGET (source), x);
	    move_child_on_layout (GTK_WIDGET (self->linked_track), GTK_WIDGET (dragged->linked), x);
	  }
	else
	  {
	    GtkWidget *linked_ref;
	    gtk_container_remove (GTK_CONTAINER (parent), GTK_WIDGET (source));
	    pitivi_add_to_layout (GTK_WIDGET (self),  source, x, 0);
	    
	    /* linked widget */
	    
	    linked_ref = gtk_widget_ref (GTK_WIDGET (dragged->linked));
	    gtk_container_remove (GTK_CONTAINER (parent->linked_track), GTK_WIDGET (dragged->linked));
	    pitivi_add_to_layout (GTK_WIDGET (self->linked_track), linked_ref, x, 0);
	    gtk_widget_unref (linked_ref);
	  }
	pitivi_send_expose_event (self->linked_track);
      }
      else /* Single Widget */
	{
	  gtk_container_remove (GTK_CONTAINER (parent), GTK_WIDGET (dragged));
	  pitivi_add_to_layout  (GTK_WIDGET (self),  GTK_WIDGET (dragged), x, 0);
	}
    }
}

void
pitivi_timelinecellrenderer_drag_effects (PitiviTimelineCellRenderer *self, gpointer data, gint x, gint y)
{
  GList	*child;
  GtkWidget *apply_on;
  
  for (child = gtk_container_get_children(GTK_CONTAINER(self)); child; child = child->next) {
    apply_on = child->data;
    if (x >= apply_on->allocation.x && x <= apply_on->allocation.x + apply_on->allocation.width)
      {
	PitiviSourceFile **sf = (PitiviSourceFile **) data;
	pitivi_timelinemedia_associate_effect (PITIVI_TIMELINEMEDIA (apply_on), *sf);
	break;
      }
  }
  g_list_free (child);
}




/*
  convert_time_pix
  Returns the pixel size depending on the unit of the ruler, and the zoom level
*/

guint
convert_time_pix (PitiviTimelineCellRenderer *self, gint64 timelength)
{
  gint64 len = timelength;
  gdouble	ratio;
  PitiviProject	*proj = PITIVI_WINDOWS(self->private->timewin)->mainapp->project;
  
  switch (self->private->timewin->unit)
    {
    case PITIVI_NANOSECONDS:
      len = timelength * self->private->timewin->zoom;
      break;
    case PITIVI_SECONDS:
      len = (timelength / GST_SECOND) * self->private->timewin->zoom;
      break;
    case PITIVI_FRAMES:
      ratio = ( pitivi_projectsettings_get_videorate(proj->settings)
		* self->private->timewin->zoom );
	
      len = (timelength / GST_SECOND) * ratio;
      break;
    default:
      break;
    }
/*   g_printf ("Converting time %03lld:%02lld:%03lld  -> pixels %lld\n", */
/* 	    GST_M_S_M (timelength), len); */
  return len;
}

gint64
convert_pix_time (PitiviTimelineCellRenderer *self, guint pos)
{
  PitiviProject	*proj = PITIVI_WINDOWS(self->private->timewin)->mainapp->project;
  gdouble videorate;
  
  videorate = pitivi_projectsettings_get_videorate (proj->settings);
  return convert_sub_pix_time (pos,
			       self->private->timewin->unit,
			       self->private->timewin->zoom,
			       videorate
			       );
}

/**************************************************************
 * Callbacks Signal Activate / Deactivate		      *
 * This callbacks are used to acitvate and deactivate Layout  *
 *							      *
 **************************************************************/

/**
 * pitivi_timelinecellrenderer_activate:
 * @PitiviTimelineCellRenderer: the timelinecellrenderer
 *
 * Activates a layout
 *
 */

void
pitivi_timelinecellrenderer_activate (PitiviTimelineCellRenderer *self)
{
  g_signal_emit_by_name (GTK_OBJECT (self), "activate");
}

/**
 * pitivi_timelinecellrenderer_deactivate:
 * @PitiviTimelineCellRenderer: the timelinecellrenderer
 *
 * Deactivates a layout
 *
 */

void
pitivi_timelinecellrenderer_deactivate (PitiviTimelineCellRenderer *self)
{
  g_signal_emit_by_name (GTK_OBJECT (self), "deactivate");
}

/**
 * pitivi_setback_tracktype:
 * @PitiviTimelineCellRenderer: the timelinecellrenderer
 *
 * Set the background of the widget
 *
 */

void
pitivi_setback_tracktype ( PitiviTimelineCellRenderer *self )
{
  GdkPixmap *pixmap = NULL;
  
  if (self->track_type != PITIVI_NO_TRACK)
    {
      pixmap = self->private->bgs[self->track_type];
      if ( pixmap )
	{
	  // Set background Color
	  pitivi_drawing_set_pixmap_bg (GTK_WIDGET(self), pixmap);
	}
    }
}

/*
** Scroll event
*/

static gboolean
pitivi_timelinecellrenderer_scroll_event (GtkWidget *widget, GdkEventScroll *event)
{
  PitiviTimelineCellRenderer	*self = PITIVI_TIMELINECELLRENDERER (widget);

  if (event->state & GDK_SHIFT_MASK) { // ZOOM
    
    if ((event->direction == GDK_SCROLL_UP) && (self->private->timewin->zoom < 16)) { // ZOOM IN
      self->private->timewin->zoom *= 2;
      pitivi_timelinewindow_zoom_changed (self->private->timewin);
    } else if ((event->direction == GDK_SCROLL_DOWN) && (self->private->timewin->zoom > 1)) { // ZOOM OUT
      self->private->timewin->zoom /= 2;
      pitivi_timelinewindow_zoom_changed (self->private->timewin);
    }
  } else { // MOVE
    gdouble	value, lower, upper, increment;
    
    g_object_get(G_OBJECT(self->private->timewin->hscrollbar),
		 "lower", &lower,
		 "upper", &upper,
		 "step-increment", &increment,
		 "value", &value,
		 NULL);
    if (event->direction == GDK_SCROLL_UP) { // MOVE LEFT
      value  = value - increment;
      if (value < lower)
	value = lower;
      gtk_adjustment_set_value (self->private->timewin->hscrollbar, value);
    } else if (event->direction == GDK_SCROLL_DOWN) { // MOVE RIGHT
      value = value + increment;
      if (value > upper)
	value = upper;
      gtk_adjustment_set_value (self->private->timewin->hscrollbar, value);
    }
  }
  pitivi_ruler_set_zoom_metric (GTK_RULER (self->private->timewin->hruler),
				self->private->timewin->unit, self->private->timewin->zoom);
  return FALSE;
}


/*
 **********************************************************
 * Selection	  			                  *
 *							  *
 **********************************************************
*/

guint
pitivi_timecellrenderer_track_type ( PitiviTimelineCellRenderer *cell )
{
  return cell->track_type;
}

void
pitivi_timelinecellrenderer_rendering ( PitiviTimelineCellRenderer *cell )
{
  pitivi_calculate_priorities ( GTK_WIDGET (cell) );
}

/**
 * pitivi_timelinecellrenderer_media_selected_ontrack:
 * @PitiviTimelineCellRenderer: the timelinecellrenderer
 *
 * Update the selected media widget on the track
 *
 * Returns: A widget GtkWidget, or NULL if no widget is selected 
 */

GtkWidget *
pitivi_timelinecellrenderer_media_selected_ontrack  ( PitiviTimelineCellRenderer *cell )
{
  GtkWidget *media;
  GList	*childlist;
  
  for (childlist = gtk_container_get_children (GTK_CONTAINER (cell)); 
       childlist; childlist = childlist->next)
    {
      media = GTK_WIDGET (childlist->data);
      if ( PITIVI_TIMELINEMEDIA (media)->selected )
	return (media); 
    }
  return NULL;
}

void
pitivi_timelinecellrenderer_callb_deselect (PitiviTimelineCellRenderer *self)
{
  self->private->selected = FALSE;
  gdk_window_clear (GTK_LAYOUT (self)->bin_window);
  gtk_paint_hline (GTK_WIDGET(self)->style,
		   GTK_LAYOUT(self)->bin_window, 
		   GTK_STATE_NORMAL,
		   NULL, GTK_WIDGET(self), "middle-line",
		   0, GTK_WIDGET(self)->allocation.width, GTK_WIDGET(self)->allocation.height/2);
  send_signal_to_childs_direct (GTK_WIDGET (self), "deselect", NULL);
}

static void
pitivi_timelinecellrenderer_callb_cut_source  (PitiviTimelineCellRenderer *container, guint x, gpointer data)
{
  PitiviTimelineMedia *media[2], *link;
  PitiviTimelineMedia *media_source;
  gint64 start1, start2, stop1, stop2, mstart1, mstart2, mstop1, mstop2;
  guint	 pos =  0;
  
  if (GTK_IS_WIDGET (data))
    {
      media_source = data;
      pos = GTK_WIDGET (media_source)->allocation.x+x; // calcul de la position du nouveau media

      start2 = stop1 = convert_pix_time(container, pos);
      pitivi_timelinemedia_get_start_stop(media_source, &start1, &stop2);
      pitivi_timelinemedia_get_media_start_stop(media_source, &mstart1, &mstop2);
      mstop1 = mstart2 = mstart1 + (stop1 - start1);
      GTK_WIDGET (media_source)->allocation.width = GTK_WIDGET (media_source)->allocation.width - x; // calcul

      media[0] = pitivi_timelinemedia_new ( media_source->sourceitem->srcfile,
					    GTK_WIDGET (media_source)->allocation.width, container );
      // donner un nouveau stop/media_stop a l'ancien media
      pitivi_timelinemedia_set_start_stop(media_source, start1, stop1);
      pitivi_timelinemedia_set_media_start_stop(media_source, mstart1, mstop1);
      // donner un stop/media_start/media_stop au nouveau media
      pitivi_timelinemedia_set_media_start_stop(media[0], mstart2, mstop2);

      pitivi_layout_put (GTK_LAYOUT (container),  GTK_WIDGET ( media[0] ), pos, 0); // placement du nouveau media
      pitivi_media_set_size (GTK_WIDGET (media_source), x); // retaillage de l'ancien media
      pitivi_layout_add_to_composition (container, media[0]);
      gtk_widget_show ( GTK_WIDGET ( media[0] ) );
      assign_next_prev ( media_source->track );
      if ( media_source->linked )
	{
	  link = media_source->linked;
	  GTK_WIDGET ( link )->allocation.width = GTK_WIDGET (media_source)->allocation.width;
	  media[1] = pitivi_timelinemedia_new (media_source->sourceitem->srcfile,
					       GTK_WIDGET (media_source)->allocation.width, container->linked_track );
	  pitivi_media_set_size ( GTK_WIDGET (media_source->linked), x);
	  link_widgets (media[0], media[1]);
	  pitivi_timelinemedia_set_media_start_stop(link, mstart1, mstop1);
	  pitivi_timelinemedia_set_media_start_stop(media[1], mstart2, mstop2);
	  pitivi_layout_put (GTK_LAYOUT ( container->linked_track ), GTK_WIDGET ( media[1] ), pos, 0);
	  pitivi_layout_add_to_composition (PITIVI_TIMELINECELLRENDERER (container->linked_track),
					    media[1]);
	  gtk_widget_show (GTK_WIDGET ( media[1] ));
	  assign_next_prev ( media_source->linked->track );
	}
      else
	pitivi_calculate_priorities ( GTK_WIDGET (container) );
    }
}

void
pitivi_timelinecellrenderer_callb_delete_sf (PitiviTimelineCellRenderer *self, gpointer data)
{
  PitiviTimelineMedia *media;
  PitiviSourceFile *sf;
  GList *child  = NULL;
  GList *delete = NULL;
  
  for (child = gtk_container_get_children (GTK_CONTAINER (self)); child; child = child->next )
    {
      sf = data;
      media = child->data;
      if (media->sourceitem->srcfile->filename == sf->filename)
	delete = g_list_append (delete, media);
    }
  while (delete)
    {
      if (GTK_IS_WIDGET (delete->data))
	{
	  media = delete->data;
	  if ( media->linked ) {
	    gtk_container_remove (GTK_CONTAINER (self->linked_track), GTK_WIDGET (media->linked));
	    pitivi_layout_remove_from_composition (PITIVI_TIMELINECELLRENDERER (self->linked_track),
						   PITIVI_TIMELINEMEDIA (media->linked));
	    assign_next_prev ( PITIVI_TIMELINEMEDIA (media->linked)->track );
	  }
	  gtk_container_remove (GTK_CONTAINER (self), GTK_WIDGET (media) );
	  pitivi_layout_remove_from_composition (self, media);
	  assign_next_prev ( media->track );
	}
      delete = delete->next;
    }
  g_list_free (delete);
  g_list_free (child);
  pitivi_calculate_priorities ( GTK_WIDGET (self) );
}

static void
pitivi_timelinecellrenderer_key_delete (PitiviTimelineCellRenderer* self) 
{
  PitiviTimelineMedia *media;
  GList *child   = NULL;
  
  for (child = gtk_container_get_children (GTK_CONTAINER (self)); child; child = child->next )
    {
      media = &(*((PitiviTimelineMedia *)child->data));
      if ( media->selected ) {
	if (media->effectschilds)
	  while ( media->effectschilds )
	    {
	      if ( media->effectschilds->data )
		{
		  gtk_container_remove ( GTK_CONTAINER (PITIVI_TIMELINEMEDIA (media->effectschilds->data)->track), 
					 GTK_WIDGET (media->effectschilds->data));
		  assign_next_prev ( PITIVI_TIMELINEMEDIA (media->effectschilds->data)->track );
		}
	      media->effectschilds = media->effectschilds->next;
	    }
	gtk_container_remove ( GTK_CONTAINER (self), GTK_WIDGET (media));
	pitivi_layout_remove_from_composition (self, media);
	assign_next_prev ( media->track );
      }
    }
  pitivi_calculate_priorities ( GTK_WIDGET (self) );
  g_list_free (child);
}

/*
 **********************************************************
 * Slide Operation			                  *
 *							  *
 **********************************************************
*/

void
pitivi_timelinecellrenderer_callb_drag_source_begin (PitiviTimelineCellRenderer *self, 
						     gpointer data)
{
  struct _Pslide
  {
    gint64 length;
    gchar  *path;
  } *slide;
  gint64 len;
  PitiviLayerType type;
 
  slide = (struct _Pslide *) data;
  len = slide->length;
  if (len > 0)
    self->private->slide_width = convert_time_pix (self, len);
  type = pitivi_check_media_type_str (slide->path);
  if (type == PITIVI_VIDEO_AUDIO_TRACK)
    self->private->slide_both = TRUE;
}

void
pitivi_timelinecellrenderer_callb_drag_source_end (PitiviTimelineCellRenderer *self, 
						   gpointer data)
{
  self->private->slide_both = FALSE;
  self->private->slide_width = 0;
}


guint 
slide_media_get_widget_size (PitiviTimelineMedia  *source)
{
  guint width = DEFAULT_MEDIA_SIZE;

  if (PITIVI_IS_TIMELINEMEDIA (source))
    width = GTK_WIDGET (source)->allocation.width;
  return width;
}

gboolean
check_before_draw_slide (PitiviTimelineCellRenderer *self, GtkWidget *source)
{
  if (self->track_type != PITIVI_EFFECTS_TRACK)
    {
      if (PITIVI_IS_EFFECTSWINDOW (gtk_widget_get_toplevel(source)) 
	  && self->track_type != PITIVI_TRANSITION_TRACK)
	return FALSE;
    }
  if (self->track_type == PITIVI_EFFECTS_TRACK)
    return FALSE;
  return TRUE;
}

static void
pitivi_timelinecellrenderer_drag_motion (GtkWidget          *widget,
					 GdkDragContext     *dc,
					 gint                x,
					 gint                y,
					 guint               time)
{ 
  PitiviTimelineCellRenderer *self = (PitiviTimelineCellRenderer *) widget;
  PitiviTimelineMedia  *source = NULL;
  PitiviCursor *cursor;
  guint width;
  guint decrement = 0;
  
  cursor = pitivi_getcursor_id (widget);
  source = (PitiviTimelineMedia  *)gtk_drag_get_source_widget(dc);
  if (cursor->type == PITIVI_CURSOR_RESIZE)
    {
      if (PITIVI_IS_TIMELINEMEDIA (source))
	{
	  decrement = GTK_RULER(self->private->timewin->hruler)->metric->pixels_per_unit;
	  if (self->private->timewin->unit == PITIVI_FRAMES)
	    decrement *= 10;
	  pitivi_timelinecellrenderer_resizing_media (source, self, decrement, x);
	  return;
	}
    }
  else
    {
      if (cursor->type == PITIVI_CURSOR_SELECT || cursor->type == PITIVI_CURSOR_HAND)
	{
	  if (source && dc && PITIVI_IS_TIMELINEMEDIA (source))
	    width = slide_media_get_widget_size (source);
	  else
	    width = self->private->slide_width;
	  /* Decaling drag and drop to the middle of the source */
	  x -= width/2;
	  /* -------- */
	  gdk_window_clear (GTK_LAYOUT (widget)->bin_window);
	  if (check_before_draw_slide (self, GTK_WIDGET (source)))
	    {
	      pitivi_draw_slide (widget, x, width);
	      if ((self->linked_track && source && source->linked) || 
		  (self->linked_track && self->private->slide_both))
		{
		  gdk_window_clear  (GTK_LAYOUT (self->linked_track)->bin_window);
		  pitivi_draw_slide (GTK_WIDGET (self->linked_track), x, width);
		}
	    }
	}
    }
}


/*
 **********************************************************
 * Widget Initialisation		                  *
 *							  *
 **********************************************************
*/


static GObject *
pitivi_timelinecellrenderer_constructor (GType type,
					 guint n_construct_properties,
					 GObjectConstructParam * construct_properties)
{
  GObject *object;
  PitiviTimelineCellRenderer *self;
  
  /* Constructor  */
  
  object = (* G_OBJECT_CLASS (parent_class)->constructor) 
    (type, n_construct_properties, construct_properties);
  
  self = (PitiviTimelineCellRenderer *) object;
  
  /* Deactivation */
  pitivi_timelinecellrenderer_deactivate (self);
  
  /* Set Size Layer */
  set_tracksize (self);
  
  /* Bg */
  self->private->bgs = self->private->timewin->bgs;
  
  self->nb_added = self->private->timewin->nb_added;
  return object;
}

static void
pitivi_timelinecellrenderer_instance_init (GTypeInstance * instance, gpointer g_class)
{
  GdkPixmap *pixmap;
  
  PitiviTimelineCellRenderer *self = (PitiviTimelineCellRenderer *) instance;

  self->private = g_new0(PitiviTimelineCellRendererPrivate, 1);
  
  /* Motion notify Event Button Press release for selection */

  gtk_widget_set_events (GTK_WIDGET (self),
			 GDK_BUTTON_RELEASE_MASK |
			 GDK_POINTER_MOTION_MASK | 
			 gtk_widget_get_events (GTK_WIDGET (self)));
  
  /* initialize all public and private members to reasonable default values. */
  
  self->private->dispose_has_run = FALSE;
  
  /* Initializations */
  
  self->private->width  = FIXED_WIDTH;
  self->private->height = FIXED_HEIGHT;
  self->private->selected = FALSE;
  self->children = NULL;
  self->track_nb = 0;
  self->private->slide_width = DEFAULT_MEDIA_SIZE;
  self->private->slide_both  = FALSE;
  
  /* Set background Color Desactivation of default pixmap is possible */
  
  pixmap = pitivi_drawing_getpixmap (GTK_WIDGET(self), bg_xpm);
  pitivi_drawing_set_pixmap_bg (GTK_WIDGET(self), pixmap);
  
  /* Drag and drop signal connection */
  
  gtk_drag_dest_set  (GTK_WIDGET (self), GTK_DEST_DEFAULT_ALL, 
		      TargetEntries,
		      iNbTargetEntries,
		      GDK_ACTION_COPY|GDK_ACTION_MOVE);

  g_signal_connect (G_OBJECT (self), "drag_drop",\
		    G_CALLBACK ( pitivi_timelinecellrenderer_drag_drop ), NULL);
  g_signal_connect (G_OBJECT (self), "drag_leave",\
		    G_CALLBACK ( pitivi_timelinecellrenderer_drag_leave ), NULL);
  g_signal_connect (G_OBJECT (self), "drag_data_received",\
		    G_CALLBACK ( pitivi_timelinecellrenderer_drag_data_received ), NULL);
  g_signal_connect (G_OBJECT (self), "drag_motion",
		    G_CALLBACK ( pitivi_timelinecellrenderer_drag_motion ), NULL);
  g_signal_connect (G_OBJECT (self), "button_release_event",
		    G_CALLBACK ( pitivi_timelinecellrenderer_button_release_event ), NULL);
}

static void
pitivi_timelinecellrenderer_class_init (gpointer g_class, gpointer g_class_data)
{
  GObjectClass *cellobj_class = G_OBJECT_CLASS (g_class);
  PitiviTimelineCellRendererClass *cell_class = PITIVI_TIMELINECELLRENDERER_CLASS (g_class);
 
  GtkWidgetClass *widget_class = GTK_WIDGET_CLASS (g_class);
/*   GtkContainerClass *container_class = (GtkContainerClass*) (g_class); */
  
  parent_class = gtk_type_class (GTK_TYPE_LAYOUT);
  cellobj_class->constructor = pitivi_timelinecellrenderer_constructor;
  cellobj_class->dispose = pitivi_timelinecellrenderer_dispose;
  cellobj_class->finalize = pitivi_timelinecellrenderer_finalize;
  cellobj_class->set_property = pitivi_timelinecellrenderer_set_property;
  cellobj_class->get_property = pitivi_timelinecellrenderer_get_property;
  
  /* Widget properties */
  
  widget_class->expose_event = pitivi_timelinecellrenderer_expose;
  widget_class->scroll_event = pitivi_timelinecellrenderer_scroll_event;
  
  /* Container Properties */

  /* Install the properties in the class here ! */
  
  g_object_class_install_property (G_OBJECT_CLASS (cellobj_class), PROP_TYPE_LAYER_PROPERTY,
				   g_param_spec_int ("track_type","track_type","track_type",
						     G_MININT, G_MAXINT, 0, G_PARAM_READWRITE | G_PARAM_CONSTRUCT_ONLY));
  
  g_object_class_install_property (G_OBJECT_CLASS (cellobj_class), PROP_TIMELINEWINDOW,
				   g_param_spec_pointer ("timelinewindow","timelinewindow","timelinewindow",
							 G_PARAM_WRITABLE | G_PARAM_CONSTRUCT_ONLY));
  
  g_object_class_install_property (G_OBJECT_CLASS (cellobj_class), PROP_TRACK_NB_PROPERTY,
				   g_param_spec_int ("track_nb","track_nb","track_nb",
						     G_MININT, G_MAXINT, 0, G_PARAM_READWRITE | G_PARAM_CONSTRUCT_ONLY));

  /* Signals */
  
  layoutsignals[ACTIVATE_SIGNAL] = g_signal_new ("activate",
						 G_TYPE_FROM_CLASS (g_class),
						 G_SIGNAL_RUN_FIRST | G_SIGNAL_ACTION,
						 G_STRUCT_OFFSET (PitiviTimelineCellRendererClass, activate),
						 NULL, 
						 NULL,                
						 g_cclosure_marshal_VOID__VOID,
						 G_TYPE_NONE, 0);
 
  layoutsignals[DEACTIVATE_SIGNAL] = g_signal_new ("deactivate",
						   G_TYPE_FROM_CLASS (g_class),
						   G_SIGNAL_RUN_FIRST | G_SIGNAL_ACTION,
						   G_STRUCT_OFFSET (PitiviTimelineCellRendererClass, deactivate),
						   NULL, 
						   NULL,                
						   g_cclosure_marshal_VOID__VOID,
						   G_TYPE_NONE, 0);
   
  layoutsignals[DESELECT_SIGNAL] = g_signal_new ("deselect",
						 G_TYPE_FROM_CLASS (g_class),
						 G_SIGNAL_RUN_FIRST | G_SIGNAL_ACTION,
						 G_STRUCT_OFFSET (PitiviTimelineCellRendererClass, deselect),
						 NULL, 
						 NULL,                
						 g_cclosure_marshal_VOID__VOID,
						 G_TYPE_NONE, 0);
   
  layoutsignals[DELETE_KEY_SIGNAL] = g_signal_new ("key-delete-source",
						   G_TYPE_FROM_CLASS (g_class),
						   G_SIGNAL_RUN_FIRST | G_SIGNAL_ACTION,
						   G_STRUCT_OFFSET (PitiviTimelineCellRendererClass, key_delete),
						   NULL,
						   NULL,       
						   g_cclosure_marshal_VOID__VOID,
						   G_TYPE_NONE, 0);

  layoutsignals[DELETE_SIGNAL] = g_signal_new ("delete-source",
					       G_TYPE_FROM_CLASS (g_class),
					       G_SIGNAL_RUN_FIRST | G_SIGNAL_ACTION,
					       G_STRUCT_OFFSET (PitiviTimelineCellRendererClass, delete),
					       NULL,
					       NULL,       
					       g_cclosure_marshal_VOID__POINTER,
					       G_TYPE_NONE, 1, G_TYPE_POINTER);
   
  layoutsignals[DRAG_SOURCE_BEGIN_SIGNAL] = g_signal_new ("drag-source-begin",
							  G_TYPE_FROM_CLASS (g_class),
							  G_SIGNAL_RUN_FIRST,
							  G_STRUCT_OFFSET (PitiviTimelineCellRendererClass, drag_source_begin),
							  NULL,
							  NULL,       
							  g_cclosure_marshal_VOID__POINTER,
							  G_TYPE_NONE, 1, G_TYPE_POINTER);
  
  layoutsignals[DRAG_SOURCE_END_SIGNAL] = g_signal_new ("drag-source-end",
							G_TYPE_FROM_CLASS (g_class),
							G_SIGNAL_RUN_FIRST,
							G_STRUCT_OFFSET (PitiviTimelineCellRendererClass, drag_source_end),
							NULL,
							NULL,       
							g_cclosure_marshal_VOID__POINTER,
							G_TYPE_NONE, 1, G_TYPE_POINTER);
  
  layoutsignals[CUT_SOURCE_SIGNAL] = g_signal_new ("cut-source",
						   G_TYPE_FROM_CLASS (g_class),
						   G_SIGNAL_RUN_LAST,
						   G_STRUCT_OFFSET (PitiviTimelineCellRendererClass, cut_source),
						   NULL,
						   NULL,       
						   g_cclosure_marshal_VOID__UINT_POINTER,
						   G_TYPE_NONE, 2, G_TYPE_UINT, G_TYPE_POINTER);
   
  layoutsignals[ZOOM_CHANGED_SIGNAL] = g_signal_new ("zoom-changed",
						     G_TYPE_FROM_CLASS (g_class),
						     G_SIGNAL_RUN_FIRST | G_SIGNAL_ACTION,
						     G_STRUCT_OFFSET (PitiviTimelineCellRendererClass, zoom_changed),
						     NULL, 
						     NULL,                
						     g_cclosure_marshal_VOID__VOID,
						     G_TYPE_NONE, 0);
  
  layoutsignals[RENDERING_SIGNAL] = g_signal_new ("rendering",
						  G_TYPE_FROM_CLASS (g_class),
						  G_SIGNAL_RUN_FIRST | G_SIGNAL_ACTION,
						  G_STRUCT_OFFSET (PitiviTimelineCellRendererClass, rendering),
						  NULL, 
						  NULL,                
						  g_cclosure_marshal_VOID__VOID,
						  G_TYPE_NONE, 0);
  
  cell_class->activate = pitivi_timelinecellrenderer_callb_activate;
  cell_class->deactivate = pitivi_timelinecellrenderer_callb_deactivate;
  cell_class->deselect = pitivi_timelinecellrenderer_callb_deselect;
  cell_class->drag_source_begin = pitivi_timelinecellrenderer_callb_drag_source_begin;
  cell_class->drag_source_end = pitivi_timelinecellrenderer_callb_drag_source_end;
  cell_class->delete = pitivi_timelinecellrenderer_callb_delete_sf;
  cell_class->cut_source = pitivi_timelinecellrenderer_callb_cut_source;
  cell_class->zoom_changed = pitivi_timelinecellrenderer_zoom_changed;
  cell_class->key_delete = pitivi_timelinecellrenderer_key_delete;
  cell_class->rendering = pitivi_timelinecellrenderer_rendering;
}

GType
pitivi_timelinecellrenderer_get_type (void)
{
  static GType type = 0;
 
  if (type == 0)
    {
      static const GTypeInfo info = {
	sizeof (PitiviTimelineCellRendererClass),
	NULL,			/* base_init */
	NULL,			/* base_finalize */
	pitivi_timelinecellrenderer_class_init,	/* class_init */
	NULL,			/* class_finalize */
	NULL,			/* class_data */
	sizeof (PitiviTimelineCellRenderer),
	0,			/* n_preallocs */
	pitivi_timelinecellrenderer_instance_init	/* instance_init */
      };
      type = g_type_register_static (GTK_TYPE_LAYOUT,
				     "PitiviTimelineCellRendererType", &info, 0);
    }
  return type;
}
