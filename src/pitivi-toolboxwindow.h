/* 
 * PiTiVi
 * Copyright (C) <2004> Bloch Stephan <bloch_s@epita.fr>
 *                      Carbon Julien <carbon_j@epita.fr>
 *                      Dubart Loic <dubart_l@epita.fr>
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

#ifndef PITIVI_TOOLBOXWINDOW_H
#define PITIVI_TOOLBOXWINDOW_H

/*
 * Potentially, include other headers on which this header depends.
 */
#include <gtk/gtk.h>
#include "pitivi-mainapp.h"
#include "pitivi-menu.h"
#include "pitivi-stockicons.h"
#include "pitivi-toolbox.h"
#include "pitivi-timelinewindow.h"
#include "pitivi-sourcelistwindow.h"
#include "pitivi-effectswindow.h"
#include "pitivi-projectsettings.h"
#include "pitivi-newprojectwindow.h"
#include "pitivi-viewerwindow.h"

/*
 * Type macros.
 */

#define PITIVI_TOOLBOXWINDOW_TYPE (pitivi_toolboxwindow_get_type ())
#define PITIVI_TOOLBOXWINDOW(obj) (G_TYPE_CHECK_INSTANCE_CAST ((obj), PITIVI_TOOLBOXWINDOW_TYPE, PitiviToolboxWindow))
#define PITIVI_TOOLBOXWINDOW_CLASS(klass) (G_TYPE_CHECK_CLASS_CAST ((klass), PITIVI_TOOLBOXWINDOW_TYPE, PitiviToolboxWindowClass))
#define PITIVI_IS_TOOLBOXWINDOW(obj) (G_TYPE_CHECK_TYPE ((obj), PITIVI_TOOLBOXWINDOW_TYPE))
#define PITIVI_IS_TOOLBOXWINDOW_CLASS(klass) (G_TYPE_CHECK_CLASS_TYPE ((klass), PITIVI_TOOLBOXWINDOW_TYPE))
#define PITIVI_TOOLBOXWINDOW_GET_CLASS(obj) (G_TYPE_INSTANCE_GET_CLASS ((obj), PITIVI_TOOLBOXWINDOW_TYPE, PitiviToolboxWindowClass))

#define PITIVI_TOOLBOXWINDOW_DF_TITLE "Pitivi Project"

typedef struct _PitiviToolboxWindow PitiviToolboxWindow;
typedef struct _PitiviToolboxWindowClass PitiviToolboxWindowClass;
typedef struct _PitiviToolboxWindowPrivate PitiviToolboxWindowPrivate;

struct _PitiviToolboxWindow
{
  GtkWindow parent;

  /* instance public members */
  
  PitiviTimelineWindow	 *timelinewin;
  PitiviSourceListWindow *srclistwin;
  PitiviEffectsWindow	 *effectswin;
  PitiviViewerWindow	 *viewerwin;
  
  /* private */
  
  PitiviToolboxWindowPrivate *private;
};

struct _PitiviToolboxWindowClass
{
  GtkWindowClass parent;
  /* class members */
};

/* used by PITIVI_TOOLBOXWINDOW_TYPE */
GType pitivi_toolboxwindow_get_type (void);

/*
 * Method definitions.
 */

PitiviToolboxWindow	*pitivi_toolboxwindow_new (PitiviMainApp *main_app);
void			pitivi_callb_toolbox_fileopen_project ( GtkAction *action, PitiviToolboxWindow *self );

#endif
