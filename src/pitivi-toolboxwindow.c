/* 
 * PiTiVi
 * Copyright (C) <2004> Bloch Stephan <bloch_s@epita.fr>
 *                      Carbon Julien <carbon_j@epita.fr>
 *                      Dubart Loic <dubart_l@epita.fr>
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
#include "pitivi-toolboxwindow.h"
#include "pitivi-menu.h"
#include "pitivi-stockicons.h"
#include "pitivi-toolbox.h"
#include "pitivi-projectsettings.h"
#include "pitivi-newprojectwindow.h"

static PitiviWindowsClass	*parent_class = NULL;

struct _PitiviToolboxWindowPrivate
{
  /* instance private members */
  gboolean		dispose_has_run;
  GtkWidget		*vbox;
  PitiviToolbox		*toolbox;
};

/*
 * forward definitions
 */

/*
 * Insert "added-value" functions here
 */

void
pitivi_callb_toolbox_filenew_project ( GtkAction *action, PitiviToolboxWindow *self )
{
  PitiviNewProjectWindow *win_new_project;
  PitiviMainApp *mainapp = ((PitiviWindows *) self)->mainapp;
    
  /* New Project window */
  win_new_project = pitivi_newprojectwindow_new( mainapp );
  gtk_widget_show_all ( GTK_WIDGET (win_new_project) );
}

void
pitivi_toolbar_set_icon_mode (GtkWidget *toolbar, guint *styles)
{
  if (GTK_IS_TOOLBAR (toolbar))
    {
      gtk_toolbar_set_icon_size (GTK_TOOLBAR (toolbar), *styles);
      gtk_toolbar_set_style (GTK_TOOLBAR (toolbar), *(styles+1));
    }
}

static void
pitivi_callb_toolbox_exit ( GtkAction *action, PitiviToolboxWindow *self )
{  
  gtk_main_quit ();
}

void
pitivi_callb_toolbox_fileopen_project ( GtkAction *action, PitiviToolboxWindow *self )
{    
  PitiviMainApp	*mainapp = ((PitiviWindows *) self)->mainapp;
  PitiviProject	*project;
  GtkWidget	*dialog;
  char		*filename = NULL;
  
  /* Get the filename */
  dialog = gtk_file_chooser_dialog_new("Open a PiTiVi project",
				       GTK_WINDOW (self), GTK_FILE_CHOOSER_ACTION_OPEN,
				       GTK_STOCK_CANCEL, GTK_RESPONSE_CANCEL,
				       GTK_STOCK_OPEN, GTK_RESPONSE_ACCEPT,
				       NULL);
  if (gtk_dialog_run (GTK_DIALOG (dialog)) == GTK_RESPONSE_ACCEPT)
    filename = gtk_file_chooser_get_filename (GTK_FILE_CHOOSER (dialog));
  gtk_widget_destroy ( dialog );

  project = pitivi_project_new_from_file(filename);

  g_free (filename);
  /* Il faut remplacer cette fonction par une vrai ouverture de fichier */
  if ((project != NULL) && (pitivi_mainapp_add_project( mainapp, project )))
    pitivi_mainapp_create_wintools( mainapp , project );

}

static GtkActionEntry toolbox_menu_entries[] = {
  { "FileBoxMenu", NULL, "_File" },
  { "FileBoxNew", PITIVI_STOCK_NEW_PROJECT, "Ne_w", "<control>N", "New File", G_CALLBACK (pitivi_callb_toolbox_filenew_project) },
  { "FileBoxOpen", GTK_STOCK_OPEN, "_Open", "<control>O", "Open a file",  G_CALLBACK (pitivi_callb_toolbox_fileopen_project) },
  { "FileBoxExit", GTK_STOCK_QUIT, "E_xit", "<control>Q", "Exit the program", G_CALLBACK (pitivi_callb_toolbox_exit)},
};

static GtkActionEntry toolbox_recent_entries[]= {
  { "FileBoxRecent", GTK_STOCK_OPEN, "_Open Recent File", "<control>R", "Open a recent file", NULL},
};


PitiviToolboxWindow *
pitivi_toolboxwindow_new (PitiviMainApp *mainapp)
{
  PitiviToolboxWindow		*toolboxwindow;

  toolboxwindow = (PitiviToolboxWindow *) 
    g_object_new (PITIVI_TOOLBOXWINDOW_TYPE, "mainapp", mainapp, NULL);

  g_assert (toolboxwindow != NULL);

  return (toolboxwindow);
}

