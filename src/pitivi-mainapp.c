/* 
 * PiTiVi
 * Copyright (C) <2004> Edward Hervey <hervey_e@epita.fr>
 *                      Bloch Stephan <bloch_s@epita.fr>
 *                      Carbon Julien <carbon_j@epita.fr>
 *                      Dubart Loic <dubart_l@epita.fr>
 *			Delettrez Marc <delett_m@epita.fr>
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

#include <unistd.h>
#include <gst/gst.h>
#include "pitivi.h"
#include "pitivi-mainapp.h"
#include "pitivi-newprojectwindow.h"
#include "pitivi-sourcelistwindow.h"
#include "pitivi-timelinewindow.h"
#include "pitivi-viewerwindow.h"
#include "pitivi-effectswindow.h"
#include "pitivi-projectsettings.h"
#include "pitivi-settings.h"
#include "pitivi-splashscreenwindow.h"

#define BORDER 10
#define BOTTOM2 42
#define BOTTOM 75

struct _PitiviMainAppPrivate
{
  /* instance private members */
  gboolean			dispose_has_run;
  PitiviNewProjectWindow	*win_new_project;

  PitiviSourceListWindow	*srclistwin;
  PitiviTimelineWindow		*timelinewin;
  PitiviViewerWindow		*viewerwin;
  PitiviEffectsWindow		*effectswin;  
  PitiviSplashScreenWindow	*splash_screen;
};


/*
 * forward definitions
 */
void			pitivi_mainapp_destroy			( GtkWidget *pWidget, gpointer pData );
void			pitivi_mainapp_add_newcategory		( PitiviMainApp *self, const gchar *cat_name);
void			pitivi_mainapp_add_settings		( PitiviMainApp *self, PitiviProjectSettings *new_setting, gint *position );
void			pitivi_mainapp_del_settings		( PitiviMainApp *self, gint *position );

/*
 * Insert "added-value" functions here
 */

/**
 * pitivi_mainapp_get_timelinewin:
 * @PitiviMainApp: The object containing all references of the application
 * 
 * Get the timeline's references 
 *
 * Returns: An element PitiviTimelineWindow, the timeline window
 */

PitiviTimelineWindow *
pitivi_mainapp_get_timelinewin(PitiviMainApp *self) {
  return (PitiviTimelineWindow *) self->private->timelinewin;
}

/**
 * pitivi_mainapp_get_viewerwin:
 * @PitiviMainApp: The object containing all references of the application
 * 
 * Get the timeline's references 
 *
 * Returns: An element PitiviViewerWindow, the viewer window
 */

PitiviViewerWindow *
pitivi_mainapp_get_viewerwin(PitiviMainApp *self) {
  return self->private->viewerwin;
}

/**
 * pitivi_mainapp_get_effectwin:
 * @PitiviMainApp: The object containing all references of the application
 * 
 * Get the timeline's references 
 *
 * Returns: An element PitiviEffectWindow, the effect window
 */

PitiviEffectsWindow *
pitivi_mainapp_get_effectswin(PitiviMainApp *self) {
  return self->private->effectswin;
}

void
pitivi_mainapp_destroy(GtkWidget *pWidget, gpointer pData)
{
  PitiviMainApp *mainapp = PITIVI_WINDOWS(pWidget)->mainapp;
  gchar	*conf;

  conf = g_strdup_printf("%s/.pitivi", g_get_home_dir());
  /* Save settings before exiting */
  if (pitivi_settings_save_to_file(mainapp->global_settings, conf) == FALSE)
    g_printf("Error saving configuration file");
  g_free(conf);
  gtk_main_quit();
}

void
pitivi_mainapp_callb_sourcelist (GtkWindow *win, gpointer data)
{
  PitiviMainApp *self = data;
  self->private->srclistwin = NULL;
}

void
pitivi_mainapp_callb_effects (GtkWindow *win, gpointer data)
{
  g_printf("removed the effects window...\n");
  PitiviMainApp *self = data;
  self->private->effectswin = NULL;
}

