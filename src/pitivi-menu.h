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

#ifndef PITIVI_MENU_H
#define PITIVI_MENU_H

/*
 * Potentially, include other headers on which this header depends.
 */

#include  <gtk/gtk.h>
#include  "pitivi-types.h"

/*
 * Type macros.
 */

#define PITIVI_MENU_TYPE (pitivi_menu_get_type ())
#define PITIVI_MENU(obj) (G_TYPE_CHECK_INSTANCE_CAST ((obj), PITIVI_MENU_TYPE, PitiviMenu))
#define PITIVI_MENU_CLASS(klass) (G_TYPE_CHECK_CLASS_CAST ((klass), PITIVI_MENU_TYPE, PitiviMenuClass))
#define PITIVI_IS_MENU(obj) (G_TYPE_CHECK_TYPE ((obj), PITIVI_MENU_TYPE))
#define PITIVI_IS_MENU_CLASS(klass) (G_TYPE_CHECK_CLASS_TYPE ((klass), PITIVI_MENU_TYPE))
#define PITIVI_MENU_GET_CLASS(obj) (G_TYPE_INSTANCE_GET_CLASS ((obj), PITIVI_MENU_TYPE, PitiviMenuClass))


#define PITIVI_MAIN_ENTRY_MENUBAR    "MenuActions"
#define PITIVI_DEF_MENUBAR_FILENAME  "../ui/main_menubar.xml"
#define PITIVI_MAIN_MENUBAR_XML      "/MainMenu"
#define PITIVI_MAIN_TOOLBAR_XML      "/DefaultToolbar"

typedef struct _PitiviMenuPrivate PitiviMenuPrivate;
typedef struct _PitiviMenuPublic PitiviMenuPublic;
typedef struct _PitiviMenuClassPublic PitiviMenuClassPublic; 

struct _PitiviMenuPublic
{
  GtkWidget *menu;
  GtkUIManager *ui;
};

struct _PitiviMenu
{
  GtkWidget parent;
  
  /* instance public members */
  PitiviMenuPublic *public;
  
  /* private */
  PitiviMenuPrivate *private;
};


struct _PitiviMenuClassPublic
{
  void (*configure) (PitiviMenu *self);
};


struct _PitiviMenuClass
{
  GtkWidgetClass parent;
  /* class members */

  /* public */
  PitiviMenuClassPublic *public;
  /* private */
};

/* used by PITIVI_MENU_TYPE */
GType pitivi_menu_get_type (void);

/*
 * Method definitions.
 */

PitiviMenu	*pitivi_menu_new(GtkWidget *window, gchar *fname);
void		pitivi_menu_set_filename (PitiviMenu *menubar, const gchar *filename);
void		pitivi_menu_configure (PitiviMenu *self);
GtkWidget	*pitivi_create_menupopup (GtkWidget *self, 
				   GtkItemFactoryEntry *pMenuItem, 
				   gint iNbMenuItem);
#endif
