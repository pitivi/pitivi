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
#include "pitivi-newprojectwindow.h"

static GtkWindowClass *parent_class = NULL;

struct _PitiviNewProjectWindowPrivate
{
  /* instance private members */
  gboolean	dispose_has_run;

  GtkWidget     *hbox;
};

/*
 * forward definitions
 */

GtkTreeStore		*pitivi_tree_create();
GtkWidget		*pitivi_tree_show(GtkTreeStore *tree);
GtkWidget		*pitivi_notebook_new(GtkWidget *window);
GtkWidget		*pitivi_make_presets_hbox(GtkWidget *window, GtkWidget *presets_hbox);
GtkWidget		*pitivi_create_presets_table(GtkWidget *window);
GtkWidget		*pitivi_make_settings_table(GtkWidget *settings_table);
GtkWidget		*pitivi_make_video_frame();
GtkWidget		*pitivi_make_audio_frame();
void			pitivi_fill_hbox(GtkWidget *window, GtkWidget *hbox);

/*
 * Insert "added-value" functions here
 */

void		pitivi_fill_hbox(GtkWidget *window, GtkWidget *hbox)
{
  GtkTreeStore	*tree;
  GtkWidget	*show_tree;
  GtkWidget	*notebook;
  GtkWidget	*scroll;
  
  tree = pitivi_tree_create();
  show_tree = pitivi_tree_show(tree);
  
/* Ajout du scrolling pour la selection */
  scroll = gtk_scrolled_window_new(NULL, NULL);
  gtk_widget_set_usize (scroll, 150, -1);
  gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scroll), GTK_POLICY_AUTOMATIC, GTK_POLICY_AUTOMATIC);
  gtk_container_add(GTK_CONTAINER(scroll), show_tree);
  
  notebook = pitivi_notebook_new(window);
  
  gtk_box_pack_start (GTK_BOX (hbox ), scroll, FALSE, FALSE, 0);
  gtk_box_pack_start (GTK_BOX (hbox), notebook, TRUE, TRUE, 0);
}

GtkTreeStore	*pitivi_tree_create()
{
  GtkTreeStore	*tree;
  GtkTreeIter	pIter;
  GtkTreeIter	pIter2;

/* Nouvel arbre */ 
  tree = gtk_tree_store_new(1, G_TYPE_STRING);

/* pere 1*/
  gtk_tree_store_append(tree, &pIter, NULL);
  gtk_tree_store_set(tree, &pIter, 0, "case 1", -1);

/* fils 1*/
  gtk_tree_store_append(tree, &pIter2, &pIter);
  gtk_tree_store_set(tree, &pIter2, 0, "subcase 1", -1);

/* pere 2*/
  gtk_tree_store_append(tree, &pIter, NULL);
  gtk_tree_store_set(tree, &pIter, 0, "case 2", -1);

/* fils 2*/
  gtk_tree_store_append(tree, &pIter2, &pIter);
  gtk_tree_store_set(tree, &pIter2, 0, "subcase 1", -1);
  gtk_tree_store_append(tree, &pIter2, &pIter);
  gtk_tree_store_set(tree, &pIter2, 0, "subcase 2", -1);

/* pere 3*/
  gtk_tree_store_append(tree, &pIter, NULL);
  gtk_tree_store_set(tree, &pIter, 0, "case 3", -1);

/* fils 3*/
  gtk_tree_store_append(tree, &pIter2, &pIter);
  gtk_tree_store_set(tree, &pIter2, 0, "subcase 1", -1);
  gtk_tree_store_append(tree, &pIter2, &pIter);
  gtk_tree_store_set(tree, &pIter2, 0, "subcase 2", -1);
  gtk_tree_store_append(tree, &pIter2, &pIter);
  gtk_tree_store_set(tree, &pIter2, 0, "subcase 3", -1);

/* pere 4*/
  gtk_tree_store_append(tree, &pIter, NULL);
  gtk_tree_store_set(tree, &pIter, 0, "case 4", -1);

/* fils 4*/
  gtk_tree_store_append(tree, &pIter2, &pIter);
  gtk_tree_store_set(tree, &pIter2, 0, "subcase 1", -1);
  gtk_tree_store_append(tree, &pIter2, &pIter);
  gtk_tree_store_set(tree, &pIter2, 0, "subcase 2", -1);
  gtk_tree_store_append(tree, &pIter2, &pIter);
  gtk_tree_store_set(tree, &pIter2, 0, "subcase 3", -1);
  gtk_tree_store_append(tree, &pIter2, &pIter);
  gtk_tree_store_set(tree, &pIter2, 0, "subcasevvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv 4", -1);

  return (tree);
}

