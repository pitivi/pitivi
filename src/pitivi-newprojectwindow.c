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

/*
  - Delete Categorie : 
	o Pour chaque setting de la liste de categorie, supprimer :
		\ Properties
		\ Caps
		\ List de media
		\ Le Setting



  - Modify Setting : 
	o Supprimer le setting modifie et ce kil contient
		\ Properties
		\ Caps
		\ List de media
		\ Le Setting
	o Creer et inserer le nouveau setting dans la categorie selectionnee
	o Prendre en compte les properties



  - Delete Setting : Effacer tout ce ke le setting contient :
	o Properties
	o Caps
	o List de media
	o Le Setting

*/

#include <gtk/gtk.h>
#include <gst/gst.h>
#include "pitivi-newprojectwindow.h"
#include "pitivi-codecconfwindow.h"
#include "pitivi-viewerwindow.h"
#include "pitivi-projectsettings.h"
#include "pitivi-settings.h"

static PitiviWindowsClass	*parent_class = NULL;

/* enum { */
/*   PROP_0, */
/*   PROP_MAINAPP */
/* }; */

enum
  {
    TEXT_COLUMN,
    NUM_COLUMN
  };

gchar	*freq_tab[] = {
  "48000",
  "32000",
  "24000",
  "12000",
  0
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

  /* PitiviMainApp object */
/*   PitiviMainApp		*mainapp; */

  /* Arbre des reglages */
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
  
  /* Codecs Videos */
  GtkWidget		*video_combo_codec;
  GList			*video_codec_list;
  GtkWidget		*size_width;
  GtkWidget		*size_height;
  GtkWidget		*fps_text;
  GList			*video_listname;
  gchar			**video_tabname;

  /* Codecs Audio */
  GtkWidget		*audio_combo_codec;
  GtkWidget		*audio_combo_freq;
  GtkWidget		*audio_combo_ech;
  GList			*audio_codec_list;
  GList			*audio_listname;
  gchar			**audio_tabname;
  
  /* Category */
  GtkWidget		*cat_text;

  /* Properties */
  PitiviCodecConfWindow	*audio_codecwindow;
  PitiviCodecConfWindow	*video_codecwindow;
  GList			*video_codecconflist;
  GList			*audio_codecconflist;
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

  /* Position de la selection */
  gint			*position;
};

/*
 * forward definitions
 */

void			pitivi_fill_hbox		( PitiviNewProjectWindow	*self );
void			 pitivi_tree_create		( PitiviNewProjectWindow	*self );
GtkWidget		*pitivi_tree_show		( PitiviNewProjectWindow	*self );
GtkWidget		*pitivi_notebook_new		( PitiviNewProjectWindow	*self );
GtkWidget		*pitivi_make_presets_hbox	( PitiviNewProjectWindow	*self );
GtkWidget		*pitivi_create_presets_table	( PitiviNewProjectWindow	*self );
GtkWidget		*pitivi_make_settings_table	( PitiviNewProjectWindow	*self );
GtkWidget		*pitivi_make_video_frame	( PitiviNewProjectWindow	*self );
GtkWidget		*pitivi_make_audio_frame	( PitiviNewProjectWindow	*self );
GtkWidget		*pitivi_make_name_frame		( PitiviNewProjectWindow	*self );
GtkWidget		*pitivi_make_cat_frame		( PitiviNewProjectWindow	*self );
PitiviConfProperties	*pitivi_setprop_new		( gchar				*name, GValue	value, GtkWidget	*pwidget );
gchar			*pitivi_newprojectwindow_getstr	( gint				i );
void			pitivi_newprojectwindow_put_info( PitiviNewProjectWindow	*self, gchar		*setting_name );
gchar			*pitivi_combobox_get_active	( GtkWidget			*combobox, gchar	*listname );
int			pitivi_get_nb_codec		( gchar	*klass_choice );
PitiviCombobox		*pitivi_make_codec_combobox	( gchar	*klass_choice );

/* 
 *  Signals Definitions 
*/

// Category and Settings Signals
void			pitivi_npw_close_window		( GtkButton			*button, gpointer	user_data );
void			pitivi_npw_add_category		( GtkButton 			*button, gpointer	user_data);
void			pitivi_npw_add_setting		( GtkButton			*button, gpointer	user_data );
void			pitivi_npw_add_projectsettings	( PitiviNewProjectWindow	*self );
void			pitivi_npw_mod_setting		( GtkButton 			*button, gpointer 	user_data);
PitiviMediaSettings	*pitivi_npw_get_a_media		( PitiviNewProjectWindow	*self );
PitiviMediaSettings	*pitivi_npw_get_v_media		( PitiviNewProjectWindow	*self );
void			pitivi_npw_del_setting		( GtkButton 			*button, gpointer 	user_data);
gboolean		pitivi_del_desc			( GtkWidget 			*name_text_settings, GdkEventButton 	*event, gpointer user_data );

void			create_codec_conf_video		( GtkWidget			*widget, gpointer		user_data );
void			create_codec_conf_audio		( GtkWidget 			*widget, gpointer		user_data );
gboolean		setting_is_selected		( GtkTreeView 			*tree_view, GtkTreeModel	*model, GtkTreePath 	*path, gboolean 	value, gpointer 	user_data );

void			pitivi_del_category		( GtkButton  			*button, gpointer 		user_data );
gboolean		categorie_button_callback	( GtkWidget 			*cat_button_clicked, 
							  GdkEventButton 		*event, 
							  gpointer 			user_data );
gchar			*pitivi_settingswindow_get_row_list ( GList	*List, gint	row );

/*
 * Insert "added-value" functions here
 */

#define DESC_TEXT	"Description:\nInsert a description of the setting"

/* 
 * Signals
 */

void 
pitivi_npw_close_window(GtkButton *button, gpointer user_data)
{
  gtk_widget_destroy(user_data);
}

/* *** CATEGORIES *** */
/* Add the new category when cat_add button is clicked */
void
pitivi_npw_add_category(GtkButton *button, gpointer user_data)
{
  PitiviNewProjectWindow	*self = (PitiviNewProjectWindow *) user_data;
  PitiviMainApp			*mainapp = ((PitiviWindows *) self)->mainapp;
  PitiviSettings		*global_settings;

  if ( strlen(gtk_entry_get_text(GTK_ENTRY(self->private->cat_text))) )
    {
      pitivi_settings_add_category( pitivi_mainapp_settings(mainapp), 
				    gtk_entry_get_text ( GTK_ENTRY (self->private->cat_text) ) );
      gtk_tree_store_append(self->private->tree, &self->private->pIter2, NULL);
      gtk_tree_store_set(self->private->tree, &self->private->pIter2, 0, 
			 gtk_entry_get_text(GTK_ENTRY(self->private->cat_text)), -1);
    }
}

/* Delete the category selected when cat_delete button is clicked */
void
pitivi_del_category(GtkButton *button, gpointer user_data)
{
  PitiviNewProjectWindow	*self;
  PitiviMainApp			*mainapp = ((PitiviWindows *) self)->mainapp;

  self = (PitiviNewProjectWindow *) user_data;
  if (gtk_tree_store_iter_is_valid (self->private->tree, &self->private->pIter) && 
      (!gtk_tree_store_iter_depth(self->private->tree, &self->private->pIter)))
    {
      // AJOUTER ICI LE CODE POUR :
      //	- LA SUPPRESSION DES SETTINGS
      //	- LA SUPPRESSION DE LA CATEGORIE
      pitivi_settings_del_category( pitivi_mainapp_settings(mainapp), self->private->position );
      gtk_tree_store_remove (self->private->tree, &self->private->pIter);
    }
}

