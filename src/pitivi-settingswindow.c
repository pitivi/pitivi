/* 
 * PiTiVi
 * Copyright (C) <2004> Delettrez Marc	<delett_m@epita.fr>
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
#include "pitivi-mainapp.h"
#include "pitivi-settingswindow.h"
#include "pitivi-settings.h"
#include "pitivi-gstelementsettings.h"

#define	X_SPACE_TAB	5
#define Y_SPACE_TAB	5
#define BORDER		5
#define W_COMBO_BOX	100


static     PitiviWindowsClass *parent_class;


struct _PitiviSettingsWindowPrivate
{
  /* instance private members */
  gboolean	dispose_has_run;

  GtkWidget	*MainBox;

  GtkWidget	*Tab;
  GtkWidget	*TabContainer;
  GtkWidget	*TabCodec;
  GtkWidget	*TabParser;
  GtkWidget	*TabOut;
  GtkWidget	*TabIn;

  GtkWidget	*ButtonBox;
  GtkWidget	*ButtonOk;
  GtkWidget	*ButtonCancel;
  
  GtkTooltips	*Ttips;
  PitiviSettings *settings;
};

/*
 *
 * CALL BACK
 *
 */

GstElementFactory *
pitivi_settingswindow_get_row_list (GList *List, gint row)
{
  gint cpt;

  for (cpt = 0; List; List = g_list_next (List), cpt++) {
    if (cpt == row) {
      return (List->data);
    }
  }
  return (NULL);
}

GstElementFactory *
pitivi_settingswindow_combobox_get_active (GtkWidget *widget)
{
  GstElementFactory *elm;
  
  elm = pitivi_settingswindow_get_row_list 
    (g_object_get_data (G_OBJECT (widget), "list"), 
    gtk_combo_box_get_active (GTK_COMBO_BOX (widget)));
  return (elm);
}

void 
pitivi_settingswindow_accept_reponse (PitiviGstElementSettings *prop, PitiviSettingsWindow *self)
{
  PitiviSettingsIoElement	*elm_info;
  
  elm_info = NULL;
  g_print ("######################################################\n");
  g_print ("ACCEPT\n");
  g_print ("SAVE %s [%s]\n", prop->elm, prop->class);

  elm_info = pitivi_settings_get_io_settings_struct_info (self->private->settings, gst_element_factory_find (prop->elm));

  /*
    GList				*pt;
    //GList				*list;
    
    if (!strcmp (prop->class, "Sink/Video")) {
    elm_info = pitivi_settings_get_io_settings_struct_info
    (self->private->settings->elm_video_out, prop->elm);
    } else if (!strcmp (prop->class, "Sink/Audio")) {
    elm_info = pitivi_settings_get_io_settings_struct_info
    (self->private->settings->elm_audio_out, prop->elm);
    } else if (!strcmp (prop->class, "Source/Video")) {
    elm_info = pitivi_settings_get_io_settings_struct_info
    (self->private->settings->elm_video_in, prop->elm);
    } else if (!strcmp (prop->class, "Source/Audio")) {
    elm_info = pitivi_settings_get_io_settings_struct_info
    (self->private->settings->elm_audio_in, prop->elm);
    }
    
    if (elm_info) {
    pt = elm_info->prop_list;
    for (; pt; pt = g_list_next (pt)) {
    PitiviSettingsProp *prop2 = (PitiviSettingsProp *) pt->data;
    
    g_free (prop2->name);
    g_free (pt->data);
    }
    
    g_list_free (elm_info->prop_list);
    
    elm_info->prop_list = pitivi_gstelementsettings_get_list (prop);
    }
  */

  /*
    for (; list; list = g_list_next (list)) {
    PitiviGstElementSettingsProp *prop = (PitiviGstElementSettingsProp *) list->data;
    g_print ("------------------------\n");
    g_print ("name:%s\n", prop->name);
    g_print ("value:%s\n", g_strdup_value_contents (&(prop->value)));
    }
  */

  g_print ("######################################################\n");

  return ;
}

