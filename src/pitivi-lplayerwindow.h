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

#ifndef PITIVI_LPLAYERWINDOW_H
#define PITIVI_LPLAYERWINDOW_H

/*
 * Potentially, include other headers on which this header depends.
 */

/*
 * Type macros.
 */

#define PITIVI_LPLAYERWINDOW_TYPE (pitivi_lplayerwindow_get_type ())
#define PITIVI_LPLAYERWINDOW(obj) (G_TYPE_CHECK_INSTANCE_CAST ((obj), PITIVI_LPLAYERWINDOW_TYPE, PitiviLPlayerWindow))
#define PITIVI_LPLAYERWINDOW_CLASS(klass) (G_TYPE_CHECK_CLASS_CAST ((klass), PITIVI_LPLAYERWINDOW_TYPE, PitiviLPlayerWindowClass))
#define PITIVI_IS_LPLAYERWINDOW(obj) (G_TYPE_CHECK_TYPE ((obj), PITIVI_LPLAYERWINDOW_TYPE))
#define PITIVI_IS_LPLAYERWINDOW_CLASS(klass) (G_TYPE_CHECK_CLASS_TYPE ((klass), PITIVI_LPLAYERWINDOW_TYPE))
#define PITIVI_LPLAYERWINDOW_GET_CLASS(obj) (G_TYPE_INSTANCE_GET_CLASS ((obj), PITIVI_LPLAYERWINDOW_TYPE, PitiviLPlayerWindowClass))

typedef struct _PitiviLPlayerWindow PitiviLPlayerWindow;
typedef struct _PitiviLPlayerWindowClass PitiviLPlayerWindowClass;
typedef struct _PitiviLPlayerWindowPrivate PitiviLPlayerWindowPrivate;

struct _PitiviLPlayerWindow
{
  GtkWindow parent;

  /* instance public members */
  gchar *filename;

  /* private */
  PitiviLPlayerWindowPrivate *private;
};

struct _PitiviLPlayerWindowClass
{
  GtkWindowClass parent;
  /* class members */
};

/* used by PITIVI_LPLAYERWINDOW_TYPE */
GType pitivi_lplayerwindow_get_type (void);

/*
 * Method definitions.
 */

PitiviLPlayerWindow	*pitivi_lplayerwindow_new(gchar *filename);

#endif
