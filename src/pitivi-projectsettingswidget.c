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

/*
  TODO

  * Implement GUI => PitiviProjectSettings ( _get_copy() )
  DONE * Implement PitiviProjectSettings => GUI ( update_gui() )
  * Implement Audio/Video/Container codecs control (Configure Button)
  DONE * (de)Activate Custom controls depending on combobox selection
  * Implement codecs settings <=> PitiviGstElementSettings
  * Make the graphical layout less ugly
*/

#include "pitivi.h"
#include "pitivi-debug.h"
#include "pitivi-mainapp.h"
#include "pitivi-projectsettings.h"
#include "pitivi-projectsettingswidget.h"
#include "pitivi-gstelementsettings.h"
#include "pitivi-settings.h"
#include "pitivi-windows.h"

enum {
  PROP_0,
  PROP_MAINAPP,
  PROP_SETTINGS
};

typedef struct {
  gchar	*label;
  guint	width;
  guint	height;
}	VideoSize;

static	VideoSize videosizetab[] = {
  {"DV PAL (720x576)",	720,	576},
  {"640x480",		640,	480},
  {"Custom",		0,	0},
  {NULL,		0,	0}
};

/* DON'T FORGET TO UPDATE THE _CUSTOM !! */

#define	IDX_VIDEO_SIZE_CUSTOM 2

typedef struct {
  gchar	*label;
  gfloat	rate;
} charfloat;

static	charfloat videoratetab[] = {
  {"PAL 25fps",		25.0f},
  {"NTSC 30fps",	30.0f},
  {"Custom",	0.0f},
  {NULL,	0}
};

#define	IDX_VIDEO_RATE_CUSTOM 2

typedef struct{
  gchar	*label;
  guint	depth;
}	charuint;

static	charuint audioratetab[] = {
  {"8 KHz",		8000},
  {"11.025 KHz",	11025},
  {"16 KHz",		16000},
  {"22.05 KHz",		22050},
  {"24 KHz",		24000},
  {"44.1 KHz",		44100},
  {"48 KHz",		48000},
  {"88.2 KHz",		88200},
  {"96 KHz",		96000},
  {"Custom",		0},
  {NULL,		0}
};

#define	IDX_AUDIO_RATE_CUSTOM 9

static	charuint audiochanntab[] = {
  {"Mono (1)",		1},
  {"Stereo (2)",	2},
  {"Custom",		0},
  {NULL,		0}
};

#define	IDX_AUDIO_CHANN_CUSTOM 2

static	charuint audiodepthtab[] = {
  {"8 bits",		8},
  {"16 bits",		16},
  {"24 bits",		24},
  {"32 bits",		32},
  {NULL,		0}
};

static     GObjectClass *parent_class;

/*
  PitiviProjectSettingsWidget
  
  A GtkWidget to manipulated PitiviProjectSettings

  Functions:
    _set_settings : Sets the active PitiviProjectSettings
    _blank : Sets the widget to default value and a NULL settings
    _get_copy : Returns a copy of the PitiviProjectSettings selected
  Eventually :
    _get_modified : Returns the PitiviProjectSettings modified 
     But could really be done by the parent handler (window,...)

*/


struct _PitiviProjectSettingsWidgetPrivate
{
  /* instance private members */
  gboolean	dispose_has_run;

  PitiviMainApp	*mainapp;

  GtkWidget	*vbox;

  GtkSizeGroup	*sizegroupleft;

  GtkWidget	*nameentry;
  GtkTextBuffer	*descentry;

  GtkWidget	*videocodeccbox;
  GtkWidget	*videoconfbutton;
  PitiviSettingsIoElement	*videocodecprops;

  GtkWidget	*videosizecbox;
  GtkWidget	*videosizehbox;
  GtkWidget	*videowidthentry;
  GtkWidget	*videoheightentry;

  GtkWidget	*videoratecbox;
  GtkWidget	*videoratehbox;
  GtkWidget	*videorateentry;

  GtkWidget	*audiocodeccbox;
  GtkWidget	*audioconfbutton;
  PitiviSettingsIoElement	*audiocodecprops;

  GtkWidget	*audiodepthcbox;

  GtkWidget	*audiochanncbox;
  GtkWidget	*audiochannhbox;
  GtkWidget	*audiochannentry;

  GtkWidget	*audioratecbox;
  GtkWidget	*audioratehbox;
  GtkWidget	*audiorateentry;

  GtkWidget	*containercbox;
  GtkWidget	*containerconfbutton;
  PitiviSettingsIoElement	*containercodecprops;

  GList		*venc_list;
  GList		*aenc_list;
  GList		*container_list;
};

/*
 * forward definitions
 */

static void
pitivi_projectsettingswidget_update_gui (PitiviProjectSettingsWidget *self);

static void
pitivi_projectsettingswidget_update_props (PitiviProjectSettingsWidget *self);

static void
pitivi_projectsettingswidget_reset_gui (PitiviProjectSettingsWidget *self);

static void
pitivi_projectsettingswidget_reset_props (PitiviProjectSettingsWidget *self);


static const gchar *
get_cbox_selected_item_name (GtkComboBox *cbox, GList *plist);

/*
 * Insert "added-value" functions here
 */

/**
 * pitivi_projectsettingswidget_set_settings:
 * @self : the widget
 * @settings : the project settings
 */

