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
#include "pitivi-sourcelistwindow.h"
#include "pitivi-projectsourcelist.h"

static GtkWindowClass *parent_class = NULL;

struct _PitiviSourceListWindowPrivate
{
  /* instance private members */
  gboolean	dispose_has_run;
  PitiviProjectSourceList	*prjsrclist;
  GtkWidget	*hpaned;
  GtkWidget	*selectfile;
  GtkWidget	*treeview;
  GtkWidget	*listview;
  GtkListStore	*liststore;
  GtkTreeStore	*treestore;
  gchar		*treepath;
  gchar		*filepath;
  guint		newfile_signal_id;
};

/*
 * forward definitions
 */

void		OnNewBin(gpointer data, gint action, GtkWidget *widget);
void		OnImportFile(gpointer data, gint action, GtkWidget *widget);
void		OnImportFolder(gpointer data, gint action, GtkWidget *widget);
void		OnImportProject(void);
void		OnFind(void);
void		OnOptionProject(void);

static gint	my_popup_handler(GtkWidget *widget, GdkEvent *event);
gboolean	on_row_selected(GtkTreeView *view, GtkTreeModel *model,
				GtkTreePath *path, gboolean path_current, 
				gpointer user_data);
enum
  {
    BMP_COLUMN,
    TEXT_TREECOLUMN,
    N_TREECOLUMN
  };

enum
  {
    TEXT_LISTCOLUMN1,
    TEXT_LISTCOLUMN2,
    TEXT_LISTCOLUMN3,
    TEXT_LISTCOLUMN4,
    TEXT_LISTCOLUMN5,
    TEXT_LISTCOLUMN6,
    TEXT_LISTCOLUMN7,
    N_LISTCOLOUMN
  };

enum
  {
    FILEIMPORT_SIGNAL,
    LAST_SIGNAL
  };

static guint nbrchutier = 1;

static gint projectview_signals[LAST_SIGNAL] = {0};

static GtkItemFactoryEntry	TreePopup[] = {
  {"/New bin...", NULL, OnNewBin, 1, "<Item>", NULL},
  {"/Import", NULL, NULL, 0, "<Branch>", NULL},
  {"/Import/File", NULL, OnImportFile, 1, "<Item>", NULL},
  {"/Import/Folder", NULL, OnImportFolder, 1, "<Item>", NULL},
  {"/Import/Project", NULL, OnImportProject, 0, "<Item>", NULL},
  {"/Sep1", NULL, NULL, 0, "<Separator>"}, 
  {"/Find...", NULL, OnFind, 0, "<Item>", NULL},
  {"/Sep2", NULL, NULL, 0, "<Separator>"},
  {"/Options de la fenetre Projet...", NULL, OnOptionProject, 0, "<Item>", NULL}
};

static gint	iNbTreePopup = sizeof(TreePopup)/sizeof(TreePopup[0]);

static GtkItemFactoryEntry	ListPopup[] = {
  {"/New", NULL, NULL, 0, "<Branch>", NULL},
  {"/New/Bin...", NULL, OnNewBin, 1, "<Item>", NULL},
  {"/New/Storyboard", NULL, NULL, 0, "<Item>", NULL},
  {"/New/Sep1", NULL, NULL, 0, "<Separator>"},
  {"/New/Title", NULL, NULL, 0, "<Item>", NULL},
  {"/New/Sep2", NULL, NULL, 0, "<Separator>"},
  {"/New/Fichier off-line", NULL, NULL, 0, "<Item>", NULL},
  {"/Import", NULL, NULL, 0, "<Branch>", NULL},
  {"/Import/File", NULL, OnImportFile, 1, "<Item>", NULL},
  {"/Import/Folder", NULL, OnImportFolder, 1, "<Item>", NULL},
  {"/Import/Project", NULL, NULL, 0, "<Item>", NULL},
  {"/Sep3", NULL, NULL, 0, "<Separator>"},
  {"/Rechercher...", NULL, NULL, 0, "<Item>", NULL},
  {"/Sep4", NULL, NULL, 0, "<Separator>"},
  {"/Options de la fenetre Projet...", NULL, NULL, 0, "<Item>", NULL}
};

static gint	iNbListPopup = sizeof(ListPopup)/sizeof(ListPopup[0]);


