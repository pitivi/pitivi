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
#include "pitivi-menu.h"
#include "pitivi-menu-actions.h"

enum {
  ES_MENUBAR_ACTIVATE_SIGNAL = 1,
  ES_MENUBAR_LAST_SIGNAL
 };

enum {
  PITIVI_WINDOW_PROPERTY = 1,
  PITIVI_FILE_MENU_PROPERTY,
  PITIVI_ACTIONS_MENU_PROPERTY,
  PITIVI_MENU_DESCRIPTION_PROPERTY,
  PITIVI_LAST_ENUM_MENU,
};


struct  _PitiviMenuPrivate
{    
  /* instance private members */

  GtkWindow		*window;
  GtkUIManager		*ui_manager;
  guint			merge_id;
  gchar			*filename;
  gchar			*ui_description;
  
  GList			*action_group;
  GtkActionEntry	*action_entries;
  GtkToggleActionEntry	*action_toggle;
  GtkRadioActionEntry	*action_radio;
  
  GtkAccelGroup		*accel_group;
  gboolean		dispose_has_run;
  
};


/*
 * forward definitions
 */

/*
 * Insert "added-value" functions here
 */

/**
 * pitivi_menu_new:
 * @GtkWidget: the widget containing the menu 
 * @gchar: the menu name
 *
 * Creates a new menu
 *
 * Returns: A PitiviMenu, the menu
 */

PitiviMenu *
pitivi_menu_new(GtkWidget *window, gchar *fname)
{
  PitiviMenu	*menu;

  menu = PITIVI_MENU (g_object_new(PITIVI_MENU_TYPE, "window"\
				   , GTK_WINDOW(window), "filename", fname, NULL));
  g_assert(menu != NULL);
  return menu;
}

static GObject *
pitivi_menu_constructor (GType type,
			     guint n_construct_properties,
			     GObjectConstructParam * construct_properties)
{
  GObject *obj;
  PitiviMenu *self;
  /* Invoke parent constructor. */
  PitiviMenuClass *klass;
  GObjectClass *parent_class;
  klass = PITIVI_MENU_CLASS (g_type_class_peek (PITIVI_MENU_TYPE));
  parent_class = G_OBJECT_CLASS (g_type_class_peek_parent (klass));
  obj = parent_class->constructor (type, n_construct_properties,
				   construct_properties);
    
  self = (PitiviMenu *) obj;
  self->private = g_new0(PitiviMenuPrivate, 1);
  
  /* initialize all public and private members to reasonable default values. */ 
  
  self->private->dispose_has_run = FALSE;
  self->private->ui_manager = gtk_ui_manager_new ();
  self->ui = self->private->ui_manager;
  self->menu = gtk_ui_manager_get_widget (self->private->ui_manager, PITIVI_MAIN_MENUBAR_XML);
  gtk_ui_manager_set_add_tearoffs (self->private->ui_manager, TRUE);
  self->private->action_group = gtk_ui_manager_get_action_groups (self->private->ui_manager);
  self->accel_group = gtk_ui_manager_get_accel_group (self->private->ui_manager);
  
  /* If you need specific consruction properties to complete initialization, 
   * delay initialization completion until the property is set. 
   */
  
  gtk_ui_manager_ensure_update (self->private->ui_manager);
 
  return obj;
}

/**
 * pitivi_create_menupopup:
 * @GtkWidget: the widget containing the menu 
 * @GtkItemFactoryEntry: the different items of the menu
 * @gint: the number of items
 *
 * Creates the menupopup
 *
 * Returns: A GtkWidget, the menupopup
 */

GtkWidget *
pitivi_create_menupopup(GtkWidget *self, 
			GtkItemFactoryEntry *pMenuItem, 
			gint iNbMenuItem)
{
  GtkWidget		*pMenu;
  GtkItemFactory	*pItemFactory;
  GtkAccelGroup		*pAccel;

  pAccel = gtk_accel_group_new();

  /* Creation du menu */
  pItemFactory = gtk_item_factory_new(GTK_TYPE_MENU, "<menu>", NULL);
  
  /* Recuperation des elements du menu */
  gtk_item_factory_create_items(pItemFactory, iNbMenuItem, pMenuItem, self);

  /* Recuperation du widget pour l'affichage du menu */
  pMenu = gtk_item_factory_get_widget(pItemFactory, "<menu>");

  gtk_widget_show_all(pMenu);

  return pMenu;
}

static void
pitivi_menu_instance_init (GTypeInstance * instance, gpointer g_class)
{
}

