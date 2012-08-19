#!/usr/bin/env python2
# -*- coding: UTF-8 -*-
#
# suim.py
#
# (c) Copyright 2010-2011 Michael Towers (larch42 at googlemail dot com)
#
# This file is part of the larch project.
#
#    larch is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    larch is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with larch; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
#----------------------------------------------------------------------------
# 2011.02.01

#++++++++++++++++++++++++++++++++++++++++++++++++++++
#TODO
# Add more widgets
# Add more attribute handling
# Add more signal handling

# Fetching of image and icon files via a sort of url-like mechanism, I
# suppose initially using the 'base:' prefix might be ok.
# Then the cwd of the gui script would be irrelevant.

#New file dialog for accessing the 'server' end.

# I suspect the DialogButtonBox stuff needs changing to cope with
# translations.

#----------------------------------------------------


"""SUIM - Simple User Interface Module

The aim is to provide a means of creating graphical user interfaces of
moderate complexity while abstracting the interface to the actual underlying
toolkit in such a way that (at least potentially) an alternative toolkit
could be used.
[At present this aspect is rather theoretical since only a pyqt based
version has been written.]

The gui layout is specified as a python data structure, using widget types,
parameter and signal names independent of the underlying toolkit. All
widgets are accessible by their tag, which must be specified.

A widget is defined by a call to the 'widget' method of the GuiApp instance.
The first argument is the widget type, the second is the widget tag, the
remaining ones must be named, they form the parameters to the constructor.
If the widget is a 'container' (i.e. if it contains other widgets), it will
need a 'layout' parameter defining the layout of its contents.

There is also a 'widgetlist' method which accepts a list of widget
definitions, each definition being itself a list. The first entry in a
definition is the widget type, the second is the widget tag, the
third is a dictionary containing all the parameters. For convenience (I'm not
sure if I will keep this, though) any entries after the dictionary will be
treated as signal names. These are just added to the parameter dictionary
with value '' (enabling the signal with its default tag).

Signals have signatures/keys comprising the tag of the emitting widget and
the signal name (separated by '*'), and this will by default also be the tag
by which the signal is known for connection purposes. But this can be
overridden, for example to allow several widgets to emit the same signal.
In the latter case the widget tag can (optionally) be passed as the first
argument to the signal handler.

Passing signal names as parameters to a widget constructor enables these
signals. They can later be disabled, if desired.

Connect and disconnect methods are available, to associate (or dissociate)
handler functions with (/from) signals.
"""

import os, sys, traceback, threading
from PyQt4 import QtGui, QtCore, QtWebKit
from collections import deque


def debug(text):
    sys.stderr.write("GUI: %s\n" % text)
    sys.stderr.flush()

# Either I need to wrap all text input with this or I need to ensure that
# I get unicode from outside ...
import locale
encoding = locale.getdefaultlocale()[1]
def convert(text):
    """Try to handle encoding.
    """
    if isinstance(text, str):
        return text.decode(encoding) if encoding else text.decode()
    else:
        return text


# Widget Base Classes - essentially used as 'Mixins' >>>>>>>>>>>>>>>>
class WBase:
    def x__tt(self, text):
        """Set tooltip.
        """
        self.setToolTip(text)                               #qt

    def x__text(self, text=""):
        """Set widget text.
        """
        self.setText(convert(text))                         #qt

    def x__enable(self, on):
        """Enable/Disable widget. on should be True to enable the widget
        (display it in its normal, active state), False to disable it
        (which will normally be paler and non-interactive).
        """
        self.setEnabled(on)                                 #qt

    def x__focus(self):
        self.setFocus()                                     #qt

    def x__width(self, w):
        """Set the minimum width for the widget.
        """
        self.setMinimumWidth(w)                             #qt

    def x__typewriter(self, on):
        """Use a typewriter (fixed spacing) font.
        """
        if on:
            f = QtGui.QFont(self.font())                    #qt
            f.setFamily("Courier")                          #qt
            self.setFont(f)                                 #qt

    def x__busycursor(self, on):
        """Set/clear the busy-cursor for this widget.
        """
        if on:
            self.setCursor(QtCore.Qt.BusyCursor)            #qt
        else:
            self.unsetCursor()                              #qt


class BBase:
    """Button mixin.
    """
    def x__icon(self, icon):
        self.setIcon(self.style().standardIcon(icondict[icon])) #qt

#qt
icondict = {    "left"      : QtGui.QStyle.SP_ArrowLeft,
                "right"     : QtGui.QStyle.SP_ArrowRight,
                "down"      : QtGui.QStyle.SP_ArrowDown,
                "up"        : QtGui.QStyle.SP_ArrowUp,
                "reload"    : QtGui.QStyle.SP_BrowserReload,
                "critical"  : QtGui.QStyle.SP_MessageBoxCritical,
                "apply"     : QtGui.QStyle.SP_DialogApplyButton,
                "close"     : QtGui.QStyle.SP_DialogCloseButton,
                "cancel"    : QtGui.QStyle.SP_DialogCancelButton,
        }