/*
 * Insert "added-value" functions here
 */

int	get_num_of_selected_row(gchar *treepath, gint *depth)
{
  gchar	*tmp;
  gchar *tmp2;
 
 *depth = 0;
  tmp = tmp2 = treepath;
 
  while (*tmp != 0)
    {
      if (*tmp == ':')
	{
	  tmp2 = tmp;
	  tmp2++;
	  *depth++;
	}
      tmp++;
    }
 /*  g_printf("tmp2 ==> %s\n", tmp2); */
  return (atoi(tmp2));
}

void	remove_all_row_from_listview(PitiviSourceListWindow *self)
{
  gtk_list_store_clear(self->private->liststore);
}

void	show_file_in_current_bin(PitiviSourceListWindow *self)
{
  GtkTreeIter	iter;
  gchar	*name;
  gchar	*sTexte;
  gchar	*sExempleTexte;
  gchar	*info;
  gint	selected_row;
  gint	index;
  gint	depth;

  selected_row = get_num_of_selected_row(self->private->treepath, &depth);

  index = 0;
  while ((info = pitivi_projectsourcelist_get_file_info(self->private->prjsrclist, 
					 selected_row, index)) != NULL)
    {
    /*   g_printf("%s\n", info); */
      sTexte = g_malloc(12);
      sExempleTexte = g_malloc(12);

      sprintf(sTexte, "Ligne %d\0", index);
      sprintf(sExempleTexte, "exemple %d\0", index);
  
      /* Creation de la nouvelle ligne */
      gtk_list_store_append(self->private->liststore, &iter);
      
      name = strrchr(info, '/');
      name++;

      /* Mise a jour des donnees */
      gtk_list_store_set(self->private->liststore,
			 &iter, TEXT_LISTCOLUMN1, sTexte,
			 TEXT_LISTCOLUMN2, name,
			 TEXT_LISTCOLUMN3, sExempleTexte,
			 TEXT_LISTCOLUMN4, sExempleTexte,
			 TEXT_LISTCOLUMN5, sExempleTexte,
			 TEXT_LISTCOLUMN6, sExempleTexte,
			 TEXT_LISTCOLUMN7, sExempleTexte,
			 -1);
      index++;
    }
  
}

void	new_file(GtkWidget *widget, gpointer data)
{
  PitiviSourceListWindow *self = (PitiviSourceListWindow*)data;
  GtkTreeIter	pIter;
  gchar		*sTexte;
  gchar		*name;
  gchar		*sExempleTexte;
  gboolean	add;
  gint		row_selected;
  gint		depth;
  static int	i = 0;

  row_selected = 0;
  if (self->private->treepath != NULL)
    row_selected = get_num_of_selected_row(self->private->treepath, &depth);
  
  /* call pitivi_projectsourcelist_add_chutier_file */
  add = pitivi_projectsourcelist_add_file_to_bin(self->private->prjsrclist, 
						 row_selected,
						 self->private->filepath);
 
  if (add == FALSE)
    return;

  sTexte = g_malloc(12);
  sExempleTexte = g_malloc(12);

  sprintf(sTexte, "Ligne %d\0", i);
  sprintf(sExempleTexte, "exemple %d\0", i);
  
  /* Creation de la nouvelle ligne */
  gtk_list_store_append(self->private->liststore, &pIter);
  
  name = strrchr(self->private->filepath, '/');
  name++;

  /* Mise a jour des donnees */
  gtk_list_store_set(self->private->liststore,
		     &pIter, TEXT_LISTCOLUMN1, sTexte,
		     TEXT_LISTCOLUMN2, name,
		     TEXT_LISTCOLUMN3, sExempleTexte,
		     TEXT_LISTCOLUMN4, sExempleTexte,
		     TEXT_LISTCOLUMN5, sExempleTexte,
		     TEXT_LISTCOLUMN6, sExempleTexte,
		     TEXT_LISTCOLUMN7, sExempleTexte,
		     -1);
  i++;
/*   pitivi_projectsourcelist_showfile(self->private->prjsrclist, row_selected); */
}