GstElement *
pitivi_settingswindow_make_element (PitiviSettings *self, GstElementFactory *factory)
{
  GList		*prop_list;
  GstElement	*elm;

  elm = gst_element_factory_create (factory, "elm_tmp");

  prop_list = NULL;

  /*
    prop_list = pitivi_settings_get_io_prop_list 
    (self, (gchar *) gst_plugin_feature_get_name (GST_PLUGIN_FEATURE(factory)));
    
    for (; prop_list; prop_list = g_list_next (prop_list)) {
    PitiviSettingsProp *prop = (PitiviSettingsProp *) prop_list->data;
    
    g_object_set_property (G_OBJECT (elm), prop->name, &(prop->value));
    }
  */

  return (elm);
}

void
pitivi_settingswindow_cb_button (GtkWidget *widget, gpointer data)
{
  GstElement		*my_elm;
  PitiviSettingsWindow	*self;
  GtkWidget		*ComboBox = (GtkWidget *) data;
  GtkWidget		*Dialog;
  GstElementFactory	*elm;
  gint			result;
  gchar			*elm_name;
  PitiviGstElementSettings *Properties;

  self = (PitiviSettingsWindow *) g_object_get_data (G_OBJECT (ComboBox), "self");

  elm = pitivi_settingswindow_combobox_get_active (ComboBox);

  Dialog = gtk_dialog_new ();

  elm_name = g_strdup ((gchar *) gst_plugin_feature_get_name (GST_PLUGIN_FEATURE(elm)));

  gtk_window_set_title (GTK_WINDOW (Dialog), elm_name);

  gtk_window_set_resizable (GTK_WINDOW (Dialog), FALSE);

  ////////////////////////////
  ////////// creer l element en fonction des settings deja present
  ////////////////////////////
  
  my_elm = pitivi_settingswindow_make_element (self->private->settings, elm);

  //Properties = pitivi_gstelementsettings_new_with_name (elm_name); 
  Properties = pitivi_gstelementsettings_new_with_elm (my_elm, 0); 

  gtk_container_add (GTK_CONTAINER (GTK_DIALOG(Dialog)->vbox),
		     GTK_WIDGET (Properties));

  gtk_dialog_add_buttons (GTK_DIALOG (Dialog),
			  GTK_STOCK_CANCEL,
			  GTK_RESPONSE_REJECT,
			  GTK_STOCK_OK,
			  GTK_RESPONSE_ACCEPT,
			  NULL);

  gtk_widget_show_all (GTK_WIDGET (Dialog));

  result  = gtk_dialog_run (GTK_DIALOG (Dialog));
  switch (result) {
  case GTK_RESPONSE_ACCEPT:
    pitivi_settingswindow_accept_reponse (Properties, self);
    break;
    /*   default: */
    /*     g_print ("CANCEL\n"); */
    /*     break; */
  }

  g_free (elm_name);
  gtk_widget_destroy (Dialog);

  return ;
}

void
pitivi_settingswindow_cb_destroy (GtkWidget *widget, gpointer data)
{
  /*   PitiviSettingsWindow *self = (PitiviSettingsWindow *) data; */
  
  /* TODO : do we need to do something when we destroy this window ?? */
  //g_print ("SETTINGS DESTROY\n");  
  return ;
}

GList *
pitivi_settings_new_list (GList *old, gint num)
{
  gint	cpt;
  GList *list;

  list = NULL;
  list = g_list_append (list , 
			pitivi_settingswindow_get_row_list (old, num));
  for (cpt = 0; old; old = g_list_next (old), cpt++) {
    if (cpt != num) {
      list = g_list_append (list , old->data);
    }
  }
  return (list);
}

GList *
pitivi_settings_get_pointer (GList *elm, gint row, gint col)
{
  gint cpt;

  for (cpt = 1; elm; elm = g_list_next (elm), cpt++) {
    if (row == cpt) {
      PitiviSettingsMimeType *tmp = (PitiviSettingsMimeType *) elm->data;

      if (col == 1) {
	return (tmp->decoder);
      } else if (col == 2) {
	return (tmp->encoder);
      }      
    }
  }
  return (NULL);
}

