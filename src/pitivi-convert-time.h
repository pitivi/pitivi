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

#ifndef PITIVI_CONVERT_TIME_H
# define PITIVI_CONVERT_TIME_H

#include <glib.h>

#define PITIVI_TIMECONVDIALOG_BORDER_WIDTH 6
#define PITIVI_TIMECONVINFINITE_DB -43.1

guint64 pitivi_timeconv_ms_to_frames (guint64 ms,
			     guint rate);
guint64 pitivi_timeconv_frames_to_ms (guint64 frames,
			     guint rate);
char *pitivi_timeconv_ms_to_time_string (guint64 ms);
char *pitivi_timeconv_ms_to_pretty_time (guint64 ms);
guint64 pitivi_timeconv_time_string_to_ms (const char *str);

double pitivi_timeconv_db_to_percent (double db);

int pitivi_timeconv_gconf_get_int (const char *key);
void pitivi_timeconv_gconf_set_int (const char *key,
			   int value);
float pitivi_timeconv_gconf_get_float (const char *key);
void pitivi_timeconv_gconf_set_float (const char *key,
			     float value);
char *pitivi_timeconv_gconf_get_string (const char *key);
void pitivi_timeconv_gconf_set_string (const char *key,
			      const char *value);
/*
GConfClient *pitivi_timeconv_gconf_get_default (void);
*/

#endif /* PITIVI_CONVERT_TIME_H */
