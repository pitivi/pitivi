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

#include <gtk/gtk.h>
#include <gst/gst.h>
#include "pitivi-newprojectwindow.h"
#include "pitivi-viewerwindow.h"
#include "pitivi-projectsettings.h"
#include "pitivi-settings.h"
#include "pitivi-settingswindow.h"
#include "pitivi-gstelementsettings.h"
#include "pitivi-projectsettingswidget.h"

static GdkPixbuf		*window_icon = NULL;
static PitiviWindowsClass	*parent_class = NULL;

enum
  {
    TEXT_COLUMN,
    NUM_COLUMN
  };

typedef struct	_PitiviConfProperties
{
  gchar		*pname;
  GValue	value;
  GtkWidget	*pwidget;
}		PitiviConfProperties;

typedef struct	_PitiviRetProperties
{
  gchar		*pname;
  GValue	value;
}		PitiviRetProperties;

typedef	struct	_PitiviCombobox
{
  GtkWidget	*combobox;
  GList		*listname;
  gchar		**tabname;
}		PitiviCombobox;

struct _PitiviNewProjectWindowPrivate
{
  /* instance private members */
  gboolean		dispose_has_run;
  GtkWidget		*hbox;

  /* Tree settings */
  GtkTreeStore		*tree;
  GtkWidget		*show_tree;
  GtkTreeIter		pIter;
  GtkTreeIter		pIter2;

  /* Custom Settings */
  GtkWidget		*name_text;
  GtkTextBuffer		*desc_text_buffer;
  GtkTextBuffer		*preset_text_buffer;
  GtkTextIter		start_preset_iter;
  GtkTextIter		end_preset_iter;
  GtkTextIter		start_description_iter;
  GtkTextIter		end_description_iter;
  GtkWidget		*name_text_settings;
  GtkWidget		*name_scroll;
  
  /* Video codecs */
  GtkWidget		*video_combo_codec;
  GtkWidget		*size_width;
  GtkWidget		*size_height;
  GtkWidget		*fps_text;
  GList			*video_listname;
  gchar			**video_tabname;

  /* Audio codecs */
  GtkWidget		*audio_combo_codec;
  GtkWidget		*audio_combo_freq;
  GtkWidget		*audio_combo_ech;
  GtkWidget		*audio_combo_depth;
  GList			*audio_listname;
  gchar			**audio_tabname;
  
  /* Container */
  GtkWidget		*container_cbox;
  GList			*container_list;

  /* Category */
  GtkWidget		*cat_text;

  /* Properties */
  GList			*video_confboxlist;
  GList			*audio_confboxlist;
 
  /* Listes des proprietes */
  GList			*video_prop_list;
  GList			*audio_prop_list;

  /* Buttons */
  GtkWidget		*cat_but_add;
  GtkWidget		*cat_but_del;
  GtkWidget		*button_add;
  GtkWidget		*button_mod;
  GtkWidget		*button_del;

  GtkWidget		*button_new;

  PitiviProjectSettingsWidget	*win_settings;
  /* Selected position */
  gint			*position;
};

/*
 * forward definitions
 */

static void			pitivi_fill_hbox		( PitiviNewProjectWindow	*self );
static void			 pitivi_tree_create		( PitiviNewProjectWindow	*self );
static GtkWidget		*pitivi_tree_show		( PitiviNewProjectWindow	*self );
static GtkWidget		*pitivi_notebook_new		( PitiviNewProjectWindow	*self );
static GtkWidget		*pitivi_make_presets_hbox	( PitiviNewProjectWindow	*self );
static GtkWidget		*pitivi_create_presets_table	( PitiviNewProjectWindow	*self );
static GtkWidget		*pitivi_make_settings_table	( PitiviNewProjectWindow	*self );
static GtkWidget		*pitivi_make_cat_frame		( PitiviNewProjectWindow	*self );
static void			pitivi_newprojectwindow_put_info( PitiviNewProjectWindow	*self, gchar		*setting_name );

/* 
 *  Signals Definitions 
*/

// Category and Settings Signals
static void			pitivi_npw_close_window		( GtkButton			*button, gpointer	user_data );
static void			pitivi_npw_add_category		( GtkButton 			*button, gpointer	user_data);
static void			pitivi_npw_add_setting		( GtkButton			*button, gpointer	user_data );
static PitiviProjectSettings	*pitivi_npw_add_projectsettings	( PitiviNewProjectWindow	*self );
static void			pitivi_npw_mod_setting		( GtkButton 			*button, gpointer 	user_data);
static void			pitivi_npw_del_setting		( GtkButton 			*button, gpointer 	user_data);
static gboolean		setting_is_selected		( GtkTreeView 			*tree_view, GtkTreeModel	*model, GtkTreePath 	*path, gboolean 	value, gpointer 	user_data );

