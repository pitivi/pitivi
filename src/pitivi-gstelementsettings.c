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

#include "pitivi.h"
#include "pitivi-gstelementsettings.h"

static     GObjectClass *parent_class;

#define BORDER		5
#define	X_SPACE_TAB	5
#define Y_SPACE_TAB	5

struct _PitiviGstElementSettingsPrivate
{
  /* instance private members */
  gboolean	dispose_has_run;

  GtkWidget	*frame_info;
  GtkWidget	*frame_prop;

  GstElementFactory *factory;
  GstElement   	    *element;

  //GtkWidget *hprop;
  
};

enum {
  PROP_0,
  PROP_ELM
};


/*
 * forward definitions
 */






/*
 * Insert "added-value" functions here
 */

gchar *
pitivi_gstelementsettings_string_bold (gchar *text)
{
  return (g_locale_to_utf8 (g_strdup_printf ("<b>%s</b>", text),
			    -1, NULL, NULL, NULL));
}

void
pitivi_gstelementsettings_add_new_label (gpointer data, 
					 gchar *text)
{
  GtkWidget *Label;
  
  Label = gtk_label_new (NULL);
  gtk_label_set_markup (GTK_LABEL (Label), text);
  gtk_box_pack_start (GTK_BOX (data), Label, FALSE, FALSE, BORDER);
  return ;
}

void
pitivi_gstelementsettings_add_new_separator (gpointer data)
{
  GtkWidget *Sep;
  
  Sep = gtk_hseparator_new ();
  gtk_box_pack_start (GTK_BOX (data), Sep, FALSE, FALSE, BORDER);
  return ;
}

GtkWidget *
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

void
pitivi_gstelementsettings_add_new_frame_info (PitiviGstElementSettings *self) 
{
    self->private->frame_info = pitivi_gstelementsettings_add_new_frame (self, "Info:");
    pitivi_gstelementsettings_add_new_label (self->private->frame_info, 
					     pitivi_gstelementsettings_string_bold ("Name:"));
    pitivi_gstelementsettings_add_new_label (self->private->frame_info, 
					     (gchar *) gst_element_factory_get_longname (self->private->factory));
    pitivi_gstelementsettings_add_new_label (self->private->frame_info, 
					     pitivi_gstelementsettings_string_bold ("Description:"));
    pitivi_gstelementsettings_add_new_label (self->private->frame_info, 
					     (gchar *) gst_element_factory_get_description (self->private->factory));
    return ;
}

void
pitivi_gstelementsettings_table_widget_add (GtkWidget *Table, GtkWidget *widget, gint row, gint col)
{
  gtk_table_attach(GTK_TABLE(Table), widget,
		   col, col+1, row, row+1, 
		   GTK_FILL, GTK_FILL,
		   X_SPACE_TAB, Y_SPACE_TAB);
  return ;
}

void
pitivi_gstelementsettings_table_new_label_add (PitiviGstElementSettings *self,
						gchar *text, gint row, gint col)
{
  GtkWidget *Label;
  
  Label = gtk_label_new (NULL);
  gtk_label_set_markup (GTK_LABEL (Label), text);
  pitivi_settingswindow_table_widget_add (self->Table, Label, row, col);  
  return ;
}

///////////////////////// FONCTIONS AFF PARAMS ////////////////////////////////////////

///////////////////////////////////////////////////////////////////////////////////////

GtkWidget *
pitivi_gstelementsettings_conf_value_string (const gchar *name, GValue value)
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

  return (text_entry);
}

GtkWidget *
pitivi_gstelementsettings_value_conf_boolean (const gchar *name, GValue value)
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

  return (button_hbox);
}

