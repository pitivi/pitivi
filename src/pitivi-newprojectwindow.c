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

  - Delete Setting : Effacer tout ce ke le setting contient :
	o Properties
	o Caps
	o List de media
	o Le Setting


  - Delete Categorie : 
	o Pour chaque setting de la liste de categorie
		\ Properties
		\ Caps
		\ List de media
		\ Le Setting
	o Supprimer la categorie selectionnee
	

  - Modify : 
	o Supprimer le setting modifie et ce kil contient
		\ Properties
		\ Caps
		\ List de media
		\ Le Setting
	o Creer et inserer le nouveau setting dans la categorie selectionnee

*/

#include <gtk/gtk.h>
#include <gst/gst.h>
#include "pitivi-newprojectwindow.h"
#include "pitivi-codecconfwindow.h"
#include "pitivi-viewerwindow.h"
#include "pitivi-projectsettings.h"

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
  gchar			**video_tabname;

  /* Codecs Audio */
  GtkWidget		*audio_combo_codec;
  GtkWidget		*audio_combo_freq;
  GtkWidget		*audio_combo_ech;
  GList			*audio_codec_list;
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

  /* Position de la selection */
  gint			*position;
};

/*
 * forward definitions
 */
void			pitivi_newprojectwindow_add_mainapp_setting( PitiviNewProjectWindow *self );
GSList			*pitivi_newprojectwindow_get_list_media(PitiviNewProjectWindow	*self );
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
GtkWidget		*pitivi_value_conf_boolean	( const gchar			*name, 
							  GValue			value );
GtkWidget		*pitivi_value_conf_uint		( const gchar			*name,
							  GValue			value, 
							  GParamSpec			*param );
GtkWidget		*pitivi_value_conf_int		( const gchar			*name,
							  GValue			value,
							  GParamSpec			*param );
GtkWidget		*pitivi_value_conf_uint64	( const gchar			*name,
							  GValue			value,
							  GParamSpec			*param );
GtkWidget		*pitivi_value_conf_int64	( const gchar			*name,
							  GValue			value,
							  GParamSpec			*param );
GtkWidget		*pitivi_value_conf_ulong	( const gchar			*name,
							  GValue			value,
							  GParamSpec			*param );
GtkWidget		*pitivi_value_conf_long		( const gchar			*name,
							  GValue			value,
							  GParamSpec			*param );
GtkWidget		*pitivi_value_conf_float	( const gchar			*name,
							  GValue			value,
							  GParamSpec			*param );
GtkWidget		*pitivi_value_conf_double	( const gchar			*name,
							  GValue			value,
							  GParamSpec			*param );
GtkWidget		*pitivi_conf_value_string	( const gchar			*name,
							  GValue			 value );
GtkWidget		*pitivi_value_conf_default	( const gchar			*name,
							  GValue			 value, 
							  GParamSpec			*param );
PitiviConfProperties	*pitivi_setprop_new		( gchar				*name,
							  GValue			 value, 
							  GtkWidget			*pwidget );
PitiviRetProperties 	*pitivi_conf_int_update		( PitiviConfProperties		*confprop,
							  PitiviNewProjectWindow	*self, 
							  gchar				*type );
PitiviRetProperties 	*pitivi_conf_float_update	( PitiviConfProperties		*confprop,
							  PitiviNewProjectWindow	*self);
PitiviRetProperties 	*pitivi_conf_boolean_update	( PitiviConfProperties		*confprop,
							  PitiviNewProjectWindow	*self);
PitiviRetProperties 	*pitivi_conf_default_update	( PitiviConfProperties		*confprop,
							  PitiviNewProjectWindow	*self);
gchar			*pitivi_newprojectwindow_getstr	( gint				i );
void			pitivi_newprojectwindow_put_info( PitiviNewProjectWindow	*self, 
							  gchar				*setting_name );

/* Signals Definitions */
void			pitivi_newprojectwindow_close_window( GtkButton			*button, 
							      gpointer			user_data );
void			pitivi_newprojectwindow_add_setting( GtkButton			*button, 
							     gpointer			user_data );
void			create_codec_conf_video		( GtkButton			*button, 
							  gpointer			user_data );
void			create_codec_conf_audio		( GtkButton 			*button, 
							  gpointer 			user_data );
gboolean		setting_is_selected		( GtkTreeView 			*tree_view, 
							  GtkTreeModel 			*model, 
							  GtkTreePath 			*path, 
							  gboolean 			value, 
							  gpointer 			user_data );
gboolean		pitivi_del_desc			( GtkWidget 			*name_text_settings, 
							  GdkEventButton 		*event,
							  gpointer 			user_data );
void			pitivi_add_category		( GtkButton 			*button, 
							  gpointer 			user_data);
void			pitivi_del_category		( GtkButton  			*button, 
							  gpointer 			user_data);
GSList			*pitivi_mainapp_project_settings( PitiviMainApp 		*self );
gboolean		categorie_button_callback	( GtkWidget 			*cat_button_clicked, 
							  GdkEventButton 		*event, 
							  gpointer 			user_data );
void			pitivi_del_settings		( GtkButton 			*button, 
							  gpointer 			user_data);
void			pitivi_valide_video_codec_conf	( GtkButton 			*button, 
							  gpointer 			user_data );
void			pitivi_valide_audio_codec_conf	( GtkButton 			*button, 
							  gpointer 			user_data );

/*
 * Insert "added-value" functions here
 */

#define DESC_TEXT	"Description:\nInsert a description of the setting"

/* 
 * Signals
 */
void 
pitivi_newprojectwindow_close_window(GtkButton *button, gpointer user_data)
{
  gtk_widget_destroy(user_data);
}

void
pitivi_newprojectwindow_add_setting (GtkButton *button, gpointer user_data)
{
  PitiviNewProjectWindow	*self;

  self = (PitiviNewProjectWindow *) user_data;

  /* Insertion du nouveau setting dans une categorie de la fenetre NewProjectWindow */
  if ( strlen(gtk_entry_get_text( GTK_ENTRY(self->private->name_text))) )
    {
      pitivi_newprojectwindow_add_mainapp_setting ( self );
      
      gtk_tree_store_append(self->private->tree,
			    &self->private->pIter2,
			    &self->private->pIter );
      gtk_tree_store_set(self->private->tree, &self->private->pIter2,
			 0, gtk_entry_get_text(GTK_ENTRY(self->private->name_text)), -1);
    }
}

void
pitivi_add_category(GtkButton *button, gpointer user_data)
{
  PitiviNewProjectWindow *self = (PitiviNewProjectWindow *) user_data;
  PitiviMainApp *mainapp = ((PitiviWindows *) self)->mainapp;

  if ( strlen(gtk_entry_get_text(GTK_ENTRY(self->private->cat_text))) )
    { 
      pitivi_mainapp_add_newcategory( mainapp, 
				      gtk_entry_get_text ( GTK_ENTRY (self->private->cat_text) ) );

      gtk_tree_store_append(self->private->tree,
			    &self->private->pIter2,
			    NULL);
      gtk_tree_store_set(self->private->tree, &self->private->pIter2, 
			 0, gtk_entry_get_text(GTK_ENTRY(self->private->cat_text)), -1);
    }
}


void
pitivi_modif_settings(GtkButton *button, gpointer user_data)
{
  PitiviNewProjectWindow *self = (PitiviNewProjectWindow *) user_data;
  PitiviMainApp *mainapp = ((PitiviWindows *) self)->mainapp;
  PitiviProjectSettings		*new_setting;
  GSList			*list_media;

  g_print("Entree Modif setting\n");
  if (gtk_tree_store_iter_is_valid (self->private->tree, &self->private->pIter2) &&
      gtk_tree_store_iter_depth(self->private->tree, &self->private->pIter2))
    {
      gtk_text_buffer_get_start_iter(self->private->desc_text_buffer, 
				     &self->private->start_description_iter);
      gtk_text_buffer_get_end_iter(self->private->desc_text_buffer, 
				   &self->private->end_description_iter);
      
      /* Creation du nouveau setting En recuperant les valeurs des champs */
      list_media = pitivi_newprojectwindow_get_list_media(self);
      
      new_setting = pitivi_projectsettings_new_with_name( (gchar *) gtk_entry_get_text(GTK_ENTRY(self->private->name_text)),
							  gtk_text_buffer_get_text( GTK_TEXT_BUFFER(self->private->desc_text_buffer),
										    &self->private->start_description_iter,
										    &self->private->end_description_iter, 
										    FALSE ), 
							  list_media );
      
      pitivi_mainapp_modif_settings( mainapp, new_setting, self->private->position );
      
      gtk_tree_store_set(self->private->tree, &self->private->pIter2,
			 0, gtk_entry_get_text(GTK_ENTRY(self->private->name_text)), -1);
    }
}


void
pitivi_del_category(GtkButton *button, gpointer user_data)
{
  PitiviNewProjectWindow	*self;

  self = (PitiviNewProjectWindow *) user_data;
  
  if (gtk_tree_store_iter_is_valid (self->private->tree, &self->private->pIter) && 
      (!gtk_tree_store_iter_depth(self->private->tree, &self->private->pIter)))
    gtk_tree_store_remove (self->private->tree, &self->private->pIter);
}

void
pitivi_del_settings(GtkButton *button, gpointer user_data)
{
  PitiviNewProjectWindow *self = (PitiviNewProjectWindow *) user_data;
  PitiviMainApp *mainapp = ((PitiviWindows *) self)->mainapp;
  
  if (gtk_tree_store_iter_is_valid (self->private->tree, &self->private->pIter2) &&
      gtk_tree_store_iter_depth(self->private->tree, &self->private->pIter2))
    {
      pitivi_mainapp_del_settings( mainapp, self->private->position );
      gtk_tree_store_remove (self->private->tree, &self->private->pIter2);
    }
}

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
	  gtk_text_buffer_delete (self->private->desc_text_buffer,
				  &self->private->start_description_iter,
				  &self->private->end_description_iter);
	}
    }
  return FALSE;
}

/* 
 * Personal Fonctions
 */

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


