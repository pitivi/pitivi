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

#ifndef PITIVI_TEMPLATE_H
#define PITIVI_TEMPLATE_H

/*
 * Potentially, include other headers on which this header depends.
 */

/*
 * Type macros.
 */

#define PITIVI_TEMPLATE_TYPE (pitivi_temp_late_get_type ())
#define PITIVI_TEMPLATE(obj) (G_TYPE_CHECK_INSTANCE_CAST ((obj), PITIVI_TEMPLATE_TYPE, PitiviTemplate))
#define PITIVI_TEMPLATE_CLASS(klass) (G_TYPE_CHECK_CLASS_CAST ((klass), PITIVI_TEMPLATE_TYPE, PitiviTemplateClass))
#define PITIVI_IS_TEMPLATE(obj) (G_TYPE_CHECK_TYPE ((obj), PITIVI_TEMPLATE_TYPE))
#define PITIVI_IS_TEMPLATE_CLASS(klass) (G_TYPE_CHECK_CLASS_TYPE ((klass), PITIVI_TEMPLATE_TYPE))
#define PITIVI_TEMPLATE_GET_CLASS(obj) (G_TYPE_INSTANCE_GET_CLASS ((obj), PITIVI_TEMPLATE_TYPE, PitiviTemplateClass))

typedef struct _PitiviTemplate PitiviTemplate;
typedef struct _PitiviTemplateClass PitiviTemplateClass;
typedef struct _PitiviTemplatePrivate PitiviTemplatePrivate;

struct _PitiviTemplate
{
  GObject parent;

  /* instance public members */

  /* private */
  PitiviTemplatePrivate *private;
};

struct _PitiviTemplateClass
{
  GObjectClass parent;
  /* class members */
};

/* used by PITIVI_TEMPLATE_TYPE */
GType pitivi_temp_late_get_type (void);

/*
 * Method definitions.
 */

PitiviTemplate	*pitivi_temp_late_new(void);

#endif
