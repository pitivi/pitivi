/* 
 * PiTiVi
 * Copyright (C) <2004> Guillaume Casanova <casano_g@epita.fr>
 *
 * This software has been written in EPITECH <http://www.epitech.net>
 * EPITECH is a computer science school in Paris - FRANCE -
 * under the direction of Flavien Astraud and Jerome Landrieu.
 *
 * This program is free software; you can redistribute it and/or2
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

#include <gst/gst.h>
#include "pitivi.h"
#include "pitivi-ruler.h"
#include "pitivi-units.h"
#include "pitivi-drawing.h"
#include "pitivi-dragdrop.h"

#define RULER_HEIGHT          14
#define MINIMUM_INCR          5
#define MAXIMUM_SUBDIVIDE     5
#define MAXIMUM_SCALES        10

#define ROUND(x) ((int) ((x) + 0.5))


static void pitivi_ruler_class_init    (PitiviRulerClass *klass);
static void pitivi_ruler_init          (PitiviRuler      *hruler);
static gint pitivi_ruler_motion_notify (GtkWidget      *widget,
					GdkEventMotion *event);
static void pitivi_ruler_draw_ticks    (GtkRuler       *ruler);
static void pitivi_ruler_draw_pos      (GtkRuler       *ruler);


struct _PitiviRulerPrivate
{
  PitiviConvert	 unit;
  guint		 videorate;
  guint		 idx;
  GdkGC		 *gc_play;
};


enum {  
  PROP_UNIT = 1,
  PROP_VIDEORATE,
  PROP_LAST
};

/* Subdivisions */

static const GtkRulerMetric pitivi_ruler_metrics[] =
  {
    {"NanoSeconds", "ns",          1.0,   { 1, 2, 5, 10, 25, 50, 100, 250, 500, 1000 }, { 1, 5, 10, 50, 100 }},
    {"NanoSeconds 2x",  "ns2x",    2.0,   { 1, 2, 4, 8, 16, 32, 64, 128, 256, 512 }, { 1, 16, 32, 64, 128 }},
    {"NanoSeconds 4x",  "ns4x",    4.0,   { 1, 2, 4, 8, 16, 32, 64, 128, 256, 512 }, { 1, 8, 16, 32, 64 }},
    {"NanoSeconds 8x",  "ns8x",    8.0,   { 1, 2, 4, 8, 16, 32, 64, 128, 256, 512 }, { 1, 4, 8, 16, 32 }},
    {"NanoSeconds 16x", "ns16x",  16.0,   { 1, 2, 4, 8, 16, 32, 64, 128, 256, 512 }, { 1, 2, 4, 8, 16  }},
    /* If in the future we want represent Seconds with different subdivision compared to nanoseconds */
    {"Seconds",     "s",      1.0,   { 1, 2, 5, 10, 25, 50, 100, 250, 500, 1000 }, { 1, 5, 10, 50, 100 }},
    {"Seconds 2x",  "s2x",    2.0,   { 1, 2, 4, 8, 16, 32, 64, 128, 256, 512 }, { 1, 16, 32, 64, 128 }},
    {"Seconds 4x",  "s4x",    4.0,   { 1, 2, 4, 8, 16, 32, 64, 128, 256, 512 }, { 1, 8, 16, 32, 64 }},
    {"Seconds 8x",  "s8x",    8.0,   { 1, 2, 4, 8, 16, 32, 64, 128, 256, 512 }, { 1, 4, 8, 16, 32 }},
    {"Seconds 16x", "s16x",  16.0,   { 1, 2, 4, 8, 16, 32, 64, 128, 256, 512 }, { 1, 2, 4, 8, 16  }},
    /* If in the future we want represent Frames with different subdivision compared to seconds */
    {"Frames",      "Fm",     1.0,   { 1, 2, 5, 10, 25, 50, 100, 250, 500, 1000 }, { 1, 5, 10, 50, 100 }},
    {"Frames 2x",   "Fm2x",   2.0,   { 1, 2, 4, 8, 16, 32, 64, 128, 256, 512 }, { 1, 16, 32, 64, 128 }},
    {"Frames 4x",   "Fm4x",   4.0,   { 1, 2, 4, 8, 16, 32, 64, 128, 256, 512 }, { 1, 8, 16, 32, 64 }},
    {"Frames 8x",   "Fm8x",   8.0,   { 1, 2, 4, 8, 16, 32, 64, 128, 256, 512 }, { 1, 4, 8, 16, 32 }},
    {"Frames 16x",  "Fm16x", 16.0,   { 1, 2, 4, 8, 16, 32, 64, 128, 256, 512 }, { 1, 2, 4, 8, 16 }},
    /* ------------ */
  };