void
pitivi_settingswindow_save_settings (GList *elm, GtkWidget *widget)
{
  GList *list;

  list = GTK_TABLE (widget)->children;
  for (; list; list = g_list_next (list)) {
    GtkTableChild *tmp = (GtkTableChild *) list->data;

    if (GTK_IS_COMBO_BOX (tmp->widget)) {
      gint	num;
      
      num = gtk_combo_box_get_active (GTK_COMBO_BOX (tmp->widget));
      if (num) {
	g_print ("Value Change\n");
	/*
	  GList *new_list;
	  GList *old_list;
	  
	  old_list = g_object_get_data (G_OBJECT (tmp->widget), "list");
	  new_list = pitivi_settings_new_list (old_list, num);

	  pitivi_settings_replace_list (pitivi_settings_get_pointer 
	  (elm, 
	  (gint) g_object_get_data 
	  (G_OBJECT (tmp->widget), "row"),
	  (gint) g_object_get_data 
	  (G_OBJECT (tmp->widget), "col")),
	  new_list);
	*/
      }

    }
  }
  return ;
}

void 
pitivi_settingswindow_cb_ok (GtkWidget *widget, gpointer data)
{
  PitiviSettingsWindow *self = (PitiviSettingsWindow *) data;

  pitivi_settingswindow_save_settings (self->private->settings->container, 
				       self->private->TabContainer);
  pitivi_settingswindow_save_settings (self->private->settings->parser, 
				       self->private->TabParser);
  pitivi_settingswindow_save_settings (self->private->settings->codec, 
				       self->private->TabCodec);
  g_print ("SETTINGS OK\n");
  gtk_widget_destroy (GTK_WIDGET (self));
  return ;
}

void 
pitivi_settingswindow_cb_cancel (GtkWidget *widget, gpointer data)
{
  PitiviSettingsWindow *self = (PitiviSettingsWindow *) data;

  g_print ("SETTINGS CANCEL\n");
  gtk_widget_destroy (GTK_WIDGET (self));
  return ;
}

/*
 * 
 * WIDGETS
 *
*/

void
pitivi_settingswindow_table_widget_add (GtkWidget *Table, GtkWidget *widget, gint row, gint col)
{
  gtk_table_attach(GTK_TABLE(Table), widget,
		   col, col+1, row, row+1, 
		   GTK_FILL, GTK_FILL,
		   X_SPACE_TAB, Y_SPACE_TAB);
  return ;
}

void
pitivi_settingswindow_ajout_button (GtkWidget *Table, gint row, gint col, 
				    gchar *stock_id, gpointer pt)
{
  GtkWidget	*Button;
  
  Button = gtk_button_new_from_stock (stock_id);
  g_signal_connect (G_OBJECT (Button), "clicked",
		    G_CALLBACK (pitivi_settingswindow_cb_button), pt);
/*   g_object_set (G_OBJECT (Button), "sensitive", FALSE, NULL); */
  pitivi_settingswindow_table_widget_add (Table, Button, row, col);
  gtk_widget_show (Button);

  return ;
}

void
pitivi_settingswindow_ajout_label (GtkWidget *Table, gint row, gint col, gchar *lname)
{
  GtkWidget	*Label;
  
  Label = gtk_label_new (NULL);
  gtk_label_set_markup(GTK_LABEL (Label), lname);
  gtk_misc_set_alignment (GTK_MISC (Label), 0.0, 0.5);
  pitivi_settingswindow_table_widget_add (Table, Label, row, col);
  gtk_widget_show (Label);

  return ;
}

