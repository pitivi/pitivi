/* 
 * PiTiVi
 * Copyright (C) <2004> Delettrez Marc <delett_m@epita.fr>
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

TODO TODO TODO TODO TODO TODO
TODO TODO TODO TODO TODO TODO
TODO TODO TODO TODO TODO TODO
TODO TODO TODO TODO TODO TODO
TODO TODO TODO TODO TODO TODO
TODO TODO TODO TODO TODO TODO
TODO TODO TODO TODO TODO TODO
TODO TODO TODO TODO TODO TODO
TODO TODO TODO TODO TODO TODO
TODO TODO TODO TODO TODO TODO

:::::::::::::::::::::::::::::

1) if(param != WRITABLE) gtk_widget_set_sensitive (FALSE)

2) SAVE return LIST with method

3) refresh code


*/

#include "pitivi.h"
#include "pitivi-debug.h"
#include "pitivi-gstelementsettings.h"
#include "pitivi-settingswindow.h"

static     GObjectClass *parent_class;

#define BORDER		5
#define	X_SPACE_TAB	5
#define Y_SPACE_TAB	5

struct _PitiviGstElementSettingsPrivate
{
  /* instance private members */
  gboolean		dispose_has_run;

  GtkWidget		*frame_info;
  GtkWidget		*frame_prop;

  GstElement		*element;

  gint			num_prop;
  GParamSpec		**prop;

  gint			option;

  //GtkWidget *hprop;
  
};

enum {
  PROP_0,
  PROP_IO,
  PROP_OPT
};

/*
 * forward definitions
 */






/*
 * Insert "added-value" functions here
 */

static gchar *
pitivi_gstelementsettings_string_bold (gchar *text)
{
  return (g_locale_to_utf8 (g_strdup_printf ("<b>%s</b>", text),
			    -1, NULL, NULL, NULL));
}

static void
pitivi_gstelementsettings_add_new_label (gpointer data, 
					 gchar *text)
{
  GtkWidget *Label;
  
  Label = gtk_label_new (NULL);
  gtk_label_set_markup (GTK_LABEL (Label), text);
  gtk_box_pack_start (GTK_BOX (data), Label, FALSE, FALSE, BORDER);
  return ;
}

/* static void */
/* pitivi_gstelementsettings_add_new_separator (gpointer data) */
/* { */
/*   GtkWidget *Sep; */
  
/*   Sep = gtk_hseparator_new (); */
/*   gtk_box_pack_start (GTK_BOX (data), Sep, FALSE, FALSE, BORDER); */
/*   return ; */
/* } */

static GtkWidget *
pitivi_gstelementsettings_add_new_frame_expand (gpointer data,
					 gchar *text)
{
  GtkWidget *Frame;
  GtkWidget *VBox;

  Frame = gtk_frame_new(text);
  gtk_box_pack_start (GTK_BOX (data), Frame, TRUE, TRUE, BORDER);
  VBox = gtk_vbox_new (FALSE, 0);
  gtk_container_add (GTK_CONTAINER (Frame), VBox);

  return (VBox);
}

static GtkWidget *
pitivi_gstelementsettings_add_new_frame (gpointer data,
					 gchar *text)
{
  GtkWidget *Frame;
  GtkWidget *VBox;

  Frame = gtk_frame_new(text);
  gtk_box_pack_start (GTK_BOX (data), Frame, FALSE, FALSE, BORDER);
  VBox = gtk_vbox_new (FALSE, 0);
  gtk_container_add (GTK_CONTAINER (Frame), VBox);
  return (VBox);
}

static void
pitivi_gstelementsettings_add_new_frame_info (PitiviGstElementSettings *self) 
{
    self->private->frame_info = pitivi_gstelementsettings_add_new_frame (self, "Info:");
    pitivi_gstelementsettings_add_new_label (self->private->frame_info, 
					     pitivi_gstelementsettings_string_bold ("Name:"));
    pitivi_gstelementsettings_add_new_label (self->private->frame_info, 
					     (gchar *) gst_element_factory_get_longname (self->io->factory));
    pitivi_gstelementsettings_add_new_label (self->private->frame_info, 
					     pitivi_gstelementsettings_string_bold ("Class:"));
    pitivi_gstelementsettings_add_new_label (self->private->frame_info, 
					     (gchar *) gst_element_factory_get_klass (self->io->factory));
    pitivi_gstelementsettings_add_new_label (self->private->frame_info, 
					     pitivi_gstelementsettings_string_bold ("Description:"));
    pitivi_gstelementsettings_add_new_label (self->private->frame_info, 
					     (gchar *) gst_element_factory_get_description (self->io->factory));
    return ;
}

static void
pitivi_gstelementsettings_table_widget_add (GtkWidget *Table, GtkWidget *widget, gint row, gint col)
{
  gtk_table_attach(GTK_TABLE(Table), widget,
		   col, col+1, row, row+1, 
		   GTK_FILL, GTK_FILL,
		   X_SPACE_TAB, Y_SPACE_TAB);
  return ;
}

