/* GStreamer
 * Copyright (C) 2001 Wim Taymans <wim.taymans@chello.be>
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

#include "config.h"
#include "gnlsource.h"
#include "gnloperation.h"
#include "gnlcomposition.h"

static GstElementDetails gnl_composition_details = GST_ELEMENT_DETAILS ( "GNL Composition",
		      "Filter/Editor",
		      "Combines GNL objects",
		      "Wim Taymans <wim.taymans@chello.be>"
		      );

static void		gnl_composition_base_init		(gpointer g_class);
static void 		gnl_composition_class_init 		(GnlCompositionClass *klass);
static void 		gnl_composition_init 			(GnlComposition *comp);
static void 		gnl_composition_dispose 		(GObject *object);
static void 		gnl_composition_finalize 		(GObject *object);

static GstElementStateReturn
			gnl_composition_change_state 		(GstElement *element);
	
static GnlObjectClass *parent_class = NULL;

void			gnl_composition_show	 		(GnlComposition *comp);

#define CLASS(comp)  GNL_COMPOSITION_CLASS (G_OBJECT_GET_CLASS (comp))

static gboolean         gnl_composition_query                	(GstElement *element, GstQueryType type,
		                                                 GstFormat *format, gint64 *value);

static gboolean 	gnl_composition_covers_func		(GnlObject *object, 
								 GstClockTime start, GstClockTime stop,
							 	 GnlCoverType type);
static gboolean 	gnl_composition_prepare			(GnlObject *object, GstEvent *event);
static GstClockTime 	gnl_composition_nearest_cover_func 	(GnlComposition *comp, GstClockTime start, 
								 GnlDirection direction);

static gboolean 	gnl_composition_schedule_entries 	(GnlComposition *comp, GstClockTime start,
								 GstClockTime stop, gint minprio, GstPad **pad);

void	composition_update_start_stop(GnlComposition *comp);

struct _GnlCompositionEntry
{
  GnlObject *object;
  gulong	starthandler;
  gulong	stophandler;
  gulong	priorityhandler;
  gulong	activehandler;
};

#define GNL_COMP_ENTRY(entry)		((GnlCompositionEntry *)entry)
#define GNL_COMP_ENTRY_OBJECT(entry)	(GNL_OBJECT (GNL_COMP_ENTRY (entry)->object))

GType
gnl_composition_get_type (void)
{
  static GType composition_type = 0;

  if (!composition_type) {
    static const GTypeInfo composition_info = {
      sizeof (GnlCompositionClass),
      (GBaseInitFunc) gnl_composition_base_init,
      NULL,
      (GClassInitFunc) gnl_composition_class_init,
      NULL,
      NULL,
      sizeof (GnlComposition),
      32,
      (GInstanceInitFunc) gnl_composition_init,
    };
    composition_type = g_type_register_static (GNL_TYPE_OBJECT, "GnlComposition", &composition_info, 0);
  }
  return composition_type;
}

static void
gnl_composition_base_init (gpointer g_class)
{
  GstElementClass *gstclass = GST_ELEMENT_CLASS (g_class);

  gst_element_class_set_details (gstclass, &gnl_composition_details);
}

static void
gnl_composition_class_init (GnlCompositionClass *klass)
{
  GObjectClass *gobject_class;
  GstElementClass *gstelement_class;
  GstBinClass *gstbin_class;
  GnlObjectClass *gnlobject_class;

  gobject_class    = (GObjectClass*)klass;
  gstelement_class = (GstElementClass*)klass;
  gstbin_class     = (GstBinClass*)klass;
  gnlobject_class  = (GnlObjectClass*)klass;

  parent_class = g_type_class_ref (GNL_TYPE_OBJECT);

  gobject_class->dispose 	 = gnl_composition_dispose;
  gobject_class->finalize 	 = gnl_composition_finalize;

  gstelement_class->change_state = gnl_composition_change_state;
  gstelement_class->query	 = gnl_composition_query;

  gstbin_class->add_element      = (void (*) (GstBin *, GstElement *))gnl_composition_add_object;
  gstbin_class->remove_element   = (void (*) (GstBin *, GstElement *))gnl_composition_remove_object;

  gnlobject_class->prepare       = gnl_composition_prepare;
  gnlobject_class->covers	 = gnl_composition_covers_func;

  klass->nearest_cover	 	 = gnl_composition_nearest_cover_func;
}


static void
gnl_composition_init (GnlComposition *comp)
{
  comp->objects = NULL;
  GNL_OBJECT(comp)->start = 0;
  GNL_OBJECT(comp)->stop = G_MAXINT64;
  comp->next_stop = 0;
  comp->active_objects = NULL;
  comp->to_remove = NULL;
}

static void
gnl_composition_dispose (GObject *object)
{
  GnlComposition *comp = GNL_COMPOSITION (object);
  GList *objects = comp->objects;
  GnlCompositionEntry *entry = NULL;

  GST_INFO("dispose");
  while (objects) {
    entry = (GnlCompositionEntry *) (objects->data);
    g_signal_handler_disconnect (entry->object,
				 entry->starthandler);
    g_signal_handler_disconnect (entry->object,
				 entry->stophandler);
    g_signal_handler_disconnect (entry->object,
				 entry->priorityhandler);
    g_signal_handler_disconnect (entry->object,
				 entry->activehandler);
    g_object_unref (entry->object);

    objects = g_list_next (objects);
  }

  G_OBJECT_CLASS (parent_class)->dispose (object);
}

static void
gnl_composition_finalize (GObject *object)
{
  GnlComposition *comp = GNL_COMPOSITION (object);
  GList *objects = comp->objects;
  GnlCompositionEntry *entry = NULL;

  GST_INFO("finalize");
  while (objects) {
    entry = (GnlCompositionEntry *) (objects->data);
    g_free (entry);
    objects = g_list_next (objects);
  }

  g_list_free (comp->objects);
  g_list_free (comp->active_objects);

  G_OBJECT_CLASS (parent_class)->finalize (object);
}

/*
 * gnl_composition_find_entry_priority:
 * @comp: The composition in which we're looking for an entry
 * @time: The time to start the search
 * @method: the #GnlFindMethod to use
 * @minpriority: The minimum priority to use
 *
 * Returns: The #GnlCompositionEntry found, or NULL if nothing was found
*/