void
pitivi_mainapp_callb_viewer (GtkWindow *win, gpointer data)
{
  PitiviMainApp *self = data;
  self->private->viewerwin = NULL;
}

void
pitivi_mainapp_callb_timelinewin (GtkWindow *win, gpointer data)
{
  PitiviMainApp *self = data;
  self->private->timelinewin = NULL;
}

/**
 * pitivi_mainapp_activate_effectswindow:
 * @PitiviMainApp: The object containing all references of the application
 * @gboolean: A flag to control if the Effect Window is shown or not
 *
 * Activates the Effects Window
 *
 */

void
pitivi_mainapp_activate_effectswindow (PitiviMainApp *self, gboolean activate)
{
  if (self->private->effectswin)
    {
      gtk_window_get_position(GTK_WINDOW (self->private->effectswin), 
			      &self->private->effectswin->x, 
			      &self->private->effectswin->y);

      if (!activate)
	  gtk_widget_hide (GTK_WIDGET (self->private->effectswin));
      else
	{
	  gtk_window_move(GTK_WINDOW (self->private->effectswin), 
			  self->private->effectswin->x, 
			  self->private->effectswin->y);
	  gtk_widget_show (GTK_WIDGET (self->private->effectswin));
	}
    }
  else
    if (activate) {
      self->private->effectswin = pitivi_effectswindow_new(self);
      gtk_widget_show_all (GTK_WIDGET (self->private->effectswin) );
      gtk_window_move (GTK_WINDOW (self->private->effectswin), 720, 450);
      gtk_signal_connect (GTK_OBJECT (self->private->effectswin), "destroy"\
			  , GTK_SIGNAL_FUNC (pitivi_mainapp_callb_effects), self);
    }
}

/**
 * pitivi_mainapp_activate_sourcelistwindow:
 * @PitiviMainApp: The object containing all references of the application
 * @gboolean: A flag to control if the Effect Window is shown or not
 * 
 * Active the Sourcelist Window
 *
 */

void
pitivi_mainapp_activate_sourcelistwindow (PitiviMainApp *self, gboolean activate)
{
  if (self->private->srclistwin)
    {
      gtk_window_get_position(GTK_WINDOW (self->private->srclistwin), 
			      &self->private->srclistwin->x, 
			      &self->private->srclistwin->y);
      if (!activate)
	gtk_widget_hide (GTK_WIDGET (self->private->srclistwin));
      else
	{
	  gtk_window_move(GTK_WINDOW (self->private->srclistwin), 
			  self->private->srclistwin->x, 
			  self->private->srclistwin->y);
	  gtk_widget_show_all (GTK_WIDGET (self->private->srclistwin));
	}
    }
  else
    if (activate) {
      self->private->srclistwin = pitivi_sourcelistwindow_new(self, self->project);
      gtk_widget_show_all (GTK_WIDGET (self->private->srclistwin) );
      gtk_window_move (GTK_WINDOW (self->private->srclistwin), 0, 0);
      gtk_signal_connect (GTK_OBJECT (self->private->srclistwin), "destroy"\
			  , GTK_SIGNAL_FUNC (pitivi_mainapp_callb_sourcelist), self);
    }
}

/**
 * pitivi_mainapp_activate_viewerwindow:
 * @PitiviMainApp: The object containing all references of the application
 * @gboolean: A flag to control if the Effect Window is shown or not
 *
 * Active the Viewer Window
 *
 */

void
pitivi_mainapp_activate_viewerwindow (PitiviMainApp *self, gboolean activate)
{
  if (self->private->viewerwin)
    {
      gtk_window_get_position(GTK_WINDOW (self->private->viewerwin), 
			      &self->private->viewerwin->x, 
			      &self->private->viewerwin->y);
      if (!activate)
	gtk_widget_hide (GTK_WIDGET (self->private->viewerwin));
      else
	{
	  gtk_window_move(GTK_WINDOW (self->private->viewerwin), 
			  self->private->viewerwin->x, 
			  self->private->viewerwin->y);
	  gtk_widget_show (GTK_WIDGET (self->private->viewerwin));
	}
    }
  else
    {
      if (activate) {
	self->private->viewerwin = pitivi_viewerwindow_new(self);
	gtk_widget_show_all (GTK_WIDGET (self->private->viewerwin) );
	gtk_window_move (GTK_WINDOW (self->private->viewerwin), 0, 0);
	gtk_signal_connect (GTK_OBJECT (self->private->viewerwin), "destroy"\
			    , GTK_SIGNAL_FUNC (pitivi_mainapp_callb_viewer), self);
      }
    }
}