void
pitivi_projectsettingswidget_set_settings (PitiviProjectSettingsWidget *self,
					   PitiviProjectSettings *settings)
{
  PITIVI_DEBUG ("Settings : %p", settings);
  if (self->settings)
    g_object_unref (G_OBJECT (self->settings));
  g_object_ref (G_OBJECT (settings));
  self->settings = settings;
  pitivi_projectsettingswidget_update_props (self);
  pitivi_projectsettingswidget_update_gui (self);
}

void
pitivi_projectsettingswidget_blank (PitiviProjectSettingsWidget *self)
{
  if (self->settings)
    g_object_unref (G_OBJECT (self->settings));
  self->settings = NULL;
  pitivi_projectsettingswidget_reset_props (self);
  pitivi_projectsettingswidget_reset_gui (self);
}

PitiviProjectSettings *
pitivi_projectsettingswidget_get_copy (PitiviProjectSettingsWidget *self)
{
  PitiviProjectSettings	*res = NULL;
  /*
    Create a new PitiviProjectSettings for the values in the widget 
    and return it. Return NULL if there's a problem
  */
  return res;
}

/* PitiviProjectSettings * */
/* pitivi_projectsettingswidget_get_modified (PitiviProjectSettingsWidget *self) */
/* { */
/*   PitiviProjectSettings *res = NULL; */
/*   /\* */
/*     Modify the values of self->settings according to the values in the widget */
/*     and return it. If there's no self->settings, return NULL. */
/*   *\/ */
/*   if (!self->settings) */
/*     return NULL; */
/*   return res; */
/* } */

static void
video_rate_cbox_changed (GtkComboBox *cbox, PitiviProjectSettingsWidget *self)
{
  int	i;

  i = gtk_combo_box_get_active (cbox);
  gtk_widget_set_sensitive (self->private->videoratehbox,
			    (i == IDX_VIDEO_RATE_CUSTOM) ? TRUE : FALSE);
  if (i != IDX_VIDEO_RATE_CUSTOM)
    gtk_entry_set_text (GTK_ENTRY (self->private->videorateentry), 
			g_strdup_printf("%f", videoratetab[i].rate));
}

static void
audio_rate_cbox_changed (GtkComboBox *cbox, PitiviProjectSettingsWidget *self)
{
  int	i;

  i = gtk_combo_box_get_active (cbox);
  gtk_widget_set_sensitive (self->private->audioratehbox,
			    (i == IDX_AUDIO_RATE_CUSTOM) ? TRUE : FALSE);
  if (i != IDX_AUDIO_RATE_CUSTOM)
    gtk_spin_button_set_value (GTK_SPIN_BUTTON (self->private->audiorateentry), 
			       audioratetab[i].depth);
}

static void
audio_chann_cbox_changed (GtkComboBox *cbox, PitiviProjectSettingsWidget *self)
{
  int	i;

  i = gtk_combo_box_get_active (cbox);
  gtk_widget_set_sensitive (self->private->audiochannhbox,
			    (i == IDX_AUDIO_CHANN_CUSTOM) ? TRUE : FALSE);
  if (i != IDX_AUDIO_CHANN_CUSTOM)
    gtk_spin_button_set_value (GTK_SPIN_BUTTON (self->private->audiochannentry),
			       audiochanntab[i].depth);
}

static void
video_size_cbox_changed (GtkComboBox *cbox, PitiviProjectSettingsWidget *self)
{
  int	i;

  i = gtk_combo_box_get_active (cbox);
  gtk_widget_set_sensitive (self->private->videosizehbox,
			    (i == IDX_VIDEO_SIZE_CUSTOM) ? TRUE : FALSE);
  if (i != IDX_VIDEO_SIZE_CUSTOM) {
    gtk_spin_button_set_value (GTK_SPIN_BUTTON (self->private->videowidthentry),
			       videosizetab[i].width);
    gtk_spin_button_set_value (GTK_SPIN_BUTTON (self->private->videoheightentry),
			       videosizetab[i].height);
  }
}

static void
video_conf_clicked (GtkButton *button, PitiviProjectSettingsWidget *self)
{
  GtkWidget	*dialog;
  GtkWidget	*widget;
  PitiviSettingsIoElement	*io;
  const gchar		*selectedfactory;

  PITIVI_DEBUG ("clicked...");
  dialog = gtk_dialog_new_with_buttons ("Configure Video Codec properties",
					NULL,
					GTK_DIALOG_MODAL,
					GTK_STOCK_OK,
					GTK_RESPONSE_ACCEPT,
					GTK_STOCK_CANCEL,
					GTK_RESPONSE_CANCEL,
					NULL);

  selectedfactory = get_cbox_selected_item_name(GTK_COMBO_BOX (self->private->videocodeccbox), 
						self->private->venc_list);
  PITIVI_DEBUG ("got selectedfactory");
  if ((!self->private->videocodecprops)
      || ( g_ascii_strcasecmp (selectedfactory,
			       gst_plugin_feature_get_name (GST_PLUGIN_FEATURE(self->private->videocodecprops->factory))) )) {
    PITIVI_DEBUG ("no existing IO or not same as selected codec");
    io = pitivi_settings_new_io_element_with_factory (gst_element_factory_find (selectedfactory));
  } else {
    PITIVI_DEBUG ("taking existing IO");
    io = self->private->videocodecprops;
  }
  widget = GTK_WIDGET (pitivi_gstelementsettings_new (io, 0));

  gtk_container_add (GTK_CONTAINER (GTK_DIALOG(dialog)->vbox),
		     widget);
  PITIVI_DEBUG ("Added widget to dialog box's vbox");

  gtk_widget_show_all (dialog);
  switch (gtk_dialog_run (GTK_DIALOG (dialog))) {
  case GTK_RESPONSE_ACCEPT:
    PITIVI_DEBUG ("OK");
    break;
  case GTK_RESPONSE_CANCEL:
  default:
    PITIVI_DEBUG ("Cancel...");
    break;
  }
  gtk_widget_destroy (dialog);
}

