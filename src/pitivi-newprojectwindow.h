/* 
 * PiTiVi
 * Copyright (C) <2004> Bloch Stephan <bloch_s@epita.fr>
 *                      Carbon Julien <carbon_j@epita.fr>
 *                      Dubart Loic <dubart_l@epita.fr>
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

#ifndef PITIVI_NEWPROJECTWINDOW_H
#define PITIVI_NEWPROJECTWINDOW_H

/*
 * Potentially, include other headers on which this header depends.
 */

#include "pitivi.h"
#include "pitivi-windows.h"

/*
 * Type macros.
 */

#define PITIVI_NEWPROJECTWINDOW_TYPE (pitivi_newprojectwindow_get_type ())
#define PITIVI_NEWPROJECTWINDOW(obj) (G_TYPE_CHECK_INSTANCE_CAST ((obj), PITIVI_NEWPROJECTWINDOW_TYPE, PitiviNewProjectWindow))
#define PITIVI_NEWPROJECTWINDOW_CLASS(klass) (G_TYPE_CHECK_CLASS_CAST ((klass), PITIVI_NEWPROJECTWINDOW_TYPE, PitiviNewProjectWindowClass))
#define PITIVI_IS_NEWPROJECTWINDOW(obj) (G_TYPE_CHECK_TYPE ((obj), PITIVI_NEWPROJECTWINDOW_TYPE))
#define PITIVI_IS_NEWPROJECTWINDOW_CLASS(klass) (G_TYPE_CHECK_CLASS_TYPE ((klass), PITIVI_NEWPROJECTWINDOW_TYPE))
#define PITIVI_NEWPROJECTWINDOW_GET_CLASS(obj) (G_TYPE_INSTANCE_GET_CLASS ((obj), PITIVI_NEWPROJECTWINDOW_TYPE, PitiviNewProjectWindowClass))

typedef struct _PitiviNewProjectWindow PitiviNewProjectWindow;
typedef struct _PitiviNewProjectWindowClass PitiviNewProjectWindowClass;
typedef struct _PitiviNewProjectWindowPrivate PitiviNewProjectWindowPrivate;

struct _PitiviNewProjectWindow
{
  PitiviWindows parent;
  
  /* instance public members */

  /* private */
  PitiviNewProjectWindowPrivate *private;
};

struct _PitiviNewProjectWindowClass
{
  PitiviWindowsClass parent;
  /* class members */
};

/* used by PITIVI_NEWPROJECTWINDOW_TYPE */
GType			pitivi_newprojectwindow_get_type (void);

/*
 * Method definitions.
 */

PitiviNewProjectWindow	*pitivi_newprojectwindow_new(PitiviMainApp *mainapp);

#endif
