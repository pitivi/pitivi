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

static GtkCellRendererClass *parent_class = NULL;

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
  gboolean	dispose_has_run;
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

GtkCellRenderer *
pitivi_timelinecellrenderer_new(void)
{
  PitiviTimelineCellRenderer	*timelinecellrenderer;

  timelinecellrenderer = (PitiviTimelineCellRenderer *) g_object_new(PITIVI_TIMELINECELLRENDERER_TYPE, NULL);
  g_assert(timelinecellrenderer != NULL);
  return ((GtkCellRenderer *) timelinecellrenderer);
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
pitivi_timelinecellrenderer_get_size (GtkCellRenderer *cell,
				      GtkWidget       *widget,
				      GdkRectangle    *cell_area,
				      gint            *x_offset,
				      gint            *y_offset,
				      gint            *width,
				      gint            *height)
{
  gint calc_width;
  gint calc_height;

  PitiviTimelineCellRenderer	*treecell = PITIVI_TIMELINECELLRENDERER (cell);
  
  if (treecell->private->cell_type == PITIVI_TML_LAYER_AUDIO)
    {
      calc_width  = (gint) cell->xpad * 2 + FIXED_WIDTH;
      calc_height = (gint) cell->ypad * 2 + FIXED_HEIGHT;
    }
  else
    {
      calc_width  = (gint) cell->xpad * 2 + FIXED_WIDTH / 2;
      calc_height = (gint) cell->ypad * 2 + FIXED_HEIGHT / 2;
    }

  if (width)
    *width = calc_width;

  if (height)
    *height = calc_height;

  if (cell_area)
    {
      if (x_offset)
	{
	  *x_offset = cell->xalign * (cell_area->width - calc_width);
	  *x_offset = MAX (*x_offset, 0);
	}
    
      if (y_offset)
	{
	  *y_offset = cell->yalign * (cell_area->height - calc_height);
	  *y_offset = MAX (*y_offset, 0);
	}
    }
}

static void
pitivi_timelinecellrenderer_render (GtkCellRenderer *cell,
				    GdkWindow       *window,
				    GtkWidget       *widget,
				    GdkRectangle    *background_area,
				    GdkRectangle    *cell_area,
				    GdkRectangle    *expose_area,
				    guint            flags)
     
{
  PitiviTimelineCellRenderer	*treecell = PITIVI_TIMELINECELLRENDERER (cell);
  gint				width, height;
  gint				x_offset, y_offset;
  gdouble			colors[3];
  GtkStateType			state;
  GtkShadowType			shadow;

  pitivi_timelinecellrenderer_get_size (cell, widget, cell_area,
					&x_offset, &y_offset,
					&width, &height);
  
    if (GTK_WIDGET_HAS_FOCUS (widget))
      state = GTK_STATE_ACTIVE;
    else
      state = GTK_STATE_NORMAL;
    
    if (treecell->private->cell_type == PITIVI_TML_LAYER_AUDIO)
      shadow = GTK_SHADOW_ETCHED_OUT;
    else
      shadow = GTK_SHADOW_NONE;
    
    gtk_paint_box (widget->style, window,
		       state, shadow,
		       NULL, widget, "layer",
		       cell_area->x,
		       cell_area->y,
		       widget->allocation.width,
		   height);
    
    if (treecell->private->cell_type == PITIVI_TML_LAYER_AUDIO)
      gtk_draw_hline (widget->style, (GdkWindow *)window, state,  cell_area->x, widget->allocation.width, cell_area->y + height/2);
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
  
  GTK_CELL_RENDERER(self)->mode = GTK_CELL_RENDERER_MODE_INERT;
  GTK_CELL_RENDERER(self)->xpad = 0;
  GTK_CELL_RENDERER(self)->ypad = 0;
  self->private->width  = FIXED_WIDTH;
  self->private->height = FIXED_HEIGHT;
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
pitivi_timelinecellrenderer_class_init (gpointer g_class, gpointer g_class_data)
{
  GObjectClass *gobject_class = G_OBJECT_CLASS (g_class);
  PitiviTimelineCellRendererClass *klass = PITIVI_TIMELINECELLRENDERER_CLASS (g_class);
  GtkCellRendererClass *cell_class   = GTK_CELL_RENDERER_CLASS(klass);
  
  parent_class = g_type_class_peek_parent (klass);
  gobject_class->constructor = pitivi_timelinecellrenderer_constructor;
  gobject_class->dispose = pitivi_timelinecellrenderer_dispose;
  gobject_class->finalize = pitivi_timelinecellrenderer_finalize;
  gobject_class->set_property = pitivi_timelinecellrenderer_set_property;
  gobject_class->get_property = pitivi_timelinecellrenderer_get_property;
  
  /* Install the properties in the class here ! */
  g_object_class_install_property
    (gobject_class,
     PITIVI_TML_LAYER_PROPERTY,
     g_param_spec_string ("layer",
			  "Layer",
			  "Layer",
			  NULL,
			  (G_PARAM_READABLE|G_PARAM_WRITABLE)));
  
  g_object_class_install_property (G_OBJECT_CLASS(klass),  PITIVI_TML_HEIGHT_PROPERTY,
				   g_param_spec_int("height","height","height",
						    G_MININT,G_MAXINT,0,G_PARAM_READWRITE));
  
  g_object_class_install_property (G_OBJECT_CLASS(klass), PITIVI_TML_WIDTH_PROPERTY,
				   g_param_spec_int("width","width","width",
						    G_MININT,G_MAXINT,0,G_PARAM_READWRITE));
  
  g_object_class_install_property (G_OBJECT_CLASS(klass), PITIVI_TML_TYPE_LAYER_PROPERTY,
				   g_param_spec_int ("type","type","type",
						     G_MININT, G_MAXINT, 0,G_PARAM_READWRITE));
  
  cell_class->get_size = pitivi_timelinecellrenderer_get_size;
  cell_class->render   = pitivi_timelinecellrenderer_render;
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
      type = g_type_register_static (GTK_TYPE_CELL_RENDERER,
				     "PitiviTimelineCellRendererType", &info, 0);
    }

  return type;
}