void	new_bin(PitiviSourceListWindow *self, gchar *bin_name)
{
  GtkTreeSelection *selection;
  GdkPixbuf	*pixbufa;
  GtkTreeIter	iter;

  g_printf("insert new chutier\n");
  g_printf("== %s ==\n", bin_name);

  pitivi_projectsourcelist_new_bin(self->private->prjsrclist, bin_name);
  /* Chargement des images */
  /* pixbufa = gdk_pixbuf_new_from_stock("./info.xpm", NULL); */

  pixbufa = gtk_widget_render_icon(self->private->treeview, GTK_STOCK_OPEN, GTK_ICON_SIZE_MENU, NULL);
  /* Insertion des elements */
  
  gtk_tree_store_append(self->private->treestore, &iter, NULL);
      
  /* Creation de la nouvelle ligne */
  gtk_tree_store_set(self->private->treestore, &iter, BMP_COLUMN, pixbufa,
		     TEXT_TREECOLUMN, bin_name, -1);

  selection = gtk_tree_view_get_selection(GTK_TREE_VIEW(self->private->treeview));
  gtk_tree_selection_select_iter(selection, &iter);

  g_object_unref(pixbufa);  
}

GtkWidget	*create_menupopup(PitiviSourceListWindow *self, 
				  GtkItemFactoryEntry *pMenuItem, 
				  gint iNbMenuItem)
{
  GtkWidget		*pMenu;
  GtkItemFactory	*pItemFactory;
  GtkAccelGroup		*pAccel;

  pAccel = gtk_accel_group_new();

  /* Creation du menu */
  pItemFactory = gtk_item_factory_new(GTK_TYPE_MENU, "<menu>", NULL);
  
  /* Recuperation des elements du menu */
  gtk_item_factory_create_items(pItemFactory, iNbMenuItem, pMenuItem, self);

  /* Recuperation du widget pour l'affichage du menu */
  pMenu = gtk_item_factory_get_widget(pItemFactory, "<menu>");

  gtk_widget_show_all(pMenu);

  return pMenu;
}

GtkWidget	*create_listview(PitiviSourceListWindow *self,
				 GtkWidget *pWindow)
{
  GtkWidget		*menupopup;
  GtkWidget		*pListView;
  GtkWidget		*pScrollbar;
  GtkListStore		*pListStore;
  GtkTreeViewColumn	*pColumn;
  GtkCellRenderer      	*pCellRenderer;

  /* Creation du modele */
  self->private->liststore = gtk_list_store_new(N_LISTCOLOUMN, G_TYPE_STRING, G_TYPE_STRING, 
				  G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING, 
				  G_TYPE_STRING, G_TYPE_STRING);

  /* Creation de la vue */
  pListView = gtk_tree_view_new_with_model(GTK_TREE_MODEL(self->private->liststore));

  self->private->listview = pListView;

  /* Creation du menu popup */
  menupopup = create_menupopup(self, ListPopup, iNbListPopup);

  g_signal_connect_swapped(G_OBJECT(pListView), "button_press_event",
			   G_CALLBACK(my_popup_handler), 
			   GTK_OBJECT(menupopup));

  /* Creation de la premiere colonne */
  pCellRenderer = gtk_cell_renderer_text_new();
  pColumn = gtk_tree_view_column_new_with_attributes("Elements", pCellRenderer,
						     "text", TEXT_LISTCOLUMN1, 
						     NULL);
  
  /* Ajout de la colonne a la vue */
  gtk_tree_view_append_column(GTK_TREE_VIEW(pListView), pColumn);

  /* Creation de la deuxieme colonne */
  pCellRenderer = gtk_cell_renderer_text_new();
/*   pCellRenderer = gtk_cell_renderer_toggle_new(); */
  pColumn = gtk_tree_view_column_new_with_attributes("Nom", pCellRenderer,
						     "text", TEXT_LISTCOLUMN2,
						     NULL);
  
  /* Ajout de la colonne a la vue */
  gtk_tree_view_append_column(GTK_TREE_VIEW(pListView), pColumn);

  /* Creation de la troisieme colonne */
  pCellRenderer = gtk_cell_renderer_text_new();
  pColumn = gtk_tree_view_column_new_with_attributes("Type de media",
						     pCellRenderer,
						     "text", TEXT_LISTCOLUMN3,
						     NULL);
  
  /* Ajout de la colonne a la vue */
  gtk_tree_view_append_column(GTK_TREE_VIEW(pListView), pColumn);

  /* Creation de la quatrieme colonne */
  pCellRenderer = gtk_cell_renderer_text_new();
  pColumn = gtk_tree_view_column_new_with_attributes("Duree", pCellRenderer,
						     "text", TEXT_LISTCOLUMN4,
						     NULL);
  
  /* Ajout de la colonne a la vue */
  gtk_tree_view_append_column(GTK_TREE_VIEW(pListView), pColumn);

  /* Creation de la cinquieme colonne */
  pCellRenderer = gtk_cell_renderer_text_new();
  pColumn = gtk_tree_view_column_new_with_attributes("Info video",
						     pCellRenderer,
						     "text", TEXT_LISTCOLUMN5,
						     NULL);
  
  /* Ajout de la colonne a la vue */
  gtk_tree_view_append_column(GTK_TREE_VIEW(pListView), pColumn);

  /* Creation de la sixieme colonne */
  pCellRenderer = gtk_cell_renderer_text_new();
  pColumn = gtk_tree_view_column_new_with_attributes("Info audio",
						     pCellRenderer,
						     "text", TEXT_LISTCOLUMN6,
						     NULL);
  
  /* Ajout de la colonne a la vue */
  gtk_tree_view_append_column(GTK_TREE_VIEW(pListView), pColumn);

  /* Creation de la septieme colonne */
  pCellRenderer = gtk_cell_renderer_text_new();
  pColumn = gtk_tree_view_column_new_with_attributes("Commentaire",
						     pCellRenderer,
						     "text", TEXT_LISTCOLUMN7,
						     NULL);
  
  /* Ajout de la colonne a la vue */
  gtk_tree_view_append_column(GTK_TREE_VIEW(pListView), pColumn);

  /* Ajout de la vue a la fenetre */
  pScrollbar = gtk_scrolled_window_new(NULL, NULL);
  gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(pScrollbar),
				 GTK_POLICY_AUTOMATIC, GTK_POLICY_AUTOMATIC);
  gtk_container_add(GTK_CONTAINER(pScrollbar), pListView);
  
  return pScrollbar;
}