void
pitivi_mainapp_create_timelinewin (PitiviMainApp *self, PitiviProject *project)
{
  gint width;
  gint height;
  gint tmp_w;
  gint tmp_h;
  width = gdk_screen_width ();
  height = gdk_screen_height ();
    
  if (!GTK_IS_WIDGET (self->private->timelinewin))
    {
      self->private->timelinewin = pitivi_timelinewindow_new(self);
      gtk_widget_show_all (GTK_WIDGET (self->private->timelinewin));
      gtk_window_get_size (GTK_WINDOW (self->private->timelinewin), &tmp_w, &tmp_h);
      gtk_window_move (GTK_WINDOW (self->private->timelinewin), 0, (height - (tmp_h + BORDER + BOTTOM)));
      gtk_window_resize (GTK_WINDOW (self->private->timelinewin), (width - 250 -  (2 * BORDER)), (tmp_h));
      gtk_signal_connect (GTK_OBJECT (self->private->timelinewin), "destroy"\
			  , GTK_SIGNAL_FUNC (pitivi_mainapp_callb_timelinewin), self);
    }
  else {
    ((PitiviProjectWindows *) (self->private->timelinewin))->project = project;
    g_signal_emit_by_name (GTK_OBJECT (self->private->timelinewin), "activate");
  }
}

/**
 * pitivi_mainapp_create_wintools:
 * @PitiviMainApp: The object containing all references of the application
 * @PitiviProject: The object containing all references of the current project
 *
 * Set and show all the windows
 *
 */

void
pitivi_mainapp_create_wintools (PitiviMainApp *self, PitiviProject *project)
{
  gint width;
  gint height;
  gint tmp_w;
  gint tmp_h;
  gint tmp1_w;
  gint tmp1_h;

  width = gdk_screen_width ();
  height = gdk_screen_height ();

  /* The project is killed if a new one is created */  
  if (self->project) {
    exit(0);
  }
  self->project = project;
  
  /* Viewer Window */

  if (self->private->viewerwin == NULL)
    {
      self->private->viewerwin = pitivi_viewerwindow_new(self, project);
      gtk_widget_show_all (GTK_WIDGET (self->private->viewerwin) );
      gtk_window_move (GTK_WINDOW (self->private->viewerwin), (width - 400 + BORDER), 0);
      gtk_signal_connect (GTK_OBJECT (self->private->viewerwin), "destroy"\
			  , GTK_SIGNAL_FUNC (pitivi_mainapp_callb_viewer), self);
    }
  
  /* Timeline Window */
  pitivi_mainapp_create_timelinewin (self, project);
  
  /* Effect Window */

  if (self->private->effectswin == NULL) {
    pitivi_mainapp_activate_effectswindow(self, TRUE);
    gtk_window_get_size (GTK_WINDOW (self->private->effectswin), &tmp1_w, &tmp1_h);
    gtk_window_resize (GTK_WINDOW (self->private->effectswin), tmp1_w, 420);
    gtk_window_move (GTK_WINDOW (self->private->effectswin), 
		     (width - (tmp1_w + BORDER)), 
		     (height - (420 + BORDER + BOTTOM))
		     );
  }
  
  /* Source List Window */

  if (self->private->srclistwin == NULL)
    {
      self->private->srclistwin = pitivi_sourcelistwindow_new(self, project);
      gtk_widget_show_all (GTK_WIDGET (self->private->srclistwin) );
      gtk_window_move (GTK_WINDOW (self->private->srclistwin), 0, 0);
      gtk_window_get_size (GTK_WINDOW (self->private->srclistwin), &tmp_w, &tmp_h);
      gtk_signal_connect (GTK_OBJECT (self->private->srclistwin), "destroy"\
			  , GTK_SIGNAL_FUNC (pitivi_mainapp_callb_sourcelist), self);
    }
  
  gtk_window_set_transient_for (GTK_WINDOW (self->private->srclistwin), GTK_WINDOW (self->private->timelinewin));
  gtk_window_set_transient_for (GTK_WINDOW (self->private->effectswin), GTK_WINDOW (self->private->timelinewin));
  gtk_window_set_transient_for (GTK_WINDOW (self->private->viewerwin),  GTK_WINDOW (self->private->timelinewin));
}