/*	
  Get the inputs, create a new PitiviProjectSettings and add it into the 
  PitiviMainApp struct
*/
void
pitivi_newprojectwindow_add_mainapp_setting (PitiviNewProjectWindow *self)
{
  PitiviProjectSettings		*new_setting;
  GSList			*list_media;
  PitiviMainApp *mainapp = ((PitiviWindows *) self)->mainapp;

  gtk_text_buffer_get_start_iter(self->private->desc_text_buffer, 
				 &self->private->start_description_iter);
  gtk_text_buffer_get_end_iter(self->private->desc_text_buffer, 
			       &self->private->end_description_iter);
  
  /* Creation du nouveau setting En recuperant les valeurs des champs */
  list_media = pitivi_newprojectwindow_get_list_media(self);
  
  new_setting = pitivi_projectsettings_new_with_name( (gchar *) gtk_entry_get_text(GTK_ENTRY(self->private->name_text)),
						      gtk_text_buffer_get_text( GTK_TEXT_BUFFER(self->private->desc_text_buffer),
										&self->private->start_description_iter,
										&self->private->end_description_iter, 
										FALSE ), 
						      list_media );
  
  /* Insertion du nouveau setting dans la PitiviMainApp */
  pitivi_mainapp_add_settings( mainapp, 
				new_setting, 
				self->private->position );
}


GSList *
pitivi_newprojectwindow_get_list_media(PitiviNewProjectWindow *self)
{
  GSList	*list_media;
  GstCaps	*caps_video;
  GstCaps	*caps_audio;

  caps_video = pitivi_projectsettings_vcaps_create ( atoi ( gtk_entry_get_text(GTK_ENTRY(self->private->size_width))),
						     atoi ( gtk_entry_get_text(GTK_ENTRY(self->private->size_height))),
						     atoi ( gtk_entry_get_text(GTK_ENTRY(self->private->fps_text))) );
  
  caps_audio = pitivi_projectsettings_acaps_create ( atoi ( freq_tab[ gtk_combo_box_get_active( GTK_COMBO_BOX(self->private->audio_combo_freq)) ]),
						     gtk_spin_button_get_value_as_int ( GTK_SPIN_BUTTON( self->private->audio_combo_ech)) );
  
  list_media = NULL;
  list_media = g_slist_append( list_media, (gpointer) pitivi_projectsettings_media_new( self->private->video_tabname[gtk_combo_box_get_active( GTK_COMBO_BOX(self->private->video_combo_codec) )], caps_video, gtk_combo_box_get_active (GTK_COMBO_BOX(self->private->video_combo_codec) ) ) );
  
  list_media = g_slist_append(list_media, (gpointer) pitivi_projectsettings_media_new( self->private->audio_tabname[gtk_combo_box_get_active( GTK_COMBO_BOX(self->private->audio_combo_codec) )], caps_audio, gtk_combo_box_get_active (GTK_COMBO_BOX(self->private->audio_combo_codec) ) ) );
  
  return (list_media);
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
  GSList			*list;
  PitiviCategorieSettings	*categorie;
  PitiviProjectSettings		*setting;
  int				i;
  int				j;
  PitiviMainApp *mainapp = ((PitiviWindows *) self)->mainapp;
  
  /* Nouvel arbre */
  self->private->tree = gtk_tree_store_new(1, G_TYPE_STRING);
  
  /* Liste des PitiviCategorieSettings et des PitiviProjectSettings */
  list = pitivi_mainapp_project_settings( mainapp );

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
	  gtk_tree_model_get_iter(model, &self->private->pIter, path);

	  gtk_text_buffer_set_text(self->private->preset_text_buffer, setting_name, strlen(setting_name));
	  gtk_entry_set_text(GTK_ENTRY(self->private->cat_text), setting_name);
	}
      else if (!value && (gtk_tree_store_iter_depth(self->private->tree, &self->private->pIter2)))
	{
	  pitivi_newprojectwindow_put_info( self, setting_name );

	  gtk_tree_model_iter_parent (model, &self->private->pIter, &self->private->pIter2);
	  gtk_tree_model_get(model, &self->private->pIter, TEXT_COLUMN, &parent_name, -1);
	  gtk_entry_set_text(GTK_ENTRY(self->private->cat_text),  parent_name);
	  /* 	  printf("select setting : \" %s \"\n", setting_name); */
	}
      else
	{
	  /*  debut du buffer */
	  gtk_text_buffer_get_start_iter(self->private->preset_text_buffer, &piter1);
	  /*  fin du buffer */
	  gtk_text_buffer_get_end_iter(self->private->preset_text_buffer, &piter2);
	  /*  On vide le buffer */
	  gtk_text_buffer_delete (self->private->preset_text_buffer, &piter1, &piter2);
	  /* 	  printf("unselect setting : \" %s \"\n", setting_name); */
	}
    }
  return TRUE;
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
  PitiviMainApp *mainapp = ((PitiviWindows *) self)->mainapp;
  
  categorie = pitivi_mainapp_get_selected_category( mainapp, self->private->position );
  g_print( "\nSELECTED CATEGORY NAME : %s.\n", categorie->name );
  
  reglage = (PitiviProjectSettings *) g_slist_nth_data(categorie->list_settings, self->private->position[1] );
  g_print( "NAME SETTING : \n%s.\nDESCRIPTION SETTING :\n%s.\nLIST MEDIA : \n", reglage->name, reglage->description);

  vmedia = (PitiviMediaSettings *) g_slist_nth_data(reglage->media_settings, 0);
  amedia = (PitiviMediaSettings *) g_slist_nth_data(reglage->media_settings, 1);
  g_print( "V INDEX : %d.\n", vmedia->combo_box_codec_index );
  g_print( "A INDEX : %d.\n", amedia->combo_box_codec_index );

  /* Put the name into the GtkEntry */
  gtk_entry_set_text(GTK_ENTRY(self->private->name_text), reglage->name);

  /* Put the description */
  gtk_text_buffer_set_text(self->private->preset_text_buffer, reglage->description, strlen(reglage->description));
  gtk_text_buffer_get_start_iter (self->private->desc_text_buffer, &self->private->start_description_iter );
  gtk_text_buffer_get_end_iter (self->private->desc_text_buffer, &self->private->end_description_iter );
  gtk_text_buffer_delete ( self->private->desc_text_buffer,
			   &self->private->start_description_iter,
			   &self->private->end_description_iter );
  gtk_text_buffer_set_text ( self->private->desc_text_buffer, reglage->description, strlen (reglage->description) );

  /* Put the Video entries */
  if (caps != NULL && (structure = gst_caps_get_structure (vmedia->caps, 0)))
    {
      val = (GValue *) gst_structure_get_value ( structure, "width");
      gtk_entry_set_text( GTK_ENTRY (self->private->size_width) , pitivi_newprojectwindow_getstr( g_value_get_int (val) ));
      
      val = (GValue *) gst_structure_get_value (structure, "height");
      gtk_entry_set_text( GTK_ENTRY (self->private->size_height ), pitivi_newprojectwindow_getstr( g_value_get_int (val) ));
      
      val = (GValue *) gst_structure_get_value (structure, "framerate"); 
      gtk_entry_set_text(GTK_ENTRY (self->private->fps_text ), pitivi_newprojectwindow_getstr( g_value_get_int (val) ));
      
      gtk_combo_box_set_active ( GTK_COMBO_BOX (self->private->video_combo_codec), vmedia->combo_box_codec_index );
    }

  /* Put the Audio entries */
  if (caps != NULL && (structure = gst_caps_get_structure (amedia->caps, 0)))
    {
      val = (GValue *) gst_structure_get_value ( structure, "channels");
      gtk_combo_box_set_active ( GTK_COMBO_BOX (self->private->audio_combo_codec), amedia->combo_box_codec_index );
      gtk_spin_button_set_value (GTK_SPIN_BUTTON (self->private->audio_combo_ech),
				 g_value_get_int (val));
    }
}

gchar *
pitivi_newprojectwindow_getstr(gint i)
{
  gchar  *str;
  gint   c;
  gint   d;
   
  str = malloc(sizeof (char *) * 2);
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
  GtkTreeIter		*iter;

  /* Creation de la vue */
  show_tree = gtk_tree_view_new_with_model(GTK_TREE_MODEL(self->private->tree));
  
  /* Creation de la premiere colonne */
  cell = gtk_cell_renderer_text_new();
  column = gtk_tree_view_column_new_with_attributes("Selection", cell, "text", TEXT_COLUMN, NULL);
  gtk_tree_view_column_set_sizing(column, GTK_TREE_VIEW_COLUMN_AUTOSIZE);
  /* Ajout de la colonne à la vue */
  gtk_tree_view_append_column(GTK_TREE_VIEW(show_tree), column);

  /* selection d'un element  */
  select = gtk_tree_view_get_selection(GTK_TREE_VIEW(show_tree));
  gtk_tree_selection_set_mode(select, GTK_SELECTION_SINGLE);

  gtk_tree_selection_set_select_function(select, (GtkTreeSelectionFunc)setting_is_selected,
					 (gpointer)(GTK_WIDGET(self)), NULL);
  gtk_tree_view_expand_all (GTK_TREE_VIEW (show_tree));

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
  /* Creation d'un notebook puis positionnement des onglets */
  notebook = gtk_notebook_new ();
  gtk_notebook_set_tab_pos (GTK_NOTEBOOK (notebook), GTK_POS_TOP);
  
  /* Appel a la fct pitivi_make_presets_hbox qui va remplir la hbox de l'onglet presets */
  presets_hbox = pitivi_make_presets_hbox(self);
  settings_table = pitivi_make_settings_table(self);
  
  /* Les deux widgets suivantes serviront a afficher le nom des deux onglets */
  presets = gtk_label_new("Presets");
  settings = gtk_label_new("Settings");
  
  /* On rattache les hbox presets et settings au notebook */
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
  
  /* Ajout d'une nouvelle frame dans la box presets_hbox globale */
  presets_frame = gtk_frame_new("Current setting");
  gtk_box_pack_start (GTK_BOX (presets_hbox), presets_frame, TRUE, TRUE, 5);
  
  /* Creation et Insertion du tableau dans la frame de reglages */
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

  categorie = pitivi_mainapp_get_selected_category( mainapp, self->private->position );
  if (categorie == NULL)
    return ;

  /* On recupere une copie du PitiviProjectSettings selectionne */
  settings = pitivi_projectsettings_copy ((PitiviProjectSettings *) g_slist_nth_data(categorie->list_settings, self->private->position[1]));

  /* Creation d'un nouveau projet avec ces settings */
  project = pitivi_project_new( settings );

  /* 
     Si on arrive a ajouter correctement le projet a mainapp alors on affiche les bonnes fenetres 

     P.S. c'est un peu cra-cra de faire comme ca, vaudrait mieux emmettre un signal et faire que
     ca soit le PitiviMainApp ou la PitiviToolboxWindow qui gere ca
  */
  if (pitivi_mainapp_add_project(mainapp, project))
    pitivi_mainapp_create_wintools (mainapp, project);
  
  gtk_widget_destroy (GTK_WIDGET (self));
}