GtkWidget	*create_treeview(PitiviSourceListWindow *self,
				 GtkWidget *pScrollbar)
{
  GtkWidget		*pTreeView;
  GtkWidget		*menupopup;
  GtkTreeViewColumn	*pColumn;
  GtkCellRenderer	*pCellRenderer;
  GtkTreeSelection	*selection;

  /* Creation du modele */
  self->private->treestore = gtk_tree_store_new(N_TREECOLUMN, GDK_TYPE_PIXBUF, 
						G_TYPE_STRING);  

  /* Creation de la vue */
  pTreeView = gtk_tree_view_new_with_model(GTK_TREE_MODEL(self->private->treestore));

  self->private->treeview = pTreeView;

  /* Creation du menu popup */
  menupopup = create_menupopup(self, TreePopup, iNbTreePopup);

  g_signal_connect_swapped(G_OBJECT(pTreeView), "button_press_event",
			   G_CALLBACK(my_popup_handler), GTK_OBJECT(menupopup));

  selection = gtk_tree_view_get_selection(GTK_TREE_VIEW(self->private->treeview));

  gtk_tree_selection_set_select_function(selection, (GtkTreeSelectionFunc)on_row_selected, self, NULL);

  
  /* Creation de la premiere colonne */
  pCellRenderer = gtk_cell_renderer_pixbuf_new();
  pColumn = gtk_tree_view_column_new_with_attributes("Images", pCellRenderer,
						     "pixbuf", BMP_COLUMN,
						     NULL);

  /* Ajout de la colonne a la vue */
  gtk_tree_view_append_column(GTK_TREE_VIEW(pTreeView), pColumn);

  /* Creation de la deuxieme colonne */
  pCellRenderer = gtk_cell_renderer_text_new();
  pColumn = gtk_tree_view_column_new_with_attributes("Label", pCellRenderer,
						      "text", TEXT_TREECOLUMN,
						      NULL);
  
  /* Ajout de la colonne a la vue */
  gtk_tree_view_append_column(GTK_TREE_VIEW(pTreeView), pColumn);
						      
  /* Ajout de la vue a la fenetre */
  pScrollbar = gtk_scrolled_window_new(NULL, NULL);
  gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(pScrollbar),
				 GTK_POLICY_AUTOMATIC, GTK_POLICY_AUTOMATIC);
  gtk_container_add(GTK_CONTAINER(pScrollbar), pTreeView);

  return pScrollbar;
}

