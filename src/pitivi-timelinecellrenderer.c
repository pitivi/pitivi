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
#include "pitivi-timelinewindow.h"
#include "pitivi-timelinecellrenderer.h"
#include "pitivi-timelinemedia.h"
#include "pitivi-dragdrop.h"

// Parent Class
static GtkLayoutClass	    *parent_class = NULL;

// Caching Operation  
static GdkPixmap	    *pixmap = NULL;

// Testing Widget
static PitiviTimelineMedia  *current_media;

// default Dashes
static char gdefault_dash [2] = {5, 4};

typedef enum
{
  PITIVI_VIDEO_TRACK,
  PITIVI_AUDIO_TRACK,
} PitiviLayerType;

typedef enum {
  PITIVI_TML_LAYER_PROPERTY = 1,
  PITIVI_TML_TYPE_LAYER_PROPERTY,
  PITIVI_TML_HEIGHT_PROPERTY,
  PITIVI_TML_WIDTH_PROPERTY,
} PitiviLayerProperty;

struct _PitiviTimelineCellRendererPrivate
{
  /* instance private members */
  PitiviTimelineWindow *timewin;
  GtkSelectionData     *current_selection;
  gboolean	       dispose_has_run;
  gboolean	       selected;
  gint		       width;
  gint		       height;
};

/*
 * forward definitions
 */

static GtkTargetEntry TargetEntries[] =
  {
    { "pitivi/sourcefile", GTK_TARGET_SAME_APP, DND_TARGET_SOURCEFILEWIN },
    { "pitivi/sourceeffect", GTK_TARGET_SAME_APP, DND_TARGET_EFFECTSWIN },
    { "STRING", GTK_TARGET_SAME_APP, DND_TARGET_STRING },
    { "text/plain", GTK_TARGET_SAME_APP, DND_TARGET_URI },
  };

static gint iNbTargetEntries = G_N_ELEMENTS (TargetEntries);


/*
 * Insert "added-value" functions here
 */

GtkWidget *
pitivi_timelinecellrenderer_new (PitiviTimelineWindow *timewin)
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


void 
draw_selection (GtkWidget *widget, int width, char dash[])
{
  GdkGC *style = gdk_gc_new ( widget->window );
  GdkWindow *window;
  
  if (width == 0)
    width = DEFAULT_WIDTH_DASHES;
  if (dash == NULL)
    gdk_gc_set_dashes ( style, 0, (gint8*)gdefault_dash, sizeof (gdefault_dash) / 2);
  else
    gdk_gc_set_dashes ( style, 0, (gint8*)dash, sizeof (dash) / 2); 
  gdk_gc_set_line_attributes ( style, width, GDK_LINE_ON_OFF_DASH, GDK_CAP_BUTT, GDK_JOIN_MITER);
  if (GTK_IS_LAYOUT (widget))
    window = GDK_WINDOW (GTK_LAYOUT (widget)->bin_window);
  else
    window = GDK_WINDOW (widget->window);
  gdk_draw_rectangle ( window, style, 
		       FALSE, 
		       widget->allocation.x, 0, 
		       widget->allocation.width, widget->allocation.height);
}

void 
draw_slide (GtkWidget *widget, int start, int end)
{
  GdkGC *style = gdk_gc_new ( widget->window );
  gdk_gc_set_line_attributes ( style, 1, GDK_LINE_ON_OFF_DASH, GDK_CAP_BUTT, GDK_JOIN_MITER);
  GdkWindow *window;
  
  if (GTK_IS_LAYOUT (widget))
    window = GDK_WINDOW (GTK_LAYOUT (widget)->bin_window);
  else
    window = GDK_WINDOW (widget->window);
  gdk_draw_rectangle (GDK_WINDOW (window), widget->style->black_gc, TRUE, start, 0, end, widget->allocation.height);
}

