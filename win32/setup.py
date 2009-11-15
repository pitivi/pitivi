#!/usr/bin/env python
# PiTiVi , Non-linear video editor
#
# Copyright (c) 2009, Andoni Morales Alastruey <ylatuya@gmail.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

from distutils.core import setup
import py2exe
import os
import sys
import shutil
from optparse import OptionParser


class Deploy():

    def __init__(self, gstPath, gtkPath):
        self.gstPath = gstPath
        self.gtkPath = gtkPath
        self.setPathVariables()
        self.createDeploymentFolder()
        self.setPath()
        self.checkDependencies()
        self.deployPitivi()
        self.deployGStreamer()
        self.deployGTK()
        self.runPy2exeSetup()
        self.close()


    def close(self, message=None):
        if message is not None:
            print 'ERROR: %s' % message
            exit(1)
        else:
            exit(0)
    
    def setPathVariables(self):
        self.curr_dir = os.getcwd()
        if not self.curr_dir.endswith('win32'):
            self.close("The script must be run from 'pitivi/win32'")
        self.root_dir = os.path.abspath(os.path.join(self.curr_dir,'..'))
        self.dist_dir = os.path.join (self.root_dir, 'win32', 'dist')
        self.dist_bin_dir = os.path.join (self.dist_dir, 'bin')
        self.dist_etc_dir = os.path.join (self.dist_dir, 'etc')
        self.dist_share_dir = os.path.join (self.dist_dir, 'share')
        self.dist_share_pixmaps_dir = os.path.join (self.dist_share_dir, 'pitivi', 'pixmaps')
        self.dist_lib_dir = os.path.join (self.dist_dir, 'lib')
        self.dist_lib_pitivi_dir = os.path.join (self.dist_lib_dir, 'pitivi')

    def setPath(self):
        # Add root folder to the python path for pitivi
        sys.path.insert(0, self.root_dir)
        # Add site-pacakes folrder for goocanvas
        sys.path.insert(0, os.path.join(self.curr_dir, 'site-packages'))
        # Add Gtk and GStreamer folder to the system path
        for folder in [self.gstPath, self.gtkPath]:
            os.environ['PATH'] = os.environ['PATH']+';'+os.path.join(folder, 'bin')
        # FIXME: libgoocanvas links to libxml2.dll while the GStreamer installer
        # provides libxml2-2.dll
        shutil.copy(os.path.join(self.gstPath, 'bin',  'libxml2-2.dll'),
            os.path.join(self.dist_bin_dir, 'libxml2.dll'))
        os.environ['PATH'] = os.environ['PATH']+';'+self.dist_bin_dir
        
    def createDeploymentFolder(self):
        # Create a Unix-like diretory tree to deploy PiTiVi
        print ('Create deployment directory')
        if os.path.exists(self.dist_dir):
            try:
                shutil.rmtree(self.dist_dir)
            except :
                self.close("ERROR: Can't delete folder %s"%self.dist_dir)

        for path in [self.dist_dir, self.dist_bin_dir, self.dist_etc_dir, 
                self.dist_share_dir, self.dist_lib_pitivi_dir, 
                self.dist_share_pixmaps_dir]:
                os.makedirs(path)
         
    def checkDependencies(self):
        print ('Checking dependencies')
        try:
            import pygst
            pygst.require('0.10')
            import gst
        except ImportError:
            self.close('IMPORT_ERROR: Could not found the GStreamer Pythonbindings.\n'
                'You can download the installers at:\n'
                'http://www.gstreamer-winbuild.ylatuya.es')
        else:
            print ('GStreamer... OK')
     
        try:
            import pygtk
            pygtk.require('2.0')
            import gtk
            import gtk.gdk
            import gobject
        except ImportError:
                self.close('IMPORT_ERROR: Could not find the Gtk Python bindings.\n'
                    'You can download the installers at:\n'
                    'http://www.pygtk.org/\n'
                    'http://www.gtk.org/')
        else:
            print ('Gtk... OK')

        try:
            import gtk.glade
        except ImportError:
            self.close('IMPORT_ERROR: Could not find libglade in the system.\n'
                    'You can download the installers at:\n'
                    'http://sourceforge.net/projects/gladewin32/files/libglade-win32'
                    '/2.4.0/libglade-2.4.0-bin.zip/download')
        else:
            print ('libglade... OK')

        try:
            import goocanvas
        except ImportError:
            self.close('IMPORT_ERROR: Could not find the Goocanvas Python bindings.\n'
                    'You can download the intallers at:\n'
                    'http://ftp.gnome.org/pub/GNOME/binaries/win32/goocanvas/\n'
                    'http://sqlkit.argolinux.org/download/goocanvas.pyd')
        else:
            print ('goocanvas... OK')

        try:
            import zope.interface
        except:
            self.close('ERROR: Could not found Zope.Interface')
        else:
            print ('zope.interface... OK')


    def deployPitivi(self):
        print('Deploying PiTiVi')
        # Copy files autogenerated using autotools
        shutil.copy (os.path.join(self.curr_dir, 'configure.py'),
            os.path.join(self.root_dir, 'pitivi'))
        # Copy ui files to lib/pitivi
        ui_dir = os.path.join(self.root_dir, 'pitivi', 'ui')
        shutil.copy (os.path.join(ui_dir, 'mainwindow.xml'), 
            os.path.join(self.dist_lib_pitivi_dir, 'mainwindow.xml'))
        for name in [x for x in os.listdir(ui_dir) if x.endswith('glade')]:
            shutil.copy (os.path.join(ui_dir, name),
                    os.path.join(self.dist_lib_pitivi_dir, name))
        # Copy the pixmaps to the dist dir
        pitivi_pixmaps_dir = os.path.join(self.root_dir, 'pitivi', 'pixmaps')
        win32_pixmaps_dir = os.path.join(self.curr_dir, 'pixmaps')
        for name in os.listdir(pitivi_pixmaps_dir):
            shutil.copy (os.path.join(pitivi_pixmaps_dir,name),
                    self.dist_share_pixmaps_dir)
        # Override SVG pixmaps with PNG pixmaps using the .svg extension
        # so they can be loaded if gdk doesn't support svg
        for name in os.listdir(win32_pixmaps_dir):
            out_name = name.replace('.png', '.svg')
            shutil.copy (os.path.join(win32_pixmaps_dir, name),
                  os.path.join(self.dist_share_pixmaps_dir, out_name))
    
    def deployGStreamer(self):
        print ('Deploying GStreamer')
        # Copy gstreamer binaries to the dist folder
        for name in os.listdir(os.path.join(self.gstPath, 'bin')):
            shutil.copy (os.path.join(self.gstPath, 'bin', name), 
                    self.dist_bin_dir)
        shutil.copytree(os.path.join(self.gstPath, 'lib', 'gstreamer-0.10'),
             os.path.join(self.dist_lib_dir, 'gstreamer-0.10'))
    
    def deployGTK(self):
        print ('Deploying Gtk dependencies')
        # Copy Gtk files to the dist folder
        for name in ['fonts', 'pango', 'gtk-2.0']:
            shutil.copytree(os.path.join(self.gtkPath, 'etc', name),
                     os.path.join(self.dist_etc_dir, name))
        shutil.copytree(os.path.join(self.gtkPath, 'lib', 'gtk-2.0'),
            os.path.join(self.dist_lib_dir, name))

    def runPy2exeSetup(self):
        sys.argv.insert(1, 'py2exe')
        setup(
            name = 'PiTiVi',
            description = 'Non-Linear Video Editor',
            version = '0.13.4',

            windows = [
                        {
                           'script': 'pitivi',
                           'icon_resources': [(1, "pitivi.ico")],
                        }
                    ],

            options = {
                        'py2exe': {
                              'packages':'pitivi',
                              'includes': 'gtk, cairo, pango, atk, pangocairo,\
                                      zope.interface, gobject, gst, email',
                              'dist_dir' : self.dist_bin_dir  
                        }
                    },
                          
            zipfile = None,
        )

    
def main():
    usage = "usage: %prog [options]"
    parser = OptionParser(usage)
    parser.add_option("-g", "--gst-path", action="store",
            dest="gstPath",default="c:\\gstreamer", type="string",
            help="GStreamer installation path")
    parser.add_option("-k", "--gtk-path", action="store",
            dest="gtkPath",default="c:\\gtk", type="string",
            help="GTK+ installation path")

    (options, args) = parser.parse_args()
    Deploy(options.gstPath, options.gtkPath)
    
if __name__ == "__main__":
    main()