static void
pitivi_gstelementsettings_table_new_label_add (PitiviGstElementSettings *self,
						gchar *text, gint row, gint col, gchar *tips)
{
  GtkWidget	*Label;
  GtkWidget	*EventBox;
  GtkTooltips	*Ttips;

  Ttips = gtk_tooltips_new ();
  EventBox = gtk_event_box_new ();
  gtk_tooltips_set_tip (Ttips, EventBox, tips, NULL);
  
  Label = gtk_label_new (NULL);
  gtk_label_set_markup (GTK_LABEL (Label), text);
  gtk_misc_set_alignment (GTK_MISC (Label), 0.0, 0.5);
  
  gtk_container_add (GTK_CONTAINER (EventBox), Label);
  pitivi_settingswindow_table_widget_add (self->Table, EventBox, row, col);  

  return ;
}

///////////////////////// FONCTIONS AFF PARAMS ////////////////////////////////////////

///////////////////////////////////////////////////////////////////////////////////////

static GtkWidget *
pitivi_gstelementsettings_conf_value_string (gchar *name, GValue value, GParamSpec *param)
{
  const gchar		*string_val;
  GtkWidget		*text_entry;

  text_entry = gtk_entry_new ();

  string_val = g_value_get_string (&value);  
  if (string_val == NULL) {
    gtk_entry_set_text (GTK_ENTRY (text_entry), ""); 
  } else {
    gtk_entry_set_text (GTK_ENTRY (text_entry), string_val);
  }

  g_object_set_data (G_OBJECT(text_entry), "name", name);

  if (param->flags & G_PARAM_WRITABLE) {
    gtk_widget_set_sensitive (text_entry, TRUE);
  } else {
    gtk_widget_set_sensitive (text_entry, FALSE);
  }

  return (text_entry);
}

static GtkWidget *
pitivi_gstelementsettings_value_conf_boolean (gchar *name, GValue value, GParamSpec *param)
{
  GSList		*radio_list;
  GtkWidget		*radio_true;
  GtkWidget		*radio_false;
  GtkWidget		*button_hbox;
		    
  button_hbox = gtk_hbox_new(FALSE, 0);
		    
  radio_true = gtk_radio_button_new_with_label (NULL, "True");
  radio_list = gtk_radio_button_get_group (GTK_RADIO_BUTTON (radio_true));
  radio_false = gtk_radio_button_new_with_label (radio_list, "False");		    

  if (g_value_get_boolean (&value))
    gtk_toggle_button_set_active(GTK_TOGGLE_BUTTON (radio_true), TRUE);
  else
    gtk_toggle_button_set_active(GTK_TOGGLE_BUTTON (radio_false), TRUE);

  gtk_box_pack_start(GTK_BOX (button_hbox), radio_true, FALSE, FALSE, BORDER);
  gtk_box_pack_start(GTK_BOX (button_hbox), radio_false, FALSE, FALSE, BORDER);

  g_object_set_data (G_OBJECT(button_hbox), "name", name);

  if (param->flags & G_PARAM_WRITABLE) {
    gtk_widget_set_sensitive (radio_true, TRUE);
    gtk_widget_set_sensitive (radio_false, TRUE);
  } else {
    gtk_widget_set_sensitive (radio_true, FALSE);
    gtk_widget_set_sensitive (radio_false, FALSE);
  }

  return (button_hbox);
}

static GtkWidget *
pitivi_gstelementsettings_value_conf_uint (gchar *name, GValue value, GParamSpec *param)
{
  GParamSpecUInt	*puint;
  GtkWidget		*spin_button;

  puint = G_PARAM_SPEC_UINT (param);
  spin_button = gtk_spin_button_new_with_range(puint->minimum, puint->maximum, 1);

  /* valeur par defaut */
  gtk_spin_button_set_value(GTK_SPIN_BUTTON(spin_button), g_value_get_uint (&value));

  g_object_set_data (G_OBJECT(spin_button), "name", name);
  g_object_set_data (G_OBJECT(spin_button), "type", "UINT");

  if (param->flags & G_PARAM_WRITABLE) {
    gtk_widget_set_sensitive (spin_button, TRUE);
  } else {
    gtk_widget_set_sensitive (spin_button, FALSE);
  }

  return (spin_button);
}

static GtkWidget *
pitivi_gstelementsettings_value_conf_int (gchar *name, GValue value, GParamSpec	*param)
{
  GParamSpecInt		*pint;  
  GtkWidget		*spin_button;

  pint = G_PARAM_SPEC_INT (param);
  spin_button = gtk_spin_button_new_with_range(pint->minimum, pint->maximum, 1);

  /* valeur par defaut */
  gtk_spin_button_set_value(GTK_SPIN_BUTTON(spin_button), g_value_get_int (&value));

  g_object_set_data (G_OBJECT(spin_button), "name", name);
  g_object_set_data (G_OBJECT(spin_button), "type", "INT");

  if (param->flags & G_PARAM_WRITABLE) {
    gtk_widget_set_sensitive (spin_button, TRUE);
  } else {
    gtk_widget_set_sensitive (spin_button, FALSE);
  }

  return (spin_button);
}

