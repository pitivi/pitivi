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

#ifndef PITIVI_RULER_H
#define PITIVI_RULER_H

/*
 * Potentially, include other headers on which this header depends.
 */

#include <gtk/gtk.h>

/*
 * Type macros.
 */

#define PITIVI_RULER_TYPE (pitivi_ruler_get_type ())
#define PITIVI_RULER(obj) (G_TYPE_CHECK_INSTANCE_CAST ((obj), PITIVI_RULER_TYPE, PitiviRuler))
#define PITIVI_RULER_CLASS(klass) (G_TYPE_CHECK_CLASS_CAST ((klass), PITIVI_RULER_TYPE, PitiviRulerClass))
#define PITIVI_IS_RULER(obj) (G_TYPE_CHECK_TYPE ((obj), PITIVI_RULER_TYPE))
#define PITIVI_IS_RULER_CLASS(klass) (G_TYPE_CHECK_CLASS_TYPE ((klass), PITIVI_RULER_TYPE))
#define PITIVI_RULER_GET_CLASS(obj) (G_TYPE_INSTANCE_GET_CLASS ((obj), PITIVI_RULER_TYPE, PitiviRulerClass))

typedef struct _PitiviRuler PitiviRuler;
typedef struct _PitiviRulerClass PitiviRulerClass;
typedef struct _PitiviRulerPrivate PitiviRulerPrivate;

struct _PitiviRuler
{
  GtkRulerClass parent;

  /* instance public members */

  /* private */
  PitiviRulerPrivate *private;
};

struct _PitiviRulerClass
{
  GtkRulerClass parent;
  /* class members */
};

/* used by PITIVI_RULER_TYPE */
GType pitivi_ruler_get_type (void);

/*
 * Method definitions.
 */

PitiviRuler	*pitivi_ruler_new(void);

#endif
