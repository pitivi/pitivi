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
#include "pitivi-menu.h"
#include "pitivi-menu-actions.h"
#include "pitivi-stockicons.h"
#include "pitivi-timelinewindow.h"
#include "pitivi-newprojectwindow.h"
#include "pitivi-sourcelistwindow.h"

static GtkActionGroup *actions_group[EA_LAST_ACTION];
  
static void
default_action (GtkAction *action, gpointer data )
{
  gtk_main_quit ();
}

static void
pitivi_callb_menufile_new ( GtkAction *action, gpointer data )
{  
  PitiviNewProjectWindow *win_new_project;
  PitiviTimelineWindow *win_timeline;

  /* New Project window */
  win_new_project = pitivi_newprojectwindow_new();
  gtk_widget_show_all ( GTK_WIDGET (win_new_project) );
  win_timeline = pitivi_timelinewindow_new();
  gtk_widget_show_all ( GTK_WIDGET (win_timeline) );
}

static void
pitivi_callb_menufile_open ( GtkAction *action, gpointer data )
{
  PitiviSourceListWindow *srclistwin;
  
  /* Source List Window */
  srclistwin = pitivi_sourcelistwindow_new();
  gtk_widget_show_all (GTK_WIDGET (srclistwin) ); 
}

static void
pitivi_callb_menufile_save ( GtkAction *action, gpointer data )
{
  
}


static void
pitivi_callb_menufile_saveas ( GtkAction *action, gpointer data )
{
  
}


static void
pitivi_callb_menufile_copy ( GtkAction *action, gpointer data )
{
  
}

static void
pitivi_callb_menufile_revert ( GtkAction *action, gpointer data )
{
  
}


static void
pitivi_callb_menuimport_file ( GtkAction *action, gpointer data )
{
  
}

static void
pitivi_callb_menuimport_folder ( GtkAction *action, gpointer data )
{
  
}
  
static void
pitivi_callb_menuimport_project ( GtkAction *action, gpointer data )
{
  
}
 
static void
pitivi_callb_menu_pagesetup ( GtkAction *action, gpointer data )
{
  
}

static void
pitivi_callb_menu_print ( GtkAction *action, gpointer data )
{
  
}

static void pitivi_callb_menu_close ( GtkAction *action, gpointer data )
{

}

static GtkActionEntry default_entries_toplevels[] = {
  { "FileMenu", NULL, "_File" },
  { "EditMenu", NULL, "_Edit" },
  { "ClipMenu", NULL, "_Clip" },
  { "TimelineMenu", NULL, "_Timeline" },
  { "HelpMenu", NULL, "_Help" },
};
  

