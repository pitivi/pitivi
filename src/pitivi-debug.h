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

#ifndef __PITIVI_DEBUG_H__
#define __PITIVI_DEBUG_H__

#include <glib.h>
#include <gst/gst.h>

G_BEGIN_DECLS 

GST_DEBUG_CATEGORY_EXTERN (pitivi_debug_cat);

#ifdef G_HAVE_ISO_VARARGS
#define PITIVI_ERROR(...)       GST_CAT_ERROR (pitivi_debug_cat, __VA_ARGS__)
#define PITIVI_WARNING(...)     GST_CAT_WARNING (pitivi_debug_cat, __VA_ARGS__)
#define PITIVI_INFO(...)        GST_CAT_INFO (pitivi_debug_cat,  __VA_ARGS__)
#define PITIVI_DEBUG(...)       GST_CAT_DEBUG (pitivi_debug_cat, __VA_ARGS__)
#define PITIVI_LOG(...)         GST_CAT_LOG (pitivi_debug_cat, __VA_ARGS__)
#elif defined(G_HAVE_GNUC_VARARGS)
#define PITIVI_ERROR(args...)   GST_CAT_ERROR (pitivi_debug_cat, ##args)
#define PITIVI_WARNING(args...) GST_CAT_WARNING (pitivi_debug_cat, ##args)
#define PITIVI_INFO(args...)    GST_CAT_INFO (pitivi_debug_cat, ##args)
#define PITIVI_DEBUG(args...)   GST_CAT_DEBUG (pitivi_debug_cat, ##args)
#define PITIVI_LOG(args...)     GST_CAT_LOG (pitivi_debug_cat, ##args)
#endif

void pitivi_debug_init (void);

char *
pitivi_element_debug(GstElement *elt);

void
pitivi_printf_element(GstElement *elt);

void
print_element_schedulers(GstElement *element);

G_END_DECLS

#endif