static void			pitivi_del_category		( GtkButton  			*button, gpointer 		user_data );
gchar			*pitivi_settingswindow_get_row_list ( GList	*List, gint	row );

/*
 * Insert "added-value" functions here
 */

#define DESC_TEXT	"Description:\nInsert a description of the setting"

/* 
 * Signals
 */

static void 
pitivi_npw_close_window(GtkButton *button, gpointer user_data)
{
  gtk_widget_destroy(user_data);
}

/* *** CATEGORIES *** */
/* Add the new category when cat_add button is clicked */
static void
pitivi_npw_add_category(GtkButton *button, gpointer user_data)
{
  PitiviNewProjectWindow	*self = (PitiviNewProjectWindow *) user_data;
  PitiviMainApp			*mainapp = ((PitiviWindows *) self)->mainapp;

  if ( strlen(gtk_entry_get_text(GTK_ENTRY(self->private->cat_text))) )
    {
      pitivi_settings_add_category( mainapp->global_settings, 
				    gtk_entry_get_text ( GTK_ENTRY (self->private->cat_text) ) );
      gtk_tree_store_append(self->private->tree, &self->private->pIter2, NULL);
      gtk_tree_store_set(self->private->tree, &self->private->pIter2, 0, 
			 gtk_entry_get_text(GTK_ENTRY(self->private->cat_text)), -1);
    }
}

static void
pitivi_del_category(GtkButton *button, gpointer user_data)
{
  PitiviNewProjectWindow	*self = (PitiviNewProjectWindow *) user_data;
  PitiviMainApp			*mainapp = ((PitiviWindows *) self)->mainapp;

  if (gtk_tree_store_iter_is_valid (self->private->tree, &self->private->pIter) && 
      (!gtk_tree_store_iter_depth(self->private->tree, &self->private->pIter)))
    {
      // AJOUTER ICI LE CODE POUR :
      //	- LA SUPPRESSION DES SETTINGS
      //	- LA SUPPRESSION DE LA CATEGORIE
      pitivi_settings_del_category( mainapp->global_settings, self->private->position );
      gtk_tree_store_remove (self->private->tree, &self->private->pIter);
    }
}

/* *** SETTINGS *** */

static PitiviProjectSettings*
pitivi_npw_add_projectsettings (PitiviNewProjectWindow *self)
{
  PitiviMainApp			*mainapp = ((PitiviWindows *) self)->mainapp;
  PitiviProjectSettings		*new_setting;

  new_setting = pitivi_projectsettingswidget_get_copy (self->private->win_settings); 
  pitivi_settings_add_setting ( mainapp->global_settings, new_setting, self->private->position );
  return (new_setting);
}

/* Add the new setting when button_add is clicked */
static void
pitivi_npw_add_setting (GtkButton *button, gpointer user_data)
{
  PitiviNewProjectWindow	*self = (PitiviNewProjectWindow *) user_data;
  PitiviMainApp			*mainapp = (PitiviMainApp *) ((PitiviWindows *) self)->mainapp;
  PitiviSettings		*global_settings;
  PitiviProjectSettings		*setting;
  
  global_settings = mainapp->global_settings;
  if (global_settings->project_settings)
    {
      setting = pitivi_npw_add_projectsettings ( self );
      gtk_tree_store_append(self->private->tree, &self->private->pIter2, &self->private->pIter );
      gtk_tree_store_set(self->private->tree, &self->private->pIter2, 0, 
			 setting->name, -1);
    }
}

/* Modify the setting selected when button_mod is clicked */
static void
pitivi_npw_mod_setting(GtkButton *button, gpointer user_data)
{
  PitiviNewProjectWindow	*self = (PitiviNewProjectWindow *) user_data;
  PitiviMainApp			*mainapp = ((PitiviWindows *) self)->mainapp;
  PitiviProjectSettings		*new_setting;

  if (gtk_tree_store_iter_is_valid (self->private->tree, &self->private->pIter2) &&
      gtk_tree_store_iter_depth(self->private->tree, &self->private->pIter2))
    {
      new_setting = pitivi_projectsettingswidget_get_copy (self->private->win_settings);
      pitivi_settings_mod_setting( mainapp->global_settings, new_setting, self->private->position );
      gtk_tree_store_set(self->private->tree, &self->private->pIter2, 0,
			 new_setting->name, -1);
    }
}