static GtkWidget *
pitivi_gstelementsettings_value_conf_uint64 (gchar *name, GValue value, GParamSpec *param)
{
  GParamSpecUInt64	*puint64;
  GtkWidget		*spin_button;

  puint64 = G_PARAM_SPEC_UINT64 (param);
  spin_button = gtk_spin_button_new_with_range(puint64->minimum, puint64->maximum, 1);

  /* valeur par defaut */
  gtk_spin_button_set_value(GTK_SPIN_BUTTON(spin_button), g_value_get_uint64 (&value));

  g_object_set_data (G_OBJECT(spin_button), "name", name);
  g_object_set_data (G_OBJECT(spin_button), "type", "UINT64");

  if (param->flags & G_PARAM_WRITABLE) {
    gtk_widget_set_sensitive (spin_button, TRUE);
  } else {
    gtk_widget_set_sensitive (spin_button, FALSE);
  }

  return (spin_button);
}

static GtkWidget *
pitivi_gstelementsettings_value_conf_int64 (gchar *name, GValue value, GParamSpec *param)
{
  GParamSpecInt64	*pint64;
  GtkWidget		*spin_button;

  pint64 = G_PARAM_SPEC_INT64 (param);
  spin_button = gtk_spin_button_new_with_range(pint64->minimum, pint64->maximum, 1);

  /* valeur par defaut */
  gtk_spin_button_set_value(GTK_SPIN_BUTTON(spin_button), g_value_get_int64 (&value));

  g_object_set_data (G_OBJECT(spin_button), "name", name);
  g_object_set_data (G_OBJECT(spin_button), "type", "INT64");

  if (param->flags & G_PARAM_WRITABLE) {
    gtk_widget_set_sensitive (spin_button, TRUE);
  } else {
    gtk_widget_set_sensitive (spin_button, FALSE);
  }

  return (spin_button);
}

static GtkWidget *
pitivi_gstelementsettings_value_conf_ulong (gchar *name, GValue value, GParamSpec *param)
{
  GParamSpecULong	*pulong;
  GtkWidget		*spin_button;

  pulong = G_PARAM_SPEC_ULONG (param);
  spin_button = gtk_spin_button_new_with_range(pulong->minimum, pulong->maximum, 1);

  /* valeur par defaut */
  gtk_spin_button_set_value(GTK_SPIN_BUTTON(spin_button), g_value_get_ulong (&value));

  g_object_set_data (G_OBJECT(spin_button), "name", name);
  g_object_set_data (G_OBJECT(spin_button), "type", "ULONG");

  if (param->flags & G_PARAM_WRITABLE) {
    gtk_widget_set_sensitive (spin_button, TRUE);
  } else {
    gtk_widget_set_sensitive (spin_button, FALSE);
  }

  return (spin_button);
}

static GtkWidget *
pitivi_gstelementsettings_value_conf_long (gchar *name, GValue value, GParamSpec *param)
{
  GParamSpecLong	*plong;
  GtkWidget		*spin_button;

  plong = G_PARAM_SPEC_LONG (param);
  spin_button = gtk_spin_button_new_with_range(plong->minimum, plong->maximum, 1);

  /* valeur par defaut */
  gtk_spin_button_set_value(GTK_SPIN_BUTTON(spin_button), g_value_get_long (&value));

  g_object_set_data (G_OBJECT(spin_button), "name", name);
  g_object_set_data (G_OBJECT(spin_button), "type", "LONG");

  if (param->flags & G_PARAM_WRITABLE) {
    gtk_widget_set_sensitive (spin_button, TRUE);
  } else {
    gtk_widget_set_sensitive (spin_button, FALSE);
  }

  return (spin_button);
}

static GtkWidget *
pitivi_gstelementsettings_value_conf_float (gchar *name, GValue value, GParamSpec *param)
{
  GParamSpecFloat	*pfloat;
  GtkWidget		*spin_button;

  pfloat = G_PARAM_SPEC_FLOAT (param);
  spin_button = gtk_spin_button_new_with_range(pfloat->minimum, pfloat->maximum, 1);

  /* valeur par defaut */
  gtk_spin_button_set_value(GTK_SPIN_BUTTON(spin_button), g_value_get_float (&value));

  g_object_set_data (G_OBJECT(spin_button), "name", name);
  g_object_set_data (G_OBJECT(spin_button), "type", "FLOAT");

  if (param->flags & G_PARAM_WRITABLE) {
    gtk_widget_set_sensitive (spin_button, TRUE);
  } else {
    gtk_widget_set_sensitive (spin_button, FALSE);
  }

  return (spin_button);
}

static GtkWidget *
pitivi_gstelementsettings_value_conf_double (gchar *name, GValue value, GParamSpec *param)
{
  GParamSpecDouble	*pdouble;
  GtkWidget		*spin_button;

  pdouble = G_PARAM_SPEC_DOUBLE (param);
  spin_button = gtk_spin_button_new_with_range(pdouble->minimum, pdouble->maximum, 1);

  /* valeur par defaut */
  gtk_spin_button_set_value(GTK_SPIN_BUTTON(spin_button), g_value_get_double (&value));

  g_object_set_data (G_OBJECT(spin_button), "name", name);
  g_object_set_data (G_OBJECT(spin_button), "type", "DOUBLE");

  if (param->flags & G_PARAM_WRITABLE) {
    gtk_widget_set_sensitive (spin_button, TRUE);
  } else {
    gtk_widget_set_sensitive (spin_button, FALSE);
  }

  return (spin_button);
}