static gint
pitivi_timelinecellrenderer_expose (GtkWidget      *widget,
				    GdkEventExpose *event)
{
  PitiviTimelineCellRenderer	*cell = PITIVI_TIMELINECELLRENDERER (widget);
  GtkLayout *layout;
  
  g_return_val_if_fail (GTK_IS_LAYOUT (widget), FALSE);
  layout = GTK_LAYOUT (widget);
  gtk_paint_hline (widget->style,
		   layout->bin_window, 
		   GTK_STATE_NORMAL,
		   NULL, widget, "middle-line",
		   0, widget->allocation.width, widget->allocation.height/2);

  if (event->window != layout->bin_window)
    return FALSE;
  
  (* GTK_WIDGET_CLASS (parent_class)->expose_event) (widget, event);
  
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
  gtk_selection_data_set (selection_data, selection_data->target, 8, "move", strlen ("move"));
}


static void
pitivi_timelinemedia_drag_delete  (GtkWidget          *widget,
				   GdkDragContext     *context,
				   gpointer	      dragging)
{
  g_printf ("drag delete \n");
}

static gint
pitivi_timelinemedia_button_press (GtkWidget      *widget,
				   GdkEventButton *event)
{
  draw_selection (widget, 0, NULL);
  return FALSE;
}

static
int add_to_layout (GtkWidget *self, GtkWidget *widget, gint x, gint y)
{
  GtkRequisition req;
  PitiviTimelineCellRenderer *cell; 

  cell = PITIVI_TIMELINECELLRENDERER (self);
  gtk_widget_size_request (widget, &req);
  gtk_layout_put (GTK_LAYOUT (self), widget, x, 0);
  x += req.width;
  gtk_layout_set_size (GTK_LAYOUT (self), x, 0);

  if (cell->children != NULL)
    {
      g_list_free (cell->children);
      cell->children = NULL;
    }
  
  cell->children = gtk_container_get_children (GTK_CONTAINER (self));
  gtk_drag_source_set  (GTK_WIDGET (widget), 
			GDK_BUTTON1_MASK, 
			TargetEntries, 
			iNbTargetEntries, 
			GDK_ACTION_COPY);
  
  g_signal_connect (widget, "drag_data_get",	      
		    G_CALLBACK (pitivi_timelinemedia_drag_get), self);
  g_signal_connect (widget, "drag_data_delete",
		    G_CALLBACK (pitivi_timelinemedia_drag_delete), self);
  g_signal_connect (widget, "button_press_event",
		    G_CALLBACK (pitivi_timelinemedia_button_press), self);
  return TRUE;
}

static void
pitivi_timelinecellrenderer_drag_data_received (GObject *object,
						GdkDragContext *context,
						int x,
						int y,
						GtkSelectionData *selection,
						guint info,
						guint time,
						gpointer data)
{
  PitiviTimelineCellRenderer *self = PITIVI_TIMELINECELLRENDERER(object);
  
  if (!selection->data) {
    gtk_drag_finish (context, FALSE, FALSE, time);
    return;
  }
  
  self->private->current_selection = selection;
  switch (info) {
  case DND_TARGET_SOURCEFILEWIN:
    current_media = pitivi_timelinemedia_new ();
    gtk_widget_set_size_request (GTK_WIDGET (current_media),  60, 50);
    gtk_widget_show (GTK_WIDGET (current_media));
    add_to_layout ( GTK_WIDGET (self), GTK_WIDGET (current_media), x, y);
    gtk_drag_finish (context, TRUE, TRUE, time);
    break;
  case DND_TARGET_EFFECTSWIN:
    g_printf ("Window Effects dropping %s\n", selection->data);
    gtk_drag_finish (context, TRUE, TRUE, time);
    break;
  default:
    break;
  }
}

static void 
pitivi_timelinecellrenderer_drag_leave (GtkWidget	*widget,
					GdkDragContext	*context,
					guint		time)
{
  
}

static gboolean 
pitivi_timelinecellrenderer_drag_drop (GtkWidget *widget, 
				       GdkDragContext *dc, 
				       gint x, 
				       gint y, 
				       guint time, 
				       gpointer data)
{
}