GtkWidget*
pitivi_create_presets_table(PitiviNewProjectWindow *self)
{
  GtkTextIter		iter;
  GtkTextTagTable	*tag_table;
  gchar			*presets;
  GtkWidget		*button_new;
  GtkWidget		*button_cancel;
  GtkWidget		*text_presets;
  GtkWidget		*table;			/* contient la presets et les boutons New 
						   project et Annuler */

  /* Creation du champs texte de description */
  /* Creation de la Tag Table */
  tag_table = gtk_text_tag_table_new();
  /* Creation du buffer text */
  self->private->preset_text_buffer = gtk_text_buffer_new(tag_table);
  /* Creation du champs Text */
  presets = "Setting's descriptions";
  gtk_text_buffer_get_end_iter(self->private->preset_text_buffer, &iter);
  gtk_text_buffer_set_text (self->private->preset_text_buffer, presets, strlen(presets));
  /* gtk_text_buffer_insert_interactive(text_buffer, &iter, presets, strlen(presets), FALSE); */
  text_presets = gtk_text_view_new_with_buffer (self->private->preset_text_buffer);
  gtk_text_view_set_editable(GTK_TEXT_VIEW(text_presets), FALSE);
  gtk_text_view_set_right_margin  (GTK_TEXT_VIEW(text_presets), 5);
  gtk_text_view_set_left_margin  (GTK_TEXT_VIEW(text_presets), 5);
 
  /* Creation de la table */
  table = gtk_table_new(2, 2, FALSE);
  /* Insertion des cases du Tableau */
  /* Champs Texte de description du reglage selectionne */
  gtk_table_attach( GTK_TABLE(table),
		    text_presets,
		    0,2,0,1,
		    GTK_EXPAND | GTK_FILL, GTK_EXPAND | GTK_FILL,
		    5, 5);

  /* Bouton Nouveau projet */
  button_new = gtk_button_new_from_stock(GTK_STOCK_NEW);
  gtk_table_attach( GTK_TABLE(table),
		    button_new,
		    0,1,1,2,
		    GTK_EXPAND, FALSE,
		    1, 1);
  
  g_signal_connect(button_new, "clicked", G_CALLBACK(pitivi_create_new_project), self);

  /* Bouton Annuler projet */
  button_cancel = gtk_button_new_from_stock(GTK_STOCK_CANCEL);
  gtk_table_attach( GTK_TABLE(table),
		    button_cancel,
		    1,2,1,2,
		    GTK_EXPAND, FALSE,
		    1, 1);
  
  /* Signal emit lorsque le bouton Annuler est click& */
  g_signal_connect( G_OBJECT(button_cancel), "clicked",
		    G_CALLBACK(pitivi_newprojectwindow_close_window), 
		    (gpointer) (GTK_WIDGET(self)) );
  
  /* Retourne la table creee */
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
  
  /* Ligne 1 */
  name_frame = pitivi_make_name_frame(self);
  gtk_table_attach (GTK_TABLE(settings_table), name_frame,
		    0, 2, 0, 1, GTK_EXPAND | GTK_FILL, GTK_EXPAND | GTK_FILL, 0, 0);
  
  /* Ligne 2 */
  video_frame = pitivi_make_video_frame(self);

  gtk_table_attach (GTK_TABLE(settings_table), video_frame, 
		    0, 2, 1, 2, GTK_EXPAND | GTK_FILL, FALSE , 0, 0);
  
  /* Ligne 3 */
  audio_frame = pitivi_make_audio_frame(self);
  gtk_table_attach (GTK_TABLE(settings_table), audio_frame, 
		    0, 2, 2, 3, GTK_EXPAND | GTK_FILL, FALSE , 0, 0);
  
  /* Ligne 4 */
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
  
  /* Buttons Settings Signals */
  g_signal_connect( G_OBJECT(self->private->button_add), "clicked",
		    G_CALLBACK(pitivi_newprojectwindow_add_setting), (gpointer) (GTK_WIDGET(self)) );
  
  g_signal_connect( G_OBJECT(self->private->button_mod), "clicked",
		    G_CALLBACK(pitivi_modif_settings), (gpointer) (GTK_WIDGET(self)) );

  g_signal_connect( G_OBJECT(self->private->button_del), "clicked",
		    G_CALLBACK(pitivi_del_settings), (gpointer) (GTK_WIDGET(self)) );

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
		    G_CALLBACK(pitivi_add_category), (gpointer) (GTK_WIDGET(self)) );
  
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
  GstElementFactory	*factory;
  const gchar		*klass;
  const gchar		*name;
  const gchar		*short_name;
  const gchar		*desc;
  GtkWidget		*video_conf_but;
  GtkWidget		*rate_unit;
  GtkWidget		*resol_unit;
  GtkWidget		*blank1;
  GtkWidget		*blank2;
  GstElement		*element;
  int			i;  
  int			j;
  int			nb_videocodec;

  /* Creation de la frame "video" et du tableau principal */
  video_frame = gtk_frame_new("Video");
  video_table = gtk_table_new(2, 2, FALSE);

  nb_videocodec = 0;
  self->private->video_codec_list = gst_registry_pool_feature_list (GST_TYPE_ELEMENT_FACTORY);
  for (i = 0; self->private->video_codec_list != NULL; i++)
    {
      factory = (GstElementFactory *) self->private->video_codec_list->data;
      klass = gst_element_factory_get_klass (factory);
      name = gst_element_factory_get_longname (factory);
      if (!strncmp (klass, "Codec/Encoder/Video", 19))
	{
	  nb_videocodec++;
	}
      else
	{
	  goto next1;
	}
    next1:
      self->private->video_codec_list = self->private->video_codec_list->next;
    }
  /* liste des noms des codecs */
  self->private->video_tabname = g_malloc(sizeof(gchar **) * nb_videocodec);  
  j = 0;
  /* vcodec_hbox */
  vcodec_hbox = gtk_hbox_new(FALSE, 5);

  /* Premier label "codecs" */
  video_label_codec = gtk_label_new("Codecs : ");
  gtk_misc_set_alignment (GTK_MISC (video_label_codec), 0.0f, 0.0f);
  gtk_misc_set_padding (GTK_MISC (video_label_codec), 5, 0);
  gtk_table_attach (GTK_TABLE(video_table), video_label_codec, 
		    0, 1, 0, 1, GTK_FILL, FALSE, 5, 5);
  
  /*   Champ texte "codecs" */
  self->private->video_combo_codec = gtk_combo_box_new_text();

  self->private->video_codec_list = gst_registry_pool_feature_list (GST_TYPE_ELEMENT_FACTORY);
  for (i = 0; self->private->video_codec_list != NULL; i++)
    {
      factory = (GstElementFactory *) self->private->video_codec_list->data;
      klass = gst_element_factory_get_klass (factory);
      name = gst_element_factory_get_longname (factory);
      short_name = gst_plugin_feature_get_name (GST_PLUGIN_FEATURE(factory));
      if (!strncmp (klass, "Codec/Encoder/Video", 19))
	{
	  gtk_combo_box_insert_text (GTK_COMBO_BOX (self->private->video_combo_codec), i, name/* g_strdup (GST_PLUGIN_FEATURE (factory)->longname) */);
	  self->private->video_tabname[j] = g_strdup(short_name);
	  j++;
	}
      else
	{
	  goto next;
	}
    next:
      self->private->video_codec_list = self->private->video_codec_list->next;
    }

  /* Active le premier choix*/
  gtk_combo_box_set_active (GTK_COMBO_BOX (self->private->video_combo_codec), 0);
  gtk_box_pack_start(GTK_BOX (vcodec_hbox), self->private->video_combo_codec, TRUE, TRUE, 0);

  /* Bouton de configuration des codecs */
  video_conf_but = gtk_button_new_with_label("Configure");
  g_signal_connect(video_conf_but, "clicked", G_CALLBACK(create_codec_conf_video), self);
  gtk_box_pack_start(GTK_BOX (vcodec_hbox), video_conf_but, FALSE, FALSE, 0);
  gtk_table_attach (GTK_TABLE(video_table), vcodec_hbox,
		    1, 2, 0, 1, GTK_EXPAND | GTK_FILL, FALSE, 5, 5);

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
  GstElementFactory	*factory;
  GstElement		*element;
  GtkObject		*spin_adjustment;
  const gchar		*klass;
  const gchar		*name;
  const gchar		*short_name; 
  int			i;
  int			j;
  int			nb_audiocodec;

  /* Creation de la frame "audio" et du tableau principal */
  audio_frame = gtk_frame_new("Audio"); 
  audio_table = gtk_table_new(2, 2, FALSE);

  nb_audiocodec = 0;
  self->private->audio_codec_list = gst_registry_pool_feature_list (GST_TYPE_ELEMENT_FACTORY);
  for (i = 0; self->private->audio_codec_list != NULL; i++)
    {
      factory = (GstElementFactory *) self->private->audio_codec_list->data;
      klass = gst_element_factory_get_klass (factory);
      name = gst_element_factory_get_longname (factory);
      
      if (!strncmp (klass, "Codec/Encoder/Audio", 19))
	{
	  nb_audiocodec++;
	}
      else
	{
	  goto next1;
	}
    next1:
      self->private->audio_codec_list = self->private->audio_codec_list->next;
    }

  /*  nom des codecs  */
  self->private->audio_tabname = g_malloc(sizeof(gchar **) * nb_audiocodec);  
  j = 0;  
  /* Premier label "codecs" */
  audio_label_codec = gtk_label_new("Codecs : ");
  gtk_misc_set_alignment (GTK_MISC (audio_label_codec), 0.0f, 0.0f);
  gtk_misc_set_padding (GTK_MISC (audio_label_codec), 5, 0);
  gtk_table_attach (GTK_TABLE(audio_table), audio_label_codec, 
		    0, 1, 0, 1, GTK_FILL, FALSE, 5, 5);
 
  /* acodec_hbox */
  acodec_hbox = gtk_hbox_new(FALSE, 5);

  /*   Champ texte "codecs" */
  self->private->audio_combo_codec = gtk_combo_box_new_text();

  self->private->audio_codec_list = gst_registry_pool_feature_list (GST_TYPE_ELEMENT_FACTORY);
  for (i = 0; self->private->audio_codec_list != NULL; i++)
    {
      factory = (GstElementFactory *) self->private->audio_codec_list->data;
      klass = gst_element_factory_get_klass (factory);
      name = gst_element_factory_get_longname (factory);
      short_name = gst_plugin_feature_get_name (GST_PLUGIN_FEATURE(factory));

      if (!strncmp (klass, "Codec/Encoder/Audio", 19))
	{
	  gtk_combo_box_insert_text (GTK_COMBO_BOX (self->private->audio_combo_codec), i, name /* g_strdup (GST_PLUGIN_FEATURE (factory)->name) */);
	  self->private->audio_tabname[j] = g_strdup(short_name);
	  j++;
	}
      else
	{
	  goto next;
	}
    next:
      self->private->audio_codec_list = self->private->audio_codec_list->next;
    }