void
pitivi_ruler_set_metric (GtkRuler *ruler,
			 PitiviMetricType metric)
{
  g_return_if_fail (GTK_IS_RULER (ruler));

  ruler->metric = (GtkRulerMetric *) &pitivi_ruler_metrics[metric];

  if (GTK_WIDGET_DRAWABLE (ruler))
    gtk_widget_queue_draw (GTK_WIDGET (ruler));
}

void
pitivi_ruler_set_data_metric (GtkRuler *ruler,
			      GtkRulerMetric *metric)
{
  g_return_if_fail (GTK_IS_RULER (ruler));

  ruler->metric = metric;

  if (GTK_WIDGET_DRAWABLE (ruler))
    gtk_widget_queue_draw (GTK_WIDGET (ruler));
}

gint
pitivi_ruler_get_pixel_per_unit (PitiviRuler *pitivi_ruler)
{
  gint result;
  
  result = pitivi_ruler_metrics[pitivi_ruler->private->idx].pixels_per_unit;
  if ( pitivi_ruler->private->idx <= PITIVI_RFRAMES16x && pitivi_ruler->private->idx >= PITIVI_RFRAMES )
    result *= pitivi_ruler->private->videorate;
  return ( result );
}

void
pitivi_ruler_set_zoom_metric (GtkRuler *ruler, guint unit, guint zoom)
{
  int count = 0;
  int start = 0;
  int end = 0;
  
  PITIVI_RULER(ruler)->private->unit = unit;
  if ( unit == PITIVI_SECONDS )
    {
      start = PITIVI_RSECONDS;
      end  = PITIVI_RSECONDS16x;
    }
  else if ( unit == PITIVI_FRAMES )
    {
      start = PITIVI_RFRAMES;
      end  = PITIVI_RFRAMES16x;
    }
  else  if ( unit == PITIVI_NANOSECONDS )
    {
      start = PITIVI_RNANOSECONDS;
      end  = PITIVI_RNANOSECONDS16x;
    }
  for (count = start; count <= end; count++)
    {
      if ((int)pitivi_ruler_metrics[count].pixels_per_unit == (int)zoom)
	{
	  PITIVI_RULER(ruler)->private->idx = count;
	  pitivi_ruler_set_metric (ruler, (count));
	  break;
	}
    }
}


GType
pitivi_ruler_get_type (void)
{
  static GType hruler_type = 0;

  if (!hruler_type)
    {
      static const GTypeInfo hruler_info =
      {
	sizeof (PitiviRulerClass),
	NULL,		/* base_init */
	NULL,		/* base_finalize */
	(GClassInitFunc) pitivi_ruler_class_init,
	NULL,		/* class_finalize */
	NULL,		/* class_data */
	sizeof (PitiviRuler),
	0,		/* n_preallocs */
	(GInstanceInitFunc) pitivi_ruler_init,
      };

      hruler_type = g_type_register_static (GTK_TYPE_RULER, "PitiviRuler",
					    &hruler_info, 0);
    }

  return hruler_type;
}

static void
pitivi_ruler_set_property (GObject * object,
			   guint property_id,
			   const GValue * value, GParamSpec * pspec)
{
  PitiviRuler *self = (PitiviRuler *) object;
  switch (property_id)
    {
    case PROP_UNIT:
      self->private->unit = g_value_get_int (value); 
      break;
    case PROP_VIDEORATE:
      self->private->videorate = g_value_get_int (value); 
      break;
    default:
      g_assert (FALSE);
      break;
    }
}

static void
pitivi_ruler_get_property (GObject * object,
			   guint property_id,
			   GValue * value, GParamSpec * pspec)
{
/*   PitiviRuler *self = (PitiviRuler *) object; */
  switch (property_id)
    {
    case PROP_UNIT:
      break;
    default:
      g_assert (FALSE);
      break;
    }
}


