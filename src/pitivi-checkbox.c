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

#include <gtk/gtk.h>
#include "pitivi.h"
#include "pitivi-checkbox.h"

static     GObjectClass *parent_class;

enum {
  
  PITIVI_CHECKBOX_PROPERTY,
  PITIVI_CHECKBOX_INDICATOR
};

struct _PitiviCheckBoxPrivate
{
  /* instance private members */
  gboolean	dispose_has_run;
  gchar		*name;
  guint		type;
};

/*
 * forward definitions
 */

/*
 * Insert "added-value" functions here
 */

PitiviCheckBox *
pitivi_checkbox_new(guint type)
{
  PitiviCheckBox	*checkbox;
  
  checkbox = (PitiviCheckBox *) g_object_new(PITIVI_CHECKBOX_TYPE, NULL);
  checkbox->private->type = type;
  g_assert(checkbox != NULL);
  return checkbox;
}

static GObject *
pitivi_checkbox_constructor (GType type,
			     guint n_construct_properties,
			     GObjectConstructParam * construct_properties)
{
  GObject *obj;
  /* Invoke parent constructor. */
  obj = parent_class->constructor (type, n_construct_properties,
				   construct_properties);
  
  /* do stuff. */
  return obj;
}

static void
pitivi_checkbox_instance_init (GTypeInstance * instance, gpointer g_class)
{
  PitiviCheckBox *self = (PitiviCheckBox *) instance;

  self->private = g_new0(PitiviCheckBoxPrivate, 1);
  /* initialize all public and private members to reasonable default values. */ 
  
  self->private->dispose_has_run = FALSE;
  
  /* Do only initialisation here */
  /* The construction of the object should be done in the Constructor
     So that properties set at instanciation can be set */
}