/*   while(self->private->audio_codecconflist) */
/*     { */
/*       g_print("OK : %s\n", self->private->audio_codecconflist->data); */
/*       self->private->audio_codecconflist->next; */
/*     } */
  gtk_combo_box_set_active(GTK_COMBO_BOX (self->private->audio_combo_codec), 0); /*  Choix par defaut */
  gtk_box_pack_start(GTK_BOX (acodec_hbox), self->private->audio_combo_codec, TRUE, TRUE, 0);

  /* Bouton de configuration des codecs */
  audio_conf_but = gtk_button_new_with_label("Configure");
  g_signal_connect(audio_conf_but, "clicked", G_CALLBACK(create_codec_conf_audio), self);
  gtk_box_pack_start(GTK_BOX (acodec_hbox), audio_conf_but, FALSE, FALSE, 0);
  gtk_table_attach (GTK_TABLE(audio_table), acodec_hbox, 
		    1, 2, 0, 1, GTK_EXPAND | GTK_FILL, FALSE, 5, 5);

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

void
create_codec_conf_video(GtkButton *button, gpointer user_data)
{
  PitiviNewProjectWindow	*self;
 /*  PitiviCodecConfWindow		*video_codecwindow; */
  PitiviConfProperties		*confprop;
  GstElementFactory		*factory;
  const gchar			*intern_name;
  GParamSpec			**property_specs;
  GParamSpec			*param;
  GstElement			*element;
  GtkWidget			*videoconf_vbox;
  GtkWidget			*videoconfprop_vbox;
  GtkWidget			*videoconfdesc_vbox;
  GtkWidget			*video_label_desc_conf;
  GtkWidget			*videoconf_frame1;
  GtkWidget			*videoconf_frame2;
  GtkWidget			*videoconf_hbox1;
  GtkWidget			*videoconf_hbox2;
  GtkWidget			*prop_name;
  GtkWidget			*prop_desc;
  GtkWidget			*prop_value_hbox;
  GtkWidget			*separator;
  GtkWidget			*videoconfprop_table;
  GtkWidget			*scroll;
  GtkWidget			*button_ok;
  GtkWidget			*button_reset;
  GtkWidget			*button_cancel;
  GtkWidget			*button_hbox;
  GList				*video_confprop_list;
  gboolean			readable;
  gchar				name;
  gint				num_properties;
  gint				active_combo;
  gint				nb;
  gint				i;

  self = (PitiviNewProjectWindow *) user_data;

  /* nouvelle fenetre */
  self->private->video_codecwindow = g_new0(PitiviCodecConfWindow, 1);
  self->private->video_codecwindow = pitivi_codecconfwindow_new();
  gtk_window_set_position(GTK_WINDOW (self->private->video_codecwindow), GTK_WIN_POS_CENTER);
  gtk_window_set_modal(GTK_WINDOW(self->private->video_codecwindow), TRUE);
  /*   gtk_widget_set_usize(GTK_WIDGET(self->private->video_codecwindow), 150, 150); */

  /* choix selectionne */
  active_combo = gtk_combo_box_get_active(GTK_COMBO_BOX(self->private->video_combo_codec));

  /* vbox contenant les deux frames */
  videoconf_vbox = gtk_vbox_new(FALSE, 0);

  /* Nouvelles frames */
  factory = gst_element_factory_find(self->private->video_tabname[active_combo]);
  
  /* frame 1 */
  videoconf_frame1 = gtk_frame_new(gst_element_factory_get_longname (factory));
  gtk_widget_queue_resize(GTK_WIDGET(videoconf_frame1));
  gtk_container_set_border_width (GTK_CONTAINER (videoconf_frame1), 5);

  /* frame 2 */
  videoconf_frame2 = gtk_frame_new("Properties");
  gtk_container_set_border_width (GTK_CONTAINER (videoconf_frame2), 5);

  /* vbox description*/
  videoconfdesc_vbox = gtk_vbox_new(FALSE, 0);
  gtk_container_set_border_width (GTK_CONTAINER (videoconfdesc_vbox), 20);
  video_label_desc_conf = gtk_label_new(gst_element_factory_get_description (factory));

  /* On link les widgets de la premiere frame dans videoconf_vbox */
  gtk_box_pack_start (GTK_BOX (videoconfdesc_vbox), video_label_desc_conf, FALSE, FALSE, 0);
  gtk_container_add(GTK_CONTAINER(videoconf_frame1), videoconfdesc_vbox);
  gtk_container_add(GTK_CONTAINER(videoconf_vbox), videoconf_frame1);

  /* vbox propriete */
  videoconfprop_vbox = gtk_vbox_new(FALSE, 0);
  gtk_container_set_border_width (GTK_CONTAINER (videoconfprop_vbox), 20);

  /* Recuperation des infos des proprietes*/
  intern_name = "Video Codec Configure";
  if (factory)
    {
      element = gst_element_factory_create(factory, intern_name);  
      property_specs = g_object_class_list_properties(G_OBJECT_GET_CLASS (element), &num_properties);
 
      /* Liste des proprietes */
      self->private->video_codecconflist = g_new0(GList, 1);
      self->private->video_codecconflist = NULL;
  
      if (num_properties < 2)
	{
	  /*       separator = gtk_hseparator_new(); */
	  prop_name = gtk_label_new("No property...");
	  /*       gtk_box_pack_start (GTK_BOX (videoconfprop_vbox), separator, TRUE, TRUE, 0); */
	  gtk_box_pack_start (GTK_BOX (videoconfprop_vbox), prop_name, FALSE, FALSE, 0);
	}
      else
	{
	  nb = (num_properties - 1);

	  for (i = 1; i < nb; i++)
	    {
	      GValue value = { 0, };
	      param = property_specs[i];
	      readable = FALSE;
      
	      g_value_init (&value, param->value_type);
	      if (param->flags & G_PARAM_READABLE)
		{
		  g_object_get_property (G_OBJECT (element), param->name, &value);
		  readable = TRUE;
		}
	      prop_value_hbox = gtk_hbox_new(TRUE, 0);
	      prop_name = gtk_label_new(g_strdup(g_param_spec_get_nick (param)));
	      gtk_misc_set_alignment(GTK_MISC (prop_name), 0.0f, 0.0f);
	      gtk_box_pack_start(GTK_BOX (prop_value_hbox), prop_name, TRUE, TRUE, 0);

	      /* parsage de "value" */
	      switch (G_VALUE_TYPE (&value))
		{
		case G_TYPE_STRING:
		  {
		    if (readable)
		      gtk_box_pack_start(GTK_BOX (prop_value_hbox), 
					 pitivi_conf_value_string(g_strdup(g_param_spec_get_nick (param)), value),
					 TRUE, TRUE, 0);
		    break;
		  }
		case G_TYPE_BOOLEAN:
		  {
		    if (readable)
		      gtk_box_pack_start(GTK_BOX (prop_value_hbox), 
					 pitivi_value_conf_boolean(g_strdup(g_param_spec_get_nick (param)), value),
					 TRUE, TRUE, 0);
		    break;
		  }
		case G_TYPE_UINT:
		  {
		    if (readable)
		      gtk_box_pack_start(GTK_BOX (prop_value_hbox), 
					 pitivi_value_conf_uint(g_strdup(g_param_spec_get_nick (param)), value, param), 
					 TRUE, TRUE, 0);
		    break;
		  }
		case G_TYPE_INT:
		  {
		    if (readable)
		      gtk_box_pack_start(GTK_BOX (prop_value_hbox),
					 pitivi_value_conf_int(g_strdup(g_param_spec_get_nick (param)), value, param),
					 TRUE, TRUE, 0);
		    break;
		  }
		case G_TYPE_UINT64:
		  {
		    if (readable)
		      gtk_box_pack_start(GTK_BOX (prop_value_hbox),
					 pitivi_value_conf_uint64(g_strdup(g_param_spec_get_nick (param)), value, param),
					 TRUE, TRUE, 0);
		    break;
		  }
		case G_TYPE_INT64:
		  {
		    if (readable)
		      gtk_box_pack_start(GTK_BOX (prop_value_hbox),
					 pitivi_value_conf_int64(g_strdup(g_param_spec_get_nick (param)), value, param),
					 TRUE, TRUE, 0);
		    break;
		  }
		case G_TYPE_ULONG:
		  {
		    if (readable)
		      gtk_box_pack_start(GTK_BOX (prop_value_hbox),
					 pitivi_value_conf_ulong(g_strdup(g_param_spec_get_nick (param)), value, param),
					 TRUE, TRUE, 0);
		    break;
		  }
		case G_TYPE_LONG:
		  {
		    if (readable)
		      gtk_box_pack_start(GTK_BOX (prop_value_hbox),
					 pitivi_value_conf_long(g_strdup(g_param_spec_get_nick (param)), value, param),
					 TRUE, TRUE, 0);
		    break;
		  }
	      
		case G_TYPE_FLOAT:
		  {
		    if (readable)
		      gtk_box_pack_start(GTK_BOX (prop_value_hbox),
					 pitivi_value_conf_float(g_strdup(g_param_spec_get_nick (param)), value, param),
					 TRUE, TRUE, 0);
		    break;
		  }
		case G_TYPE_DOUBLE:
		  {
		    if (readable)
		      gtk_box_pack_start(GTK_BOX (prop_value_hbox),
					 pitivi_value_conf_double(g_strdup(g_param_spec_get_nick (param)), value, param),
					 TRUE, TRUE, 0);
		    break;
		  }
		default:
		  {
		    gtk_box_pack_start(GTK_BOX (prop_value_hbox),
				       pitivi_value_conf_default(g_strdup(g_param_spec_get_nick (param)), value, param),
				       TRUE, TRUE, 0);
		    break;
		  }
		}

	      /* Separateur */
	      separator = gtk_hseparator_new();

	      /* Attributs text  a revoir */
	      PangoAttrList *desc = pango_attr_list_new();
	      PangoAttribute *desc_attr = pango_attr_style_new(PANGO_STYLE_ITALIC);
	      pango_attr_list_insert(desc, desc_attr);

	      /* description */
	      prop_desc = gtk_label_new(g_strdup(g_param_spec_get_blurb (param)));
	      gtk_label_set_line_wrap(GTK_LABEL(prop_desc), TRUE);
	      gtk_misc_set_alignment(GTK_MISC (prop_desc), 0.0f, 0.0f);
	      gtk_misc_set_padding(GTK_MISC (prop_desc), 5, 0);

	      /* italic */
	      gtk_label_set_attributes(GTK_LABEL(prop_desc), desc);


	      confprop = pitivi_setprop_new(g_strdup(g_param_spec_get_nick (param)), value, prop_value_hbox);
	      confprop = (gpointer) confprop;
	      g_object_set_data(G_OBJECT(prop_value_hbox), "prop", confprop);

	      /* link to vbox of properties */
	      gtk_box_pack_start (GTK_BOX (videoconfprop_vbox), prop_value_hbox, TRUE, TRUE, 0);
	      gtk_box_pack_start (GTK_BOX (videoconfprop_vbox), prop_desc, TRUE, TRUE, 0);
	      gtk_box_pack_start (GTK_BOX (videoconfprop_vbox), separator, TRUE, TRUE, 10);
	    }
	}
      scroll = gtk_scrolled_window_new(NULL, NULL);
      gtk_widget_set_usize (scroll, 600, 250);
      gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scroll),
				     GTK_POLICY_AUTOMATIC,
				     GTK_POLICY_AUTOMATIC);
      gtk_container_set_border_width (GTK_CONTAINER (scroll), 5);
      gtk_scrolled_window_add_with_viewport(GTK_SCROLLED_WINDOW(scroll), GTK_WIDGET(videoconfprop_vbox));
  
      gtk_container_add(GTK_CONTAINER(videoconf_frame2), scroll);
      gtk_container_add(GTK_CONTAINER(videoconf_vbox), videoconf_frame2);
  
      /* boutons "OK" et "Reset" */
      button_ok = gtk_button_new_with_label("Ok");
      button_reset = gtk_button_new_with_label("Reset");
      button_cancel = gtk_button_new_with_label("Cancel");
      button_hbox = gtk_hbox_new(TRUE, 0);
      gtk_box_pack_start (GTK_BOX (button_hbox), button_ok, FALSE, TRUE, 3);
      gtk_box_pack_start (GTK_BOX (button_hbox), button_reset, FALSE, TRUE, 3);
      gtk_box_pack_start (GTK_BOX (button_hbox), button_cancel, FALSE, TRUE, 3);
      gtk_container_set_border_width (GTK_CONTAINER (button_hbox), 5);
      gtk_container_add(GTK_CONTAINER(videoconf_vbox), button_hbox);
  
      /* liste des hbox */
      self->private->video_confboxlist = gtk_container_get_children(GTK_CONTAINER(videoconfprop_vbox));

      /* Signaux */
      g_signal_connect( G_OBJECT(button_cancel), "clicked",
			G_CALLBACK(pitivi_newprojectwindow_close_window), (gpointer) (GTK_WIDGET(self->private->video_codecwindow)) );
      g_signal_connect( G_OBJECT(button_ok), "clicked",
			G_CALLBACK(pitivi_valide_video_codec_conf), (gpointer) self );
      /* on link les contenus a la window mere */
      gtk_container_add (GTK_CONTAINER (self->private->video_codecwindow), videoconf_vbox);
      gtk_widget_show_all (GTK_WIDGET (self->private->video_codecwindow)); 
    }
}