static void
pitivi_ruler_moving (PitiviRuler *pitivi_ruler, gint *gpos)
{  
  GtkRuler *ruler = (GtkRuler *) pitivi_ruler;
  gint bs_width, bs_height, slide_width;
  gint i, height, x, y;
 
  gint pos = *gpos;
  height = GTK_WIDGET(pitivi_ruler)->allocation.height - GTK_WIDGET(pitivi_ruler)->style->ythickness * 2;
  bs_width = height / 2;
  bs_width |= 1;
  bs_height = bs_width / 2 + 1;
  y = (height + bs_height) / 2 + GTK_WIDGET(pitivi_ruler)->style->ythickness;
  slide_width = bs_height; 
  x = PITIVI_RULER (ruler)->timeline_x - slide_width;
  if (ruler->backing_store && ruler->non_gr_exp_gc)
    {
      gdk_draw_drawable (ruler->widget.window,
			 ruler->non_gr_exp_gc,
			 ruler->backing_store,
			 x, 0,
			 x, 0,
			 bs_width, height);
    }
  
  PITIVI_RULER (ruler)->timeline_x=pos*pitivi_ruler_get_pixel_per_unit (pitivi_ruler);
  x = PITIVI_RULER (ruler)->timeline_x - slide_width;
  if (GTK_WIDGET_IS_SENSITIVE(GTK_WIDGET(ruler)))
    {
      for (i = 0; i < bs_height; i++)
	{
	  gdk_draw_line (GTK_WIDGET(pitivi_ruler)->window, 
			 pitivi_ruler->private->gc_play,
			 x + i, y + i,
			 x + bs_width - 1 - i, y + i);
	  if (i)
	    gdk_draw_line (GTK_WIDGET(pitivi_ruler)->window,
			   pitivi_ruler->private->gc_play,
			   x + i + 2, 0,
			   x + i + 2, y);
	}
    }
  pitivi_ruler_draw_pos (GTK_RULER (pitivi_ruler));
}


static void
pitivi_ruler_class_init (PitiviRulerClass *klass)
{
  GObjectClass   *cellobj_class = G_OBJECT_CLASS (klass);
  GtkWidgetClass *widget_class;
  GtkRulerClass  *ruler_class;
  PitiviRulerClass *pitivi_class;

  widget_class = (GtkWidgetClass*) klass;
  ruler_class = (GtkRulerClass*) klass;
  pitivi_class = (PitiviRulerClass*) klass;
  
  widget_class->motion_notify_event = pitivi_ruler_motion_notify;

  ruler_class->draw_ticks = pitivi_ruler_draw_ticks;
  ruler_class->draw_pos = pitivi_ruler_draw_pos;
  
  cellobj_class->set_property = pitivi_ruler_set_property;
  cellobj_class->get_property = pitivi_ruler_get_property;
  
  g_object_class_install_property (G_OBJECT_CLASS (klass), PROP_UNIT,
				   g_param_spec_int ("ruler-unit","ruler-unit","ruler-unit",
						     G_MININT, G_MAXINT, 0, G_PARAM_READWRITE));
 
  g_object_class_install_property (G_OBJECT_CLASS (klass), PROP_VIDEORATE,
				   g_param_spec_int ("ruler-videorate", "ruler-videorate", "ruler-videorate",
						     G_MININT, G_MAXINT, 0, G_PARAM_READWRITE));
  g_signal_new ("moving-play",
		G_TYPE_FROM_CLASS (pitivi_class),
		G_SIGNAL_RUN_FIRST | G_SIGNAL_ACTION,
		G_STRUCT_OFFSET (PitiviRulerClass, moving),
		NULL, 
		NULL,                
		g_cclosure_marshal_VOID__POINTER,
		G_TYPE_NONE, 1, G_TYPE_POINTER);
  pitivi_class->moving = pitivi_ruler_moving;
}

static void
pitivi_ruler_init (PitiviRuler *ruler)
{
  GtkWidget *widget = GTK_WIDGET (ruler);

  ruler->private = g_new0 (PitiviRulerPrivate, 1);
  ruler->private->unit = PITIVI_SECONDS;
  ruler->timeline_x = 0;
  widget->requisition.width = widget->style->xthickness * 2 + 1;
  widget->requisition.height = widget->style->ythickness * 2 + RULER_HEIGHT;
  ruler->private->gc_play = pitivi_drawing_GdkGCcolor_new (255, 0, 0);
}


GtkWidget*
pitivi_ruler_new (gint unit)
{
  GtkWidget *ruler;

  ruler = g_object_new (PITIVI_TYPE_RULER, 
			"ruler-unit",
			unit,
			NULL);
  g_assert (ruler != NULL);
  return ruler;
}