/* Delete the setting selected when button_del is clicked */
static void
pitivi_npw_del_setting(GtkButton *button, gpointer user_data)
{
  PitiviNewProjectWindow *self = (PitiviNewProjectWindow *) user_data;
  PitiviMainApp *mainapp = ((PitiviWindows *) self)->mainapp;
  
  if (gtk_tree_store_iter_is_valid (self->private->tree, &self->private->pIter2) &&
      gtk_tree_store_iter_depth(self->private->tree, &self->private->pIter2))
    {
      pitivi_settings_del_setting( mainapp->global_settings, self->private->position );
      gtk_tree_store_remove (self->private->tree, &self->private->pIter2);
    }
}

/* 
*  Personal Fonctions
*/

/**
 * pitivi_npw_select_first_setting:
 * @PitiviNewProjectWindow: the project's window
 *
 * Select the default settings, the first
 *
 */

void
pitivi_npw_select_first_setting(PitiviNewProjectWindow *self)
{
  GtkTreePath		*path;
  GtkTreeSelection	*selection;

  path = gtk_tree_path_new_from_string  ("0:0");
  selection = gtk_tree_view_get_selection ( GTK_TREE_VIEW(self->private->show_tree) );
  gtk_tree_selection_select_path  (selection, path);
}

static void
pitivi_fill_hbox(PitiviNewProjectWindow *self)
{
  GtkWidget	*notebook;
  GtkWidget	*scroll;
  GtkWidget	*lefthbox;
  GtkWidget	*catframe;

  pitivi_tree_create(self);
  self->private->show_tree = pitivi_tree_show( self );

/* Ajout du scrolling pour la selection */
  scroll = gtk_scrolled_window_new(NULL, NULL);
  gtk_widget_set_usize (scroll, 150, -1);
  gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scroll), GTK_POLICY_AUTOMATIC,
				 GTK_POLICY_AUTOMATIC);

  lefthbox = gtk_vbox_new (FALSE, 1);
  
  gtk_container_add(GTK_CONTAINER(scroll), self->private->show_tree);
  notebook = pitivi_notebook_new(self);

  catframe = pitivi_make_cat_frame (self);
  gtk_box_pack_start (GTK_BOX (lefthbox), scroll, TRUE, TRUE, 1);
  gtk_box_pack_start (GTK_BOX (lefthbox), catframe, FALSE, FALSE, 1);

  gtk_box_pack_start (GTK_BOX (self->private->hbox), lefthbox, FALSE, FALSE, 0);
  gtk_box_pack_start (GTK_BOX (self->private->hbox), notebook, TRUE, TRUE, 0);
}

static void
pitivi_tree_create(PitiviNewProjectWindow *self)
{
  PitiviSettings		*gl_settings;
  GSList			*list;
  PitiviCategorieSettings	*categorie;
  PitiviProjectSettings		*setting;
  int				i;
  int				j;
  PitiviMainApp			*mainapp = ((PitiviWindows *) self)->mainapp;
  
/*   Nouvel arbre */
  self->private->tree = gtk_tree_store_new(1, G_TYPE_STRING);
  
/*   Liste des PitiviCategorieSettings et des PitiviProjectSettings */
  gl_settings = mainapp->global_settings;
  list = gl_settings->project_settings;
  
  for (i = 0; (categorie = (PitiviCategorieSettings *) g_slist_nth_data (list, i) ) ; i++)
    {
      gtk_tree_store_append(self->private->tree, &self->private->pIter, NULL);
      gtk_tree_store_set(self->private->tree, &self->private->pIter, 0, (gchar *) categorie->name, -1);
      for (j = 0; (setting = (PitiviProjectSettings *) g_slist_nth_data(categorie->list_settings, j)); j++)
	{
	  gtk_tree_store_append(self->private->tree, &self->private->pIter2, &self->private->pIter);
	  gtk_tree_store_set(self->private->tree, &self->private->pIter2, 0, setting->name, -1);
	}
    }
}