class Container:
    """This just adds layout management for widgets which contain
    other widgets.
    """
    def x__layout(self, layout, immediate=False):
        """A layout specifies and organizes the contents of a widget.
        Note that the layouting is not immediately performed by default as
        it is unlikely that all the contained widgets have been defined yet.
        """
        self._layout = layout
        if immediate:
            self.x__pack()

    def x__pack(self):
        """A layout call specifies and organizes the contents of a widget.
        The layout can be a layout manager list, or a single widget name
        (or an empty string, which will cause a warning to be issued, but
        may be useful during development).

        There are three sorts of thing which can appear in layout manager
        lists (apart from the layout type at the head of the list and an
        optional attribute dict as second item). There can be named
        widgets, there can be further layout managers (specified as lists,
        nested as deeply as you like) and there can be layout widgets,
        like spacers and separators.

        A layout widget can have optional arguments, which are separated
        by commas, e.g. 'VLINE,3' passes the argument '3' to the VLINE
        constructor.
        """
        # getattr avoids having to have an __init__() for Container.
        if getattr(self, '_layout', None):
            if self._layout != '$':
                self.setLayout(self.getlayout(self._layout))
                self._layout = '$'
        else:
            debug("No layout set on '%s'" % self.w_name)

    def getlayout(self, item):
        if isinstance(item, list):
            try:
                # Create a layout manager instance
                layoutmanager = layout_table[item[0]]()
                assert isinstance(layoutmanager, Layout)
            except:
                gui_error("Unknown layout type: %s" % item[0])
            if (len(item) > 1) and isinstance(item[1], dict):
                dictarg = item[1]
                ilist = item[2:]
            else:
                dictarg = {}
                ilist = item[1:]
            # Build up the list of objects to lay out
            # If the layout manager is a GRID, accept only grid rows ('+')
            if isinstance(layoutmanager, GRID):
                args = []
                rowlen = None
                for i in ilist:
                    if isinstance(i, list) and (i[0] == '+'):
                        args.append(self.getlayoutlist(i[1:], grid=True))
                        if rowlen == None:
                            rowlen = len(i)
                        elif len(i) != rowlen:
                            gui_error("Grid (%s) row lengths unequal"
                                    % self.w_name)
                    else:
                        gui_error("Grid (%s) layouts must consist of grid"
                                " rows ('+')" % self.w_name)
            else:
                # Otherwise the elements of the argument list can be:
                #   A sub-layout
                #   A widget
                #   A SPACE
                args = self.getlayoutlist(ilist)
            layoutmanager.do_layout(args)
            # Attributes
            for key, val in dictarg:
                handler = "x__" + key
                if hasattr(layoutmanager, handler):
                    getattr(layoutmanager, handler)(val)
            return layoutmanager

        else:
            # It must be a widget, which will need to be put in a box (qt)
            return self.getlayout(['VBOX', item])

    def getlayoutlist(self, items, grid=False):
        objects = []
        for i in items:
            if isinstance(i, list):
                obj = self.getlayout(i)
            else:
                parts = i.split(',')
                i = parts[0]
                args = parts[1:]
                try:
                    obj = layout_table[i](*args)
                    if not (isinstance(obj, SPACE)  # or a separator line
                            or isinstance(obj, QtGui.QWidget)): #qt
                        assert (grid and isinstance(obj, Span))
                except:
                    obj = guiapp.getwidget(i)
                    if obj != None:
                        if isinstance(obj, Container):
                            obj.x__pack()
                    else:
                        gui_error("Bad item in layout of '%s': '%s'"
                                % (self.w_name, i))
            objects.append(obj)
        return objects


class XContainer(Container):
    """This is a mixin class for containers which can contain more than
    one layout.
    """
    def x__layout(self, layout):
        gui_error("An extended container (%s) has no 'layout' method"
                % self.w_name)


class TopLevel(Container):
    def x__show(self):
        self.set_visible()

    def set_visible(self, on=True):
        self.setVisible(on)                                 #qt

    def x__size(self, w_h):
        w, h = [int(i) for i in w_h.split("_")]
        self.resize(w, h)                                   #qt

    def x__icon(self, iconpath):
        guiapp.setWindowIcon(QtGui.QIcon(iconpath))         #qt

    def x__title(self, text):
        if text == None:
            text = guiapp.appname
        self.setWindowTitle(text)                           #qt

    def x__getSize(self):
        s = self.size()                                     #qt
        return "%d_%d" % (s.width(), s.height())            #qt

    def x__getScreenSize(self):
        dw = guiapp.desktop()                               #qt
        geom = dw.screenGeometry(self)                      #qt
        return "%d_%d" % (geom.width(), geom.height())      #qt

#<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

class Window(QtGui.QWidget, TopLevel):                      #qt
    """This is needed to trap window closing events.
    """
    def __init__(self):
        QtGui.QWidget.__init__(self)                        #qt
        self.closesignal = ""

    def closeEvent(self, event):                            #qt
        if self.closesignal:
            guiapp.sendsignal(self.closesignal)
            event.ignore()                                  #qt
            return
        QtGui.QWidget.closeEvent(self, event)               #qt

    def x__closesignal(self, text):
        self.closesignal = text


class Dialog(QtGui.QDialog, TopLevel):
    def __init__(self):
        QtGui.QDialog.__init__(self)                        #qt

    def x__showmodal(self):
        return self.exec_() == QtGui.QDialog.Accepted       #qt


class DialogButtons(QtGui.QDialogButtonBox):                #qt
    def __init__(self):
        return

    def x__buttons(self, args):
        """This keyword argument MUST be present.
        """
        buttons = 0
        for a in args:
            try:
                b = getattr(QtGui.QDialogButtonBox, a)      #qt
                assert isinstance(b, int)                   #qt
                buttons |= b                                #qt
            except:
                gui_warning("Unknown Dialog button: %s" % a)
        QtGui.QDialogButtonBox.__init__(self, buttons)      #qt

    def x__dialog(self, dname):
        """This must be set or else the dialog buttons won't do anything.
        """
        self._dialog = guiapp.getwidget(dname)
        self.connect(self, QtCore.SIGNAL("clicked(QAbstractButton *)"), #qt
                self._clicked)                              #qt

    def _clicked(self, button):                             #qt
        if self.buttonRole(button) == self.AcceptRole:      #qt
            self._dialog.accept()                           #qt
        else:
            self._dialog.reject()                           #qt