/* *** SETTINGS *** */

void
pitivi_npw_put_properties(PitiviMediaSettings *media, GList *properties)
{
  PitiviSettingsValue	*tmp;
  PitiviSettingsValue	*prop;
  GList			*list;
  
  for (list = properties; list; list = list->next) {
    tmp = (PitiviSettingsValue *) list->data;
    prop = g_new0(PitiviSettingsValue, 1);
    
    prop->name = g_strdup(tmp->name);
    g_value_init(&(prop->value), G_VALUE_TYPE(&(tmp->value)));
    g_value_copy(&(tmp->value), &(prop->value));
/*     g_printf("  AUDIO Codec Settings [%s]:[%s]\n", prop->name, g_strdup_value_contents(&(tmp->value))); */
    media->codec_properties = g_list_append(media->codec_properties, (gpointer) prop);
  }
}

PitiviMediaSettings *
pitivi_npw_get_a_media(PitiviNewProjectWindow *self)
{
  PitiviMediaSettings	*media;
  GstCaps		*caps_audio;
  gint			freq, rate, index;
  gchar			*factory_name;
  
  factory_name = self->private->audio_tabname[gtk_combo_box_get_active( GTK_COMBO_BOX(self->private->audio_combo_codec) )];
  index = gtk_combo_box_get_active (GTK_COMBO_BOX(self->private->audio_combo_codec));
  freq = atoi ( freq_tab[ gtk_combo_box_get_active( GTK_COMBO_BOX(self->private->audio_combo_freq)) ]);
  rate = gtk_spin_button_get_value_as_int ( GTK_SPIN_BUTTON( self->private->audio_combo_ech));

  caps_audio = pitivi_projectsettings_acaps_create ( freq, rate );
  media = pitivi_projectsettings_media_new( factory_name, caps_audio, index);

// PROPERTIES
  media->codec_properties = NULL;
  pitivi_npw_put_properties( media, self->private->audio_prop_list );
  
  return (media);
}

PitiviMediaSettings *
pitivi_npw_get_v_media(PitiviNewProjectWindow *self)
{
  GList			*list;
  PitiviMediaSettings	*media;
  GstCaps		*caps_video;
  gint			index;
  gchar			*factory_name;

  factory_name = self->private->video_tabname[gtk_combo_box_get_active( GTK_COMBO_BOX(self->private->video_combo_codec) )];
  caps_video = pitivi_projectsettings_vcaps_create ( atoi ( gtk_entry_get_text(GTK_ENTRY(self->private->size_width))),
						     atoi ( gtk_entry_get_text(GTK_ENTRY(self->private->size_height))),
						     atoi ( gtk_entry_get_text(GTK_ENTRY(self->private->fps_text))) );
  index = gtk_combo_box_get_active (GTK_COMBO_BOX(self->private->video_combo_codec) );
  media = pitivi_projectsettings_media_new( factory_name, caps_video, index );
  
// PROPERTIES
  media->codec_properties = NULL;
  pitivi_npw_put_properties( media, self->private->video_prop_list );

  return (media);
}

void
pitivi_npw_add_projectsettings (PitiviNewProjectWindow *self)
{
  PitiviMainApp			*mainapp = ((PitiviWindows *) self)->mainapp;
  PitiviProjectSettings		*new_setting;
  PitiviMediaSettings		*a_media, *v_media;
  gchar				*name, *desc;

  gtk_text_buffer_get_start_iter(self->private->desc_text_buffer, 
				 &self->private->start_description_iter);
  gtk_text_buffer_get_end_iter(self->private->desc_text_buffer, 
			       &self->private->end_description_iter);
  name = (gchar *) gtk_entry_get_text(GTK_ENTRY(self->private->name_text));
  desc = gtk_text_buffer_get_text( GTK_TEXT_BUFFER(self->private->desc_text_buffer),
				   &self->private->start_description_iter,
				   &self->private->end_description_iter,
				   FALSE );
  v_media = pitivi_npw_get_v_media(self);
  a_media = pitivi_npw_get_a_media(self);
  new_setting = pitivi_projectsettings_new_with_name(name, desc);
  new_setting->media_settings = NULL;
  new_setting->media_settings = g_slist_append(new_setting->media_settings, (gpointer) v_media);
  new_setting->media_settings = g_slist_append(new_setting->media_settings, (gpointer) a_media);
  
  pitivi_settings_add_setting ( pitivi_mainapp_settings(mainapp), new_setting, self->private->position );
}

/* Add the new setting when button_add is clicked */
void
pitivi_npw_add_setting (GtkButton *button, gpointer user_data)
{
  PitiviNewProjectWindow	*self;
  PitiviMainApp			*mainapp = (PitiviMainApp *) ((PitiviWindows *) self)->mainapp;
  PitiviSettings		*global_settings;
  
  self = (PitiviNewProjectWindow *) user_data;
  if ( strlen(gtk_entry_get_text( GTK_ENTRY(self->private->name_text))) )
    {
      global_settings = pitivi_mainapp_settings(mainapp);
      if (global_settings->project_settings)
	{
	  pitivi_npw_add_projectsettings ( self );
	  gtk_tree_store_append(self->private->tree, &self->private->pIter2, &self->private->pIter );
	  gtk_tree_store_set(self->private->tree, &self->private->pIter2, 0, 
			     gtk_entry_get_text(GTK_ENTRY(self->private->name_text)), -1);
	}
    }
}

/* Modify the setting selected when button_mod is clicked */
void
pitivi_npw_mod_setting(GtkButton *button, gpointer user_data)
{
  PitiviNewProjectWindow	*self = (PitiviNewProjectWindow *) user_data;
  PitiviMainApp			*mainapp = ((PitiviWindows *) self)->mainapp;
  PitiviProjectSettings		*new_setting;
  PitiviMediaSettings		*a_media, *v_media;
  gchar				*name, *desc;

  if (gtk_tree_store_iter_is_valid (self->private->tree, &self->private->pIter2) &&
      gtk_tree_store_iter_depth(self->private->tree, &self->private->pIter2))
    {
      gtk_text_buffer_get_start_iter(self->private->desc_text_buffer, 
				     &self->private->start_description_iter);
      gtk_text_buffer_get_end_iter(self->private->desc_text_buffer, 
				   &self->private->end_description_iter);
      name = (gchar *) gtk_entry_get_text(GTK_ENTRY(self->private->name_text));
      desc = gtk_text_buffer_get_text( GTK_TEXT_BUFFER(self->private->desc_text_buffer),
				       &self->private->start_description_iter,
				       &self->private->end_description_iter,
				       FALSE );
      v_media = pitivi_npw_get_v_media(self);
      a_media = pitivi_npw_get_a_media(self);
      new_setting = pitivi_projectsettings_new_with_name(name, desc);
      new_setting->media_settings = NULL;
      new_setting->media_settings = g_slist_append(new_setting->media_settings, (gpointer) v_media);
      new_setting->media_settings = g_slist_append(new_setting->media_settings, (gpointer) a_media);
      pitivi_settings_mod_setting( pitivi_mainapp_settings(mainapp), new_setting, self->private->position );

      gtk_tree_store_set(self->private->tree, &self->private->pIter2, 0, 
			 gtk_entry_get_text(GTK_ENTRY(self->private->name_text)), -1);
    }
}

