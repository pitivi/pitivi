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

#ifdef HAVE_CONFIG_H
#include <config.h>
#endif

#include <math.h>
#include "pitivi-convert-time.h"

/* static GConfClient *client = NULL; */

guint64
pitivi_timeconv_ms_to_frames (guint64 ms,
		     guint rate)
{
	float rate_ms;

	rate_ms = rate / 1000.0;
	return (guint64) (ms * rate_ms);
}

guint64
pitivi_timeconv_frames_to_ms (guint64 frames,
		     guint rate)
{
	float rate_ms;

	rate_ms = rate / 1000.0;
	return (guint64) (frames / rate_ms);
}

char *
pitivi_timeconv_ms_to_time_string (guint64 ms)
{
	int hours, mins, secs, milli;

	hours = ms / 3600000;
        ms -= (hours * 3600000);
	
        mins = ms / 60000;
        ms -= (mins * 60000);
	
        secs = ms / 1000;
        milli = ms - (secs * 1000);

        return g_strdup_printf ("%d:%02d:%02d.%03d", hours, mins, secs, milli);
}

char *
pitivi_timeconv_ms_to_pretty_time (guint64 ms)
{
	int hours, mins, secs, milli;
	char *ret, *s, *h, *m;
	
	hours = ms / 3600000;
        ms -= (hours * 3600000);
	
        mins = ms / 60000;
        ms -= (mins * 60000);
	
        secs = ms / 1000;
        milli = ms - (secs * 1000);
	/*
	if (milli == 0) {
		s = g_strdup_printf (ngettext ("%d second", "%d seconds", secs), secs);
	} else {
		s = g_strdup_printf (ngettext ("%d.%03d second", "%d.%03d seconds", milli), secs, milli);
	}
	
	m = g_strdup_printf (ngettext ("%d minute", "%d minutes", mins), mins);
	h = g_strdup_printf (ngettext ("%d hour", "%d hours", hours), hours);
	*/
	if (hours > 0) {
		if (mins > 0) {
			ret = g_strdup_printf ("%s %s %s", h, m, s);
		} else {
			ret = g_strdup_printf ("%s %s", h, s);
		}

		goto end;
	} else {
		if (mins > 0) {
			ret = g_strdup_printf ("%s %s", m, s);
		} else {
			ret = g_strdup (s);
		}
		
		goto end;
	}

	ret = NULL;
 end:
	g_free (s);
	g_free (h);
	g_free (m);
	return ret;
}

guint64
pitivi_timeconv_time_string_to_ms (const char *str)
{
	guint64 ms = (guint64) 0;
	char *point;
	int num_of_colons = 0, i;
	
	point = strrchr (str, '.');
	if (point != NULL) {
		char ms_str[4];

		ms_str[3] = 0;
		if (point[1] == 0) {
			ms_str[0] = '0';
			ms_str[1] = '0';
			ms_str[2] = '0';
		} else {
			ms_str[0] = point[1];

			if (point[2] == 0) {
				ms_str[1] = '0';
				ms_str[2] = '0';
			} else {
				ms_str[1] = point[2];

				if (point[3] == 0) {
					ms_str[2] = '0';
				} else {
					ms_str[2] = point[3];
				}
			}
		}

		ms += (guint64) atoi (ms_str);
	}

	for (i = 0; str[i]; i++) {
		if (str[i] == ':') {
			num_of_colons++;
		}
	}

	if (num_of_colons == 0) {
		int seconds;

		seconds = atoi (str);
		ms += (guint64) seconds * 1000;
		
	} else if (num_of_colons == 1) {
		int seconds, minutes;
		char *colon;

		minutes = atoi (str);
		colon = strchr (str, ':');
		seconds = atoi (colon + 1);

		ms += (guint64) ((minutes * 60000) + (seconds * 1000));
	} else {
		int seconds, minutes, hours;
		char *colon;

		hours = atoi (str);
		colon = strchr (str, ':');
		minutes = atoi (colon + 1);
		colon = strchr (colon + 1, ':');
		seconds = atoi (colon + 1);

		ms += (guint64) ((hours * 60 * 60000) + (minutes * 60000) + (seconds * 1000));
	}
		
	return ms;
}

double
pitivi_timeconv_db_to_percent (double db)
{
	return 100.0 * pow (10.0, db / 10.0);
}

int
pitivi_timeconv_gconf_get_int (const char *key)
{
	int result;
	/*
	if (client == NULL) {
		client = gconf_client_get_default ();
	}

	result = gconf_client_get_int (client, key, NULL);
	*/
	return result;
}

void
pitivi_timeconv_gconf_set_int (const char *key,
		      int value)
{
  /*if (client == NULL) {
		client = gconf_client_get_default ();
	}

	gconf_client_set_int (client, key, value, NULL);*/
}

float
pitivi_timeconv_gconf_get_float (const char *key)
{
  float result;
  /*
	if (client == NULL) {
		client = gconf_client_get_default ();
	}

	result = gconf_client_get_float (client, key, NULL);
  */
	return result;
}

void
pitivi_timeconv_gconf_set_float (const char *key,
			float value)
{
  /*if (client == NULL) {
		client = gconf_client_get_default ();
	}

	gconf_client_set_float (client, key, value, NULL);
  */
}

char *
pitivi_timeconv_gconf_get_string (const char *key)
{
	char *result;
	/*
	if (client == NULL) {
		client = gconf_client_get_default ();
	}

	result = gconf_client_get_string (client, key, NULL);
	*/
	return result;
}