static GtkWidget *
pitivi_gstelementsettings_aff_enum (PitiviGstElementSettings *self,
				    gchar *name, GValue value, GParamSpec *param)
{
  gint			i;
  gint			*enum_values;
  gchar			*label;
  GtkWidget		*widget;
  
  GEnumClass *class = G_ENUM_CLASS (g_type_class_ref (param->value_type));
  enum_values = g_new0 (gint, class->n_values);
    
  if (self->private->option) {

    GEnumValue *evalue = &class->values[g_value_get_enum(&value)];
    label = g_strdup_printf ("%s", evalue->value_nick);
    widget = gtk_label_new (label);

  } else {

    widget = gtk_combo_box_new_text();
    
    for (i=0; i < class->n_values; i++) {
      GEnumValue *evalue = &class->values[i];
      
      enum_values[i] = evalue->value;
      label = g_strdup_printf ("%s (%d)", evalue->value_nick, evalue->value);
      gtk_combo_box_insert_text (GTK_COMBO_BOX (widget), i, label);
    }
    
    ////////////////////////////////// transformer le numero en ligne !!!!!!!!!!!!!!!!!!!!!!!!
    gtk_combo_box_set_active (GTK_COMBO_BOX (widget), g_value_get_enum(&value));
    
    
    if (param->flags & G_PARAM_WRITABLE) {
      gtk_widget_set_sensitive (widget, TRUE);
    } else {
      gtk_widget_set_sensitive (widget, FALSE);
    }



    g_object_set_data (G_OBJECT(widget), "tab", enum_values);
  }

  g_object_set_data (G_OBJECT(widget), "name", name);
  
  //g_object_set_data (G_OBJECT(widget), "type", &value);
  
  return (widget);
}

static GtkWidget *
pitivi_gstelementsettings_aff_flags (gchar *name, GValue value, GParamSpec *param)
{
  GtkWidget		*Tab;
  GFlagsValue		*values;
  guint			j;
  gint			flags_value;
  gint			nb_value;
  
  values = G_FLAGS_CLASS (g_type_class_ref (param->value_type))->values;
  nb_value = G_FLAGS_CLASS (g_type_class_ref (param->value_type))->n_values;
  flags_value = g_value_get_flags (&value);
  
  Tab = gtk_table_new (nb_value, 2, FALSE);
  
  for (j = 0; j < nb_value; j++) {
    GtkWidget*	check;
    GtkWidget*	label;
    gint		tmp;
    
    check = gtk_check_button_new ();
    
    tmp = values[j].value;
    g_object_set_data (G_OBJECT (check), "value", GINT_TO_POINTER (tmp));
    pitivi_gstelementsettings_table_widget_add (Tab, check, j, 1);
    
    label = gtk_label_new (values[j].value_nick);
    pitivi_gstelementsettings_table_widget_add (Tab, label, j, 2);
    
    //if (values[j].value & flags_value) {
    if (values[j].value && flags_value) {
      gtk_toggle_button_set_active (GTK_TOGGLE_BUTTON (check), TRUE);
    } else {
      gtk_toggle_button_set_active (GTK_TOGGLE_BUTTON (check), FALSE);
    }
    
    if (param->flags & G_PARAM_WRITABLE) {
      gtk_widget_set_sensitive (check, TRUE);
    } else {
      gtk_widget_set_sensitive (check, FALSE);
    }

  }

  g_object_set_data (G_OBJECT(Tab), "name", name);
  //g_object_set_data (G_OBJECT(Tab), "type", &value);

  return (Tab);
}

static GtkWidget *
pitivi_gstelementsettings_value_conf_default (PitiviGstElementSettings *self,
					      gchar *name, GValue value, GParamSpec *param)
{
  GtkWidget *tmp;
  
  if (G_IS_PARAM_SPEC_ENUM (param)) {    
    //PITIVI_DEBUG ("ENUM_TYPE:%d\n", G_TYPE_FUNDAMENTAL (G_VALUE_TYPE (&value)));
    tmp = pitivi_gstelementsettings_aff_enum (self, name, value, param);    
  } else if (G_IS_PARAM_SPEC_FLAGS (param)) {
    //PITIVI_DEBUG ("FLAGS_TYPE:%d\n", G_TYPE_FUNDAMENTAL (G_VALUE_TYPE (&value)));
    tmp = pitivi_gstelementsettings_aff_flags (name, value, param);    
  } else {
    tmp = gtk_label_new("Default Case for Value");
  }
  return (tmp);  
}


///////////////////////////////////////////////////////////////////////////////////////

///////////////////////////////////////////////////////////////////////////////////////