static void
audio_conf_clicked (GtkButton *button, PitiviProjectSettingsWidget *self)
{
  
}

static void
container_conf_clicked (GtkButton *button, PitiviProjectSettingsWidget *self)
{
  
}

/* activate_combobox_entry : ONLY for codec combobox */

static void
activate_combobox_entry (GtkWidget *combobox, GList *list, gchar *tofind)
{
  int	i;
  GList	*elm;

  for (i = 0, elm = list; elm; elm = g_list_next (elm), i++) {
    if (!(g_ascii_strcasecmp ((gchar *) elm->data, tofind)))
      break;
  }
  gtk_combo_box_set_active (GTK_COMBO_BOX (combobox), i);
}

static void
update_video_width_height (PitiviProjectSettingsWidget *self, gint width, gint height)
{
  gint	i;

  PITIVI_DEBUG ("width:%d, height:%d", width, height);
  /* Look trough the tabs if we have an existing preset */
  for (i = 0; videosizetab[i].label; i++)
    if ((videosizetab[i].width == width) && (videosizetab[i].height == height))
      break;
  if (!videosizetab[i].label) {
    /* Custom, set text */
    gtk_spin_button_set_value (GTK_SPIN_BUTTON (self->private->videowidthentry), width);
    gtk_spin_button_set_value (GTK_SPIN_BUTTON (self->private->videoheightentry), height);
    i--;
  };
  gtk_combo_box_set_active (GTK_COMBO_BOX (self->private->videosizecbox), i);
  video_size_cbox_changed(GTK_COMBO_BOX (self->private->videosizecbox), self);
}

static void
update_video_framerate (PitiviProjectSettingsWidget *self, gfloat rate)
{
  gint	i;

  for (i = 0; videoratetab[i].label; i++)
    if (videoratetab[i].rate == rate)
      break;
  if (!videoratetab[i].label) {
    gtk_entry_set_text (GTK_ENTRY (self->private->videorateentry), 
			g_strdup_printf("%f", rate));
    i--;
  }
  gtk_combo_box_set_active (GTK_COMBO_BOX (self->private->videoratecbox), i);
  video_rate_cbox_changed (GTK_COMBO_BOX (self->private->videoratecbox), self);
}

static void
update_audio_depth (PitiviProjectSettingsWidget *self, gint depth)
{
  gint	i;

  PITIVI_DEBUG("depth : %d", depth);
  for (i = 0; audiodepthtab[i].label; i++)
    if (audiodepthtab[i].depth == depth)
      break;
  if (!audiodepthtab[i].label)
    i = -1;
  gtk_combo_box_set_active (GTK_COMBO_BOX (self->private->audiodepthcbox), i);
}

static void
update_audio_rate (PitiviProjectSettingsWidget *self, gint rate)
{
  gint	i;

  for (i = 0; audioratetab[i].label; i++)
    if (audioratetab[i].depth == rate)
      break;
  if (!audioratetab[i].label) {
    i--;
    gtk_spin_button_set_value (GTK_SPIN_BUTTON (self->private->audiorateentry), rate);
  }
  gtk_combo_box_set_active (GTK_COMBO_BOX (self->private->audioratecbox), i);
  audio_rate_cbox_changed (GTK_COMBO_BOX (self->private->audioratecbox), self);
}

static void
update_audio_chann (PitiviProjectSettingsWidget *self, gint rate)
{
  gint	i;

  for (i = 0; audiochanntab[i].label; i++)
    if (audiochanntab[i].depth == rate)
      break;
  if (!audiochanntab[i].label) {
    i--;
    gtk_spin_button_set_value (GTK_SPIN_BUTTON (self->private->audiochannentry), rate);
  }
  gtk_combo_box_set_active (GTK_COMBO_BOX (self->private->audiochanncbox), i);
  audio_rate_cbox_changed (GTK_COMBO_BOX (self->private->audiochanncbox), self);
}

static void
pitivi_projectsettingswidget_update_gui (PitiviProjectSettingsWidget *self)
{
  PitiviMediaSettings	*mset;
  gint	width, height;

  if (!self->settings)
    return;
  /* Set name and description */
  gtk_entry_set_text (GTK_ENTRY (self->private->nameentry),
		      self->settings->name);
  gtk_text_buffer_set_text (self->private->descentry,
			    self->settings->description, -1);


  /* Set video properties */
  mset = (PitiviMediaSettings *) self->settings->media_settings->data;
  activate_combobox_entry (self->private->videocodeccbox, self->private->venc_list,
			   mset->codec_factory_name);
  /* TODO : Set video codec properties */
  if (!pitivi_projectsettings_get_videosize (self->settings, &width, &height))
    PITIVI_WARNING ("Couldn't get videosize from PitiviProjectSettings !");
  else
    update_video_width_height (self, width, height);
  update_video_framerate (self, pitivi_projectsettings_get_videorate (self->settings));


  /* Set audio properties */
  mset = (PitiviMediaSettings *) self->settings->media_settings->next->data;
  activate_combobox_entry (self->private->audiocodeccbox, self->private->aenc_list,
			   mset->codec_factory_name);
  /* TODO : Set audio codec properties */
  update_audio_depth (self, pitivi_projectsettings_get_audiodepth(self->settings));
  update_audio_chann (self, pitivi_projectsettings_get_audiochann(self->settings));
  update_audio_rate (self, pitivi_projectsettings_get_audiorate (self->settings));
  

  /* Set container properties */
  activate_combobox_entry (self->private->containercbox, self->private->container_list,
			   self->settings->container_factory_name);
  /* TODO : Set container codec properties */
}