static gint
pitivi_ruler_motion_notify (GtkWidget      *widget,
			  GdkEventMotion *event)
{
  GtkRuler *ruler;
  gint x;

  ruler = GTK_RULER (widget);

  if (event->is_hint)
    gdk_window_get_pointer (widget->window, &x, NULL, NULL);
  else
    x = event->x;

  ruler->position = ruler->lower + ((ruler->upper - ruler->lower) * x) / widget->allocation.width;
  g_object_notify (G_OBJECT (ruler), "position");

  /*  Make sure the ruler has been allocated already  */
  if (ruler->backing_store != NULL)
    gtk_ruler_draw_pos (ruler);

  return FALSE;
}

gchar *
under_ten (int nb)
{
  gchar *snb;
 
  snb = g_malloc (sizeof (gint) * 2);
  if (nb < 10)
    g_snprintf (snb, sizeof (snb), "0%d", nb);
  else
    g_snprintf (snb, sizeof (snb), "%d", nb);
  return snb;
}

gchar *
format_seconds (int secs)
{
  gchar *time[3], *str;
  gchar unit_str[1024];
  int count, hours, minutes, seconds = 0;
  
  str = unit_str;
  hours = (secs / 3600);
  minutes = (secs % 3600) / 60;
  seconds = (secs % 3600) % 60;
  
  time[2] = under_ten (hours);
  time[1] = under_ten (minutes);
  time[0] = under_ten (seconds);
  
  g_snprintf (unit_str, sizeof (unit_str), "%s:%s:%s" , 
	      time[2], 
	      time[1] , 
	      time[0]);
  for (count = 0; count < 2; count++)
    g_free (time[count]);
  return str;
}

static gchar *
pitivi_draw_label  (GtkRuler *ruler, int cur)
{
  PitiviRuler *self = ( PitiviRuler *) ruler;
  gchar unit_str[1024];
  gchar *label;
  gint64 nanoseconds;
  gint64 frames;

  label = unit_str;
  switch  ( self->private->unit )
    {
    case PITIVI_SECONDS:
      label = format_seconds (cur);
      break;
    case PITIVI_NANOSECONDS:
      nanoseconds = ((cur * GST_SECOND) / PITIVI_RULER (ruler)->private->videorate);
      g_snprintf (unit_str, sizeof (unit_str), "%lld" , ( gint64 ) nanoseconds);
      break;
    case PITIVI_FRAMES:
      frames = cur * PITIVI_RULER (ruler)->private->videorate;
      g_snprintf (unit_str, sizeof (unit_str), "%lld" , ( gint64 ) frames);
      break;
    default:
      g_snprintf (unit_str, sizeof (unit_str), "%lld" , ( gint64 ) cur);
      break;
    }
  return label;
}