GtkWidget *
pitivi_gstelementsettings_value_conf_uint (const gchar *name, GValue value, GParamSpec	*param)
{
  GParamSpecUInt	*puint;
  GtkWidget		*spin_button;
  GtkWidget		*prop_value_hbox;

  puint = G_PARAM_SPEC_UINT (param);
  prop_value_hbox = gtk_hbox_new(FALSE, 0);
  spin_button = gtk_spin_button_new_with_range(puint->minimum, puint->maximum, 1);

  /* valeur par defaut */
  gtk_spin_button_set_value(GTK_SPIN_BUTTON(spin_button), g_value_get_uint (&value));
  gtk_box_pack_start(GTK_BOX (prop_value_hbox), spin_button, TRUE, TRUE, 0);

  return (prop_value_hbox);
}

GtkWidget *
pitivi_gstelementsettings_value_conf_int (const gchar *name, GValue value, GParamSpec	*param)
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
pitivi_gstelementsettings_value_conf_uint64 (const gchar *name, GValue value, GParamSpec *param)
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
pitivi_gstelementsettings_value_conf_int64 (const gchar *name, GValue value, GParamSpec *param)
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
pitivi_gstelementsettings_value_conf_ulong (const gchar *name, GValue value, GParamSpec *param)
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
pitivi_gstelementsettings_value_conf_long (const gchar *name, GValue value, GParamSpec *param)
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
pitivi_gstelementsettings_value_conf_float (const gchar *name, GValue value, GParamSpec *param)
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
pitivi_gstelementsettings_value_conf_double (const gchar *name, GValue value, GParamSpec *param)
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
pitivi_gstelementsettings_value_conf_default (const gchar *name, GValue value, GParamSpec *param)
{

  if (G_IS_PARAM_SPEC_ENUM (param)) {    

    gint		i;
    gint		*enum_values;
    gchar		*label;

    GtkWidget	*prop_value_hbox;
    GtkWidget	*prop_value_label;
    GtkWidget	*prop_value_combobox;
    
    GList		*combobox_list;
    GList		*test_list;
    
    prop_value_combobox = gtk_combo_box_new_text();
    prop_value_hbox = gtk_hbox_new(0, FALSE);
    combobox_list = NULL;

    GEnumClass *class = G_ENUM_CLASS (g_type_class_ref (param->value_type));
    enum_values = g_new0 (gint, class->n_values);
    
    for (i=0; i < class->n_values; i++)
      {
	GEnumValue *evalue = &class->values[i];
	
	enum_values[i] = evalue->value;
	label = g_strdup_printf ("%s (%d)", evalue->value_nick, evalue->value);
	gtk_combo_box_insert_text (GTK_COMBO_BOX (prop_value_combobox), i, label);
	combobox_list = g_list_append (combobox_list, &(evalue->value));
      }

    gtk_combo_box_set_active (GTK_COMBO_BOX (prop_value_combobox), g_value_get_enum(&value));

    gtk_box_pack_start (GTK_BOX (prop_value_hbox), prop_value_combobox, TRUE, TRUE, 0);
    
    combobox_list = (gpointer) combobox_list;
    g_object_set_data (G_OBJECT(prop_value_hbox), "combo", combobox_list);
    
    return (prop_value_hbox);
    
  } else if (G_IS_PARAM_SPEC_FLAGS (param)) {
    
    GtkWidget	*Tab;
    GFlagsValue *values;
    guint	j;
    gint	flags_value;
    gint	nb_value;
    GString	*flags = NULL;
    
    values = G_FLAGS_CLASS (g_type_class_ref (param->value_type))->values;
    nb_value = G_FLAGS_CLASS (g_type_class_ref (param->value_type))->n_values;
    flags_value = g_value_get_flags (&value);
    g_print ("FLAG_VALUE:%s\nNB_VALUE:%d\n", flags_value, nb_value);
    
    Tab = gtk_table_new (nb_value, 2, FALSE);

    for (j = 0; j < nb_value; j++) {

      GtkWidget*  check;
      GtkWidget*  label;
      
      check = gtk_check_button_new ();
      g_object_set_data (G_OBJECT (check), "value", &(values[j].value));
      //g_print ("VALUE:%d\n", values[j].value);
      pitivi_gstelementsettings_table_widget_add (Tab, check, j, 1);
      
      label = gtk_label_new (values[j].value_nick);
      pitivi_gstelementsettings_table_widget_add (Tab, label, j, 2);
      
      //g_print ("%s(%d):%s\n",
      //     values[j].value_name, values[j].value, values[j].value_nick);

      if (values[j].value & flags_value) {
	gtk_toggle_button_set_active (GTK_TOGGLE_BUTTON (check), TRUE);
      } else {
	gtk_toggle_button_set_active (GTK_TOGGLE_BUTTON (check), FALSE);
      }

    }
    
    return (Tab);
    
  } else {
    GtkWidget *Label;

    Label = gtk_label_new("Default Case for Value");
    return (Label);
  }
  
}