/**
 * pitivi_mainapp_add_project:
 * @PitiviMainApp: The object containing all references of the application
 * @PitiviProject: The object containing all references of the current project
 *
 * Adds a PitiviProject to the list of projects handled by the application
 *
 */

gboolean
pitivi_mainapp_add_project(PitiviMainApp *self, PitiviProject *project)
{
  if (project == NULL)
    return FALSE;

  self->projects = g_list_append(self->projects, project);
  return TRUE;
}

/**
 * pitivi_mainapp_new:
 * 
 * Create a new instance for a new Object
 *
 * Returns: A PitiviMainApp pointer on the new main_app
 */

PitiviMainApp *
pitivi_mainapp_new (void)
{
  PitiviMainApp *mainapp;
  
  mainapp = (PitiviMainApp *) g_object_new (PITIVI_MAINAPP_TYPE, NULL);
  g_assert (mainapp != NULL);

  return mainapp;
}

static GObject *
pitivi_mainapp_constructor (GType type,
			    guint n_construct_properties,
			    GObjectConstructParam * construct_properties)
{
  PitiviMainApp	*self;
  gchar		*settingsfile;
  GObject	*obj;
  gint		width;
  gint		height;

  width = gdk_screen_width ();
  height = gdk_screen_height ();

  /* Invoke parent constructor. */
  PitiviMainAppClass *klass;
  GObjectClass *parent_class;
  klass = PITIVI_MAINAPP_CLASS (g_type_class_peek (PITIVI_MAINAPP_TYPE));
  parent_class = G_OBJECT_CLASS (g_type_class_peek_parent (klass));
  obj = parent_class->constructor (type, n_construct_properties,
				   construct_properties);
  
  /* do stuff. */
  self = (PitiviMainApp *) obj;
  /* Lancement du splash screen */
  self->private->splash_screen = pitivi_splashscreenwindow_new();
  usleep (10);
  /* Enregistrement des Icones */
  pitivi_splashscreenwindow_set_both (self->private->splash_screen, 
				      0.0, "Loading Register Stockicons");
  pitivi_stockicons_register ();
  pitivi_splashscreenwindow_set_both (self->private->splash_screen, 
				      0.2, "Loading Default Settings");
  /* Creation des settings globaux */
  pitivi_splashscreenwindow_set_both (self->private->splash_screen, 
				      0.4, "Loading Global Settings");

  
  settingsfile = g_strdup_printf("%s/.pitivi", g_get_home_dir());
  if ( g_file_test(settingsfile, G_FILE_TEST_EXISTS) )
    self->global_settings = pitivi_settings_load_from_file(settingsfile);
  else
    self->global_settings = pitivi_settings_new();
  g_free(settingsfile);
  
  pitivi_mainapp_create_timelinewin (self, NULL);
  /* Connection des Signaux */
  pitivi_splashscreenwindow_set_both (self->private->splash_screen, 
				      0.8, "Loading Signals");
  g_signal_connect(G_OBJECT(self->private->timelinewin), "delete_event",
		   G_CALLBACK(pitivi_mainapp_destroy), NULL);
  /* Launching RC Styles */
  gtk_rc_parse( "../ui/styles.rc" );
  /* finish */
  pitivi_splashscreenwindow_set_both (self->private->splash_screen, 
  				      1.0, "Loading Finished");
  return obj;
}