static void
pitivi_menu_dispose (GObject *object)
{
  PitiviMenu	*self = PITIVI_MENU(object);

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
pitivi_menu_finalize (GObject *object)
{
  PitiviMenu	*self = PITIVI_MENU(object);

  /* 
   * Here, complete object destruction. 
   * You might not need to do much... 
   */
  g_list_free (self->private->action_group);
  g_free (self->private);
}

/**
 * pitivi_menu_configure:
 * @GtkWidget: the widget containing the menu 
 *
 * Configure the menu
 *
 */

void
pitivi_menu_configure (PitiviMenu *self)
{
  GError *error;
  
  error = NULL;
  PitiviMenuPrivate *priv = self->private;
  if (priv->merge_id)
    gtk_ui_manager_remove_ui(priv->ui_manager, priv->merge_id);
  pitivi_menubar_configure (priv->ui_manager, priv);
  if ((priv->merge_id = gtk_ui_manager_add_ui_from_file (priv->ui_manager, \
							 priv->filename, &error)))
    {
      priv->ui_description = gtk_ui_manager_get_ui (priv->ui_manager);
      self->menu = gtk_ui_manager_get_widget (priv->ui_manager, PITIVI_MAIN_MENUBAR_XML);
      gtk_ui_manager_ensure_update (priv->ui_manager);
    }
  else
    {
      g_message ("building menus failed: %s", error->message);
      exit (0);
    }
}

/**
 * pitivi_menu_set_filename:
 * @PitiviMenu: All references about the menu
 * @const gchar: the menu filename
 *
 * Set the menu filename
 *
 */

void
pitivi_menu_set_filename (PitiviMenu *self, const gchar *filename)
{
  PitiviMenuPrivate *priv;
  
  priv = self->private;
  if (self)
    {
      if (!priv->filename)
	g_free (priv->filename);
      priv->filename = g_strdup(filename);
    }
}



static void
pitivi_menu_set_property (GObject * object,
			      guint property_id,
			      const GValue * value, GParamSpec * pspec)
{
  PitiviMenu *self = (PitiviMenu *) object;

  switch (property_id)
    {
    case PITIVI_FILE_MENU_PROPERTY:
      pitivi_menu_set_filename (self, g_value_get_string (value));
      break;
    case PITIVI_WINDOW_PROPERTY:
      self->private->window = g_value_get_pointer (value);
      break;
    default:
      g_assert (FALSE);
      break;
    }
}

static void
pitivi_menu_get_property (GObject * object,
			      guint property_id,
			      GValue * value, GParamSpec * pspec)
{
  PitiviMenu *self = (PitiviMenu *) object;

  switch (property_id)
    {
     case PITIVI_FILE_MENU_PROPERTY:
      g_value_set_object (value, self->private->filename);
      break;
    case PITIVI_MENU_DESCRIPTION_PROPERTY:
      g_value_set_object (value, self->private->ui_description);
      break;
    case PITIVI_ACTIONS_MENU_PROPERTY:
      g_value_set_object (value, self->private->action_entries);
      break;
    default:
      G_OBJECT_WARN_INVALID_PROPERTY_ID (object, property_id, pspec);
      break;
    }
}

static void
pitivi_menu_class_init (gpointer g_class, gpointer g_class_data)
{
  GObjectClass *gobject_class = G_OBJECT_CLASS (g_class);
  PitiviMenuClass *klass = PITIVI_MENU_CLASS (g_class);

  gobject_class->constructor = pitivi_menu_constructor;
  gobject_class->dispose = pitivi_menu_dispose;
  gobject_class->finalize = pitivi_menu_finalize;

  gobject_class->set_property = pitivi_menu_set_property;
  gobject_class->get_property = pitivi_menu_get_property;

  g_object_class_install_property
    (gobject_class,
     PITIVI_FILE_MENU_PROPERTY,
     g_param_spec_string ("filename",
			  "Filename",
			  "Filename xml description file ui",
			  NULL,
			  (G_PARAM_READABLE|G_PARAM_WRITABLE)));

  g_object_class_install_property (G_OBJECT_CLASS (gobject_class), PITIVI_WINDOW_PROPERTY,
				   g_param_spec_pointer ("window","window","window",
							 G_PARAM_WRITABLE ));
  klass->configure = pitivi_menu_configure;
}

GType
pitivi_menu_get_type (void)
{
  static GType type = 0;
 
  if (type == 0)
    {
      static const GTypeInfo info = {
	sizeof (PitiviMenuClass),
	NULL,			/* base_init */
	NULL,			/* base_finalize */
	pitivi_menu_class_init,	/* class_init */
	NULL,			/* class_finalize */
	NULL,			/* class_data */
	sizeof (PitiviMenu),
	0,			/* n_preallocs */
	pitivi_menu_instance_init	/* instance_init */
      };
      type = g_type_register_static (GTK_TYPE_WIDGET,
				     "PitiviMenuType", &info, 0);
    }

  return type;
}