static void
pitivi_gstelementsettings_table_new_param_add (PitiviGstElementSettings *self,
					       GParamSpec *prop, gint row, gint col)
{
  GtkWidget *tmp;
  GValue value = { 0, };

  g_value_init (&value, prop->value_type);

  switch (G_VALUE_TYPE (&value)) {
  case G_TYPE_STRING: {
    tmp = pitivi_gstelementsettings_conf_value_string 
      (g_strdup(g_param_spec_get_name (prop)), self->io->params[row].value, prop);
    break;
  } case G_TYPE_BOOLEAN: {
    tmp = pitivi_gstelementsettings_value_conf_boolean 
      (g_strdup(g_param_spec_get_name (prop)), self->io->params[row].value, prop);
    break;
  } case G_TYPE_UINT: {
    tmp = pitivi_gstelementsettings_value_conf_uint 
      (g_strdup(g_param_spec_get_name (prop)), self->io->params[row].value, prop);
    break;
  } case G_TYPE_INT: {
    tmp = pitivi_gstelementsettings_value_conf_int 
      (g_strdup(g_param_spec_get_name (prop)), self->io->params[row].value, prop);
    break;
  } case G_TYPE_UINT64: {
    tmp = pitivi_gstelementsettings_value_conf_uint64 
      (g_strdup(g_param_spec_get_name (prop)), self->io->params[row].value, prop);
    break;
  } case G_TYPE_INT64: {
    tmp = pitivi_gstelementsettings_value_conf_int64 
      (g_strdup(g_param_spec_get_name (prop)), self->io->params[row].value, prop);
    break;
  } case G_TYPE_ULONG: {
    tmp = pitivi_gstelementsettings_value_conf_ulong 
      (g_strdup(g_param_spec_get_name (prop)), self->io->params[row].value, prop);
    break;
  } case G_TYPE_LONG: {
    tmp = pitivi_gstelementsettings_value_conf_long 
      (g_strdup(g_param_spec_get_name (prop)), self->io->params[row].value, prop);
    break;
  } case G_TYPE_FLOAT: {
    tmp = pitivi_gstelementsettings_value_conf_float 
      (g_strdup(g_param_spec_get_name (prop)), self->io->params[row].value, prop);
    break;
  } case G_TYPE_DOUBLE: {
    tmp = pitivi_gstelementsettings_value_conf_double 
      (g_strdup(g_param_spec_get_name (prop)), self->io->params[row].value, prop);
    break;
  } default: {
    tmp = pitivi_gstelementsettings_value_conf_default 
      (self, g_strdup (g_param_spec_get_name (prop)), self->io->params[row].value, prop);
    break;
  }
  }

  pitivi_gstelementsettings_table_widget_add (self->Table, tmp, row, col);

  return ;
}

static GParamSpec *
pitivi_gstelementsettings_get_info_prop (PitiviGstElementSettings *self, gchar *name)
{
  gint cpt;

  for (cpt = 0; cpt < self->private->num_prop; cpt++) {
    if (!strcmp ((self->private->prop)[cpt]->name, name)) {
      return ((self->private->prop)[cpt]);
    }
  }

  return (NULL);
}

static void
pitivi_gstelementsettings_add_new_frame_prop (PitiviGstElementSettings *self)
{
  gint cpt;
  GtkWidget	*ScrollBar;

  self->private->frame_prop = pitivi_gstelementsettings_add_new_frame_expand (self, "Properties:");

  if (self->io->n_param < 1) {
    GtkWidget *Label;

    Label = gtk_label_new ("No Properties ...");
    gtk_box_pack_start (GTK_BOX (self->private->frame_prop),
			Label, FALSE, FALSE, BORDER);
  } else {
    self->Table = gtk_table_new ((self->io->n_param), 2, FALSE);
    gtk_container_set_border_width (GTK_CONTAINER (self->Table), BORDER);
    ScrollBar = gtk_scrolled_window_new (NULL, NULL);
    gtk_scrolled_window_set_policy (GTK_SCROLLED_WINDOW (ScrollBar),
				    GTK_POLICY_NEVER,
				    GTK_POLICY_AUTOMATIC);
    gtk_widget_set_size_request (ScrollBar, -1, 100);

    gtk_container_add (GTK_CONTAINER (self->private->frame_prop), ScrollBar);
    gtk_scrolled_window_add_with_viewport (GTK_SCROLLED_WINDOW (ScrollBar), self->Table);
   
    for (cpt = 0; cpt < self->io->n_param; cpt++) {
      GParamSpec *pspec;

      pspec = pitivi_gstelementsettings_get_info_prop (self, (gchar *) (self->io->params[cpt]).name);

      pitivi_gstelementsettings_table_new_label_add (self, pitivi_gstelementsettings_string_bold 
						     ((gchar *) g_param_spec_get_name (pspec)), 
						     cpt, 0, (gchar *) g_param_spec_get_blurb (pspec));

      pitivi_gstelementsettings_table_new_param_add (self, pspec, cpt, 1);

    }
  }
  return ;
}

static void
pitivi_gstelementsettings_create_gui (PitiviGstElementSettings *self)
{
  self->private->element = gst_element_factory_create(self->io->factory, "test");

  self->private->prop = g_object_class_list_properties(G_OBJECT_GET_CLASS (self->private->element), 
						       &(self->private->num_prop));

  pitivi_gstelementsettings_add_new_frame_info (self);
  pitivi_gstelementsettings_add_new_frame_prop (self);

  gtk_widget_show_all (GTK_WIDGET (self));  

  return ;
}