def textLineDialog(label="???:", title=None, text="", pw=False):
    if title == None:
        title = guiapp.appname
    echo = QtGui.QLineEdit.Password if pw else QtGui.QLineEdit.Normal    #qt
    res, ok = QtGui.QInputDialog.getText(None, title, label, echo, text) #qt
    return (ok, unicode(res))


def listDialog(label="???", title=None, items=[], current=0):
    if title == None:
        title = guiapp.appname
    res, ok = QtGui.QInputDialog.getItem(None, title, label, items, current)
    return (ok, unicode(res))


def confirmDialog(message, title=None):
    if title == None:
        title = guiapp.appname
    return (QtGui.QMessageBox.question(None, title, convert(message),
            QtGui.QMessageBox.Ok | QtGui.QMessageBox.Cancel)
            == QtGui.QMessageBox.Ok)


def infoDialog(message, title=None):
    if title == None:
        title = guiapp.appname
    QtGui.QMessageBox.information(None, title, message)


#+++++++++++++++++++++++++++
# Error handling
def gui_error(message, title=None):
    if title == None:
        title = "!!! %s !!!" % guiapp.appname
    QtGui.QMessageBox.critical(None, title, message)
    guiapp.quit()

def gui_warning(message, title=None):
    if title == None:
        title = guiapp.appname
    QtGui.QMessageBox.warning(None, title, message)

def onexcept(text):
    debug(traceback.format_exc())
    gui_error(text, "Exception")
#---------------------------


fileDialogDir = ''
# In tests with the gtk dialog the options were not respected,
# with ro you could still create new directories
# and all files were shown when only-directories was specified.
# So I am using the non-native dialogs.

def fileDialog_getdir(caption = None, ro = True, startdir=None):
    global fileDialogDir
    if caption == None:
        caption = ''
    if startdir == None:
        startdir = fileDialogDir
    options = QtGui.QFileDialog.ShowDirsOnly | QtGui.QFileDialog.DontUseNativeDialog
    if ro:
        options |= QtGui.QFileDialog.ReadOnly
    d = QtGui.QFileDialog.getExistingDirectory(None, caption, startdir, options)
    if d:
        d = unicode(d)
        fileDialogDir = d
    return d

def fileDialog_open(caption = None, startdir=None, filter=None):
    global fileDialogDir
    if caption == None:
        caption = ''
    if startdir == None:
        startdir = fileDialogDir
    if filter:
        filter = '%s (%s)' % (filter[0], ' '.join(filter[1:]))  #qt
    else:
        filter = ''
    d = QtGui.QFileDialog.getOpenFileName(None, caption, startdir, filter,          #qt
        options=QtGui.QFileDialog.DontUseNativeDialog | QtGui.QFileDialog.ReadOnly) #qt
    if d:
        d = unicode(d)
        fileDialogDir = os.path.dirname(d)
    return d

def fileDialog_save(caption = None, startdir=None, filter=None):
    global fileDialogDir
    if caption == None:
        caption = ''
    if startdir == None:
        startdir = fileDialogDir
    if filter:
        filter = '%s (%s)' % (filter[0], ' '.join(filter[1:]))  #qt
    else:
        filter = ''
    d = QtGui.QFileDialog.getSaveFileName(None, caption, startdir, filter,  #qt
        options=QtGui.QFileDialog.DontUseNativeDialog)                      #qt
    if d:
        d = unicode(d)
        fileDialogDir = os.path.dirname(d)
    return d


class Stack(QtGui.QStackedWidget, XContainer):              #qt
    def __init__(self):
        QtGui.QStackedWidget.__init__(self)                 #qt
        self.x_twidgets = []

    def x__pages(self, pages):
        self.x_twidgets = pages

    def x__pack(self):
        for name in self.x_twidgets:
            w = guiapp.getwidget(name)
            w.x__pack()
            self.addWidget(w)                               #qt

    def x__set(self, index=0):
        self.setCurrentIndex(index)                         #qt


class Notebook(QtGui.QTabWidget, XContainer):               #qt
    def __init__(self):
        QtGui.QTabWidget.__init__(self)                     #qt
        self.x_tabs = []
        self.x_twidgets = []

    def x__changed(self, name=''):
        guiapp.signal(self, 'changed', name, 'currentChanged(int)') #qt

    def x__tabs(self, tabs):
        self.x_twidgets = tabs

    def x__pack(self):
        for name, title in self.x_twidgets:
            w = guiapp.getwidget(name)
            w.x__pack()
            self.addTab(w, title)                           #qt
            self.x_tabs.append([name, w])

    def x__set(self, index=0):
        self.setCurrentIndex(index)                         #qt

    def x__enableTab(self, index, on):
        self.setTabEnabled(index, on)                       #qt


class Page(QtGui.QWidget, Container):                       #qt
    def __init__(self):
        QtGui.QWidget.__init__(self)                        #qt

    def x__enable(self, on):
        """Enable/Disable widget. on should be True to enable the widget
        (display it in its normal, active state), False to disable it
        (which will normally be paler and non-interactive).
        """
        self.setEnabled(on)                                 #qt