/* Delete the setting selected when button_del is clicked */
void
pitivi_npw_del_setting(GtkButton *button, gpointer user_data)
{
  PitiviNewProjectWindow *self = (PitiviNewProjectWindow *) user_data;
  PitiviMainApp *mainapp = ((PitiviWindows *) self)->mainapp;
  
  if (gtk_tree_store_iter_is_valid (self->private->tree, &self->private->pIter2) &&
      gtk_tree_store_iter_depth(self->private->tree, &self->private->pIter2))
    {
      pitivi_settings_del_setting( pitivi_mainapp_settings(mainapp), self->private->position );
      gtk_tree_store_remove (self->private->tree, &self->private->pIter2);
    }
}

/* Delete the description when focus is set into the field */
gboolean
pitivi_del_desc(GtkWidget *name_text_settings, GdkEventButton *event, gpointer user_data)
{
  PitiviNewProjectWindow	*self;
  gchar				*desc_text;
  
  self = (PitiviNewProjectWindow *) user_data;
  gtk_text_buffer_get_start_iter(self->private->desc_text_buffer, 
				 &self->private->start_description_iter);
  gtk_text_buffer_get_end_iter(self->private->desc_text_buffer, 
			       &self->private->end_description_iter);
  if (event->type == GDK_BUTTON_PRESS && event->button == 1)
    {
      desc_text = gtk_text_buffer_get_text (self->private->desc_text_buffer,
					    &self->private->start_description_iter,
					    &self->private->end_description_iter,
					    FALSE);
      if (!strncmp (DESC_TEXT, desc_text, strlen(DESC_TEXT)))
	{
	  gtk_text_buffer_delete (self->private->desc_text_buffer, &self->private->start_description_iter,
				  &self->private->end_description_iter);
	}
    }
  return FALSE;
}

/* 
*  Personal Fonctions
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

/* element de la liste de proprietes */
PitiviConfProperties *
pitivi_setprop_new(gchar *name, GValue value, GtkWidget *pwidget)
{
  PitiviConfProperties	*confprop;

  confprop = g_new0(PitiviConfProperties, 1);
  confprop->pname = name;
  confprop->value = value;
  confprop->pwidget = pwidget;

  return(confprop);
}

void
pitivi_fill_hbox(PitiviNewProjectWindow *self)
{
  GtkWidget	*notebook;
  GtkWidget	*scroll;

  pitivi_tree_create(self);
  self->private->show_tree = pitivi_tree_show( self );

  
/* Ajout du scrolling pour la selection */
  scroll = gtk_scrolled_window_new(NULL, NULL);
  gtk_widget_set_usize (scroll, 150, -1);
  gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scroll), GTK_POLICY_AUTOMATIC,
				 GTK_POLICY_AUTOMATIC);
  
  gtk_container_add(GTK_CONTAINER(scroll), self->private->show_tree);
  notebook = pitivi_notebook_new(self);
  gtk_box_pack_start (GTK_BOX (self->private->hbox), scroll, FALSE, FALSE, 0);
  gtk_box_pack_start (GTK_BOX (self->private->hbox), notebook, TRUE, TRUE, 0);
}

void
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
  gl_settings = pitivi_mainapp_settings(mainapp);
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

gboolean
setting_is_selected(GtkTreeView *tree_view, GtkTreeModel *model, 
		    GtkTreePath *path, gboolean value, gpointer user_data)
{
  gchar				*setting_name;
  gchar				*parent_name;
  GtkTextIter			piter1;
  GtkTextIter			piter2;
  PitiviNewProjectWindow	*self;
  gint				*position;
  PitiviCategorieSettings	*categorie;
  PitiviProjectSettings		*reglage;

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

/* 	  printf("select categorie : \" %s \"\n", setting_name); */
	}
      else if (!value && (gtk_tree_store_iter_depth(self->private->tree, &self->private->pIter2)))
	{
	  gtk_widget_set_sensitive(self->private->button_new, TRUE);

	  pitivi_newprojectwindow_put_info( self, setting_name );
	  gtk_tree_model_iter_parent (model, &self->private->pIter, &self->private->pIter2);
	  gtk_tree_model_get(model, &self->private->pIter, TEXT_COLUMN, &parent_name, -1);
	  gtk_entry_set_text(GTK_ENTRY(self->private->cat_text),  parent_name);
/* 	  printf("select setting : \" %s \"\n", setting_name); */
	}
      else
	{
	  gtk_text_buffer_get_start_iter(self->private->preset_text_buffer, &piter1);
	  gtk_text_buffer_get_end_iter(self->private->preset_text_buffer, &piter2);
	  gtk_text_buffer_delete (self->private->preset_text_buffer, &piter1, &piter2);
/* 	  printf("unselect setting : \" %s \"\n", setting_name); */
	}
    }
  return TRUE;
}

gchar	*
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

void
pitivi_npw_put_entire_description(PitiviNewProjectWindow *self, PitiviProjectSettings *reglage)
{
  PitiviMediaSettings	*vmedia;
  PitiviMediaSettings	*amedia;
  gchar			*setting_desc;
  gchar			*vmedia_desc;
  gchar			*amedia_desc;
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
  setting_desc = g_new0(gchar, 150);
  setting_desc = strcat(setting_desc, "SETTING DESCRIPTION :\n\nName : ");
  setting_desc = strcat(setting_desc, reglage->name);
  setting_desc = strcat(setting_desc, "\nDescription : ");
  setting_desc = strcat(setting_desc, reglage->description);
  gtk_text_buffer_insert ( self->private->preset_text_buffer, &self->private->start_preset_iter, 
			   setting_desc, strlen (setting_desc) );
  
  //#### MEDIA VIDEO
  vmedia = (PitiviMediaSettings *) g_slist_nth_data(reglage->media_settings, 0);
  vmedia_desc = g_new0(gchar, 2000);
  vmedia_desc = strcat(vmedia_desc, "\n\n\nMEDIAS DESCRIPTIONS :\n\nVideo Codec Name : ");
  vmedia_desc = strcat(vmedia_desc, vmedia->codec_factory_name);
  vmedia_desc = strcat(vmedia_desc, "\nCaps Video : ");
  vmedia_desc = strcat(vmedia_desc, gst_caps_to_string(vmedia->caps) );
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
  amedia_desc = g_new0(gchar, 2000);
  amedia_desc = strcat(amedia_desc, "\n\nAudio Codec Name : ");
  amedia_desc = strcat(amedia_desc, amedia->codec_factory_name);
  amedia_desc = strcat(amedia_desc, "\nCaps Audio : ");
  amedia_desc = strcat(amedia_desc, gst_caps_to_string(amedia->caps) );
  //#### PROPERTIES
  if ( amedia->codec_properties ) {
    aprop = pitivi_npw_get_properties(amedia->codec_properties);
    amedia_desc = strcat( amedia_desc, aprop );
    g_free(aprop);
  }
  
/*   g_print("Setting L:%d.\nVmedia L:%d.\nAmedia L: %d.\nTotal:%d",  */
/* 	  strlen(setting_desc), strlen(vmedia_desc), strlen (amedia_desc), */
/* 	  strlen(setting_desc) + strlen(vmedia_desc) + strlen (amedia_desc) ); */
  
  gtk_text_buffer_get_iter_at_offset(self->private->preset_text_buffer,
				     &self->private->start_preset_iter,
				     strlen(setting_desc) + strlen(vmedia_desc) );

  gtk_text_buffer_insert ( self->private->preset_text_buffer, &self->private->start_preset_iter,
			   amedia_desc, strlen (amedia_desc) );
  
  g_free(setting_desc);
  g_free(amedia_desc);
  g_free(vmedia_desc);
}

