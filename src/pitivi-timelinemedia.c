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
#include "pitivi-timelinecellrenderer.h"
#include "pitivi-cursor.h"
#include "pitivi-dragdrop.h"

static	GtkWidgetClass	*parent_class;

// Caching Operation  
static	GdkPixmap	*pixmap = NULL;


// Properties Enumaration

typedef enum {
  PITIVI_MD_SOURCEFILE_PROPERTY = 1,
} PitiviMediaProperty;



// Source drag 'n drop on a widget

enum
  {
    MEDIA_DRAG_BEGIN_SIGNAL,
    MEDIA_DRAG_GET_SIGNAL,
    MEDIA_DRAG_END_SIGNAL,
    MEDIA_DRAG_DELETE_SIGNAL,
    LAST_SIGNAL
  };

static guint	      media_signals[LAST_SIGNAL] = {0};

static GtkTargetEntry TargetSameEntry[] =
  {
    { "pitivi/sourcetimeline", 0, DND_TARGET_TIMELINEWIN },
  };

static gint iNbTargetSameEntry = G_N_ELEMENTS (TargetSameEntry);


struct _PitiviTimelineMediaPrivate
{
  /* instance private members */
  gboolean	dispose_has_run;
  PitiviCursorType cursor_type;
  
  guint64	original_width;
  guint64	original_height;
};

/*
 * forward definitions
 */

/*
 * Insert "added-value" functions here
 */

PitiviTimelineMedia *
pitivi_timelinemedia_new (PitiviSourceFile *sf)
{
  PitiviTimelineMedia	*timelinemedia;

  timelinemedia = (PitiviTimelineMedia *) g_object_new(PITIVI_TIMELINEMEDIA_TYPE, NULL);

  timelinemedia->sf = sf;
  g_assert(timelinemedia != NULL);
  return timelinemedia;
}

static GObject *
pitivi_timelinemedia_constructor (GType type,
				  guint n_construct_properties,
				  GObjectConstructParam * construct_properties)
{
  GObject *obj;
  {
    /* Invoke parent constructor. */
    PitiviTimelineMediaClass *klass;
    GObjectClass *parent_class;
    klass = PITIVI_TIMELINEMEDIA_CLASS (g_type_class_peek (PITIVI_TIMELINEMEDIA_TYPE));
    parent_class = G_OBJECT_CLASS (g_type_class_peek_parent (klass));
    obj = parent_class->constructor (type, n_construct_properties,
				     construct_properties);
  }

  /* do stuff. */
  
  return obj;
}


void 
draw_selection_dash (GtkWidget *widget, int width)
{
  char dash [2] = {4, 4};
  GdkGC *style = gdk_gc_new ( widget->window );
  GdkWindow *window;
  
  gdk_gc_set_dashes ( style, 0, (gint8*)dash, sizeof (dash) / 2); 
  gdk_gc_set_line_attributes ( style, width, GDK_LINE_ON_OFF_DASH, GDK_CAP_BUTT, GDK_JOIN_MITER);
  window = GDK_WINDOW (widget->window);
  gdk_draw_rectangle ( window, style, FALSE, 0, 0, widget->allocation.width, widget->allocation.height);
}

static gint
pitivi_timelinemedia_expose (GtkWidget      *widget,
			     GdkEventExpose *event)
{
  GdkWindow *window;
  
  PitiviTimelineMedia	*self = PITIVI_TIMELINEMEDIA (widget);
  gtk_paint_box (widget->style, widget->window,
		 GTK_STATE_NORMAL, GTK_SHADOW_IN,
		 &event->area, widget, "mediadefault",
		 0, 0, widget->allocation.width-2, -1);
  if (self->selected == TRUE)
    draw_selection_dash (widget, 4);
  return FALSE;
}

