#include <stdlib.h>
#include "gnl.h"

#define MAX_PATH_SPLIT	16

gchar *_gnl_progname;

GST_DEBUG_CATEGORY (GST_CAT_DEFAULT);

#if 0
extern gboolean gnl_elements_plugin_init (GstPlugin *plugin); 
 
static GstPluginDesc gnl_elements_plugin_desc = { 
  GST_VERSION_MAJOR, 
  GST_VERSION_MINOR, 
  "gnlelements", 
  "gnonlin pipeline handling elements",
  gnl_elements_plugin_init, NULL,
  "0.1", "LGPL", "gnonlin", "http://gnonlin.sf.net"
}; 
#endif


static gboolean 	gnl_init_check 		(int *argc, gchar ***argv);

/**
 * gnl_init:
 * @argc: pointer to application's argc
 * @argv: pointer to application's argv
 *
 * Initializes the GStreamer library, setting up internal path lists,
 * registering built-in elements, and loading standard plugins.
 */

void 
gnl_init (int *argc, char **argv[]) 
{
#if 0
  GstPlugin *plugin;
#endif

  GST_DEBUG_CATEGORY_INIT (gnonlin, "gnonlin", GST_DEBUG_FG_GREEN, "gnonlin non-linear library"); 
 
  if (!gnl_init_check (argc,argv)) {
    exit (0);
  }

  gst_init (argc, argv);

  gst_scheduler_factory_set_default_name ("opt");

#if 0
  plugin = gst_registry_pool_find_plugin ("gnlelements");
  if (plugin == NULL) {
    _gst_plugin_register_static (&gnl_elements_plugin_desc);
  }
#endif
}

/* returns FALSE if the program can be aborted */
static gboolean
gnl_init_check (int     *argc,
		gchar ***argv)
{
  gboolean ret = TRUE;

  _gnl_progname = NULL;

  if (argc && argv) {
    _gnl_progname = g_strdup(*argv[0]);
  }

  if (_gnl_progname == NULL) {
    _gnl_progname = g_strdup("gnlprog");
  }

  return ret;
}

/**
 * gnl_main:
 *
 * Enter the main GStreamer processing loop 
 */
void 
gnl_main (void) 
{

}

/**
 * gnl_main_quit:
 *
 * Exits the main GStreamer processing loop 
 */
void 
gnl_main_quit (void) 
{

}