static void
pitivi_timelinecellrenderer_drag_motion (GtkWidget          *widget,
					 GdkDragContext     *context,
					 gint                x,
					 gint                y,
					 guint               time)
{ 
  PitiviTimelineCellRenderer *self = (PitiviTimelineCellRenderer *) widget;
  
  if (self->motion_area->height == 0)
  {
      self->motion_area->width  = 60;
      self->motion_area->height = FIXED_HEIGHT;
      self->motion_area->x      = 60;
      self->motion_area->y      = 0;
  }

  // Expose on left
  gdk_window_clear_area_e (GTK_LAYOUT (widget)->bin_window,
			   x-self->motion_area->x,
			   self->motion_area->y,
			   self->motion_area->width,
			   self->motion_area->height);
  
  // Expose on right
  gdk_window_clear_area_e (GTK_LAYOUT (widget)->bin_window,
			   x+self->motion_area->x,
			   self->motion_area->y,
			   self->motion_area->width,
			   self->motion_area->height);
  
  draw_slide (widget, x, self->motion_area->width);
}


static void
pitivi_timelinecellrenderer_instance_init (GTypeInstance * instance, gpointer g_class)
{
  GdkColor color;
  GtkStyle *DefaultLayoutStyle;

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
  self->children = NULL;
  self->motion_area = g_new0 (GdkRectangle, 1);

  gtk_drag_dest_set  (GTK_WIDGET (self), GTK_DEST_DEFAULT_ALL, 
		      TargetEntries, 
		      iNbTargetEntries, 
		      GDK_ACTION_COPY);
  
  g_signal_connect (G_OBJECT (self), "drag_data_received",\
		      G_CALLBACK ( pitivi_timelinecellrenderer_drag_data_received ), NULL);
  g_signal_connect (G_OBJECT (self), "drag_motion",
		    G_CALLBACK ( pitivi_timelinecellrenderer_drag_motion ), NULL);
  g_signal_connect (G_OBJECT (self), "drag_leave",
		    G_CALLBACK ( pitivi_timelinecellrenderer_drag_leave ), NULL);
  g_signal_connect (G_OBJECT (self), "drag_drop",
		    G_CALLBACK ( pitivi_timelinecellrenderer_drag_drop ), NULL);
  
  // Set background Color
  
  DefaultLayoutStyle = gtk_style_copy (GTK_WIDGET(self)->style);
  color.red = 0xc490;
  color.blue = 0xc2ce;
  color.green = 0xcc40;
  DefaultLayoutStyle->bg[GTK_STATE_NORMAL] = color;
  gtk_widget_set_style (GTK_WIDGET (self), DefaultLayoutStyle);
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
      self->track_type = g_value_get_int (value);
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
  return FALSE;
}

static gint
pitivi_timelinecellrenderer_motion_notify_event (GtkWidget      *widget,
						 GdkEventMotion *event)
{
  PitiviTimelineCellRenderer *cell;
  GdkModifierType mods;
  gint x, y, mask;
  
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
  GtkContainerClass *container_class = (GtkContainerClass*) (g_class);
  
  parent_class = gtk_type_class (GTK_TYPE_LAYOUT);
    
  gobject_class->constructor = pitivi_timelinecellrenderer_constructor;
  gobject_class->dispose = pitivi_timelinecellrenderer_dispose;
  gobject_class->finalize = pitivi_timelinecellrenderer_finalize;
  gobject_class->set_property = pitivi_timelinecellrenderer_set_property;
  gobject_class->get_property = pitivi_timelinecellrenderer_get_property;

  /* Widget properties */
  
  widget_class->expose_event = pitivi_timelinecellrenderer_expose;
  widget_class->configure_event = pitivi_timelinecellrenderer_configure_event;
  widget_class->button_press_event = pitivi_timelinecellrenderer_button_press_event;
  widget_class->button_release_event = pitivi_timelinecellrenderer_button_release_event;
  
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
      type = g_type_register_static (GTK_TYPE_LAYOUT,
				     "PitiviTimelineCellRendererType", &info, 0);
    }
  return type;
}
