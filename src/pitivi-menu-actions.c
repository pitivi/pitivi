/* 
 * PiTiVi
 * Copyright (C) <2004> Guillaume Casanova <casano_g@epita.fr>
 *                      
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
#include "pitivi-stockicons.h"
#include "pitivi-menu-actions.h"

static GtkActionGroup *actions_group[EA_LAST_ACT];

static void
pitivi_callb_menuhelp_search ( GtkAction *action, gpointer data )
{

}

void
pitivi_callb_menuhelp_about ( GtkAction *action, gpointer data)
{
  GtkWidget			*about_window;
  GtkWidget			*about_vbox;
  GtkWidget			*about_hbox;
  GtkWidget			*team_frame;
  GtkWidget			*info_frame;
  GtkWidget			*pitivi_label;
  GtkWidget			*team_label;
  GtkWidget			*info_label;
  GtkWidget			*logo;
  gchar				*filelogo;

  about_vbox = gtk_vbox_new(FALSE, 10);
  about_hbox = gtk_hbox_new(FALSE, 10);
  about_window = gtk_dialog_new_with_buttons ("PiTiVi About...",
					      NULL,
					      GTK_DIALOG_DESTROY_WITH_PARENT,
					      GTK_STOCK_OK,
					      GTK_RESPONSE_ACCEPT,
					      NULL);

  /* frames */
  team_frame = gtk_frame_new("Team");
  info_frame = gtk_frame_new("Info");

  /* Labels */
  pitivi_label = gtk_label_new("Pitivi is a non-linear\nMultimedia Editor.\nIt is an Open-Source project.\nGNU GPL license.\nVersion : "PITIVI_VERSION);
  team_label = gtk_label_new("- HERVEY Edward\n- CASANOVA Guillaume\n- DELETTREZ Marc\n- PRALAT Raphael\n- BLOCH Stephan");
  info_label = gtk_label_new("Visit our website :\n http://www.pitivi.org");
  filelogo = pitivi_file ("pitivi-logo-small.png");
  logo = gtk_image_new_from_file(filelogo);

  /* alignement */
  gtk_misc_set_alignment (GTK_MISC (team_label), 0.0f, 0.0f);
  gtk_misc_set_alignment (GTK_MISC (info_label), 0.0f, 0.0f);
  gtk_misc_set_padding (GTK_MISC (team_label), 10, 10);
  gtk_misc_set_padding (GTK_MISC (info_label), 10, 10);

  /* frames */
  gtk_container_add(GTK_CONTAINER(team_frame), team_label);
  gtk_container_add(GTK_CONTAINER(info_frame), info_label);
  gtk_box_pack_start(GTK_BOX (about_hbox), logo, TRUE, TRUE, 5);
  gtk_box_pack_start(GTK_BOX (about_hbox), pitivi_label, TRUE, TRUE, 5);

  /* fill Vbox */
  gtk_box_pack_start(GTK_BOX (about_vbox), about_hbox, TRUE, TRUE, 5);
  gtk_box_pack_start (GTK_BOX (about_vbox), team_frame, FALSE, TRUE, 5);
  gtk_box_pack_start (GTK_BOX (about_vbox), info_frame, FALSE, TRUE, 5);
 
  gtk_container_add (GTK_CONTAINER (GTK_DIALOG(about_window)->vbox), about_vbox);
  gtk_widget_show_all(about_window);
  
  if (gtk_dialog_run (GTK_DIALOG (about_window)) == GTK_RESPONSE_ACCEPT)
    gtk_widget_destroy (about_window);
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
  { "HelpAbout", PITIVI_STOCK_INFO, "About", NULL, "Help About",  G_CALLBACK (pitivi_callb_menuhelp_about) },
  { "HelpIndex", GTK_STOCK_INDEX, "Index", NULL, "Help Index", G_CALLBACK (pitivi_callb_menuhelp_index) },
  { "HelpContents", GTK_STOCK_SPELL_CHECK, "Contents", NULL, "Help Contents", G_CALLBACK (pitivi_callb_menuhelp_contents) },
};


GtkActionGroup **
pitivi_menubar_configure (GtkUIManager *ui_manager, gpointer data)
{
  int		count;
  GList		*help_list;

  actions_group[EA_MENU_HELP] = gtk_action_group_new ("MenuHelp");
  gtk_action_group_add_actions (actions_group[EA_MENU_HELP], default_entries_help, G_N_ELEMENTS (default_entries_help), data);

  help_list = gtk_action_group_list_actions(actions_group[EA_MENU_HELP]);
  while (help_list)
    {
      help_list = help_list->next;
    }
  for (count = 0; count < EA_LAST_ACT; count++)
    if (actions_group[count])
       gtk_ui_manager_insert_action_group (ui_manager, actions_group[count], 0);
  return ( actions_group );
}