///////////////////////////////////////////////////////////////////////////////////////

///////////////////////////////////////////////////////////////////////////////////////

void
pitivi_gstelementsettings_table_new_param_add (PitiviGstElementSettings *self,
					       GParamSpec *prop, gint row, gint col)
{
  GtkWidget *tmp;
  GValue value = { 0, };

  g_value_init (&value, prop->value_type);
  g_object_get_property (G_OBJECT (self->private->element), prop->name, &value);

  //g_print ("Prop Nick:%s\n", g_param_spec_get_nick (prop));

  switch (G_VALUE_TYPE (&value)) {
  case G_TYPE_STRING: {
    tmp = pitivi_gstelementsettings_conf_value_string 
      (g_strdup(g_param_spec_get_nick (prop)), value);
    break;
  } case G_TYPE_BOOLEAN: {
    tmp = pitivi_gstelementsettings_value_conf_boolean 
      (g_strdup(g_param_spec_get_nick (prop)), value);
    break;
  } case G_TYPE_UINT: {
    tmp = pitivi_gstelementsettings_value_conf_uint 
      (g_strdup(g_param_spec_get_nick (prop)), value, prop);
    break;
  } case G_TYPE_INT: {
    tmp = pitivi_gstelementsettings_value_conf_int 
      (g_strdup(g_param_spec_get_nick (prop)), value, prop);
    break;
  } case G_TYPE_UINT64: {
    tmp = pitivi_gstelementsettings_value_conf_uint64 
      (g_strdup(g_param_spec_get_nick (prop)), value, prop);
    break;
  } case G_TYPE_INT64: {
    tmp = pitivi_gstelementsettings_value_conf_int64 
      (g_strdup(g_param_spec_get_nick (prop)), value, prop);
    break;
  } case G_TYPE_ULONG: {
    tmp = pitivi_gstelementsettings_value_conf_ulong 
      (g_strdup(g_param_spec_get_nick (prop)), value, prop);
    break;
  } case G_TYPE_LONG: {
    tmp = pitivi_gstelementsettings_value_conf_long 
      (g_strdup(g_param_spec_get_nick (prop)), value, prop);
    break;
  } case G_TYPE_FLOAT: {
    tmp = pitivi_gstelementsettings_value_conf_float 
      (g_strdup(g_param_spec_get_nick (prop)), value, prop);
    break;
  } case G_TYPE_DOUBLE: {
    tmp = pitivi_gstelementsettings_value_conf_double 
      (g_strdup(g_param_spec_get_nick (prop)), value, prop);
    break;
  } default: {
    tmp = pitivi_gstelementsettings_value_conf_default 
      (g_strdup (g_param_spec_get_nick (prop)), value, prop);
    break;
  }
  }

  pitivi_gstelementsettings_table_widget_add (self->Table, tmp, row, col);

  return ;
}