static GtkActionEntry default_entries_file[] = {
  { "FileNew", PITIVI_STOCK_NEW_PROJECT, "Ne_w", "<control>N", "New File", G_CALLBACK (pitivi_callb_menufile_new) },
  { "FileOpen", GTK_STOCK_OPEN, "_Open", "<control>O", "Open a file",  G_CALLBACK (pitivi_callb_menufile_open) },
  { "FileSave", GTK_STOCK_SAVE, "_Save", "<control>S", "Save a file", G_CALLBACK (pitivi_callb_menufile_save) },
  { "FileSaveAs", GTK_STOCK_SAVE_AS, "Save _As", "<control>A", "Save a file", G_CALLBACK (pitivi_callb_menufile_saveas) },
  { "FileSaveCopy", GTK_STOCK_SAVE_AS, "Save A _Copy", "<control>A", "Save a copy", G_CALLBACK (pitivi_callb_menufile_copy) },
  { "FileRevert", GTK_STOCK_CLOSE, "_Revert", "<control>R", "Revert", G_CALLBACK (pitivi_callb_menufile_revert) },
  { "FileCapture", NULL, "_Capture"},
  { "FileImport", NULL, "_Import"},
  { "FileImportFile", GTK_STOCK_NEW, "File ...", NULL, "Import File", G_CALLBACK (pitivi_callb_menuimport_file) },
  { "FileImportFolder", GTK_STOCK_OPEN, "Folder ...", NULL, "Import Folder",  G_CALLBACK (pitivi_callb_menuimport_folder) },
  { "FileImportProject", GTK_STOCK_NEW, "Project ...", NULL, "Import Project", G_CALLBACK (pitivi_callb_menuimport_project) },
  { "FileExportTimeline", NULL, "Export Timeline"},
  { "FileExportClip", NULL, "Export Clip"},
  { "FilePageSetup", GTK_STOCK_PRINT, "Page Setup ...", NULL, "Print", G_CALLBACK (pitivi_callb_menu_pagesetup) },
  { "FilePrint", GTK_STOCK_PRINT, "_Print ...", "<control>P", "Print", G_CALLBACK (pitivi_callb_menu_print) },
  { "FileClose", GTK_STOCK_CLOSE, "_Close", "<control>C", "Close a project", G_CALLBACK (pitivi_callb_menu_close) },
  { "FileExit", GTK_STOCK_QUIT, "E_xit", "<control>Q", "Exit the program", G_CALLBACK ( default_action )},
  { "FileNewProject", GTK_STOCK_NEW, "_New Project", "<control>N", "New File", G_CALLBACK (pitivi_callb_menufile_new) },
  { "FileProjectStory", GTK_STOCK_NEW, "StoryBoard", NULL, "StoryBoard", G_CALLBACK ( default_action ) },
  { "FileProjectBin", GTK_STOCK_NEW, "Bin", NULL, "Bin", G_CALLBACK ( default_action ) },
  { "FileProjectTitle", GTK_STOCK_NEW, "Title", NULL, "Title", NULL },
  { "FileProjectUC", GTK_STOCK_CONVERT, "Universal Conversion", NULL, "Universal Conversion", G_CALLBACK ( default_action ) },
  { "FileProjectBVideo", GTK_STOCK_CONVERT, "Black Video", NULL, "Black Video", G_CALLBACK ( default_action ) },
  { "FileProjectMatCol", GTK_STOCK_CONVERT, "Matte Video", NULL, "Black Video", G_CALLBACK ( default_action ) },
  { "empty", NULL, "" },
};


static GtkActionEntry recent_entry[]= {
  { "FileRecent", GTK_STOCK_OPEN, "_Open Recent File", "<control>R", "Open a recent file",  G_CALLBACK (pitivi_callb_menufile_open) },
};


static void
pitivi_callb_menuedit_undo ( GtkAction *entry, gpointer data )
{
  gtk_action_group_set_sensitive (actions_group[EA_REDO_EDIT], TRUE);
}

static void
pitivi_callb_menuedit_redo ( GtkAction *action, gpointer data )
{
  
}


static void
pitivi_callb_menuedit_cut ( GtkAction *action, gpointer data )
{
  
}

static void
pitivi_callb_menuedit_copy ( GtkAction *action, gpointer data )
{

}

static void
pitivi_callb_menuedit_paste ( GtkAction *action, gpointer data )
{
  
}

static void
pitivi_callb_menuedit_find ( GtkAction *action, gpointer data )
{

}


static void
pitivi_callb_menuedit_sets ( GtkAction *action, gpointer data )
{

}

static void
pitivi_callb_menuedit_clear ( GtkAction *action, gpointer data )
{

}

static GtkActionEntry default_entries_edit[] = {
  { "EditMenu", NULL, "_Edit" },
  { "EditCut", GTK_STOCK_CUT,  "Cut", NULL, "",  G_CALLBACK (pitivi_callb_menuedit_cut) },
  { "EditCopy", GTK_STOCK_COPY, "Copy", NULL, "",  G_CALLBACK (pitivi_callb_menuedit_copy) },
  { "EditPaste", GTK_STOCK_PASTE, "Paste", NULL, "",  G_CALLBACK (pitivi_callb_menuedit_paste) },
  { "EditClear", GTK_STOCK_CLEAR, "Clear", NULL, "",  G_CALLBACK (pitivi_callb_menuedit_clear) },
  { "EditFind", GTK_STOCK_FIND, "Find", NULL, "",  G_CALLBACK (pitivi_callb_menuedit_find) },
  { "EditPrefs", GTK_STOCK_PREFERENCES, "Preferences", NULL, "", G_CALLBACK (pitivi_callb_menuedit_sets)  },
};

