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

#include "pitivi.h"
#include "pitivi-stockicons.h"

static const char *items [] =
{
	PITIVI_STOCK_CUT,
	PITIVI_STOCK_HAND,
	PITIVI_STOCK_POINTER,
	PITIVI_STOCK_ZOOM,
	PITIVI_STOCK_EFFECT_CAT,
	PITIVI_STOCK_EFFECT_CAT_OPEN,
	PITIVI_STOCK_EFFECT_SOUND,
	PITIVI_STOCK_EFFECT_TV
};

void
pitivi_stockicons_register (void)
{
  GtkIconFactory	*factory;
  int			i;
  
  factory = gtk_icon_factory_new ();
  gtk_icon_factory_add_default (factory);

  for (i = 0; i < (int) G_N_ELEMENTS (items); i++) {
    GtkIconSet *icon_set;
    GdkPixbuf *pixbuf;
    char *filename, *fullname;
		
    filename = g_strconcat ("../pixmaps/", items[i], ".png", NULL);
    fullname = g_strdup (filename);
    g_free (filename);
		
    pixbuf = gdk_pixbuf_new_from_file (fullname, NULL);
    g_free (fullname);

    icon_set = gtk_icon_set_new_from_pixbuf (pixbuf);
    gtk_icon_factory_add (factory, items[i], icon_set);
    gtk_icon_set_unref (icon_set);

    g_object_unref (G_OBJECT (pixbuf));
  }
	
  g_object_unref (G_OBJECT (factory));
}
