/* GStreamer
 * Copyright (C) 2001 Wim Taymans <wim.taymans@chello.be>
 *
 * gnltimeline.h: Header for base GnlTimeline
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


#ifndef __GNL_TIMELINE_H__
#define __GNL_TIMELINE_H__

#include <gnl/gnl.h>
#include <gnl/gnlcomposition.h>
#include <gnl/gnlgroup.h>

G_BEGIN_DECLS

#define GNL_TYPE_TIMELINE \
  (gnl_timeline_get_type())
#define GNL_TIMELINE(obj) \
  (G_TYPE_CHECK_INSTANCE_CAST((obj),GNL_TYPE_TIMELINE,GnlTimeline))
#define GNL_TIMELINE_CLASS(klass) \
  (G_TYPE_CHECK_CLASS_CAST((klass),GNL_TYPE_TIMELINE,GnlTimelineClass))
#define GNL_IS_TIMELINE(obj) \
  (G_TYPE_CHECK_INSTANCE_TYPE((obj),GNL_TYPE_TIMELINE))
#define GNL_IS_TIMELINE_CLASS(obj) \
  (G_TYPE_CHECK_CLASS_TYPE((klass),GNL_TYPE_TIMELINE))

typedef struct _GnlTimeline GnlTimeline;
typedef struct _GnlTimelineClass GnlTimelineClass;
typedef struct _GnlTimelineTimer GnlTimelineTimer;

struct _GnlTimeline {
  GnlComposition	 parent;

  GList			*groups;
  GnlTimelineTimer 	*timer;
};

struct _GnlTimelineClass {
  GnlCompositionClass 	parent_class;
};

GType		gnl_timeline_get_type		(void);
GnlTimeline*	gnl_timeline_new		(const gchar *name);

void		gnl_timeline_add_group		(GnlTimeline *timeline, GnlGroup *group);

GstPad*		gnl_timeline_get_pad_for_group	(GnlTimeline *timeline, GnlGroup *group);

G_END_DECLS

#endif /* __GNL_TIMELINE_H__ */