static GnlCompositionEntry *
gnl_composition_find_entry_priority (GnlComposition *comp, GstClockTime time,
				     GnlFindMethod method, gint minpriority) {
  GList	*objects = comp->objects;
  GnlCompositionEntry	*tmp = NULL;

  GST_INFO ("Composition[%s], time[%lld:%lld:%lld], Method[%d], minpriority[%d]",
	    gst_element_get_name(GST_ELEMENT(comp)),
	    GST_M_S_M(time), method, minpriority);

  /*
    Take into account the fact that we now have to search for the lowest priority
  */

  if (method == GNL_FIND_AT) {
    while (objects) {
      GnlCompositionEntry *entry = (GnlCompositionEntry *) (objects->data);
      GstClockTime start, stop;
      
      if (entry->object->priority >= minpriority) {
	gnl_object_get_start_stop (entry->object, &start, &stop);
	GST_INFO("Comparing %s [%lld:%02lld:%03lld]->[%lld:%02lld:%03lld] priority:%d",
		 gst_element_get_name(GST_ELEMENT(entry->object)),
		 GST_M_S_M(start), GST_M_S_M(stop),
		 gnl_object_get_priority(entry->object));

	if ((start <= time && start + (stop - start) > time)
	    && (!tmp || (tmp && tmp->object->priority > entry->object->priority))) {
	  tmp = entry;
	  /*	  GST_INFO("found tmp[%s]", gst_element_get_name(GST_ELEMENT(tmp->object)));*/
	}
      }
      objects = g_list_next(objects);
    }
    return tmp;
  } else
    while (objects) {
      GnlCompositionEntry *entry = (GnlCompositionEntry *) (objects->data);
      GstClockTime start, stop;
      
      gnl_object_get_start_stop (entry->object, &start, &stop);
      
      if (entry->object->priority >= minpriority)
	switch (method) {
	case GNL_FIND_AFTER:
	  if (start >= time)
	    return entry;
	  break;
	case GNL_FIND_START:
	  if (start == time)
	    return entry;
	  break;
	default:
	  GST_WARNING ("%s: unkown find method", gst_element_get_name (GST_ELEMENT (comp)));
	  break;
	}
      objects = g_list_next(objects);
    }
  return NULL;
}

/*
  gnl_composition_find_entry

  Find the GnlCompositionEntry located AT/AFTER/START

*/

