/* 
 * PiTiVi
 * Copyright (C) <2004> Guillaume Casanova <casano_g@epita.fr>
 *                      
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
#include "pitivi-timelinemedia.h"
#include "pitivi-cursor.h"
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

void draw_media (GtkWidget *widget);
void draw_media_expose (GtkWidget *widget);


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
    MEDIA_DRAG_BEGIN_SIGNAL,
    MEDIA_DRAG_GET_SIGNAL,
    MEDIA_DRAG_END_SIGNAL,
    MEDIA_DRAG_DELETE_SIGNAL,
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
 * Source drag 'n drop on a widge		          *
 *							  *
 **********************************************************
*/

static GtkTargetEntry TargetSameEntry[] =
  {
    { "pitivi/sourcetimeline", 0, DND_TARGET_TIMELINEWIN },
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

static GtkItemFactoryEntry  TimeItemPopup[] = {
  {"/Dissociate", NULL, pitivi_timelinemedia_callb_dissociate, 0, "<Item>", NULL},
  {"/Delete", NULL, pitivi_timelinemedia_callb_destroy, 1, "<Item>", NULL},
  {"/Sep1", NULL, NULL, 0, "<Separator>"},
  {"/Copy", NULL, pitivi_timelinemedia_callb_copied, 0, "<Item>", NULL},
  {"/Cut", NULL, pitivi_timelinemedia_callb_cut, 0, "<Item>", NULL},
  {"/Sep1", NULL, NULL, 0, "<Separator>"},
  {"/Properties", NULL, NULL, 0, "<Item>", NULL},
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
  GdkPixmap	   *pixmapcache;
};

PitiviTimelineMedia *
pitivi_timelinemedia_new ( PitiviSourceFile *sf, int width, PitiviTimelineCellRenderer *track )
{
  PitiviTimelineMedia	*this;
  PitiviLayerType	type;
 
  type = PITIVI_NO_TRACK;
  if (sf)
    type = check_media_type (sf);
  
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
  GtkTooltipsData*	data;
  char			*str;
  GnlObject		*obj = this->sourceitem->gnlobject;

  /* Make the string */
  str = g_strdup_printf("%s\nposition : %4lld:%3lld->%4lld:%3lld\nMedia : %4lld:%3lld->%4lld:%3lld",
			gst_element_get_name(GST_ELEMENT (obj)),
			obj->start / GST_SECOND, (obj->start % GST_SECOND) / GST_MSECOND,
			obj->stop / GST_SECOND, (obj->stop % GST_SECOND) / GST_MSECOND,
			obj->media_start / GST_SECOND, (obj->media_start % GST_SECOND) / GST_MSECOND,
			obj->media_stop / GST_SECOND, (obj->media_stop % GST_SECOND) / GST_MSECOND);
  gtk_tooltips_set_tip (this->private->tooltips, GTK_WIDGET(this),
			str, NULL);
  g_free(str);
}

void
pitivi_timelinemedia_get_start_stop (PitiviTimelineMedia *media, gint64 *start, gint64 *stop)
{
  gnl_object_get_start_stop(media->sourceitem->gnlobject, start, stop);
}

void
pitivi_timelinemedia_set_start_stop (PitiviTimelineMedia *media, gint64 start, gint64 stop)
{
  g_printf("pitivi_timelinemedia start:%lld stop:%lld\n", start, stop);
  gnl_object_set_start_stop (media->sourceitem->gnlobject, start, stop);
  pitivi_timelinemedia_update_tooltip(media);
}

void
pitivi_timelinemedia_put (PitiviTimelineMedia *media, gint64 start)
{
  gint64 mstart, mstop;

  // check the size of the widget !!!
  gnl_object_get_media_start_stop (media->sourceitem->gnlobject, &mstart, &mstop);
  g_printf("pitivi_timelinemedia_put start:%lld stop:%lld\n", start, start + mstop - mstart);
  gnl_object_set_start_stop (media->sourceitem->gnlobject, start, start + mstop - mstart);
  pitivi_timelinemedia_update_tooltip(media);
}

void
pitivi_timelinemedia_get_media_start_stop (PitiviTimelineMedia *media, gint64 *start, gint64 *stop)
{
  gnl_object_get_media_start_stop (media->sourceitem->gnlobject, start, stop);
}


void
pitivi_timelinemedia_set_media_start_stop (PitiviTimelineMedia *media, gint64 start, gint64 stop)
{
  g_printf("pitivi_timelinemedia mediastart:%lld mediastop:%lld\n", start, stop);
  gnl_object_set_media_start_stop (media->sourceitem->gnlobject, start, stop);
  pitivi_timelinemedia_update_tooltip(media);
}

void
pitivi_timelinemedia_set_priority (PitiviTimelineMedia *media, gint priority)
{
  gnl_object_set_priority (media->sourceitem->gnlobject, priority);
}

GtkWidget *
pitivi_timelinemedia_get_track (PitiviTimelineMedia *media)
{
  return GTK_WIDGET (media->private->cell);
}

static gint
pitivi_timelinemedia_expose (GtkWidget      *widget,
			     GdkEventExpose *event)
{
  PitiviTimelineMedia  *this = PITIVI_TIMELINEMEDIA (widget);
  GtkStyle *style;
  
  gdk_draw_drawable (GDK_WINDOW (widget->window),
			 widget->style->fg_gc[GTK_WIDGET_STATE (widget)],
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
  GObject *object;
  PitiviTimelineMedia *this;
  gchar *name;
  
  /* Constructor  */
  
  object = (* G_OBJECT_CLASS (parent_class)->constructor) 
    (type, n_construct_properties, construct_properties);
  
  this = (PitiviTimelineMedia *) object;
  
  /* Tooltip  */
  
  this->private->tooltips = gtk_tooltips_new();
  
  /* Source Item  */

  this->sourceitem = g_new0 (PitiviSourceItem, 1);
  this->sourceitem->srcfile = g_new0 (PitiviSourceFile, 1);
  memcpy (this->sourceitem->srcfile, this->private->sf, sizeof (*this->private->sf)); 
  this->sourceitem->id = this->track->nb_added[0];
  
  if (this->track->track_type == PITIVI_AUDIO_TRACK)
    this->sourceitem->isaudio = TRUE;

  if ( this->sourceitem->srcfile->pipeline )
    {
      pitivi_printf_element(this->sourceitem->srcfile->pipeline );
      /* Construct Id : filename + '_' + mediatype  + '_' + id */
      name = g_malloc (strlen (this->sourceitem->srcfile->filename) + 
		       strlen (this->sourceitem->srcfile->mediatype) + 10);
      sprintf (name, "%s_%s_%lld", this->sourceitem->srcfile->filename, 
	       this->sourceitem->srcfile->mediatype, this->sourceitem->id);
      if ( this->track->track_type == PITIVI_EFFECTS_TRACK ||  this->track->track_type == PITIVI_TRANSITION_TRACK )
	{
	  this->sourceitem->gnlobject = (GnlObject *)gnl_operation_new (name, this->sourceitem->srcfile->pipeline);
	  if ( this->track->track_type == PITIVI_TRANSITION_TRACK )
	    /* specific to transition */
	    pitivi_timelinemedia_set_priority (this, 1);
	}
      else
	{
	  this->sourceitem->gnlobject = (GnlObject *)gnl_source_new (name, this->sourceitem->srcfile->pipeline);
	  //gnl_object_set_media_start_stop (GNL_OBJECT(this->sourceitem->gnlobject), 0, this->sourceitem->srcfile->length);
	}
    }
    
  gtk_widget_set_size_request (GTK_WIDGET (this), this->private->width, GTK_WIDGET (this->track)->allocation.height);
  gtk_drawing_area_size (GTK_DRAWING_AREA (this), this->private->width, GTK_WIDGET (this->track)->allocation.height);
  /* Setting Tooltip */
  pitivi_timelinemedia_update_tooltip (this);
  
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
pitivi_timelinemedia_drag_delete  (GtkWidget          *widget,
				   GdkDragContext     *context,
				   gpointer	      dragging)
{
}

static void
pitivi_timelinemedia_drag_begin (GtkWidget          *widget,
				 GdkDragContext     *context,
				 gpointer	    user_data)
{ 
}

static void
connect_drag_and_drop (GtkWidget *widget)
{
  media_signals[MEDIA_DRAG_BEGIN_SIGNAL] = g_signal_connect (widget, "drag_begin",
							     G_CALLBACK (pitivi_timelinemedia_drag_begin), NULL);
  media_signals[MEDIA_DRAG_GET_SIGNAL] = g_signal_connect (widget, "drag_data_get",	      
							   G_CALLBACK (pitivi_timelinemedia_drag_get), NULL);
  media_signals[MEDIA_DRAG_DELETE_SIGNAL] = g_signal_connect (widget, "drag_data_delete",
							      G_CALLBACK (pitivi_timelinemedia_drag_delete), NULL);  
}

static void
pitivi_timelinemedia_instance_init (GTypeInstance * instance, gpointer g_class)
{
  GdkPixbuf *pixbuf;
  PitiviTimelineMedia *this = (PitiviTimelineMedia *) instance;
  PitiviTimelineCellRenderer *container;
  PitiviCursor  *cursor;
  
  gtk_widget_set_events (GTK_WIDGET (this), GDK_EXPOSURE_MASK
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
  
  pixbuf = gtk_widget_render_icon(GTK_WIDGET (this), PITIVI_STOCK_HAND, GTK_ICON_SIZE_DND, NULL);
  gtk_drag_source_set_icon_pixbuf (GTK_WIDGET (this), pixbuf);
  connect_drag_and_drop (GTK_WIDGET (this));
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
  PitiviTimelineMedia *this = (PitiviTimelineMedia *) object;

  switch (property_id)
    {
    default:
      /* We don't have any other property... */
      g_assert (FALSE);
      break;
    }
}

void
show_audio_media (GtkWidget *widget)
{
  PitiviTimelineMedia	*this = PITIVI_TIMELINEMEDIA (widget);

  if ( this->sourceitem->srcfile->thumbs_audio  )
    gdk_draw_pixbuf( this->private->pixmapcache, NULL, GDK_PIXBUF 
		     ( this->sourceitem->srcfile->thumbs_audio ), 0, 0, 0, 0, 
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
show_video_media (GtkWidget *widget)
{
  PitiviTimelineMedia	*this = PITIVI_TIMELINEMEDIA (widget);
  
  if (GTK_IS_WIDGET ( widget ) )
    {
      if ( this->sourceitem->srcfile->thumbs_video )
	{
	  gdk_draw_pixbuf( this->private->pixmapcache, NULL, 
			   this->sourceitem->srcfile->thumbs_video, 0, 0, 0, 0, 
			   -1, 
			   -1, 
			   GDK_RGB_DITHER_MAX, 0, 0);
	}
    }
}

void
show_effects_media (GtkWidget *widget)
{
  PitiviTimelineMedia	*this = PITIVI_TIMELINEMEDIA (widget);
  int count, pix_width = 0;
  
  if (GTK_IS_WIDGET ( widget ))
    {
      if ( this->sourceitem->srcfile->thumbs_effect )
	{
	  pix_width = gdk_pixbuf_get_width (this->sourceitem->srcfile->thumbs_effect);
	  for (count = 0; count < this->private->width; count+= pix_width )
	    gdk_draw_pixbuf( this->private->pixmapcache, NULL, GDK_PIXBUF 
			     (  this->sourceitem->srcfile->thumbs_effect  ), 0, 0, count, 0, -1, -1, GDK_RGB_DITHER_MAX, 0, 0);
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
draw_media (GtkWidget *widget)
{
  PitiviTimelineMedia *this = (PitiviTimelineMedia *)widget;
  
  if (GDK_IS_PIXMAP ( this->private->pixmapcache ))
    {
      gdk_draw_rectangle ( this->private->pixmapcache, 
			   widget->style->white_gc,
			   TRUE, 0, 0,
			   -1, -1);
      
      gdk_draw_rectangle ( this->private->pixmapcache, 
			   widget->style->black_gc,
			   FALSE, 0, 0,
			   widget->allocation.width-1,  widget->allocation.height-1);
      
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
	}
        
      if (this->selected)
	{
	  GdkColor selection = {0, 65355, 0};
	  draw_selection_dash (widget, this->private->pixmapcache, &selection, 2);
	}
    }
}


static void
pitivi_timelinemedia_leave_notify_event (GtkWidget        *widget,
					 GdkEventMotion   *event)
{
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
	  this->private->menu = GTK_WIDGET (create_menupopup (widget, TimeItemPopup, iNbTimeItemPopup));
	  gtk_menu_popup(GTK_MENU (this->private->menu), NULL, NULL, NULL, NULL, event->button, event->time);
	}
    }
  return TRUE;
}

static gint
pitivi_timelinemedia_button_release_event (GtkWidget      *widget,
					   GdkEventButton *event)
{ 
  PitiviTimelineMedia *this = PITIVI_TIMELINEMEDIA (widget);
  PitiviTimelineCellRenderer *container;
  gint x = event->x;

  PitiviCursor *cursor = pitivi_getcursor_id (widget);
  if (cursor->type == PITIVI_CURSOR_ZOOM)
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
pitivi_timelinemedia_callb_associate_effect (PitiviTimelineMedia *this, gpointer data)
{
  PitiviSourceFile *se =  (PitiviSourceFile *)data;
  PitiviTimelineMedia *neareffect, *effect;
  GList	*listeffects = NULL;
  int offset_currenteffect = 0;
  
  
  se->length = this->sourceitem->srcfile->length;
  if ( this->track->effects_track)
    {
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
	      pitivi_layout_put (GTK_LAYOUT (this->track->effects_track), 
				 GTK_WIDGET (effect), 
				 GTK_WIDGET (this)->allocation.x, 
				 0);
	      this->effectschilds = g_list_append (this->effectschilds, effect);
	      this->effectschilds = g_list_sort (this->effectschilds, compare_littlechild);
	      calculate_priorities ( this->track );
	      gtk_widget_show (GTK_WIDGET (effect));		
	    }
	  /* ----------------------------------------------------------- */
	}
    }
}

void
pitivi_timelinemedia_callb_destroy (PitiviTimelineMedia *this, gpointer data)
{
  GtkWidget *track;
  
  if (this->selected)
    {
      if ( this->linked )
	{
	  gtk_container_remove (GTK_CONTAINER ( this->track->linked_track ), this->linked );
	  calculate_priorities ( this->track->linked_track );
	}
      track = &(*GTK_WIDGET (this->track));
      gtk_container_remove (GTK_CONTAINER ( track ), GTK_WIDGET (this) );
      calculate_priorities ( track );
    }
}

static gboolean
pitivi_timelinemedia_callb_key_release_event (GtkWidget *widget,
					      GdkEventKey *event)
{
  PitiviTimelineMedia *this = PITIVI_TIMELINEMEDIA (widget);
  pitivi_timelinemedia_callb_destroy (this, event);
  return TRUE;
}

static void
pitivi_timelinemedia_callb_snapped_effect (PitiviTimelineMedia *media, gpointer data)
{
  /* FIXME Deference pointer */
  g_object_unref (media->sourceitem->srcfile->thumbs_video);
  media->sourceitem->srcfile->thumbs_video = gdk_pixbuf_new_from_file (PITIVI_THUMBS(data)->output, NULL);
  draw_media_expose (GTK_WIDGET (media));
  g_object_ref (media->sourceitem->srcfile->thumbs_video);
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
						     G_MININT, G_MAXINT, 0, G_PARAM_READWRITE|G_PARAM_CONSTRUCT )); 
  
  g_object_class_install_property (G_OBJECT_CLASS (gobject_class), PROP_MEDIA_WIDTH,
				   g_param_spec_int ("width","width","width",
						     G_MININT, G_MAXINT, 0, G_PARAM_READWRITE|G_PARAM_CONSTRUCT )); 

  g_object_class_install_property (G_OBJECT_CLASS (gobject_class), PROP_SOURCEFILE,
				   g_param_spec_pointer ("source_file","source_file","source_file",
							 G_PARAM_READWRITE|G_PARAM_CONSTRUCT));
  
  g_object_class_install_property (G_OBJECT_CLASS (gobject_class), PROP_TRACK,
				   g_param_spec_pointer ("track","track","track",
							 G_PARAM_READWRITE | G_PARAM_CONSTRUCT_ONLY));
  
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

void	pitivi_timelinemedia_callb_cut (PitiviTimelineMedia *this, gpointer data)
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
