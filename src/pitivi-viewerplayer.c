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
#include "pitivi-viewerplayer.h"

enum
  {
    PITIVI_VPLAY_PIXBUFLOGO_PROPERTY = 1,
    PITIVI_VPLAY_PIXBUFFILE_PROPERTY
  };


struct _PitiviViewerPlayerPrivate
{
  /* instance private members */
  gboolean	dispose_has_run;
  
  GdkWindow *event_window;
  GdkWindow *video_window;

  const gchar *logo_file;
  GdkPixbuf   *logo_pixbuf;
  
  guint video_window_width;
  guint video_window_height;
  
  guint source_width;
  guint source_height;

  gint width_mini;
  gint height_mini;
  
  gboolean auto_resize;
  gboolean logo_focused;
  gboolean cursor_visible;
};

/*
 * forward definitions
 */

static GtkWidgetClass *parent_class = NULL;

/*
 * Insert "added-value" functions here
 */

GtkWidget *
pitivi_viewerplayer_new(void)
{
  PitiviViewerPlayer	*viewerplayer;

  viewerplayer = g_object_new(PITIVI_VIEWERPLAYER_TYPE, NULL);
  g_assert(viewerplayer != NULL);
  return GTK_WIDGET ( viewerplayer );
}

static GObject *
pitivi_viewerplayer_constructor (GType type,
			     guint n_construct_properties,
			     GObjectConstructParam * construct_properties)
{
  GObject *obj;
  {
    /* Invoke parent constructor. */
    PitiviViewerPlayerClass *klass;
    GObjectClass *parent_class;
    klass = PITIVI_VIEWERPLAYER_CLASS (g_type_class_peek (PITIVI_VIEWERPLAYER_TYPE));
    parent_class = G_OBJECT_CLASS (g_type_class_peek_parent (klass));
    obj = parent_class->constructor (type, n_construct_properties,
				     construct_properties);
  }

  /* do stuff. */

  return obj;
}

static void
pitivi_viewerplayer_instance_init (GTypeInstance * instance, gpointer g_class)
{
  PitiviViewerPlayer *self = (PitiviViewerPlayer *) instance;

  self->private = g_new0(PitiviViewerPlayerPrivate, 1);
  
  /* initialize all public and private members to reasonable default values. */ 
  
  self->private->dispose_has_run = FALSE;
  
  /* If you need specific consruction properties to complete initialization, 
   * delay initialization completion until the property is set. 
   */
  
  self->private->source_width = 0;
  self->private->source_height = 0;
  self->private->width_mini = 0;
  self->private->height_mini = 0;
  self->private->auto_resize = FALSE;
  self->private->logo_focused = FALSE;
  self->private->cursor_visible = FALSE;
  self->private->event_window = NULL;
  self->private->video_window = NULL;
  self->private->logo_pixbuf = NULL;
  
}