static gboolean
setting_is_selected(GtkTreeView *tree_view, GtkTreeModel *model, 
		    GtkTreePath *path, gboolean value, gpointer user_data)
{
  gchar				*setting_name;
  gchar				*parent_name;
  GtkTextIter			piter1;
  GtkTextIter			piter2;
  PitiviNewProjectWindow	*self;
  gint				*position;

  self = (PitiviNewProjectWindow *) user_data;
  if (gtk_tree_model_get_iter(model, &self->private->pIter2, path))
    {
      position = gtk_tree_path_get_indices(path);
      self->private->position[0] = position[0];
      self->private->position[1] = position[1];
      gtk_tree_model_get(model, &self->private->pIter2, TEXT_COLUMN, &setting_name, -1);
      if (!value && !(gtk_tree_store_iter_depth(self->private->tree, &self->private->pIter2)))
	{
	  gtk_widget_set_sensitive(self->private->button_new, FALSE);

	  gtk_tree_model_get_iter(model, &self->private->pIter, path);
	  gtk_text_buffer_set_text(self->private->preset_text_buffer, setting_name, strlen(setting_name));
	  gtk_entry_set_text(GTK_ENTRY(self->private->cat_text), setting_name);
	}
      else if (!value && (gtk_tree_store_iter_depth(self->private->tree, &self->private->pIter2)))
	{
	  gtk_widget_set_sensitive(self->private->button_new, TRUE);

	  pitivi_newprojectwindow_put_info( self, setting_name );
	  gtk_tree_model_iter_parent (model, &self->private->pIter, &self->private->pIter2);
	  gtk_tree_model_get(model, &self->private->pIter, TEXT_COLUMN, &parent_name, -1);
	  gtk_entry_set_text(GTK_ENTRY(self->private->cat_text),  parent_name);
	}
      else
	{
	  gtk_text_buffer_get_start_iter(self->private->preset_text_buffer, &piter1);
	  gtk_text_buffer_get_end_iter(self->private->preset_text_buffer, &piter2);
	  gtk_text_buffer_delete (self->private->preset_text_buffer, &piter1, &piter2);
	}
    }
  return TRUE;
}

static gchar	*
pitivi_npw_get_properties(GList *properties)
{
  PitiviSettingsValue	*setting_value;
  GList			*list;
  gchar			*vprop;
  gchar			*tmp;

  vprop = g_new0(gchar, 2000);
  for (list = properties; list; list = list->next) {
    if ( list->data ) {
      setting_value = (PitiviSettingsValue *) list->data;
      tmp = g_strdup_value_contents( &(setting_value->value) );
      vprop = strcat(vprop, "\n\tPropertie Name : ");
      vprop = strcat(vprop, setting_value->name);
      vprop = strcat(vprop, "\n\tPropertie Value : ");
      vprop = strcat(vprop, tmp);
      g_free(tmp);
    }
  }
  return (vprop);
}

static void
pitivi_npw_put_entire_description(PitiviNewProjectWindow *self, PitiviProjectSettings *reglage)
{
  PitiviMediaSettings	*vmedia;
  PitiviMediaSettings	*amedia;
  gchar			*setting_desc;
  gchar			*vmedia_desc;
  gchar			*amedia_desc;
  gchar			*amedia_desc2;
  gchar			*vprop;
  gchar			*aprop;
  
  gtk_text_buffer_get_start_iter( self->private->preset_text_buffer, 
				  &self->private->start_preset_iter );
  gtk_text_buffer_get_end_iter  ( self->private->preset_text_buffer, 
				  &self->private->end_preset_iter );
  gtk_text_buffer_delete ( self->private->preset_text_buffer, 
			   &self->private->start_preset_iter, 
			   &self->private->end_preset_iter );
  
  //#### SETTING
  setting_desc = g_strdup_printf ("SETTING DESCRIPTION :\n\nName : %s\nDescription : %s",
				  reglage->name, reglage->description);
  gtk_text_buffer_insert ( self->private->preset_text_buffer, &self->private->start_preset_iter, 
			   setting_desc, strlen (setting_desc) );
  
  //#### MEDIA VIDEO
  vmedia = (PitiviMediaSettings *) g_slist_nth_data(reglage->media_settings, 0);
  vmedia_desc = g_strdup_printf ("\n\n\nMEDIAS DESCRIPTIONS :\n\nVideo Codec Name : %s\nCaps Video : %s",
				 vmedia->codec_factory_name, gst_caps_to_string(vmedia->caps));
  //#### PROPERTIES
  if ( vmedia->codec_properties ) {
    vprop = pitivi_npw_get_properties(vmedia->codec_properties);
    vmedia_desc = strcat( vmedia_desc, vprop );
    g_free(vprop);
  }
  gtk_text_buffer_get_iter_at_offset(self->private->preset_text_buffer, &self->private->start_preset_iter, 
				     strlen(setting_desc) );
  gtk_text_buffer_insert ( self->private->preset_text_buffer, &self->private->start_preset_iter, 
			   vmedia_desc, strlen (vmedia_desc) );
  
  //#### MEDIA AUDIO
  amedia = (PitiviMediaSettings *) g_slist_nth_data(reglage->media_settings, 1);
  amedia_desc = g_strdup_printf ("\n\n\nMEDIAS DESCRIPTIONS :\n\nAudio Codec Name : %s\nCaps Audio : %s",
				 amedia->codec_factory_name, gst_caps_to_string(amedia->caps));
  //#### PROPERTIES
  if ( amedia->codec_properties ) {
    aprop = pitivi_npw_get_properties(amedia->codec_properties);
    amedia_desc2 = g_strdup_printf ("%s%s", amedia_desc, aprop);
    g_free(aprop);
    g_free (amedia_desc);
    amedia_desc = amedia_desc2;
  }
  
  if (reglage->container_factory_name) {
    amedia_desc2 = g_strdup_printf ("%s\n\nContainer : %s\n", amedia_desc,
				    reglage->container_factory_name);
    g_free (amedia_desc);
    amedia_desc = amedia_desc2;
  }

  gtk_text_buffer_get_iter_at_offset(self->private->preset_text_buffer,
				     &self->private->start_preset_iter,
				     strlen(setting_desc) + strlen(vmedia_desc) );

  gtk_text_buffer_insert ( self->private->preset_text_buffer, &self->private->start_preset_iter,
			   amedia_desc, strlen (amedia_desc) );
  
  g_free(setting_desc);
  g_free(amedia_desc);
  g_free(vmedia_desc);
}