void
create_codec_conf_audio(GtkButton *button, gpointer user_data)
{
  PitiviNewProjectWindow	*self;
  /*  PitiviCodecConfWindow		*audio_codecwindow; */
  PitiviConfProperties		*confprop;
  GstElementFactory		*factory;
  const gchar			*intern_name;
  GParamSpec			**property_specs;
  GParamSpec			*param;
  GstElement			*element;
  GtkWidget			*audioconf_vbox;
  GtkWidget			*audioconfprop_vbox;
  GtkWidget			*audioconfdesc_vbox;
  GtkWidget			*audio_label_desc_conf;
  GtkWidget			*audioconf_frame1;
  GtkWidget			*audioconf_frame2;
  GtkWidget			*audioconf_hbox1;
  GtkWidget			*audioconf_hbox2;
  GtkWidget			*prop_name;
  GtkWidget			*prop_desc;
  GtkWidget			*prop_value_hbox;
  GtkWidget			*separator;
  GtkWidget			*audioconfprop_table;
  GtkWidget			*scroll;
  GtkWidget			*button_ok;
  GtkWidget			*button_reset;
  GtkWidget			*button_cancel;
  GtkWidget			*button_hbox;
  GList				*audio_confprop_list;
  gboolean			readable;
  gchar				name;
  gint				num_properties;
  gint				active_combo;
  gint				nb;
  gint				i;

  self = (PitiviNewProjectWindow *) user_data;

  /* nouvelle fenetre */
  self->private->audio_codecwindow = g_new0(PitiviCodecConfWindow, 1);
  self->private->audio_codecwindow = pitivi_codecconfwindow_new();
  gtk_window_set_position(GTK_WINDOW (self->private->audio_codecwindow), GTK_WIN_POS_CENTER);
  gtk_window_set_modal(GTK_WINDOW(self->private->audio_codecwindow), TRUE);
  /*   gtk_widget_set_usize(GTK_WIDGET(self->private->audio_codecwindow), 150, 150); */

  /* choix selectionne */
  active_combo = gtk_combo_box_get_active(GTK_COMBO_BOX(self->private->audio_combo_codec));

  /* vbox contenant les deux frames */
  audioconf_vbox = gtk_vbox_new(FALSE, 0);

  /* Nouvelles frames */
  factory = gst_element_factory_find(self->private->audio_tabname[active_combo]);
  
  /* frame 1 */
  audioconf_frame1 = gtk_frame_new(gst_element_factory_get_longname (factory));
  gtk_widget_queue_resize(GTK_WIDGET(audioconf_frame1));
  gtk_container_set_border_width (GTK_CONTAINER (audioconf_frame1), 5);

  /* frame 2 */
  audioconf_frame2 = gtk_frame_new("Properties");
  gtk_container_set_border_width (GTK_CONTAINER (audioconf_frame2), 5);

  /* vbox description*/
  audioconfdesc_vbox = gtk_vbox_new(FALSE, 0);
  gtk_container_set_border_width (GTK_CONTAINER (audioconfdesc_vbox), 20);
  audio_label_desc_conf = gtk_label_new(gst_element_factory_get_description (factory));

  /* On link les widgets de la premiere frame dans audioconf_vbox */
  gtk_box_pack_start (GTK_BOX (audioconfdesc_vbox), audio_label_desc_conf, FALSE, FALSE, 0);
  gtk_container_add(GTK_CONTAINER(audioconf_frame1), audioconfdesc_vbox);
  gtk_container_add(GTK_CONTAINER(audioconf_vbox), audioconf_frame1);

  /* vbox propriete */
  audioconfprop_vbox = gtk_vbox_new(FALSE, 0);
  gtk_container_set_border_width (GTK_CONTAINER (audioconfprop_vbox), 20);

  /* Recuperation des infos des proprietes*/
  intern_name = "Audio Codec Configure";
  if (factory)
    {
      element = gst_element_factory_create(factory, intern_name);  
      property_specs = g_object_class_list_properties(G_OBJECT_GET_CLASS (element), &num_properties);
 
      /* Liste des proprietes */
      self->private->audio_codecconflist = g_new0(GList, 1);
      self->private->audio_codecconflist = NULL;
  
      if (num_properties < 2)
	{
	  /*       separator = gtk_hseparator_new(); */
	  prop_name = gtk_label_new("No property...");
	  /*       gtk_box_pack_start (GTK_BOX (audioconfprop_vbox), separator, TRUE, TRUE, 0); */
	  gtk_box_pack_start (GTK_BOX (audioconfprop_vbox), prop_name, FALSE, FALSE, 0);
	}
      else
	{
	  nb = (num_properties - 1);

	  for (i = 1; i < nb; i++)
	    {
	      GValue value = { 0, };
	      param = property_specs[i];
	      readable = FALSE;
      
	      g_value_init (&value, param->value_type);
	      if (param->flags & G_PARAM_READABLE)
		{
		  g_object_get_property (G_OBJECT (element), param->name, &value);
		  readable = TRUE;
		}
	      prop_value_hbox = gtk_hbox_new(TRUE, 0);
	      prop_name = gtk_label_new(g_strdup(g_param_spec_get_nick (param)));
	      gtk_misc_set_alignment(GTK_MISC (prop_name), 0.0f, 0.0f);
	      gtk_box_pack_start(GTK_BOX (prop_value_hbox), prop_name, TRUE, TRUE, 0);

	      /* parsage de "value" */
	      switch (G_VALUE_TYPE (&value))
		{
		case G_TYPE_STRING:
		  {
		    if (readable)
		      gtk_box_pack_start(GTK_BOX (prop_value_hbox), 
					 pitivi_conf_value_string(g_strdup(g_param_spec_get_nick (param)), value),
					 TRUE, TRUE, 0);
		    break;
		  }
		case G_TYPE_BOOLEAN:
		  {
		    if (readable)
		      gtk_box_pack_start(GTK_BOX (prop_value_hbox), 
					 pitivi_value_conf_boolean(g_strdup(g_param_spec_get_nick (param)), value),
					 TRUE, TRUE, 0);
		    break;
		  }
		case G_TYPE_UINT:
		  {
		    if (readable)
		      gtk_box_pack_start(GTK_BOX (prop_value_hbox), 
					 pitivi_value_conf_uint(g_strdup(g_param_spec_get_nick (param)), value, param), 
					 TRUE, TRUE, 0);
		    break;
		  }
		case G_TYPE_INT:
		  {
		    if (readable)
		      gtk_box_pack_start(GTK_BOX (prop_value_hbox),
					 pitivi_value_conf_int(g_strdup(g_param_spec_get_nick (param)), value, param),
					 TRUE, TRUE, 0);
		    break;
		  }
		case G_TYPE_UINT64:
		  {
		    if (readable)
		      gtk_box_pack_start(GTK_BOX (prop_value_hbox),
					 pitivi_value_conf_uint64(g_strdup(g_param_spec_get_nick (param)), value, param),
					 TRUE, TRUE, 0);
		    break;
		  }
		case G_TYPE_INT64:
		  {
		    if (readable)
		      gtk_box_pack_start(GTK_BOX (prop_value_hbox),
					 pitivi_value_conf_int64(g_strdup(g_param_spec_get_nick (param)), value, param),
					 TRUE, TRUE, 0);
		    break;
		  }
		case G_TYPE_ULONG:
		  {
		    if (readable)
		      gtk_box_pack_start(GTK_BOX (prop_value_hbox),
					 pitivi_value_conf_ulong(g_strdup(g_param_spec_get_nick (param)), value, param),
					 TRUE, TRUE, 0);
		    break;
		  }
		case G_TYPE_LONG:
		  {
		    if (readable)
		      gtk_box_pack_start(GTK_BOX (prop_value_hbox),
					 pitivi_value_conf_long(g_strdup(g_param_spec_get_nick (param)), value, param),
					 TRUE, TRUE, 0);
		    break;
		  }
	      
		case G_TYPE_FLOAT:
		  {
		    if (readable)
		      gtk_box_pack_start(GTK_BOX (prop_value_hbox),
					 pitivi_value_conf_float(g_strdup(g_param_spec_get_nick (param)), value, param),
					 TRUE, TRUE, 0);
		    break;
		  }
		case G_TYPE_DOUBLE:
		  {
		    if (readable)
		      gtk_box_pack_start(GTK_BOX (prop_value_hbox),
					 pitivi_value_conf_double(g_strdup(g_param_spec_get_nick (param)), value, param),
					 TRUE, TRUE, 0);
		    break;
		  }
		default:
		  {
		    gtk_box_pack_start(GTK_BOX (prop_value_hbox),
				       pitivi_value_conf_default(g_strdup(g_param_spec_get_nick (param)), value, param),
				       TRUE, TRUE, 0);
		    break;
		  }
		}

	      /* 	  PitiviRetProperties *confprop_tmp; */
	  
	      /* 	  while(self->private->audio_prop_list) */
	      /* 	    { */
	      /* 	      confprop_tmp = self->private->audio_prop_list->data; */
	      /* 	      g_print("prop list : %s\n", confprop_tmp->pname); */
	      /* 	      self->private->audio_prop_list = self->private->audio_prop_list->next; */
	      /* 	    } */
	  
	      /* Separateur */
	      separator = gtk_hseparator_new();

	      /* Attributs text  a revoir */
	      PangoAttrList *desc = pango_attr_list_new();
	      PangoAttribute *desc_attr = pango_attr_style_new(PANGO_STYLE_ITALIC);
	      pango_attr_list_insert(desc, desc_attr);

	      /* description */
	      prop_desc = gtk_label_new(g_strdup(g_param_spec_get_blurb (param)));
	      gtk_label_set_line_wrap(GTK_LABEL(prop_desc), TRUE);
	      gtk_misc_set_alignment(GTK_MISC (prop_desc), 0.0f, 0.0f);
	      gtk_misc_set_padding(GTK_MISC (prop_desc), 5, 0);
	  
	      /* italic */
	      gtk_label_set_attributes(GTK_LABEL(prop_desc), desc);


	      confprop = pitivi_setprop_new(g_strdup(g_param_spec_get_nick (param)), value, prop_value_hbox);
	      confprop = (gpointer) confprop;
	      g_object_set_data(G_OBJECT(prop_value_hbox), "prop", confprop);

	      /* link to vbox of properties */
	      gtk_box_pack_start (GTK_BOX (audioconfprop_vbox), prop_value_hbox, TRUE, TRUE, 0);
	      gtk_box_pack_start (GTK_BOX (audioconfprop_vbox), prop_desc, TRUE, TRUE, 0);
	      gtk_box_pack_start (GTK_BOX (audioconfprop_vbox), separator, TRUE, TRUE, 10);
	    }
	}
      scroll = gtk_scrolled_window_new(NULL, NULL);
      gtk_widget_set_usize (scroll, 600, 250);
      gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scroll),
				     GTK_POLICY_AUTOMATIC,
				     GTK_POLICY_AUTOMATIC);
      gtk_container_set_border_width (GTK_CONTAINER (scroll), 5);
      gtk_scrolled_window_add_with_viewport(GTK_SCROLLED_WINDOW(scroll), GTK_WIDGET(audioconfprop_vbox));
  
      gtk_container_add(GTK_CONTAINER(audioconf_frame2), scroll);
      gtk_container_add(GTK_CONTAINER(audioconf_vbox), audioconf_frame2);
  
      /* boutons "OK" et "Reset" */
      button_ok = gtk_button_new_with_label("Ok");
      button_reset = gtk_button_new_with_label("Reset");
      button_cancel = gtk_button_new_with_label("Cancel");
      button_hbox = gtk_hbox_new(TRUE, 0);
      gtk_box_pack_start (GTK_BOX (button_hbox), button_ok, FALSE, TRUE, 3);
      gtk_box_pack_start (GTK_BOX (button_hbox), button_reset, FALSE, TRUE, 3);
      gtk_box_pack_start (GTK_BOX (button_hbox), button_cancel, FALSE, TRUE, 3);
      gtk_container_set_border_width (GTK_CONTAINER (button_hbox), 5);
      gtk_container_add(GTK_CONTAINER(audioconf_vbox), button_hbox);
  
      /* liste des hbox */
      self->private->audio_confboxlist = gtk_container_get_children(GTK_CONTAINER(audioconfprop_vbox));

      /* Signaux */
      g_signal_connect( G_OBJECT(button_cancel), "clicked",
			G_CALLBACK(pitivi_newprojectwindow_close_window), (gpointer) (GTK_WIDGET(self->private->audio_codecwindow)) );
      g_signal_connect( G_OBJECT(button_ok), "clicked",
			G_CALLBACK(pitivi_valide_audio_codec_conf), (gpointer) self );
  
      /* on link les contenus a la window mere */
      gtk_container_add (GTK_CONTAINER (self->private->audio_codecwindow), audioconf_vbox);
      gtk_widget_show_all (GTK_WIDGET (self->private->audio_codecwindow)); 
    }
}