GtkWidget		*pitivi_tree_show(GtkTreeStore *tree)
{
  GtkWidget		*show_tree;
  GtkCellRenderer	*cell;
  GtkTreeViewColumn	*column;

  /* Creation de la vue */
  show_tree = gtk_tree_view_new_with_model(GTK_TREE_MODEL(tree));

  /* Creation de la premiere colonne */
  cell = gtk_cell_renderer_text_new();
  column = gtk_tree_view_column_new_with_attributes("Selection", cell, "text", 0, NULL);
  
  /* Ajout de la colonne à la vue */
  gtk_tree_view_append_column(GTK_TREE_VIEW(show_tree), column);
  
  return (show_tree);
}

GtkWidget	*pitivi_notebook_new(GtkWidget *window)
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
  presets_hbox = pitivi_make_presets_hbox(window, presets_hbox);
  settings_table = pitivi_make_settings_table(settings_table);

  /* Les deux widgets suivantes serviront a afficher le nom des deux onglets */
  presets = gtk_label_new("Presets");
  settings = gtk_label_new("Settings");

  /* On rattache les hbox presets et settings au notebook */
  gtk_notebook_append_page (GTK_NOTEBOOK (notebook), presets_hbox, presets);
  gtk_notebook_append_page (GTK_NOTEBOOK (notebook), settings_table, settings);

  return (notebook);
}

GtkWidget*
pitivi_make_presets_hbox(GtkWidget *window, GtkWidget *presets_hbox)
{
  GtkWidget	*table;
  GtkWidget	*presets_frame;
  
  presets_hbox = gtk_hbox_new (FALSE, 0);
  
  /* Ajout d'une nouvelle frame dans la box presets_hbox globale */
  presets_frame = gtk_frame_new("Reglages");
  gtk_box_pack_start (GTK_BOX (presets_hbox), presets_frame, TRUE, TRUE, 0);
  
  /* Creation et Insertion du tableau dans la frame de reglages */
  table = pitivi_create_presets_table(window);
  gtk_container_add(GTK_CONTAINER(presets_frame), table);

  return (presets_hbox);
}

GtkWidget*
pitivi_create_presets_table(GtkWidget *window)
{
  GtkTextIter		iter;
  GtkTextTagTable	*tag_table;
  gchar			*presets;
  GtkTextBuffer		*text_buffer;
  GtkWidget		*button_new;
  GtkWidget		*button_cancel;
  GtkWidget		*text_presets;
  GtkWidget		*table;			/* contient la presets et les boutons New 
						   project et Annuler */

/* Creation du champs texte de description */
/* Creation de la Tag Table */
  tag_table = gtk_text_tag_table_new();
/* Creation du buffer text */
  text_buffer = gtk_text_buffer_new(tag_table);
/* Creation du champs Text */
  presets = "Description:\nFenetre de description des reglages";
  gtk_text_buffer_get_end_iter(text_buffer, &iter);
  gtk_text_buffer_set_text (text_buffer, presets, strlen(presets));
/* gtk_text_buffer_insert_interactive(text_buffer, &iter, presets, strlen(presets), FALSE); */
  text_presets = gtk_text_view_new_with_buffer (text_buffer);
  gtk_text_view_set_editable(GTK_TEXT_VIEW(text_presets), FALSE);
  gtk_text_view_set_right_margin  (GTK_TEXT_VIEW(text_presets), 3);
  gtk_text_view_set_left_margin  (GTK_TEXT_VIEW(text_presets), 3);
  
/* Creation de la table */
  table = gtk_table_new(2, 2, FALSE);
/* Insertion des cases du Tableau */
/* Champs Texte de description du reglage selectionne */
  gtk_table_attach( GTK_TABLE(table),
		    text_presets,
		    0,2,0,1,
		    GTK_EXPAND | GTK_FILL, GTK_EXPAND | GTK_FILL,
		    1, 1);

/* Bouton Nouveau projet */
  button_new = gtk_button_new_from_stock(GTK_STOCK_NEW);
  gtk_table_attach( GTK_TABLE(table),
		    button_new,
		    0,1,1,2,
		    GTK_EXPAND, FALSE,
		    1, 1);
  
  /* Bouton Annuler projet */
  button_cancel = gtk_button_new_from_stock(GTK_STOCK_CANCEL);
  gtk_table_attach( GTK_TABLE(table),
		    button_cancel,
		    1,2,1,2,
		    GTK_EXPAND, FALSE,
		    1, 1);
  
  /* Signal emit lorsque le bouton Annuler est click& */
/*   g_signal_connect( G_OBJECT(button_cancel), "clicked", */
/* 		    G_CALLBACK(pitivi_destroy_newproject), (gpointer) (window) ); */
  
  /* Retourne la table creee */
  return (table);
}