static void
pitivi_newprojectwindow_put_info(PitiviNewProjectWindow *self, gchar *setting_name)
{
  PitiviCategorieSettings	*categorie;
  PitiviProjectSettings		*reglage;
  PitiviMainApp			*mainapp = ((PitiviWindows *) self)->mainapp;
  categorie = pitivi_settings_get_selected_category( mainapp->global_settings, self->private->position );
  reglage = (PitiviProjectSettings *) g_slist_nth_data(categorie->list_settings, self->private->position[1] );
  g_printf("Selection des categories... 63\n");

  pitivi_projectsettingswidget_set_settings (self->private->win_settings, reglage);

  g_printf("Selection des categories... 64\n");
  pitivi_npw_put_entire_description(self, reglage);
}

static GtkWidget *
pitivi_tree_show(PitiviNewProjectWindow *self)
{
  GtkWidget		*show_tree;
  GtkCellRenderer	*cell;
  GtkTreeViewColumn	*column;
  GtkTreeSelection	*select;

/*   Creation de la vue */
  show_tree = gtk_tree_view_new_with_model( GTK_TREE_MODEL(self->private->tree) );
  gtk_tree_view_expand_all ( GTK_TREE_VIEW(show_tree));
  
/*   Creation de la premiere colonne */
  cell = gtk_cell_renderer_text_new();
  column = gtk_tree_view_column_new_with_attributes("Selection", cell, "text", TEXT_COLUMN, NULL);
  gtk_tree_view_column_set_sizing(column, GTK_TREE_VIEW_COLUMN_AUTOSIZE);

/*   Ajout de la colonne à la vue */
  gtk_tree_view_append_column(GTK_TREE_VIEW(show_tree), column);


/*   selection d'un element */
  select = gtk_tree_view_get_selection(GTK_TREE_VIEW(show_tree));
  gtk_tree_selection_set_mode(select, GTK_SELECTION_SINGLE);
  gtk_tree_selection_set_select_function( select, (GtkTreeSelectionFunc) setting_is_selected,
					 (gpointer) (GTK_WIDGET(self)), NULL);
  
  return (show_tree);
}

static GtkWidget*
pitivi_notebook_new(PitiviNewProjectWindow *self)
{
  GtkWidget	*notebook;
  GtkWidget	*presets;
  GtkWidget	*settings;
  GtkWidget	*presets_hbox;
  GtkWidget	*settings_table;

/*   Creation d'un notebook puis positionnement des onglets */
  notebook = gtk_notebook_new ();
  gtk_notebook_set_tab_pos (GTK_NOTEBOOK (notebook), GTK_POS_TOP);
  
/*   Appel a la fct pitivi_make_presets_hbox qui va remplir la hbox de l'onglet presets */
  presets_hbox = pitivi_make_presets_hbox(self);
  settings_table = pitivi_make_settings_table(self);
  
  gtk_container_set_border_width(GTK_CONTAINER(presets_hbox), 5);
  gtk_container_set_border_width(GTK_CONTAINER(settings_table), 5);

/*   Les deux widgets suivantes serviront a afficher le nom des deux onglets */
  presets = gtk_label_new("Presets");
  settings = gtk_label_new("Settings");
  
/*   On rattache les hbox presets et settings au notebook */
  gtk_notebook_append_page (GTK_NOTEBOOK (notebook), presets_hbox, presets);
  gtk_notebook_append_page (GTK_NOTEBOOK (notebook), settings_table, settings);

  return (notebook);
}

