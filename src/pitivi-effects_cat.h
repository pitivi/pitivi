/* 
 * PiTiVi
 * Copyright (C) <2004>		 Stephan Bloch <bloch_s@epita.fr>
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

#ifndef PITIVI_EFFECTS_CAT_H
#define PITIVI_EFFECTS_CAT_H

typedef struct _PitiviTransProp
{
  gint		id_categorie;
  gchar		*name;
  gchar		*description;
  gchar		*image;
  gint		smpte_num;
}		PitiviTransProp;

typedef struct	_PitiviVAEffect
{
  gchar		*name;
  gchar		*image;
}		PitiviVAEffect;

/*
 **********************************************************
 * VIDEO / AUDIO EFFECTS				  *
 *							  *
 **********************************************************
*/

static PitiviVAEffect video_effect_tab[] =
  {	
    {"alphacolor", PITIVI_ALPHA_COLOR_EFFECT},
    {"alpha", PITIVI_ALPHA_EFFECT},
    {"videobalance", PITIVI_BALANCE_EFFECT},
    {"videobox", PITIVI_BOX_EFFECT},
    {"videocrop", PITIVI_CROP_EFFECT},
    {"deinterlace", PITIVI_DEINTERLACE_EFFECT},
    {"videoflip", PITIVI_FLIPPER_EFFECT},
    {"videodrop", PITIVI_FRAME_EFFECT},
    {"gamma", PITIVI_GAMMA_EFFECT},
    {"median", PITIVI_MEDIAN_EFFECT},
    {"videorate", PITIVI_RATE_EFFECT},
    {"videoscale", PITIVI_SCALER_EFFECT},
    {"smooth", PITIVI_SMOOTH_EFFECT}
  };

/*
 **********************************************************
 * SMTPE						  *
 *							  *
 **********************************************************
*/

typedef enum {
  PITIVI_BARWIPE,
  PITIVI_BOXWIPE,
  PITIVI_FOURBOXWIPE,
  PITIVI_BARNDOORWIPE,
  PITIVI_DIAGONALWIPE,
  PITIVI_BOWTIEWIPE,
  PITIVI_MISCDIAGONALWIPE,
  PITIVI_VEEWIPE,
  PITIVI_BARNVEEWIPE,
  PITIVI_IRISWIPE,
  PITIVI_CLOCKWIPE,
  PITIVI_PINWHEELWIPE,
  PITIVI_FANWIPE,
  PITIVI_DOUBLEFANWIPE,
  PITIVI_SINGLESWEEPWIPE, 
  PITIVI_DOUBLESWEEPWIPE,
  PITIVI_SALOONDOORWIPE,
  PITIVI_WINDSHIELDWIPE,
  PITIVI_LAST_WIPE
} PitiviSmpteEnum;

gchar* transition_cat[PITIVI_LAST_WIPE+1] = 
  {
    "BarWipe", "BoxWipe", "FourBoxWipe", "BarnDoorWipe",
    "DiagonalWipe", "BowTieWipe", "MiscDiagonalWipe",
    "VeeWipe", "BarnVeeWipe", "IrisWipe", "ClockWipe",
    "PinWheelWipe","FanWipe", "DoubleFanWipe", "SingleSweepWipe", 
    "DoubleSweepWipe", "SaloonDoorWipe", "WindshieldWipe",
    0
  };

