/* 
 * PiTiVi
 * Copyright (C) <2004>		 Guillaume Casanova <casano_g@epita.fr>
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

#ifndef PITIVI_CONTROLLER_H
#define PITIVI_CONTROLLER_H

/*
 * Potentially, include other headers on which this header depends.
 */

#include <gtk/gtk.h>
#include "pitivi-types.h"
#include "pitivi-stockicons.h"

/*
 * Type macros.
 */

#define PITIVI_CONTROLLER_TYPE (pitivi_controller_get_type ())
#define PITIVI_CONTROLLER(obj) (G_TYPE_CHECK_INSTANCE_CAST ((obj), PITIVI_CONTROLLER_TYPE, PitiviController))
#define PITIVI_CONTROLLER_CLASS(klass) (G_TYPE_CHECK_CLASS_CAST ((klass), PITIVI_CONTROLLER_TYPE, PitiviControllerClass))
#define PITIVI_IS_CONTROLLER(obj) (G_TYPE_CHECK_TYPE ((obj), PITIVI_CONTROLLER_TYPE))
#define PITIVI_IS_CONTROLLER_CLASS(klass) (G_TYPE_CHECK_CLASS_TYPE ((klass), PITIVI_CONTROLLER_TYPE))
#define PITIVI_CONTROLLER_GET_CLASS(obj) (G_TYPE_INSTANCE_GET_CLASS ((obj), PITIVI_CONTROLLER_TYPE, PitiviControllerClass))

typedef struct _PitiviControllerPrivate PitiviControllerPrivate;

struct _PitiviController
{
  GtkHBox parent;

  /* instance public members */

  /* private */
  PitiviControllerPrivate *private;
};

struct _PitiviControllerClass
{
  GtkHBoxClass parent;
  /* class members */
  void (* pause) (PitiviController *cell, gpointer data);
};

/* used by PITIVI_CONTROLLER_TYPE */
GType pitivi_controller_get_type (void);

/*
 * Method definitions.
 */

PitiviController	*pitivi_controller_new (void);
void			connect2viewer (PitiviController *controller, GtkWidget *viewer);

#endif