static void
pitivi_create_new_project ( GtkAction *action, PitiviNewProjectWindow *self )
{
  PitiviMainApp *mainapp = ((PitiviWindows *) self)->mainapp;
  PitiviProject			*project;
  PitiviProjectSettings		*settings;
  PitiviCategorieSettings	*categorie;
  
  while (gtk_events_pending())
    gtk_main_iteration();
  categorie = pitivi_settings_get_selected_category( mainapp->global_settings, self->private->position );
  if (categorie == NULL)
    return ;

/*   On recupere une copie du PitiviProjectSettings selectionne */
  settings = pitivi_projectsettings_copy ((PitiviProjectSettings *) 
					  g_slist_nth_data(categorie->list_settings, self->private->position[1]));

/*   Creation d'un nouveau projet avec ces settings */
  project = pitivi_project_new( settings );
  pitivi_mainapp_create_wintools (mainapp, project);  
  gtk_widget_destroy (GTK_WIDGET (self));
}

static GtkWidget*
pitivi_make_presets_hbox(PitiviNewProjectWindow *self)
{
  GtkWidget	*presets_vbox;
  GtkWidget	*table;
  GtkWidget	*presets_frame;
  GtkWidget	*help_frame;
  GtkWidget	*button_cancel;
  GtkWidget	*hbox_button;
  GtkWidget	*help_label;
  
  //presets_hbox = gtk_hbox_new (FALSE, 0);
  presets_vbox = gtk_vbox_new(FALSE, 0);
/*   Ajout d'une nouvelle frame dans la box presets_hbox globale */
  presets_frame = gtk_frame_new("Current setting");
  gtk_box_pack_start (GTK_BOX (presets_vbox), presets_frame, TRUE, TRUE, 5);
  
/*   Creation et Insertion du tableau dans la frame de reglages */
  table = pitivi_create_presets_table(self);
  gtk_container_add(GTK_CONTAINER(presets_frame), table);
  
  help_frame = gtk_frame_new("Help");
  help_label = gtk_label_new("Help text....................je vais le faire ....");
  gtk_container_add(GTK_CONTAINER(help_frame), help_label);

  gtk_box_pack_start (GTK_BOX (presets_vbox), help_frame, FALSE, FALSE, 5);

  hbox_button = gtk_hbox_new(FALSE, 0);
  self->private->button_new = gtk_button_new_from_stock(GTK_STOCK_NEW);
  button_cancel = gtk_button_new_from_stock(GTK_STOCK_CANCEL);
  
  gtk_box_pack_start(GTK_BOX(hbox_button), self->private->button_new, FALSE, FALSE, 5);
  gtk_box_pack_start(GTK_BOX(hbox_button), button_cancel, FALSE, FALSE, 5);
  g_signal_connect(self->private->button_new, "clicked", 
		   G_CALLBACK(pitivi_create_new_project),
		   self);
  g_signal_connect( G_OBJECT(button_cancel), "clicked",
		    G_CALLBACK(pitivi_npw_close_window), 
		    (gpointer) (GTK_WIDGET(self)) );
  
  gtk_box_pack_start(GTK_BOX(presets_vbox), hbox_button, FALSE, FALSE, 5);

  return (presets_vbox);
}

static GtkWidget*
pitivi_create_presets_table(PitiviNewProjectWindow *self)
{
  GtkWidget		*name_scroll;
  GtkTextTagTable	*tag_table;
  gchar			*presets;
  GtkWidget		*text_presets;

/*   Creation du champs texte de description */
  name_scroll = gtk_scrolled_window_new(NULL, NULL);
/*   Creation de la Tag Table */
  tag_table = gtk_text_tag_table_new();
/*   Creation du buffer text */
  self->private->preset_text_buffer = gtk_text_buffer_new(tag_table);
/*   Creation du champs Text */
  presets = "Setting's descriptions";

  gtk_text_buffer_set_text (self->private->preset_text_buffer, presets, strlen(presets));
  gtk_text_buffer_get_start_iter(self->private->preset_text_buffer, &self->private->start_preset_iter);
  gtk_text_buffer_get_end_iter(self->private->preset_text_buffer, &self->private->end_preset_iter);
  text_presets = gtk_text_view_new_with_buffer (self->private->preset_text_buffer);
  
  gtk_text_view_set_editable(GTK_TEXT_VIEW(text_presets), FALSE);
  gtk_text_view_set_right_margin  (GTK_TEXT_VIEW(text_presets), 5);
  gtk_text_view_set_left_margin  (GTK_TEXT_VIEW(text_presets), 5);

  gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(name_scroll), GTK_POLICY_AUTOMATIC, GTK_POLICY_AUTOMATIC);
  gtk_container_add(GTK_CONTAINER(name_scroll), text_presets);
  
  return (name_scroll);
}

