/* GStreamer
 * Copyright (C) 2001 Wim Taymans <wim.taymans@chello.be>
 *
 * gnlobject.h: Header for base GnlObject
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


#ifndef __GNL_OBJECT_H__
#define __GNL_OBJECT_H__

#include <gst/gst.h>

G_BEGIN_DECLS

#define GNL_TYPE_OBJECT \
  (gnl_object_get_type())
#define GNL_OBJECT(obj) \
  (G_TYPE_CHECK_INSTANCE_CAST((obj),GNL_TYPE_OBJECT,GnlObject))
#define GNL_OBJECT_CLASS(klass) \
  (G_TYPE_CHECK_CLASS_CAST((klass),GNL_TYPE_OBJECT,GnlObjectClass))
#define GNL_IS_OBJECT(obj) \
  (G_TYPE_CHECK_INSTANCE_TYPE((obj),GNL_TYPE_OBJECT))
#define GNL_IS_OBJECT_CLASS(obj) \
  (G_TYPE_CHECK_CLASS_TYPE((klass),GNL_TYPE_OBJECT))

extern GstElementDetails gnl_object_details;
gboolean gnl_object_factory_init (GstElementFactory *factory);

typedef enum {
  GNL_OBJECT_INVALID_RATE_CONTROL = 0,
  GNL_OBJECT_FIX_MEDIA_STOP = 1,
  GNL_OBJECT_USE_MEDIA_STOP = 2,
} GnlObjectRateControl;
		
typedef enum
{
  GNL_COVER_ALL,
  GNL_COVER_SOME,
  GNL_COVER_START,
  GNL_COVER_STOP,
} GnlCoverType;

typedef enum
{
  GNL_DIRECTION_FORWARD,
  GNL_DIRECTION_BACKWARD,
} GnlDirection;

typedef struct _GnlObject GnlObject;
typedef struct _GnlObjectClass GnlObjectClass;

struct _GnlObject {
  GstBin 		 parent;

  GstClockTime  	 start;
  GstClockTime 		 stop;
  GstClockTime  	 media_start;
  GstClockTime 		 media_stop;
  gint			 priority;
  gboolean		 active;

  GnlObjectRateControl	 rate_control;
  GstClockTime  	 current_time;

  gpointer		 comp_private;
};

struct _GnlObjectClass {
  GstBinClass		parent_class;

  gboolean		(*prepare)		(GnlObject *object, GstEvent *event);
  gboolean		(*covers)		(GnlObject *object, 
		   				 GstClockTime start, GstClockTime stop, GnlCoverType);
  GstClockTime		(*nearest_change)	(GnlObject *object, GstClockTime time, 
		                                 GnlDirection direction);
};

/* normal GObject stuff */
GType			gnl_object_get_type		(void);

void			gnl_object_set_media_start_stop	(GnlObject *object, GstClockTime start, GstClockTime stop);
void			gnl_object_get_media_start_stop	(GnlObject *object, GstClockTime *start, GstClockTime *stop);
void			gnl_object_set_start_stop	(GnlObject *object, GstClockTime start, GstClockTime stop);
void			gnl_object_get_start_stop	(GnlObject *object, GstClockTime *start, GstClockTime *stop);
void			gnl_object_set_priority		(GnlObject *object, gint priority);
gint			gnl_object_get_priority		(GnlObject *object);

GnlObjectRateControl	gnl_object_get_rate_control	(GnlObject *object);
void			gnl_object_set_rate_control	(GnlObject *object, GnlObjectRateControl control);

gboolean		gnl_object_is_active		(GnlObject *object);
void			gnl_object_set_active		(GnlObject *object, gboolean active);

gboolean 		gnl_object_covers 		(GnlObject *object, GstClockTime start,
		                  			 GstClockTime stop, GnlCoverType type);
GstClockTime    	gnl_object_nearest_change 	(GnlObject *object, GstClockTime time, 
							 GnlDirection direction);


G_END_DECLS

#endif /* __GNL_OBJECT_H__ */