GtkWidget*
pitivi_make_settings_table(GtkWidget *settings_table)
{
  GtkWidget	*button_hbox;
  GtkWidget	*name_label;
  GtkWidget	*name_text;
  GtkWidget	*video_frame;
  GtkWidget	*audio_frame;
  GtkWidget	*button_add;
  GtkWidget	*button_mod;
  GtkWidget	*button_del;
  GtkWidget	*desc_label;
  GtkTextTagTable	*name_tag_table;
  gchar			*name_settings;
  GtkTextBuffer		*name_text_buffer;
  GtkTextIter		name_iter;
  GtkWidget		*name_text_settings;
  GtkWidget		*name_scroll;

  settings_table = gtk_table_new (5, 2, FALSE);

  /* Ligne 1 */
  name_label = gtk_label_new("Nom :");
  gtk_table_attach (GTK_TABLE(settings_table), name_label,
		    0, 1, 0, 1, FALSE, FALSE, 30, 5);


  name_text = gtk_entry_new();
  gtk_table_attach (GTK_TABLE(settings_table), name_text, 
		    1, 2, 0, 1, GTK_EXPAND | GTK_FILL, FALSE, 50, 5);
  
  /* Ligne 2 */
  desc_label = gtk_label_new("Description :");
  gtk_table_attach (GTK_TABLE(settings_table), desc_label, 
		    0, 1, 1, 2, FALSE, FALSE, 30, 5);

  /* Creation du champs texte de description */
  /* Creation de la Tag Table */
  name_tag_table = gtk_text_tag_table_new();
  /* Creation du buffer text */
  name_text_buffer = gtk_text_buffer_new(name_tag_table);
  /* Creation du champs Text */
  name_settings = "Description:\nInserez une description de votre reglage";
  gtk_text_buffer_get_end_iter(name_text_buffer, &name_iter);
  gtk_text_buffer_set_text (name_text_buffer, name_settings, strlen(name_settings));
  name_text_settings = gtk_text_view_new_with_buffer (name_text_buffer);
  gtk_text_view_set_right_margin  (GTK_TEXT_VIEW(name_text_settings), 3);
  gtk_text_view_set_left_margin  (GTK_TEXT_VIEW(name_text_settings), 3);

  
  /* Ajout du scrolling pour le champ texte */
  name_scroll = gtk_scrolled_window_new(NULL, NULL);
  gtk_widget_set_usize (name_scroll, -1, 70);
  gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(name_scroll), GTK_POLICY_AUTOMATIC, GTK_POLICY_AUTOMATIC);
  gtk_container_add(GTK_CONTAINER(name_scroll), name_text_settings);

  gtk_table_attach (GTK_TABLE(settings_table), name_scroll, 
		    1, 2, 1, 2, GTK_EXPAND | GTK_FILL, FALSE, 50, 5);
  
/* Ligne 3 */
  video_frame = pitivi_make_video_frame();
  gtk_table_attach (GTK_TABLE(settings_table), video_frame, 
		    0, 2, 2, 3, GTK_EXPAND | GTK_FILL, FALSE , 0, 5);
  
