/* GStreamer
 * Copyright (C) 2001 Wim Taymans <wim.taymans@chello.be>
 *
 * gnlcomposition.h: Header for base GnlComposition
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Library General Public
 * License as published by the Free Software Foundation; either
 * version 2 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Library General Public License for more details.
 *
 * You should have received a copy of the GNU Library General Public
 * License along with this library; if not, write to the
 * Free Software Foundation, Inc., 59 Temple Place - Suite 330,
 * Boston, MA 02111-1307, USA.
 */


#ifndef __GNL_COMPOSITION_H__
#define __GNL_COMPOSITION_H__

#include <glib/gprintf.h>

#include <gst/gst.h>
#include <gnl/gnl.h>
#include <gnl/gnltypes.h>
#include <gnl/gnlobject.h>

G_BEGIN_DECLS

#define GNL_TYPE_COMPOSITION \
  (gnl_composition_get_type())
#define GNL_COMPOSITION(obj) \
  (G_TYPE_CHECK_INSTANCE_CAST((obj),GNL_TYPE_COMPOSITION,GnlComposition))
#define GNL_COMPOSITION_CLASS(klass) \
  (G_TYPE_CHECK_CLASS_CAST((klass),GNL_TYPE_COMPOSITION,GnlCompositionClass))
#define GNL_IS_COMPOSITION(obj) \
  (G_TYPE_CHECK_INSTANCE_TYPE((obj),GNL_TYPE_COMPOSITION))
#define GNL_IS_COMPOSITION_CLASS(obj) \
  (G_TYPE_CHECK_CLASS_TYPE((klass),GNL_TYPE_COMPOSITION))

extern GstElementDetails gnl_composition_details;

typedef struct _GnlCompositionEntry GnlCompositionEntry;

typedef enum
{
  GNL_FIND_AT,
  GNL_FIND_AFTER,
  GNL_FIND_START,
} GnlFindMethod;

struct _GnlComposition {
  GnlObject		 parent;

  GList			*objects;

  GstClockTime	 	 next_stop;
  GList			*active_objects;
};

struct _GnlCompositionClass {
  GnlObjectClass	parent_class;

  GstClockTime		(*nearest_cover)	(GnlComposition *comp, 
		  				 GstClockTime start, GnlDirection direction);
};

GType			gnl_composition_get_type	(void);
GnlComposition*		gnl_composition_new		(const gchar *name);

void			gnl_composition_add_object 	(GnlComposition *comp, 
							 GnlObject *object); 
void			gnl_composition_remove_object 	(GnlComposition *comp, 
							 GnlObject *object); 

GnlObject*		gnl_composition_find_object	(GnlComposition *comp, 
							 GstClockTime time, GnlFindMethod method);

G_END_DECLS

#endif /* __GNL_COMPOSITION_H__ */

