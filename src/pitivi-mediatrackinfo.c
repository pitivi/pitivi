/* 
 * PiTiVi
 * Copyright (C) <2004> Guillaume Casanova <casano_g@epita.fr>
 *                      
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
#include "pitivi-mediatrackinfo.h"

static   GtkVBoxClass   *parent_class;

enum {
  PROP_0,
  PROP_LABEL,
  PROP_TRACK,
};

struct _PitiviMediaTrackInfoPrivate
{
  PitiviTimelineCellRenderer	*cell;
  GtkWidget			*arrow;
  gchar				*trackname;
  gchar				*font_desc;
  
  /* instance private members */
  gboolean			dispose_has_run;
};

/*
 * forward definitions
 */

/*
 * Insert "added-value" functions here
 */

GtkWidget *
pitivi_mediatrackinfo_new (PitiviTimelineCellRenderer *cell, gchar *label)
{
  PitiviMediaTrackInfo	*mediatrackinfo;
  
  mediatrackinfo = (PitiviMediaTrackInfo *) g_object_new(PITIVI_MEDIATRACKINFO_TYPE, 
							 "label", label,
							 "cell",  cell,
							 NULL);
  g_assert(mediatrackinfo != NULL);
  return  GTK_WIDGET ( mediatrackinfo );
}

static void
pitivi_mediatrackinfo_instance_init (GTypeInstance * instance, gpointer g_class)
{
  PitiviMediaTrackInfo *self = (PitiviMediaTrackInfo *) instance;

  self->private = g_new0(PitiviMediaTrackInfoPrivate, 1);
  
  /* initialize all public and private members to reasonable default values. */ 
  
  self->private->dispose_has_run = FALSE;
  if (!self->private->trackname)
    self->private->trackname = PITIVI_DEFAULT_MEDIA_NAME;
  self->private->font_desc = PITIVI_DEFAULT_FONT_DESC;
}

static void
pitivi_mediatrackinfo_dispose (GObject *object)
{
  PitiviMediaTrackInfo	*self = PITIVI_MEDIATRACKINFO(object);

  /* If dispose did already run, return. */
  if (self->private->dispose_has_run)
    return;
  
  /* Make sure dispose does not run twice. */
  
  self->private->dispose_has_run = TRUE;	
  G_OBJECT_CLASS (parent_class)->dispose (object);
}

static void
pitivi_mediatrackinfo_finalize (GObject *object)
{
  PitiviMediaTrackInfo	*self = PITIVI_MEDIATRACKINFO(object);
  
  g_free (self->private);
  G_OBJECT_CLASS (parent_class)->finalize (object);
}

static void
pitivi_mediatrackinfo_set_property (GObject * object,
				    guint property_id,
				    const GValue * value, GParamSpec * pspec)
{
  PitiviMediaTrackInfo *self = (PitiviMediaTrackInfo *) object;

  switch (property_id)
    {
    case PROP_TRACK:
      self->private->cell = g_value_get_pointer (value);
      break;
    case PROP_LABEL:
      self->private->trackname = g_value_dup_string (value);
      break;
    default:
      g_assert (FALSE);
      break;
    }
}

static void
pitivi_mediatrackinfo_get_property (GObject * object,
				    guint property_id,
				    GValue * value, GParamSpec * pspec)
{
  PitiviMediaTrackInfo *self = (PitiviMediaTrackInfo *) object;

  switch (property_id)
    {
    case PROP_TRACK:
      g_value_set_pointer (value, self->private->cell);
      break;
    default:
      g_assert (FALSE);
      break;
    }
}

static GObject *
pitivi_mediatrackinfo_constructor (GType type,
				   guint n_construct_properties,
				   GObjectConstructParam * construct_properties)
{
  PitiviMediaTrackInfo *self;    
  GObject   *object;
  GtkWidget *hbox;
  GtkWidget *label;
  int ch, cw = 0;
  int mh = 50;

  /* Constructor  */
  
  object = (* G_OBJECT_CLASS (parent_class)->constructor) 
    (type, n_construct_properties, construct_properties);
  
  /* PitiviMediaTrackInfo */
  
  hbox = gtk_hbox_new (FALSE, 0);
  self = (PitiviMediaTrackInfo *) object;
  
  /* Arrow */
  
  /*  self->private->arrow = gtk_expander_new (NULL);
  gtk_box_pack_start (GTK_BOX(hbox), self->private->arrow, TRUE, FALSE, 2);
  gtk_widget_set_usize (GTK_WIDGET (self->private->arrow), 5, 50);
  */
  /* label */

  label = gtk_label_new (self->private->trackname);
  pitivi_widget_changefont (label, self->private->font_desc);
  gtk_box_pack_start (GTK_BOX(hbox), label, TRUE, FALSE, 0);

  /* Packing ans sizing */
  gtk_widget_get_size_request (GTK_WIDGET (self->private->cell), &cw, &ch);
  if (ch > 0)
    mh = ch;
  gtk_widget_set_usize (GTK_WIDGET (self), MEDIA_TRACK_DEFAULT_WIDTH, mh);
  gtk_box_pack_start (GTK_BOX(self), hbox, TRUE, FALSE, 2);
  return object;
}

static void
pitivi_mediatrackinfo_class_init (gpointer g_class, gpointer g_class_data)
{
  GObjectClass *gobject_class = G_OBJECT_CLASS (g_class);
  PitiviMediaTrackInfoClass *klass = PITIVI_MEDIATRACKINFO_CLASS (g_class);
  GtkContainerClass *container_class = (GtkContainerClass*) (g_class);

  parent_class = g_type_class_peek_parent (g_class);
  gobject_class->constructor =  pitivi_mediatrackinfo_constructor; 
  gobject_class->dispose = pitivi_mediatrackinfo_dispose;
  gobject_class->finalize = pitivi_mediatrackinfo_finalize;
  gobject_class->set_property = pitivi_mediatrackinfo_set_property;
  gobject_class->get_property = pitivi_mediatrackinfo_get_property;

  g_object_class_install_property (gobject_class,
                                   PROP_LABEL,
                                   g_param_spec_string ("label",
							"label",
							"Pointer on the PitiviMainApp instance",
							PITIVI_DEFAULT_MEDIA_NAME,
							G_PARAM_WRITABLE | G_PARAM_CONSTRUCT_ONLY) );
  g_object_class_install_property (gobject_class,
                                   PROP_TRACK,
                                   g_param_spec_pointer ("cell",
							 "cell",
							 "Pointer on the PitiviTimecellRenederer instance",
							 G_PARAM_WRITABLE | G_PARAM_CONSTRUCT_ONLY) );
}

GType
pitivi_mediatrackinfo_get_type (void)
{
  static GType type = 0;
 
  if (type == 0)
    {
      static const GTypeInfo info = {
	sizeof (PitiviMediaTrackInfoClass),
	NULL,					/* base_init */
	NULL,					/* base_finalize */
	pitivi_mediatrackinfo_class_init,	/* class_init */
	NULL,					/* class_finalize */
	NULL,					/* class_data */
	sizeof (PitiviMediaTrackInfo),
	0,					/* n_preallocs */
	pitivi_mediatrackinfo_instance_init	/* instance_init */
      };
      type = g_type_register_static (GTK_TYPE_HBOX,
				     "PitiviMediaTrackInfoType", &info, 0);
    }

  return type;
}