gint
pitivi_npw_get_index_from_tabname ( PitiviNewProjectWindow *self, gchar **tabname, gchar *codec_factory_name )
{
  gint		i;
  
  for (i = 0; tabname[i]; i++)
    if ( !strcmp(codec_factory_name, tabname[i] ) )
      return i;
  return ( -1 );
}

void
pitivi_newprojectwindow_put_info(PitiviNewProjectWindow *self, gchar *setting_name)
{
  GstCaps			*caps;
  PitiviMediaSettings		*vmedia;
  PitiviMediaSettings		*amedia;
  PitiviCategorieSettings	*categorie;
  GSList			*selected_setting;
  PitiviProjectSettings		*reglage;
  GtkObject			*spin_adjustment;
  GstStructure			*structure;
  GValue			*val;
  PitiviMainApp			*mainapp = ((PitiviWindows *) self)->mainapp;
  gint				index;

  categorie = pitivi_settings_get_selected_category( pitivi_mainapp_settings(mainapp), self->private->position );
  reglage = (PitiviProjectSettings *) g_slist_nth_data(categorie->list_settings, self->private->position[1] );
  vmedia = (PitiviMediaSettings *) g_slist_nth_data(reglage->media_settings, 0);
  amedia = (PitiviMediaSettings *) g_slist_nth_data(reglage->media_settings, 1);
  
/*   g_print( "\nSELECTED CATEGORY NAME : %s.\n", categorie->name ); */
/*   pitivi_projectsettings_print(reglage); */
  
  pitivi_npw_put_entire_description(self, reglage);
  
/*   Put informations into the GtkEntry's */
  gtk_entry_set_text(GTK_ENTRY(self->private->name_text), reglage->name);
  gtk_text_buffer_get_start_iter (self->private->desc_text_buffer, &self->private->start_description_iter );
  gtk_text_buffer_get_end_iter (self->private->desc_text_buffer, &self->private->end_description_iter );
  gtk_text_buffer_delete ( self->private->desc_text_buffer,
			   &self->private->start_description_iter,
			   &self->private->end_description_iter );
  gtk_text_buffer_set_text ( self->private->desc_text_buffer, reglage->description, strlen (reglage->description) );

/*   Put the Video entries */
  if (caps != NULL && (structure = gst_caps_get_structure (vmedia->caps, 0)))
    {
      val = (GValue *) gst_structure_get_value ( structure, "width");
      gtk_entry_set_text( GTK_ENTRY (self->private->size_width) , pitivi_newprojectwindow_getstr( g_value_get_int (val) ));
      val = (GValue *) gst_structure_get_value (structure, "height");
      gtk_entry_set_text( GTK_ENTRY (self->private->size_height ), pitivi_newprojectwindow_getstr( g_value_get_int (val) ));
      val = (GValue *) gst_structure_get_value (structure, "framerate"); 
      gtk_entry_set_text(GTK_ENTRY (self->private->fps_text ), pitivi_newprojectwindow_getstr( g_value_get_int (val) ));

      index = pitivi_npw_get_index_from_tabname ( self, self->private->video_tabname, vmedia->codec_factory_name );
      if (index != -1)
	gtk_combo_box_set_active ( GTK_COMBO_BOX (self->private->video_combo_codec), index );
    }

/*   Put the Audio entries */
  if (caps != NULL && (structure = gst_caps_get_structure (amedia->caps, 0)))
    {
      val = (GValue *) gst_structure_get_value ( structure, "channels");
      gtk_spin_button_set_value (GTK_SPIN_BUTTON (self->private->audio_combo_ech), g_value_get_int (val));
      val = (GValue *) gst_structure_get_value ( structure, "rate");
      
      index = pitivi_npw_get_index_from_tabname ( self, freq_tab, pitivi_newprojectwindow_getstr( g_value_get_int (val) ));
      if (index != -1)
	gtk_combo_box_set_active ( GTK_COMBO_BOX (self->private->audio_combo_freq), index );
      
      index = pitivi_npw_get_index_from_tabname ( self, self->private->audio_tabname, amedia->codec_factory_name );
      if (index != -1)
	gtk_combo_box_set_active ( GTK_COMBO_BOX (self->private->audio_combo_codec), index );
    }
}

gchar *
pitivi_newprojectwindow_getstr(gint i)
{
  gchar  *str;
  gint   c;
  gint   d;
   
  str = g_new0(gchar, 2);
  c = 0;
  if (i < 0)
    {
      *str = '-';
      i = -i;
      str++;
      c++;
    }
  d = 1;
  while (i / d >= 10)
    d *= 10;
  while (d)
    {
      *str = ('0' + i / d);
      i %= d;
      d /= 10;
      str++;
      c++;
    }
  *str = '\0';
  str -= c;
  return (str);
}

GtkWidget *
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

GtkWidget*
pitivi_notebook_new(PitiviNewProjectWindow *self)
{
  GtkWidget	*notebook;
  GtkWidget	*presets;
  GtkWidget	*settings;
  GtkWidget	*presets_hbox;
  GtkWidget	*settings_table;

  settings_table = g_new0(GtkWidget, 1);
/*   Creation d'un notebook puis positionnement des onglets */
  notebook = gtk_notebook_new ();
  gtk_notebook_set_tab_pos (GTK_NOTEBOOK (notebook), GTK_POS_TOP);
  
/*   Appel a la fct pitivi_make_presets_hbox qui va remplir la hbox de l'onglet presets */
  presets_hbox = pitivi_make_presets_hbox(self);
  settings_table = pitivi_make_settings_table(self);
  
/*   Les deux widgets suivantes serviront a afficher le nom des deux onglets */
  presets = gtk_label_new("Presets");
  settings = gtk_label_new("Settings");
  
/*   On rattache les hbox presets et settings au notebook */
  gtk_notebook_append_page (GTK_NOTEBOOK (notebook), presets_hbox, presets);
  gtk_notebook_append_page (GTK_NOTEBOOK (notebook), settings_table, settings);

  return (notebook);
}

GtkWidget*
pitivi_make_presets_hbox(PitiviNewProjectWindow *self)
{
  GtkWidget	*presets_hbox;
  GtkWidget	*table;
  GtkWidget	*presets_frame;
  
  presets_hbox = gtk_hbox_new (FALSE, 0);
  
/*   Ajout d'une nouvelle frame dans la box presets_hbox globale */
  presets_frame = gtk_frame_new("Current setting");
  gtk_box_pack_start (GTK_BOX (presets_hbox), presets_frame, TRUE, TRUE, 5);
  
/*   Creation et Insertion du tableau dans la frame de reglages */
  table = pitivi_create_presets_table(self);
  gtk_container_add(GTK_CONTAINER(presets_frame), table);
  
  return (presets_hbox);
}

void
pitivi_create_new_project ( GtkAction *action, PitiviNewProjectWindow *self )
{
  PitiviMainApp *mainapp = ((PitiviWindows *) self)->mainapp;
  PitiviProject			*project;
  PitiviProjectSettings		*settings;
  PitiviCategorieSettings	*categorie;
  
  categorie = pitivi_settings_get_selected_category( pitivi_mainapp_settings(mainapp), self->private->position );
  if (categorie == NULL)
    return ;

/*   On recupere une copie du PitiviProjectSettings selectionne */
  settings = pitivi_projectsettings_copy ((PitiviProjectSettings *) 
					  g_slist_nth_data(categorie->list_settings, self->private->position[1]));

/*   Creation d'un nouveau projet avec ces settings */
  project = pitivi_project_new( settings );

/*      Si on arrive a ajouter correctement le projet a mainapp alors on affiche les bonnes fenetres  */
/*      P.S. c'est un peu cra-cra de faire comme ca, vaudrait mieux emmettre un signal et faire que */
/*      ca soit le PitiviMainApp ou la PitiviToolboxWindow qui gere ca */
  //if (pitivi_mainapp_add_project(mainapp, project))
  pitivi_mainapp_create_wintools (mainapp, project);
  
  gtk_widget_destroy (GTK_WIDGET (self));
}