static void
pitivi_ruler_draw_ticks (GtkRuler *ruler)
{
  GtkWidget *widget;
  GdkGC *gc, *bg_gc;
  gint i;
  gint width, height;
  gint xthickness;
  gint ythickness;
  gint length, ideal_length;
  gdouble lower, upper;		/* Upper and lower limits, in ruler units */
  gdouble increment;		/* Number of pixels per unit */
  gint scale;			/* Number of units per major unit */
  gdouble subd_incr;
  gdouble start, end, cur;
  gchar unit_str[32];
  gchar *myunit_str;
  gint digit_height;
  gint digit_offset;
  gint text_width;
  gint pos;
  PangoLayout *layout;
  PangoRectangle logical_rect, ink_rect;

  if (!GTK_WIDGET_DRAWABLE (ruler)) 
    return;

  widget = GTK_WIDGET (ruler);

  gc = widget->style->fg_gc[GTK_STATE_NORMAL];
  bg_gc = widget->style->bg_gc[GTK_STATE_NORMAL];

  xthickness = widget->style->xthickness;
  ythickness = widget->style->ythickness;
  layout = gtk_widget_create_pango_layout (widget, "012456789");
  pango_layout_get_extents (layout, &ink_rect, &logical_rect);
  
  digit_height = PANGO_PIXELS (ink_rect.height) + 2;
  digit_offset = ink_rect.y;

  width = widget->allocation.width;
  height = widget->allocation.height - ythickness * 2;
   
  gtk_paint_box (widget->style, ruler->backing_store,
		 GTK_STATE_NORMAL, GTK_SHADOW_OUT, 
		 NULL, widget, "hruler",
		 0, 0, 
		 widget->allocation.width, widget->allocation.height);
  
  
  gdk_draw_line (ruler->backing_store, gc,
		 xthickness,
		 height + ythickness,
		 widget->allocation.width - xthickness,
		 height + ythickness);

  upper = ruler->upper / ruler->metric->pixels_per_unit;
  lower = ruler->lower / ruler->metric->pixels_per_unit;

  if ((upper - lower) == 0) 
    return;
  increment = (gdouble) width / (upper - lower);

  /* determine the scale
   *  We calculate the text size as for the vruler instead of using
   *  text_width = gdk_string_width(font, unit_str), so that the result
   *  for the scale looks consistent with an accompanying vruler
   */
  scale = ceil (ruler->max_size / ruler->metric->pixels_per_unit);
  g_snprintf (unit_str, sizeof (unit_str), "%d", scale);
  text_width = strlen (unit_str) * digit_height + 1;

  for (scale = 0; scale < MAXIMUM_SCALES; scale++)
    if (ruler->metric->ruler_scale[scale] * fabs(increment) > 2 * text_width)
      break;

  if (scale == MAXIMUM_SCALES)
    scale = MAXIMUM_SCALES - 1;

  /* drawing starts here */
  length = 0;
  for (i = MAXIMUM_SUBDIVIDE - 1; i >= 0; i--)
    {
      subd_incr = (gdouble) ruler->metric->ruler_scale[scale] / 
	          (gdouble) ruler->metric->subdivide[i];
      if (subd_incr * fabs(increment) <= MINIMUM_INCR) 
	continue;

      /* Calculate the length of the tickmarks. Make sure that
       * this length increases for each set of ticks
       */
      ideal_length = height / (i + 1) - 1;
      if (ideal_length > ++length)
	length = ideal_length;

      if (lower < upper)
	{
	  start = floor (lower / subd_incr) * subd_incr;
	  end   = ceil  (upper / subd_incr) * subd_incr;
	}
      else
	{
	  start = floor (upper / subd_incr) * subd_incr;
	  end   = ceil  (lower / subd_incr) * subd_incr;
	}

  
      for (cur = start; cur <= end; cur += subd_incr)
	{
	  pos = ROUND ((cur - lower) * increment);

	  gdk_draw_line (ruler->backing_store, gc,
			 pos, height + ythickness, 
			 pos, height - length + ythickness);

	  /* draw label */
	  if (i == 0)
	    {
	      myunit_str = pitivi_draw_label  (GTK_RULER (widget), (int) cur);
	      pango_layout_set_text (layout, myunit_str, -1);
	      pango_layout_get_extents (layout, &logical_rect, NULL);
              gtk_paint_layout (widget->style,
                                ruler->backing_store,
                                GTK_WIDGET_STATE (widget),
				FALSE,
                                NULL,
                                widget,
                                "hruler",
                                pos + 2, ythickness + PANGO_PIXELS (logical_rect.y - digit_offset),
                                layout);
	    }
	}
    }

  g_object_unref (layout);
}

static void
pitivi_ruler_draw_pos (GtkRuler *ruler)
{
  GtkWidget *widget;
  GdkGC *gc;
  int i;
  gint x, y;
  gint width, height;
  gint bs_width, bs_height;
  gint xthickness;
  gint ythickness;
  gdouble increment;

  if (GTK_WIDGET_DRAWABLE (ruler))
    {
      widget = GTK_WIDGET (ruler);

      gc = widget->style->fg_gc[GTK_STATE_NORMAL];
      xthickness = widget->style->xthickness;
      ythickness = widget->style->ythickness;
      width = widget->allocation.width;
      height = widget->allocation.height - ythickness * 2;

      bs_width = height / 2;
      bs_width |= 1;  /* make sure it's odd */
      bs_height = bs_width / 2 + 1;

      if ((bs_width > 0) && (bs_height > 0))
	{
	  /*  If a backing store exists, restore the ruler  */
	  if (ruler->backing_store && ruler->non_gr_exp_gc)
	    {
	    gdk_draw_drawable (ruler->widget.window,
			       ruler->non_gr_exp_gc,
			       ruler->backing_store,
			       ruler->xsrc, ruler->ysrc,
			       ruler->xsrc, ruler->ysrc,
			       bs_width, bs_height);
	    }
	  increment = (gdouble) width / (ruler->upper - ruler->lower);
	  
	  x = ROUND ((ruler->position - ruler->lower) * increment) + (xthickness - bs_width) / 2 - 1;
	  y = (height + bs_height) / 2 + ythickness;
	  
	  if (GTK_WIDGET_IS_SENSITIVE(GTK_WIDGET(ruler)))
	    {
	      for (i = 0; i < bs_height; i++)
		{
		  gdk_draw_line (widget->window, gc,
				 x + i, y + i,
				 x + bs_width - 1 - i, y + i);
		}
	    }
	  ruler->xsrc = x;
	  ruler->ysrc = y;
	}
    }
}