static GtkWidget*
pitivi_make_settings_table(PitiviNewProjectWindow *self)
{
  GtkWidget		*settings_table;
  GtkWidget		*button_hbox;

  settings_table = gtk_table_new (5, 2, FALSE);  
  self->private->win_settings = pitivi_projectsettingswidget_new(PITIVI_WINDOWS(self)->mainapp);
  gtk_table_attach (GTK_TABLE(settings_table), GTK_WIDGET(self->private->win_settings),
		    0, 2, 3, 4, GTK_EXPAND | GTK_FILL, FALSE , 0, 0);

/*   Ligne 4 */
  button_hbox = gtk_hbox_new(TRUE, 10);
  
  self->private->button_add = gtk_button_new_with_label("Add");
  gtk_box_pack_start(GTK_BOX(button_hbox), self->private->button_add, 
		     FALSE, GTK_EXPAND | GTK_FILL, 0);

  self->private->button_mod = gtk_button_new_with_label("Modify");
  gtk_box_pack_start(GTK_BOX(button_hbox), self->private->button_mod, 
		     FALSE, GTK_EXPAND | GTK_FILL, 0);
  
  self->private->button_del = gtk_button_new_with_label("Delete");
  gtk_box_pack_start(GTK_BOX(button_hbox), self->private->button_del, 
		     FALSE, GTK_EXPAND | GTK_FILL, 0);
  
/*   Buttons Settings Signals */
  g_signal_connect( G_OBJECT(self->private->button_add), "clicked",
		    G_CALLBACK(pitivi_npw_add_setting), (gpointer) (GTK_WIDGET(self)) );
  
  g_signal_connect( G_OBJECT(self->private->button_mod), "clicked",
		    G_CALLBACK(pitivi_npw_mod_setting), (gpointer) (GTK_WIDGET(self)) );

  g_signal_connect( G_OBJECT(self->private->button_del), "clicked",
		    G_CALLBACK(pitivi_npw_del_setting), (gpointer) (GTK_WIDGET(self)) );

  gtk_table_attach( GTK_TABLE(settings_table), button_hbox, 
		    0, 2, 4, 5, FALSE, FALSE, 0, 3);
  
  return (settings_table);
}

static GtkWidget*
pitivi_make_cat_frame(PitiviNewProjectWindow *self)
{

  GtkWidget		*cat_frame;
  GtkWidget		*cat_table;
  GtkWidget		*cat_but_hbox;

  cat_frame = gtk_frame_new("Category");
  cat_table = gtk_vbox_new (FALSE, 5);
  self->private->cat_text = gtk_entry_new();
  gtk_box_pack_start (GTK_BOX (cat_table),
		      self->private->cat_text,
		      TRUE, TRUE, 5);

  cat_but_hbox = gtk_hbox_new(TRUE, 10);
  self->private->cat_but_add = gtk_button_new_with_label("Add");
  gtk_box_pack_start(GTK_BOX(cat_but_hbox), self->private->cat_but_add, 
		     FALSE, GTK_EXPAND | GTK_FILL, 5);

  g_signal_connect( G_OBJECT(self->private->cat_but_add), "clicked",
		    G_CALLBACK(pitivi_npw_add_category), (gpointer) (GTK_WIDGET(self)) );
  
  self->private->cat_but_del = gtk_button_new_with_label("Delete");
  gtk_box_pack_start(GTK_BOX(cat_but_hbox), self->private->cat_but_del, 
		     FALSE, GTK_EXPAND | GTK_FILL, 5);

  g_signal_connect( G_OBJECT(self->private->cat_but_del), "clicked",
		    G_CALLBACK(pitivi_del_category), (gpointer) (GTK_WIDGET(self)) );

  gtk_box_pack_start (GTK_BOX (cat_table),
		      cat_but_hbox,
		      TRUE, TRUE, 5);
  gtk_container_add(GTK_CONTAINER(cat_frame), cat_table);
  gtk_container_set_border_width (GTK_CONTAINER (cat_frame), 5);

  return (cat_frame);
}

/* 
 * Object PitiviNewProject initialisation 
 */

/**
 * pitivi_newprojectwindow_new:
 * @mainapp: The #PitiviMainApp
 *
 * Creates a window for a new project
 *
 * Returns: A newly-allocated #PitiviNewProjectWindow
 */

