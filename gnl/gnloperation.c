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



#include "gnloperation.h"

static void 		gnl_operation_class_init 	(GnlOperationClass *klass);
static void 		gnl_operation_init 		(GnlOperation *operation);

static GnlObjectClass *parent_class = NULL;

GType
gnl_operation_get_type (void)
{
  static GType operation_type = 0;

  if (!operation_type) {
    static const GTypeInfo operation_info = {
      sizeof (GnlOperationClass),
      NULL,
      NULL,
      (GClassInitFunc) gnl_operation_class_init,
      NULL,
      NULL,
      sizeof (GnlOperation),
      32,
      (GInstanceInitFunc) gnl_operation_init,
    };
    operation_type = g_type_register_static (GNL_TYPE_OBJECT, "GnlOperation", &operation_info, 0);
  }
  return operation_type;
}

static void
gnl_operation_class_init (GnlOperationClass *klass)
{
  GObjectClass *gobject_class;
  GnlObjectClass        *gnlobject_class;

  gobject_class =       (GObjectClass*)klass;
  gnlobject_class =     (GnlObjectClass*)klass;

  parent_class = g_type_class_ref (GNL_TYPE_OBJECT);
}

static void
gnl_operation_init (GnlOperation *operation)
{
  operation->num_sinks = 0;
}

static void
gnl_operation_set_element (GnlOperation *operation, GstElement *element)
{
  const GList *walk;

  operation->element = element;

  gst_bin_add (GST_BIN (operation), element);

  walk = gst_element_get_pad_list (element);
  while (walk) {
    GstPad *pad = GST_PAD (walk->data);

    if (GST_PAD_IS_SRC(pad)) {
      operation->queue = gst_element_factory_make("queue", "operation-queue");
      gst_bin_add(GST_BIN (operation), operation->queue);
      gst_element_link(element, operation->queue);
      gst_element_add_ghost_pad (GST_ELEMENT (operation),
                                 gst_element_get_pad (operation->queue, "src"),
                                 gst_object_get_name (GST_OBJECT(pad)));
    } else {
      gst_element_add_ghost_pad (GST_ELEMENT (operation),
				 pad, gst_object_get_name (GST_OBJECT (pad)));
      operation->num_sinks++;
    }
    walk = g_list_next (walk);
  }

}

/**
 * gnl_operation_new:
 * @name: the name of the #GnlOperation to create
 * @element: the #GstElement which is to be the provider
 *
 * Returns: a newly allocated #GnlOperation, or NULL if the creation failed
 */

GnlOperation*
gnl_operation_new (const gchar *name, GstElement *element)
{
  GnlOperation *operation;

  g_return_val_if_fail (name != NULL, NULL);

  operation = g_object_new (GNL_TYPE_OPERATION, NULL);
  gst_object_set_name (GST_OBJECT (operation), name);

  gnl_operation_set_element (operation, element);

  return operation;
}

/**
 * gnl_operation_get_num_sinks:
 * @operation: A #GnlOperation
 *
 * Returns: The number of sink pads
 */

guint
gnl_operation_get_num_sinks (GnlOperation *operation)
{
  return operation->num_sinks; 
}