gboolean	on_row_selected(GtkTreeView *view, GtkTreeModel *model,
				GtkTreePath *treepath, gboolean path_current, 
				gpointer user_data)
{
  PitiviSourceListWindow *self = (PitiviSourceListWindow*)user_data;
  GtkTreeIter	iter;

  if (gtk_tree_model_get_iter(model, &iter, treepath))
    {
      gchar	*name;
      
      gtk_tree_model_get(model, &iter, TEXT_TREECOLUMN, &name, -1);
      
      if (!path_current)
	{
	  if (self->private->treepath != NULL)
	    g_free(self->private->treepath);
	  
	  self->private->treepath = gtk_tree_path_to_string(treepath);
	  g_printf("%s is selected\n", name);
	  
	  /* show all file in current bin */
	  show_file_in_current_bin(self);
	  g_free(name);
	}
       else
	 {
	   g_printf("cleanning %s\n", name);
	   remove_all_row_from_listview(self);
	 }
      
    }
  return TRUE;
}

static gint	my_popup_handler(GtkWidget *widget, GdkEvent *event)
{
  GtkMenu		*pMenu;
  GdkEventButton	*event_button;

  g_return_val_if_fail(widget != NULL, FALSE);
  g_return_val_if_fail(GTK_IS_MENU(widget), FALSE);
  g_return_val_if_fail(event != NULL, FALSE);

  /* The "widget" is the menu that was supplied when
   * g_signal_connect_swapped() was called.
   */
  pMenu = GTK_MENU(widget);

  if (event->type == GDK_BUTTON_PRESS)
    {
      event_button = (GdkEventButton *)event;
      if (event_button->button == 3)
	{ 
	  gtk_menu_popup(pMenu, NULL, NULL, NULL, NULL,
			 event_button->button, event_button->time);
	  return TRUE;
	}
    }

  return FALSE;
}


void	retrieve_path(GtkWidget *bouton, gpointer data)
{
  PitiviSourceListWindow *self = (PitiviSourceListWindow*)data;
  
  self->private->filepath = g_strdup(gtk_file_selection_get_filename(GTK_FILE_SELECTION(self->private->selectfile)));

/*   g_printf("path ==> %s\n", self->private->filepath); */

  g_signal_emit(self, self->private->newfile_signal_id,
                       0 /* details */, 
                       NULL);

  gtk_widget_destroy(self->private->selectfile);
}

void	OnNewBin(gpointer data, gint action, GtkWidget *widget)
{
  PitiviSourceListWindow *self = (PitiviSourceListWindow*)data;
  GtkWidget *dialog;
  GtkWidget *label;
  GtkWidget *entry;
  GtkWidget	*hbox;
  gchar		*stexte;
  gchar		*sname;

  dialog = gtk_dialog_new_with_buttons("New Bin", GTK_WINDOW(self),
				       GTK_DIALOG_MODAL|GTK_DIALOG_NO_SEPARATOR,
				       GTK_STOCK_OK, GTK_RESPONSE_OK,
				       GTK_STOCK_CANCEL, GTK_RESPONSE_CANCEL,
				       NULL);
  
  hbox = gtk_hbox_new(FALSE, 0);

  label = gtk_label_new("Bin Name :");

  gtk_box_pack_start(GTK_BOX(hbox), label, TRUE, FALSE, 0);
  
  entry = gtk_entry_new();

  stexte = g_malloc(12);

  sprintf(stexte, "Bin %d", nbrchutier);
  gtk_entry_set_text(GTK_ENTRY(entry), stexte);

  gtk_box_pack_start(GTK_BOX(hbox), entry, TRUE, FALSE, 0);
  
  gtk_box_pack_start(GTK_BOX(GTK_DIALOG(dialog)->vbox), hbox, TRUE, FALSE, 0);
  
  gtk_widget_show_all(GTK_DIALOG(dialog)->vbox);
  
  switch (gtk_dialog_run(GTK_DIALOG(dialog)))
    {
    case GTK_RESPONSE_OK:
      sname = g_strdup(gtk_entry_get_text(GTK_ENTRY(entry)));
      new_bin(self, sname);
      nbrchutier++;
      break;
    case GTK_RESPONSE_CANCEL:
    case GTK_RESPONSE_NONE:
    default:
      break;
    }
  gtk_widget_destroy(dialog);
  g_free(stexte);
}