static void
pitivi_timelinemedia_drag_get  (GtkWidget          *widget,
				GdkDragContext     *context,
				GtkSelectionData   *selection_data,
				guint               info,
				guint32             time,
				gpointer	    dragging)
{
  PitiviCursor *cursor;
  PitiviTimelineCellRenderer *cell;
 
  cursor = pitivi_getcursor_id (widget);
  if (cursor->type == PITIVI_CURSOR_SELECT || cursor->type == PITIVI_CURSOR_HAND)
    gtk_selection_data_set (selection_data, selection_data->target, 
			    8, (void *) widget, 
			    sizeof (PitiviTimelineMedia));
  
  cell = (PitiviTimelineCellRenderer *) gtk_widget_get_parent (widget);
  cell->motion_area->x = widget->allocation.width;
  cell->motion_area->width = widget->allocation.width;
  
}


static void
pitivi_timelinemedia_drag_delete  (GtkWidget          *widget,
				   GdkDragContext     *context,
				   gpointer	      dragging)
{
  GtkContainer *container;
  
  container = (GtkContainer *) gtk_widget_get_parent ( widget );
  pitivi_timelinecellrenderer_remove (container, GTK_WIDGET ( widget ));
}

static void
pitivi_timelinemedia_drag_begin (GtkWidget          *widget,
				 GdkDragContext     *context,
				 gpointer	    user_data)
{ 
  PitiviCursor *cursor;
  PitiviTimelineCellRenderer *cell;
  GdkEventExpose ev;
  gboolean retval;
  
  cell = (PitiviTimelineCellRenderer *) gtk_widget_get_parent (widget);
  cell->motion_area->x = widget->allocation.width;
  cell->motion_area->width = widget->allocation.width;
  pitivi_timelinecellrenderer_deselection_ontracks (GTK_WIDGET (cell), TRUE);
}


static void
pitivi_timelinemedia_instance_init (GTypeInstance * instance, gpointer g_class)
{
  PitiviTimelineMedia *self = (PitiviTimelineMedia *) instance;

  self->private = g_new0(PitiviTimelineMediaPrivate, 1);
  
  /* initialize all public and private members to reasonable default values. */ 
  
  self->private->dispose_has_run = FALSE;
  
  /* Do only initialisation here */
  /* The construction of the object should be done in the Constructor
     So that properties set at instanciation can be set */
  
  self->selected = FALSE;
  self->private->cursor_type = PITIVI_CURSOR_SELECT;

  gtk_drag_source_set  (GTK_WIDGET (self),
			GDK_BUTTON1_MASK|GDK_BUTTON3_MASK,
			TargetSameEntry, 
			iNbTargetSameEntry, 
			GDK_ACTION_COPY);
  
  media_signals[MEDIA_DRAG_BEGIN_SIGNAL] = g_signal_connect (GTK_WIDGET (self), "drag_begin",
							     G_CALLBACK (pitivi_timelinemedia_drag_begin), NULL);
  media_signals[MEDIA_DRAG_GET_SIGNAL] = g_signal_connect (GTK_WIDGET (self), "drag_data_get",	      
							   G_CALLBACK (pitivi_timelinemedia_drag_get), NULL);
  media_signals[MEDIA_DRAG_DELETE_SIGNAL] = g_signal_connect (GTK_WIDGET (self), "drag_data_delete",
							      G_CALLBACK (pitivi_timelinemedia_drag_delete), NULL);
}