static GnlCompositionEntry*
gnl_composition_find_entry (GnlComposition *comp, GstClockTime time, GnlFindMethod method)
{
/*   GList *objects = comp->objects; */

  GST_INFO ("Composition[%s], time[%lld], Method[%d]",
	    gst_element_get_name(GST_ELEMENT(comp)),
	    time, method);

  return gnl_composition_find_entry_priority(comp, time, method, 1);
}

/**
 * gnl_composition_find_object:
 * @comp: The #GnlComposition to look into
 * @time: The time to start looking at
 * @method: The #GnlFindMethod used to look to the object
 *
 * Returns: The #GnlObject found , or NULL if none
 */

GnlObject*
gnl_composition_find_object (GnlComposition *comp, GstClockTime time, GnlFindMethod method)
{
  GnlCompositionEntry *entry;

  GST_INFO ("Composition[%s], time[%lld:%02lld:%03lld], Method[%d]",
	    gst_element_get_name(GST_ELEMENT(comp)),
	    GST_M_S_M(time), method);

  entry = gnl_composition_find_entry (comp, time, method);
  if (entry) {
    return entry->object;
  }

  return NULL;
}

/*
  GnlCompositionEntry comparision function

  Allows to sort by priority and THEN by time

  MODIFIED : sort by time and then by priority
*/

static gint 
_entry_compare_func (gconstpointer a, gconstpointer b)
{
  GnlObject *object1, *object2;
  GstClockTime start1, start2;
  gint res;
  long long int lres;

  object1 = ((GnlCompositionEntry *) a)->object;
  object2 = ((GnlCompositionEntry *) b)->object;

  start1 = object1->start;
  start2 = object2->start;

  lres = start1 - start2;

  if (lres < 0)
    res = -1;
  else {
    if (lres > 0)
      res = 1;
    else
      res = gnl_object_get_priority (object1) -
	gnl_object_get_priority (object2); 
  }

  return res;
}

/**
 * gnl_composition_new:
 * @name: the name of the composition
 *
 * Returns: an initialized #GnlComposition
 */

GnlComposition*
gnl_composition_new (const gchar *name)
{
  GnlComposition *comp;

  GST_INFO ("name[%s]", name);

  g_return_val_if_fail (name != NULL, NULL);

  comp = g_object_new (GNL_TYPE_COMPOSITION, NULL);
  gst_object_set_name (GST_OBJECT (comp), name);

  return comp;
}

void
child_priority_changed (GnlObject *object,  GParamSpec *arg, gpointer udata)
{
  GnlComposition *comp = GNL_COMPOSITION (udata);

  comp->objects = g_list_sort (comp->objects, _entry_compare_func);
}

void
child_start_stop_changed (GnlObject *object, GParamSpec *arg, gpointer udata)
{
  GnlComposition *comp = GNL_COMPOSITION (udata);

  comp->objects = g_list_sort (comp->objects, _entry_compare_func);
  composition_update_start_stop (comp);
}

void
child_active_changed (GnlObject *object, GParamSpec *arg, gpointer udata)
{
  GnlComposition *comp = GNL_COMPOSITION (udata);

  GST_INFO("%s : State of child %s has changed",
	   gst_element_get_name(GST_ELEMENT (comp)),
	   gst_element_get_name(GST_ELEMENT (object)));
  if (object->active) {
    GST_FLAG_UNSET (GST_ELEMENT (object), GST_ELEMENT_LOCKED_STATE);
    gst_element_set_state (GST_ELEMENT (object), GST_STATE_PAUSED);
    comp->active_objects = g_list_append (comp->active_objects, object);
    comp->to_remove = g_list_remove (comp->to_remove, object);
  } else {
    gst_element_set_state (GST_ELEMENT (object), GST_STATE_READY);
    GST_FLAG_SET (GST_ELEMENT (object), GST_ELEMENT_LOCKED_STATE);
    comp->active_objects = g_list_remove(comp->active_objects, object);
  }
}

/**
 * gnl_composition_add_object:
 * @comp: The #GnlComposition to add an object to
 * @object: The #GnlObject to add to the composition
 */

