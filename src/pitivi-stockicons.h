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

#ifndef PITIVI_STOCKICONS_H
#define PITIVI_STOCKICONS_H

/*
 * Potentially, include other headers on which this header depends.
 */


#include	<gtk/gtk.h>
#include	<gdk/gdk.h>

#define PITIVI_STOCK_CUT "pitivi-cut"
#define PITIVI_STOCK_HAND "pitivi-hand"
#define PITIVI_STOCK_POINTER "pitivi-pointer"
#define PITIVI_STOCK_ZOOM "pitivi-zoom"

/*
 * Type macros.
 */

#define PITIVI_STOCKICONS_TYPE (pitivi_stockicons_get_type ())
#define PITIVI_STOCKICONS(obj) (G_TYPE_CHECK_INSTANCE_CAST ((obj), PITIVI_STOCKICONS_TYPE, PitiviStockIcons))
#define PITIVI_STOCKICONS_CLASS(klass) (G_TYPE_CHECK_CLASS_CAST ((klass), PITIVI_STOCKICONS_TYPE, PitiviStockIconsClass))
#define PITIVI_IS_STOCKICONS(obj) (G_TYPE_CHECK_TYPE ((obj), PITIVI_STOCKICONS_TYPE))
#define PITIVI_IS_STOCKICONS_CLASS(klass) (G_TYPE_CHECK_CLASS_TYPE ((klass), PITIVI_STOCKICONS_TYPE))
#define PITIVI_STOCKICONS_GET_CLASS(obj) (G_TYPE_INSTANCE_GET_CLASS ((obj), PITIVI_STOCKICONS_TYPE, PitiviStockIconsClass))

typedef struct _PitiviStockIcons PitiviStockIcons;
typedef struct _PitiviStockIconsClass PitiviStockIconsClass;
typedef struct _PitiviStockIconsPrivate PitiviStockIconsPrivate;

struct _PitiviStockIcons
{
  GObject parent;

  /* instance public members */

  /* private */
  PitiviStockIconsPrivate *private;
};

struct _PitiviStockIconsClass
{
  GObjectClass parent;
  /* class members */
};

/* used by PITIVI_STOCKICONS_TYPE */
GType pitivi_stockicons_get_type (void);

/*
 * Method definitions.
 */

PitiviStockIcons	*pitivi_stockicons_new(void);

#endif
