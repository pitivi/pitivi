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

#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

#include <glib.h>
#include <glib/gprintf.h>
#include <gst/gst.h>

#include "pitivi-debug.h"

GST_DEBUG_CATEGORY (pitivi_debug_cat);

void
pitivi_debug_init (void)
{
  GST_DEBUG_CATEGORY_INIT (pitivi_debug_cat, "PITIVI", 0, "PiTiVi messages");
}


char *
pitivi_element_debug(GstElement *elt) {
  return g_strdup_printf("\"%s\" [%s]", 
			 gst_element_get_name(elt),
			 gst_plugin_feature_get_name(GST_PLUGIN_FEATURE(gst_element_get_factory(elt))));
}


static void
pitivi_printf_element_nb(GstElement *elt, int dep) {
  GstScheduler	*msched;
  const GList		*pads, *childs, *pads2;
  GstPad	*pad, *gpad;
  GstElement	*child;
  char	*tp;
  char	*pd = "";

  tp = g_strnfill((gsize) dep + 1, '.');
  /* Global info about element */
  PITIVI_DEBUG("%sElement : %s State:%d\n", tp, pitivi_element_debug(elt),
	   gst_element_get_state (elt));

  /* Element Scheduler and state */
  msched = GST_ELEMENT_SCHED(elt);
  PITIVI_DEBUG("%s\tScheduler %p State:%d\n", tp, msched, (msched ? GST_SCHEDULER_STATE(msched) : 0));

  /* State of Pads (Active/Linked) */
  for (pads = gst_element_get_pad_list(elt); pads ; pads = pads->next) {
    pad = GST_PAD(pads->data);
    if (GST_IS_GHOST_PAD(pad))
      pd = "Ghost";
    else
      pd = "";
    if (GST_PAD_PEER(pad))
      PITIVI_DEBUG("%s\t%sPad: %s Active:%d Linked to %s:%s\n", tp, pd,
	       gst_pad_get_name(pad), GST_PAD_IS_ACTIVE(pad),
	       GST_DEBUG_PAD_NAME(GST_PAD_PEER(pad)));
    else
      PITIVI_DEBUG("%s\t%sPad: %s Active:%d NOT linked\n", tp, pd,
	       gst_pad_get_name(pad), GST_PAD_IS_ACTIVE(pad));
    for (pads2 = gst_pad_get_ghost_pad_list(pad); pads2; pads2 = pads2->next) {
      gpad = GST_PAD(pads2->data);
      if (GST_PAD_PEER(gpad))
	PITIVI_DEBUG("%s\t GhostPad %s:%s linked to %s:%s\n", tp,
		 GST_DEBUG_PAD_NAME(gpad),
		 GST_DEBUG_PAD_NAME(GST_PAD_PEER(gpad)));
      else
	PITIVI_DEBUG("%s\t GhostPad %s:%s NOT linked\n", tp, 
		 GST_DEBUG_PAD_NAME(gpad));
    }
  }

  /* If container, recursive call on children */
  if (GST_IS_BIN(elt)) {
    PITIVI_DEBUG("%s/ CHILDS \\\n", tp);
    for (childs = gst_bin_get_list(GST_BIN(elt)); childs; childs = childs->next) {
      child = GST_ELEMENT(childs->data);
      pitivi_printf_element_nb(child, dep+1);
    }
    PITIVI_DEBUG("%s\\       /\n", tp);
  }
  g_free(tp);
}

void
pitivi_printf_element(GstElement *elt) {
  pitivi_printf_element_nb(elt, 0);
}

void
print_element_schedulers(GstElement *element) {
  GList *sched;
  GstScheduler  *son;
  GstScheduler  *msch;

  msch = gst_element_get_scheduler(element);
  PITIVI_DEBUG("Schedulers in Element[%s](ElementState:%d)(SchedulerState:%d):\n",
           gst_element_get_name(element), gst_element_get_state(element),
	   msch->state);
  for (sched = gst_element_get_scheduler(element)->schedulers; sched;
       sched = sched->next) {
    son = (GstScheduler *) sched->data;
    
    PITIVI_DEBUG("\tScheduler[%s]:%p State=%d\n",
             gst_element_get_name(son->parent), son, son->state);
    PITIVI_DEBUG("/-------\\\n");
    print_element_schedulers(son->parent);
    PITIVI_DEBUG("\\-------/\n");
  }
}