void	OnImportFile(gpointer data, gint action, GtkWidget *widget)
{
  PitiviSourceListWindow	*self = (PitiviSourceListWindow*)data;

  printf("== Import File ==\n");

  self->private->selectfile = gtk_file_selection_new("Import File");

  gtk_window_set_modal(GTK_WINDOW(self->private->selectfile), TRUE);

  gtk_file_selection_complete(GTK_FILE_SELECTION(self->private->selectfile), "*.c");

  g_signal_connect(GTK_FILE_SELECTION(self->private->selectfile)->ok_button, 
		   "clicked",
		   G_CALLBACK(retrieve_path), self);

  g_signal_connect_swapped(G_OBJECT(GTK_FILE_SELECTION(self->private->selectfile)->cancel_button),
			   "clicked", G_CALLBACK(gtk_widget_destroy), 
			   self->private->selectfile);

  gtk_widget_show(self->private->selectfile);  
}

void	OnImportFolder(gpointer data, gint action, GtkWidget *widget)
{
  PitiviSourceListWindow *self = (PitiviSourceListWindow*)data;

  printf("== Import Folder ==\n");
/*       for (j = 0; j < 2; ++j) */
/* 	{ */
/* 	  sprintf(sTexte, "Repertoire %d", j); */

/* 	  /\* Creation de la nouvelle ligne enfant *\/ */
/* 	  gtk_tree_store_append(pTreeStore, &pIter2, &pIter); */
	  
/* 	  /\* Mise a jour des donnees *\/ */
/* 	  gtk_tree_store_set(pTreeStore, &pIter2, BMP_COLUMN, */
/* 			     pPixBufB, TEXT_TREECOLUMN, sTexte, -1); */
/* 	} */
}

void	OnImportProject(void)
{
  printf("== Import Project ==\n");
}

void	OnFind(void)
{
  printf("== Find ==\n");
}

void	OnOptionProject(void)
{
  printf(" == Options Project ==\n");
}

GtkWidget	*create_projectview(PitiviSourceListWindow *self)
{
  GtkWidget	*pScrollbar;
  GtkWidget	*pScrollbar2;
  GtkWidget	*pHBox;
  GtkWidget	*pHpaned;
  GtkWidget	*pVSeparator;
  GtkWidget	*pMenupopup;

  pHpaned = gtk_hpaned_new();

  pScrollbar = create_treeview(self, pScrollbar);
  pScrollbar2 = create_listview(self, pScrollbar2);
 
  g_signal_connect (G_OBJECT (self), "newfile",
                          (GCallback)new_file,
                          self);
  gtk_paned_set_position(GTK_PANED(pHpaned), 200);
  gtk_paned_pack1(GTK_PANED(pHpaned), pScrollbar, TRUE, FALSE);
  gtk_paned_pack2(GTK_PANED(pHpaned), pScrollbar2, FALSE, FALSE);
  
  return pHpaned;
}

PitiviSourceListWindow *
pitivi_sourcelistwindow_new(void)
{
  PitiviSourceListWindow	*sourcelistwindow;

  sourcelistwindow = (PitiviSourceListWindow *) g_object_new(PITIVI_SOURCELISTWINDOW_TYPE, NULL);
  g_assert(sourcelistwindow != NULL);
  return sourcelistwindow;
}

static GObject *
pitivi_sourcelistwindow_constructor (GType type,
			     guint n_construct_properties,
			     GObjectConstructParam * construct_properties)
{
  GObject *obj;
  {
    /* Invoke parent constructor. */
    PitiviSourceListWindowClass *klass;
    GObjectClass *parent_class;
    klass = PITIVI_SOURCELISTWINDOW_CLASS (g_type_class_peek (PITIVI_SOURCELISTWINDOW_TYPE));
    parent_class = G_OBJECT_CLASS (g_type_class_peek_parent (klass));
    obj = parent_class->constructor (type, n_construct_properties,
				     construct_properties);
  }

  /* do stuff. */

  return obj;
}