static void
pitivi_viewerplayer_dispose (GObject *object)
{
  PitiviViewerPlayer	*self = PITIVI_VIEWERPLAYER(object);

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
pitivi_viewerplayer_finalize (GObject *object)
{
  PitiviViewerPlayer	*self = PITIVI_VIEWERPLAYER(object);

  /* 
   * Here, complete object destruction. 
   * You might not need to do much... 
   */

  g_free (self->private);
}


void
pitivi_viewerplayer_set_logo (PitiviViewerPlayer *view, GdkPixbuf *logo_pixbuf)
{
  g_return_if_fail (view != NULL);
  g_return_if_fail ( PITIVI_IS_VIEWERPLAYER (view));
  
  if (logo_pixbuf == view->private->logo_pixbuf)
    return;
  
  if (view->private->logo_pixbuf)
    g_object_unref (view->private->logo_pixbuf);
  view->private->logo_pixbuf = logo_pixbuf;
}

static void
pitivi_viewerplayer_set_property (GObject * object,
			      guint property_id,
			      const GValue * value, GParamSpec * pspec)
{
  PitiviViewerPlayer *self = (PitiviViewerPlayer *) object;
  
  switch (property_id)
    {
    case PITIVI_VPLAY_PIXBUFFILE_PROPERTY:
      self->private->logo_file = g_value_get_string (value);
      break;
    case PITIVI_VPLAY_PIXBUFLOGO_PROPERTY:
      pitivi_viewerplayer_set_logo (self, g_value_get_object (value));
      break;
    default:
      g_assert (FALSE);
      break;
    }
}

static void
pitivi_viewerplayer_get_property (GObject * object,
			      guint property_id,
			      GValue * value, GParamSpec * pspec)
{
  PitiviViewerPlayer *self = (PitiviViewerPlayer *) object;

  switch (property_id)
    {
    case PITIVI_VPLAY_PIXBUFLOGO_PROPERTY:
      g_value_set_object (value, (GObject *) self->private->logo_pixbuf);
      break;
    case PITIVI_VPLAY_PIXBUFFILE_PROPERTY:
      g_value_set_object (value, (GObject *) self->private->logo_file);
      break;
    default:
      G_OBJECT_WARN_INVALID_PROPERTY_ID (object, property_id, pspec);
      g_assert (FALSE);
      break;
    }
}

static void
pitivi_viewerplayer_unrealize (GtkWidget * widget)
{
  PitiviViewerPlayer *self;

  g_return_if_fail (widget != NULL);
  g_return_if_fail ( PITIVI_IS_VIEWERPLAYER (widget));

  self =  PITIVI_VIEWERPLAYER (widget);

  GTK_WIDGET_UNSET_FLAGS (widget, GTK_REALIZED);

  /* Cacher les fenetres */

  if (GTK_WIDGET_MAPPED (widget))
    gtk_widget_unmap (widget);

  GTK_WIDGET_UNSET_FLAGS (widget, GTK_MAPPED);

  /* Destruction de la fenetre d'evenement */

  if (GDK_IS_WINDOW (self->private->event_window)) {
    gdk_window_set_user_data (self->private->event_window, NULL);
    gdk_window_destroy (self->private->event_window);
    self->private->event_window = NULL;
  }

  if (GDK_IS_WINDOW (self->private->video_window)) {
    gdk_window_set_user_data (self->private->video_window, NULL);
    gdk_window_destroy (self->private->video_window);
    self->private->video_window = NULL;
  }

  if (GTK_WIDGET_CLASS (parent_class)->unrealize)
    GTK_WIDGET_CLASS (parent_class)->unrealize (widget);
  
}

static void
pitivi_viewerplayer_realize (GtkWidget * widget)
{
  PitiviViewerPlayer *self = PITIVI_VIEWERPLAYER (widget);
  GdkWindowAttr attributes;
  gint attributes_mask;
  
  GTK_WIDGET_SET_FLAGS (widget, GTK_REALIZED);
  
  /* Creating our widget's window */

  attributes.window_type = GDK_WINDOW_CHILD;
  attributes.x = widget->allocation.x;
  attributes.y = widget->allocation.y;
  attributes.width = widget->allocation.width;
  attributes.height = widget->allocation.height;
  attributes.wclass = GDK_INPUT_OUTPUT;
  attributes.visual = gtk_widget_get_visual (widget);
  attributes.colormap = gtk_widget_get_colormap (widget);
  attributes.event_mask = gtk_widget_get_events (widget);
  attributes.event_mask |= GDK_EXPOSURE_MASK;

  attributes_mask = GDK_WA_X | GDK_WA_Y | GDK_WA_VISUAL | GDK_WA_COLORMAP;
  
  widget->window = gdk_window_new (gtk_widget_get_parent_window (widget),
				   &attributes, attributes_mask);
  
  gdk_window_set_user_data (widget->window, widget);
  
  /* Creation de la fenetre video */

  attributes.window_type = GDK_WINDOW_CHILD;
  attributes.x = 0;
  attributes.y = 0;
  attributes.width = widget->allocation.width;
  attributes.height = widget->allocation.height;
  attributes.wclass = GDK_INPUT_OUTPUT;
  attributes.event_mask = GDK_EXPOSURE_MASK;

  attributes_mask = GDK_WA_X | GDK_WA_Y;

  self->private->video_window = gdk_window_new (widget->window,
					     &attributes, attributes_mask);

  gdk_window_set_user_data (self->private->video_window, widget);

  gdk_window_show (self->private->video_window);

  /* Creation de la fenetre d'evenement */
  
  attributes.window_type = GDK_WINDOW_CHILD;
  attributes.x = 0;
  attributes.y = 0;
  attributes.width = widget->allocation.width;
  attributes.height = widget->allocation.height;
  attributes.wclass = GDK_INPUT_ONLY;
  attributes.event_mask = GDK_ALL_EVENTS_MASK;

  attributes_mask = GDK_WA_X | GDK_WA_Y;

  self->private->event_window = gdk_window_new (widget->window,
					     &attributes, attributes_mask);

  gdk_window_set_user_data (self->private->event_window, widget);

  gdk_window_show (self->private->event_window);

  widget->style = gtk_style_attach (widget->style, widget->window);
  
  gtk_style_set_background (widget->style, widget->window, GTK_STATE_NORMAL);
}

static void
pitivi_viewerplayer_size_request (GtkWidget * widget, GtkRequisition * requisition)
{
  PitiviViewerPlayer *self = PITIVI_VIEWERPLAYER (widget);
  
  requisition->width  = self->private->width_mini;
  requisition->height = self->private->height_mini;
}

static gint
pitivi_viewerplayer_expose (GtkWidget * widget, GdkEventExpose * event)
{
  PitiviViewerPlayer *self;

  g_return_val_if_fail (widget != NULL, FALSE);
  g_return_val_if_fail ( PITIVI_IS_VIEWERPLAYER (widget), FALSE);
  g_return_val_if_fail (event != NULL, FALSE);

  self =  PITIVI_VIEWERPLAYER (widget);
  
  if (GTK_WIDGET_VISIBLE (widget) && GTK_WIDGET_MAPPED (widget)) {
    if ((self->private->logo_pixbuf)) { //logo focus
      GdkPixbuf *frame;
      guchar *pixels;
      int rowstride;
      gint width, height, alloc_width, alloc_height, logo_x, logo_y;
      gfloat width_ratio, height_ratio;

      frame = gdk_pixbuf_new (GDK_COLORSPACE_RGB,
			      FALSE, 8, widget->allocation.width, widget->allocation.height);

      width = gdk_pixbuf_get_width (self->private->logo_pixbuf);
      height = gdk_pixbuf_get_height (self->private->logo_pixbuf);
      
      alloc_width = widget->allocation.width;
      alloc_height = widget->allocation.height;
    
      /* Checking Si taille alloué est plus petite que le logo */
    
      if ((alloc_width < width) || (alloc_height < height)) {
	width_ratio = (gfloat) alloc_width / (gfloat) width;
	height_ratio = (gfloat) alloc_height / (gfloat) height;
	width_ratio = MIN (width_ratio, height_ratio);
	height_ratio = width_ratio;
      } else
	width_ratio = height_ratio = 1.0;
      
      logo_x = (alloc_width / 2) - (width * width_ratio / 2);
      logo_y = (alloc_height / 2) - (height * height_ratio / 2);
      
      /* Taille dispo */
      
      gdk_pixbuf_composite (self->private->logo_pixbuf,
			    frame,
			    0, 0,
			    alloc_width, alloc_height,
			    logo_x, logo_y, width_ratio, height_ratio, GDK_INTERP_BILINEAR, 255);
      
      /* Dessin de la frame */
     
      rowstride = gdk_pixbuf_get_rowstride (frame);

      pixels = gdk_pixbuf_get_pixels (frame) +
	rowstride * event->area.y + event->area.x * 3;
      
      gdk_draw_rgb_image_dithalign (widget->window,
				    widget->style->black_gc,
				    event->area.x, event->area.y,
				    event->area.width, event->area.height,
				    GDK_RGB_DITHER_NORMAL, pixels,
				    rowstride, event->area.x, event->area.y);
      g_object_unref (frame);
    } else {
      gdk_draw_rectangle (widget->window, widget->style->black_gc, TRUE,
			  event->area.x, event->area.y, event->area.width, event->area.height);
    }

  }
  return FALSE;
}

static void
pitivi_viewerplayer_allocate (GtkWidget * widget, GtkAllocation * allocation)
{
  PitiviViewerPlayer *self;
  gint width, height = 1;

  widget->allocation = *allocation;
  
  self = PITIVI_VIEWERPLAYER (widget);

  if (GTK_WIDGET_REALIZED (widget)) {
    gdk_window_move_resize (widget->window,
			    allocation->x, allocation->y, 
			    allocation->width, 
			    allocation->height);
    
    if (GDK_IS_WINDOW (self->private->event_window))
      gdk_window_move_resize (self->private->event_window,
			      0, 
			      0, 
			      allocation->width, 
			      allocation->height);
    
    self->private->video_window_width = width;
    self->private->video_window_height = height;
    
    if (GDK_IS_WINDOW (self->private->video_window)) {  
      gdk_window_move_resize (self->private->video_window,
			      allocation->width, allocation->height, \
			      allocation->width, allocation->height);
    }
  }
}

static void
pitivi_viewerplayer_class_init (gpointer g_class, gpointer g_class_data)
{
  GtkWidgetClass *widget_class;
  GObjectClass *gobject_class = G_OBJECT_CLASS (g_class);
  
  PitiviViewerPlayerClass *klass = PITIVI_VIEWERPLAYER_CLASS (g_class);
  widget_class = (GtkWidgetClass *) klass;
  
  parent_class = gtk_type_class (gtk_widget_get_type ());
  
  gobject_class->constructor = pitivi_viewerplayer_constructor;
  gobject_class->dispose = pitivi_viewerplayer_dispose;
  gobject_class->finalize = pitivi_viewerplayer_finalize;

  gobject_class->set_property = pitivi_viewerplayer_set_property;
  gobject_class->get_property = pitivi_viewerplayer_get_property;

  g_object_class_install_property (gobject_class,
				   PITIVI_VPLAY_PIXBUFLOGO_PROPERTY,
				   g_param_spec_object ("logo",
							"Logo",
							"Picture that should appear as a logo when no video",
							gdk_pixbuf_get_type (), G_PARAM_READWRITE));

  widget_class->realize = pitivi_viewerplayer_realize;
  widget_class->unrealize = pitivi_viewerplayer_unrealize;
  widget_class->expose_event = pitivi_viewerplayer_expose;
  widget_class->size_request = pitivi_viewerplayer_size_request;
  widget_class->size_allocate = pitivi_viewerplayer_allocate;
  
}

void
pitivi_viewerplayer_choose_mode_start (PitiviViewerPlayer *self)
{
  if (GDK_IS_WINDOW (self->private->video_window))
    gdk_window_hide (self->private->video_window);
}

gboolean
pitivi_viewerplayer_set_minimum_size (PitiviViewerPlayer *self, gint width, gint height)
{
  g_return_val_if_fail (self != NULL, FALSE);
  g_return_val_if_fail (PITIVI_VIEWERPLAYER (self), FALSE);

  self->private->width_mini = width;
  self->private->height_mini = height;
  gtk_widget_queue_resize (GTK_WIDGET (self));

  return TRUE;
}

GType
pitivi_viewerplayer_get_type (void)
{
  static GType type = 0;
 
  if (type == 0)
    {
      static const GTypeInfo info = {
	sizeof (PitiviViewerPlayerClass),
	NULL,			/* base_init */
	NULL,			/* base_finalize */
	pitivi_viewerplayer_class_init,	/* class_init */
	NULL,			/* class_finalize */
	NULL,			/* class_data */
	sizeof (PitiviViewerPlayer),
	0,			/* n_preallocs */
	pitivi_viewerplayer_instance_init	/* instance_init */
      };
      type = g_type_register_static (GTK_TYPE_WIDGET,
				     "PitiviViewerPlayerType", &info, (GTypeFlags) 0);
    }

  return type;
}