GtkWidget *
pitivi_settingswindow_ajout_combobox (GtkWidget *Table, gint row, gint col, GList *List)
{
  GtkWidget	*combobox;
  GList		*sv;
  
  combobox = gtk_combo_box_new_text ();
  for (sv = List; List; List = g_list_next (List)) {
    gtk_combo_box_append_text (GTK_COMBO_BOX (combobox), (gchar *) List->data);
  }
  gtk_combo_box_set_active (GTK_COMBO_BOX (combobox), 0);  
  //gtk_combo_box_set_wrap_width (GTK_COMBO_BOX (combobox), W_COMBO_BOX);
  g_object_set_data (G_OBJECT (combobox), "list", sv);
  g_object_set_data (G_OBJECT (combobox), "row", GINT_TO_POINTER (row));
  g_object_set_data (G_OBJECT (combobox), "col", GINT_TO_POINTER (col));
  pitivi_settingswindow_table_widget_add (Table, combobox, row, col);
  gtk_widget_show (combobox);

  return (combobox);
}

void
pitivi_settingswindow_create_row_header (GtkWidget *Table)
{
  pitivi_settingswindow_ajout_label (Table, 0, 0, 
				     g_locale_to_utf8 
				     ("<b>Flux</b>", -1, NULL, NULL, NULL));
  pitivi_settingswindow_ajout_label (Table, 0, 1, 
				     g_locale_to_utf8 
				     ("<b>Decoder</b>", -1, NULL, NULL, NULL));
  pitivi_settingswindow_ajout_label (Table, 0, 2, 
				     g_locale_to_utf8 
				     ("<b>Encoder</b>", -1, NULL, NULL, NULL));

  return ;
}

void
pitivi_settingswindow_ajout_coder (GtkWidget *Box, gint row, gint col, GList *List)
{
  if (List) {
    gint length;
    
    length = g_list_length (List);
    if (length != 1) {
      pitivi_settingswindow_ajout_combobox (Box, row, col, List);
    } else {
      pitivi_settingswindow_ajout_label (Box, row, col, List->data);
    }
  } else {
    pitivi_settingswindow_ajout_label (Box, row, col, 
				       g_locale_to_utf8 ("<span foreground=\"#FF0000\" style=\"oblique\">Empty</span>", 
							 -1, NULL, NULL, NULL)
				       );
  }  
  return ;
}

gchar *
pitivi_settingswindow_format_flux (GstCaps *flux)
{
  gchar *str;
  gchar **tmp;

  str = gst_caps_to_string (flux);
  tmp = g_strsplit (str, ",", 0);
  return (tmp[0]);
}

void
pitivi_settingswindow_ajout_label_tips (GtkWidget *Table, gint row, gint col, gchar *lname, gchar *tips)
{
  GtkWidget	*Label;
  GtkWidget	*EventBox;
  GtkTooltips	*Ttips;

  Ttips = gtk_tooltips_new ();

  EventBox = gtk_event_box_new ();
  pitivi_settingswindow_table_widget_add (Table, EventBox, row, col);
  gtk_widget_show (EventBox);

  gtk_tooltips_set_tip (Ttips, EventBox, tips, NULL);

  Label = gtk_label_new (NULL);
  gtk_label_set_markup(GTK_LABEL (Label), lname);
  gtk_misc_set_alignment (GTK_MISC (Label), 0.0, 0.5);
  gtk_container_add (GTK_CONTAINER (EventBox), Label);
  gtk_widget_show (Label);

  return ;
}

void
pitivi_settingswindow_aff_row (GtkWidget *Table, PitiviSettingsMimeType *mime, gint row)
{
  pitivi_settingswindow_ajout_label_tips (Table, row, 0, pitivi_settingswindow_format_flux (mime->flux), 
					  gst_caps_to_string (mime->flux));
  pitivi_settingswindow_ajout_coder (Table, row, 1, mime->decoder);
  pitivi_settingswindow_ajout_coder (Table, row, 2, mime->encoder);

  return ;
}

