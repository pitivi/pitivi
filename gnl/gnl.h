/* Gnonlin
 * Copyright (C) <2001> Wim Taymans <wim.taymans@chello.be>
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

#ifndef __GNL_H__
#define __GNL_H__

#include <glib.h>
#include <gst/gst.h>
#include <gst/gsttypes.h>
#include "gnltypes.h"

G_BEGIN_DECLS

#define GST_CAT_DEFAULT gnonlin
GST_DEBUG_CATEGORY_EXTERN(GST_CAT_DEFAULT);

#define GST_M_S_M(stime) \
  (stime == GST_CLOCK_TIME_NONE) ? \
  -1 : (signed long long int) (stime / (GST_SECOND * 60)), \
  (stime == GST_CLOCK_TIME_NONE) ? \
  -1 : (signed long long int) ((stime % (GST_SECOND * 60)) / GST_SECOND), \
  (stime == GST_CLOCK_TIME_NONE) ? \
  -1 : (signed long long int) ((stime % GST_SECOND) / (GST_MSECOND))

/* initialize GNL */
void gnl_init(int *argc,char **argv[]);

void gnl_main		(void);
void gnl_main_quit	(void);

G_END_DECLS

#endif /* __GST_H__ */