void
gnl_composition_add_object (GnlComposition *comp, GnlObject *object)
{
  GnlCompositionEntry *entry;

  GST_INFO("Composition[%s](Sched:%p) Object[%s](Sched:%p) Parent:%s Ref:%d",
	   gst_element_get_name(GST_ELEMENT (comp)),
	   GST_ELEMENT_SCHED (GST_ELEMENT (comp)),
	   gst_element_get_name(GST_ELEMENT (object)),
	   GST_ELEMENT_SCHED (GST_ELEMENT (object)),
	   (gst_element_get_parent(GST_ELEMENT(object)) ?
	    gst_element_get_name(gst_element_get_parent(GST_ELEMENT(object))):
	    "None"),
	   G_OBJECT(object)->ref_count);

  g_return_if_fail (GNL_IS_COMPOSITION (comp));

  if (GNL_IS_OBJECT(object)) {
/*     gst_object_ref(GST_OBJECT(object)); */
  
    entry = g_malloc (sizeof (GnlCompositionEntry));

    gst_object_ref (GST_OBJECT (object));
    gst_object_sink (GST_OBJECT (object));
    entry->object = object;

    object->comp_private = entry;

    if (gst_element_get_pad (GST_ELEMENT (object), "src") == NULL 
	&& GNL_IS_SOURCE (object)) {
      gnl_source_get_pad_for_stream (GNL_SOURCE (object), "src");
    }
  
    entry->priorityhandler = g_signal_connect(object, "notify::priority", G_CALLBACK (child_priority_changed), comp);
    entry->starthandler = g_signal_connect(object, "notify::start", G_CALLBACK (child_start_stop_changed), comp);
    entry->stophandler = g_signal_connect(object, "notify::stop", G_CALLBACK (child_start_stop_changed), comp);
    entry->activehandler = g_signal_connect(object, "notify::active", G_CALLBACK (child_active_changed), comp);
  
    comp->objects = g_list_insert_sorted (comp->objects, entry, _entry_compare_func);
  
    composition_update_start_stop (comp);
  }
  GST_BIN_CLASS(parent_class)->add_element(GST_BIN(comp), GST_ELEMENT(object)); 
  GST_INFO ("Added Object %s(Sched:%p) to Group (Sched:%p)",
	    gst_element_get_name (GST_ELEMENT (object)),
	    GST_ELEMENT_SCHED (GST_ELEMENT (object)),
	    GST_ELEMENT_SCHED (GST_ELEMENT (comp)));
}

static gint
find_function (GnlCompositionEntry *entry, GnlObject *to_find) 
{
  GST_INFO("comparing object:%p to_find:%p",
	   entry->object, to_find);
  if (entry->object == to_find)
    return 0;

  return 1;
}

/**
 * gnl_composition_remove_object:
 * @comp: The #GnlComposition to remove an object from
 * @object: The #GnlObject to remove from the composition
 */

void
gnl_composition_remove_object (GnlComposition *comp, GnlObject *object)
{
  GList *lentry;
  GnlCompositionEntry	*entry;

  GST_INFO("Composition[%s] Object[%s](Ref:%d)",
	   gst_element_get_name(GST_ELEMENT (comp)),
	   gst_element_get_name(GST_ELEMENT (object)),
	   G_OBJECT(object)->ref_count);

  g_return_if_fail (GNL_IS_COMPOSITION (comp));
  g_return_if_fail (GNL_IS_OBJECT (object));

  lentry = g_list_find_custom (comp->objects, object, (GCompareFunc) find_function);
  g_return_if_fail (lentry);

  entry = (GnlCompositionEntry *) lentry->data;
  g_signal_handler_disconnect (entry->object, entry->priorityhandler);
  g_signal_handler_disconnect (entry->object, entry->starthandler);
  g_signal_handler_disconnect (entry->object, entry->stophandler);
  g_signal_handler_disconnect (entry->object, entry->activehandler);

  comp->active_objects = g_list_remove (comp->active_objects, object);
  comp->objects = g_list_delete_link (comp->objects, lentry);

  g_free (lentry->data);
  composition_update_start_stop (comp);

  GST_BIN_CLASS (parent_class)->remove_element(GST_BIN (comp), GST_ELEMENT (object));
}

/*
  gnl_composition_schedule_object

  Schedules the give object from start to stop and sets the output pad to *pad.

  Returns : TRUE if the object was properly scheduled, FALSE otherwise
*/