static GObject *
pitivi_toolboxwindow_constructor (GType type, 
				  guint n_construct_properties,
				  GObjectConstructParam *construct_properties)
{
  GObject			*object;
  PitiviToolboxWindow		*self;
  PitiviMenu			*menumgr;
  GtkWidget			*menu;

  object = (* G_OBJECT_CLASS (parent_class)->constructor) 
    (type, n_construct_properties, construct_properties);

/* Construction de la PitiviToolBoxWindow */
  self = (PitiviToolboxWindow *) object;
  
  self->private->toolbox = pitivi_toolbox_new ();
  self->private->vbox = gtk_vbox_new (FALSE, 0);
  gtk_window_set_title (GTK_WINDOW (self), PITIVI_TOOLBOXWINDOW_DF_TITLE);
  
  menumgr = pitivi_menu_new (GTK_WIDGET (self), PITIVI_MENU_TOOLBOX_FILENAME);
  
  GtkActionGroup *ag1 = gtk_action_group_new ("FileBoxRecent");
  GtkActionGroup *ag2 = gtk_action_group_new ("FileBoxMenu");
  
  gtk_action_group_add_actions (ag1, toolbox_menu_entries, G_N_ELEMENTS (toolbox_menu_entries), self);
  gtk_action_group_add_actions (ag2, toolbox_recent_entries, G_N_ELEMENTS (toolbox_recent_entries), self);
  
  gtk_ui_manager_insert_action_group (menumgr->public->ui, ag1, 0);
  gtk_ui_manager_insert_action_group (menumgr->public->ui, ag2, 0);
  
  PITIVI_MENU_GET_CLASS(menumgr)->public->configure (menumgr);
  
  gtk_box_pack_start (GTK_BOX (self->private->vbox),
		      GTK_WIDGET (menumgr->public->menu), FALSE, FALSE, 0);
  gtk_box_pack_start (GTK_BOX (self->private->vbox),
		     GTK_WIDGET (self->private->toolbox), FALSE, FALSE, 0);
  gtk_container_add (GTK_CONTAINER (self), self->private->vbox);

  return (object);
}

static void
pitivi_toolboxwindow_instance_init (GTypeInstance * instance, gpointer g_class)
{
  PitiviToolboxWindow	*self = (PitiviToolboxWindow *) instance;

  self->private = g_new0 (PitiviToolboxWindowPrivate, 1);
  
  /* initialize all public and private members to reasonable default values. */
  
  self->private->dispose_has_run = FALSE;
  
  /* If you need specific consruction properties to complete initialization, 
   * delay initialization completion until the property is set. 
   */
    
}

static void
pitivi_toolboxwindow_dispose (GObject * object)
{
  PitiviToolboxWindow *self = PITIVI_TOOLBOXWINDOW (object);

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

  G_OBJECT_CLASS (parent_class)->dispose (object);
}

static void
pitivi_toolboxwindow_finalize (GObject * object)
{
  PitiviToolboxWindow *self = PITIVI_TOOLBOXWINDOW (object);

  /* 
   * Here, complete object destruction. 
   * You might not need to do much... 
   */

  g_free (self->private);
  G_OBJECT_CLASS (parent_class)->finalize (object);
}

static void
pitivi_toolboxwindow_set_property (GObject * object,
				   guint property_id,
				   const GValue * value, GParamSpec * pspec)
{
  PitiviToolboxWindow *self = (PitiviToolboxWindow *) object;

  switch (property_id)
    {

    default:
      /* We don't have any other property... */
      g_assert (FALSE);
      break;
    }
}

static void
pitivi_toolboxwindow_get_property (GObject * object,
				   guint property_id,
				   GValue * value, GParamSpec * pspec)
{
  PitiviToolboxWindow *self = (PitiviToolboxWindow *) object;

  switch (property_id)
    {
      
    default:
      /* We don't have any other property... */
      g_assert (FALSE);
      break;
    }
}

static void
pitivi_toolboxwindow_class_init (gpointer g_class, gpointer g_class_data)
{
  GObjectClass *gobject_class = G_OBJECT_CLASS (g_class);
  PitiviToolboxWindowClass *klass = PITIVI_TOOLBOXWINDOW_CLASS (g_class);

  parent_class = g_type_class_peek_parent (g_class);
  

  gobject_class->constructor = pitivi_toolboxwindow_constructor;

  gobject_class->dispose = pitivi_toolboxwindow_dispose;
  gobject_class->finalize = pitivi_toolboxwindow_finalize;

  gobject_class->set_property = pitivi_toolboxwindow_set_property;
  gobject_class->get_property = pitivi_toolboxwindow_get_property;

}

GType
pitivi_toolboxwindow_get_type (void)
{
  static GType type = 0;

  if (type == 0)
    {
      static const GTypeInfo info = {
	sizeof (PitiviToolboxWindowClass),
	NULL,			/* base_init */
	NULL,			/* base_finalize */
	pitivi_toolboxwindow_class_init,	/* class_init */
	NULL,			/* class_finalize */
	NULL,			/* class_data */
	sizeof (PitiviToolboxWindow),
	0,			/* n_preallocs */
	pitivi_toolboxwindow_instance_init	/* instance_init */
      };
      type = g_type_register_static (PITIVI_WINDOWS_TYPE,
				     "PitiviToolboxWindowType", &info, 0);
    }

  return type;
}