// ############################ SAVE ##################################### 

static gint
pitivi_gstelementsettings_get_prop_num (PitiviGstElementSettings *self, gchar *prop_name)
{
  gint cpt;

  for (cpt = 1; cpt < self->private->num_prop ; cpt++) {
    if (!g_ascii_strcasecmp (self->private->prop[cpt]->name, prop_name)) {
      return (cpt);
    }
  }
  return (-1);
}

static void
pitivi_gstelementsettings_modify_prop (PitiviGstElementSettings *self, gchar *name, GValue value)
{
  gint	cpt;

  for (cpt = 0; cpt < self->io->n_param; cpt++) {
    if (!strcmp (name, (self->io->params)[cpt].name)) {
      g_value_reset (&((self->io->params)[cpt].value));
      (self->io->params)[cpt].value = value;
    }
  }
  return ;
}

static void
pitivi_gstelementsettings_get_settings_combobox (GtkWidget *widget, PitiviGstElementSettings *self)
{
  gchar  *prop_name;
  gint	 *tmp_list;
  gint	 num;
  gint	 row_sel;
  GValue value = { 0 };

  row_sel = gtk_combo_box_get_active (GTK_COMBO_BOX (widget));
  tmp_list = g_object_get_data (G_OBJECT (widget), "tab");
  prop_name = g_object_get_data (G_OBJECT (widget), "name");

  num = pitivi_gstelementsettings_get_prop_num (self, prop_name);
  g_value_init (&value, self->private->prop[num]->value_type);
  g_object_get_property (G_OBJECT (self->private->element), prop_name, &value);
  g_value_set_enum (&value, tmp_list[row_sel]);

  //PITIVI_DEBUG ("COMBO_BOX_SEL[%d]:%d\n", row_sel, tmp_list[row_sel]);
  //PITIVI_DEBUG ("PROP_NAME=[%s]\n", prop_name);
  //PITIVI_DEBUG ("NUM:%d\n", num);

  pitivi_gstelementsettings_modify_prop (self, prop_name, value);
  return ;
}

static void
pitivi_gstelementsettings_get_settings_entry (GtkWidget *widget, PitiviGstElementSettings *self)
{
  gchar		*type;
  GValue	value = { 0 };

  type = (gchar *) g_object_get_data (G_OBJECT (widget), "type");

  if (type != NULL) {
    GValue tmp = { 0};
    
    g_value_init (&tmp, G_TYPE_DOUBLE);
    g_value_set_double (&tmp, gtk_spin_button_get_value (GTK_SPIN_BUTTON (widget)));

    if (!g_ascii_strcasecmp(type, "INT")) {
      g_value_init(&value, G_TYPE_INT);
      g_value_set_int (&value, gtk_spin_button_get_value_as_int (GTK_SPIN_BUTTON (widget)));

    } else if (!g_ascii_strcasecmp(type, "UINT")) {
      g_value_init(&value, G_TYPE_UINT);
      if (!g_value_transform (&tmp, &value))
	PITIVI_DEBUG ("COULD NOT TRANSFORM TYPE\n");

    } else if (!g_ascii_strcasecmp(type, "UINT64")) {
      g_value_init(&value, G_TYPE_UINT64);
      if (!g_value_transform (&tmp, &value))
	PITIVI_DEBUG ("COULD NOT TRANSFORM TYPE\n");

    } else if (!g_ascii_strcasecmp(type, "INT64")) {
      g_value_init(&value, G_TYPE_INT64);
      if (!g_value_transform (&tmp, &value))
	PITIVI_DEBUG ("COULD NOT TRANSFORM TYPE\n");

    } else if (!g_ascii_strcasecmp(type, "ULONG")) {
      g_value_init(&value, G_TYPE_ULONG);
      if (!g_value_transform (&tmp, &value))
	PITIVI_DEBUG ("COULD NOT TRANSFORM TYPE\n");

    } else if (!g_ascii_strcasecmp(type, "LONG")) {
      g_value_init(&value, G_TYPE_LONG);
      if (!g_value_transform (&tmp, &value))
	PITIVI_DEBUG ("COULD NOT TRANSFORM TYPE\n");

    } else if (!g_ascii_strcasecmp(type, "FLOAT")) {
      g_value_init(&value, G_TYPE_FLOAT);
      if (!g_value_transform (&tmp, &value))
	PITIVI_DEBUG ("COULD NOT TRANSFORM TYPE\n");

    } else if (!g_ascii_strcasecmp(type, "DOUBLE")) {
      gst_value_init_and_copy (&value, &tmp);

    }

    //PITIVI_DEBUG ("spin type : %s\t %g \n", i, gtk_spin_button_get_value (GTK_SPIN_BUTTON (widget)));

  } else {
    g_value_init(&value, G_TYPE_STRING);
    g_value_set_string (&value, gtk_entry_get_text (GTK_ENTRY (widget)));  

    //PITIVI_DEBUG ("ENTRY:%s\n", gtk_entry_get_text (GTK_ENTRY (widget)));
    //PITIVI_DEBUG ("PROP_NAME=[%s]\n", g_object_get_data (G_OBJECT (widget), "name"));

  }
  
  pitivi_gstelementsettings_modify_prop (self, g_object_get_data (G_OBJECT (widget), "name"), value);

  return ;
}