class Frame(QtGui.QGroupBox, WBase, Container):             #qt
    def __init__(self):
        QtGui.QGroupBox.__init__(self)                      #qt
        self._text = None

    def x__text(self, text):
        self._text = text
        self.setTitle(text)                                 #qt

# A hack to improve spacing
    def setLayout(self, layout):
        topgap = 10 if self._text else 0
        layout.setContentsMargins(0, topgap, 0, 0)          #qt
        QtGui.QGroupBox.setLayout(self, layout)


class OptionalFrame(Frame):                                 #qt
    def __init__(self):                                     #qt
        Frame.__init__(self)                                #qt
        self.setCheckable(True)                             #qt
        self.setChecked(False)                              #qt

    def x__toggled(self, name=''):
        guiapp.signal(self, 'toggled', name, 'toggled(bool)') #qt

    def x__opton(self, on):
        self.setChecked(on)                                 #qt

#TODO: Is this still needed? (I think it's a qt bug)
    def x__enable_hack(self):                               #qt
        if not self.isChecked():                            #qt
            self.setChecked(True)                           #qt
            self.setChecked(False)                          #qt

    def x__active(self):
        return self.isChecked()                             #qt


def read_markup(markup):
    def read_markup0(mlist):
        text = ''
        for i in mlist:
            text += read_markup(i) if isinstance(i, list) else i
        return text
    tag = markup[0]
    if tag == '':
        return read_markup0(markup[1:])
    elif tag in ('h1', 'h2', 'h3', 'h4', 'p', 'em', 'strong'):
        return '<%s>%s</%s>' % (tag, read_markup0(markup[1:]), tag)
    elif tag == 'color':
        return '<span style="color:%s;">%s</span>' % (markup[1],
                read_markup0(markup[2:]))
    return "Markup parse error"


class Label(QtGui.QLabel, WBase):                           #qt
    def __init__(self):
        QtGui.QLabel.__init__(self)                         #qt

    def x__markup(self, markup):
        self.setText(read_markup(markup))                   #qt

    def x__image(self, path):
        self.setPixmap(QtGui.QPixmap(path))                 #qt

    def x__align(self, pos):
        if pos == "center":
            a = QtCore.Qt.AlignCenter                       #qt
        else:
            a = QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter   #qt
        self.setAlignment(a)                                #qt


class Button(QtGui.QPushButton, WBase, BBase):              #qt
    def __init__(self):
        QtGui.QPushButton.__init__(self)                    #qt

    def x__clicked(self, name=''):
        guiapp.signal(self, 'clicked', name, 'clicked()')   #qt


class ToggleButton(QtGui.QPushButton, WBase, BBase):        #qt
    def __init__(self):
        QtGui.QPushButton.__init__(self)                    #qt
        self.setCheckable(True)                             #qt

    def x__toggled(self, name=''):
        guiapp.signal(self, 'toggled', name, 'toggled(bool)') #qt

    def x__set(self, on):
        self.setChecked(on)                                 #qt


class CheckBox(QtGui.QCheckBox, WBase):                     #qt
    def __init__(self):
        QtGui.QCheckBox.__init__(self)                      #qt

    def x__toggled(self, name=''):
        # A bit of work is needed to get True/False state   #qt
        # instead of 0/1/2                                  #qt
        guiapp.signal(self, 'toggled', name,
                 'toggled(bool)', self.s_toggled)           #qt

    def s_toggled(self, state):                             #qt
        """Convert the argument to True/False.
        """                                                 #qt
        return (state != QtCore.Qt.Unchecked,)              #qt

    def x__set(self, on):
        self.setCheckState(2 if on else 0)                  #qt

    def x__active(self):
        return self.checkState() != QtCore.Qt.Unchecked     #qt


class RadioButton(QtGui.QRadioButton, WBase):               #qt
    def __init__(self):
        QtGui.QPushButton.__init__(self)                    #qt

    def x__toggled(self, name=''):
        guiapp.signal(self, 'toggled', name, 'toggled(bool)') #qt

    def x__set(self, on):
        self.setChecked(on)                                 #qt

    def x__active(self):
        return self.isChecked()                             #qt


class ComboBox(QtGui.QComboBox, WBase):                     #qt
    def __init__(self):
        QtGui.QComboBox.__init__(self)                      #qt

    def x__changed(self, name=''):
        guiapp.signal(self, 'changed', name, 'currentIndexChanged(int)') #qt

    def x__changedstr(self, name=''):
        guiapp.signal(self, 'changedstr', name,
                'currentIndexChanged(const QString &)')     #qt

    def x__set(self, items, index=0):
        self.blockSignals(True)
        self.clear()                                        #qt
        if items:
            self.addItems(items)                            #qt
            self.setCurrentIndex(index)                     #qt
        self.blockSignals(False)

    def x__index(self):
        return self.currentIndex()                          #qt

    def x__setindex(self, index):
        return self.setCurrentIndex(index)                  #qt

#    def x__colour(self, index, colour):
# Unfortunately this doesn't set the colour of the item when it is
# selected, only in the list.
#        model = self.model()
#        mitem = model.item(index)
#        mitem.setForeground(QtGui.QColor(colour))

    def x__icon(self, index, icon):
        self.setItemIcon(index, self.style().standardIcon(icondict[icon])) #qt