static void
pitivi_projectsettingswidget_update_props (PitiviProjectSettingsWidget *self)
{
  PitiviMediaSettings	*mset;

  pitivi_projectsettingswidget_reset_props (self);
  mset = (PitiviMediaSettings *) self->settings->media_settings->data;
  self->private->videocodecprops = pitivi_mediasettings_to_settingsioelement (mset);

  mset = (PitiviMediaSettings *) self->settings->media_settings->next->data;
  self->private->audiocodecprops = pitivi_mediasettings_to_settingsioelement (mset);

  self->private->containercodecprops = pitivi_containersettings_to_settingsioelement (self->settings);
}

static void
pitivi_projectsettingswidget_reset_gui (PitiviProjectSettingsWidget *self)
{
  /* Set every widget to their default value */
}

static void
pitivi_projectsettingswidget_reset_props (PitiviProjectSettingsWidget *self)
{
  if (self->private->videocodecprops) {
    g_free (self->private->videocodecprops);
    self->private->videocodecprops = NULL;
  }
  if (self->private->audiocodecprops) {
    g_free (self->private->audiocodecprops);
    self->private->audiocodecprops = NULL;
  }
  if (self->private->containercodecprops) {
    g_free (self->private->containercodecprops);
    self->private->containercodecprops = NULL;
  }
}



/*****
      VALUE RECUPERATION
*****/

static const gchar *
get_cbox_selected_item_name (GtkComboBox *cbox, GList *plist)
{
  int	i,j;
  GList	*tmp;

  if ((i = gtk_combo_box_get_active (cbox)) == -1)
    return NULL;
  for (tmp = plist, j = 0; j < i; j++)
    tmp = g_list_next (tmp);
  return ((gchar *) tmp->data);
}


/*****
      GUI CREATION
*****/

static GtkWidget *
make_new_videosize_cbox (void)
{
  GtkWidget	*cbox;
  int		i;

  cbox = gtk_combo_box_new_text();
  for (i = 0; videosizetab[i].label; i++)
    gtk_combo_box_append_text (GTK_COMBO_BOX (cbox), videosizetab[i].label);
  return cbox;
}

static GtkWidget *
make_new_videorate_cbox (void)
{
  GtkWidget	*cbox;
  int		i;

  cbox = gtk_combo_box_new_text();
  for (i = 0; videoratetab[i].label; i++)
    gtk_combo_box_append_text (GTK_COMBO_BOX (cbox), videoratetab[i].label);
  return cbox;
}

static GtkWidget *
make_new_audiorate_cbox (void)
{
  GtkWidget	*cbox;
  int		i;

  cbox = gtk_combo_box_new_text();
  for (i = 0; audioratetab[i].label; i++)
    gtk_combo_box_append_text (GTK_COMBO_BOX (cbox), audioratetab[i].label);
  return cbox;
}

static GtkWidget *
make_new_audiochann_cbox (void)
{
  GtkWidget	*cbox;
  int		i;

  cbox = gtk_combo_box_new_text();
  for (i = 0; audiochanntab[i].label; i++)
    gtk_combo_box_append_text (GTK_COMBO_BOX (cbox), audiochanntab[i].label);
  return cbox;
}

static GtkWidget *
make_new_audiodepth_cbox (void)
{
  GtkWidget	*cbox;
  int		i;

  cbox = gtk_combo_box_new_text();
  for (i = 0; audiodepthtab[i].label; i++)
    gtk_combo_box_append_text (GTK_COMBO_BOX (cbox), audiodepthtab[i].label);
  return cbox;
}

static GtkWidget *
make_new_codec_cbox (gchar *klass, GList **plist)
{
  GtkWidget	*cbox;
  GList		*codecs;
  GList		*mylist = NULL;
  gchar		*msg, *msg2;

  cbox = gtk_combo_box_new_text ();
  for (codecs = gst_registry_pool_feature_list (GST_TYPE_ELEMENT_FACTORY);
       codecs; codecs = g_list_next (codecs)) {
    if (!(g_ascii_strcasecmp (klass, gst_element_factory_get_klass (GST_ELEMENT_FACTORY (codecs->data))))) {
      GstPluginFeature *feat = GST_PLUGIN_FEATURE (codecs->data);
      
      msg = g_strdup_printf ("%s (%s)", gst_element_factory_get_longname (GST_ELEMENT_FACTORY (feat)),
			     gst_plugin_feature_get_name (feat));
      msg2 = g_strdup (gst_plugin_feature_get_name (feat));
      gtk_combo_box_append_text (GTK_COMBO_BOX (cbox), msg);
      mylist = g_list_append (mylist, msg2);
    }
  }
  gtk_combo_box_set_active (GTK_COMBO_BOX (cbox), 0);
  *plist = mylist;
  return cbox;
}