void
pitivi_gstelementsettings_add_new_frame_prop (PitiviGstElementSettings *self,
					      GParamSpec **prop, gint num_prop)
{
  gint cpt;

  self->private->frame_prop = pitivi_gstelementsettings_add_new_frame (self, "Properties:");

  if (num_prop < 2) {
    GtkWidget *Label;

    Label = gtk_label_new ("No Properties ...");
    gtk_box_pack_start (GTK_BOX (self->private->frame_prop),
			Label, FALSE, FALSE, BORDER);
  } else {
    self->Table = gtk_table_new ((num_prop - 1), 2, FALSE);
    gtk_box_pack_start (GTK_BOX (self->private->frame_prop), self->Table, FALSE, FALSE, BORDER);
    
    for (cpt = 1; cpt < num_prop; cpt++) {
      //pitivi_gstelementsettings_table_new_label_add (self, prop[cpt]->name, (cpt - 1), 0);
      pitivi_gstelementsettings_table_new_label_add 
	(self, pitivi_gstelementsettings_string_bold 
	 ((gchar *) g_param_spec_get_nick (prop[cpt])),
	 (cpt - 1), 0);
      pitivi_gstelementsettings_table_new_param_add 
	(self, prop[cpt], (cpt - 1), 1);
    }
  }

  return ;
}

void
pitivi_gstelementsettings_create_gui (PitiviGstElementSettings *self)
{
  gint				num_prop;
  GParamSpec			**prop;

  self->private->factory = gst_element_factory_find(self->elm);
  if (self->private->factory) {
    pitivi_gstelementsettings_add_new_frame_info (self);
    
    self->private->element = gst_element_factory_create(self->private->factory, "test");
    prop = g_object_class_list_properties(G_OBJECT_GET_CLASS (self->private->element), &num_prop);
    g_print ("Num Properties:%d\n", num_prop);
    
    pitivi_gstelementsettings_add_new_frame_prop (self, prop, num_prop);
  } else {
    pitivi_gstelementsettings_add_new_label (self, "Not A Factory Element!!\n");
  }
  gtk_widget_show_all (GTK_WIDGET (self));  
  return ;
}


/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * */

/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * */

/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * */

/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * */

/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * */

/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * */

/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * */

PitiviGstElementSettings *
pitivi_gstelementsettings_new(gchar *elm)
{
  PitiviGstElementSettings	*gstelementsettings;

  gstelementsettings = (PitiviGstElementSettings *) g_object_new(PITIVI_GSTELEMENTSETTINGS_TYPE,
								 "elm", elm,
								 NULL);
  g_assert(gstelementsettings != NULL);
  return gstelementsettings;
}

static GObject *
pitivi_gstelementsettings_constructor (GType type,
			     guint n_construct_properties,
			     GObjectConstructParam * construct_properties)
{
  GObject *obj;
  /* Invoke parent constructor. */
  obj =  G_OBJECT_CLASS (parent_class)->constructor (type, n_construct_properties,
						     construct_properties);

  /* do stuff. */
  PitiviGstElementSettings *self = (PitiviGstElementSettings *) obj;

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
  g_free (self->elm);
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
    case PROP_ELM:
      self->elm = g_value_dup_string (value);
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
    case PROP_ELM:
      g_value_set_string (value, self->elm);
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
  PitiviGstElementSettingsClass *klass = PITIVI_GSTELEMENTSETTINGS_CLASS (g_class);

  parent_class = G_OBJECT_CLASS (g_type_class_peek_parent (g_class));

  gobject_class->constructor = pitivi_gstelementsettings_constructor;
  gobject_class->dispose = pitivi_gstelementsettings_dispose;
  gobject_class->finalize = pitivi_gstelementsettings_finalize;

  gobject_class->set_property = pitivi_gstelementsettings_set_property;
  gobject_class->get_property = pitivi_gstelementsettings_get_property;

  /* Install the properties in the class here ! */

  g_object_class_install_property (gobject_class,
				   PROP_ELM,
				   g_param_spec_string ("elm",
							"elm",
							"GstElement's name",
							NULL, 
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