/* Ligne 4 */
  audio_frame = pitivi_make_audio_frame();
  gtk_table_attach (GTK_TABLE(settings_table), audio_frame, 
		    0, 2, 3, 4, GTK_EXPAND | GTK_FILL, FALSE , 0, 5);
  
/* Ligne 5 */
  button_hbox = gtk_hbox_new(TRUE, 10);
  
  button_add = gtk_button_new_with_label("Add");
  gtk_box_pack_start(GTK_BOX(button_hbox), button_add, GTK_EXPAND | GTK_FILL, GTK_EXPAND | GTK_FILL, 0);

  button_mod = gtk_button_new_with_label("Modify");
  gtk_box_pack_start(GTK_BOX(button_hbox), button_mod, GTK_EXPAND | GTK_FILL, GTK_EXPAND | GTK_FILL, 0);
  
  button_del = gtk_button_new_with_label("Delete");
  gtk_box_pack_start(GTK_BOX(button_hbox), button_del, GTK_EXPAND | GTK_FILL, GTK_EXPAND | GTK_FILL, 0);
  
  gtk_table_attach(GTK_TABLE(settings_table), button_hbox, 
		   0, 2, 4, 5, GTK_EXPAND | GTK_FILL, FALSE, 140, 0);
  
  return (settings_table);
}

GtkWidget*
pitivi_make_video_frame()
{
  GtkWidget	*video_table;
  GtkWidget	*video_label_codec;
  GtkWidget	*video_label_size;
  GtkWidget	*video_label_fps;
  GtkWidget	*video_combo_codec;
  GtkWidget	*size_hbox;
  GtkWidget	*size_width;
  GtkWidget	*size_label_x;
  GtkWidget	*size_height;
  GtkWidget	*fps_text;
  GtkWidget	*video_frame;

/* Creation de la frame "video" et du tableau principal */
  video_frame = gtk_frame_new("Video");
  video_table = gtk_table_new(3, 2, FALSE);
  
/* Premier label "codecs" */
  video_label_codec = gtk_label_new("Codecs : ");
  gtk_table_attach (GTK_TABLE(video_table), video_label_codec, 
		    0, 1, 0, 1, FALSE, FALSE, 40, 5);
  
/*   Champ texte "codecs" */
  video_combo_codec = gtk_combo_box_new_text();
  gtk_combo_box_insert_text (GTK_COMBO_BOX (video_combo_codec), 0, "XviD");
  gtk_combo_box_insert_text (GTK_COMBO_BOX (video_combo_codec), 1, "MPEG-4");

/* Active le premier choix*/
  gtk_combo_box_set_active (GTK_COMBO_BOX (video_combo_codec), 0);
  gtk_table_attach (GTK_TABLE(video_table), video_combo_codec,
		    1, 2, 0, 1, GTK_EXPAND | GTK_FILL, FALSE, 140, 10);
  
/* Deuxieme label "size" */
  video_label_size = gtk_label_new("Size : ");
  gtk_table_attach (GTK_TABLE(video_table), video_label_size, 
		    0, 1, 1, 2, FALSE, FALSE, 40, 5);
  
  size_hbox = gtk_hbox_new(FALSE, 5);
/* champ texte "width" */
  size_width = gtk_entry_new();
  gtk_entry_set_width_chars (GTK_ENTRY(size_width), 5);
  gtk_box_pack_start(GTK_BOX (size_hbox), size_width, FALSE, FALSE, 0);

/* label "X" */
  size_label_x = gtk_label_new("X");
  gtk_box_pack_start(GTK_BOX (size_hbox), size_label_x, FALSE, FALSE, 0);

/* champ texte "height" */
  size_height = gtk_entry_new();
  gtk_entry_set_width_chars (GTK_ENTRY(size_height), 5);
  gtk_box_pack_start(GTK_BOX (size_hbox), size_height, FALSE, FALSE, 0);
  
  gtk_table_attach(GTK_TABLE(video_table), size_hbox, 
		   1, 2, 1, 2, FALSE, FALSE, 2, 2);
   
/*   Troisieme label "Fps" */
  video_label_fps = gtk_label_new("Fps : ");
  gtk_table_attach (GTK_TABLE(video_table), video_label_fps, 
		    0, 1, 2, 3, FALSE, FALSE, 40, 10);
  
/*   champ texte "Fps" */
  fps_text = gtk_entry_new();
  gtk_table_attach (GTK_TABLE(video_table), fps_text, 
		    1, 2, 2, 3, GTK_EXPAND | GTK_FILL, FALSE, 140, 10);
 
/*   Ajoute le tableau principale ds la frame "video" */
  gtk_container_add(GTK_CONTAINER(video_frame), video_table);

  return (video_frame);  
}