static GtkWidget*
make_new_container_cbox (PitiviProjectSettingsWidget *self)
{
  GtkWidget	*cbox;
  GList		*container;
  GList		*mylist = NULL;
  gchar		*msg, *msg2;

  cbox = gtk_combo_box_new_text();
  for (container = self->private->mainapp->global_settings->container;
       container; 
       container = container->next) {
    PitiviSettingsMimeType *type = (PitiviSettingsMimeType *) container->data;
    if (type->encoder) {
      char *elt = (char *) type->encoder->data;
      GstPluginFeature *feat;

      feat = gst_registry_pool_find_feature (elt, GST_TYPE_ELEMENT_FACTORY);
      msg = g_strdup_printf ("%s (%s)", gst_element_factory_get_longname (GST_ELEMENT_FACTORY (feat)),
			     elt);
      msg2 = g_strdup (elt);
      gtk_combo_box_append_text (GTK_COMBO_BOX (cbox), msg);
      mylist = g_list_append (mylist, msg2);
    }
  }
  gtk_combo_box_set_active (GTK_COMBO_BOX (cbox), 0);
  self->private->container_list = mylist;
  return cbox;
}


static GtkWidget *
pitivi_psw_make_audioframe (PitiviProjectSettingsWidget *self)
{
  GtkWidget	*frame;
  GtkWidget	*table;
  GtkWidget	*codeclabel, *depthlabel, *channlabel, *ratelabel;
  GtkWidget	*hzlabel, *nblabel;

  frame = gtk_frame_new ("Audio settings");
  table = gtk_table_new (4, 4, FALSE);

  /* Codec */
  codeclabel = gtk_label_new ("Codec :");
  gtk_misc_set_alignment (GTK_MISC(codeclabel), 0.0f, 0.0f);
  gtk_size_group_add_widget (self->private->sizegroupleft, codeclabel);
  gtk_table_attach (GTK_TABLE (table), codeclabel,
		    0, 1, 0, 1, FALSE, FALSE, 5, 5);

  self->private->audiocodeccbox = make_new_codec_cbox ("Codec/Encoder/Audio", &(self->private->aenc_list));
  gtk_table_attach (GTK_TABLE (table), self->private->audiocodeccbox,
		    1, 3, 0, 1, GTK_EXPAND | GTK_FILL, FALSE, 5, 5);

  self->private->audioconfbutton = gtk_button_new_with_label ("Configure");
  gtk_table_attach (GTK_TABLE (table), self->private->audioconfbutton,
		    3, 4, 0, 1, FALSE, FALSE, 5, 5);
  g_signal_connect (G_OBJECT (self->private->audioconfbutton),
		    "clicked", G_CALLBACK (audio_conf_clicked),
		    self);
  
  /* Depth */
  depthlabel = gtk_label_new ("Depth :");
  gtk_misc_set_alignment (GTK_MISC(depthlabel), 0.0f, 0.0f);
  gtk_size_group_add_widget (self->private->sizegroupleft, depthlabel);
  gtk_table_attach (GTK_TABLE (table), depthlabel,
		    0, 1, 1, 2, FALSE, FALSE, 5, 5);

  self->private->audiodepthcbox = make_new_audiodepth_cbox();
  gtk_table_attach (GTK_TABLE (table), self->private->audiodepthcbox,
		    1, 3, 1, 2, GTK_EXPAND | GTK_FILL , FALSE, 5, 5);

  /* Channels */
  channlabel = gtk_label_new ("Channels :");
  gtk_misc_set_alignment (GTK_MISC(channlabel), 0.0f, 0.0f);
  gtk_size_group_add_widget (self->private->sizegroupleft, channlabel);
  gtk_table_attach (GTK_TABLE (table), channlabel,
		    0, 1, 2, 3, FALSE, FALSE, 5, 5);

  self->private->audiochanncbox = make_new_audiochann_cbox();
  g_signal_connect (G_OBJECT(self->private->audiochanncbox),
		    "changed", G_CALLBACK (audio_chann_cbox_changed), self);
  gtk_table_attach (GTK_TABLE (table), self->private->audiochanncbox,
		    1, 2, 2, 3, GTK_EXPAND | GTK_FILL , FALSE, 5, 5);

  self->private->audiochannhbox = gtk_hbox_new (FALSE, 5);
  self->private->audiochannentry = gtk_spin_button_new_with_range (1, G_MAXINT, 1);
  nblabel = gtk_label_new ("Channels");
  gtk_box_pack_start (GTK_BOX (self->private->audiochannhbox),
		      self->private->audiochannentry, FALSE, FALSE, 5);
  gtk_widget_set_sensitive (self->private->audiochannhbox, FALSE);
  gtk_box_pack_start (GTK_BOX (self->private->audiochannhbox),
		      nblabel, FALSE, FALSE, 5);
  gtk_table_attach (GTK_TABLE (table), self->private->audiochannhbox,
		    2, 4, 2, 3, FALSE, FALSE, 5, 5);


  /* Rate */
  ratelabel = gtk_label_new ("Rate :");
  gtk_misc_set_alignment (GTK_MISC(ratelabel), 0.0f, 0.0f);
  gtk_size_group_add_widget (self->private->sizegroupleft, ratelabel);
  gtk_table_attach (GTK_TABLE (table), ratelabel,
		    0, 1, 3, 4, FALSE, FALSE, 5, 5);

  self->private->audioratecbox = make_new_audiorate_cbox();
  g_signal_connect (G_OBJECT(self->private->audioratecbox),
		    "changed", G_CALLBACK (audio_rate_cbox_changed), self);
  gtk_table_attach (GTK_TABLE (table), self->private->audioratecbox,
		    1, 2, 3, 4, GTK_EXPAND | GTK_FILL , FALSE, 5, 5);

  self->private->audioratehbox = gtk_hbox_new (FALSE, 5);
  self->private->audiorateentry = gtk_spin_button_new_with_range (25, G_MAXINT, 25);
  gtk_box_pack_start (GTK_BOX (self->private->audioratehbox), self->private->audiorateentry, TRUE, TRUE, 0);
  hzlabel = gtk_label_new ("Hz");
  gtk_box_pack_start (GTK_BOX (self->private->audioratehbox), hzlabel, FALSE, FALSE, 0);
  gtk_widget_set_sensitive (self->private->audioratehbox, FALSE);
  gtk_table_attach (GTK_TABLE (table), self->private->audioratehbox,
		    2, 4, 3, 4, FALSE, FALSE, 5, 5);

  gtk_container_add (GTK_CONTAINER (frame), table);
  return frame;
}

