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
#include "pitivi-stockicons.h"
#include "pitivi-timelinewindow.h"
#include "pitivi-newprojectwindow.h"
#include "pitivi-sourcelistwindow.h"

static GtkActionGroup *actions_group[EA_LAST_ACTION];

static void
pitivi_callb_menuhelp_search ( GtkAction *action, gpointer data )
{

}

static void
pitivi_callb_menuhelp_about ( GtkAction *action, gpointer data )
{

}

static void
pitivi_callb_menuhelp_index ( GtkAction *action, gpointer data )
{

}

static void
pitivi_callb_menuhelp_contents ( GtkAction *action, gpointer data )
{

}

static GtkActionEntry default_entries_help[] = {
  { "HelpMenu", NULL, "_Help" },
  { "HelpSearch", GTK_STOCK_FIND, "Search", NULL, "Help Search", G_CALLBACK (pitivi_callb_menuhelp_search) },
  { "HelpAbout", GTK_STOCK_HELP, "About", NULL, "Help About",  G_CALLBACK (pitivi_callb_menuhelp_about) },
  { "HelpIndex", GTK_STOCK_INDEX, "Index", NULL, "Help Index", G_CALLBACK (pitivi_callb_menuhelp_index) },
  { "HelpContents", GTK_STOCK_SPELL_CHECK, "Contents", NULL, "Help Contents", G_CALLBACK (pitivi_callb_menuhelp_contents) },
};


GtkActionGroup **
pitivi_menubar_configure (GtkUIManager *ui_manager, gpointer data)
{
  int	count;
  
  actions_group[EA_MENU_HELP] = gtk_action_group_new ("MenuHelp");
  gtk_action_group_add_actions (actions_group[EA_MENU_HELP], default_entries_help, G_N_ELEMENTS (default_entries_help), data);
  
  for (count = 0; count < EA_LAST_ACTION; count++)
    if (actions_group[count])
       gtk_ui_manager_insert_action_group (ui_manager, actions_group[count], 0);
  return ( actions_group );
}


static GtkAction *
pitivi_groupaction_find_action (GtkActionGroup *actions, gchar *name)
{
  GList	*glist;

  if (!name)
    return NULL;
  for (glist = gtk_action_group_list_actions (actions); glist != NULL; glist = glist->next)
    {
      GtkActionGroup *actions = glist->data;
      GtkAction *action = gtk_action_group_get_action (actions, name);
      if (action)
	return action;
    }
  return NULL;
}
