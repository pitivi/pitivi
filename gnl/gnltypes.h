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

#ifndef __GNL_TYPES_H__
#define __GNL_TYPES_H__

typedef struct _GnlComposition GnlComposition;
typedef struct _GnlCompositionClass GnlCompositionClass;

typedef struct _GnlGroup GnlGroup;
typedef struct _GnlGroupClass GnlGroupClass;

typedef struct _GnlObject GnlObject;
typedef struct _GnlObjectClass GnlObjectClass;

typedef struct _GnlOperation GnlOperation;
typedef struct _GnlOperationClass GnlOperationClass;

typedef struct _GnlSource GnlSource;
typedef struct _GnlSourceClass GnlSourceClass;

typedef struct _GnlTimeline GnlTimeline;
typedef struct _GnlTimelineClass GnlTimelineClass;

#endif
