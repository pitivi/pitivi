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

#include "pitivi-encodewindow.h"

typedef struct _EncodePrivate {
  GtkWindow	*window;
  PitiviProject	*project;
  GtkWidget	*entry, *select;
  GtkWidget	*record, *stop, *exit;
  GtkWidget	*preview;
}		EncodePrivate;

static gboolean
window_deleted (GtkWidget *win, GdkEvent *event, EncodePrivate *priv)
{
  /* Stop and free */
  gst_element_set_state (priv->project->pipeline, GST_STATE_READY);
  PITIVI_GLOBALBIN(priv->project->bin) -> render = FALSE;
  PITIVI_GLOBALBIN(priv->project->bin) -> preview = TRUE;
  g_free (priv);

  return FALSE;
}

static void
file_select (GtkWidget *button, EncodePrivate *priv)
{
  GtkWidget	*dialog;
  gchar		*filename;

  dialog = gtk_file_chooser_dialog_new ("Select a file to record project",
					priv->window, GTK_FILE_CHOOSER_ACTION_SAVE,
					GTK_STOCK_CANCEL, GTK_RESPONSE_CANCEL,
					GTK_STOCK_SAVE, GTK_RESPONSE_ACCEPT,
					NULL);
  if (gtk_dialog_run (GTK_DIALOG (dialog)) == GTK_RESPONSE_ACCEPT) {
    filename = gtk_file_chooser_get_filename (GTK_FILE_CHOOSER (dialog));
    gtk_entry_set_text (GTK_ENTRY (priv->entry), filename);
    pitivi_project_set_file_to_encode (priv->project, filename);
  }
  gtk_widget_destroy (dialog);
}

static void
cb_preview (GtkWidget *button, EncodePrivate *priv)
{
  if (gtk_toggle_button_get_active (GTK_TOGGLE_BUTTON (button))) {
    PITIVI_GLOBALBIN(priv->project->bin) -> preview = TRUE;
  } else {
    PITIVI_GLOBALBIN(priv->project->bin) -> preview = FALSE;
  }
}

static void
cb_record (GtkWidget *button, EncodePrivate *priv)
{
  if (gtk_toggle_button_get_active (GTK_TOGGLE_BUTTON (button))) {
    gst_element_set_state (priv->project->pipeline, GST_STATE_PLAYING);
  } else {
    /* PAUSE */
    gst_element_set_state (priv->project->pipeline, GST_STATE_PAUSED);
  }
}
  
static void
cb_stop (GtkWidget *button, EncodePrivate *priv)
{
  gst_element_set_state (priv->project->pipeline, GST_STATE_READY);
}

static void
cb_exit (GtkWidget *button, EncodePrivate *priv)
{
  gtk_widget_destroy (GTK_WIDGET (priv->window));
  window_deleted (button, NULL, priv);
}

static GtkWidget *
make_file_box (GtkWindow *win, EncodePrivate *priv)
{
  GtkWidget	*fbox;
  GtkWidget	*label;

  fbox = gtk_hbox_new (FALSE, 5);

  label = gtk_label_new ("File :");
  gtk_box_pack_start (GTK_BOX (fbox), label,
		      FALSE, TRUE, 5);

  priv->entry = gtk_entry_new();
  gtk_box_pack_start (GTK_BOX (fbox), priv->entry,
		      TRUE, TRUE, 5);

  priv->select = gtk_button_new_with_label("Select");
  g_signal_connect (G_OBJECT (priv->select), "clicked",
		    G_CALLBACK (file_select), priv);
  gtk_box_pack_start (GTK_BOX (fbox), priv->select,
		      FALSE, TRUE, 5);

  return fbox;
}

static GtkWidget *
make_buttons_box (GtkWindow *win, EncodePrivate *priv)
{
  GtkWidget	*bhbox;

  bhbox = gtk_hbox_new (TRUE, 5);

  priv->record = gtk_toggle_button_new_with_label ("Record");
  g_signal_connect (G_OBJECT (priv->record), "toggled",
		    G_CALLBACK (cb_record), priv);

  priv->stop = gtk_button_new_with_label ("Stop");
  g_signal_connect (G_OBJECT (priv->stop), "clicked",
		    G_CALLBACK (cb_stop), priv);

  priv->exit = gtk_button_new_with_label ("Exit");
  g_signal_connect (G_OBJECT (priv->exit), "clicked",
		    G_CALLBACK (cb_exit), priv);

  gtk_box_pack_start (GTK_BOX (bhbox), priv->record,
		      TRUE, TRUE, 5);
  gtk_box_pack_start (GTK_BOX (bhbox), priv->stop,
		      TRUE, TRUE, 5);
  gtk_box_pack_start (GTK_BOX (bhbox), priv->exit,
		      TRUE, TRUE, 5);
  return bhbox;
}

static void
pitivi_encodewindow_make_gui (GtkWindow *win)
{
  GtkWidget	*main_vbox;
  GtkWidget	*bhbox, *fbox;
  GtkWidget	*sep;
  EncodePrivate	*priv;

  priv = g_object_get_data (G_OBJECT(win), "mydata");

  main_vbox = gtk_vbox_new(FALSE, 5);

  fbox = make_file_box (win, priv);

  gtk_box_pack_start (GTK_BOX (main_vbox),
		      fbox, TRUE, TRUE, 5);

  priv->preview = gtk_check_button_new_with_label ("Preview");
  gtk_toggle_button_set_active (GTK_TOGGLE_BUTTON (priv->preview),
				PITIVI_GLOBALBIN(priv->project->bin) -> preview);
  g_signal_connect (G_OBJECT (priv->preview), "toggled",
		    G_CALLBACK (cb_preview), priv);
  gtk_box_pack_start (GTK_BOX (main_vbox),
		      priv->preview, TRUE, TRUE, 5);

  sep = gtk_hseparator_new();
  gtk_box_pack_start (GTK_BOX (main_vbox),
		      sep, FALSE, TRUE, 0);

  bhbox = make_buttons_box (win, priv);

  gtk_box_pack_start (GTK_BOX (main_vbox),
		      bhbox, TRUE, TRUE, 5);

  gtk_container_add (GTK_CONTAINER (win), main_vbox);
}

GtkWindow *
pitivi_encodewindow_new (PitiviProject *project)
{
  GtkWindow	*win;
  EncodePrivate	*priv;

  win = (GtkWindow *) gtk_window_new (GTK_WINDOW_TOPLEVEL);
  gtk_window_set_modal (win, TRUE);
  gtk_window_set_title (win, "Encoding Project");
  gtk_window_set_policy (win, FALSE, FALSE, TRUE);
  gtk_window_set_keep_above (win, TRUE);

  priv = g_new0 (EncodePrivate, 1);
  priv->window = win;
  priv->project = project;
  g_object_set_data (G_OBJECT (win), "mydata", priv);

  g_signal_connect (G_OBJECT (win), "delete-event",
		    G_CALLBACK (window_deleted), priv);

  pitivi_encodewindow_make_gui (win);

  gst_element_set_state (priv->project->pipeline, GST_STATE_READY);
  PITIVI_GLOBALBIN(priv->project->bin) -> render = TRUE;
  
  return win;
}
