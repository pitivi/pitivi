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
#include "pitivi-progressbar.h"
#include "pitivi-mainapp.h"

static	   GtkWindowClass *parent_class = NULL;

struct _PitiviProgressBarPrivate
{
  GtkWidget     *table;
  GtkWidget	*img;
  /* instance private members */
  gboolean	activity_mode;
  gboolean	dispose_has_run;
};

/*
 * forward definitions
 */

/*
 * Insert "added-value" functions here
 */

static gboolean progress_timeout( gpointer data )
{
  PitiviProgressBar *self = (PitiviProgressBar *) data;
  gdouble new_val;
  
  g_return_val_if_fail (GTK_IS_WIDGET (self), FALSE);
  if (GTK_IS_PROGRESS_BAR (self->bar))
    {
      new_val = gtk_progress_bar_get_fraction (GTK_PROGRESS_BAR (self->bar));
      if ( new_val == 1.0 ) {
	gtk_widget_destroy (GTK_WIDGET (self));
	return FALSE;
      }
      while ( gtk_events_pending() )
	gtk_main_iteration();
      return TRUE;
    }
  return FALSE;
} 


void
pitivi_progressbar_set_info (PitiviProgressBar *self, gchar *label)
{
  gchar *utf8;

  if (GTK_IS_WIDGET (self))
    {
      utf8 = g_locale_to_utf8 (label, -1, NULL, NULL, NULL);
      gtk_label_set_text (GTK_LABEL (self->infos), utf8);
    }
  return ;
}

void
pitivi_progressbar_set_fraction (PitiviProgressBar *self, gdouble val)
{
  gchar	    *percent;
  gint	    res;
 
  if (GTK_IS_WIDGET (self))
    {
      gtk_progress_bar_set_fraction (GTK_PROGRESS_BAR (self->bar), (gdouble)val);
      res = val*100;
      percent = g_strdup_printf("%d %%", (int)res);
      gtk_progress_bar_set_text (GTK_PROGRESS_BAR (self->bar), percent);
    }
  return ;
}


PitiviProgressBar *
pitivi_progressbar_new ( void )
{
  PitiviProgressBar	*progressbar;
  
  progressbar = (PitiviProgressBar *) g_object_new(PITIVI_PROGRESSBAR_TYPE,
						   NULL);
  g_assert(progressbar != NULL);
  return progressbar;
}

static GObject *
pitivi_progressbar_constructor (GType type,
				guint n_construct_properties,
				GObjectConstructParam * construct_properties)
{
  GtkWidget *main_vbox;
  GObjectClass *parent_class;
  PitiviProgressBarClass *klass;
  
  /* Invoke parent constructor. */
  
  klass = PITIVI_PROGRESSBAR_CLASS (g_type_class_peek (PITIVI_PROGRESSBAR_TYPE));
  parent_class = G_OBJECT_CLASS (g_type_class_peek_parent (klass));
  GObject *obj = parent_class->constructor (type, n_construct_properties,
				   construct_properties);
  PitiviProgressBar *self = (PitiviProgressBar *) obj;
  
  /* window properties */
  gtk_window_set_title (GTK_WINDOW(self), "Loading");
  gtk_window_set_type_hint (GTK_WINDOW(self), GDK_WINDOW_TYPE_HINT_DIALOG);
  gtk_window_set_position (GTK_WINDOW (self), GTK_WIN_POS_CENTER);
  gtk_window_set_modal (GTK_WINDOW(self), TRUE);
  gtk_window_resize(GTK_WINDOW(self),350, 100);
  
  /* window element */
  main_vbox = gtk_vbox_new (FALSE, 0);
  gtk_container_set_border_width (GTK_CONTAINER (main_vbox), 10);
  self->bar   = gtk_progress_bar_new ();
  self->label = gtk_label_new ("Please wait ... Loading medias");
  self->infos = gtk_label_new ("");
  
  self->private->table = gtk_table_new (2, 5, FALSE);
  gtk_table_attach (GTK_TABLE (self->private->table), self->label, 0, 2, 1, 2,
		    GTK_EXPAND | GTK_FILL, GTK_EXPAND | GTK_FILL,
		    0, 5);
  gtk_table_attach (GTK_TABLE (self->private->table), self->bar, 0, 2, 2, 3,
		    GTK_EXPAND | GTK_FILL, GTK_EXPAND | GTK_FILL,
		    0, 5);
  gtk_table_attach (GTK_TABLE (self->private->table), self->infos, 0, 2, 3, 5,
		    GTK_EXPAND | GTK_FILL, GTK_EXPAND | GTK_FILL,
		    0, 5);
  gtk_box_pack_start (GTK_BOX (main_vbox), GTK_WIDGET (self->private->table), FALSE, FALSE, 0);
  gtk_container_add  (GTK_CONTAINER (self), main_vbox);
  gtk_progress_bar_set_fraction (GTK_PROGRESS_BAR (self->bar), 0.01);
  gtk_widget_show_all (GTK_WIDGET (self));
  g_timeout_add (2000, progress_timeout, self);
  return obj;
}

