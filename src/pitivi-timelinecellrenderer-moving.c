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
 * Adding Widget  			                  *
 *							  *
 **********************************************************
*/

/* Comparaison */

gint 
compare_littlechild (gconstpointer a, gconstpointer b)
{
  GtkWidget *wa, *wb;
  
  wa = GTK_WIDGET (a);
  wb = GTK_WIDGET (b);
  
  if (wa->allocation.x > wb->allocation.x)
    return 1;
  else if (wa->allocation.x < wb->allocation.x)
    return -1;
  return 0;
}

gint
compare_bigchild (gconstpointer a, gconstpointer b)
{
  GtkWidget *wa, *wb;
  
  wa = GTK_WIDGET (a);
  wb = GTK_WIDGET (b);
  
  if (wa->allocation.x > wb->allocation.x)
    return -1;
  else if (wa->allocation.x < wb->allocation.x)
    return 1;
  return 0;
}

gint 
compare_track (gconstpointer a, gconstpointer b)
{
  GtkWidget *wa, *wb;
  
  wa = GTK_WIDGET (a);
  wb = GTK_WIDGET (b);
  
  if (wa->allocation.x > wb->allocation.x)
    return 1;
  else if (wa->allocation.x < wb->allocation.x)
    return -1;
  else if ( PITIVI_TIMELINEMEDIA (wa)->track->track_nb > PITIVI_TIMELINEMEDIA (wb)->track->track_nb )
    return 1;
  return 0;
}

void
assign_next_prev (PitiviTimelineCellRenderer *self)
{
  GList *childs;
  PitiviTimelineMedia *source;

  childs = gtk_container_get_children (GTK_CONTAINER (self));
  for (childs = g_list_sort (childs, compare_track); childs; childs = childs->next)
    {
      source = childs->data;
      if ( childs->next )
	source->next = PITIVI_TIMELINEMEDIA (childs->next->data);
      else
	source->next = NULL;
      if ( childs->prev )
	source->prev = PITIVI_TIMELINEMEDIA (childs->prev->data);
      else
	source->prev = NULL;
    }
  g_list_free (childs);
}

/**
 * pitivi_layout_put:
 * @GtkLayout: the layout to put the widgets into
 * @GtkWidget: the widget to put into the layout
 * @gint: the widget position in X 
 * @gint: the widget position in Y 
 * 
 * Adds the given widget to the layout at the given x/y position.
 * Updates the position of the attached GnlSource.
 *
 */

void
pitivi_layout_put (GtkLayout *layout, GtkWidget *widget, gint x, gint y)
{
  widget->allocation.x = x;
  widget->allocation.y = y;
  gtk_layout_put ( layout, widget, x, y );
  pitivi_calculate_priorities (GTK_WIDGET (layout) );
  if (PITIVI_IS_TIMELINEMEDIA(widget) && PITIVI_IS_TIMELINECELLRENDERER(layout))
    pitivi_timelinemedia_put (PITIVI_TIMELINEMEDIA(widget), 
			      convert_pix_time(PITIVI_TIMELINECELLRENDERER(layout), x));
}

/*
  pitivi_layout_move

  Moves the widget in the layout at the given x/y position
  Updates the position of the attached GnlSource
*/

void
pitivi_layout_move (GtkLayout *layout, GtkWidget *widget, gint x, gint y)
{
  widget->allocation.x = x;
  widget->allocation.y = y;
  gtk_layout_move (layout, widget, x, y);
  pitivi_calculate_priorities ( GTK_WIDGET (layout) );
  if (PITIVI_IS_TIMELINEMEDIA(widget) && PITIVI_IS_TIMELINECELLRENDERER(layout)) {
    pitivi_timelinemedia_put (PITIVI_TIMELINEMEDIA(widget), 
			      convert_pix_time(PITIVI_TIMELINECELLRENDERER(layout), x));
  }
}

void
link_widgets ( PitiviTimelineMedia *media1, PitiviTimelineMedia *media2)
{
  media1->linked = media2;
  media2->linked = media1;
}