GtkWidget*
pitivi_make_audio_frame()
{
  GtkWidget	*audio_frame;
  GtkWidget	*audio_table;
  GtkWidget	*audio_label_codec;
  GtkWidget	*audio_combo_codec;
  GtkWidget	*audio_label_freq;
  GtkWidget	*audio_combo_freq;
  GtkWidget	*audio_label_ech;
  GtkWidget	*audio_combo_ech;

/* Creation de la frame "audio" et du tableau principal */
  audio_frame = gtk_frame_new("Audio"); 
  audio_table = gtk_table_new(3, 2, FALSE);
  
/* Premier label "codecs" */
  audio_label_codec = gtk_label_new("Codecs : ");
  gtk_table_attach (GTK_TABLE(audio_table), audio_label_codec, 
		    0, 1, 0, 1, FALSE, FALSE, 20, 10);
  
/*   Champ texte "codecs" */
  audio_combo_codec = gtk_combo_box_new_text();
  gtk_combo_box_insert_text (GTK_COMBO_BOX (audio_combo_codec), 0, "MPEG-layer 3");
  gtk_combo_box_insert_text (GTK_COMBO_BOX (audio_combo_codec), 1, "MIDI");
  gtk_combo_box_insert_text (GTK_COMBO_BOX (audio_combo_codec), 2, "PCM");
  gtk_combo_box_set_active(GTK_COMBO_BOX (audio_combo_codec), 0); /*  Choix par defaut */
  gtk_table_attach (GTK_TABLE(audio_table), audio_combo_codec, 
		    1, 2, 0, 1, GTK_EXPAND | GTK_FILL, FALSE, 140, 10);

/* Deuxieme label "frequence" */
  audio_label_freq = gtk_label_new("Frequence : ");
  gtk_table_attach (GTK_TABLE(audio_table), audio_label_freq, 
		    0, 1, 1, 2, FALSE, FALSE, 20, 0);

/*   Champ texte "frequence" */
  audio_combo_freq = gtk_combo_box_new_text();
  gtk_combo_box_insert_text (GTK_COMBO_BOX (audio_combo_freq), 0, "48000 Hz");
  gtk_combo_box_insert_text (GTK_COMBO_BOX (audio_combo_freq), 1, "24000 Hz");
  gtk_combo_box_insert_text (GTK_COMBO_BOX (audio_combo_freq), 2, "12000 Hz");
  gtk_combo_box_set_active(GTK_COMBO_BOX (audio_combo_freq), 0); /*  Choix par defaut */
  gtk_table_attach (GTK_TABLE(audio_table), audio_combo_freq, 
		    1, 2, 1, 2, GTK_EXPAND | GTK_FILL, FALSE, 140, 10);

 /* Troisieme label "echantillonage" */
  audio_label_ech = gtk_label_new("Echantillonage : ");
  gtk_table_attach (GTK_TABLE(audio_table), audio_label_ech, 
		    0, 1, 2, 3, FALSE, FALSE, 20, 10);
  
/*   Champ texte "echantillonage" */
  audio_combo_ech = gtk_combo_box_new_text();
  gtk_combo_box_insert_text (GTK_COMBO_BOX (audio_combo_ech), 0, "8 bits");
  gtk_combo_box_insert_text (GTK_COMBO_BOX (audio_combo_ech), 1, "16 bits");
  gtk_combo_box_insert_text (GTK_COMBO_BOX (audio_combo_ech), 2, "24 bits");
  gtk_combo_box_insert_text (GTK_COMBO_BOX (audio_combo_ech), 3, "32 bits");
  gtk_combo_box_set_active(GTK_COMBO_BOX (audio_combo_ech), 0); /*  Choix par defaut */
  gtk_table_attach (GTK_TABLE(audio_table), audio_combo_ech, 
		    1, 2, 2, 3, GTK_EXPAND | GTK_FILL, FALSE, 140, 10);

  gtk_container_add(GTK_CONTAINER(audio_frame), audio_table);
  return (audio_frame);   
}




