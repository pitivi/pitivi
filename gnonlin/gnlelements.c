/* GStreamer
 * Copyright (C) 1999,2000 Erik Walthinsen <omega@cse.ogi.edu>
 *                    2000 Wim Taymans <wtay@chello.be>
 *
 * gstelements.c:
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

#include <gst/gst.h>
#include "config.h"
#include "gnlsource.h"
#include "gnlcomposition.h"

struct _elements_entry {
  gchar *name;
  GType (*type) (void);
};


/*extern GType gst_filesrc_get_type(void);*/
/*extern GstElementDetails gst_filesrc_details;*/

static struct _elements_entry _elements[] = {
  { "gnlsource", 	gnl_source_get_type },
  { "gnlcomposition", 	gnl_composition_get_type },
  { NULL, 0 }
};

gboolean
gnl_elements_plugin_init (GstPlugin *plugin)
{
  gint i = 0;

  /*  gst_plugin_set_longname (plugin, "Standard GNL Elements");*/

  for ( ; _elements[i].name; i++ )
    if (!(gst_element_register(plugin,
			       _elements[i].name,
			       GST_RANK_NONE,
			       (_elements[i].type) () )))
      return FALSE;
	
  
  /*	factory = gst_element_factory_new (_elements[i].name,
	(_elements[i].type) (),
	_elements[i].details);
	
	if (!factory) {
	g_warning ("gst_element_factory_new failed for `%s'",
	_elements[i].name);
	continue;
  
  
	gst_plugin_add_feature (plugin, GST_PLUGIN_FEATURE (factory));
	if (_elements[i].factoryinit) {
	_elements[i].factoryinit (factory);
	}*/
  return TRUE;
}

/* GstPluginDesc plugin_desc = { */
/*   GST_VERSION_MAJOR, */
/*   GST_VERSION_MINOR, */
/*   "gnlelements", */
/*   gnl_elements_plugin_init */
/* }; */

GST_PLUGIN_DEFINE ( GST_VERSION_MAJOR, GST_VERSION_MINOR,
		    "gnlelements",
		    "Standard elements for nonlinear video editing",
		    gnl_elements_plugin_init,
		    VERSION,
		    "LGPL",
		    "Gnonlin",
		    "http://gnonlin.sf.net/")