void move_attached_effects (GtkWidget *widget, int x)
{
  PitiviTimelineMedia *media = (PitiviTimelineMedia *) widget;
  GList	*childs = media->effectschilds;
  int width = 0;

  while (childs)
    {
      pitivi_layout_move (GTK_LAYOUT (PITIVI_TIMELINEMEDIA (childs->data)->track), 
			  GTK_WIDGET (childs->data), x+width, 0);
      width += GTK_WIDGET (childs->data)->allocation.width;
      childs = childs->next;
    }
}

GtkWidget **layout_intersection_widget (GtkWidget *self, GtkWidget *widget, gint x, gboolean move)
{
  GList	*child;
  GtkRequisition req;
  GtkWidget **matches;
  int xchild, widthchild = 0;
  
  matches =  g_new0(GtkWidget *, (int) 2);
  gtk_widget_size_request (widget, &req);
  child = gtk_container_get_children (GTK_CONTAINER (self));
  for (child = g_list_sort (child, compare_littlechild); 
       child; 
       child = child->next )
    {
      xchild = GTK_WIDGET(child->data)->allocation.x;
      if (move && xchild == widget->allocation.x)
	continue;
      widthchild = GTK_WIDGET(child->data)->allocation.width;
      if (xchild <= x && x <= xchild + widthchild)
	matches[0] = GTK_WIDGET (child->data);
      else if (xchild <= x + req.width && x + req.width <= xchild + widthchild)
	matches[1] = GTK_WIDGET (child->data);
    }
  g_list_free (child);
  return matches;
}


void move_media (GtkWidget *cell, GtkWidget *widget, guint x, gboolean move)
{
  GtkWidget **intersec;
  GtkWidget *first;
  int       xbegin;

  intersec = layout_intersection_widget (cell, widget, x, move);
  first = intersec[1];
  if (first && GTK_IS_WIDGET (first) && first->allocation.x != x)
    {
      xbegin = x + first->allocation.width;
      pitivi_layout_move (GTK_LAYOUT (cell), first, xbegin, 0);
      move_attached_effects (first, xbegin);
      move_media (cell, first, xbegin, move);
    }
  return;
}

void
move_child_on_layout (GtkWidget *self, GtkWidget *widget, gint x)
{
  GtkWidget **intersec;
  int xbegin = x;
  
  intersec = layout_intersection_widget (self, widget, x, TRUE);
  if (!intersec[1] && intersec[0])
    {
      if ( x >=  intersec[0]->allocation.x &&
	   x <= intersec[0]->allocation.x+intersec[0]->allocation.width )
	xbegin = intersec[0]->allocation.x+intersec[0]->allocation.width;
      else
	xbegin = x;
      pitivi_layout_move (GTK_LAYOUT (self), widget, xbegin, 0);
      move_attached_effects (widget, xbegin);
    }
  else if (!intersec[0] && intersec[1])
    {
      move_media (self, widget, x, TRUE);
      pitivi_layout_move (GTK_LAYOUT (self), widget, x, 0);
    }
  else if (intersec[1] && intersec[0])
    {
      xbegin = intersec[0]->allocation.x+intersec[0]->allocation.width;
      pitivi_layout_move (GTK_LAYOUT (self), widget, xbegin, 0);
      move_media (self, widget, xbegin, TRUE);
      move_attached_effects (widget, x);
    }
  else
    {
      pitivi_layout_move (GTK_LAYOUT (self), widget, xbegin, 0);
      move_attached_effects (widget, xbegin);
    }
  assign_next_prev (PITIVI_TIMELINECELLRENDERER (self));
  g_free ( intersec );
}


/**
 * pitivi_add_to_layout:
 * @GtkWidget: the parent widget
 * @GtkWidget: the child widget
 * @gint: the position in x
 * @gint: the position in y
 *
 * Add a widget to the layer
 *
 * Returns: A flag setted to TRUE
 */

