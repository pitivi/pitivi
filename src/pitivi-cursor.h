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

#ifndef PITIVI_CURSOR_H
#define PITIVI_CURSOR_H

#define CST_WIDTH 32
#define CST_HEIGHT 32
#define CST_MASK_WIDTH 32
#define CST_MASK_HEIGHT 32
#define CST_X_HOT 0
#define CST_Y_HOT 0

typedef struct _PitiviCursor PitiviCursor;

typedef enum
{
  PITIVI_CURSOR_SELECT = 1,
  PITIVI_CURSOR_CUT,
  PITIVI_CURSOR_HAND,
  PITIVI_CURSOR_HAND2,
  PITIVI_CURSOR_ZOOM,
  PITIVI_CURSOR_ZOOM_INC,
  PITIVI_CURSOR_ZOOM_DEC,
  PITIVI_CURSOR_RESIZE,
  PITIVI_CURSOR_NOALLOW,
  PITIVI_CURSOR_ALL
  
} PitiviCursorType;

struct _PitiviCursor
{
  GdkCursor	       *cursor;
  PitiviCursorType     type;
  gboolean	       is_enable;
  int		       width;
  int		       height;
  int		       hot_x;
  int		       hot_y;
};

/* Cursor Functions */
void	      load_cursor (GdkWindow *win, 
				PitiviCursor *pitivi_cursor, 
				PitiviCursorType PiCursorType);

#endif