static void
pitivi_gstelementsettings_get_settings_box (GtkWidget *widget, PitiviGstElementSettings *self)
{
  GList *plist;
  gint i;
  GValue value = { 0 };

  g_value_init(&value, G_TYPE_BOOLEAN);
  
  //PITIVI_DEBUG ("BUTTON:[TRUE|FALSE]\n");
  //PITIVI_DEBUG ("PROP_NAME=[%s]\n", g_object_get_data (G_OBJECT (widget), "name"));

  plist = GTK_BOX (widget)->children;
  for (i = 0; plist; plist = g_list_next (plist), i++) { 
    GtkBoxChild *child = (GtkBoxChild *) plist->data; 
    
    if (GTK_IS_BUTTON (child->widget)) {	    
      if (gtk_toggle_button_get_active (GTK_TOGGLE_BUTTON (child->widget))) {
	if (i == 0) {
	  //PITIVI_DEBUG ("Button:TRUE\n");
	  g_value_set_boolean (&value, TRUE);
	} else {
	  //PITIVI_DEBUG ("Button:FALSE\n");
	  g_value_set_boolean (&value, FALSE);
	}
      }
    }
  }

  pitivi_gstelementsettings_modify_prop (self, g_object_get_data (G_OBJECT (widget), "name"), value);

  return ;
}

static void
pitivi_gstelementsettings_get_settings_table (GtkWidget *widget, PitiviGstElementSettings *self)
{
  GValue value = { 0 };
  gchar *prop_name;
  GList *table_box;
  gint nb;
  gint num;
  
  prop_name = g_object_get_data (G_OBJECT (widget), "name");

  table_box = GTK_TABLE (widget)->children;
  for (nb = 0; table_box; table_box = g_list_next (table_box)) {
    GtkTableChild *tmp2 = (GtkTableChild *) table_box->data;
    
    if (GTK_IS_BUTTON (tmp2->widget)) {
      if (!GTK_TOGGLE_BUTTON (tmp2->widget)) {
	PITIVI_DEBUG ("NOT TOGGLE BOUTTON \n");
      } else {
	
	if (gtk_toggle_button_get_active (GTK_TOGGLE_BUTTON (tmp2->widget))) {
	  nb += GPOINTER_TO_INT (g_object_get_data (G_OBJECT (tmp2->widget), "value"));
	  
	  //PITIVI_DEBUG ("FLAG:%d\n", (gint) g_object_get_data (G_OBJECT (tmp2->widget), "value"));
	  /* 	} else { */
	  /* 	  PITIVI_DEBUG ("FLAG:NULL\n"); */
	  
	}
	
      } 
    }  
  }
  
  /////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

  num = pitivi_gstelementsettings_get_prop_num (self, prop_name);
  g_value_init (&value, self->private->prop[num]->value_type);
  g_object_get_property (G_OBJECT (self->private->element), prop_name, &value); 
  g_value_set_enum (&value, nb);
  
  PITIVI_DEBUG ("<<<<<<<<<<<TABLE>>>>>>>>>>>\n");
  PITIVI_DEBUG ("PROP_NAME=[%s]\n", prop_name);
  PITIVI_DEBUG ("result flags : %d\n", nb);
  PITIVI_DEBUG ("NUM:%d\n", num);
  PITIVI_DEBUG ("<<<<<<<<<<</TABLE>>>>>>>>>>\n");
  
  pitivi_gstelementsettings_modify_prop (self, prop_name, value);

  return ;
}

PitiviSettingsIoElement *
pitivi_gstelementsettings_get_settings_elem (PitiviGstElementSettings *Properties)
{
  if (Properties->Table) {
    GList *list;

    list = GTK_TABLE (Properties->Table)->children;
    for (; list; list = g_list_next (list)) {
      GtkTableChild *tmp = (GtkTableChild *) list->data;
      
      if (GTK_IS_COMBO_BOX (tmp->widget)) {
	pitivi_gstelementsettings_get_settings_combobox (tmp->widget, Properties);

      } else if (GTK_IS_ENTRY (tmp->widget)) {
	pitivi_gstelementsettings_get_settings_entry (tmp->widget, Properties);

      } else if (GTK_IS_BOX (tmp->widget)) {
	pitivi_gstelementsettings_get_settings_box (tmp->widget, Properties);

      } else if (GTK_IS_TABLE (tmp->widget)) {
	pitivi_gstelementsettings_get_settings_table (tmp->widget, Properties);

      }      
      
    }
  }
  return (Properties->io);
}

/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * */
/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * */
/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * */
/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * */
/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * */
/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * */
/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * */

PitiviGstElementSettings *
pitivi_gstelementsettings_new (PitiviSettingsIoElement *io, gint opt)
{
  PitiviGstElementSettings	*gstelementsettings;

  gstelementsettings = (PitiviGstElementSettings *) g_object_new(PITIVI_GSTELEMENTSETTINGS_TYPE,
								 "option", opt,
								 "io", io,
								 NULL);
  g_assert (gstelementsettings != NULL);
  return gstelementsettings;
}

static GObject *
pitivi_gstelementsettings_constructor (GType type,
			     guint n_construct_properties,
			     GObjectConstructParam * construct_properties)
{
  GObject *obj;
  PitiviGstElementSettings *self;
  /* Invoke parent constructor. */
  obj =  G_OBJECT_CLASS (parent_class)->constructor (type, n_construct_properties,
						     construct_properties);

  /* do stuff. */
  self = (PitiviGstElementSettings *) obj;

  pitivi_gstelementsettings_create_gui (self);

  return obj;
}

static void
pitivi_gstelementsettings_instance_init (GTypeInstance * instance, gpointer g_class)
{
  PitiviGstElementSettings *self = (PitiviGstElementSettings *) instance;

  self->private = g_new0(PitiviGstElementSettingsPrivate, 1);
  
  /* initialize all public and private members to reasonable default values. */ 
  
  self->private->dispose_has_run = FALSE;

  self->Table = NULL;
  self->io = NULL;

  self->private->option = 0;

  /* Do only initialisation here */
  /* The construction of the object should be done in the Constructor
     So that properties set at instanciation can be set */
}

static void
pitivi_gstelementsettings_dispose (GObject *object)
{
  PitiviGstElementSettings	*self = PITIVI_GSTELEMENTSETTINGS(object);

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
pitivi_gstelementsettings_finalize (GObject *object)
{
  PitiviGstElementSettings	*self = PITIVI_GSTELEMENTSETTINGS(object);

  /* 
   * Here, complete object destruction. 
   * You might not need to do much... 
   */

  g_free (self->private);

  G_OBJECT_CLASS (parent_class)->finalize (object);
}

static void
pitivi_gstelementsettings_set_property (GObject * object,
			      guint property_id,
			      const GValue * value, GParamSpec * pspec)
{
  PitiviGstElementSettings *self = (PitiviGstElementSettings *) object;

  switch (property_id)
    {
    case PROP_IO:
      self->io = pitivi_settings_new_io_element_with_io (g_value_get_pointer (value));
      break;
    case PROP_OPT:
      self->private->option = g_value_get_int (value);
      break;
    default:
      /* We don't have any other property... */
      g_assert (FALSE);
      break;
    }
}

static void
pitivi_gstelementsettings_get_property (GObject * object,
			      guint property_id,
			      GValue * value, GParamSpec * pspec)
{
  PitiviGstElementSettings *self = (PitiviGstElementSettings *) object;

  switch (property_id)
    {
    case PROP_IO:
      g_value_set_pointer (value, self->io);
      break;
    case PROP_OPT:
      g_value_set_int (value, self->private->option);
      break;
    default:
      /* We don't have any other property... */
      g_assert (FALSE);
      break;
    }
}

static void
pitivi_gstelementsettings_class_init (gpointer g_class, gpointer g_class_data)
{
  GObjectClass *gobject_class = G_OBJECT_CLASS (g_class);
/*   PitiviGstElementSettingsClass *klass = PITIVI_GSTELEMENTSETTINGS_CLASS (g_class); */

  parent_class = G_OBJECT_CLASS (g_type_class_peek_parent (g_class));

  gobject_class->constructor = pitivi_gstelementsettings_constructor;
  gobject_class->dispose = pitivi_gstelementsettings_dispose;
  gobject_class->finalize = pitivi_gstelementsettings_finalize;

  gobject_class->set_property = pitivi_gstelementsettings_set_property;
  gobject_class->get_property = pitivi_gstelementsettings_get_property;

  /* Install the properties in the class here ! */

  g_object_class_install_property (gobject_class,
				   PROP_IO,
				   g_param_spec_pointer ("io",
							 "io",
							 "Gst Element's stuct info",
							 G_PARAM_CONSTRUCT_ONLY | G_PARAM_WRITABLE)
				   );

  g_object_class_install_property (gobject_class,
				   PROP_OPT,
				   g_param_spec_int ("option",
						     "option",
						     "GstElement's option",
						     0, 10, 0,
						     G_PARAM_CONSTRUCT_ONLY | G_PARAM_WRITABLE)
				   );


}

GType
pitivi_gstelementsettings_get_type (void)
{
  static GType type = 0;
 
  if (type == 0)
    {
      static const GTypeInfo info = {
	sizeof (PitiviGstElementSettingsClass),
	NULL,			/* base_init */
	NULL,			/* base_finalize */
	pitivi_gstelementsettings_class_init,	/* class_init */
	NULL,			/* class_finalize */
	NULL,			/* class_data */
	sizeof (PitiviGstElementSettings),
	0,			/* n_preallocs */
	pitivi_gstelementsettings_instance_init	/* instance_init */
      };
      type = g_type_register_static (GTK_TYPE_VBOX,
				     "PitiviGstElementSettingsType", &info, 0);
    }

  return type;
}