class ListChoice(QtGui.QListWidget, WBase):                 #qt
    def __init__(self):
        QtGui.QListWidget.__init__(self)                    #qt

    def x__changed(self, name=''):
        guiapp.signal(self, 'changed', name, 'currentRowChanged(int)') #qt

    def x__set(self, items, index=0):
        self.blockSignals(True)
        self.clear()                                        #qt
        if items:
            self.addItems(items)                            #qt
            self.setCurrentRow(index)                       #qt
        self.blockSignals(False)


class List(QtGui.QTreeWidget, WBase):                       #qt
    # Only using top-level items of the tree
    def __init__(self):
        QtGui.QTreeWidget.__init__(self)                    #qt
        self.mode = ""
        self.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection) #qt
        self.setRootIsDecorated(False)                      #qt
        self._hcompact = False  # used for scheduling header-compaction

    def x__select(self, name=''):
        guiapp.signal(self, 'select', name,
                'itemSelectionChanged()', self.s_select)    #qt

    def x__clicked(self, name=''):
        guiapp.signal(self, 'clicked', name,
                'itemClicked(QTreeWidgetItem *,int)', self.s_clicked) #qt

    def s_select(self):
        # Signal a selection change, passing the new selection list (indexes)
        s = [self.indexOfTopLevelItem(i) for i in self.selectedItems()] #qt
        if self.mode == "Single":
            return s
        else:
            return (s,)

    def s_clicked(self, item, col):                         #qt
        """This is intended for activating a user-defined editing function.
        Tests showed that this is called after the selection is changed, so
        if using this signal, use it only in 'Single' selection mode and
        use this, not 'select' to record selection changes. Clicking on the
        selected row should start editing the cell, otherwise just change
        the selection.
        """
        ix = self.indexOfTopLevelItem(item)                 #qt
        return (ix, col)

    def x__selectionmode(self, sm):
        self.mode = sm
        if sm == "None":
            self.setSelectionMode(QtGui.QAbstractItemView.NoSelection)  #qt
        elif sm == "Single":
            self.setSelectionMode(QtGui.QAbstractItemView.SingleSelection) #qt
        else:
            self.mode = ""
            self.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection) #qt

    def x__headers(self, headers):                          #qt
        self.setHeaderLabels(headers)                       #qt
        if self._hcompact:
            self._compact()

    def x__set(self, items, index=0):                       #qt
        # Note that each item must be a tuple/list containing
        # entries for each column.
        self.clear()                                        #qt
        c = 0
        for i in items:
            item = QtGui.QTreeWidgetItem(self, i)           #qt
            self.addTopLevelItem(item)                      #qt
            if c == index:
                self.setCurrentItem(item)
            c += 1
        if self._hcompact:
            self._compact()

    def x__compact(self, on=True):
        self._hcompact = on
        if on:
            self._compact()

    def _compact(self):
        for i in range(self.columnCount()):                 #qt
            self.resizeColumnToContents(i)                  #qt

    def x__single_icon(self, row, column, icon):
        """Set the icon for the given cell.
        <icon> is the file-path of the icon, the icons being cached to
        avoid duplication.
        Only the setting of a single icon is supported,
        so this is unlikely to be useful in a layout definition.
        """
        item = self.topLevelItem(row)                       #qt
        item.setIcon(column, _Icons(icon))                  #qt
        if self._hcompact:
            self._compact()

    def x__single_disable(self, row, disable=True):
        """Disable (or reenable) the given item.
        For the moment only the setting of a single item is supported,
        so this is unlikely to be useful in a layout definition.
        """
        item = self.topLevelItem(row)                       #qt
        item.setDisabled(disable)                           #qt

    def x__icon(self, row, column, icon):
        """Set the icon for the given cell.
        <icon> is the name of a standard icon.
        Only the setting of a single icon is supported,
        so this is unlikely to be useful in a layout definition.
        """
        item = self.topLevelItem(row)                       #qt
        item.setIcon(column, self.style().standardIcon(icondict[icon])) #qt
        if self._hcompact:
            self._compact()

    def x__scroll_to(self, row):
        model = self.model()                                #qt
        self.scrollTo(model.index(row, 0), self.PositionAtTop) #qt


_iconcache = {}
def _Icons(filepath):
    icon = _iconcache.get(filepath)
    if not icon:
        icon = QtGui.QIcon(filepath)                        #qt
    return icon


class LineEdit(QtGui.QLineEdit, WBase):                     #qt
    def __init__(self):
        QtGui.QLineEdit.__init__(self)                      #qt

    def x__enter(self, name=''):
        guiapp.signal(self, 'enter', name, 'returnPressed()') #qt

    def x__changed(self, name=''):
        guiapp.signal(self, 'changed', name, 'textEdited(const QString &)') #qt

    def x__get(self):
        return unicode(self.text())                         #qt

    def x__ro(self, ro):
        self.setReadOnly(ro)                                #qt

    def x__pw(self, star):
        self.setEchoMode(QtGui.QLineEdit.Password if star == "+" #qt
                else QtGui.QLineEdit.NoEcho if star == "-"  #qt
                else QtGui.QLineEdit.Normal)                #qt