static void
pitivi_progressbar_instance_init (GTypeInstance * instance, gpointer g_class)
{
  PitiviProgressBar *self = (PitiviProgressBar *) instance;

  self->private = g_new0(PitiviProgressBarPrivate, 1);
  
  /* initialize all public and private members to reasonable default values. */ 
  
  self->private->dispose_has_run = FALSE;
}

static void
pitivi_progressbar_dispose (GObject *object)
{
  PitiviProgressBar	*self = PITIVI_PROGRESSBAR(object);

  /* If dispose did already run, return. */
  if (self->private->dispose_has_run)
    return;
  
  /* Make sure dispose does not run twice. */
  self->private->dispose_has_run = TRUE;	
  G_OBJECT_CLASS (parent_class)->dispose (object);
}

static void
pitivi_progressbar_finalize (GObject *object)
{
  PitiviProgressBar	*self = PITIVI_PROGRESSBAR(object);
  
  g_free (self->private);
  G_OBJECT_CLASS (parent_class)->finalize (object);
}

static gboolean
pitivi_progressbar_delete_event ( GtkWidget  *widget,
				  GdkEventAny *event )
{
  PitiviProgressBar	*self = PITIVI_PROGRESSBAR(widget);
  
  g_return_val_if_fail (GTK_IS_WIDGET (widget), FALSE);
  self->close = TRUE;
  return TRUE;
}

static void
pitivi_progressbar_class_init (gpointer g_class, gpointer g_class_data)
{
  GObjectClass *gobject_class = G_OBJECT_CLASS (g_class);
  GtkWidgetClass *widget_class = GTK_WIDGET_CLASS (g_class);
  
  parent_class = g_type_class_peek_parent (g_class);
  gobject_class->constructor = pitivi_progressbar_constructor;
  gobject_class->dispose = pitivi_progressbar_dispose;
  gobject_class->finalize = pitivi_progressbar_finalize;
  widget_class->delete_event = pitivi_progressbar_delete_event;
}

GType
pitivi_progressbar_get_type (void)
{
  static GType type = 0;
 
  if (type == 0)
    {
      static const GTypeInfo info = {
	sizeof (PitiviProgressBarClass),
	NULL,			/* base_init */
	NULL,			/* base_finalize */
	pitivi_progressbar_class_init,	/* class_init */
	NULL,			/* class_finalize */
	NULL,			/* class_data */
	sizeof (PitiviProgressBar),
	0,			/* n_preallocs */
	pitivi_progressbar_instance_init	/* instance_init */
      };
      type = g_type_register_static (PITIVI_WINDOWS_TYPE,
				     "PitiviProgressBarType", &info, 0);
    }

  return type;
}