GtkWidget *
pitivi_settingswindow_create_table (GtkWidget *frame, GList *List)
{
  gint		cpt;
  gint		length;
  GtkWidget	*Table;
  GtkWidget	*ScrollBar;

  length = g_list_length (List);

  ScrollBar = gtk_scrolled_window_new(NULL, NULL);
  gtk_container_set_border_width (GTK_CONTAINER (ScrollBar), BORDER);
  gtk_container_add(GTK_CONTAINER (frame), ScrollBar);
  gtk_scrolled_window_set_policy (GTK_SCROLLED_WINDOW (ScrollBar), 
				 GTK_POLICY_AUTOMATIC, 
				 GTK_POLICY_AUTOMATIC);
  gtk_widget_show (ScrollBar);

  Table = gtk_table_new (length+1, 3, FALSE);
  gtk_container_set_border_width (GTK_CONTAINER (Table), BORDER);
  gtk_scrolled_window_add_with_viewport (GTK_SCROLLED_WINDOW (ScrollBar), Table);
  gtk_widget_show (Table);

  pitivi_settingswindow_create_row_header (Table);

  for (cpt = 1; List; List = g_list_next (List), cpt++) {
    pitivi_settingswindow_aff_row (Table, List->data, cpt);
  }

  return (Table);
}

GtkWidget *
pitivi_settingswindow_ajout_inout_combobox (GtkWidget *Table, gint row, gint col, GList *List, gchar *path)
{
  GtkWidget	*combobox;
  GList		*sv;
  GstElementFactory	*factory;

  combobox = gtk_combo_box_new_text ();
  for (sv = NULL; List; List = g_list_next (List)) {
    factory = (GstElementFactory *) List->data;
    if (!strcmp (path, gst_element_factory_get_klass (factory))) {
      sv = g_list_append (sv, factory);
      gtk_combo_box_append_text (GTK_COMBO_BOX (combobox), 
				 g_strdup_printf ("%s [%s]",
						  (gchar *) gst_element_factory_get_longname (factory),
						  (gchar *) gst_plugin_feature_get_name (GST_PLUGIN_FEATURE(factory))));
    }
  }
  gtk_combo_box_set_active (GTK_COMBO_BOX (combobox), 0);  
  g_object_set_data (G_OBJECT (combobox), "list", sv);
  g_object_set_data (G_OBJECT (combobox), "row", GINT_TO_POINTER (row));
  g_object_set_data (G_OBJECT (combobox), "col", GINT_TO_POINTER (col));
  pitivi_settingswindow_table_widget_add (Table, combobox, row, col);
  gtk_widget_show (combobox);

  return (combobox);
}

void
pitivi_settingswindow_create_row_table_InOut (PitiviSettingsWindow *self,
					      GList *element, GtkWidget *table, 
					      gchar *io, gchar *type, gint row)
{
  GtkWidget *ComboBox;

  pitivi_settingswindow_ajout_label (table, row, 0, g_strdup_printf ("%s%s:\t", type, io));
  ComboBox = pitivi_settingswindow_ajout_inout_combobox (table, row, 1, element, g_strdup_printf ("%s/%s", io, type));
  pitivi_settingswindow_ajout_button (table, row, 2, GTK_STOCK_PREFERENCES, ComboBox);
  g_object_set_data (G_OBJECT (ComboBox), "self", self);

  return ;
}

GtkWidget *
pitivi_settingswindow_create_frame_InOut (PitiviSettingsWindow *self, 
					  GList *element, GtkWidget *table, gchar *io)
{
  GtkWidget *Tab;
  GtkWidget *Frame;

  Frame = gtk_frame_new (io);
  gtk_container_set_border_width (GTK_CONTAINER (Frame), BORDER);
  gtk_box_pack_start (GTK_BOX (table), 
		     Frame,
		     FALSE, FALSE, 0);
  gtk_widget_show (Frame);

  Tab = gtk_table_new (2, 3, FALSE);
  gtk_container_set_border_width (GTK_CONTAINER (Tab), BORDER);
  gtk_container_add (GTK_CONTAINER (Frame), Tab);
  gtk_widget_show (Tab);

  pitivi_settingswindow_create_row_table_InOut (self, element, Tab, io, "Video", 0);
  pitivi_settingswindow_create_row_table_InOut (self, element, Tab, io, "Audio", 1);

  return (Tab);
}