gboolean
pitivi_add_to_layout (GtkWidget *self, GtkWidget *widget, gint x, gint y)
{
  GtkWidget **intersec = layout_intersection_widget (self, widget, x, FALSE);
  PitiviTimelineMedia *right =  PITIVI_TIMELINEMEDIA (intersec[0]);
  PitiviTimelineMedia *left = PITIVI_TIMELINEMEDIA (intersec[1]);
  int xbegin = 0;
  
  if (!right && !left)
    pitivi_layout_put (GTK_LAYOUT (self), widget, x, 0);
  else if (!left) /* Case intersection right */
    {
      move_media (self, widget, x, FALSE);
      xbegin = intersec[0]->allocation.x+intersec[0]->allocation.width;
      pitivi_layout_put (GTK_LAYOUT (self), widget, xbegin, y);
    }
  else if (!right) /* Case intersection left */
    {
      move_media (self, GTK_WIDGET (left), x, FALSE);
      pitivi_layout_put (GTK_LAYOUT (self), widget, x, 0);
    }
  else if (right && left) /* Case intersection on left and right */
    { 
      xbegin = intersec[0]->allocation.x+intersec[0]->allocation.width;
      pitivi_layout_put (GTK_LAYOUT (self), widget, xbegin, 0);
      move_media (self, intersec[1], xbegin, FALSE);
    }
  assign_next_prev (PITIVI_TIMELINECELLRENDERER (self));
  g_free ( intersec );
  return TRUE;
}


/**
 * pitivi_calculate_priorities:
 * @GtkWidget: the widget containing a media source
 * 
 * Calculates the priorities of the media sources
 *
 */

void
pitivi_calculate_priorities ( GtkWidget *widget )
{
  PitiviTimelineCellRenderer *self = (PitiviTimelineCellRenderer *)widget;
  PitiviTimelineMedia *media;
  GList *containerlist = NULL;
  GList *layoutlist = NULL;
  GList *sublist = NULL;
  int	priority = 2;
  int   x, width = 0;
  gboolean found = FALSE;

  if (self->track_type == PITIVI_EFFECTS_TRACK)
    self = PITIVI_TIMELINECELLRENDERER (self->linked_track);
  containerlist = gtk_container_get_children (GTK_CONTAINER (gtk_widget_get_parent(GTK_WIDGET (self))));
  for (; containerlist; containerlist = containerlist->next)
    if (self->track_type == PITIVI_TIMELINECELLRENDERER (containerlist->data)->track_type)
      {
	if (!layoutlist)
	  {
	    layoutlist = gtk_container_get_children (GTK_CONTAINER (containerlist->data));
	    layoutlist = g_list_last  (layoutlist);
	  }
	else
	  layoutlist->next = gtk_container_get_children (GTK_CONTAINER (containerlist->data));
      }
  
  if ( layoutlist )
    {
      layoutlist = g_list_first (layoutlist);
      layoutlist = g_list_sort (layoutlist, compare_track);
      for (; layoutlist; layoutlist = layoutlist->next)
	{
	  media = layoutlist->data;
	  if ( media->track->effects_track)
	    {
	      found = FALSE;
	      sublist = gtk_container_get_children (GTK_CONTAINER (media->track->effects_track));
	      for (; sublist; sublist = sublist->next)
		{
		  x = GTK_WIDGET (sublist->data)->allocation.x;
		  width = GTK_WIDGET (sublist->data)->allocation.width;
		  if (GTK_WIDGET (media)->allocation.x <= x 
		      && (x-GTK_WIDGET (media)->allocation.x)+width<=GTK_WIDGET (media)->allocation.width)
		    {
		      pitivi_timelinemedia_set_priority ( PITIVI_TIMELINEMEDIA (sublist->data), priority);
		      found = TRUE;
		    }
		}
	      if ( found )
		priority++;
	    }
	  if ( media && media->track->track_type != PITIVI_TRANSITION_TRACK)
	    {
	      pitivi_timelinemedia_set_priority ( media, priority);
	      priority++;
	    }
	}
    }
  g_list_free (containerlist);
  g_list_free (layoutlist);
  g_list_free (sublist);
}