static gboolean
gnl_composition_schedule_object (GnlComposition *comp, GnlObject *object,
				 GstClockTime start, GstClockTime stop,
				 GstPad **pad)
{

  GST_INFO("Comp[%s]/sched=%p  Object[%s] Start [%lld] Stop[%lld] sched(object)=%p IS_SCHED:%d",
	   gst_element_get_name(GST_ELEMENT(comp)),
	   GST_ELEMENT_SCHED(GST_ELEMENT(comp)),
	   gst_element_get_name(GST_ELEMENT(object)),
	   start, stop, GST_ELEMENT_SCHED(object), GST_IS_SCHEDULER(GST_ELEMENT_SCHED(object)));

  /* Activate object */
  gnl_object_set_active(object, TRUE);

  if (gst_element_get_parent (GST_ELEMENT (object)) == NULL) { 

    GST_INFO("Object has no parent, adding it to %s[Sched:%p]",
	     gst_element_get_name(GST_ELEMENT(comp)), GST_ELEMENT_SCHED(GST_ELEMENT(comp)));

    GST_BIN_CLASS (parent_class)->add_element (GST_BIN (comp), GST_ELEMENT (object));
  }

  gst_element_send_event (GST_ELEMENT (object),
			  gst_event_new_segment_seek (
						      GST_FORMAT_TIME |
						      GST_SEEK_METHOD_SET |
						      GST_SEEK_FLAG_FLUSH |
						      GST_SEEK_FLAG_ACCURATE,
						      start,
						      stop)
			  );
  *pad = gst_element_get_pad (GST_ELEMENT (object), "src");
  
  GST_INFO("end of gnl_composition_schedule_object");

  return TRUE;
}

/*
  gnl_composition_schedule_object

  Schedules the given operation from start to stop and sets *pad to the output pad

  Returns : TRUE if the operation was properly scheduled, FALSE otherwise
*/

static gboolean
gnl_composition_schedule_operation (GnlComposition *comp, GnlOperation *oper, 
				    GstClockTime start, GstClockTime stop,
				    GstPad **pad)
{
  const GList *pads;
  gint	minprio = GNL_OBJECT(oper)->priority;

  GST_INFO("Composition[%s]  Operation[%s] Start[%lld] Stop[%lld]",
	   gst_element_get_name(GST_ELEMENT(comp)),
	   gst_element_get_name(GST_ELEMENT(oper)),
	   start, stop);

  gnl_composition_schedule_object (comp, GNL_OBJECT (oper), start, stop, pad);

  pads = gst_element_get_pad_list (GST_ELEMENT (oper));
  while (pads) {
    GstPad *newpad = NULL;
    GstPad *sinkpad = GST_PAD (pads->data);

    pads = g_list_next (pads);

    if (GST_PAD_IS_SRC (sinkpad))
      continue;

    minprio += 1;
    gnl_composition_schedule_entries (comp, start, stop, minprio, &newpad);

    GST_INFO ("Linking source pad %s:%s to operation pad %s:%s",
	      GST_DEBUG_PAD_NAME (newpad),
	      GST_DEBUG_PAD_NAME (sinkpad));
    if (GST_PAD_PEER(newpad)) {
      GST_WARNING ("newpad %s:%s is still connected to %s:%s. Unlinking them !!",
		   GST_DEBUG_PAD_NAME(newpad),
		   GST_DEBUG_PAD_NAME(GST_PAD_PEER (newpad)));
      gst_pad_unlink (newpad, GST_PAD_PEER (newpad));
    }
    if (!gst_pad_link (newpad, sinkpad)) {
      GST_WARNING ("Couldn't link source pad to operation pad");
      return FALSE;
    }
    GST_INFO ("pads were linked with caps:%s",
	      gst_caps_to_string(gst_pad_get_caps(sinkpad)));
  }

  GST_INFO("Finished");
  return TRUE;
}

/*
  de-activates all active_objects
*/

void
gnl_composition_deactivate_childs (GList	*childs)
{
  GList	*tmp, *next;

  GST_INFO("deactivate childs %p", childs);
  for (next = NULL, tmp = childs; tmp; tmp = next) {
    next = g_list_next (tmp);
    gst_element_set_state(GST_ELEMENT (tmp->data), GST_STATE_READY );
    gnl_object_set_active(GNL_OBJECT (tmp->data), FALSE);
  }
}

/*
  gnl_composition_schedule_entries NEW_VERSION

  comp : the composition whose entries to schedule
  start, stop : the start and stop time of what to schedule
  minprio : the minimum priority to schedule
  *pad : the output pad

  Returns TRUE if the entries are scheduled and the pad is set
  Only schedules the next entry. If no entries left, reset comp->next_stop
*/