static GtkActionEntry default_entries_undo[] = {
  { "EditUndo", GTK_STOCK_UNDO, "Undo", NULL, "",   G_CALLBACK (pitivi_callb_menuedit_undo) },
};


static GtkActionEntry default_entries_redo[] = {
  { "EditRedo", GTK_STOCK_REDO, "Redo", NULL, "",   G_CALLBACK (pitivi_callb_menuedit_redo) },
};

static void
pitivi_callb_menuedit_select ( GtkAction *action, gpointer data )
{

}


static void
pitivi_callb_menuedit_selectall ( GtkAction *action, gpointer data )
{

}

static void
pitivi_callb_menuedit_deselectall ( GtkAction *action, gpointer data )
{

}

static GtkActionEntry default_entries_selection[] = {
  { "EditSelect", PITIVI_STOCK_SELECTION_GROW, "Select", NULL, "",  G_CALLBACK ( pitivi_callb_menuedit_select) },
  { "EditSelectAll", PITIVI_STOCK_SELECT_ALL, "Select All", NULL, "", G_CALLBACK (pitivi_callb_menuedit_selectall) },
  { "EditDeSelectAll", PITIVI_STOCK_SELECT_NONE, "DeSelect All", NULL, "", G_CALLBACK (pitivi_callb_menuedit_deselectall) },  
};


static void
pitivi_callb_menutimeline_prev ( GtkAction *action, gpointer data )
{

}



static void
pitivi_callb_menutimeline_render ( GtkAction *action, gpointer data )
{

}


static void
pitivi_callb_menutimeline_audio ( GtkAction *action, gpointer data )
{

}

static void
pitivi_callb_menutimeline_zoomin ( GtkAction *action, gpointer data )
{

}

static void
pitivi_callb_menutimeline_zoomout ( GtkAction *action, gpointer data )
{

}

static void
pitivi_callb_menutimeline_trackaudio ( GtkAction *action, gpointer data )
{

}


static void
pitivi_callb_menutimeline_trackvideo ( GtkAction *action, gpointer data )
{

}

static void
pitivi_callb_menutimeline_trackoption ( GtkAction *action, gpointer data )
{

}

static GtkActionEntry default_entries_timeline[] = {
  { "TimeLinePreview", GTK_STOCK_EXECUTE, "Preview", NULL, "",  G_CALLBACK (pitivi_callb_menutimeline_prev) },
  { "TimeLineRenderWork", GTK_STOCK_STOP, "Render Work", NULL, "", G_CALLBACK (pitivi_callb_menutimeline_render) },
  { "TimeLineRenderAudio", GTK_STOCK_EXECUTE, "Render Audio", NULL, "", G_CALLBACK (pitivi_callb_menutimeline_audio) },
  { "TimeLineZoomIn", GTK_STOCK_ZOOM_IN, "Zoom _In", "plus", "Zoom into the image",  G_CALLBACK (pitivi_callb_menutimeline_zoomin) },
  { "TimeLineZoomOut", GTK_STOCK_ZOOM_OUT, "Zoom _Out", "minus", "Zoom away from the image", G_CALLBACK (pitivi_callb_menutimeline_zoomout) },
  { "TimeLineAddAudioTrack", GTK_STOCK_CDROM, "Add Audio Track", NULL, "Add a new Track Audio",  G_CALLBACK (pitivi_callb_menutimeline_trackaudio) },
  { "TimeLineAddVideoTrack", GTK_STOCK_ADD, "Add Video Track", NULL, "Add a new Track Video",  G_CALLBACK (pitivi_callb_menutimeline_trackvideo) },
  { "TimeLineAddOptionTrack", GTK_STOCK_PREFERENCES, "Add Option Track", NULL, "Option Track",  G_CALLBACK (pitivi_callb_menutimeline_trackoption) },
};
 

static void
pitivi_callb_menuclip_new ( GtkAction *action, gpointer data )
{

}

static GtkActionEntry default_entries_clip[] = {
  { "ClipNew", GTK_STOCK_FIND, "New", NULL, "Clip", G_CALLBACK (pitivi_callb_menuclip_new) },
};


static void
pitivi_callb_menuhelp_search ( GtkAction *action, gpointer data )
{

}

