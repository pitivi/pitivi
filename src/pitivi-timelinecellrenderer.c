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
#include "pitivi-thumbs.h"

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
  GtkSelectionData     *current_selection;
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
pitivi_media_set_size (GtkWidget *widget, guint width)
{
  gtk_widget_set_size_request (widget, width, widget->allocation.height);
  if (PITIVI_IS_TIMELINEMEDIA (widget))
    PITIVI_TIMELINEMEDIA (widget)->original_width = width;
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


/* Comparaison */

gint 
compare_track (gconstpointer a, gconstpointer b)
{
  GtkWidget *wa, *wb;
  
  wa = GTK_WIDGET (a);
  wb = GTK_WIDGET (b);
  
  if (wa->allocation.x > wb->allocation.x)
    return 1;
  else if (wa->allocation.x < wb->allocation.x)
    return -1;
  else if ( PITIVI_TIMELINEMEDIA (wa)->track->track_nb > PITIVI_TIMELINEMEDIA (wb)->track->track_nb )
    return 1;
  return 0;
}

/**
 * pitivi_calculate_priorities:
 * @GtkWidget: the widget containing a media source
 * 
 * Calculates the priorities of the media sources
 *
 */

void
pitivi_calculate_priorities ( GtkWidget *widget )
{
  PitiviTimelineCellRenderer *self = (PitiviTimelineCellRenderer *)widget;
  PitiviTimelineMedia *media;
  GList *containerlist = NULL;
  GList *layoutlist = NULL;
  GList *sublist = NULL;
  int	priority = 2;
  int   x, width = 0;
  gboolean found = FALSE;

  if (self->track_type == PITIVI_EFFECTS_TRACK)
    self = PITIVI_TIMELINECELLRENDERER (self->linked_track);
  containerlist = gtk_container_get_children (GTK_CONTAINER (gtk_widget_get_parent(GTK_WIDGET (self))));
  for (; containerlist; containerlist = containerlist->next)
    if (self->track_type == PITIVI_TIMELINECELLRENDERER (containerlist->data)->track_type)
      {
	if (!layoutlist)
	  {
	    layoutlist = gtk_container_get_children (GTK_CONTAINER (containerlist->data));
	    layoutlist = g_list_last  (layoutlist);
	  }
	else
	  layoutlist->next = gtk_container_get_children (GTK_CONTAINER (containerlist->data));
      }
  
  if ( layoutlist )
    {
      layoutlist = g_list_first (layoutlist);
      layoutlist = g_list_sort (layoutlist, compare_track);
      for (; layoutlist; layoutlist = layoutlist->next)
	{
	  media = layoutlist->data;
	  if ( media->track->effects_track)
	    {
	      found = FALSE;
	      sublist = gtk_container_get_children (GTK_CONTAINER (media->track->effects_track));
	      for (; sublist; sublist = sublist->next)
		{
		  x = GTK_WIDGET (sublist->data)->allocation.x;
		  width = GTK_WIDGET (sublist->data)->allocation.width;
		  if (GTK_WIDGET (media)->allocation.x <= x 
		      && (x-GTK_WIDGET (media)->allocation.x)+width<=GTK_WIDGET (media)->allocation.width)
		    {
		      pitivi_timelinemedia_set_priority ( PITIVI_TIMELINEMEDIA (sublist->data), priority);
		      found = TRUE;
		    }
		}
	      if ( found )
		priority++;
	    }
	  if ( media && media->track->track_type != PITIVI_TRANSITION_TRACK)
	    {
	      pitivi_timelinemedia_set_priority ( media, priority);
	      priority++;
	    }
	}
    }
  g_list_free (containerlist);
  g_list_free (layoutlist);
  g_list_free (sublist);
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

/**
 * pitivi_layout_put:
 * @GtkLayout: the layout to put the widgets into
 * @GtkWidget: the widget to put into the layout
 * @gint: the widget position in X 
 * @gint: the widget position in Y 
 * 
 * Adds the given widget to the layout at the given x/y position.
 * Updates the position of the attached GnlSource.
 *
 */

void
pitivi_layout_put (GtkLayout *layout, GtkWidget *widget, gint x, gint y)
{
  //PitiviProject       *project = PITIVI_WINDOWS (PITIVI_TIMELINECELLRENDERER(layout)->private->timewin)->mainapp->project;
  
  widget->allocation.x = x;
  widget->allocation.y = y;
  g_printf ("pitivi_layout_put x:%d y:%d TrackType:%d\n", x, y, PITIVI_TIMELINECELLRENDERER (layout)->track_type);
  gtk_layout_put ( layout, widget, x, y );
  pitivi_calculate_priorities (GTK_WIDGET (layout) );
/*   if (PITIVI_IS_TIMELINEMEDIA(widget) && PITIVI_IS_TIMELINECELLRENDERER(layout) */
/*       && ((PITIVI_TIMELINECELLRENDERER(layout)->track_type == PITIVI_AUDIO_TRACK) */
/* 	  || (PITIVI_TIMELINECELLRENDERER(layout)->track_type == PITIVI_VIDEO_TRACK))){ */
  if (PITIVI_IS_TIMELINEMEDIA(widget) && PITIVI_IS_TIMELINECELLRENDERER(layout))
    pitivi_timelinemedia_put (PITIVI_TIMELINEMEDIA(widget), 
			      convert_pix_time(PITIVI_TIMELINECELLRENDERER(layout), x));
  // TODO : Check if widget isn't already on this layout (!move)
    // set the priority
/*     pitivi_timelinemedia_set_priority(PITIVI_TIMELINEMEDIA(widget), 1); */
/*     if (PITIVI_TIMELINECELLRENDERER(layout)->track_type == PITIVI_AUDIO_TRACK) { */
/*       gnl_composition_add_object(GNL_COMPOSITION(project->audiogroup), */
/* 				 PITIVI_TIMELINEMEDIA(widget)->sourceitem->gnlobject); */
/*     } else if (PITIVI_TIMELINECELLRENDERER(layout)->track_type == PITIVI_VIDEO_TRACK) { */
/*       gnl_composition_add_object(GNL_COMPOSITION(project->videogroup), */
/* 				 PITIVI_TIMELINEMEDIA(widget)->sourceitem->gnlobject);       */
/*     } */
    // pitivi_printf_element( PITIVI_TIMELINEMEDIA(widget)->sourceitem->srcfile->pipeline );
 
    // Add to the composition
    //  Find what kind of media it is (audio/video) PITIVI_VIDEO/AUDIO_TRACK (layout->track_type)
    //  gnl_composition_add_object() to the correct group
}

/*
  pitivi_layout_move

  Moves the widget in the layout at the given x/y position
  Updates the position of the attached GnlSource
*/

void
pitivi_layout_move (GtkLayout *layout, GtkWidget *widget, gint x, gint y)
{
  widget->allocation.x = x;
  widget->allocation.y = y;
  gtk_layout_move (layout, widget, x, y);
  pitivi_calculate_priorities ( GTK_WIDGET (layout) );
  if (PITIVI_IS_TIMELINEMEDIA(widget) && PITIVI_IS_TIMELINECELLRENDERER(layout)) {
    pitivi_timelinemedia_put (PITIVI_TIMELINEMEDIA(widget), 
			      convert_pix_time(PITIVI_TIMELINECELLRENDERER(layout), x));
  }
}

GtkWidget **layout_intersection_widget (GtkWidget *self, GtkWidget *widget, gint x)
{
  GList	*child;
  GtkRequisition req;
  GtkWidget **p;
  GtkWidget *matches[2];
  int xchild, widthchild = 0;
  
  matches[0] = 0;
  matches[1] = 0;
  p = matches;

  gtk_widget_size_request (widget, &req);
  child = gtk_container_get_children (GTK_CONTAINER (self));
  for (child = g_list_sort (child, compare_littlechild); 
       child; 
       child = child->next )
    {
      xchild = GTK_WIDGET(child->data)->allocation.x;
      widthchild = GTK_WIDGET(child->data)->allocation.width;
      if (xchild <= x && x <= xchild + widthchild)
	matches[0] = GTK_WIDGET (child->data);
      else if (xchild <= x + req.width && x + req.width <= xchild + widthchild)
	matches[1] = GTK_WIDGET (child->data);
    }
  g_list_free (child);
  return p;
}

void move_attached_effects (GtkWidget *widget, int x)
{
  PitiviTimelineMedia *media = (PitiviTimelineMedia *) widget;
  GList	*childs = media->effectschilds;
  int width = 0;

  while (childs)
    {
      pitivi_layout_move (GTK_LAYOUT (PITIVI_TIMELINEMEDIA (childs->data)->track), 
			  GTK_WIDGET (childs->data), x+width, 0);
      width += GTK_WIDGET (childs->data)->allocation.width;
      childs = childs->next;
    }
}

void move_media (GtkWidget *cell, GtkWidget *widget, guint x)
{
  GtkWidget **intersec;
  GtkWidget *first;
  int       xbegin;

  intersec = layout_intersection_widget (cell, widget, x);
  first = intersec[1];
  if (first && GTK_IS_WIDGET (first) && first->allocation.x != x)
    {
      xbegin = x + first->allocation.width;
      pitivi_layout_move (GTK_LAYOUT (cell), first, xbegin, 0);
      move_attached_effects (first, xbegin);
      move_media (cell, first, xbegin);
    }
  return;
}

void
move_child_on_layout (GtkWidget *self, GtkWidget *widget, gint x)
{
  GtkWidget **intersec;
  int xbegin = x;
  
  intersec = layout_intersection_widget (self, widget, x);
  if (!intersec[1] && intersec[0])
    {
      if ( x >=  intersec[0]->allocation.x &&
	   x <= intersec[0]->allocation.x+intersec[0]->allocation.width )
	xbegin = intersec[0]->allocation.x+intersec[0]->allocation.width;
      else
	xbegin = x;
      pitivi_layout_move (GTK_LAYOUT (self), widget, xbegin, 0);
      move_attached_effects (widget, xbegin);
    }
  else if (!intersec[0] && intersec[1])
    {
      move_media (self, intersec[1], x);
      move_attached_effects (intersec[1], x);
      pitivi_layout_move (GTK_LAYOUT (self), widget, x, 0);
      move_attached_effects (widget, x);
    }
  else if (intersec[1] && intersec[0])
    {
      xbegin = intersec[0]->allocation.x+intersec[0]->allocation.width;
      pitivi_layout_move (GTK_LAYOUT (self), widget, xbegin, 0);
      move_media (self, widget, xbegin);
      move_attached_effects (widget, x);
    }
  else
    {
      pitivi_layout_move (GTK_LAYOUT (self), widget, xbegin, 0);
      move_attached_effects (widget, xbegin);
    }
}

void
link_widgets ( PitiviTimelineMedia *media1, PitiviTimelineMedia *media2)
{
  media1->linked = GTK_WIDGET ( media2 );
  media2->linked = GTK_WIDGET ( media1 );
}

/**
 * pitivi_add_to_layout:
 * @GtkWidget: the parent widget
 * @GtkWidget: the child widget
 * @gint: the position in x
 * @gint: the position in y
 *
 * Add a widget to the layer
 *
 * Returns: A flag setted to TRUE
 */

gboolean
pitivi_add_to_layout (GtkWidget *self, GtkWidget *widget, gint x, gint y)
{
  PitiviTimelineCellRenderer *cell;
  GtkWidget **intersec;
  int	    xbegin;
  
  cell = PITIVI_TIMELINECELLRENDERER (self);
  intersec = layout_intersection_widget (self, widget, x);
  if (!intersec[0] && !intersec[1])
    pitivi_layout_put (GTK_LAYOUT (self), widget, x, 0);
  else if (!intersec[1]) /* right */
    {
      move_media (self, widget, x);
      xbegin = intersec[0]->allocation.x+intersec[0]->allocation.width;
      pitivi_layout_put (GTK_LAYOUT (self), widget, xbegin, y);
    }
  else if (!intersec[0]) /* left */
    {
      move_media (self, intersec[1], x);
      pitivi_layout_put (GTK_LAYOUT (self), widget, x, 0);
    }
  else if (intersec[1] && intersec[0])
    { 
      xbegin = intersec[0]->allocation.x+intersec[0]->allocation.width;
      pitivi_layout_put (GTK_LAYOUT (self), widget, xbegin, 0);
      move_media (self, intersec[1], xbegin);
    }
  return TRUE;
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

static void
pitivi_timelinecellrenderer_button_zooming (PitiviTimelineCellRenderer *self, PitiviCursor *cursor)
{
  GtkWidget *container = (GtkWidget *) pitivi_timelinewindow_get_container(self->private->timewin);
  if (cursor->type == PITIVI_CURSOR_ZOOM || cursor->type == PITIVI_CURSOR_ZOOM_INC)
    {
      if (self->private->timewin->zoom >= 16)
	{
	  load_cursor (GDK_WINDOW(container->window), cursor,  PITIVI_CURSOR_ZOOM_DEC);
	  self->private->timewin->zoom/=2;
	}
      else
	self->private->timewin->zoom*=2;
    }
  else if (cursor->type == PITIVI_CURSOR_ZOOM_DEC)
    {
      if (self->private->timewin->zoom - 2 > 0)
	self->private->timewin->zoom/=2;
      else
	self->private->timewin->zoom = 1;
      if (self->private->timewin->zoom <= 1)
	load_cursor (GDK_WINDOW(container->window), cursor,  PITIVI_CURSOR_ZOOM_INC);
    }
  pitivi_timelinewindow_zoom_changed (self->private->timewin);
  pitivi_ruler_set_zoom_metric (GTK_RULER (self->private->timewin->hruler),
				self->private->timewin->unit, self->private->timewin->zoom);
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
    pitivi_timelinecellrenderer_button_zooming (self, 
						self->private->timewin->toolbox->pitivi_cursor);
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
    case PROP_LAYER_PROPERTY:
      break;
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
/*   PitiviTimelineCellRenderer *self = (PitiviTimelineCellRenderer *) object; */

  switch (property_id)
    {
    case PROP_LAYER_PROPERTY:
      break;
    case PROP_TYPE_LAYER_PROPERTY:
      break;
    case PROP_TRACK_NB_PROPERTY:
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

/*
  convert_time_pix
  Returns the pixel size depending on the unit of the ruler, and the zoom level
*/

guint
convert_time_pix (PitiviTimelineCellRenderer *self, gint64 timelength)
{
  gint64 len = timelength;
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
      len = (timelength / GST_SECOND) 
	* pitivi_projectsettings_get_videorate(proj->settings)
	* self->private->timewin->zoom;
      break;
    default:
      break;
    }
  return len;
}

/*
  convert_pix_time
  Converts given pixel position into nanosecond time,
	depends on the zoom level, and the unit of the ruler
*/

gint64
convert_sub_pix_time (guint pos,
		      guint unit,
		      guint zoom,
		      guint videorate)
{
  gint64 res;

  switch ( unit ) {
  case PITIVI_SECONDS:
    res = (pos / zoom) * GST_SECOND;
    break;
  case PITIVI_FRAMES:
    res = (pos * GST_SECOND)
      / (videorate * zoom);
    break;
  case PITIVI_NANOSECONDS:
  default:
    res = pos;
    break;
  }
  return res;
}

gint64
convert_pix_time (PitiviTimelineCellRenderer *self, guint pos)
{
  PitiviProject	*proj = PITIVI_WINDOWS(self->private->timewin)->mainapp->project;
  guint videorate = 0;
  
  videorate = pitivi_projectsettings_get_videorate (proj->settings);
  return convert_sub_pix_time (pos,
			       self->private->timewin->unit,
			       self->private->timewin->zoom,
			       videorate
			       );
}

void
create_media_video_audio_track (PitiviTimelineCellRenderer *cell, PitiviSourceFile *sf, int x)
{
  PitiviTimelineMedia *media[2];
  guint64 length = sf->length;
  int width = 0;
  
  g_printf("create_media_video_audio_track\n");
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



static void
pitivi_timelinecellrenderer_drag_on_effects (PitiviTimelineCellRenderer *self,
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

static void 
pitivi_timelinecellrenderer_drag_on_track (PitiviTimelineCellRenderer *self, 
					   GtkWidget *source,
					   GtkSelectionData *selection,
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
	    move_child_on_layout (GTK_WIDGET (self->linked_track), dragged->linked, x);
	  }
	else
	  {
	    gtk_container_remove (GTK_CONTAINER (parent), GTK_WIDGET (source));
	    pitivi_add_to_layout (GTK_WIDGET (self),  source, x, 0);
	    
	    /* linked widget */
	    
	    GtkWidget *linked_ref = gtk_widget_ref (dragged->linked);
	    gtk_container_remove (GTK_CONTAINER (parent->linked_track), dragged->linked);
	    pitivi_add_to_layout (GTK_WIDGET (self->linked_track), linked_ref, x, 0);
	    gtk_widget_unref (linked_ref);
	  }
	pitivi_send_expose_event (self->linked_track);
      }
      else /* Single Widget */
	{
	  GTK_CONTAINER_CLASS (parent_class)->remove (GTK_CONTAINER (parent), GTK_WIDGET (dragged));
	  pitivi_add_to_layout  (GTK_WIDGET (self),  GTK_WIDGET (dragged), x, 0);
	}
    }
}



static void
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
  self->private->current_selection = selection;
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
	  pitivi_timelinecellrenderer_drag_on_source_file (self, self->private->current_selection, x, y);
	  gtk_drag_finish (dc, TRUE, TRUE, time);
	  break;
	case DND_TARGET_TIMELINEWIN:
	  x -= source->allocation.width/2;
	  if ( x < 0)
	    x = 0;
	  pitivi_timelinecellrenderer_drag_on_track (self, source, self->private->current_selection, x, y);
	  gtk_drag_finish (dc, TRUE, TRUE, time);
	  break;
	case DND_TARGET_EFFECTSWIN:
	  if (self->track_type == PITIVI_TRANSITION_TRACK)
	    {
	      x -= self->private->slide_width/2;
	      if ( x < 0)
		x = 0;
	      pitivi_timelinecellrenderer_drag_on_effects (self, self->private->current_selection, x, y);
	      gtk_drag_finish (dc, TRUE, TRUE, time);
	    }
	  break;
	default:
	  break;
	}
      g_signal_emit_by_name (self->private->timewin, "drag-source-end", NULL);
    }
}