PitiviNewProjectWindow *
pitivi_newprojectwindow_new( PitiviMainApp *mainapp )
{
  PitiviNewProjectWindow	*newprojectwindow;
  
  newprojectwindow = (PitiviNewProjectWindow *) 
    g_object_new(PITIVI_NEWPROJECTWINDOW_TYPE, "mainapp", mainapp, NULL);
  
  g_assert(newprojectwindow != NULL);
  return newprojectwindow;
}

static GObject *
pitivi_newprojectwindow_constructor (GType type,
				     guint n_construct_properties,
				     GObjectConstructParam * construct_properties)
{
  GObject			*object;
  PitiviNewProjectWindow	*self;

  object = (* G_OBJECT_CLASS (parent_class)->constructor) 
    (type, n_construct_properties, construct_properties);
  
  /* do stuff. */
  /*   Creation de la fenetre de reglages d'un nouveau projet */
  self = (PitiviNewProjectWindow *) object;
  gtk_window_set_position (GTK_WINDOW (self), GTK_WIN_POS_CENTER);
  gtk_window_set_modal (GTK_WINDOW(self), TRUE);
  
  /* Creation de hBox et Insertion dans la window du projet */
  self->private->hbox = gtk_hbox_new (FALSE, 0);
  
  /* Creation des elements de la fenetre NewProject */
  pitivi_fill_hbox(self);
  gtk_container_add (GTK_CONTAINER (self), self->private->hbox);

  self->private->position = g_new0(gint, 2);
  
  return object;
}

static void
pitivi_newprojectwindow_instance_init (GTypeInstance * instance, gpointer g_class)
{
  PitiviNewProjectWindow *self = (PitiviNewProjectWindow *) instance;

  self->private = g_new0(PitiviNewProjectWindowPrivate, 1);
  
  /* initialize all public and private members to reasonable default values. */ 
  
  self->private->dispose_has_run = FALSE;
  gtk_window_set_default_size(GTK_WINDOW(self), PITIVI_NEWPROJECT_DF_WIN_WIDTH, PITIVI_NEWPROJECT_DF_WIN_HEIGHT);
  gtk_window_set_title (GTK_WINDOW (self), PITIVI_NEWPROJECT_DF_TITLE); 
  if (window_icon == NULL) 
    {
      char *filename;
      
      filename = g_strdup(pitivi_file (PITIVI_NEWPROJECT_LOGO));
      window_icon = gdk_pixbuf_new_from_file (filename, NULL);
      g_free (filename);
    }
  gtk_window_set_icon (GTK_WINDOW (self), window_icon);

  /* If you need specific consruction properties to complete initialization, 
   * delay initialization completion until the property is set. 
   */
}

static void
pitivi_newprojectwindow_dispose (GObject *object)
{
  PitiviNewProjectWindow	*self = PITIVI_NEWPROJECTWINDOW(object);

  /* If dispose did already run, return. */
  if (self->private->dispose_has_run)
    return ;
  
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
pitivi_newprojectwindow_finalize (GObject *object)
{
  PitiviNewProjectWindow	*self = PITIVI_NEWPROJECTWINDOW(object);

  /* 
   * Here, complete object destruction. 
   * You might not need to do much... 
   */

  g_free (self->private);
  G_OBJECT_CLASS (parent_class)->finalize (object);
}

static void
pitivi_newprojectwindow_class_init (gpointer g_class, gpointer g_class_data)
{
  GObjectClass *gobject_class = G_OBJECT_CLASS (g_class);
  parent_class = g_type_class_peek_parent (g_class);
  gobject_class->constructor = pitivi_newprojectwindow_constructor;
  gobject_class->dispose = pitivi_newprojectwindow_dispose;
  gobject_class->finalize = pitivi_newprojectwindow_finalize;
}

GType	
pitivi_newprojectwindow_get_type (void)
{
  static GType type = 0;
 
  if (type == 0)
    {
      static const GTypeInfo info = {
	sizeof (PitiviNewProjectWindowClass),
	NULL,					/* base_init */
	NULL,					/* base_finalize */
	pitivi_newprojectwindow_class_init,	/* class_init */
	NULL,					/* class_finalize */
	NULL,					/* class_data */
	sizeof (PitiviNewProjectWindow),
	0,					/* n_preallocs */
	pitivi_newprojectwindow_instance_init	/* instance_init */
      };
      type = g_type_register_static (PITIVI_WINDOWS_TYPE,
				     "PitiviNewProjectWindowType", &info, 0);
    }

  return type;
}