/* 
 * Fonctions d'affichage des proprietes des codecs
 */

GtkWidget *
pitivi_conf_value_string(const gchar *name, GValue value)
{
  const gchar		*string_val;
  GtkWidget		*prop_value_label;

  string_val = g_value_get_string (&value);

  if (string_val == NULL)
    prop_value_label = gtk_label_new("Default String Value"); 
  else
    prop_value_label = gtk_label_new(g_value_get_string(&value));
  return (prop_value_label);
}

GtkWidget *
pitivi_value_conf_boolean(const gchar *name, GValue value)
{
  GtkWidget		*radio_button_group;
  GSList		*radio_button_list;
  GtkWidget		*radio_button_true;
  GtkWidget		*radio_button_false;
  GtkWidget		*button_hbox;
		    
  button_hbox = gtk_hbox_new(0, FALSE);
		    
  /* Liste des boutons */
  radio_button_true = gtk_radio_button_new_with_label(NULL, "True");
  radio_button_list = gtk_radio_button_get_group(GTK_RADIO_BUTTON(radio_button_true));
  radio_button_false = gtk_radio_button_new_with_label(radio_button_list, "False");
		    
  /* On teste les proprietes a activer */
  if (g_value_get_boolean (&value))
    gtk_toggle_button_set_active(GTK_TOGGLE_BUTTON(radio_button_true), TRUE);
  else
    gtk_toggle_button_set_active(GTK_TOGGLE_BUTTON(radio_button_false), TRUE);

  gtk_box_pack_start(GTK_BOX (button_hbox), radio_button_true, TRUE, FALSE, 0);
  gtk_box_pack_start(GTK_BOX (button_hbox), radio_button_false, TRUE, TRUE, 0);
  return (button_hbox);
}

GtkWidget *
pitivi_value_conf_uint(const gchar *name, GValue value, GParamSpec	*param)
{
  GParamSpecUInt	*puint;
  GtkWidget		*spin_button;
  GtkWidget		*prop_value_hbox;

  puint = G_PARAM_SPEC_UINT (param);
  prop_value_hbox = gtk_hbox_new(0, FALSE);
  spin_button = gtk_spin_button_new_with_range(puint->minimum, puint->maximum, 1);
  /* valeur par defaut */
  gtk_spin_button_set_value(GTK_SPIN_BUTTON(spin_button), g_value_get_uint (&value));
  gtk_box_pack_start(GTK_BOX (prop_value_hbox), spin_button, TRUE, TRUE, 0);
  return (prop_value_hbox);
}

