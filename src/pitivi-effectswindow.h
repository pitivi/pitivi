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

#ifndef PITIVI_EFFECTSWINDOW_H
#define PITIVI_EFFECTSWINDOW_H

typedef struct _PitiviEffectsWindow PitiviEffectsWindow;

/*
 * Potentially, include other headers on which this header depends.
 */

#include <gtk/gtk.h>
#include <gst/gst.h>
#include "pitivi-windows.h"
#include "pitivi-stockicons.h"

/*
 * Type macros.
 */

#define PITIVI_EFFECTSWINDOW_TYPE (pitivi_effectswindow_get_type ())
#define PITIVI_EFFECTSWINDOW(obj) (G_TYPE_CHECK_INSTANCE_CAST ((obj), PITIVI_EFFECTSWINDOW_TYPE, PitiviEffectsWindow))
#define PITIVI_EFFECTSWINDOW_CLASS(klass) (G_TYPE_CHECK_CLASS_CAST ((klass), PITIVI_EFFECTSWINDOW_TYPE, PitiviEffectsWindowClass))
#define PITIVI_IS_EFFECTSWINDOW(obj) (G_TYPE_CHECK_TYPE ((obj), PITIVI_EFFECTSWINDOW_TYPE))
#define PITIVI_IS_EFFECTSWINDOW_CLASS(klass) (G_TYPE_CHECK_CLASS_TYPE ((klass), PITIVI_EFFECTSWINDOW_TYPE))
#define PITIVI_EFFECTSWINDOW_GET_CLASS(obj) (G_TYPE_INSTANCE_GET_CLASS ((obj), PITIVI_EFFECTSWINDOW_TYPE, PitiviEffectsWindowClass))

typedef struct _PitiviEffectsWindowClass PitiviEffectsWindowClass;
typedef struct _PitiviEffectsWindowPrivate PitiviEffectsWindowPrivate;
typedef struct _PitiviEffectsTree PitiviEffectsTree;

#define PITIVI_EFFECTS_WINDOW_NB_COL	  1
#define PITIVI_VIDEO_EFFECT_LABEL	  "Video"
#define PITIVI_AUDIO_EFFECT_LABEL	  "Audio"
#define PITIVI_TRANSITION_EFFECT_LABEL	  "Transition"

#define PITIVI_EFFECTS_WIN_SIZEX	  200
#define PITIVI_EFFECTS_WIN_SIZEY	  250

typedef enum {

  PITIVI_EFFECT_TRANSITION_TYPE = 1,  
  PITIVI_EFFECT_VIDEO_TYPE,
  PITIVI_EFFECT_AUDIO_TYPE,
  PITIVI_EFFECT_NBCAT_TYPE
  
} PitiviEffectsTypeEnum;

typedef enum {
  PITIVI_BARWIPE,
  PITIVI_BOXWIPE,
  PITIVI_FOURBOXWIPE,
  PITIVI_BARNDOORWIPE,
  PITIVI_DIAGONALWIPE,
  PITIVI_BOWTIEWIPE,
  PITIVI_MISCDIAGONALWIPE,
  PITIVI_VEEWIPE,
  PITIVI_BARNVEEWIPE,
  PITIVI_IRISWIPE,
  PITIVI_CLOCKWIPE,
  PITIVI_PINWHEELWIPE,
  PITIVI_FANWIPE,
  PITIVI_DOUBLEFANWIPE,
  PITIVI_SINGLESWEEPWIPE, 
  PITIVI_DOUBLESWEEPWIPE,
  PITIVI_SALOONDOORWIPE,
  PITIVI_WINDSHIELDWIPE,
  PITIVI_LAST_WIPE
} PitiviSmpteEnum;

typedef struct _PitiviTransProp
{
  gint		id_categorie;
  gchar		*name;
  gchar		*description;
  gchar		*image;
  gint		smpte_num;
}		PitiviTransProp;

struct _PitiviEffectsTree
{
  GtkWidget     *window;
  GtkWidget     *label;
  GtkWidget     *treeview;
  GtkTreeStore	*model;
  GtkTreeIter	treeiter;
  GdkPixbuf	*pixbuf;
  GtkWidget     *scroll;
  guint		order;
};

struct _PitiviEffectsWindow
{
  PitiviWindows parent;

  /* instance public members */

  /* private */
  PitiviEffectsWindowPrivate *private;
};

struct _PitiviEffectsWindowClass
{
  PitiviWindowsClass parent;
  /* class members */
};

/* used by PITIVI_EFFECTSWINDOW_TYPE */
GType pitivi_effectswindow_get_type (void);

/*
 * Method definitions.
 */

PitiviEffectsWindow	*pitivi_effectswindow_new(PitiviMainApp *mainapp);

void pitivi_effectstree_set_gst (PitiviEffectsTree *tree_effect, 
				 PitiviEffectsTypeEnum eneffects,  
				 PitiviSettings *self);
GList *get_transition_effects_list(GstElementFactory *factory);
GList *fill_smpte_transition_list(GList* fx_transition);
#endif