static void
pitivi_timelinemedia_dispose (GObject *object)
{
  PitiviTimelineMedia	*self = PITIVI_TIMELINEMEDIA(object);

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
pitivi_timelinemedia_finalize (GObject *object)
{
  PitiviTimelineMedia	*self = PITIVI_TIMELINEMEDIA(object);

  /* 
   * Here, complete object destruction. 
   * You might not need to do much... 
   */

  g_free (self->private);
  G_OBJECT_CLASS (parent_class)->finalize (object);
}

static void
pitivi_timelinemedia_set_property (GObject * object,
				   guint property_id,
				   const GValue * value, GParamSpec * pspec)
{
  PitiviTimelineMedia *self = (PitiviTimelineMedia *) object;

  switch (property_id)
    {
    case PITIVI_MD_SOURCEFILE_PROPERTY:
      break;
    default:
      g_assert (FALSE);
      break;
    }
}

static void
pitivi_timelinemedia_get_property (GObject * object,
			      guint property_id,
			      GValue * value, GParamSpec * pspec)
{
  PitiviTimelineMedia *self = (PitiviTimelineMedia *) object;

  switch (property_id)
    {
    default:
      /* We don't have any other property... */
      g_assert (FALSE);
      break;
    }
}

static void
pitivi_timelinemedia_size_request (GtkWidget *widget,
				   GtkRequisition *requisition)
{
  g_return_if_fail (widget != NULL);
  g_return_if_fail (requisition != NULL);
  
  requisition->width = DEFAULT_WIDTH;
  requisition->height = DEFAULT_HEIGHT;
}

static void
pitivi_timelinemedia_size_allocate (GtkWidget     *widget,
				    GtkAllocation *allocation)
{
  g_return_if_fail (widget != NULL);
  g_return_if_fail (allocation != NULL);

  widget->allocation = *allocation;
  if (GTK_WIDGET_REALIZED (widget))
    {
      gdk_window_move_resize (widget->window,
			      allocation->x, allocation->y,
			      allocation->width, allocation->height);
      
    }
}

static void
pitivi_timelinemedia_realize (GtkWidget *widget)
{
  GdkWindowAttr attributes;
  gint attributes_mask;

  g_return_if_fail (widget != NULL);

  GTK_WIDGET_SET_FLAGS (widget, GTK_REALIZED);
  
  attributes.window_type = GDK_WINDOW_CHILD;
  attributes.x = widget->allocation.x;
  attributes.y = widget->allocation.y;
  attributes.width = widget->allocation.width;
  attributes.height = widget->allocation.height;
  attributes.wclass = GDK_INPUT_OUTPUT;
  attributes.event_mask = gtk_widget_get_events (widget) | 
    GDK_EXPOSURE_MASK |
    GDK_ENTER_NOTIFY_MASK |
    GDK_LEAVE_NOTIFY_MASK |
    GDK_BUTTON_PRESS_MASK |
    GDK_VISIBILITY_NOTIFY_MASK |
    GDK_BUTTON_RELEASE_MASK |
    GDK_POINTER_MOTION_MASK |
    GDK_POINTER_MOTION_HINT_MASK;
  
  attributes.visual = gtk_widget_get_visual (widget);
  attributes.colormap = gtk_widget_get_colormap (widget);

  attributes_mask = GDK_WA_X | GDK_WA_Y | GDK_WA_VISUAL | GDK_WA_COLORMAP;
  
  widget->window = gdk_window_new (widget->parent->window, &attributes, attributes_mask);
  widget->style = gtk_style_attach (widget->style, widget->window);
  
  gdk_window_set_user_data (widget->window, widget);
  gtk_style_set_background (widget->style, widget->window, GTK_STATE_ACTIVE);
}

static void
pitivi_timelinemedia_leave_notify_event (GtkWidget        *widget,
					 GdkEventMotion   *event)
{
  PitiviCursor *cursor;
  PitiviTimelineMedia *self;
  GdkModifierType mods;
  gint x, y, mask;

  x = event->x;
  self = PITIVI_TIMELINEMEDIA (widget);
  cursor = pitivi_getcursor_id (widget);
  load_cursor (widget->window, cursor, self->private->cursor_type);
  gtk_drag_source_set  (GTK_WIDGET (self),
			GDK_BUTTON1_MASK|GDK_BUTTON3_MASK,
			TargetSameEntry, 
			iNbTargetSameEntry, 
			GDK_ACTION_COPY);
}

static
gint pitivi_timelinemedia_motion_notify_event (GtkWidget        *widget,
					       GdkEventMotion   *event)
{
  PitiviCursor *cursor;
  PitiviTimelineMedia *self;
  GdkModifierType mods;
  gint x, y, mask;
  gint x_size_reduce;

  g_return_val_if_fail (widget != NULL, FALSE);
  g_return_val_if_fail (event != NULL, FALSE);
  self = PITIVI_TIMELINEMEDIA (widget);
  
  x = event->x;
  y = event->y;
  
  if (event->is_hint || (event->window != widget->window))
    {
      cursor = pitivi_getcursor_id (widget);
      if ((event->x <= REDUCE_CURSOR_AREA_SIZE) 
	  || ((event->x <= widget->allocation.width) 
	      && event->x >= (widget->allocation.width - REDUCE_CURSOR_AREA_SIZE)))
	{
	  if (cursor->type !=  PITIVI_CURSOR_RESIZE)
	    {
	      self->private->cursor_type = cursor->type;
	      load_cursor (widget->window, cursor, PITIVI_CURSOR_RESIZE);
	      gtk_drag_source_unset (widget);
	    }
	  x_size_reduce = widget->allocation.width-(widget->allocation.width-event->x);
	  if (event->state >= 256)
	    {
	      if (((event->x <= widget->allocation.width) 
		   && event->x >= (widget->allocation.width - REDUCE_CURSOR_AREA_SIZE)))
		{
		  if (x_size_reduce > 0)
		    {
		      gtk_widget_set_size_request (widget, 
						   x_size_reduce,
						   widget->allocation.height);
		    }
		}
	      if (event->x <= REDUCE_CURSOR_AREA_SIZE)
		 {
		   
		 }
	    }
	}
      else
	{
	  if (cursor->type == PITIVI_CURSOR_SELECT || cursor->type == PITIVI_CURSOR_HAND)
	    {
	      gtk_drag_source_set  (widget, GDK_BUTTON1_MASK|GDK_BUTTON3_MASK, 
				    TargetSameEntry, 
				    iNbTargetSameEntry, 
				    GDK_ACTION_COPY);
	    }
	  else
	    gtk_drag_source_unset (widget);
	  load_cursor (widget->window, cursor, self->private->cursor_type);
	}
    }
  gdk_window_get_pointer (widget->window, &x, &y, &mods);
}


static gint
pitivi_timelinemedia_configure_event (GtkWidget *widget, GdkEventConfigure *event)
{
  PitiviCursor *cursor;
  PitiviTimelineMedia *self = PITIVI_TIMELINEMEDIA (widget);
  
  cursor = pitivi_getcursor_id (widget);
  self->private->cursor_type = cursor->type;
  return FALSE;
}


static gint
pitivi_timelinemedia_button_release_event (GtkWidget      *widget,
					   GdkEventButton *event)
{ 
  PitiviCursor *cursor;
  
  cursor = pitivi_getcursor_id (widget);
  if (cursor->type == PITIVI_CURSOR_CUT)
    {
      g_printf ("coucou\n");
    }
  return FALSE;
}

static void
pitivi_timelinemedia_class_init (gpointer g_class, gpointer g_class_data)
{
  GObjectClass *gobject_class = G_OBJECT_CLASS (g_class);
  PitiviTimelineMediaClass *klass = PITIVI_TIMELINEMEDIA_CLASS (g_class);
  GtkWidgetClass *widget_class = GTK_WIDGET_CLASS (g_class);

  parent_class = GTK_WIDGET_CLASS (g_type_class_peek_parent (g_class));

  gobject_class->constructor = pitivi_timelinemedia_constructor;
  gobject_class->dispose = pitivi_timelinemedia_dispose;
  gobject_class->finalize = pitivi_timelinemedia_finalize;

  gobject_class->set_property = pitivi_timelinemedia_set_property;
  gobject_class->get_property = pitivi_timelinemedia_get_property;

  widget_class->expose_event = pitivi_timelinemedia_expose;
  widget_class->size_request = pitivi_timelinemedia_size_request;
  widget_class->size_allocate = pitivi_timelinemedia_size_allocate; 
  widget_class->realize = pitivi_timelinemedia_realize;
  widget_class->motion_notify_event = pitivi_timelinemedia_motion_notify_event;
  widget_class->configure_event = pitivi_timelinemedia_configure_event;
  widget_class->leave_notify_event = pitivi_timelinemedia_leave_notify_event;
  widget_class->button_release_event = pitivi_timelinemedia_button_release_event;
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
      type = g_type_register_static (GTK_TYPE_WIDGET,
				     "PitiviTimelineMediaType", &info, 0);
    }

  return type;
}