GtkWidget *
pitivi_value_conf_int(const gchar *name, GValue value, GParamSpec	*param)
{
  GParamSpecInt		*pint;  
  GtkWidget		*spin_button;
  GtkWidget		*prop_value_hbox;

  pint = G_PARAM_SPEC_INT (param);
  prop_value_hbox = gtk_hbox_new(0, FALSE);
  spin_button = gtk_spin_button_new_with_range(pint->minimum, pint->maximum, 1);
  /* valeur par defaut */
  gtk_spin_button_set_value(GTK_SPIN_BUTTON(spin_button), g_value_get_int (&value));
  gtk_box_pack_start(GTK_BOX (prop_value_hbox), spin_button, TRUE, TRUE, 0);
  return (prop_value_hbox);
}

GtkWidget *
pitivi_value_conf_uint64(const gchar *name, GValue value, GParamSpec *param)
{
  GParamSpecUInt64	*puint64;
  GtkWidget		*spin_button;
  GtkWidget		*prop_value_hbox;

  puint64 = G_PARAM_SPEC_UINT64 (param);
  prop_value_hbox = gtk_hbox_new(0, FALSE);
  spin_button = gtk_spin_button_new_with_range(puint64->minimum, puint64->maximum, 1);
  /* valeur par defaut */
  gtk_spin_button_set_value(GTK_SPIN_BUTTON(spin_button), g_value_get_uint64 (&value));
  gtk_box_pack_start(GTK_BOX (prop_value_hbox), spin_button, TRUE, TRUE, 0);
  return (prop_value_hbox);
}

GtkWidget *
pitivi_value_conf_int64(const gchar *name, GValue value, GParamSpec *param)
{
  GParamSpecInt64	*pint64;
  GtkWidget		*spin_button;
  GtkWidget		*prop_value_hbox;

  pint64 = G_PARAM_SPEC_INT64 (param);
  prop_value_hbox = gtk_hbox_new(0, FALSE);
  spin_button = gtk_spin_button_new_with_range(pint64->minimum, pint64->maximum, 1);
  /* valeur par defaut */
  gtk_spin_button_set_value(GTK_SPIN_BUTTON(spin_button), g_value_get_int64 (&value));
  gtk_box_pack_start(GTK_BOX (prop_value_hbox), spin_button, TRUE, TRUE, 0);
  return (prop_value_hbox);
}

GtkWidget *
pitivi_value_conf_ulong(const gchar *name, GValue value, GParamSpec *param)
{
  GParamSpecULong	*pulong;
  GtkWidget		*spin_button;
  GtkWidget		*prop_value_hbox;

  pulong = G_PARAM_SPEC_ULONG (param);
  prop_value_hbox = gtk_hbox_new(0, FALSE);
  spin_button = gtk_spin_button_new_with_range(pulong->minimum, pulong->maximum, 1);
  /* valeur par defaut */
  gtk_spin_button_set_value(GTK_SPIN_BUTTON(spin_button), g_value_get_ulong (&value));
  gtk_box_pack_start(GTK_BOX (prop_value_hbox), spin_button, TRUE, TRUE, 0);
  return (prop_value_hbox);
}

GtkWidget *
pitivi_value_conf_long(const gchar *name, GValue value, GParamSpec *param)
{
  GParamSpecLong	*plong;
  GtkWidget		*spin_button;
  GtkWidget		*prop_value_hbox;

  plong = G_PARAM_SPEC_LONG (param);
  prop_value_hbox = gtk_hbox_new(0, FALSE);
  spin_button = gtk_spin_button_new_with_range(plong->minimum, plong->maximum, 1);
  /* valeur par defaut */
  gtk_spin_button_set_value(GTK_SPIN_BUTTON(spin_button), g_value_get_long (&value));
  gtk_box_pack_start(GTK_BOX (prop_value_hbox), spin_button, TRUE, TRUE, 0);
  return (prop_value_hbox);
}

GtkWidget *
pitivi_value_conf_float(const gchar *name, GValue value, GParamSpec *param)
{
  GParamSpecFloat	*pfloat;
  GtkWidget		*spin_button;
  GtkWidget		*prop_value_hbox;

  pfloat = G_PARAM_SPEC_FLOAT (param);
  prop_value_hbox = gtk_hbox_new(0, FALSE);
  spin_button = gtk_spin_button_new_with_range(pfloat->minimum, pfloat->maximum, 1);
  /* valeur par defaut */
  gtk_spin_button_set_value(GTK_SPIN_BUTTON(spin_button), g_value_get_float (&value));
  gtk_box_pack_start(GTK_BOX (prop_value_hbox), spin_button, TRUE, TRUE, 0);
  return (prop_value_hbox);
}

GtkWidget *
pitivi_value_conf_double(const gchar *name, GValue value, GParamSpec *param)
{
  GParamSpecDouble	*pdouble;
  GtkWidget		*spin_button;
  GtkWidget		*prop_value_hbox;

  pdouble = G_PARAM_SPEC_DOUBLE (param);
  prop_value_hbox = gtk_hbox_new(0, FALSE);
  spin_button = gtk_spin_button_new_with_range(pdouble->minimum, pdouble->maximum, 1);
  /* valeur par defaut */
  gtk_spin_button_set_value(GTK_SPIN_BUTTON(spin_button), g_value_get_double (&value));
  gtk_box_pack_start(GTK_BOX (prop_value_hbox), spin_button, TRUE, TRUE, 0);
  return (prop_value_hbox);
}

GtkWidget *
pitivi_value_conf_default(const gchar *name, GValue value, GParamSpec *param)
{
  GtkWidget	*prop_value_hbox;
  GtkWidget	*prop_value_label;
  GtkWidget	*prop_value_combobox;
  gint		i;
  gint		*enum_values;
  gchar		*label;
  GList		*combobox_list;
  GList		*test_list;
 
  /*
    Dans ce cas la on ne renvoit pas la chaine de caractere mais l index de l element a seter
  */

  prop_value_combobox = gtk_combo_box_new_text();
  prop_value_hbox = gtk_hbox_new(0, FALSE);
  combobox_list = g_new0(GList, 1);

  if (G_IS_PARAM_SPEC_ENUM (param))
    {    
      GEnumClass *class = G_ENUM_CLASS (g_type_class_ref (param->value_type));
      enum_values = g_new0 (gint, class->n_values);
      
      for (i=0; i < class->n_values; i++)
	{
	  GEnumValue *evalue = &class->values[i];
                
	  enum_values[i] = evalue->value;
	  label = g_strdup_printf ("%s (%d)", evalue->value_nick, evalue->value);
	  gtk_combo_box_insert_text(GTK_COMBO_BOX (prop_value_combobox), i, label);
	  combobox_list = g_list_append(combobox_list, (gpointer)evalue->value_nick);
	}
      gtk_combo_box_set_active (GTK_COMBO_BOX (prop_value_combobox), g_value_get_enum(&value));
    }
  else
    prop_value_label = gtk_label_new("Default Case for Value");
  gtk_box_pack_start(GTK_BOX (prop_value_hbox), prop_value_combobox, TRUE, TRUE, 0);

  /* On attache la liste de la combobox */

  /*   while (combobox_list) */
  /*     { */
  /*       g_print("OK : %s\n", combobox_list->data); */
  /*       combobox_list = combobox_list->next; */
  /*     } */
  
  combobox_list = (gpointer) combobox_list;
  g_object_set_data(G_OBJECT(prop_value_hbox), "combo", combobox_list);
  return (prop_value_hbox);
}

void 
pitivi_valide_video_codec_conf(GtkButton *button, gpointer user_data)
{
  PitiviNewProjectWindow	*self;
  PitiviConfProperties		*confprop;
  PitiviRetProperties		*ret_confprop;
  gint				i;
  gint				spin;
  GtkWidget			*pwidget;
  GList				*plist;
  GList				*pwidget_hbox_list;
  GList				*pwidget_value_list;

  self = (PitiviNewProjectWindow *) user_data;
  confprop = (gpointer) g_new0(PitiviConfProperties, 1);
  ret_confprop = g_new0(PitiviRetProperties, 1);
  plist = self->private->video_confboxlist;

  self->private->video_prop_list = g_new0(GList, 1);

  i = 0;
  while (plist)
    {
      i++;
      pwidget = GTK_WIDGET(plist->data);
      if (g_object_get_data(G_OBJECT(pwidget), "prop"))
	{
	  confprop = g_object_get_data(G_OBJECT(pwidget), "prop");
	 /*  g_print("%d name : %s\n", i, confprop->pname); */

	  switch (G_VALUE_TYPE (&confprop->value))
	    {
	    case G_TYPE_STRING:
	      {
		g_print("String\n");
		break;
	      }
	    case G_TYPE_BOOLEAN:
	      {
		ret_confprop = pitivi_conf_boolean_update(confprop, self);
		break;
	      }
	    case G_TYPE_UINT:
	      {
		ret_confprop = pitivi_conf_int_update(confprop, self, "uint");
		break;
	      }
	    case G_TYPE_INT:
	      {
		ret_confprop = pitivi_conf_int_update(confprop, self, "int");
		break;
	      }
	    case G_TYPE_UINT64:
	      {
		ret_confprop = pitivi_conf_int_update(confprop, self, "uint64");
		break;
	      } 

	    case G_TYPE_INT64:
	      {
		ret_confprop = pitivi_conf_int_update(confprop, self, "int64");
		break;
	      }
	    case G_TYPE_ULONG:
	      {
		ret_confprop = pitivi_conf_int_update(confprop, self, "ulong");
		break;
	      }
	    case G_TYPE_LONG:
	      {
		ret_confprop = pitivi_conf_int_update(confprop, self, "long");
		break;
	      }
	    case G_TYPE_FLOAT:
	      {
		ret_confprop = pitivi_conf_float_update(confprop, self);
		break;
	      }
	    case G_TYPE_DOUBLE:
	      {
		ret_confprop = pitivi_conf_int_update(confprop, self, "double");
		break;
	      }
	    default:
	      {
		ret_confprop = pitivi_conf_default_update(confprop, self);
		break;
	      }
	    }
	}
/*       else */
/* 	g_print("%d No properties\n", i); */
      plist = plist->next;
      if (g_object_get_data(G_OBJECT(pwidget), "prop"))
	{
	  plist = plist->next;
	  plist = plist->next;
	}
      self->private->video_prop_list = g_list_append(self->private->video_prop_list, ret_confprop);
    }
/*   g_print("nombre de propriete : %d\n", i); */
  gtk_widget_destroy((gpointer) self->private->video_codecwindow);
}

