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

#ifndef PITIVI_PROJECTWINDOWS_H
#define PITIVI_PROJECTWINDOWS_H

/*
 * Potentially, include other headers on which this header depends.
 */

#include "pitivi-windows.h"
#include "pitivi-project.h"

/*
 * Type macros.
 */

#define PITIVI_PROJECTWINDOWS_TYPE (pitivi_projectwindows_get_type ())
#define PITIVI_PROJECTWINDOWS(obj) (G_TYPE_CHECK_INSTANCE_CAST ((obj), PITIVI_PROJECTWINDOWS_TYPE, PitiviProjectWindows))
#define PITIVI_PROJECTWINDOWS_CLASS(klass) (G_TYPE_CHECK_CLASS_CAST ((klass), PITIVI_PROJECTWINDOWS_TYPE, PitiviProjectWindowsClass))
#define PITIVI_IS_PROJECTWINDOWS(obj) (G_TYPE_CHECK_TYPE ((obj), PITIVI_PROJECTWINDOWS_TYPE))
#define PITIVI_IS_PROJECTWINDOWS_CLASS(klass) (G_TYPE_CHECK_CLASS_TYPE ((klass), PITIVI_PROJECTWINDOWS_TYPE))
#define PITIVI_PROJECTWINDOWS_GET_CLASS(obj) (G_TYPE_INSTANCE_GET_CLASS ((obj), PITIVI_PROJECTWINDOWS_TYPE, PitiviProjectWindowsClass))

typedef struct _PitiviProjectWindows PitiviProjectWindows;
typedef struct _PitiviProjectWindowsClass PitiviProjectWindowsClass;
typedef struct _PitiviProjectWindowsPrivate PitiviProjectWindowsPrivate;

struct _PitiviProjectWindows
{
  PitiviWindows parent;

  /* instance public members */
  PitiviProject	*project;

  /* private */
  PitiviProjectWindowsPrivate *private;
};

struct _PitiviProjectWindowsClass
{
  PitiviWindowsClass parent;
  /* class members */
};

/* used by PITIVI_PROJECTWINDOWS_TYPE */
GType pitivi_projectwindows_get_type (void);

/*
 * Method definitions.
 */

PitiviProjectWindows	*pitivi_projectwindows_new(void);

#endif