static PitiviTransProp tab_category[] = {
  {PITIVI_BARWIPE, "LeftToRight",
   "A bar moves from left to right", PITIVI_SMPTE_1, 1},
  {PITIVI_BARWIPE, "TopToBottom",
   "A bar moves from top to bottom",PITIVI_SMPTE_2, 2},
  {PITIVI_BOXWIPE, "TopLeft",
   "A box expands from the upper-left corner to the lower-right corner",
  PITIVI_SMPTE_3, 3},
  {PITIVI_BOXWIPE, "TopRight",
   "A box expands from the upper-right corner to the lower-left corner",
  PITIVI_SMPTE_4, 4},
  {PITIVI_BOXWIPE, "BottomRight",
   "A box expands from the lower-right corner to the upper-left corner",
  PITIVI_SMPTE_5, 5},
  {PITIVI_BOXWIPE, "BottomLeft",
   "A box expands from the lower-left corner to the upper-right corner",
  PITIVI_SMPTE_6, 6},
  {PITIVI_BOXWIPE, "TopCenter",
   "A box expands from the top edge's midpoint to the bottom corners",
  PITIVI_SMPTE_23, 23},
  {PITIVI_BOXWIPE, "RightCenter",
   "A box expands from the right edge's midpoint to the left corners",
  PITIVI_SMPTE_24, 24},
  {PITIVI_BOXWIPE, "BottomCenter",
   "A box expands from the bottom edge's midpoint to the top corners",
  PITIVI_SMPTE_25, 25},
  {PITIVI_BOXWIPE, "LeftCenter",
   "A box expands from the left edge's midpoint to the right corners",
  PITIVI_SMPTE_26, 26},
  {PITIVI_FOURBOXWIPE, "CornersIn",
   "A box shape expands from each of the four corners toward the center",
  PITIVI_SMPTE_7, 7},
  {PITIVI_FOURBOXWIPE, "CornersOut",
   "A box shape expands from the center of each quadrant toward the corners of each quadrant",
  PITIVI_SMPTE_8, 8},
  {PITIVI_BARNDOORWIPE,"Vertical",
   "A central, vertical line splits and expands toward the left and right edges",
  PITIVI_SMPTE_21, 21},
  {PITIVI_BARNDOORWIPE,"Horizontal",
   "A central, horizontal line splits and expands toward the top and bottom edges",
  PITIVI_SMPTE_22, 22},
  {PITIVI_BARNDOORWIPE,"DiagonalBottomLeft",
   "A diagonal line from the lower-left to upper-right corners splits and expands toward the opposite corners",
  PITIVI_SMPTE_45, 45},
  {PITIVI_BARNDOORWIPE,"DiagonalTopLeft",
   "A diagonal line from upper-left to lower-right corners splits and expands toward the opposite corners",
  PITIVI_SMPTE_46, 46},
  {PITIVI_DIAGONALWIPE, "TopLeft",
   "A diagonal line moves from the upper-left corner to the lower-right corner",
  PITIVI_SMPTE_41, 41},
  {PITIVI_DIAGONALWIPE, "TopRight",
   "A diagonal line moves from the upper right corner to the lower-left corner",
  PITIVI_SMPTE_42, 42},
  {PITIVI_BOWTIEWIPE, "Vertical",
   "Two wedge shapes slide in from the top and bottom edges toward the center",
  PITIVI_SMPTE_43, 43},
  {PITIVI_BOWTIEWIPE, "Horizontal",
   "Two wedge shapes slide in from the left and right edges toward the center",
  PITIVI_SMPTE_44, 44},
  {PITIVI_MISCDIAGONALWIPE, "DoubleBarnDoor",
   "Four wedge shapes split from the center and retract toward the four edges",
  PITIVI_SMPTE_47, 47},
  {PITIVI_MISCDIAGONALWIPE, "DoubleDiamond",
   "A diamond connecting the four edge midpoints simultaneously contracts toward the center and expands toward the edges",
  PITIVI_SMPTE_48, 48},
  {PITIVI_VEEWIPE, "Down",
   "A wedge shape moves from top to bottom", 
  PITIVI_SMPTE_61, 61},
  {PITIVI_VEEWIPE, "Left",
   "A wedge shape moves from right to left",
  PITIVI_SMPTE_62, 62},
  {PITIVI_VEEWIPE, "Up",
   "A wedge shape moves from bottom to top",
  PITIVI_SMPTE_63, 63},
  {PITIVI_VEEWIPE, "Right",
   "A wedge shape moves from left to right",
  PITIVI_SMPTE_64, 64},
  {PITIVI_BARNVEEWIPE,"Down",
   "A \"V\" shape extending from the bottom edge's midpoint to the opposite corners contracts toward the center and expands toward the edges",
  PITIVI_SMPTE_65, 65},
  {PITIVI_BARNVEEWIPE, "Left",
   "A \"V\" shape extending from the left edge's midpoint to the opposite corners contracts toward the center and expands toward the edges",
  PITIVI_SMPTE_66, 66},
  {PITIVI_BARNVEEWIPE, "Up",
   "A \"V\" shape extending from the top edge's midpoint to the opposite corners contracts toward the center and expands toward the edges",
  PITIVI_SMPTE_67, 67},
  {PITIVI_BARNVEEWIPE, "Right",
   "A \"V\" shape extending from the right edge's midpoint to the opposite corners contracts toward the center and expands toward the edges",
  PITIVI_SMPTE_68, 68},
  {PITIVI_IRISWIPE, "Rectangle",
   "A rectangle expands from the center",
  PITIVI_SMPTE_101, 101},
  {PITIVI_IRISWIPE, "Diamond",
   "A four-sided diamond expands from the center",
  PITIVI_SMPTE_102, 102},
  {PITIVI_CLOCKWIPE," ClockwiseTwelve",
   "A radial hand sweeps clockwise from the twelve o'clock position",
  PITIVI_SMPTE_201, 201},
  {PITIVI_CLOCKWIPE," ClockwiseThree", 
   "A radial hand sweeps clockwise from the three o'clock position",
  PITIVI_SMPTE_202, 202},
  {PITIVI_CLOCKWIPE," ClockwiseSix",
   "A radial hand sweeps clockwise from the six o'clock position",
  PITIVI_SMPTE_203, 203},
  {PITIVI_CLOCKWIPE," ClockwiseNine",
   "A radial hand sweeps clockwise from the nine o'clock position",
  PITIVI_SMPTE_204, 204},
  {PITIVI_PINWHEELWIPE, "TwoBladeVertical",
   "Two radial hands sweep clockwise from the twelve and six o'clock positions",
  PITIVI_SMPTE_205, 205},
  {PITIVI_PINWHEELWIPE, "TwoBladeHorizontal",
   "Two radial hands sweep clockwise from the nine and three o'clock positions",
  PITIVI_SMPTE_206, 206},
  {PITIVI_PINWHEELWIPE, "FourBlade",
   "Four radial hands sweep clockwise",
  PITIVI_SMPTE_207, 207},
  {PITIVI_FANWIPE, "CenterTop",
   "A fan unfolds from the top edge, the fan axis at the center",
  PITIVI_SMPTE_211, 211},
  {PITIVI_FANWIPE, "CenterRight",
   "A fan unfolds from the right edge, the fan axis at the center",
  PITIVI_SMPTE_212, 212},
  {PITIVI_FANWIPE, "Top",
   "A fan unfolds from the bottom, the fan axis at the top edge's midpoint",
  PITIVI_SMPTE_231, 231},
  {PITIVI_FANWIPE, "Right",
   "A fan unfolds from the left, the fan axis at the right edge's midpoint",
  PITIVI_SMPTE_232, 232},
  {PITIVI_FANWIPE, "Bottom",
   "A fan unfolds from the top, the fan axis at the bottom edge's midpoint",
  PITIVI_SMPTE_233, 233},
  {PITIVI_FANWIPE, "Left",
   "A fan unfolds from the right, the fan axis at the left edge's midpoint", 
  PITIVI_SMPTE_234, 234},
  {PITIVI_DOUBLEFANWIPE, "FanOutVertical",
   "Two fans, their axes at the center, unfold from the top and bottom",
  PITIVI_SMPTE_213, 213},
  {PITIVI_DOUBLEFANWIPE, "FanOutHorizontal",
   "Two fans, their axes at the center, unfold from the left and right",
  PITIVI_SMPTE_214, 214},
  {PITIVI_DOUBLEFANWIPE, "FanInVertical",
   "Two fans, their axes at the top and bottom, unfold from the center",
  PITIVI_SMPTE_235, 235},
  {PITIVI_DOUBLEFANWIPE, "FanInHorizontal",
   "Two fans, their axes at the left and right, unfold from the center",
  PITIVI_SMPTE_236, 236},
  {PITIVI_SINGLESWEEPWIPE, "ClockwiseTop",
   "A radial hand sweeps clockwise from the top edge's midpoint",
  PITIVI_SMPTE_221, 221},
  {PITIVI_SINGLESWEEPWIPE, "ClockwiseRight",
   "A radial hand sweeps clockwise from the right edge's midpoint",
  PITIVI_SMPTE_222, 222},
  {PITIVI_SINGLESWEEPWIPE, "ClockwiseBottom",
   "A radial hand sweeps clockwise from the bottom edge's midpoint",
  PITIVI_SMPTE_223, 223},
  {PITIVI_SINGLESWEEPWIPE, "ClockwiseLeft",
   "A radial hand sweeps clockwise from the left edge's midpoint",
  PITIVI_SMPTE_224, 224},
  {PITIVI_SINGLESWEEPWIPE, "ClockwiseTopLeft",
   "A radial hand sweeps clockwise from the upper-left corner",
  PITIVI_SMPTE_241, 241},
  {PITIVI_SINGLESWEEPWIPE, "CounterClockwiseBottomLeft",
   "A radial hand sweeps counter-clockwise from the lower-left corner",
  PITIVI_SMPTE_242, 242},
  {PITIVI_SINGLESWEEPWIPE, "ClockwiseBottomRight",
   "A radial hand sweeps clockwise from the lower-right corner",
  PITIVI_SMPTE_243, 243},
  {PITIVI_SINGLESWEEPWIPE, "CounterClockwiseTopRight",
   "A radial hand sweeps counter-clockwise from the upper-right corner",
  PITIVI_SMPTE_244, 244},
  {PITIVI_DOUBLESWEEPWIPE, "ParallelVertical",
   "Two radial hands sweep clockwise and counter-clockwise from the top and bottom edges' midpoints",
  PITIVI_SMPTE_225, 225},
  {PITIVI_DOUBLESWEEPWIPE, "ParallelDiagonal",
   "Two radial hands sweep clockwise and counter-clockwise from the left and right edges' midpoints",
  PITIVI_SMPTE_226, 226},
  {PITIVI_DOUBLESWEEPWIPE, "OppositeVertical",
   "Two radial hands attached at the top and bottom edges' midpoints sweep from right to left",
  PITIVI_SMPTE_227, 227},
  {PITIVI_DOUBLESWEEPWIPE, "OppositeHorizontal",
   "Two radial hands attached at the left and right edges' midpoints sweep from top to bottom",
  PITIVI_SMPTE_228, 228},
  {PITIVI_DOUBLESWEEPWIPE, "ParallelDiagonalTopToLeft",
   "Two radial hands attached at the upper-left and lower-right corners sweep down and up",
  PITIVI_SMPTE_245, 245},
  {PITIVI_DOUBLESWEEPWIPE, "ParallelDiagonalBottomToLeft",
   "Two radial hands attached at the lower-left and upper-right corners sweep down and up",
  PITIVI_SMPTE_246, 246},
  {PITIVI_SALOONDOORWIPE, "Top",
   "Two radial hands attached at the upper-left and upper-right corners sweep down",
  PITIVI_SMPTE_251, 251},
  {PITIVI_SALOONDOORWIPE, "Left",
   "Two radial hands attached at the upper-left and lower-left corners sweep to the right",
  PITIVI_SMPTE_252, 252},
  {PITIVI_SALOONDOORWIPE, "Bottom",
   "Two radial hands attached at the lower-left and lower-right corners sweep up",
  PITIVI_SMPTE_253, 253},
  {PITIVI_SALOONDOORWIPE, "Right", 
   "Two radial hands attached at the upper-right and lower-right corners sweep to the left",
  PITIVI_SMPTE_254, 254},
  {PITIVI_WINDSHIELDWIPE, "Right",
   "Two radial hands attached at the midpoints of the top and bottom halves sweep from right to left",
  PITIVI_SMPTE_261, 261},
  {PITIVI_WINDSHIELDWIPE, "Up",
   "Two radial hands attached at the midpoints of the left and right halves sweep from top to bottom",
  PITIVI_SMPTE_262, 262},
  {PITIVI_WINDSHIELDWIPE, "Vertical",
   "Two sets of radial hands attached at the midpoints of the top and bottom halves sweep from top to bottom and bottom to top",
  PITIVI_SMPTE_263, 263},
  {PITIVI_WINDSHIELDWIPE, "Horizontal",
   "Two sets of radial hands attached at the midpoints of the left and right halves sweep from left to right and right to left",
  PITIVI_SMPTE_264, 264}
};

#endif /* PITIVI_EFFECTS_CAT_H */