void 
pitivi_valide_audio_codec_conf(GtkButton *button, gpointer user_data)
{
  PitiviNewProjectWindow	*self;
  PitiviConfProperties		*confprop;
  PitiviRetProperties		*ret_confprop;
  /*   PitiviRetProperties		*confprop_tmp; */
  gint				i;
  gint				spin;
  GtkWidget			*pwidget;
  GList				*plist;
  GList				*pwidget_hbox_list;
  GList				*pwidget_value_list;

  self = (PitiviNewProjectWindow *) user_data;
  confprop = (gpointer) g_new0(PitiviConfProperties, 1);
  ret_confprop = g_new0(PitiviRetProperties, 1);
  plist = self->private->audio_confboxlist;

  i = 0;
  while (plist)
    {
      i++;
      pwidget = GTK_WIDGET(plist->data);
      if (g_object_get_data(G_OBJECT(pwidget), "prop"))
	{
	  confprop = g_object_get_data(G_OBJECT(pwidget), "prop");
	/*   g_print("%d name : %s\n", i, confprop->pname); */

	  switch (G_VALUE_TYPE (&confprop->value))
	    {
	    case G_TYPE_STRING:
	      {
		g_print("String\n");
		break;
	      }
	    case G_TYPE_BOOLEAN:
	      {
		ret_confprop = pitivi_conf_boolean_update(confprop, self);
		break;
	      }
	    case G_TYPE_UINT:
	      {
		ret_confprop = pitivi_conf_int_update(confprop, self, "uint");
		break;
	      }
	    case G_TYPE_INT:
	      {
		ret_confprop = pitivi_conf_int_update(confprop, self, "int");
		break;
	      }
	    case G_TYPE_UINT64:
	      {
		ret_confprop = pitivi_conf_int_update(confprop, self, "uint64");
		break;
	      } 

	    case G_TYPE_INT64:
	      {
		ret_confprop = pitivi_conf_int_update(confprop, self, "int64");
		break;
	      }
	    case G_TYPE_ULONG:
	      {
		ret_confprop = pitivi_conf_int_update(confprop, self, "ulong");
		break;
	      }
	    case G_TYPE_LONG:
	      {
		ret_confprop = pitivi_conf_int_update(confprop, self, "long");
		break;
	      }
	    case G_TYPE_FLOAT:
	      {
		ret_confprop = pitivi_conf_float_update(confprop, self);
		break;
	      }
	    case G_TYPE_DOUBLE:
	      {
		ret_confprop = pitivi_conf_int_update(confprop, self, "double");
		break;
	      }
	    default:
	      {
		ret_confprop = pitivi_conf_default_update(confprop, self);
		break;
	      }
	    }
	}
    /*   else */
/* 	g_print("%d No properties\n", i); */
      plist = plist->next;
      if (g_object_get_data(G_OBJECT(pwidget), "prop"))
	{
	  plist = plist->next;
	  plist = plist->next;
	}
      self->private->audio_prop_list = g_list_append(self->private->audio_prop_list, ret_confprop);
    }
  /*   while(self->private->audio_prop_list) */
  /*     { */
  /*       confprop_tmp = self->private->audio_prop_list->data; */
  /*       g_print("prop list : %s\n", confprop_tmp->pname); */
  /*       self->private->audio_prop_list = self->private->audio_prop_list->next; */
  /*     } */
/*   g_print("nombre de propriete : %d\n", i); */
  gtk_widget_destroy((gpointer) self->private->audio_codecwindow);
}

PitiviRetProperties *
pitivi_conf_int_update(PitiviConfProperties *confprop, PitiviNewProjectWindow *self, gchar *type)
{
  PitiviRetProperties	*ret_confprop;
  GList			*pwidget_hbox_list;
  GList			*pwidget_value_list;
  gint			spin;

  pwidget_hbox_list = gtk_container_get_children(GTK_CONTAINER(confprop->pwidget));
  pwidget_hbox_list = pwidget_hbox_list->next;

  pwidget_value_list = gtk_container_get_children(GTK_CONTAINER(pwidget_hbox_list->data));
  spin = gtk_spin_button_get_value_as_int(GTK_SPIN_BUTTON(pwidget_value_list->data));

  ret_confprop = g_new0(PitiviRetProperties, 1);
  ret_confprop->pname = confprop->pname;
  if (type = "uint")
    {
      g_value_init(&ret_confprop->value, G_TYPE_UINT);
      g_value_set_uint(&ret_confprop->value, spin);
      /* g_print("UInt : %d\n\n", spin); */        
    }
  else if (type = "int")
    {
      g_value_init(&ret_confprop->value, G_TYPE_INT);
      g_value_set_int(&ret_confprop->value, spin);
	/* g_print("Int : %d\n\n", spin); */    
    }
  else if (type = "uin64t")
    {
      g_value_init(&ret_confprop->value, G_TYPE_UINT64);
      g_value_set_uint64(&ret_confprop->value, spin);
      /* g_print("UInt64 : %d\n\n", spin); */  
    }
  else if (type = "int64")
    {
      g_value_init(&ret_confprop->value, G_TYPE_INT64);
      g_value_set_int64(&ret_confprop->value, spin);
      /* g_print("Int64 : %d\n\n", spin); */  
    }
  else if (type = "ulong")
    {
      g_value_init(&ret_confprop->value, G_TYPE_ULONG);
      g_value_set_ulong(&ret_confprop->value, spin);
      /* g_print("ULong : %d\n\n", spin); */  
    }
  else if (type = "long")
    {
      g_value_init(&ret_confprop->value, G_TYPE_LONG);
      g_value_set_long(&ret_confprop->value, spin);
      /* g_print("Long : %d\n\n", spin); */  
    }
  else if (type = "double")
    {
      g_value_init(&ret_confprop->value, G_TYPE_DOUBLE);
      g_value_set_double(&ret_confprop->value, spin);
      /* g_print("Double : %d\n\n", spin); */  
    }
  return (ret_confprop);
}

PitiviRetProperties *
pitivi_conf_float_update(PitiviConfProperties *confprop, PitiviNewProjectWindow	*self)
{
  PitiviRetProperties	*ret_confprop;
  GList			*pwidget_hbox_list;
  GList			*pwidget_value_list;
  gint			spin;

  pwidget_hbox_list = gtk_container_get_children(GTK_CONTAINER(confprop->pwidget));
  pwidget_hbox_list = pwidget_hbox_list->next;

  pwidget_value_list = gtk_container_get_children(GTK_CONTAINER(pwidget_hbox_list->data));

  spin = gtk_spin_button_get_value_as_float(GTK_SPIN_BUTTON(pwidget_value_list->data));

  ret_confprop = g_new0(PitiviRetProperties, 1);
  ret_confprop->pname = confprop->pname;

  g_value_init(&ret_confprop->value, G_TYPE_FLOAT);
  g_value_set_float(&ret_confprop->value, spin);
  /*   g_print("Float : %d\n\n", spin); */
  return (ret_confprop);
}

PitiviRetProperties *
pitivi_conf_boolean_update(PitiviConfProperties *confprop, PitiviNewProjectWindow *self)
{
  PitiviRetProperties	*ret_confprop;
  GList			*pwidget_hbox_list;
  GList			*pwidget_value_list;
  gboolean		bool;

  pwidget_hbox_list = gtk_container_get_children(GTK_CONTAINER(confprop->pwidget));
  pwidget_hbox_list = pwidget_hbox_list->next;

  pwidget_value_list = gtk_container_get_children(GTK_CONTAINER(pwidget_hbox_list->data));

  /* On ne teste que le premier bouton (c est le true) */
  bool = gtk_toggle_button_get_active(GTK_TOGGLE_BUTTON(pwidget_value_list->data));
  /*  if (bool) */
  /*     g_print("Le bouton True est actif\n\n"); */
  /*   else */
  /*     g_print("Le bouton False est actif\n\n"); */
  
  ret_confprop = g_new0(PitiviRetProperties, 1);
  ret_confprop->pname = confprop->pname;

  g_value_init(&ret_confprop->value, G_TYPE_BOOLEAN);
  g_value_set_boolean(&ret_confprop->value, bool);
  return (ret_confprop);
}

PitiviRetProperties *
pitivi_conf_default_update(PitiviConfProperties *confprop, PitiviNewProjectWindow *self)
{
  PitiviRetProperties	*ret_confprop;
  PitiviConfProperties	*new_confprop;
  GList			*pwidget_hbox_list;
  GList			*pwidget_value_list;
  GList			*combobox_list;
  gchar			*tmp;
  gint			i;


  new_confprop = pitivi_setprop_new(confprop->pname, confprop->value, confprop->pwidget);
  pwidget_hbox_list = g_new0(GList, 1);
  pwidget_hbox_list = g_new0(GList, 1);
  combobox_list = g_new0(GList, 1);

  pwidget_hbox_list = gtk_container_get_children(GTK_CONTAINER(new_confprop->pwidget));
  pwidget_hbox_list = pwidget_hbox_list->next;

  pwidget_value_list = gtk_container_get_children(GTK_CONTAINER(pwidget_hbox_list->data));

  /* On va chercher la liste de la combobox */
  combobox_list = g_object_get_data(G_OBJECT(pwidget_value_list->data), "combo");  

  /*   while(combobox_list) */
  /*     { */
  /*       g_print("OK 3 : %s\n", combobox_list->data); */
  /*       combobox_list = combobox_list->next; */
  /*     } */
  
  /* On recupere l index de celui qui est actif  */
  i = gtk_combo_box_get_active(GTK_COMBO_BOX(pwidget_value_list->data));

  ret_confprop = g_new0(PitiviRetProperties, 1);
  ret_confprop->pname = confprop->pname;
  g_value_init(&ret_confprop->value, G_TYPE_INT);
  g_value_set_int(&ret_confprop->value, i);

  /*   g_value_init(&ret_confprop->value, G_TYPE_STRING); */
  /*   g_value_take_string (&ret_confprop->value, tmp); */
  /*     g_print("%s\n\n", combobox_tab[i]); */
  return (ret_confprop);
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

  newprojectwindow->private->position = g_new0(gint, 2);

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