static GtkWidget *
pitivi_psw_make_videoframe (PitiviProjectSettingsWidget *self)
{
  GtkWidget	*frame;
  GtkWidget	*table;
  GtkWidget	*codeclabel, *sizelabel, *ratelabel;
  GtkWidget	*xlabel, *pixellabel, *fpslabel;

  frame = gtk_frame_new ("Video settings");
  table = gtk_table_new (3, 4, FALSE);

  /* Codec */
  codeclabel = gtk_label_new ("Codec :");
  gtk_misc_set_alignment (GTK_MISC(codeclabel), 0.0f, 0.0f);
  gtk_size_group_add_widget (self->private->sizegroupleft, codeclabel);
  gtk_table_attach (GTK_TABLE (table), codeclabel,
		    0, 1, 0, 1, FALSE, FALSE, 5, 5);

  self->private->videocodeccbox = make_new_codec_cbox ("Codec/Encoder/Video", &(self->private->venc_list));
  gtk_table_attach (GTK_TABLE (table), self->private->videocodeccbox,
		    1, 3, 0, 1, GTK_EXPAND | GTK_FILL, FALSE, 5, 5);

  self->private->videoconfbutton = gtk_button_new_with_label ("Configure");
  gtk_table_attach (GTK_TABLE (table), self->private->videoconfbutton,
		    3, 4, 0, 1, FALSE, FALSE, 5, 5);
  g_signal_connect (G_OBJECT (self->private->videoconfbutton),
		    "clicked", G_CALLBACK (video_conf_clicked),
		    self);
  
  /* Size */
  sizelabel = gtk_label_new ("Size :");
  gtk_misc_set_alignment (GTK_MISC(sizelabel), 0.0f, 0.0f);
  gtk_size_group_add_widget (self->private->sizegroupleft, sizelabel);
  gtk_table_attach (GTK_TABLE (table), sizelabel,
		    0, 1, 1, 2, FALSE, FALSE, 5, 5);

  self->private->videosizecbox = make_new_videosize_cbox();
  g_signal_connect (G_OBJECT(self->private->videosizecbox),
		    "changed", G_CALLBACK (video_size_cbox_changed), self);
  gtk_table_attach (GTK_TABLE (table), self->private->videosizecbox,
		    1, 2, 1, 2, GTK_EXPAND | GTK_FILL , FALSE, 5, 5);

  self->private->videosizehbox = gtk_hbox_new (FALSE, 2);
  self->private->videowidthentry = gtk_spin_button_new_with_range(16, G_MAXINT, 16);
  xlabel = gtk_label_new("x");
  self->private->videoheightentry = gtk_spin_button_new_with_range(16, G_MAXINT, 16);
  pixellabel = gtk_label_new("pixels");
  gtk_box_pack_start (GTK_BOX (self->private->videosizehbox), self->private->videowidthentry, FALSE, FALSE, 2);
  gtk_box_pack_start (GTK_BOX (self->private->videosizehbox), xlabel, FALSE, FALSE, 2);
  gtk_box_pack_start (GTK_BOX (self->private->videosizehbox), self->private->videoheightentry, FALSE, FALSE, 2);
  gtk_box_pack_start (GTK_BOX (self->private->videosizehbox), pixellabel, FALSE, FALSE, 2);
  gtk_widget_set_sensitive (self->private->videosizehbox, FALSE);
  gtk_table_attach (GTK_TABLE (table), self->private->videosizehbox,
		    2, 4, 1, 2, FALSE, FALSE, 5, 5);

  /* Frame Rate */
  ratelabel = gtk_label_new ("Framerate :");
  gtk_misc_set_alignment (GTK_MISC(ratelabel), 0.0f, 0.0f);
  gtk_size_group_add_widget (self->private->sizegroupleft, ratelabel);
  gtk_table_attach (GTK_TABLE (table), ratelabel,
		    0, 1, 2, 3, FALSE, FALSE, 5, 5);

  self->private->videoratecbox = make_new_videorate_cbox();
  g_signal_connect (G_OBJECT(self->private->videoratecbox),
		    "changed", G_CALLBACK (video_rate_cbox_changed), self);
  gtk_table_attach (GTK_TABLE (table), self->private->videoratecbox,
		    1, 2, 2, 3, GTK_EXPAND | GTK_FILL, FALSE, 5, 5);

  self->private->videoratehbox = gtk_hbox_new (FALSE, 2);
  self->private->videorateentry = gtk_entry_new();
  fpslabel = gtk_label_new ("fps");
  gtk_box_pack_start (GTK_BOX (self->private->videoratehbox), self->private->videorateentry, FALSE, FALSE, 2);
  gtk_box_pack_start (GTK_BOX (self->private->videoratehbox), fpslabel, FALSE, FALSE, 2);
  gtk_widget_set_sensitive (self->private->videoratehbox, FALSE);
  gtk_table_attach (GTK_TABLE (table), self->private->videoratehbox,
		    2, 4, 2, 3, FALSE, FALSE, 5, 5);

  gtk_container_add (GTK_CONTAINER (frame), table);
  return frame;
}