static void
pitivi_sourcelistwindow_instance_init (GTypeInstance * instance, gpointer g_class)
{
  PitiviSourceListWindow *self = (PitiviSourceListWindow *) instance;
  GtkWidget	*hpaned;

  self->private = g_new0(PitiviSourceListWindowPrivate, 1);
  
  /* initialize all public and private members to reasonable default values. */ 
  
  self->private->dispose_has_run = FALSE;
  
  /* If you need specific consruction properties to complete initialization, 
   * delay initialization completion until the property is set. 
   */
  self->private->newfile_signal_id = g_signal_newv("newfile",
                               G_TYPE_FROM_CLASS (g_class),
                               G_SIGNAL_RUN_LAST | G_SIGNAL_NO_RECURSE | G_SIGNAL_NO_HOOKS,
                               NULL /* class closure */,
                               NULL /* accumulator */,
                               NULL /* accu_data */,
                               g_cclosure_marshal_VOID__VOID,
                               G_TYPE_NONE /* return_type */,
                               0     /* n_params */,
                               NULL  /* param_types */);

  self->private->prjsrclist = pitivi_projectsourcelist_new();

  self->private->hpaned = create_projectview(self);
 
  gtk_window_set_default_size(GTK_WINDOW(self), 600, 200);
   
  gtk_container_add(GTK_CONTAINER(self), self->private->hpaned);
}

static void
pitivi_sourcelistwindow_dispose (GObject *object)
{
  PitiviSourceListWindow	*self = PITIVI_SOURCELISTWINDOW(object);

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
pitivi_sourcelistwindow_finalize (GObject *object)
{
  PitiviSourceListWindow	*self = PITIVI_SOURCELISTWINDOW(object);

  /* 
   * Here, complete object destruction. 
   * You might not need to do much... 
   */

  g_free (self->private);
  G_OBJECT_CLASS (parent_class)->finalize (object);
}

static void
pitivi_sourcelistwindow_set_property (GObject * object,
			      guint property_id,
			      const GValue * value, GParamSpec * pspec)
{
  PitiviSourceListWindow *self = (PitiviSourceListWindow *) object;

  switch (property_id)
    {
      /*   case PITIVI_SOURCELISTWINDOW_PROPERTY: { */
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
pitivi_sourcelistwindow_get_property (GObject * object,
			      guint property_id,
			      GValue * value, GParamSpec * pspec)
{
  PitiviSourceListWindow *self = (PitiviSourceListWindow *) object;

  switch (property_id)
    {
      /*  case PITIVI_SOURCELISTWINDOW_PROPERTY: { */
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
pitivi_sourcelistwindow_class_init (gpointer g_class, gpointer g_class_data)
{
  GObjectClass *gobject_class = G_OBJECT_CLASS (g_class);
  PitiviSourceListWindowClass *klass = PITIVI_SOURCELISTWINDOW_CLASS (g_class);

  parent_class = g_type_class_peek_parent (g_class);

  gobject_class->constructor = pitivi_sourcelistwindow_constructor;
  gobject_class->dispose = pitivi_sourcelistwindow_dispose;
  gobject_class->finalize = pitivi_sourcelistwindow_finalize;

  gobject_class->set_property = pitivi_sourcelistwindow_set_property;
  gobject_class->get_property = pitivi_sourcelistwindow_get_property;

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
pitivi_sourcelistwindow_get_type (void)
{
  static GType type = 0;
 
  if (type == 0)
    {
      static const GTypeInfo info = {
	sizeof (PitiviSourceListWindowClass),
	NULL,			/* base_init */
	NULL,			/* base_finalize */
	pitivi_sourcelistwindow_class_init,	/* class_init */
	NULL,			/* class_finalize */
	NULL,			/* class_data */
	sizeof (PitiviSourceListWindow),
	0,			/* n_preallocs */
	pitivi_sourcelistwindow_instance_init	/* instance_init */
      };
      type = g_type_register_static (GTK_TYPE_WINDOW,
				     "PitiviSourceListWindowType", &info, 0);
    }

  return type;
}