static void
pitivi_mainapp_instance_init (GTypeInstance * instance, gpointer g_class)
{
  PitiviMainApp			*self = (PitiviMainApp *) instance;

  self->private = g_new0 (PitiviMainAppPrivate, 1);

  /* initialize all public and private members to reasonable default values. */

  self->private->dispose_has_run = FALSE;

  /* If you need specific consruction properties to complete initialization, 
   * delay initialization completion until the property is set. 
   */
  self->projects = NULL;
}

static void
pitivi_mainapp_dispose (GObject * object)
{
  PitiviMainApp *self = PITIVI_MAINAPP (object);

  /* If dispose did already run, return. */
  if (self->private->dispose_has_run)
    return;

  /* Make sure dispose does not run twice. */
  self->private->dispose_has_run = TRUE;

  /* 
   * In dispose, you are supposed to free all types referenced from this 
   * object which might themselves hold a reference to self. Generally, 
   * the most simple solution is to unref all members on which you own a 
   * reference. 
   */

}

static void
pitivi_mainapp_finalize (GObject * object)
{
  PitiviMainApp *self = PITIVI_MAINAPP (object);

  /* 
   * Here, complete object destruction. 
   * You might not need to do much... 
   */
  
  g_object_unref (self->private->timelinewin);
  g_object_unref (self->private->win_new_project);
  g_free (self->private);
}

static void
pitivi_mainapp_set_property (GObject * object,
			     guint property_id,
			     const GValue * value, GParamSpec * pspec)
{

  switch (property_id)
    {
      /*   case PITIVI_MAINAPP_PROPERTY: { */
      /*     g_free (self->private->name); */
      /*     self->private->name = g_value_dup_string (value); */
      /*     g_print ("maman: %s\n",self->private->name); */
      /*   } */
      /*     break; */
    default:
      /* We don't have any other property... */
      g_assert (FALSE);
      break;
    }
}

static void
pitivi_mainapp_get_property (GObject * object,
			     guint property_id,
			     GValue * value, GParamSpec * pspec)
{

  switch (property_id)
    {
      /*  case PITIVI_MAINAPP_PROPERTY: { */
      /*     g_value_set_string (value, self->private->name); */
      /*   } */
      /*     break; */
    default:
      /* We don't have any other property... */
      g_assert (FALSE);
      break;
    }
}

static void
pitivi_mainapp_class_init (gpointer g_class, gpointer g_class_data)
{
  GObjectClass *gobject_class = G_OBJECT_CLASS (g_class);
/*   PitiviMainAppClass *klass = PITIVI_MAINAPP_CLASS (g_class); */

  gobject_class->constructor = pitivi_mainapp_constructor;
  gobject_class->dispose = pitivi_mainapp_dispose;
  gobject_class->finalize = pitivi_mainapp_finalize;

  gobject_class->set_property = pitivi_mainapp_set_property;
  gobject_class->get_property = pitivi_mainapp_get_property;

  /* Install the properties in the class here ! */
  /*   pspec = g_param_spec_string ("maman-name", */
  /*                                "Maman construct prop", */
  /*                                "Set maman's name", */
  /*                                "no-name-set" /\* default value *\/, */
  /*                                G_PARAM_CONSTRUCT_ONLY | G_PARAM_READWRITE); */
  /*   g_object_class_install_property (gobject_class, */
  /*                                    MAMAN_BAR_CONSTRUCT_NAME, */
  /*                                    pspec); */


}

GType
pitivi_mainapp_get_type (void)
{
  static GType type = 0;

  if (type == 0)
    {
      static const GTypeInfo info = {
	sizeof (PitiviMainAppClass),
	NULL,				/* base_init */
	NULL,				/* base_finalize */
	pitivi_mainapp_class_init,	/* class_init */
	NULL,				/* class_finalize */
	NULL,				/* class_data */
	sizeof (PitiviMainApp),
	0,				/* n_preallocs */
	pitivi_mainapp_instance_init	/* instance_init */
      };
      type = g_type_register_static (G_TYPE_OBJECT,
				     "PitiviMainAppType", &info, 0);
    }

  return type;
}