GtkWidget*
pitivi_create_presets_table(PitiviNewProjectWindow *self)
{
  GtkWidget		*name_scroll;
  GtkTextIter		iter;
  GtkTextTagTable	*tag_table;
  gchar			*presets;
/*   GtkWidget		*button_new; */
  GtkWidget		*button_cancel;
  GtkWidget		*text_presets;
  GtkWidget		*table;			/* contient la presets et les boutons New 
						   project et Annuler */

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
  
/*   Creation de la table */
  table = gtk_table_new(2, 2, FALSE);
/*   Insertion des cases du Tableau */
/*   Champs Texte de description du reglage selectionne */
  gtk_table_attach( GTK_TABLE(table),
		    name_scroll,
		    0,2,0,1,
		    GTK_EXPAND | GTK_FILL, GTK_EXPAND | GTK_FILL,
		    5, 5);

/*   Bouton Nouveau projet */
  self->private->button_new = gtk_button_new_from_stock(GTK_STOCK_NEW);
  gtk_table_attach( GTK_TABLE(table), self->private->button_new, 0, 1, 1, 2, GTK_EXPAND, FALSE, 1, 1);
  
  g_signal_connect(self->private->button_new, "clicked", G_CALLBACK(pitivi_create_new_project), self);

/*   Bouton Annuler projet */
  button_cancel = gtk_button_new_from_stock(GTK_STOCK_CANCEL);
  gtk_table_attach( GTK_TABLE(table),
		    button_cancel,
		    1,2,1,2,
		    GTK_EXPAND, FALSE,
		    1, 1);
  
/*   Signal emit lorsque le bouton Annuler est click& */
  g_signal_connect( G_OBJECT(button_cancel), "clicked",
		    G_CALLBACK(pitivi_npw_close_window), 
		    (gpointer) (GTK_WIDGET(self)) );
  
/*   Retourne la table creee */
  return (table);
}

GtkWidget*
pitivi_make_settings_table(PitiviNewProjectWindow *self)
{
  GtkWidget		*settings_table;
  GtkWidget		*button_hbox;
  GtkWidget		*name_label;
  GtkWidget		*desc_label;
  GtkTextTagTable	*name_tag_table;
  gchar			*name_settings;
  GtkWidget		*cat_frame;
  GtkWidget		*cat_table;
  GtkWidget		*cat_but_box;
  GtkWidget		*video_frame;
  GtkWidget		*audio_frame;
  GtkWidget		*name_frame;

  settings_table = gtk_table_new (5, 2, FALSE);
  
/*   Ligne 1 */
  name_frame = pitivi_make_name_frame(self);
  gtk_table_attach (GTK_TABLE(settings_table), name_frame,
		    0, 2, 0, 1, GTK_EXPAND | GTK_FILL, GTK_EXPAND | GTK_FILL, 0, 0);
  
/*   Ligne 2 */
  video_frame = pitivi_make_video_frame(self);

  gtk_table_attach (GTK_TABLE(settings_table), video_frame, 
		    0, 2, 1, 2, GTK_EXPAND | GTK_FILL, FALSE , 0, 0);
  
/*   Ligne 3 */
  audio_frame = pitivi_make_audio_frame(self);
  gtk_table_attach (GTK_TABLE(settings_table), audio_frame, 
		    0, 2, 2, 3, GTK_EXPAND | GTK_FILL, FALSE , 0, 0);
  
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
		    0, 2, 3, 4, FALSE, FALSE, 0, 3);
  
  /* Ligne 5 */
  cat_frame = pitivi_make_cat_frame(self);
  gtk_table_attach ( GTK_TABLE(settings_table), cat_frame, 0, 2, 4, 5, 
		     GTK_EXPAND | GTK_FILL, FALSE, 0, 0);
  
  return (settings_table);
}

GtkWidget*
pitivi_make_name_frame(PitiviNewProjectWindow *self)
{
  GtkWidget		*name_frame;
  GtkWidget		*name_table;
  GtkTextTagTable	*name_tag_table;
  GtkTextIter		name_iter;
  GtkWidget		*name_text_settings;
  GtkWidget		*name_scroll;
  GtkWidget		*name_label;
  GtkWidget		*desc_label;
  GdkEventButton	mouse_clic;

  name_frame = gtk_frame_new("General");
  name_table =  gtk_table_new(2, 2, FALSE);
  name_label = gtk_label_new("Name :");
  gtk_misc_set_alignment (GTK_MISC (name_label), 0.0f, 0.0f);
  gtk_misc_set_padding (GTK_MISC (name_label), 5, 0);
  gtk_table_attach (GTK_TABLE(name_table), name_label,
		    0, 1, 0, 1, GTK_FILL, FALSE, 5, 5);

  self->private->name_text = gtk_entry_new();
  gtk_table_attach (GTK_TABLE(name_table), self->private->name_text, 
		    1, 2, 0, 1, GTK_EXPAND | GTK_FILL, FALSE, 5, 5);
  desc_label = gtk_label_new("Description :");
  gtk_misc_set_alignment (GTK_MISC (desc_label), 0.0f, 0.0f);
  gtk_misc_set_padding (GTK_MISC (desc_label), 5, 0);
  gtk_table_attach (GTK_TABLE(name_table), desc_label, 
		    0, 1, 1, 2, GTK_FILL, FALSE, 5, 5);

  /* Creation du champs texte de description */
  /* Ajout du scrolling pour le champ texte */
  name_scroll = gtk_scrolled_window_new(NULL, NULL);
  /* Creation de la Tag Table */
  name_tag_table = gtk_text_tag_table_new();
  /* Creation du buffer text */
  self->private->desc_text_buffer = gtk_text_buffer_new(name_tag_table);
  /* Creation du champs Text */
  gtk_text_buffer_set_text (self->private->desc_text_buffer, DESC_TEXT, strlen(DESC_TEXT));
  gtk_text_buffer_get_start_iter(self->private->desc_text_buffer, &self->private->start_description_iter);
  gtk_text_buffer_get_end_iter(self->private->desc_text_buffer, &self->private->end_description_iter);
  name_text_settings = gtk_text_view_new_with_buffer (self->private->desc_text_buffer);

  gtk_text_view_set_right_margin  (GTK_TEXT_VIEW(name_text_settings), 3);
  gtk_text_view_set_left_margin  (GTK_TEXT_VIEW(name_text_settings), 3);
  gtk_text_view_set_wrap_mode (GTK_TEXT_VIEW(name_text_settings), GTK_WRAP_WORD);

  g_signal_connect( G_OBJECT(name_text_settings), "button-press-event",
		    G_CALLBACK(pitivi_del_desc), (gpointer) (GTK_WIDGET(self)) );

  gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(name_scroll), GTK_POLICY_AUTOMATIC, GTK_POLICY_AUTOMATIC);
  gtk_container_add(GTK_CONTAINER(name_scroll), name_text_settings);
  gtk_table_attach (GTK_TABLE(name_table), name_scroll, 1, 2, 1, 2, 
		    GTK_EXPAND | GTK_FILL,  GTK_EXPAND | GTK_FILL, 5, 5);
  /* ajout de la table dans la frame setting */
  gtk_container_add(GTK_CONTAINER(name_frame), name_table);
  /* ajout de la frame la table principale */

  gtk_container_set_border_width (GTK_CONTAINER (name_frame), 5);
  return (name_frame);  
}

