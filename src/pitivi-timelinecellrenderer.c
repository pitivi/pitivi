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

#include "pitivi.h"
#include "pitivi-timelinecellrenderer.h"

static GtkWidgetClass *parent_class = NULL;
static GdkPixmap *pixmap = NULL;

enum
  {
    TARGET_STRING,
    TARGET_URL
  };

static GtkTargetEntry TargetEntries[] =
  {
    { "STRING",	       0, TARGET_STRING },
    { "text/plain",    0, TARGET_STRING },
    { "text/uri-list", 0, TARGET_URL },
  };

static gint	iNbTargetEntries = sizeof(TargetEntries)/sizeof(TargetEntries[0]);

enum {
  PITIVI_TML_LAYER_AUDIO,
  PITIVI_TML_TO_MODIFY,
};

enum {
  PITIVI_TML_LAYER_PROPERTY = 1,
  PITIVI_TML_TYPE_LAYER_PROPERTY,
  PITIVI_TML_HEIGHT_PROPERTY,
  PITIVI_TML_WIDTH_PROPERTY,
};

struct _PitiviTimelineCellRendererPrivate
{
  /* instance private members */
 
  GList		medias;
  gboolean	dispose_has_run;
  gboolean	selected;
  guint		cell_type;
  gint		width;
  gint		height;
  
};

/*
 * forward definitions
 */


/*
 * Insert "added-value" functions here
 */

GtkWidget *
pitivi_timelinecellrenderer_new (void)
{
  PitiviTimelineCellRenderer	*timelinecellrenderer;

  timelinecellrenderer = (PitiviTimelineCellRenderer *) g_object_new (PITIVI_TIMELINECELLRENDERER_TYPE, NULL);
  g_assert(timelinecellrenderer != NULL);
  return GTK_WIDGET ( timelinecellrenderer );
}

static GObject *
pitivi_timelinecellrenderer_constructor (GType type,
			     guint n_construct_properties,
			     GObjectConstructParam * construct_properties)
{
  GObject *obj;
  {
    /* Invoke parent constructor. */
    PitiviTimelineCellRendererClass *klass;
    GObjectClass *parent_class;
    klass = PITIVI_TIMELINECELLRENDERER_CLASS (g_type_class_peek (PITIVI_TIMELINECELLRENDERER_TYPE));
    parent_class = G_OBJECT_CLASS (g_type_class_peek_parent (klass));
    obj = parent_class->constructor (type, n_construct_properties,
				     construct_properties);
  }

  /* do stuff. */

  return obj;

}

static void
pitivi_timelinewindow_drag_data_received (GtkWidget *widget, GdkDragContext *dc, gint x, gint y, GtkSelectionData *selection_data, guint info, guint time, gpointer data)
{
  g_printf ("---------------data received-------------- \n");
  gtk_drag_finish(dc, FALSE, FALSE, time);
}

static void
pitivi_timelinecellrenderer_instance_init (GTypeInstance * instance, gpointer g_class)
{
  PitiviTimelineCellRenderer *self = (PitiviTimelineCellRenderer *) instance;

  self->private = g_new0(PitiviTimelineCellRendererPrivate, 1);
  
  /* initialize all public and private members to reasonable default values. */ 
  
  self->private->dispose_has_run = FALSE;
  
  /* If you need specific consruction properties to complete initialization, 
   * delay initialization completion until the property is set. 
   */
  
  self->private->width  = FIXED_WIDTH;
  self->private->height = FIXED_HEIGHT;
  self->private->selected = FALSE;
  
  gtk_drag_dest_set ( GTK_WIDGET (self), GTK_DEST_DEFAULT_ALL, TargetEntries, iNbTargetEntries, GDK_ACTION_COPY);
  gtk_signal_connect (GTK_OBJECT (self), "drag_data_received"\
		      , GTK_SIGNAL_FUNC ( pitivi_timelinewindow_drag_data_received )\
		      , NULL);
  
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

  /* 
   * In dispose, you are supposed to free all types referenced from this 
   * object which might themselves hold a reference to self. Generally, 
   * the most simple solution is to unref all members on which you own a 
   * reference. 
   */

}

static void
pitivi_timelinecellrenderer_finalize (GObject *object)
{
  PitiviTimelineCellRenderer	*self = PITIVI_TIMELINECELLRENDERER(object);

  /* 
   * Here, complete object destruction. 
   * You might not need to do much... 
   */

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
    case PITIVI_TML_LAYER_PROPERTY:
      break;
    case PITIVI_TML_TYPE_LAYER_PROPERTY:
      self->private->cell_type = g_value_get_int (value);
      break;
    case PITIVI_TML_HEIGHT_PROPERTY:
      break;
    case PITIVI_TML_WIDTH_PROPERTY:
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
    case PITIVI_TML_LAYER_PROPERTY:
      break;
    case PITIVI_TML_TYPE_LAYER_PROPERTY:
      break;
    case PITIVI_TML_HEIGHT_PROPERTY:
      break;
    case PITIVI_TML_WIDTH_PROPERTY:
      break;
    default:
      g_assert (FALSE);
      break;
    }
}