class CheckList(QtGui.QWidget, WBase):                      #qt
    def __init__(self):
        QtGui.QWidget.__init__(self)                        #qt
        self.box = QtGui.QVBoxLayout(self)                  #qt
        self.title = None
        if text:                                            #qt
            l.addWidget(QtGui.QLabel(text))                 #qt
        self.widget = QtGui.QListWidget()                   #qt
        l.addWidget(self.widget)                            #qt

    def x__title(self, text):
        if self.title:
            self.title.setText(text)                        #qt
        else:
            self.title = QtGui.QLabel(text)                 #qt
            self.box.insertWidget(0, self.title)            #qt

    def x__checked(self, index):
        return (self.widget.item(index).checkState() ==     #qt
                QtCore.Qt.Checked)                          #qt

    def x__set(self, items):
        self.widget.blockSignals(True)                      #qt
        self.widget.clear()                                 #qt
        if items:
            for s, c in items:
                wi = QtGui.QListWidgetItem(s, self.widget)  #qt
                wi.setCheckState(QtCore.Qt.Checked if c     #qt
                        else QtCore.Qt.Unchecked)           #qt
        self.blockSignals(False)                            #qt


class TextEdit(QtGui.QTextEdit, WBase):                     #qt
    def __init__(self):
        QtGui.QTextEdit.__init__(self)                      #qt

    def x__ro(self, ro):
        self.setReadOnly(ro)                                #qt

    def x__append_and_scroll(self, text):
        self.append(text)                                   #qt
        self.ensureCursorVisible()                          #qt

    def x__get(self):
        return unicode(self.toPlainText())                  #qt

    def x__undo(self):
        QtGui.QTextEdit.undo(self)                          #qt

    def x__redo(self):
        QtGui.QTextEdit.redo(self)                          #qt

    def x__copy(self):
        QtGui.QTextEdit.copy(self)                          #qt

    def x__cut(self):
        QtGui.QTextEdit.cut(self)                           #qt

    def x__paste(self):
        QtGui.QTextEdit.paste(self)                         #qt


class HtmlView(QtWebKit.QWebView, WBase):                   #qt
    def __init__(self):
        QtWebKit.QWebView.__init__(self)                    #qt
        self.settings().setDefaultTextEncoding('utf-8')     #qt

    def x__html(self, content):
        self.setHtml(content)                               #qt

    def x__setUrl(self, url):
        self.load(QtCore.QUrl(url))                         #qt

    def x__prev(self):
        self.back()                                         #qt

    def x__next(self):
        self.forward()                                      #qt


class SpinBox(QtGui.QDoubleSpinBox, WBase):                 #qt
    def __init__(self):
        QtGui.QDoubleSpinBox.__init__(self)                 #qt
        self.step = None

    def x__changed(self, name=''):
        guiapp.signal(self, 'changed', name, 'valueChanged(double)') #qt

    def x__min(self, min):
        self.setMinimum(min)

    def x__max(self, max):
        self.setMaximum(max)

    def x__decimals(self, dec):
        self.setDecimals(dec)
        if not self.step:
            self.setSingleStep(10**(-dec))

    def x__step(self, step):
        self.setSingleStep(step)

    def x__value(self, val):
        self.setValue(val)


class ProgressBar(QtGui.QProgressBar, WBase):               #qt
    def __init__(self):
        QtGui.QProgressBar.__init__(self)                   #qt

    def x__set(self, value):
        self.setValue(value)                                #qt

    def x__max(self, max):
        self.setMaximum(max)                                #qt



# Layout classes
class Layout:
    """A mixin base class for all layout widgets.
    """
    pass

boxmargin=3
class _BOX(Layout):
    def do_layout(self, items):
        self.setContentsMargins(boxmargin, boxmargin, boxmargin, boxmargin) #qt
        for wl in items:
            if isinstance(wl, QtGui.QWidget):               #qt
                self.addWidget(wl)                          #qt
            elif isinstance(wl, SPACE):                     #qt
                if wl.size:                                 #qt
                    self.addSpacing(wl.size)                #qt
                self.addStretch()                           #qt
            elif isinstance(wl, Layout):                    #qt
                self.addLayout(wl)                          #qt
            else:                                           #qt
                gui_error("Invalid Box entry: %s" % repr(wl))


class VBOX(QtGui.QVBoxLayout, _BOX):                        #qt
    def __init__(self):
        QtGui.QVBoxLayout.__init__(self)                    #qt


class HBOX(QtGui.QHBoxLayout, _BOX):                        #qt
    def __init__(self):
        QtGui.QHBoxLayout.__init__(self)                    #qt


class GRID(QtGui.QGridLayout, Layout):                      #qt
    def __init__(self):
        QtGui.QGridLayout.__init__(self)                    #qt

    def do_layout(self, rows):
        y = -1
        for row in rows:
            y += 1
            x = -1
            for wl in row:
                x += 1
                if isinstance(wl, Span):
                    continue
                # Determine the row and column spans
                x1 = x + 1
                while (x1 < len(row)) and isinstance(row[x1], CSPAN):
                    x1 += 1
                y1 = y + 1
                while (y1 < len(rows)) and isinstance(rows[y1][x], RSPAN):
                    y1 += 1

                if isinstance(wl, QtGui.QWidget):           #qt
                    self.addWidget(wl, y, x, y1-y, x1-x)    #qt
                elif isinstance(wl, Layout):
                    self.addLayout(wl, y, x, y1-y, x1-x)    #qt
                elif isinstance(wl, SPACE):
                    self.addItem(QtGui.QSpacerItem(wl.size, wl.height),
                            y, x, y1-y, x1-x)               #qt
                else:
                    gui_error("Invalid entry in Grid layout: %s" % repr(wl))


class SPACE:
    """Can be used in boxes and grids. In boxes only size is of interest,
    and it also means vertical size in the case of a vbox. In grids size
    is the width.
    """
    def __init__(self, size_width='0', height='0'):         #qt
        self.size = int(size_width)                         #qt
        self.height = int(height)                           #qt