GtkWidget*
pitivi_make_cat_frame(PitiviNewProjectWindow *self)
{

  GtkWidget		*cat_frame;
  GtkWidget		*cat_table;
  GtkWidget		*cat_but_hbox;

  cat_frame = gtk_frame_new("Category");

  cat_table = gtk_table_new(2, 1, FALSE);
  self->private->cat_text = gtk_entry_new();
  gtk_table_attach (GTK_TABLE(cat_table), self->private->cat_text, 
		    0, 1, 0, 1, FALSE, FALSE, 5, 5);

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

  gtk_table_attach (GTK_TABLE(cat_table), cat_but_hbox,
		    1, 2, 0, 1,FALSE, FALSE, 5, 5);
  gtk_container_add(GTK_CONTAINER(cat_frame), cat_table);
  gtk_container_set_border_width (GTK_CONTAINER (cat_frame), 5);

  return (cat_frame);
}

int
pitivi_get_nb_codec(gchar *klass_choice)
{
  int			i;
  int			nb_codec;
  GstElementFactory	*factory;
  const gchar		*klass;
  GList			*feature_list;

  nb_codec = 0;
  feature_list = gst_registry_pool_feature_list (GST_TYPE_ELEMENT_FACTORY);
  for (i = 0; feature_list != NULL; i++)
    {
      factory = (GstElementFactory *) feature_list->data;
      klass = gst_element_factory_get_klass (factory);
      if (!strncmp (klass, klass_choice, 19))
	{
	  nb_codec++;
	}
      else
	{
	  goto next1;
	}
    next1:
      feature_list = feature_list->next;
    }
  return(nb_codec);
}

PitiviCombobox*
pitivi_make_codec_combobox(gchar *klass_choice)
{
  int			i;
  int			j;
  int			nb_codec;
  GstElementFactory	*factory;
  const gchar		*klass;
  const gchar		*name;
  const gchar		*short_name;
  GList			*codec_list;
  PitiviCombobox	*codec_combobox;

  /* nombre de codecs */
  nb_codec = 0;
  j = 0;
  nb_codec = pitivi_get_nb_codec(klass_choice);
  codec_list = NULL;
  codec_combobox = g_new0(PitiviCombobox, 1);
  codec_combobox->combobox = gtk_combo_box_new_text();
  codec_combobox->listname = NULL;
  codec_combobox->tabname = g_malloc(sizeof(gchar **) * nb_codec);

  /* on recupere la liste des plugins et on selectionne 
     les plugins correspondant aux codecs */
  codec_list = gst_registry_pool_feature_list (GST_TYPE_ELEMENT_FACTORY);
  for (i = 0; codec_list != NULL; i++)
    {
      factory = (GstElementFactory *) codec_list->data;
      klass = gst_element_factory_get_klass (factory);
      name = gst_element_factory_get_longname (factory);
      short_name = gst_plugin_feature_get_name (GST_PLUGIN_FEATURE(factory));
      if (!strncmp (klass, klass_choice, 19))
	{
	  /* on remplit la combobox */
	  gtk_combo_box_insert_text (GTK_COMBO_BOX (codec_combobox->combobox), i, name);
	  
	  /* On remplit un tableau de nom (utilise dans beaucoup de fonctions) */
	  codec_combobox->tabname[j] = g_strdup(short_name);
	  
	  /* On remplit la liste que l on va attacher a la combobox */
	  codec_combobox->listname = g_list_append (codec_combobox->listname, g_strdup(short_name));
	  j++;
	}
      else
	{
	  goto next;
	}
    next:
      codec_list = codec_list->next;
    }
  return(codec_combobox);
}

GtkWidget*
pitivi_make_video_frame(PitiviNewProjectWindow *self)
{
  GtkWidget		*video_table;
  GtkWidget		*video_label_codec;
  GtkWidget		*video_label_size;
  GtkWidget		*video_label_fps;
  GtkWidget		*size_hbox;
  GtkWidget		*vcodec_hbox;
  GtkWidget		*vrate_hbox;
  GtkWidget		*size_label_x;
  GtkWidget		*video_frame;
   GtkWidget		*video_conf_but;
  GtkWidget		*rate_unit;
  GtkWidget		*resol_unit;
  GtkWidget		*blank1;
  GtkWidget		*blank2;
  PitiviCombobox	*video_combobox;

  video_combobox = g_new0(PitiviCombobox, 1);
  /* Creation de la frame "video" et du tableau principal */
  video_frame = gtk_frame_new("Video");
  video_table = gtk_table_new(2, 2, FALSE);

  /* vcodec_hbox */
  vcodec_hbox = gtk_hbox_new(FALSE, 5);

  /* Premier label "codecs" */
  video_label_codec = gtk_label_new("Codecs : ");
  gtk_misc_set_alignment (GTK_MISC (video_label_codec), 0.0f, 0.0f);
  gtk_misc_set_padding (GTK_MISC (video_label_codec), 5, 0);
  gtk_table_attach (GTK_TABLE(video_table), video_label_codec, 
		    0, 1, 0, 1, GTK_FILL, FALSE, 5, 5);

/* ########################################################################### */

  /* Creation de la combobox video */
  video_combobox = pitivi_make_codec_combobox("Codec/Encoder/Video");

  /* On place les infos dans le self */
  self->private->video_combo_codec = video_combobox->combobox;
  self->private->video_tabname = video_combobox->tabname;
  self->private->video_listname = video_combobox->listname;

  /* On attache les noms des codecs a la combobox */
  g_object_set_data(G_OBJECT(self->private->video_combo_codec), 
		    "video_listname", 
		    (gpointer) self->private->video_listname);

  /* Active le premier choix*/
  gtk_combo_box_set_active (GTK_COMBO_BOX (self->private->video_combo_codec), 0);
  gtk_box_pack_start(GTK_BOX (vcodec_hbox), self->private->video_combo_codec, TRUE, TRUE, 0);

  /* Bouton de configuration des codecs */
  video_conf_but = gtk_button_new_with_label("Configure");
  g_signal_connect(video_conf_but, "clicked", G_CALLBACK(create_codec_conf_video), self);
  gtk_box_pack_start(GTK_BOX (vcodec_hbox), video_conf_but, FALSE, FALSE, 0);
  gtk_table_attach (GTK_TABLE(video_table), vcodec_hbox,
		    1, 2, 0, 1, GTK_EXPAND | GTK_FILL, FALSE, 5, 5);

/* ############################################################################ */

  /* size hbox */
  size_hbox = gtk_hbox_new(FALSE, 5);

  /* Deuxieme label "size" */
  video_label_size = gtk_label_new("Size : ");
  gtk_table_attach (GTK_TABLE(video_table), video_label_size, 
		    0, 1, 1, 2, GTK_FILL, FALSE, 5, 5);
  gtk_misc_set_alignment (GTK_MISC (video_label_size), 0.0f, 0.0f);
  gtk_misc_set_padding (GTK_MISC (video_label_size), 5, 0);

  /* champ texte "width" */
  self->private->size_width = gtk_entry_new();
  gtk_entry_set_width_chars (GTK_ENTRY(self->private->size_width), 5);
  gtk_entry_set_text(GTK_ENTRY (self->private->size_width), "720");
  gtk_box_pack_start(GTK_BOX (size_hbox), self->private->size_width, FALSE, FALSE, 0);

  /* label "X" */
  size_label_x = gtk_label_new("X");
  gtk_box_pack_start(GTK_BOX (size_hbox), size_label_x, FALSE, FALSE, 0);

  /* champ texte "height" */
  self->private->size_height = gtk_entry_new();
  gtk_entry_set_width_chars (GTK_ENTRY(self->private->size_height), 5);
  gtk_entry_set_text(GTK_ENTRY(self->private->size_height), "576");
  gtk_box_pack_start(GTK_BOX (size_hbox), self->private->size_height, FALSE, FALSE, 0);

  /* pixel */
  resol_unit = gtk_label_new("pixel");
  gtk_box_pack_start(GTK_BOX (size_hbox), resol_unit, FALSE, FALSE, 0);

  /* blank1 */
  blank1 =  gtk_label_new("");
  gtk_box_pack_start(GTK_BOX (size_hbox), blank1, TRUE, TRUE, 0);
  
  gtk_table_attach(GTK_TABLE(video_table), size_hbox, 
		   1, 3, 1, 2, GTK_EXPAND | GTK_FILL, FALSE, 5, 5);
 
  /* rate hbox */
  vrate_hbox = gtk_hbox_new(FALSE, 5);

  /*   Troisieme label "Fps" */
  video_label_fps = gtk_label_new("Rate : ");
  gtk_misc_set_alignment (GTK_MISC (video_label_fps), 0.0f, 0.0f);
  gtk_misc_set_padding (GTK_MISC (video_label_fps), 5, 0);
  gtk_table_attach (GTK_TABLE(video_table), video_label_fps, 
		    0, 1, 2, 3, GTK_FILL, FALSE, 5, 5);
  
  /*   champ texte "Fps" */
  self->private->fps_text = gtk_entry_new();
  gtk_entry_set_text(GTK_ENTRY(self->private->fps_text), "25");
  gtk_entry_set_width_chars (GTK_ENTRY(self->private->fps_text), 14);
  gtk_box_pack_start(GTK_BOX (vrate_hbox), self->private->fps_text, FALSE, FALSE, 0);

  rate_unit = gtk_label_new("fps");
  gtk_box_pack_start(GTK_BOX (vrate_hbox), rate_unit, FALSE, FALSE, 0);

  /* blank2 */
  blank2 =  gtk_label_new("");
  gtk_box_pack_start(GTK_BOX (vrate_hbox), blank2, TRUE, TRUE, 0);

  gtk_table_attach (GTK_TABLE(video_table), vrate_hbox, 
		    1, 2, 2, 3, GTK_EXPAND | GTK_FILL, FALSE, 5, 5); 

  /*   Ajoute le tableau principale ds la frame "video" */
  gtk_container_add(GTK_CONTAINER(video_frame), video_table);
  gtk_container_set_border_width (GTK_CONTAINER (video_frame), 5);

  return (video_frame);
}
 