static gboolean
gnl_composition_schedule_entries(GnlComposition *comp, GstClockTime start, 
				 GstClockTime stop, gint minprio, GstPad **pad)
{
  gboolean res = TRUE;
  GnlObject	*obj, *tmp = NULL;
  GList		*list;
  GnlCompositionEntry	*compentry;

  GST_INFO("%s [%lld]->[%lld]  minprio[%d]",
	   gst_element_get_name(GST_ELEMENT(comp)),
	   start, stop, minprio);
  
  /* Find the object to schedule with a suitable priority */
  compentry = gnl_composition_find_entry_priority(comp, start, GNL_FIND_AT, minprio);

  if (!compentry)
    return FALSE;

  obj = compentry->object;

  /* 
     Find the following object
     
     Doesn't handle the GnlOperation correctly 
     The trick is to use the mininum priority to find the next stop for
       GnlOperation's input(s).
  */

  for ( list = comp->objects; list; list = g_list_next(list)) {
    tmp = (GnlObject *) ((GnlCompositionEntry *) list->data)->object;

    if (tmp == obj)
      continue;
    
    if (tmp->priority >= minprio) { /* Don't take objects less important than minprio*/

      if (tmp->start >= obj->stop) { /* There is a gap before the next object */
	GST_INFO("Gap before next object");
	break;
      }

      /* fact : tmp->start < obj->stop */

      if (((tmp->priority < obj->priority) && (tmp->stop > start))
	  ||
	  ((tmp->priority > obj->priority) && (tmp->stop >= obj->stop))) {
	/* There isn't any gap */
	GST_INFO("Obj-Tmp : %d || No gap, it's ok", 
		 obj->priority - tmp->priority);
	break;
      }

    }
  }

  if (list) {

    GST_INFO("next[%s] [%lld]->[%lld]",
	     gst_element_get_name(GST_ELEMENT(tmp)),
	     tmp->start, tmp->stop);
    if (tmp->priority > obj->priority)
      stop = obj->stop;
    else
      stop = MIN(tmp->start, stop);
  } else {
    stop = MIN(obj->stop, stop);
  }

  comp->next_stop = MIN(comp->next_stop, stop);

  GST_INFO("next_stop [%lld]", comp->next_stop);
  
  if (GNL_IS_OPERATION(obj))
    res = gnl_composition_schedule_operation(comp, GNL_OPERATION(obj), 
					     start, stop, pad);
  else
    res = gnl_composition_schedule_object(comp, obj, start, stop, pad);
 
  return res;
}

static gboolean
probe_fired (GstProbe *probe, GstData **data, gpointer user_data)
{
  GnlComposition *comp = GNL_COMPOSITION (user_data);
  gboolean res = TRUE;

  if (GST_IS_BUFFER (*data)) {
    GST_INFO ("Got a buffer, updating current_time");
    GNL_OBJECT (comp)->current_time = GST_BUFFER_TIMESTAMP (*data);
  }
  else {
    GST_INFO ("Got an Event : %d",
	      GST_EVENT_TYPE (*data));
    if (GST_EVENT_TYPE (*data) == GST_EVENT_EOS) {
      GST_INFO ("Got EOS, current_time is now previous stop",
		gst_element_get_name (GST_ELEMENT (comp)));
      GNL_OBJECT (comp)->current_time = comp->next_stop;
    }
  }
  GST_INFO("%s current_time [%lld] -> [%3lldH:%3lldm:%3llds:%3lld]", 
	   gst_element_get_name(GST_ELEMENT(comp)),
	   GNL_OBJECT (comp)->current_time,
	   GNL_OBJECT (comp)->current_time / (3600 * GST_SECOND),
	   GNL_OBJECT (comp)->current_time % (3600 * GST_SECOND) / (60 * GST_SECOND),
	   GNL_OBJECT (comp)->current_time % (60 * GST_SECOND) / GST_SECOND,
	   GNL_OBJECT (comp)->current_time % GST_SECOND / GST_MSECOND);

  return res;
}