static void
pitivi_timelinecellrenderer_realize (GtkWidget *widget)
{
  PitiviTimelineCellRenderer *cell;
  GdkWindowAttr attributes;
  gint attributes_mask;

  g_return_if_fail (widget != NULL);
  g_return_if_fail (PITIVI_IS_TIMELINECELLRENDERER (widget));

  GTK_WIDGET_SET_FLAGS (widget, GTK_REALIZED);
  cell = PITIVI_TIMELINECELLRENDERER (widget);

  attributes.x = widget->allocation.x;
  attributes.y = widget->allocation.y;
  attributes.width = widget->allocation.width;
  attributes.height = widget->allocation.height;
  attributes.wclass = GDK_INPUT_OUTPUT;
  attributes.window_type = GDK_WINDOW_CHILD;
  attributes.event_mask = gtk_widget_get_events (widget) | 
    GDK_EXPOSURE_MASK | GDK_BUTTON_PRESS_MASK | 
    GDK_BUTTON_RELEASE_MASK | GDK_POINTER_MOTION_MASK |
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
pitivi_timelinecellrenderer_size_request (GtkWidget      *widget,
					  GtkRequisition *requisition)
{
  requisition->width = FIXED_WIDTH;
  requisition->height = FIXED_HEIGHT;
}


static void
pitivi_timelinecellrenderer_size_allocate (GtkWidget     *widget,
					   GtkAllocation *allocation)
{
   PitiviTimelineCellRenderer *cell;

  g_return_if_fail (widget != NULL);
  g_return_if_fail (PITIVI_IS_TIMELINECELLRENDERER (widget));
  g_return_if_fail (allocation != NULL);

  widget->allocation = *allocation;
  cell = PITIVI_TIMELINECELLRENDERER (widget);

  if (GTK_WIDGET_REALIZED (widget))
    {
      gdk_window_move_resize (widget->window,
			      allocation->x, allocation->y,
			      allocation->width, allocation->height);

    }
}

static void draw_selection (GtkWidget *widget, int width, char dash[])
{
  GdkGC *style = gdk_gc_new ( widget->window );
  gdk_gc_set_dashes ( style, 0, (gint8*)dash, sizeof (dash) / 2); 
  gdk_gc_set_line_attributes ( style, width, GDK_LINE_ON_OFF_DASH, GDK_CAP_BUTT, GDK_JOIN_MITER);
  gdk_draw_rectangle ( widget->window, style, FALSE, 0, 0, widget->allocation.width, widget->allocation.height);
}

static void draw_media (GtkWidget *widget, int start, int end)
{
  GdkGC *style = gdk_gc_new ( widget->window );
  gdk_gc_set_line_attributes ( style, 1, GDK_LINE_ON_OFF_DASH, GDK_CAP_BUTT, GDK_JOIN_MITER);
  gdk_draw_rectangle ( widget->window, style, TRUE, start, 0, end, widget->allocation.height);
}

static void draw_media_area (GtkWidget *widget, GdkRectangle area)
{
  GdkGC *style = gdk_gc_new ( widget->window );
  gdk_gc_set_line_attributes ( style, 1, GDK_LINE_ON_OFF_DASH, GDK_CAP_BUTT, GDK_JOIN_MITER);
  gdk_draw_rectangle ( widget->window, style, TRUE, area.x, area.y, area.width, area.height);
}

static gint
pitivi_timelinecellrenderer_expose (GtkWidget      *widget,
				    GdkEventExpose *event)
{
  char				dash [2] = {5, 4};
  PitiviTimelineCellRenderer	*cell = PITIVI_TIMELINECELLRENDERER (widget);
  gint				width, height;
  gint				x_offset, y_offset;
  gdouble			colors[3];
  GtkStateType			state;
  GtkShadowType			shadow;
  
  
  if (GTK_WIDGET_HAS_FOCUS (widget))
    state = GTK_STATE_ACTIVE;
  else
    state = GTK_STATE_NORMAL;
    
  shadow = GTK_SHADOW_NONE;
  
  gdk_draw_rectangle (widget->window,
		      widget->style->dark_gc[GTK_STATE_NORMAL],
		      TRUE, 0, 0,
		      widget->allocation.width, height);
  
  gtk_draw_hline (widget->style, (GdkWindow *)widget->window, \
		  state,  0, widget->allocation.width, FIXED_HEIGHT/2);    
  
  if ( cell->private->selected == TRUE )
    {
      draw_selection (widget, 2, dash);
      draw_media ( widget, 20, 600);
    }
  return FALSE;
}

static gint
pitivi_timelinecellrenderer_configure_event (GtkWidget *widget, GdkEventConfigure *event)
{
  if (pixmap)
    gdk_pixmap_unref(pixmap);
  
  pixmap = gdk_pixmap_new (widget->window,
			   widget->allocation.width,
			   widget->allocation.height,
			   -1);
  
}

static gint
pitivi_timelinecellrenderer_button_release_event (GtkWidget      *widget,
						  GdkEventButton *event)
{
  return FALSE;
}

static gint
pitivi_timelinecellrenderer_button_press_event (GtkWidget      *widget,
						GdkEventButton *event)
{
  char dash [2] = {5, 4};
  PitiviTimelineCellRenderer *cell;
  GdkEventExpose ev;
  gboolean retval;
  
  cell = PITIVI_TIMELINECELLRENDERER (widget);
  if ( cell->private->selected  == FALSE)
    {
      cell->private->selected = TRUE;
      draw_selection ( widget , 2, dash );
      draw_media ( widget, 20, 600);
    }
  else
    {
      cell->private->selected = FALSE;
      gtk_signal_emit_by_name (GTK_OBJECT (widget), "expose_event", &ev, &retval);
    }
  return FALSE;
}

static gint
pitivi_timelinecellrenderer_motion_notify_event (GtkWidget      *widget,
						 GdkEventMotion *event)
{
  PitiviTimelineCellRenderer *cell;
  GdkModifierType mods;
  gint x, y, mask;
  
  g_printf ("motion notify event \n");
  g_return_val_if_fail (widget != NULL, FALSE);
  g_return_val_if_fail (event != NULL, FALSE);
  cell = PITIVI_TIMELINECELLRENDERER (widget);
  
  x = event->x;
  y = event->y;
  if (event->is_hint || (event->window != widget->window))
    gdk_window_get_pointer (widget->window, &x, &y, &mods);
  
  return FALSE;
}

static void
pitivi_timelinecellrenderer_class_init (gpointer g_class, gpointer g_class_data)
{
  GObjectClass *gobject_class = G_OBJECT_CLASS (g_class);
  GtkWidgetClass *widget_class = GTK_WIDGET_CLASS (g_class);
  
  //parent_class = g_type_class_peek_parent (klass);
  
  //gobject_class->destroy = pitivi_timelinecellrenderer_destroy;
  gobject_class->constructor = pitivi_timelinecellrenderer_constructor;
  gobject_class->dispose = pitivi_timelinecellrenderer_dispose;
  gobject_class->finalize = pitivi_timelinecellrenderer_finalize;
  gobject_class->set_property = pitivi_timelinecellrenderer_set_property;
  gobject_class->get_property = pitivi_timelinecellrenderer_get_property;
  
  widget_class->realize = pitivi_timelinecellrenderer_realize;
  widget_class->expose_event = pitivi_timelinecellrenderer_expose;
  widget_class->size_request = pitivi_timelinecellrenderer_size_request;
  widget_class->size_allocate = pitivi_timelinecellrenderer_size_allocate;
  widget_class->configure_event = pitivi_timelinecellrenderer_configure_event;
  widget_class->button_press_event = pitivi_timelinecellrenderer_button_press_event;
  widget_class->button_release_event = pitivi_timelinecellrenderer_button_release_event;
  //widget_class->motion_notify_event = pitivi_timelinecellrenderer_motion_notify_event;
  
  /* Install the properties in the class here ! */
  
  g_object_class_install_property (G_OBJECT_CLASS (gobject_class),  PITIVI_TML_HEIGHT_PROPERTY,
				   g_param_spec_int("height","height","height",
						    G_MININT,G_MAXINT,0,G_PARAM_READWRITE));
  
  g_object_class_install_property (G_OBJECT_CLASS (gobject_class), PITIVI_TML_WIDTH_PROPERTY,
				   g_param_spec_int("width","width","width",
						    G_MININT,G_MAXINT,0,G_PARAM_READWRITE));
  
  g_object_class_install_property (G_OBJECT_CLASS (gobject_class), PITIVI_TML_TYPE_LAYER_PROPERTY,
				   g_param_spec_int ("type","type","type",
						     G_MININT, G_MAXINT, 0,G_PARAM_READWRITE));
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
      type = g_type_register_static (GTK_TYPE_WIDGET,
				     "PitiviTimelineCellRendererType", &info, 0);
    }

  return type;
}
