/* 
 * PiTiVi
 * Copyright (C) <2004>	 Guillaume Casanova <casano_g@epita.fr>
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
#include "pitivi-debug.h"
#include "pitivi-sourcefile.h"
#include "pitivi-effectswindow.h"
#include "pitivi-timelinewindow.h"
#include "pitivi-timelinecellrenderer.h"
#include "pitivi-timelinemedia.h"
#include "pitivi-dragdrop.h"
#include "pitivi-toolbox.h"
#include "pitivi-drawing.h"

void
pitivi_timelinecellrenderer_button_zooming_x (PitiviTimelineWindow *timewin, PitiviTimelineCellRenderer *self, PitiviCursor *cursor)
{
  GtkWidget *container = (GtkWidget *) pitivi_timelinewindow_get_container(timewin);
  if (cursor->type == PITIVI_CURSOR_ZOOM || cursor->type == PITIVI_CURSOR_ZOOM_INC)
    {
      if (timewin->zoom >= 16)
	{
	  load_cursor (GDK_WINDOW(container->window), cursor,  PITIVI_CURSOR_ZOOM_DEC);
	  timewin->zoom/=2;
	}
      else
	timewin->zoom*=2;
    }
  else if (cursor->type == PITIVI_CURSOR_ZOOM_DEC)
    {
      if (timewin->zoom - 2 > 0)
	timewin->zoom/=2;
      else
	timewin->zoom = 1;
      if ( timewin->zoom <= 1)
	load_cursor (GDK_WINDOW(container->window), cursor,  PITIVI_CURSOR_ZOOM_INC);
    }
  pitivi_timelinewindow_zoom_changed ( timewin );
  pitivi_ruler_set_zoom_metric (GTK_RULER ( timewin->hruler ),
				timewin->unit, timewin->zoom);
}

void
pitivi_timelinecellrenderer_button_zooming_unit (PitiviTimelineWindow *timewin, PitiviTimelineCellRenderer *self, PitiviCursor *cursor)
{
  if (timewin->unit + 1 == PITIVI_LAST_UNIT)
    timewin->unit = PITIVI_SECONDS;
  else
    timewin->unit++;
  pitivi_timelinewindow_zoom_changed ( timewin );
  pitivi_ruler_set_zoom_metric (GTK_RULER ( timewin->hruler ),
				timewin->unit, timewin->zoom);
}


/*
  convert_pix_time
  Converts given pixel position into nanosecond time,
	depends on the zoom level, and the unit of the ruler
*/

gint64
convert_sub_pix_time (guint pos,
		      guint unit,
		      guint zoom,
		      gdouble videorate)
{
  gint64 res;

  switch ( unit ) {
  case PITIVI_SECONDS:
    res = (pos / zoom) * GST_SECOND;
    break;
  case PITIVI_FRAMES:
    res = (pos * GST_SECOND)
      / (((gint64) videorate * zoom));
    break;
  case PITIVI_NANOSECONDS:
  default:
    res = pos;
    break;
  }
  return res;
}

/**
 * pitivi_timelinecellrenderer_zoom_changed:
 * @PitiviTimelineCellRenderer: the timelinecellrenderer
 *
 * Update the track with the new zoom settings
 *
 */

void
pitivi_timelinecellrenderer_zoom_changed (PitiviTimelineCellRenderer *self)
{
  GList	*child;
  GnlObject	*source;
  gint64	start,stop,mstart,mstop;
  
  // redraw all childs at the good position and at the good width
  for (child = gtk_container_get_children(GTK_CONTAINER(self)); child; child = child->next) {
    if (PITIVI_IS_TIMELINEMEDIA(child->data)) {
      // get the child time position, it's length
      source = PITIVI_TIMELINEMEDIA(child->data)->sourceitem->gnlobject;
      start = GNL_OBJECT(source)->start;
      stop = GNL_OBJECT(source)->stop;
      gnl_object_get_start_stop(GNL_OBJECT(source), &mstart, &mstop);
      // resize the child
      pitivi_media_set_size(GTK_WIDGET (child->data),
			    convert_time_pix(self, mstop-mstart));
      // move it to the good position
      pitivi_layout_move(GTK_LAYOUT(self), GTK_WIDGET(child->data), 
			 convert_time_pix(self, start) ,0);
      if ((start != GNL_OBJECT(source)->start) || (stop != GNL_OBJECT(source)->stop))
	PITIVI_WARNING ("%s was at %03lld:%02lld:%03lld -> %03lld:%02lld:%03lld  and is now at %03lld:%02lld:%03lld -> %03lld:%02lld:%03lld",
			gst_element_get_name(GST_ELEMENT(source)),
			GST_M_S_M(start), GST_M_S_M(stop),
			GST_M_S_M(GNL_OBJECT(source)->start), GST_M_S_M(GNL_OBJECT(source)->stop));
    }
  }
}