GtkWidget*
pitivi_make_audio_frame(PitiviNewProjectWindow *self)
{
  GtkWidget		*audio_frame;
  GtkWidget		*audio_table;
  GtkWidget		*audio_label_codec;
  GtkWidget		*audio_label_freq;
  GtkWidget		*audio_label_ech;
  GtkWidget		*audio_conf_but;
  GtkWidget		*acodec_hbox;
  GtkWidget		*arate_hbox;
  GtkWidget		*achannels_hbox;
  GtkObject		*spin_adjustment;
  PitiviCombobox	*audio_combobox;
  int			i;

  audio_combobox = g_new0(PitiviCombobox, 1);
  self->private->audio_listname = NULL;
  /* Creation de la frame "audio" et du tableau principal */
  audio_frame = gtk_frame_new("Audio"); 
  audio_table = gtk_table_new(2, 2, FALSE);

  /* Premier label "codecs" */
  audio_label_codec = gtk_label_new("Codecs : ");
  gtk_misc_set_alignment (GTK_MISC (audio_label_codec), 0.0f, 0.0f);
  gtk_misc_set_padding (GTK_MISC (audio_label_codec), 5, 0);
  gtk_table_attach (GTK_TABLE(audio_table), audio_label_codec, 
		    0, 1, 0, 1, GTK_FILL, FALSE, 5, 5);
 
  /* acodec_hbox */
  acodec_hbox = gtk_hbox_new(FALSE, 5);

/* ########################################################################### */

  /* Creation de la combobox audio */
  audio_combobox = pitivi_make_codec_combobox("Codec/Encoder/Audio");

  /* On place les infos dans le self */
  self->private->audio_combo_codec = audio_combobox->combobox;
  self->private->audio_tabname = audio_combobox->tabname;
  self->private->audio_listname = audio_combobox->listname;

  /* On attache les noms des codecs a la combobox */
  g_object_set_data(G_OBJECT(self->private->audio_combo_codec), 
		    "audio_listname", 
		    (gpointer) self->private->audio_listname);

  /* Active le premier choix*/
  gtk_combo_box_set_active (GTK_COMBO_BOX (self->private->audio_combo_codec), 0);
  gtk_box_pack_start(GTK_BOX (acodec_hbox), self->private->audio_combo_codec, TRUE, TRUE, 0);

  /* Bouton de configuration des codecs */
  audio_conf_but = gtk_button_new_with_label("Configure");
  g_signal_connect(audio_conf_but, "clicked", G_CALLBACK(create_codec_conf_audio), self);
  gtk_box_pack_start(GTK_BOX (acodec_hbox), audio_conf_but, FALSE, FALSE, 0);
  gtk_table_attach (GTK_TABLE(audio_table), acodec_hbox,
		    1, 2, 0, 1, GTK_EXPAND | GTK_FILL, FALSE, 5, 5);

/* ############################################################################ */


  /* Deuxieme label "frequence" */
  audio_label_freq = gtk_label_new("Rate : ");
  gtk_misc_set_alignment (GTK_MISC (audio_label_freq), 0.0f, 0.0f);
  gtk_misc_set_padding (GTK_MISC (audio_label_freq), 5, 0);
  gtk_table_attach (GTK_TABLE(audio_table), audio_label_freq, 
		    0, 1, 1, 2, GTK_FILL, FALSE, 5, 5);

  /* arate_hbox */
  arate_hbox = gtk_hbox_new(FALSE, 5);

  /*   Champ texte "frequence" */
  self->private->audio_combo_freq = gtk_combo_box_new_text();
  for (i = 0; freq_tab[i]; i++ )
    {
      gtk_combo_box_insert_text (GTK_COMBO_BOX (self->private->audio_combo_freq), i, freq_tab[i]);
    }
/*   gtk_combo_box_insert_text (GTK_COMBO_BOX (self->private->audio_combo_freq), 1, "24000 Hz"); */
/*   gtk_combo_box_insert_text (GTK_COMBO_BOX (self->private->audio_combo_freq), 2, "12000 Hz"); */
  gtk_combo_box_set_active(GTK_COMBO_BOX (self->private->audio_combo_freq), 0); /*  Choix par defaut */
  gtk_box_pack_start(GTK_BOX (arate_hbox), self->private->audio_combo_freq, TRUE, TRUE, 0);
  gtk_table_attach (GTK_TABLE(audio_table), arate_hbox, 
		    1, 2, 1, 2, GTK_EXPAND | GTK_FILL, FALSE, 5, 5);
  
  /* Troisieme label "echantillonage" */
  audio_label_ech = gtk_label_new("Channels : ");
  gtk_misc_set_alignment (GTK_MISC (audio_label_ech), 0.0f, 0.0f);
  gtk_misc_set_padding (GTK_MISC (audio_label_ech), 5, 0);
  gtk_table_attach (GTK_TABLE(audio_table), audio_label_ech, 
		    0, 1, 2, 3, GTK_FILL, FALSE, 5, 5);

  /* achannels_hbox */
  achannels_hbox = gtk_hbox_new(FALSE, 5);
  
  /*   Champ texte "canaux" */
  self->private->audio_combo_ech = gtk_spin_button_new_with_range(1, 8, 1);
  gtk_box_pack_start(GTK_BOX (achannels_hbox), self->private->audio_combo_ech, TRUE, TRUE, 0);
  gtk_table_attach (GTK_TABLE(audio_table), achannels_hbox, 
		    1, 2, 2, 3, GTK_EXPAND | GTK_FILL, FALSE, 5, 5);

  gtk_container_add(GTK_CONTAINER(audio_frame), audio_table);
  gtk_container_set_border_width (GTK_CONTAINER (audio_frame), 5);
  return (audio_frame);   
}