static gboolean
gnl_composition_prepare (GnlObject *object, GstEvent *event)
{
  GnlComposition *comp = GNL_COMPOSITION (object);
  gboolean res;
  GstPad *pad = NULL;
  GstPad *ghost;
  GstClockTime	start_pos, stop_pos;
  GstProbe *probe;

  GST_INFO("BEGIN Object[%s] Event[%lld]->[%lld]",
	   gst_element_get_name(GST_ELEMENT(object)),
	   GST_EVENT_SEEK_OFFSET(event),
	   GST_EVENT_SEEK_ENDOFFSET(event));

  start_pos = GST_EVENT_SEEK_OFFSET (event);
  stop_pos  = GST_EVENT_SEEK_ENDOFFSET (event);
  comp->next_stop  = stop_pos;
  
  ghost = gst_element_get_pad (GST_ELEMENT (comp), "src");
  if (ghost) {    
    GST_INFO("Existing ghost pad and probe, NOT removing");
    /* Remove the GstProbe attached to this pad before deleting it */
    probe = gst_pad_get_element_private(ghost);
    gst_pad_remove_probe(GST_PAD (GST_PAD_REALIZE (ghost)), probe);
    gst_element_remove_pad (GST_ELEMENT (comp), ghost);
  }

  gnl_composition_deactivate_childs (comp->active_objects);
  comp->active_objects = NULL;
  
  /* Scbedule the entries from start_pos */

  res = gnl_composition_schedule_entries (comp, start_pos,
					  stop_pos, 1, &pad);

  if (GST_PAD_IS_LINKED(pad)) {
    GST_WARNING ("pad %s:%s returned by scheduling is connected to %s:%s",
		 GST_DEBUG_PAD_NAME(pad),
		 GST_DEBUG_PAD_NAME(GST_PAD_PEER(pad)));
    gst_pad_unlink (pad, GST_PAD_PEER (pad));
  }

  if (pad) {

    GST_INFO("Have a pad");

    GST_INFO ("Putting probe and ghost pad back");
    probe = gst_probe_new (FALSE, probe_fired, comp);
    ghost = gst_element_add_ghost_pad (GST_ELEMENT (comp), 
				       pad,
				       "src");
    if (!ghost)
      GST_WARNING ("Wasn't able to create ghost src pad for composition %s",
		   gst_element_get_name (GST_ELEMENT (comp)));
    gst_pad_set_element_private(ghost, (gpointer) probe);
    gst_pad_add_probe (GST_PAD (GST_PAD_REALIZE (ghost)), probe);
    GST_INFO ("Ghost src pad and probe created");
  }
  else {
    GST_WARNING("Haven't got a pad :(");
    res = FALSE;
  }

  GST_INFO ( "END %s: configured", 
	     gst_element_get_name (GST_ELEMENT (comp)));

  return res;
}

static gboolean
gnl_composition_covers_func (GnlObject *object, GstClockTime start, 
		       GstClockTime stop, GnlCoverType type)
{
  GnlComposition *comp = GNL_COMPOSITION (object);

  GST_INFO("Object:%s , START[%lld]/STOP[%lld], TYPE:%d",
	   gst_element_get_name(GST_ELEMENT(comp)),
	   start, stop, type);
  
  switch (type) {
  case GNL_COVER_ALL:
    GST_WARNING ("comp covers all, implement me");
    break;
  case GNL_COVER_SOME:
    GST_WARNING ("comp covers some, implement me");
    break;
  case GNL_COVER_START:
    if (gnl_composition_find_entry (comp, start, GNL_FIND_AT)) {
      GST_INFO("TRUE");
      return TRUE;
    };
    break;
  case GNL_COVER_STOP:
    if (gnl_composition_find_entry (comp, stop, GNL_FIND_AT)) {
      GST_INFO("TRUE");
      return TRUE;
    };
    break;
  default:
    break;
  }
  
  GST_INFO("FALSE");
  return FALSE;
}

static GstClockTime
gnl_composition_nearest_cover_func (GnlComposition *comp, GstClockTime time, GnlDirection direction)
{
  GList			*objects = comp->objects;
  
  GST_INFO("Object:%s , Time[%lld], Direction:%d",
	   gst_element_get_name(GST_ELEMENT(comp)),
	   time, direction);
  
  if (direction == GNL_DIRECTION_BACKWARD) {
    GnlCompositionEntry	*entry;
    GnlObject	*endobject = NULL;
    
    /* 
       Look for the last object whose stop is < time
       return the stop time for that object
    */
    
    for (objects = g_list_last(comp->objects); objects; objects = objects->prev) {
      entry = (GnlCompositionEntry *) (objects->data);
      
      if (endobject) {
	if (entry->object->stop < endobject->start)
	  break;
	if (entry->object->stop > endobject->stop)
	  endobject = entry->object;
      } else if (entry->object->stop < time)
	endobject = entry->object;
      // if theres a endobject
      //   if the object ends later than the endobject it becomes the endobject
      //   if the object ends earlier than the endobject->start break !
      // else
      //   if object->stop < time
      //     it becomes the end object
    }
    if (endobject) {
      GST_INFO("endobject [%lld]->[%lld]",
	       endobject->start,
	       endobject->stop);
      return (endobject->stop);
    } else
      GST_INFO("no endobject");
  } else {
    GnlCompositionEntry *entry;
    GstClockTime	last = G_MAXINT64;
    while (objects) {
      entry = (GnlCompositionEntry *) (objects->data);
      GstClockTime start;
      
      start = entry->object->start;
      
      GST_INFO("Object[%s] Start[%lld]",
	       gst_element_get_name(GST_ELEMENT(entry->object)),
	       start);
      
      if (start >= time) {
	if (direction == GNL_DIRECTION_FORWARD)
	  return start;
	else
	  return last;
      }
      last = start;
      
      objects = g_list_next (objects);
    }
  }
  
  return GST_CLOCK_TIME_NONE;
}