void
pitivi_settingswindow_create_table_InOut (PitiviSettingsWindow *self, GList *element, GtkWidget *frame)
{
  GtkWidget *Table;

  Table = gtk_vbox_new (FALSE, 2);
  gtk_container_add(GTK_CONTAINER (frame), Table);
  gtk_widget_show (Table);

  self->private->TabIn = pitivi_settingswindow_create_frame_InOut (self, element, Table, "Source");
  self->private->TabOut = pitivi_settingswindow_create_frame_InOut (self, element, Table, "Sink");

  return ;
}

GtkWidget *
pitivi_settingswindow_create_frame (GtkWidget *widget, gchar *title, gchar *lname)
{
  GtkWidget	*frame;
  GtkWidget	*label;

  frame = gtk_frame_new (lname);
  gtk_container_set_border_width (GTK_CONTAINER (frame), BORDER);
  gtk_widget_show (frame);  
  label = gtk_label_new (title);
  gtk_notebook_prepend_page (GTK_NOTEBOOK (widget), frame, label);

  return (frame);
}

void
pitivi_settingswindow_create_all_frames (PitiviSettingsWindow *self)
{
  PitiviMainApp		*mainapp = ((PitiviWindows *) self)->mainapp;

  self->private->settings = PITIVI_SETTINGS (mainapp->global_settings);

  pitivi_settingswindow_create_table_InOut 
    (self, self->private->settings->element, 
     pitivi_settingswindow_create_frame (self->private->Tab, "In/Out", "In/Out List"));

  self->private->TabCodec = pitivi_settingswindow_create_table 
    (pitivi_settingswindow_create_frame (self->private->Tab, "Codecs", "Codecs List"),
     self->private->settings->codec);

  self->private->TabContainer = pitivi_settingswindow_create_table 
    (pitivi_settingswindow_create_frame (self->private->Tab, "Containers", "Containers List"),
     self->private->settings->container);

  self->private->TabParser = pitivi_settingswindow_create_table 
    (pitivi_settingswindow_create_frame (self->private->Tab, "Parsers", "Parsers List"), 
     self->private->settings->parser);

  return ;
}

void
pitivi_settingswindow_create_gui (PitiviSettingsWindow *self)
{
  // main container box
  self->private->MainBox = gtk_vbox_new (FALSE, 2);
  gtk_container_add (GTK_CONTAINER (self), self->private->MainBox);
  gtk_widget_show (self->private->MainBox);

  // notebook
  self->private->Tab = gtk_notebook_new ();
  gtk_box_pack_start (GTK_BOX (self->private->MainBox), 
		     self->private->Tab,
		     TRUE, TRUE, 0);
  gtk_widget_show (self->private->Tab);

  // frame of notebook
  pitivi_settingswindow_create_all_frames (self);

  // buttons bar
  self->private->ButtonBox = gtk_hbutton_box_new ();
  gtk_box_pack_start (GTK_BOX (self->private->MainBox), 
		     self->private->ButtonBox,
		     FALSE, FALSE, 0);
  gtk_button_box_set_layout (GTK_BUTTON_BOX (self->private->ButtonBox), GTK_BUTTONBOX_END);
  gtk_widget_show (self->private->ButtonBox);

  // button CANCEL
  self->private->ButtonCancel = gtk_button_new_from_stock (GTK_STOCK_CANCEL);
  gtk_container_add (GTK_CONTAINER (self->private->ButtonBox), 
		     self->private->ButtonCancel);
  g_signal_connect (G_OBJECT (self->private->ButtonCancel), "clicked",
		    G_CALLBACK (pitivi_settingswindow_cb_cancel), self);
  gtk_widget_show (self->private->ButtonCancel);

  // button OK
  self->private->ButtonOk = gtk_button_new_from_stock (GTK_STOCK_OK);
  gtk_container_add (GTK_CONTAINER (self->private->ButtonBox), 
		     self->private->ButtonOk);
  g_signal_connect (G_OBJECT (self->private->ButtonOk), "clicked",
		    G_CALLBACK (pitivi_settingswindow_cb_ok), self);
  gtk_widget_show (self->private->ButtonOk);

  gtk_widget_set_size_request (GTK_WIDGET (self), 600, 400);
  g_signal_connect (G_OBJECT (self), "destroy",
		    G_CALLBACK (pitivi_settingswindow_cb_destroy), self);
  gtk_widget_show (GTK_WIDGET (self));

  return ;
}

