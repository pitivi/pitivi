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

#include "pitivi-timelinecellrenderer.h"
#include "pitivi-timelinemedia.h"

/*
 **********************************************************
 * Resizing  			                          *
 *							  *
 **********************************************************
*/

static void
pitivi_timelinecellrenderer_resize_operation (PitiviTimelineMedia *source, guint decrement, guint x, gboolean sens)
{
  if (!sens) /* droite */
    {
      if (x < GTK_WIDGET (source)->allocation.width + GTK_WIDGET (source)->allocation.x - (decrement))
	{
	  if (GTK_WIDGET (source)->allocation.width-decrement >= 1)
	    gtk_widget_set_size_request (GTK_WIDGET (source),
					 GTK_WIDGET (source)->allocation.width-decrement,
					 GTK_WIDGET (source)->allocation.height);
	}
      else if (x > GTK_WIDGET (source)->allocation.width + GTK_WIDGET (source)->allocation.x)
	{
	  if (source->original_width > GTK_WIDGET (source)->allocation.width)
	    {
	      if (!source->next || (source->next && x < GTK_WIDGET (source->next)->allocation.x))
		gtk_widget_set_size_request (GTK_WIDGET (source),
					     GTK_WIDGET (source)->allocation.width+decrement,
					     GTK_WIDGET (source)->allocation.height);
	    }
	}
    }
  else /* gauche */
    {
      if (x > GTK_WIDGET (source)->allocation.x + (decrement))
	{
	  if (GTK_WIDGET (source)->allocation.width-decrement  >= 1)
	    {
	      gtk_widget_set_size_request (GTK_WIDGET (source),
					   GTK_WIDGET (source)->allocation.width-decrement,
					   GTK_WIDGET (source)->allocation.height);
	      gtk_layout_move (GTK_LAYOUT (source->track),  GTK_WIDGET ( source ), GTK_WIDGET (source)->allocation.x+decrement, 0);
	    }
	}
      else if ( x < GTK_WIDGET (source)->allocation.x )
	{
	  if (source->original_width > GTK_WIDGET (source)->allocation.width)
	    {
	      if (!source->prev || (source->prev && x >= GTK_WIDGET (source->prev)->allocation.x+GTK_WIDGET (source->prev)->allocation.width))
		{
		  gtk_layout_move (GTK_LAYOUT (source->track),  GTK_WIDGET ( source ), GTK_WIDGET (source)->allocation.x-decrement, 0);
		  gtk_widget_set_size_request (GTK_WIDGET (source),
					       GTK_WIDGET (source)->allocation.width+decrement,
					       GTK_WIDGET (source)->allocation.height);
		}
	    }
	}
    }
}

void
pitivi_timelinecellrenderer_resizing_media (PitiviTimelineMedia *source, 
					    PitiviTimelineCellRenderer *self, 
					    guint decrement, 
					    guint x)
{
  GList *effects;
  GtkWidget *media_effect;
  
  pitivi_timelinecellrenderer_resize_operation (source, decrement, x, source->resz);
  if (source->linked)
    pitivi_timelinecellrenderer_resize_operation (PITIVI_TIMELINEMEDIA (source->linked), decrement, x, source->resz);
  if (source->effectschilds)
    {
      effects = g_list_last (source->effectschilds);
      media_effect = GTK_WIDGET ( effects->data );
      pitivi_timelinecellrenderer_resize_operation (PITIVI_TIMELINEMEDIA ( media_effect ), decrement, x, source->resz);
    }
}

static void
pitivi_timelinecellrenderer_gnonlin_resize (PitiviTimelineMedia *source, gint64 new_stop, gboolean sens)
{
  gint64 start, stop, mstart, mstop;
  
  if ( sens )
    {
      if (source->track) {
	pitivi_timelinemedia_put (source, 
				  convert_pix_time(source->track, GTK_WIDGET (source)->allocation.x));
      }
    }
  /* resizing gnonlin */
  pitivi_timelinemedia_get_start_stop( source, &start, &stop);
  pitivi_timelinemedia_get_media_start_stop ( source, &mstart, &mstop);
  
  pitivi_timelinemedia_set_start_stop ( source, start, new_stop );
  pitivi_timelinemedia_set_media_start_stop ( source, mstart, mstart + (new_stop - start));
}

void pitivi_timelinecellrenderer_resize (PitiviTimelineCellRenderer *self, PitiviTimelineMedia *media)
{
  GList *effects;
  gint64 new_stop;
  gint new_width;

  new_width = GTK_WIDGET (media)->allocation.x + GTK_WIDGET (media)->allocation.width;
  new_stop = convert_pix_time(self, new_width );
  pitivi_timelinecellrenderer_gnonlin_resize (media, new_stop, media->resz);
  if (media->linked)
    pitivi_timelinecellrenderer_gnonlin_resize ( media->linked, new_stop, media->resz);
  if (media->effectschilds)
    {
      effects = g_list_last (media->effectschilds);
      pitivi_timelinecellrenderer_gnonlin_resize (PITIVI_TIMELINEMEDIA ( effects->data ), new_stop, media->resz);
    }
}

void
pitivi_media_set_size (GtkWidget *widget, guint width)
{
  gint real_width;

  gtk_widget_set_size_request (widget, width, widget->allocation.height);
  if (PITIVI_IS_TIMELINEMEDIA (widget))
    {      
      PitiviTimelineMedia *media = PITIVI_TIMELINEMEDIA (widget);

      real_width = convert_time_pix (media->track, media->sourceitem->srcfile->length);
      media->original_width = real_width;
    }
}