GstClockTime
gnl_composition_nearest_cover (GnlComposition *comp, GstClockTime start, GnlDirection direction)
{
  g_return_val_if_fail (GNL_IS_COMPOSITION (comp), FALSE);

  GST_INFO("Object:%s , Time[%lld], Direction:%d",
	   gst_element_get_name(GST_ELEMENT(comp)),
	   start, direction);

  if (CLASS (comp)->nearest_cover)
    return CLASS (comp)->nearest_cover (comp, start, direction);

  return GST_CLOCK_TIME_NONE;
}

static gboolean
gnl_composition_query (GstElement *element, GstQueryType type,
		       GstFormat *format, gint64 *value)
{
  gboolean res = FALSE;

  GST_INFO("Object:%s , Type[%d], Format[%d]",
	   gst_element_get_name(element),
	   type, *format);

  if (*format != GST_FORMAT_TIME)
    return res;

  switch (type) {
  default:
    res = GST_ELEMENT_CLASS (parent_class)->query (element, type, format, value);
      break;
  }
  return res;
}

/*
  update_start_stop

  Updates the composition's start and stop value
  Should be updated if an object has been added or it's start/stop has been modified
*/

void
composition_update_start_stop (GnlComposition *comp)
{
  GstClockTime	start, stop;
  
  start = gnl_composition_nearest_cover (comp, 0, GNL_DIRECTION_FORWARD);
  if (start == GST_CLOCK_TIME_NONE)
    start = 0;
  stop = gnl_composition_nearest_cover (comp, G_MAXINT64, GNL_DIRECTION_BACKWARD);
  if (stop == GST_CLOCK_TIME_NONE)
    stop = G_MAXINT64;
  GST_INFO("Start_pos:%lld, Stop_pos:%lld", 
	   start, 
	   stop);
  gnl_object_set_start_stop(GNL_OBJECT(comp), start, stop);
}

static GstElementStateReturn
gnl_composition_change_state (GstElement *element)
{
  GnlComposition *comp = GNL_COMPOSITION (element);
  gint transition = GST_STATE_TRANSITION (comp);
  GstElementStateReturn	res;

  switch (transition) {
  case GST_STATE_NULL_TO_READY:
    //composition_update_start_stop(comp);
    break;
  case GST_STATE_READY_TO_PAUSED:
    GST_INFO ( "%s: 1 ready->paused", gst_element_get_name (GST_ELEMENT (comp)));
    break;
  case GST_STATE_PAUSED_TO_PLAYING:
    GST_INFO ( "%s: 1 paused->playing", gst_element_get_name (GST_ELEMENT (comp)));
    break;
  case GST_STATE_PLAYING_TO_PAUSED:
    GST_INFO ( "%s: 1 playing->paused", gst_element_get_name (GST_ELEMENT (comp)));
    break;
  case GST_STATE_PAUSED_TO_READY:
    gnl_composition_deactivate_childs (comp->active_objects);
    /* De-activate ghost pad */
    if (gst_element_get_pad (element, "src")) {
      gst_pad_remove_probe (GST_PAD_REALIZE (gst_element_get_pad (element, "src")),
			    (GstProbe *) gst_pad_get_element_private (gst_element_get_pad (element, "src")));
      gst_element_remove_pad (element, gst_element_get_pad (element, "src"));
    }
    comp->active_objects = NULL;
    break;
  default:
    break;
  }
  
  res = GST_ELEMENT_CLASS (parent_class)->change_state (element);
  GST_INFO("%s : change_state returns %d",
	   gst_element_get_name(element),
	   res);
  return res;
}

