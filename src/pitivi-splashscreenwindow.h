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

#ifndef PITIVI_SPLASHSCREENWINDOW_H
#define PITIVI_SPLASHSCREENWINDOW_H

/*
 * Potentially, include other headers on which this header depends.
 */

#include <gtk/gtk.h>
#include "pitivi-types.h"

/*
 * Type macros.
 */

#define PITIVI_SPLASHSCREENWINDOW_TYPE (pitivi_splashscreenwindow_get_type ())
#define PITIVI_SPLASHSCREENWINDOW(obj) (G_TYPE_CHECK_INSTANCE_CAST ((obj), PITIVI_SPLASHSCREENWINDOW_TYPE, PitiviSplashScreenWindow))
#define PITIVI_SPLASHSCREENWINDOW_CLASS(klass) (G_TYPE_CHECK_CLASS_CAST ((klass), PITIVI_SPLASHSCREENWINDOW_TYPE, PitiviSplashScreenWindowClass))
#define PITIVI_IS_SPLASHSCREENWINDOW(obj) (G_TYPE_CHECK_TYPE ((obj), PITIVI_SPLASHSCREENWINDOW_TYPE))
#define PITIVI_IS_SPLASHSCREENWINDOW_CLASS(klass) (G_TYPE_CHECK_CLASS_TYPE ((klass), PITIVI_SPLASHSCREENWINDOW_TYPE))
#define PITIVI_SPLASHSCREENWINDOW_GET_CLASS(obj) (G_TYPE_INSTANCE_GET_CLASS ((obj), PITIVI_SPLASHSCREENWINDOW_TYPE, PitiviSplashScreenWindowClass))

typedef struct _PitiviSplashScreenWindowPrivate PitiviSplashScreenWindowPrivate;

struct _PitiviSplashScreenWindow
{
  GtkWindow parent;

  /* instance public members */

  /* private */
  PitiviSplashScreenWindowPrivate *private;
};

struct _PitiviSplashScreenWindowClass
{
  GtkWindowClass parent;
  /* class members */
};

/* used by PITIVI_SPLASHSCREENWINDOW_TYPE */
GType pitivi_splashscreenwindow_get_type (void);

/*
 * Method definitions.
 */

PitiviSplashScreenWindow	*pitivi_splashscreenwindow_new ();
void				pitivi_splashscreenwindow_set_fraction (PitiviSplashScreenWindow *self, gdouble per);
void				pitivi_splashscreenwindow_set_label (PitiviSplashScreenWindow *self, gchar *label);
void				pitivi_splashscreenwindow_set_both (PitiviSplashScreenWindow *self, gdouble per, gchar *label);

#endif