static GtkWidget *
pitivi_psw_make_containerframe (PitiviProjectSettingsWidget *self)
{
  GtkWidget	*frame;
  GtkWidget	*cbox;
  GtkWidget	*codeclabel;

  frame = gtk_frame_new ("Container");
  cbox = gtk_table_new (3, 1, FALSE);

  codeclabel = gtk_label_new ("Container :");
  gtk_misc_set_alignment (GTK_MISC(codeclabel), 0.0f, 0.0f);
  gtk_size_group_add_widget (self->private->sizegroupleft, codeclabel);
  gtk_table_attach (GTK_TABLE (cbox), codeclabel,
		    0, 1, 0, 1, FALSE, FALSE, 5, 5);

  self->private->containercbox = make_new_container_cbox (self);
  gtk_table_attach (GTK_TABLE (cbox), self->private->containercbox,
		    1, 2, 0, 1, GTK_EXPAND | GTK_FILL, FALSE, 5, 5);
  
  self->private->containerconfbutton = gtk_button_new_with_label ("Configure");
  gtk_table_attach (GTK_TABLE (cbox), self->private->containerconfbutton,
		    2, 3, 0, 1, FALSE, FALSE, 5, 5);
  g_signal_connect (G_OBJECT (self->private->containerconfbutton),
		    "clicked", G_CALLBACK (container_conf_clicked),
		    self);

  gtk_container_add (GTK_CONTAINER (frame), cbox);
  return frame;
}

void
pitivi_psw_make_gui(PitiviProjectSettingsWidget *self)
{
  GtkWidget	*namelabel, *desclabel;
  GtkWidget	*descscroll, *descview;
  GtkTextTagTable	*desctagtable;
  GtkWidget	*audioframe, *videoframe, *containerframe;

  self->private->vbox = gtk_table_new (2, 5, FALSE);
  self->private->sizegroupleft = gtk_size_group_new (GTK_SIZE_GROUP_HORIZONTAL);

  /* Name */
  namelabel = gtk_label_new ("Name :");
  gtk_misc_set_alignment (GTK_MISC(namelabel), 0.0f, 0.0f);
  gtk_size_group_add_widget (self->private->sizegroupleft, namelabel);
  gtk_table_attach (GTK_TABLE(self->private->vbox), namelabel,
		    0, 1, 0, 1, FALSE, FALSE, 5, 5);

  self->private->nameentry = gtk_entry_new();
  gtk_table_attach (GTK_TABLE(self->private->vbox), self->private->nameentry,
		    1, 2, 0, 1, GTK_EXPAND | GTK_FILL, FALSE, 5, 5);

  /* Description */
  desclabel = gtk_label_new ("Description :");
  gtk_misc_set_alignment (GTK_MISC (desclabel), 0.0f, 0.0f);
  gtk_size_group_add_widget (self->private->sizegroupleft, desclabel);
  gtk_table_attach (GTK_TABLE(self->private->vbox), desclabel,
		    0, 1, 1, 2, FALSE, GTK_EXPAND | GTK_FILL, 5, 5);
  descscroll = gtk_scrolled_window_new(NULL, NULL);
  desctagtable = gtk_text_tag_table_new();
  self->private->descentry = gtk_text_buffer_new(desctagtable);
  
  descview = gtk_text_view_new_with_buffer (self->private->descentry);
  gtk_text_view_set_right_margin  (GTK_TEXT_VIEW(descview), 3);
  gtk_text_view_set_left_margin  (GTK_TEXT_VIEW(descview), 3);
  gtk_text_view_set_wrap_mode (GTK_TEXT_VIEW(descview), GTK_WRAP_WORD);
  
  gtk_scrolled_window_set_policy ( GTK_SCROLLED_WINDOW (descscroll),
				   GTK_POLICY_AUTOMATIC, GTK_POLICY_AUTOMATIC );
  gtk_container_add (GTK_CONTAINER(descscroll), descview);
  gtk_table_attach (GTK_TABLE(self->private->vbox), descscroll,
		    1, 2, 1, 2, GTK_EXPAND | GTK_FILL , GTK_EXPAND | GTK_FILL, 5, 5);

  /* Video/Audio/Container frames */
  videoframe = pitivi_psw_make_videoframe(self);
  gtk_table_attach (GTK_TABLE(self->private->vbox), videoframe,
		    0, 2, 2, 3, GTK_EXPAND | GTK_FILL, FALSE, 5, 5);

  audioframe = pitivi_psw_make_audioframe(self);
  gtk_table_attach (GTK_TABLE(self->private->vbox), audioframe,
		    0, 2, 3, 4, GTK_EXPAND | GTK_FILL, FALSE, 5, 5);

  containerframe = pitivi_psw_make_containerframe(self);
  gtk_table_attach (GTK_TABLE(self->private->vbox), containerframe,
		    0, 2, 4, 5, GTK_EXPAND | GTK_FILL, FALSE, 5, 5);

  gtk_container_add (GTK_CONTAINER (self), self->private->vbox);
}

PitiviProjectSettingsWidget *
pitivi_projectsettingswidget_new(PitiviMainApp *mainapp)
{
  PitiviProjectSettingsWidget	*projectsettingswidget;

  projectsettingswidget = (PitiviProjectSettingsWidget *) g_object_new(PITIVI_PROJECTSETTINGSWIDGET_TYPE,
								       "mainapp", mainapp,
								       NULL);
  g_assert(projectsettingswidget != NULL);
  return projectsettingswidget;
}