static void
pitivi_callb_menuhelp_about ( GtkAction *action, gpointer data )
{

}

static void
pitivi_callb_menuhelp_index ( GtkAction *action, gpointer data )
{

}

static void
pitivi_callb_menuhelp_contents ( GtkAction *action, gpointer data )
{

}

static GtkActionEntry default_entries_help[] = {
  { "HelpSearch", GTK_STOCK_FIND, "Search", NULL, "Help Search", G_CALLBACK (pitivi_callb_menuhelp_search) },
  { "HelpAbout", GTK_STOCK_HELP, "About", NULL, "Help About",  G_CALLBACK (pitivi_callb_menuhelp_about) },
  { "HelpIndex", GTK_STOCK_INDEX, "Index", NULL, "Help Index", G_CALLBACK (pitivi_callb_menuhelp_index) },
  { "HelpContents", GTK_STOCK_SPELL_CHECK, "Contents", NULL, "Help Contents", G_CALLBACK (pitivi_callb_menuhelp_contents) },
};


GtkActionGroup **
pitivi_menubar_configure (GtkUIManager *ui_manager, gpointer data)
{
  int	count;
  
  actions_group[EA_MENU_TOPLEVEL] = gtk_action_group_new ("MainMenuTopLevels");
  gtk_action_group_add_actions (actions_group[EA_MENU_TOPLEVEL], default_entries_toplevels, G_N_ELEMENTS (default_entries_toplevels), data);
  actions_group[EA_DEFAULT_FILE] = gtk_action_group_new ("MenuFile");
  gtk_action_group_add_actions (actions_group[EA_DEFAULT_FILE], default_entries_file, G_N_ELEMENTS (default_entries_file), data);
  actions_group[EA_MENU_EDIT] = gtk_action_group_new ("MenuEdit");
  gtk_action_group_add_actions (actions_group[EA_MENU_EDIT], default_entries_edit, G_N_ELEMENTS (default_entries_edit), data);
  actions_group[EA_SELECT_EDIT] = gtk_action_group_new ("MenuEditSelect");
  gtk_action_group_add_actions (actions_group[EA_SELECT_EDIT], default_entries_selection, G_N_ELEMENTS (default_entries_selection), data);
  actions_group[EA_RECENT_FILE] = gtk_action_group_new ("MenuFileRecent");
  gtk_action_group_add_actions (actions_group[EA_RECENT_FILE], recent_entry, G_N_ELEMENTS (recent_entry), data);
  actions_group[EA_MENU_TIMELINE] = gtk_action_group_new ("MenuTimeLine");
  gtk_action_group_add_actions (actions_group[EA_MENU_TIMELINE], default_entries_timeline, G_N_ELEMENTS (default_entries_timeline), data);
  actions_group[EA_MENU_HELP] = gtk_action_group_new ("MenuHelp");
  gtk_action_group_add_actions (actions_group[EA_MENU_HELP], default_entries_help, G_N_ELEMENTS (default_entries_help), data);
  actions_group[EA_UNDO_EDIT] = gtk_action_group_new ("EditUndo");
  gtk_action_group_add_actions (actions_group[EA_UNDO_EDIT], default_entries_undo, G_N_ELEMENTS (default_entries_undo), data);
  actions_group[EA_REDO_EDIT] = gtk_action_group_new ("EditRedo");
  gtk_action_group_add_actions (actions_group[EA_REDO_EDIT], default_entries_redo, G_N_ELEMENTS (default_entries_redo), data);

  for (count = 0; count < EA_LAST_ACTION; count++)
    if (actions_group[count])
       gtk_ui_manager_insert_action_group (ui_manager, actions_group[count], 0);
  gtk_action_group_set_sensitive (actions_group[EA_RECENT_FILE], FALSE);
  return ( actions_group );
}


static GtkAction *
pitivi_groupaction_find_action (GtkActionGroup *actions, gchar *name)
{
  GList	*glist;

  if (!name)
    return NULL;
  for (glist = gtk_action_group_list_actions (actions); glist != NULL; glist = glist->next)
    {
      GtkActionGroup *actions = glist->data;
      GtkAction *action = gtk_action_group_get_action (actions, name);
      if (action)
	return action;
    }
  return NULL;
}