static void
pitivi_checkbox_dispose (GObject *object)
{
  PitiviCheckBox	*self = PITIVI_CHECKBOX(object);

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
pitivi_checkbox_finalize (GObject *object)
{
  PitiviCheckBox	*self = PITIVI_CHECKBOX(object);

  /* 
   * Here, complete object destruction. 
   * You might not need to do much... 
   */

  g_free (self->private);
  G_OBJECT_CLASS (parent_class)->finalize (object);
}

static void
pitivi_checkbox_set_property (GObject * object,
			      guint property_id,
			      const GValue * value, GParamSpec * pspec)
{
  PitiviCheckBox *self = (PitiviCheckBox *) object;

  switch (property_id)
    {
      case PITIVI_CHECKBOX_PROPERTY:
	g_free (self->private->name);
	self->private->name = g_value_dup_string (value);
	break;
      case PITIVI_CHECKBOX_INDICATOR:
	self->private->type = g_value_get_int (value);
	break;
    default:
      /* We don't have any other property... */
      g_assert (FALSE);
      break;
    }
}

static void
pitivi_checkbox_get_property (GObject * object,
			      guint property_id,
			      GValue * value, GParamSpec * pspec)
{
  PitiviCheckBox *self = (PitiviCheckBox *) object;

  switch (property_id)
    {
      /*  case PITIVI_CHECKBOX_PROPERTY: { */
      /*     g_value_set_string (value, self->private->name); */
      /*   } */
      /*     break; */
    default:
      /* We don't have any other property... */
      g_assert (FALSE);
      break;
    }
}

static GdkBitmap * 
get_indicator_for_screen (GdkDrawable   *drawable,
			  IndicatorPart  part)			  
{
  GdkScreen *screen = gdk_drawable_get_screen (drawable);
  GdkBitmap *bitmap;
  GList *tmp_list;
  
  tmp_list = indicator_parts[part].bmap_list;
  while (tmp_list)
    {
      bitmap = tmp_list->data;
      
      if (gdk_drawable_get_screen (bitmap) == screen)
	return bitmap;
      
      tmp_list = tmp_list->next;
    }
  
  bitmap = gdk_bitmap_create_from_data (drawable,
					(gchar *)indicator_parts[part].bits,
					INDICATOR_PART_SIZE, INDICATOR_PART_SIZE);
  indicator_parts[part].bmap_list = g_list_prepend (indicator_parts[part].bmap_list, bitmap);

  return bitmap;
}

static void
pitivi_draw_part (GdkDrawable  *drawable,
	   GdkGC        *gc,
	   GdkRectangle *area,
	   gint          x,
	   gint          y,
	   IndicatorPart part)
{
  if (area)
    gdk_gc_set_clip_rectangle (gc, area);
  
  gdk_gc_set_ts_origin (gc, x, y);
  gdk_gc_set_stipple (gc, get_indicator_for_screen (drawable, part));
  gdk_gc_set_fill (gc, GDK_STIPPLED);

  gdk_draw_rectangle (drawable, gc, TRUE, x, y, INDICATOR_PART_SIZE, INDICATOR_PART_SIZE);

  gdk_gc_set_fill (gc, GDK_SOLID);

  if (area)
    gdk_gc_set_clip_rectangle (gc, NULL);
}

static GdkGC *
create_aa_gc (GdkWindow *window, GtkStyle *style, GtkStateType state_type)
{
  GdkColor aa_color;
  GdkGC *gc = gdk_gc_new (window);
   
  aa_color.red = (style->fg[state_type].red + style->bg[state_type].red) / 2;
  aa_color.green = (style->fg[state_type].green + style->bg[state_type].green) / 2;
  aa_color.blue = (style->fg[state_type].blue + style->bg[state_type].blue) / 2;
  
  gdk_gc_set_rgb_fg_color (gc, &aa_color);

  return gc;
}

static void 
pitivi_gtk_default_draw_check (
			PitiviCheckBox *self,
			GtkStyle       *style,
			GdkWindow      *window,
			GtkStateType   state_type,
			GtkShadowType  shadow_type,
			GdkRectangle   *area,
			GtkWidget      *widget,
			const gchar    *detail,
			gint           x,
			gint           y,
			gint           width,
			gint           height)
{
  if (detail && strcmp (detail, "cellcheck") == 0)
    {
      gdk_draw_rectangle (window,
			  widget->style->base_gc[state_type],
			  TRUE,
                          x, y,
			  width, height);
      gdk_draw_rectangle (window,
			  widget->style->text_gc[state_type],
			  FALSE,
                          x, y,
			  width, height);

      x -= (1 + INDICATOR_PART_SIZE - width) / 2;
      y -= (((1 + INDICATOR_PART_SIZE - height) / 2) - 1);
      if (shadow_type == GTK_SHADOW_IN)
	{
	  pitivi_draw_part (window, style->text_gc[state_type], area, x, y, CHECK_TEXT);
	  pitivi_draw_part (window, style->text_aa_gc[state_type], area, x, y, CHECK_AA);
	}
      else if (shadow_type == GTK_SHADOW_ETCHED_IN)
	{
	  pitivi_draw_part (window, style->text_gc[state_type], area, x, y, CHECK_INCONSISTENT_TEXT);
	}
    }
  else
    {
      GdkGC *free_me = NULL;
      
      GdkGC *base_gc;
      GdkGC *text_gc;
      GdkGC *aa_gc;

      x -= (1 + INDICATOR_PART_SIZE - width) / 2;
      y -= (1 + INDICATOR_PART_SIZE - height) / 2;

      if (strcmp (detail, "check") == 0)
	{
	  text_gc = style->fg_gc[state_type];
	  base_gc = style->bg_gc[state_type];
	  aa_gc = free_me = create_aa_gc (window, style, state_type);
	}
      else
	{
	  if (state_type == GTK_STATE_ACTIVE)
	    {
	      text_gc = style->fg_gc[state_type];
	      base_gc = style->bg_gc[state_type];
	      aa_gc = free_me = create_aa_gc (window, style, state_type);
	    }
	  else
	    {
	      text_gc = style->text_gc[state_type];
	      base_gc = style->base_gc[state_type];
	      aa_gc = style->text_aa_gc[state_type];
	    }

	  pitivi_draw_part (window, base_gc, area, x, y, CHECK_BASE);
	  pitivi_draw_part (window, style->black_gc, area, x, y, CHECK_BLACK);
	  pitivi_draw_part (window, style->dark_gc[state_type], area, x, y, CHECK_DARK);
	  pitivi_draw_part (window, style->mid_gc[state_type], area, x, y, CHECK_MID);
	  pitivi_draw_part (window, style->light_gc[state_type], area, x, y, CHECK_LIGHT);
	}

      if (shadow_type == GTK_SHADOW_IN)
	{
	  pitivi_draw_part (window, text_gc, area, x, y, self->private->type);
	  /* pitivi_draw_part (window, aa_gc, area, x, y, CHECK_AA); */
	}
      else if (shadow_type == GTK_SHADOW_ETCHED_IN) /* inconsistent */
	{
	  pitivi_draw_part (window, text_gc, area, x, y, CHECK_INCONSISTENT_TEXT);
	}

      if (free_me)
	g_object_unref (free_me);
    }
}

void
pitivi_gtk_check_button_get_props (GtkCheckButton *check_button,
			     gint           *indicator_size,
			     gint           *indicator_spacing)
{
  GtkWidget *widget =  GTK_WIDGET (check_button);

  if (indicator_size)
      gtk_widget_style_get (widget, "indicator_size", indicator_size, NULL);

  if (indicator_spacing)
      gtk_widget_style_get (widget, "indicator_spacing", indicator_spacing, NULL);
}

static void
pitivi_gtk_real_check_button_draw_indicator (GtkCheckButton  *check_button,
					     GdkRectangle    *area)
{
  GtkWidget *widget;
  PitiviCheckBox * self;
  GtkWidget *child;
  GtkButton *button;
  GtkToggleButton *toggle_button;
  GtkStateType state_type;
  GtkShadowType shadow_type;
  gint x, y;
  gint indicator_size;
  gint indicator_spacing;
  gint focus_width;
  gint focus_pad;
  gboolean interior_focus;
  
  self = ( PitiviCheckBox * ) check_button;
  if (GTK_WIDGET_DRAWABLE (check_button))
    {
      widget = GTK_WIDGET (check_button);
      button = GTK_BUTTON (check_button);
      toggle_button = GTK_TOGGLE_BUTTON (check_button);
  
      gtk_widget_style_get (widget, "interior_focus", &interior_focus,
			    "focus-line-width", &focus_width, 
			    "focus-padding", &focus_pad, NULL);

      pitivi_gtk_check_button_get_props (check_button, &indicator_size, &indicator_spacing);
      x = widget->allocation.x + indicator_spacing + GTK_CONTAINER (widget)->border_width;
      y = widget->allocation.y + (widget->allocation.height - indicator_size) / 2;

      child = GTK_BIN (check_button)->child;
      if (!interior_focus || !(child && GTK_WIDGET_VISIBLE (child)))
	x += focus_width + focus_pad;      

      if (toggle_button->inconsistent)
	shadow_type = GTK_SHADOW_ETCHED_IN;
      else if (toggle_button->active)
	shadow_type = GTK_SHADOW_IN;
      else
	shadow_type = GTK_SHADOW_OUT;

      if (button->activate_timeout || (button->button_down && button->in_button))
	state_type = GTK_STATE_ACTIVE;
      else if (button->in_button)
	state_type = GTK_STATE_PRELIGHT;
      else if (!GTK_WIDGET_IS_SENSITIVE (widget))
	state_type = GTK_STATE_INSENSITIVE;
      else
	state_type = GTK_STATE_NORMAL;
      
      if (gtk_widget_get_direction (widget) == GTK_TEXT_DIR_RTL)
	x = widget->allocation.x + widget->allocation.width - (indicator_size + x - widget->allocation.x);

      if (GTK_WIDGET_STATE (toggle_button) == GTK_STATE_PRELIGHT)
	{
	  GdkRectangle restrict_area;
	  GdkRectangle new_area;
	      
	  restrict_area.x = widget->allocation.x + GTK_CONTAINER (widget)->border_width;
	  restrict_area.y = widget->allocation.y + GTK_CONTAINER (widget)->border_width;
	  restrict_area.width = widget->allocation.width - (2 * GTK_CONTAINER (widget)->border_width);
	  restrict_area.height = widget->allocation.height - (2 * GTK_CONTAINER (widget)->border_width);
	  
	    if (gdk_rectangle_intersect (area, &restrict_area, &new_area))
	    {
	      gtk_paint_flat_box (widget->style, widget->window, GTK_STATE_PRELIGHT,
				  GTK_SHADOW_ETCHED_OUT, 
				  area, widget, "checkbutton",
				  new_area.x, new_area.y,
				  new_area.width, new_area.height);
	    }
	  
	}
      pitivi_gtk_default_draw_check (self,
				     widget->style, \
				     widget->window, \
				     state_type, \
				     shadow_type, \
				     area, \
				     widget, \
				     "checkbutton", \
				     x, \
				     y, indicator_size\
				     , indicator_size);
    }
}


static void
pitivi_checkbox_class_init (gpointer g_class, gpointer g_class_data)
{
  GObjectClass *gobject_class = G_OBJECT_CLASS (g_class);
  PitiviCheckBoxClass *klass = PITIVI_CHECKBOX_CLASS (g_class);
  GtkCheckButtonClass *checkboxclass = g_class;

  parent_class = G_OBJECT_CLASS (g_type_class_peek_parent (g_class));

  gobject_class->constructor = pitivi_checkbox_constructor;
  gobject_class->dispose = pitivi_checkbox_dispose;
  gobject_class->finalize = pitivi_checkbox_finalize;

  gobject_class->set_property = pitivi_checkbox_set_property;
  gobject_class->get_property = pitivi_checkbox_get_property;
  checkboxclass->draw_indicator = pitivi_gtk_real_check_button_draw_indicator;
}

GType
pitivi_checkbox_get_type (void)
{
  static GType type = 0;
 
  if (type == 0)
    {
      static const GTypeInfo info = {
	sizeof (PitiviCheckBoxClass),
	NULL,			/* base_init */
	NULL,			/* base_finalize */
	pitivi_checkbox_class_init,	/* class_init */
	NULL,			/* class_finalize */
	NULL,			/* class_data */
	sizeof (PitiviCheckBox),
	0,			/* n_preallocs */
	pitivi_checkbox_instance_init	/* instance_init */
      };
      type = g_type_register_static (GTK_TYPE_CHECK_BUTTON,
				     "PitiviCheckBoxType", &info, 0);
    }

  return type;
}