gchar *
pitivi_combobox_get_active (GtkWidget *widget, gchar *listname)
{
  gchar *elm;
  
  elm = pitivi_settingswindow_get_row_list
    (g_object_get_data (G_OBJECT (widget), listname),
    gtk_combo_box_get_active (GTK_COMBO_BOX (widget)));
  return (elm);
}

void
create_codec_conf_video(GtkWidget *widget, gpointer data)
{
PitiviNewProjectWindow	*self;
  GtkWidget *Dialog;
  GtkWidget *Label;
  gchar *elm;
  gint result;

  self = (PitiviNewProjectWindow *) data;
  elm = pitivi_combobox_get_active (self->private->video_combo_codec, 
						   "video_listname");
  g_print ("Button Click:%s\n", elm);
  Dialog = gtk_dialog_new ();
  Label = gtk_label_new (elm);
  gtk_container_add (GTK_CONTAINER (GTK_DIALOG(Dialog)->vbox),
		     Label);
  gtk_dialog_add_buttons (GTK_DIALOG(Dialog),
			  GTK_STOCK_OK,
			  GTK_RESPONSE_ACCEPT,
			  GTK_STOCK_CANCEL,
			  GTK_RESPONSE_REJECT,
			  NULL);
  gtk_widget_show_all (GTK_WIDGET (Dialog));

 result  = gtk_dialog_run (GTK_DIALOG (Dialog));
  switch (result)
    {
      case GTK_RESPONSE_ACCEPT:
         g_print ("ACCEPT\n");
         break;
      default:
         g_print ("CANCEL\n");
         break;
    }
  gtk_widget_destroy (Dialog);  
  return ;
}

void
create_codec_conf_audio(GtkWidget *widget, gpointer data)
{
/*   GtkWidget *ComboBox = (GtkWidget *) data; */
PitiviNewProjectWindow	*self;
  GtkWidget *Dialog;
  GtkWidget *Label;
  gchar *elm;
  gint result;

  self = (PitiviNewProjectWindow *) data;
/*   elm = gtk_combo_box_get_active (GTK_COMBO_BOX (self->private->audio_combo_codec)); */
  elm = pitivi_combobox_get_active (self->private->audio_combo_codec, 
						   "audio_listname");
  g_print ("Button Click:%s\n", elm);
  Dialog = gtk_dialog_new ();
  Label = gtk_label_new (elm);
  gtk_container_add (GTK_CONTAINER (GTK_DIALOG(Dialog)->vbox),
		     Label);
  gtk_dialog_add_buttons (GTK_DIALOG(Dialog),
			  GTK_STOCK_OK,
			  GTK_RESPONSE_ACCEPT,
			  GTK_STOCK_CANCEL,
			  GTK_RESPONSE_REJECT,
			  NULL);
  gtk_widget_show_all (GTK_WIDGET (Dialog));

 result  = gtk_dialog_run (GTK_DIALOG (Dialog));
  switch (result)
    {
      case GTK_RESPONSE_ACCEPT:
         g_print ("ACCEPT\n");
         break;
      default:
         g_print ("CANCEL\n");
         break;
    }
  gtk_widget_destroy (Dialog);  
  return ;
}

/* 
 * Object PitiviNewProject initialisation 
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
  
  gtk_window_set_title (GTK_WINDOW (self), "New Project");
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

  GSList			*list;
  PitiviCategorieSettings	*categorie;
  PitiviProjectSettings		*setting;
  
  self->private = g_new0(PitiviNewProjectWindowPrivate, 1);
  
  /* initialize all public and private members to reasonable default values. */ 
  
  self->private->dispose_has_run = FALSE;
  
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
pitivi_newprojectwindow_set_property (GObject * object, guint property_id,
				      const GValue * value, GParamSpec * pspec)
{
  PitiviNewProjectWindow *self = (PitiviNewProjectWindow *) object;

  switch (property_id)
    {
      /*   case PITIVI_NEWPROJECTWINDOW_PROPERTY: { */
      /*     g_free (self->private->name); */
      /*     self->private->name = g_value_dup_string (value); */
      /*     g_print ("maman: %s\n",self->private->name); */
      /*   } */
      /*     break; */
/*     case PROP_MAINAPP: */
/*       self->private->mainapp = g_value_get_pointer (value); */
/*       break; */

    default:
      /* We don't have any other property... */
      g_assert (FALSE);
      break;
    }
}

static void
pitivi_newprojectwindow_get_property (GObject * object, guint property_id,
				      GValue * value, GParamSpec * pspec)
{
  PitiviNewProjectWindow *self = (PitiviNewProjectWindow *) object;

  switch (property_id)
    {
      /*  case PITIVI_NEWPROJECTWINDOW_PROPERTY: { */
      /*     g_value_set_string (value, self->private->name); */
      /*   } */
      /*     break; */
/*     case PROP_MAINAPP: */
/*       g_value_set_pointer (value, self->private->mainapp); */
/*       break; */
      
    default:
      /* We don't have any other property... */
      g_assert (FALSE);
      break;
    }
}

static void
pitivi_newprojectwindow_class_init (gpointer g_class, gpointer g_class_data)
{
  GObjectClass *gobject_class = G_OBJECT_CLASS (g_class);
  PitiviNewProjectWindowClass *klass = PITIVI_NEWPROJECTWINDOW_CLASS (g_class);

  parent_class = g_type_class_peek_parent (g_class);
  
  gobject_class->constructor = pitivi_newprojectwindow_constructor;

  gobject_class->dispose = pitivi_newprojectwindow_dispose;
  gobject_class->finalize = pitivi_newprojectwindow_finalize;

  gobject_class->set_property = pitivi_newprojectwindow_set_property;
  gobject_class->get_property = pitivi_newprojectwindow_get_property;

  /* Install the properties in the class here ! */
  /*   pspec = g_param_spec_string ("maman-name", */
  /*                                "Maman construct prop", */
  /*                                "Set maman's name", */
  /*                                "no-name-set" /\* default value *\/, */
  /*                                G_PARAM_CONSTRUCT_ONLY | G_PARAM_READWRITE); */
  /*   g_object_class_install_property (gobject_class, */
  /*                                    MAMAN_BAR_CONSTRUCT_NAME, */
  /*                                    pspec); */

/*   g_object_class_install_property (gobject_class, */
/*                                    PROP_MAINAPP, */
/*                                    g_param_spec_pointer ("mainapp", */
/* 							 "mainapp", */
/* 							 "Pointer on the PitiviMainApp instance", */
/* 							 G_PARAM_WRITABLE | G_PARAM_CONSTRUCT_ONLY) ); */
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