PitiviProjectSettingsWidget *
pitivi_projectsettingswidget_new_with_settings (PitiviMainApp *mainapp, PitiviProjectSettings *settings)
{
  PitiviProjectSettingsWidget	*projectsettingswidget;

  projectsettingswidget = (PitiviProjectSettingsWidget *) g_object_new(PITIVI_PROJECTSETTINGSWIDGET_TYPE,
								       "mainapp", mainapp,
								       NULL);
  g_assert(projectsettingswidget != NULL);
  pitivi_projectsettingswidget_set_settings (projectsettingswidget, settings);
  return projectsettingswidget;
}

static GObject *
pitivi_projectsettingswidget_constructor (GType type,
			     guint n_construct_properties,
			     GObjectConstructParam * construct_properties)
{
  GObject *obj;
  PitiviProjectSettingsWidget	*self;
  /* Invoke parent constructor. */
  obj = parent_class->constructor (type, n_construct_properties,
				   construct_properties);

  /* do stuff. */
  self = PITIVI_PROJECTSETTINGSWIDGET (obj);
  gtk_frame_set_label (GTK_FRAME(self), "Project settings");
  pitivi_psw_make_gui(self);

  return obj;
}

static void
pitivi_projectsettingswidget_instance_init (GTypeInstance * instance, gpointer g_class)
{
  PitiviProjectSettingsWidget *self = (PitiviProjectSettingsWidget *) instance;

  self->private = g_new0(PitiviProjectSettingsWidgetPrivate, 1);
  
  /* initialize all public and private members to reasonable default values. */ 
  
  self->private->dispose_has_run = FALSE;
  
  /* Do only initialisation here */
  /* The construction of the object should be done in the Constructor
     So that properties set at instanciation can be set */
}

static void
pitivi_projectsettingswidget_dispose (GObject *object)
{
  PitiviProjectSettingsWidget	*self = PITIVI_PROJECTSETTINGSWIDGET(object);

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
pitivi_projectsettingswidget_finalize (GObject *object)
{
  PitiviProjectSettingsWidget	*self = PITIVI_PROJECTSETTINGSWIDGET(object);

  /* 
   * Here, complete object destruction. 
   * You might not need to do much... 
   */

  g_free (self->private);
  G_OBJECT_CLASS (parent_class)->finalize (object);
}

static void
pitivi_projectsettingswidget_set_property (GObject * object,
			      guint property_id,
			      const GValue * value, GParamSpec * pspec)
{
  PitiviProjectSettingsWidget *self = (PitiviProjectSettingsWidget *) object;

  switch (property_id)
    {
    case PROP_MAINAPP:
      self->private->mainapp = g_value_get_pointer (value);
      break;
    case PROP_SETTINGS:
      pitivi_projectsettingswidget_set_settings (self, PITIVI_PROJECTSETTINGS (g_value_get_pointer (value)));
      break;
    default:
      /* We don't have any other property... */
      g_assert (FALSE);
      break;
    }
}

static void
pitivi_projectsettingswidget_get_property (GObject * object,
			      guint property_id,
			      GValue * value, GParamSpec * pspec)
{
  PitiviProjectSettingsWidget *self = (PitiviProjectSettingsWidget *) object;

  switch (property_id)
    {
    case PROP_MAINAPP:
      g_value_set_pointer (value, self->private->mainapp);
      break;
    case PROP_SETTINGS:
      g_value_set_pointer (value, self->settings);
      break;
    default:
      /* We don't have any other property... */
      g_assert (FALSE);
      break;
    }
}

static void
pitivi_projectsettingswidget_class_init (gpointer g_class, gpointer g_class_data)
{
  GObjectClass *gobject_class = G_OBJECT_CLASS (g_class);
/*   PitiviProjectSettingsWidgetClass *klass = PITIVI_PROJECTSETTINGSWIDGET_CLASS (g_class); */

  parent_class = G_OBJECT_CLASS (g_type_class_peek_parent (g_class));

  gobject_class->constructor = pitivi_projectsettingswidget_constructor;
  gobject_class->dispose = pitivi_projectsettingswidget_dispose;
  gobject_class->finalize = pitivi_projectsettingswidget_finalize;

  gobject_class->set_property = pitivi_projectsettingswidget_set_property;
  gobject_class->get_property = pitivi_projectsettingswidget_get_property;

  g_object_class_install_property (gobject_class, PROP_MAINAPP,
      g_param_spec_pointer ("mainapp", "Mainapp",
			    "Pointer on the PitiviMainApp instance",
			    G_PARAM_WRITABLE | G_PARAM_CONSTRUCT_ONLY) );

  g_object_class_install_property (gobject_class, PROP_SETTINGS,
      g_param_spec_pointer ("settings", "Project Settings", 
			    "Pointer on a PitiviProjectSettings instance",
			    G_PARAM_READWRITE));
				   
}

GType
pitivi_projectsettingswidget_get_type (void)
{
  static GType type = 0;
 
  if (type == 0)
    {
      static const GTypeInfo info = {
	sizeof (PitiviProjectSettingsWidgetClass),
	NULL,			/* base_init */
	NULL,			/* base_finalize */
	pitivi_projectsettingswidget_class_init,	/* class_init */
	NULL,			/* class_finalize */
	NULL,			/* class_data */
	sizeof (PitiviProjectSettingsWidget),
	0,			/* n_preallocs */
	pitivi_projectsettingswidget_instance_init	/* instance_init */
      };
      type = g_type_register_static (GTK_TYPE_FRAME,
				     "PitiviProjectSettingsWidgetType", &info, 0);
    }

  return type;
}
