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

#include "pitivi.h"
#include "pitivi-projectsettingswindow.h"
#include "pitivi-projectsettingswidget.h"

static     PitiviProjectWindowsClass *parent_class;


struct _PitiviProjectSettingsWindowPrivate
{
  /* instance private members */
  gboolean	dispose_has_run;

  PitiviProjectSettingsWidget	*widget;
};

/*
 * forward definitions
 */

/*
 * Insert "added-value" functions here
 */

void
apply_clicked (GtkButton *button, PitiviProjectSettingsWindow *self)
{

}

void
cancel_clicked (GtkButton *button, PitiviProjectSettingsWindow *self)
{

}

void
ok_clicked (GtkButton *button, PitiviProjectSettingsWindow *self)
{

}

GtkWidget *
pitivi_projectsettingswindow_make_buttons_box (PitiviProjectSettingsWindow *self)
{
  GtkWidget	*applyb, *cancelb, *okb;
  GtkWidget	*hbox;

  hbox = gtk_hbox_new (FALSE, 5);

  applyb = gtk_button_new_from_stock (GTK_STOCK_APPLY);
  cancelb = gtk_button_new_from_stock (GTK_STOCK_CANCEL);
  okb = gtk_button_new_from_stock (GTK_STOCK_OK);

  gtk_box_pack_start (GTK_BOX(hbox), applyb, TRUE, TRUE, 5);
  gtk_box_pack_start (GTK_BOX(hbox), cancelb, TRUE, TRUE, 5);
  gtk_box_pack_start (GTK_BOX(hbox), okb, TRUE, TRUE, 5);

  g_signal_connect (G_OBJECT(applyb), "clicked", G_CALLBACK (apply_clicked), self);
  g_signal_connect (G_OBJECT(cancelb), "clicked", G_CALLBACK (cancel_clicked), self);
  g_signal_connect (G_OBJECT(okb), "clicked", G_CALLBACK (ok_clicked), self);

  return hbox;
}

PitiviProjectSettingsWindow *
pitivi_projectsettingswindow_new(PitiviMainApp *mainapp, PitiviProject *project)
{
  PitiviProjectSettingsWindow	*projectsettingswindow;

  projectsettingswindow = (PitiviProjectSettingsWindow *) g_object_new(PITIVI_PROJECTSETTINGSWINDOW_TYPE,
								       "mainapp", mainapp,
								       "project", project,
								       NULL);
  g_assert(projectsettingswindow != NULL);
  return projectsettingswindow;
}

static GObject *
pitivi_projectsettingswindow_constructor (GType type,
			     guint n_construct_properties,
			     GObjectConstructParam * construct_properties)
{
  PitiviProjectSettingsWindow	*self;
  GtkWidget	*vbox;
  GtkWidget	*hruler;
  GtkWidget	*bbox;
  GObject *obj;
  /* Invoke parent constructor. */
  obj = G_OBJECT_CLASS (parent_class)->constructor (type, n_construct_properties,
						    construct_properties);

  /* do stuff. */
  self = PITIVI_PROJECTSETTINGSWINDOW (obj);
  /*
    Graphical creation
  */
  gtk_window_set_title (GTK_WINDOW(self), "Project Settings");
  vbox = gtk_vbox_new(FALSE, 5);

  self->private->widget = pitivi_projectsettingswidget_new(PITIVI_WINDOWS(self)->mainapp);
  pitivi_projectsettingswidget_set_settings (self->private->widget, PITIVI_PROJECTWINDOWS(self)->project->settings);
  gtk_box_pack_start (GTK_BOX(vbox), GTK_WIDGET (self->private->widget),
		      TRUE, TRUE, 5);

  hruler = gtk_hruler_new();
  gtk_box_pack_start(GTK_BOX(vbox), hruler, FALSE, FALSE, 0);

  bbox = pitivi_projectsettingswindow_make_buttons_box(self);
  gtk_box_pack_start (GTK_BOX(vbox), bbox, FALSE, FALSE, 5);

  gtk_container_add (GTK_CONTAINER(self), vbox);

  return obj;
}

static void
pitivi_projectsettingswindow_instance_init (GTypeInstance * instance, gpointer g_class)
{
  PitiviProjectSettingsWindow *self = (PitiviProjectSettingsWindow *) instance;

  self->private = g_new0(PitiviProjectSettingsWindowPrivate, 1);
  
  /* initialize all public and private members to reasonable default values. */ 
  
  self->private->dispose_has_run = FALSE;
  
  /* Do only initialisation here */
  /* The construction of the object should be done in the Constructor
     So that properties set at instanciation can be set */
}

static void
pitivi_projectsettingswindow_dispose (GObject *object)
{
  PitiviProjectSettingsWindow	*self = PITIVI_PROJECTSETTINGSWINDOW(object);

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
pitivi_projectsettingswindow_finalize (GObject *object)
{
  PitiviProjectSettingsWindow	*self = PITIVI_PROJECTSETTINGSWINDOW(object);

  /* 
   * Here, complete object destruction. 
   * You might not need to do much... 
   */

  g_free (self->private);
  G_OBJECT_CLASS (parent_class)->finalize (object);
}

static void
pitivi_projectsettingswindow_class_init (gpointer g_class, gpointer g_class_data)
{
  GObjectClass *gobject_class = G_OBJECT_CLASS (g_class);
/*   PitiviProjectSettingsWindowClass *klass = PITIVI_PROJECTSETTINGSWINDOW_CLASS (g_class); */

  parent_class = g_type_class_peek_parent (g_class);

  gobject_class->constructor = pitivi_projectsettingswindow_constructor;
  gobject_class->dispose = pitivi_projectsettingswindow_dispose;
  gobject_class->finalize = pitivi_projectsettingswindow_finalize;
}

GType
pitivi_projectsettingswindow_get_type (void)
{
  static GType type = 0;
 
  if (type == 0)
    {
      static const GTypeInfo info = {
	sizeof (PitiviProjectSettingsWindowClass),
	NULL,			/* base_init */
	NULL,			/* base_finalize */
	pitivi_projectsettingswindow_class_init,	/* class_init */
	NULL,			/* class_finalize */
	NULL,			/* class_data */
	sizeof (PitiviProjectSettingsWindow),
	0,			/* n_preallocs */
	pitivi_projectsettingswindow_instance_init	/* instance_init */
      };
      type = g_type_register_static (PITIVI_PROJECTWINDOWS_TYPE,
				     "PitiviProjectSettingsWindowType", &info, 0);
    }

  return type;
}
