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


#ifndef __PITIVI_RULER_H__
#define __PITIVI_RULER_H__


#include <gdk/gdk.h>
#include <gtk/gtk.h>
#include <config.h>
#include <math.h>
#include <glib/gprintf.h>
#include <string.h>


#ifdef __cplusplus
extern "C" {
#endif /* __cplusplus */


#define PITIVI_TYPE_RULER	      (pitivi_ruler_get_type ())
#define PITIVI_RULER(obj)             (G_TYPE_CHECK_INSTANCE_CAST ((obj), GTK_TYPE_RULER, PitiviRuler))
#define PITIVI_RULER_CLASS(klass)     (G_TYPE_CHECK_CLASS_CAST ((klass), GTK_TYPE_RULER, PitiviRulerClass))
#define PITIVI_IS_RULER(obj)         (G_TYPE_CHECK_INSTANCE_TYPE ((obj), GTK_TYPE_RULER))
#define PITIVI_IS_RULER_CLASS(klass) (G_TYPE_CHECK_CLASS_TYPE ((klass), GTK_TYPE_RULER))
#define PITIVI_RULER_GET_CLASS(obj)   (G_TYPE_INSTANCE_GET_CLASS ((obj), GTK_TYPE_RULER, PitiviRulerClass))

typedef enum
{
  PITIVI_RNANOSECONDS = 0,
  PITIVI_RSECONDS,
  PITIVI_RSECONDS2x,
  PITIVI_RSECONDS4x,
  PITIVI_RSECONDS8x,
  PITIVI_RSECONDS16x,
  PITIVI_RFRAMES,
  PITIVI_RFRAMES2x,
  PITIVI_RFRAMES4x,
  PITIVI_RFRAMES8x,
  PITIVI_RFRAMES16x
} PitiviMetricType;
  
  enum {
    GINT_WIDTH = 0,
    GINT_HEIGHT,
    GINT_XTHICKNESS,
    GINT_YTHICKNESS,
    GINT_LENGTH,
    GINT_IDEAL_LENGTH,
    GINT_LOWER,
    GINT_UPPER,
    GINT_SCALE,
    GINT_DIGIT_HEIGHT,
    GINT_DIGIT_OFFSET,
    GINT_TEXT_WIDTH,
    GINT_ITERATOR,
    GINT_LAST,
  };
  
    enum {
    GDOUBLE_START = 0,
    GDOUBLE_END,
    GDOUBLE_CUR,
    GDOUBLE_SUBD,
    GDOUBLE_INCR,
    GDOUBLE_LOWER,
    GDOUBLE_UPPER,
    GDOUBLE_LAST,
  };

  
typedef struct _PitiviRuler       PitiviRuler;
typedef struct _PitiviRulerClass  PitiviRulerClass;
typedef struct _PitiviRulerPrivate PitiviRulerPrivate;

struct _PitiviRuler
{
  GtkRuler ruler;
  PitiviRulerPrivate *private;
};

struct _PitiviRulerClass
{
  GtkRulerClass parent_class;
};


GType      pitivi_ruler_get_type (void) G_GNUC_CONST;
GtkWidget* pitivi_ruler_new      (gint unit);

#ifdef __cplusplus
}
#endif /* __cplusplus */


#endif /* __PITIVI_RULER_H__ */