guint 
slide_media_get_widget_size (PitiviTimelineMedia  *source)
{
  guint width = DEFAULT_MEDIA_SIZE;

  if (PITIVI_IS_TIMELINEMEDIA (source))
    width = GTK_WIDGET (source)->allocation.width;
  return width;
}

static void
resizing_media (PitiviTimelineMedia *source, PitiviTimelineCellRenderer *self, guint x)
{
  guint decrement = 0;
  
  decrement = GTK_RULER(self->private->timewin->hruler)->metric->pixels_per_unit;
  if (self->private->timewin->unit == PITIVI_FRAMES)
    decrement *= 10;
  if (x < GTK_WIDGET (source)->allocation.width + GTK_WIDGET (source)->allocation.x - (decrement))
    {
      /* Don"t touch please. */
      if (GTK_WIDGET (source)->allocation.width-decrement >= 1)
	gtk_widget_set_size_request (GTK_WIDGET (source),
				     GTK_WIDGET (source)->allocation.width-decrement,
				     GTK_WIDGET (source)->allocation.height);
    }
  else if (x > GTK_WIDGET (source)->allocation.width + GTK_WIDGET (source)->allocation.x)
    {
      if (source->original_width > GTK_WIDGET (source)->allocation.width)
	{
	  gtk_widget_set_size_request (GTK_WIDGET (source),
				       GTK_WIDGET (source)->allocation.width+decrement,
				       GTK_WIDGET (source)->allocation.height);
	}
    }
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
  
  cursor = pitivi_getcursor_id (widget);
  source = (PitiviTimelineMedia  *)gtk_drag_get_source_widget(dc);
  if (cursor->type == PITIVI_CURSOR_RESIZE)
    {
      resizing_media (source, self, x);
      return;
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
 * pitivi_timelinecellrenderer_zoom_changed:
 * @PitiviTimelineCellRenderer: the timelinecellrenderer
 *
 * Update the track with the new zoom settings
 *
 */

void
pitivi_timelinecellrenderer_zoom_changed (PitiviTimelineCellRenderer *self)
{
  GList	*child;
  GnlObject	*source;
  gint64	start,mstart,mstop;

  // redraw all childs at the good position and at the good width
  for (child = gtk_container_get_children(GTK_CONTAINER(self)); child; child = child->next) {
    if (PITIVI_IS_TIMELINEMEDIA(child->data)) {
      // get the child time position, it's length
      source = PITIVI_TIMELINEMEDIA(child->data)->sourceitem->gnlobject;
      start = GNL_OBJECT(source)->start;
      gnl_object_get_start_stop(GNL_OBJECT(source), &mstart, &mstop);
      // resize the child
      pitivi_media_set_size(GTK_WIDGET (child->data),
			    convert_time_pix(self, mstop-mstart));
      // move it to the good position
      pitivi_layout_move(GTK_LAYOUT(self), GTK_WIDGET(child->data), 
			 convert_time_pix(self, start) ,0);
    }
  }
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
pitivi_timelinecellrenderer_callb_select (PitiviTimelineCellRenderer *self)
{
  
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
pitivi_timelinecellrenderer_callb_dbk_source (PitiviTimelineCellRenderer *self, gpointer data)
{
  dispose_medias (self, data, 0);
}

static void
pitivi_timelinecellrenderer_callb_cut_source  (PitiviTimelineCellRenderer *container, guint x, gpointer data)
{
  PitiviTimelineMedia *media[2], *link;
/*   PitiviSourceFile	*sf; */
  GtkWidget *widget;
  gint64 start1, start2, stop1, stop2, mstart1, mstart2, mstop1, mstop2;
  guint	 pos =  0;
  
  if (GTK_IS_WIDGET (data))
    {
      widget = data;
      pos = widget->allocation.x+x; // calcul de la position du nouveau media

      start2 = stop1 = convert_pix_time(container, pos);
      pitivi_timelinemedia_get_start_stop(PITIVI_TIMELINEMEDIA(widget), &start1, &stop2);
      pitivi_timelinemedia_get_media_start_stop(PITIVI_TIMELINEMEDIA(widget), &mstart1, &mstop2);
      mstop1 = mstart2 = mstart1 + (stop1 - start1);
      widget->allocation.width = widget->allocation.width - x; // calcul

      // TODO / PABO : Creation d'un nouveau PitiviSourceFile pour le placer dans le nouveau PitiviTimelineMedia
      
/*       sf = pitivi_sourcefile_new(PITIVI_TIMELINEMEDIA(widget)->sourceitem->srcfile->filename, */
/* 				 PITIVI_WINDOWS(container->private->timewin)->mainapp); */
      g_printf("Creating a new timeline media with PitiviSourceFile %p\n", PITIVI_TIMELINEMEDIA (widget)->sourceitem->srcfile);
      media[0] = pitivi_timelinemedia_new ( PITIVI_TIMELINEMEDIA (widget)->sourceitem->srcfile,
					    widget->allocation.width, container );
      g_printf("Setting values for existing media\n");
      // donner un nouveau stop/media_stop a l'ancien media
      pitivi_timelinemedia_set_start_stop(PITIVI_TIMELINEMEDIA(widget), start1, stop1);
      pitivi_timelinemedia_set_media_start_stop(PITIVI_TIMELINEMEDIA(widget), mstart1, mstop1);
      g_printf("Setting values for new media\n");
      // donner un stop/media_start/media_stop au nouveau media
      pitivi_timelinemedia_set_media_start_stop(media[0], mstart2, mstop2);
      //      pitivi_timelinemedia_set_start_stop(media[0], start2, stop2);

      pitivi_layout_put (GTK_LAYOUT (container),  GTK_WIDGET ( media[0] ), pos, 0); // placement du nouveau media
      pitivi_media_set_size ( widget, x); // retaillage de l'ancien media
      pitivi_layout_add_to_composition (container, media[0]);
      gtk_widget_show ( GTK_WIDGET ( media[0] ) );
      if ( PITIVI_TIMELINEMEDIA (widget)->linked )
	{
	  link = PITIVI_TIMELINEMEDIA (PITIVI_TIMELINEMEDIA (widget)->linked);
	  GTK_WIDGET ( link )->allocation.width = widget->allocation.width;
	  media[1] = pitivi_timelinemedia_new (PITIVI_TIMELINEMEDIA (widget)->sourceitem->srcfile,
					       widget->allocation.width, container->linked_track );
	  pitivi_media_set_size ( PITIVI_TIMELINEMEDIA (widget)->linked, x);
	  link_widgets (media[0], media[1]);
	  g_printf("Setting values for existing media\n");
	  pitivi_timelinemedia_set_media_start_stop(PITIVI_TIMELINEMEDIA(link), mstart1, mstop1);
	  //pitivi_timelinemedia_set_start_stop(PITIVI_TIMELINEMEDIA(link), start1, stop1);
	  g_printf("Setting values for previous media\n");
	  pitivi_timelinemedia_set_media_start_stop(media[1], mstart2, mstop2);
	  //pitivi_timelinemedia_set_start_stop(media[1], start2, stop2);
	  pitivi_layout_put (GTK_LAYOUT ( container->linked_track ), GTK_WIDGET ( media[1] ), pos, 0);
	  pitivi_layout_add_to_composition (PITIVI_TIMELINECELLRENDERER (container->linked_track),
					    PITIVI_TIMELINEMEDIA (media[1]));
	  gtk_widget_show (GTK_WIDGET ( media[1] ));
	}
      else
	pitivi_calculate_priorities ( GTK_WIDGET (container) );
      PitiviThumbs* thumb = pitivi_thumbs_new (PITIVI_TIMELINEMEDIA (widget)->sourceitem->srcfile->filename, 
					       G_OBJECT (media[0]),
					       0);
      /* To do calculate frame thumb */
      g_object_set (thumb, "frame", 200LL, NULL);
      PITIVI_THUMBS_GET_CLASS (thumb)->generate_thumb (thumb);
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
	    gtk_container_remove (GTK_CONTAINER (self->linked_track), media->linked);
	    pitivi_layout_remove_from_composition (PITIVI_TIMELINECELLRENDERER (self->linked_track),
						   PITIVI_TIMELINEMEDIA (media->linked));
	  }
	  gtk_container_remove (GTK_CONTAINER (self), GTK_WIDGET (media) );
	  pitivi_layout_remove_from_composition (self, media);
	}
      delete = delete->next;
    }
  g_list_free (delete);
  g_list_free (child);
  pitivi_calculate_priorities ( GTK_WIDGET (self) );
}

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

/*
 **********************************************************
 * Instance Init  			                  *
 *							  *
 **********************************************************
*/

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
		gtk_container_remove ( GTK_CONTAINER (PITIVI_TIMELINEMEDIA (media->effectschilds->data)->track), 
				       GTK_WIDGET (media->effectschilds->data));
	      media->effectschilds = media->effectschilds->next;
	    }
	gtk_container_remove ( GTK_CONTAINER (self), GTK_WIDGET (media));
	pitivi_layout_remove_from_composition (self, media);
      }
    }
  pitivi_calculate_priorities ( GTK_WIDGET (self) );
  g_list_free (child);
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
 
  layoutsignals[SELECT_SIGNAL] = g_signal_new ("select",
					       G_TYPE_FROM_CLASS (g_class),
					       G_SIGNAL_RUN_FIRST | G_SIGNAL_ACTION,
					       G_STRUCT_OFFSET (PitiviTimelineCellRendererClass, select),
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

  layoutsignals[DBK_SOURCE_SIGNAL] = g_signal_new ("double-click-source",
						   G_TYPE_FROM_CLASS (g_class),
						   G_SIGNAL_RUN_FIRST | G_SIGNAL_ACTION,
						   G_STRUCT_OFFSET (PitiviTimelineCellRendererClass, dbk_source),
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
  cell_class->select = pitivi_timelinecellrenderer_callb_select;
  cell_class->deselect = pitivi_timelinecellrenderer_callb_deselect;
  cell_class->drag_source_begin = pitivi_timelinecellrenderer_callb_drag_source_begin;
  cell_class->drag_source_end = pitivi_timelinecellrenderer_callb_drag_source_end;
  cell_class->delete = pitivi_timelinecellrenderer_callb_delete_sf;
  cell_class->dbk_source = pitivi_timelinecellrenderer_callb_dbk_source;
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
