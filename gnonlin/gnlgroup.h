/* GStreamer
 * Copyright (C) 2001 Wim Taymans <wim.taymans@chello.be>
 *
 * gnlgroup.h: Header for base GnlGroup
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


#ifndef __GNL_GROUP_H__
#define __GNL_GROUP_H__

#include <gnl/gnlcomposition.h>

G_BEGIN_DECLS

#define GNL_TYPE_GROUP \
  (gnl_group_get_type())
#define GNL_GROUP(obj) \
  (G_TYPE_CHECK_INSTANCE_CAST((obj),GNL_TYPE_GROUP,GnlGroup))
#define GNL_GROUP_CLASS(klass) \
  (G_TYPE_CHECK_CLASS_CAST((klass),GNL_TYPE_GROUP,GnlGroupClass))
#define GNL_IS_GROUP(obj) \
  (G_TYPE_CHECK_INSTANCE_TYPE((obj),GNL_TYPE_GROUP))
#define GNL_IS_GROUP_CLASS(obj) \
  (G_TYPE_CHECK_CLASS_TYPE((klass),GNL_TYPE_GROUP))

typedef struct _GnlGroup GnlGroup;
typedef struct _GnlGroupClass GnlGroupClass;

struct _GnlGroup {
  GnlComposition	 parent;

  GList			*layers;
};

struct _GnlGroupClass {
  GnlCompositionClass	parent_class;
};

/* normal GGroup stuff */
GType		gnl_group_get_type		(void);
GnlGroup*	gnl_group_new			(const gchar *name);

void		gnl_group_append_layer		(GnlGroup *group, GnlComposition *layer);

G_END_DECLS


#endif /* __GNL_GROUP_H__ */