class Span:
    """Class to group special grid layout objects together - it doesn't
    actually do anything itself, but is used for checking object types.
    """
    pass


class CSPAN(Span):
    """Column-span layout item. It doesn't do anything itself, but it is used
    by the Grid layout constructor.
    """
    pass


class RSPAN(Span):
    """Row-span layout item. It doesn't do anything itself, but it is used
    by the Grid layout constructor.
    """
    pass


class HLINE(QtGui.QFrame):                                  #qt
    def __init__(self, pad=None):
        # pass the pad argument thus: 'HLINE,3'
        QtGui.QFrame.__init__(self)                         #qt
        self.setFrameShape(QtGui.QFrame.HLine)              #qt
        if pad:
            self.setFixedHeight(1 + 2*int(pad))             #qt


class VLINE(QtGui.QFrame):                                  #qt
    def __init__(self, pad=None):
        # pass the pad argument thus: 'VLINE,3'
        QtGui.QFrame.__init__(self)                         #qt
        self.setFrameShape(QtGui.QFrame.VLine)              #qt
        if pad:
            self.setFixedWidth(1 + 2*int(pad))              #qt


class DATA:
    """This is not really a widget, it just holds a dictionary of
    potentially internationalized messages.
    """
    def x__messages(self, mdict):
        self.messages = mdict

    def x__get(self, key):
        return self.messages.get(key)


class Suim(QtGui.QApplication):
    """This class represents an application gui, possibly with more than
    one top level window.
    """
    timers = []             # timer objects

    def __init__(self, appname='suim', busywidgets = []):
        global guiapp, T_
        guiapp = self
        QtGui.QApplication.__init__(self, [])               #qt
        self.appname = appname
        self.eno = QtCore.QEvent.registerEventType()        #qt
        # This overcomplicated looking bit should deal with translating the built in dialogs
        _translator = QtCore.QTranslator(self)
        if (_translator.load('qt_'+ QtCore.QLocale.system().name(),
                QtCore.QLibraryInfo.location(QtCore.QLibraryInfo.TranslationsPath))):
            self.installTranslator(_translator)

        # list of widgets to disable while 'busy'
        self.busywidgets = busywidgets

        self.busystate = False
        self.busy_lock = threading.Lock()

        self.setQuitOnLastWindowClosed(False)               #qt

        self.widgets = {}           # all widgets, key = widget tag
        self.signal_dict = {}       # signal connections, key = signature

        # callback list for event loop: (callback, arglist) pairs:
        self.idle_calls = deque()


    def event(self, e):
        if e.type() == self.eno:
            # Process item from list
            cb, a = self.idle_calls.popleft()
            cb(*a)
            return True
        else:
            return QtGui.QApplication.event(self, e)        #qt


    def run(self):
        self.exec_()                                        #qt


    def quit(self, cc=0):
        # QCoreApplication provides the static function 'exit'
        self.exit(cc)                                       #qt


    def addwidget(self, fullname, wo):
        if self.widgets.has_key(fullname):
            gui_error("Attempted to define widget '%s' twice." % fullname)
        self.widgets[fullname] = wo


    def getwidget(self, w):
        widget = self.widgets.get(w)
        if widget == None:
            gui_warning("Unknown widget: %s" % w)
        return widget


    def show(self, windowname):
        self.getwidget(windowname).setVisible()


    def command(self, cmdtext, *args):
        cmd = specials_table.get(cmdtext)
        if not cmd:
            w, m = cmdtext.split(".")
            wo = self.getwidget(w)
            cmd = getattr(wo, 'x__' + m)
        return cmd(*args)


    def widget(self, wtype, wname, args):
        wobj = widget_table[wtype]()
        wobj.w_name = wname

        # Attributes
        for key, val in args.iteritems():
            handler = "x__" + key
            if hasattr(wobj, handler):
                getattr(wobj, handler)(val)