PitiviNewProjectWindow *
pitivi_newprojectwindow_new(void)
{
  PitiviNewProjectWindow	*newprojectwindow;
  
  g_printf("pitivi_newprojectwindow_new()\n");

  newprojectwindow = (PitiviNewProjectWindow *) g_object_new(PITIVI_NEWPROJECTWINDOW_TYPE, NULL);
  g_assert(newprojectwindow != NULL);
  return newprojectwindow;
}

static GObject *
pitivi_newprojectwindow_constructor (GType type,
			     guint n_construct_properties,
			     GObjectConstructParam * construct_properties)
{
  g_printf("pitivi_newprojectwindow_constructor()\n");
  
  GObject *obj;
  {
    /* Invoke parent constructor. */
    PitiviNewProjectWindowClass *klass;
    GObjectClass *parent_class;
    klass = PITIVI_NEWPROJECTWINDOW_CLASS (g_type_class_peek (PITIVI_NEWPROJECTWINDOW_TYPE));
    parent_class = G_OBJECT_CLASS (g_type_class_peek_parent (klass));
    obj = parent_class->constructor (type, n_construct_properties,
				     construct_properties);
  }

  /* do stuff. */

  return obj;
}

static void
pitivi_newprojectwindow_instance_init (GTypeInstance * instance, gpointer g_class)
{
  PitiviNewProjectWindow *self = (PitiviNewProjectWindow *) instance;

  g_printf("pitivi_newprojectwindow_instance_init()\n");
  
  self->private = g_new0(PitiviNewProjectWindowPrivate, 1);
  
  /* initialize all public and private members to reasonable default values. */ 
  
  self->private->dispose_has_run = FALSE;
  
  /* If you need specific consruction properties to complete initialization, 
   * delay initialization completion until the property is set. 
   */
  
  /*   Creation de la fenetre de reglages d'un nouveau projet */
/*   self = gtk_window_new (GTK_WINDOW_TOPLEVEL); */
  gtk_window_set_default_size(GTK_WINDOW (self), 750, 520);
  gtk_window_set_title (GTK_WINDOW (self), "New Project");
  gtk_window_set_position (GTK_WINDOW (self), GTK_WIN_POS_CENTER);
  gtk_window_set_modal (GTK_WINDOW(self), TRUE);
  
/* Creation de hBox et Insertion dans la window du projet */
  self->private->hbox = gtk_hbox_new (FALSE, 0);
  gtk_widget_set_usize (self->private->hbox, 750, 520);
/* Creation des elements de la fenetre NewProject */
  pitivi_fill_hbox(GTK_WIDGET (self), self->private->hbox );
  gtk_container_add (GTK_CONTAINER (self), self->private->hbox);
  
  gtk_widget_show_all( GTK_WIDGET(self->private->hbox));
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

  G_OBJECT_CLASS (parent_class)->finalize (object);
  g_free (self->private);
}

static void
pitivi_newprojectwindow_set_property (GObject * object,
			      guint property_id,
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
    default:
      /* We don't have any other property... */
      g_assert (FALSE);
      break;
    }
}

static void
pitivi_newprojectwindow_get_property (GObject * object,
			      guint property_id,
			      GValue * value, GParamSpec * pspec)
{
  PitiviNewProjectWindow *self = (PitiviNewProjectWindow *) object;

  switch (property_id)
    {
      /*  case PITIVI_NEWPROJECTWINDOW_PROPERTY: { */
      /*     g_value_set_string (value, self->private->name); */
      /*   } */
      /*     break; */
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

  g_printf("pitivi_main_class_init()\n");

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

}

GType
pitivi_newprojectwindow_get_type (void)
{
  static GType type = 0;
 
  g_printf("pitivi_main_get_type()\n");
 
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
      type = g_type_register_static (GTK_TYPE_WINDOW,
				     "PitiviNewProjectWindowType", &info, 0);
    }

  return type;
}