/*
 * ##################################################################################
 * ################### Insert "added-value" functions here ##########################
 * ##################################################################################
 */

PitiviSettingsWindow *
pitivi_settingswindow_new(PitiviMainApp *mainapp)
{
  PitiviSettingsWindow	*settingswindow;

  settingswindow = (PitiviSettingsWindow *) g_object_new(PITIVI_SETTINGSWINDOW_TYPE, 
							 "mainapp", mainapp,
							 NULL);
  g_assert(settingswindow != NULL);
  return settingswindow;
}

static GObject *
pitivi_settingswindow_constructor (GType type,
			     guint n_construct_properties,
			     GObjectConstructParam * construct_properties)
{
  GObject *obj;
  /* Invoke parent constructor. */
  obj = G_OBJECT_CLASS (parent_class)->constructor (type, n_construct_properties,
						    construct_properties);

  /* do stuff. */
  PitiviSettingsWindow	*self = (PitiviSettingsWindow *) obj;

  pitivi_settingswindow_create_gui (self);

  return obj;
}

static void
pitivi_settingswindow_instance_init (GTypeInstance * instance, gpointer g_class)
{
  PitiviSettingsWindow *self = (PitiviSettingsWindow *) instance;

  self->private = g_new0(PitiviSettingsWindowPrivate, 1);
  
  /* initialize all public and private members to reasonable default values. */ 
  
  self->private->dispose_has_run = FALSE;

  //self->private-> = NULL;
  //self->private-> = NULL;

  self->private->MainBox = NULL;

  self->private->Tab = NULL;
  self->private->TabIn = NULL;
  self->private->TabOut = NULL;
  self->private->TabCodec = NULL;
  self->private->TabParser = NULL;
  self->private->TabContainer = NULL;

  self->private->ButtonBox = NULL;
  self->private->ButtonOk = NULL;
  self->private->ButtonCancel = NULL;

  self->private->settings = NULL;

  self->private->Ttips = gtk_tooltips_new ();
  gtk_tooltips_enable(self->private->Ttips);
}

static void
pitivi_settingswindow_dispose (GObject *object)
{
  PitiviSettingsWindow	*self = PITIVI_SETTINGSWINDOW(object);

  /* If dispose did already run, return. */
  if (self->private->dispose_has_run)
    return;
  
  /* Make sure dispose does not run twice. */
  self->private->dispose_has_run = TRUE;	
  G_OBJECT_CLASS (parent_class)->dispose (object);
}

static void
pitivi_settingswindow_finalize (GObject *object)
{
  PitiviSettingsWindow	*self = PITIVI_SETTINGSWINDOW(object);

  g_free (self->private);
  G_OBJECT_CLASS (parent_class)->finalize (object);
}

static void
pitivi_settingswindow_class_init (gpointer g_class, gpointer g_class_data)
{
  GObjectClass *gobject_class = G_OBJECT_CLASS (g_class);
  parent_class = g_type_class_peek_parent (g_class);

  gobject_class->constructor = pitivi_settingswindow_constructor;
  gobject_class->dispose = pitivi_settingswindow_dispose;
  gobject_class->finalize = pitivi_settingswindow_finalize;
}

GType
pitivi_settingswindow_get_type (void)
{
  static GType type = 0;
 
  if (type == 0)
    {
      static const GTypeInfo info = {
	sizeof (PitiviSettingsWindowClass),
	NULL,			/* base_init */
	NULL,			/* base_finalize */
	pitivi_settingswindow_class_init,	/* class_init */
	NULL,			/* class_finalize */
	NULL,			/* class_data */
	sizeof (PitiviSettingsWindow),
	0,			/* n_preallocs */
	pitivi_settingswindow_instance_init	/* instance_init */
      };
      type = g_type_register_static (PITIVI_WINDOWS_TYPE,
				     "PitiviSettingsWindowType", &info, 0);
    }

  return type;
}