# Unrecognized attributes are ignored ...

        self.addwidget(wname, wobj)


    def widgetlist(self, wlist):
        for w in wlist:
            # Add simple signals
            for s in w[3:]:
                w[2][s] = ''
            self.widget(w[0], w[1], w[2])


    def signal(self, source, signal, name=None, xsignal=None, convert=None):
        """Enable or disable a signal.
        Signal.signals is a dictionary of enabled signals.
        The key is constructed from the widget name and the formal signal name.
        The name of the signal which actually gets generated will be the
        same as the key unless the 'name' parameter is set. See the
        'Signal' class for further details.
        If 'name' is None (not ''!), the signal will be disabled.
        """
        widsig = source.w_name + '*' + signal
        if name == None:
            s = Signal.signals.get(widsig)
            if not s:
                gui_error("Can't disable signal '%s' - it's not enabled"
                        % widsig)
            s.disconnect()          # Probably not necessary in qt
            del(Signal.signals[widsig])
        else:
            if Signal.signals.has_key(widsig):
                gui_error("Signal already connected: %s" % widsig)
            Signal.signals[widsig] = Signal(source, signal, name, xsignal,
                    convert)


    def connect(self, signal, function):
        if self.signal_dict.has_key(signal):
            self.signal_dict[signal].append(function)
        else:
            self.signal_dict[signal] = [function]


    def connectlist(self, *slotlist):
        for s in slotlist:
            self.connect(*s)


    def disconnect(self, signal, function):
        try:
            l = self.signal_dict[signal]
            l.remove(function)
        except:
            gui_error("Slot disconnection for signal '%s' failed"
                    % signal)


    def sendsignal(self, name, *args):
        # When there are no slots a debug message is output.
        slots = self.signal_dict.get(name)
        if slots:
            try:
                for slot in slots:
                    slot(*args)
            except:
                gui_error("Signal handling error:\n  %s"
                        % traceback.format_exc())
        else:
            debug("Unhandled signal: %s %s" % (name, repr(args)))


    def idle_add(self, callback, *args):
        self.idle_calls.append((callback, args))
        e = QtCore.QEvent(self.eno)                         #qt
        self.postEvent(self, e)                             #qt


    def timer(self, callback, period):
        """Start a timer which calls the callback function on timeout.
        Only if the callback returns True will the timer be retriggered.
        """
        Suim.timers.append(Timer(callback, period))


    def busy(self, on, busycursor=True):
        """This activates (or deactivates, for on=False) a 'busy' mechanism,
        which can be one or both of the following:
          Make the application's cursor change to the 'busy cursor'.
          Disable a group of widgets.
        There is a lock to prevent the busy state from being set when it
        is already active, or unset it when already unset.
        """
        self.busy_lock.acquire()
        if on:
            if self.busystate:
                self.busy_lock.release()
                return
            self.busycursor = busycursor
            if busycursor:
                self.setOverrideCursor(QtCore.Qt.BusyCursor) #qt
        else:
            if not self.busystate:
                self.busy_lock.release()
                return
            if self.busycursor:
                self.restoreOverrideCursor()                #qt
        self.busystate = on
        self.busy_lock.release()
        for wn in self.busywidgets:
            w = self.getwidget(wn)
            if w:
                w.setEnabled(not on)                        #qt
            else:
                debug("*ERROR* No widget '%s'" % wn)


class Timer(QtCore.QTimer):                                 #qt
    def __init__(self, timers, callback, period):
        QtCore.QTimer.__init__(self)                        #qt
        self.x_callback = callback
        self.connect(self, QtCore.SIGNAL("timeout()"),      #qt
                self.x_timeout)
        self.start(int(period * 1000))                      #qt

    def x_timeout(self):
        if not self.x_callback():
            self.stop()                                     #qt
            Suim.timers.remove(self)



class Signal:
    """Each instance represents a single connection.
    """
    signals = {}        # Enabled signals

    def __init__(self, source, signal, name, xsignal, convert):
        """'source' is the widget object which initiates the signal.
        'signal' is the signal name.
        If 'name' is given (not empty), the signal will get this as its name,
        and this name may be used for more than one connection.
        Otherwise the name is built from the name of the source widget and
        the signal type as 'source*signal' and this is unique.
        If 'name' begins with '+' an additional argument, the source
        widget name, will be inserted at the head of the argument list.
        'xsignal' is a toolkit specific signal descriptor.
        'convert' is an optional function (default None) - toolkit specific -
        to perform signal argument conversions.
        """
        self.widsig = '%s*%s' % (source.w_name, signal)
        #+ For disconnect?
        self.xsignal = xsignal
        #-
        self.convert = convert      # Argument conversion function
        self.tag = name if name else self.widsig
        self.wname = source.w_name if self.tag[0] == '+' else None
        if not source.connect(source, QtCore.SIGNAL(xsignal),   #qt
                self.signal):
            gui_error("Couldn't enable signal '%s'" % self.widsig)

    def signal(self, *args):
        if self.convert:
            args = self.convert(*args)
        if self.wname:
            guiapp.sendsignal(self.tag, self.wname, *args)
        else:
            guiapp.sendsignal(self.tag, *args)

    def disconnect(self):
        w = guiapp.getwidget(self.widsig.split('*')[0])
        w.disconnect(w, QtCore.SIGNAL(self.xsignal), self.signal)  #qt



#+++++++++++++++++++++++++++
# Catch all unhandled errors.
def errorTrap(type, value, tb):
    etext = "".join(traceback.format_exception(type, value, tb))
    debug(etext)
    gui_error(etext, "This error could not be handled.")

sys.excepthook = errorTrap
#---------------------------

widget_table = {
    "DATA": DATA,
    "Window": Window,
    "Dialog": Dialog,
    "DialogButtons": DialogButtons,
    "Notebook": Notebook,
    "Stack": Stack,
    "Page": Page,
    "Frame": Frame,
    "Button": Button,
    "ToggleButton": ToggleButton,
    "RadioButton": RadioButton,
    "CheckBox": CheckBox,
    "Label": Label,
    "CheckList": CheckList,
    "List": List,
    "OptionalFrame": OptionalFrame,
    "ComboBox": ComboBox,
    "ListChoice": ListChoice,
    "LineEdit": LineEdit,
    "TextEdit": TextEdit,
    "HtmlView": HtmlView,
    "SpinBox": SpinBox,
    "ProgressBar": ProgressBar,
}

specials_table = {
    "textLineDialog": textLineDialog,
    "infoDialog": infoDialog,
    "confirmDialog": confirmDialog,
    "errorDialog": gui_error,
    "warningDialog": gui_warning,
    "fileDialog_getdir": fileDialog_getdir,
    "fileDialog_open": fileDialog_open,
    "fileDialog_save": fileDialog_save,
    "listDialog": listDialog,
}

layout_table = {
    "VBOX": VBOX,
    "HBOX": HBOX,
    "GRID": GRID,
#    "+": GRIDROW,
    "-": CSPAN,
    "|": RSPAN,
    "*": SPACE,
    "VLINE": VLINE,
    "HLINE": HLINE,
}

