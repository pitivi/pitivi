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

#ifndef PITIVI_EFFECTSWINDOWPROPERTIES_H
#define PITIVI_EFFECTSWINDOWPROPERTIES_H

#include <gtk/gtk.h>
#include <gst/gst.h>
#include <gnl/gnloperation.h>
#include <gnl/gnlsource.h>
#include "pitivi-types.h"
#include "pitivi-windows.h"
#include "pitivi-sourceitem.h"
#include "pitivi-gstelementsettings.h"
/*
 * Potentially, include other headers on which this header depends.
 */

/*
 * Type macros.
 */

#define PITIVI_EFFECTSWINDOWPROPERTIES_TYPE (pitivi_effectswindowproperties_get_type ())
#define PITIVI_EFFECTSWINDOWPROPERTIES(obj) (G_TYPE_CHECK_INSTANCE_CAST ((obj), PITIVI_EFFECTSWINDOWPROPERTIES_TYPE, PitiviEffectsWindowProperties))
#define PITIVI_EFFECTSWINDOWPROPERTIES_CLASS(klass) (G_TYPE_CHECK_CLASS_CAST ((klass), PITIVI_EFFECTSWINDOWPROPERTIES_TYPE, PitiviEffectsWindowPropertiesClass))
#define PITIVI_IS_EFFECTSWINDOWPROPERTIES(obj) (G_TYPE_CHECK_TYPE ((obj), PITIVI_EFFECTSWINDOWPROPERTIES_TYPE))
#define PITIVI_IS_EFFECTSWINDOWPROPERTIES_CLASS(klass) (G_TYPE_CHECK_CLASS_TYPE ((klass), PITIVI_EFFECTSWINDOWPROPERTIES_TYPE))
#define PITIVI_EFFECTSWINDOWPROPERTIES_GET_CLASS(obj) (G_TYPE_INSTANCE_GET_CLASS ((obj), PITIVI_EFFECTSWINDOWPROPERTIES_TYPE, PitiviEffectsWindowPropertiesClass))

typedef struct _PitiviEffectsWindowProperties PitiviEffectsWindowProperties;
typedef struct _PitiviEffectsWindowPropertiesClass PitiviEffectsWindowPropertiesClass;
typedef struct _PitiviEffectsWindowPropertiesPrivate PitiviEffectsWindowPropertiesPrivate;

struct _PitiviEffectsWindowProperties
{
  PitiviWindows parent;

  /* instance public members */

  /* private */
  PitiviEffectsWindowPropertiesPrivate *private;
};

struct _PitiviEffectsWindowPropertiesClass
{
  PitiviWindowsClass parent;
  /* class members */
};

/* used by PITIVI_EFFECTSWINDOWPROPERTIES_TYPE */
GType pitivi_effectswindowproperties_get_type (void);

/*
 * Method definitions.
 */

PitiviEffectsWindowProperties	*pitivi_effectswindowproperties_new(PitiviSourceItem *effect);

#endif
