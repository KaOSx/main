#!/usr/bin/python


# Next look at switching to a selected directory from the path (DONE),
# switching to a directory in the list, and removing/changing toolbar
# buttons (and their actions).
# Have a checkbutton for hidden files / directories somewhere.


import os
from PyQt4 import QtGui, QtCore

def clicked(r, c):
    print r, c

def iclicked(item):
    print item


class DirListing(QtGui.QTreeWidget):                       #qt
    # Only using top-level items of the tree
    def __init__(self):
        QtGui.QTreeWidget.__init__(self)                    #qt
        self._hcompact = False  # used for scheduling header-compaction
        self.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.headers(['Name']) #qt
        self.setRootIsDecorated(False)                      #qt

        self.connect(self, QtCore.SIGNAL('itemSelectionChanged()'),
                self.s_select)
        self.connect(self, QtCore.SIGNAL('itemClicked(QTreeWidgetItem *,int)'),
                self.s_clicked)


    def s_select(self):
        # Signal a selection change, passing the new selection list (indexes)
        s = [self.indexOfTopLevelItem(i) for i in self.selectedItems()] #qt
        print "Sel", s


    def s_clicked(self, item, col):                         #qt
        # I guess I should use this for selection if using single
        # click actions, because setting a list up might cause the
        # first item to be selected (it doesn't, actually, so select
        # could be used), and it should
        # only change directory if actually clicked.


        """This is intended for activating a user-defined editing function.
        Tests showed that this is called after the selection is changed, so
        if using this signal, use it only in 'Single' selection mode and
        use this, not 'select' to record selection changes. Clicking on the
        selected row should start editing the cell, otherwise just change
        the selection.
        """
        ix = self.indexOfTopLevelItem(item)                 #qt
        print ix, col



    def headers(self, headers):                          #qt
        self.setHeaderLabels(headers)                       #qt
        if self._hcompact:
            self._compact()

    def set(self, items, index=-1):                       #qt
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



def dirsel(action):
    print action.xtag
    i = 0
    if action.xindex == 0:
        print '/'
    else:
        path = ''
        while i < action.xindex:
            i += 1
            path += '/' + dirs[i]
        print path
    setlisting(path)
# the toolbuttons should stay the same until a different lower directory
# is chosen (one not in the old list?)


def setlisting(path):
    dlist = os.listdir(path)
    dldir = []
    dlfile = []
    for f in dlist:
        if os.path.isdir(path + '/' + f):
            dldir.append('d:' + f)
        else:
            dlfile.append('f:' + f)
    dldir.sort()
    dlfile.sort()
    listing.set([d] for d in (dldir + dlfile))


if __name__ == '__main__':

    import sys

    app = QtGui.QApplication(sys.argv)
    app.setStyleSheet("""
    QToolButton {
     border: 2px solid #8f8f91;
     border-radius: 6px;
     background-color: yellow;
    }

    QToolButton:checked {
     background-color: #f0c080;
    }
""")

    window = QtGui.QWidget()
    listing = DirListing()
    bar = QtGui.QToolBar()
    bar.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
    actg = QtGui.QActionGroup(bar)
    QtCore.QObject.connect(actg, QtCore.SIGNAL('triggered (QAction *)'), dirsel)
    actg.setExclusive(True)

    layout = QtGui.QVBoxLayout()
    layout.addWidget(bar)
    layout.addWidget(listing)
    window.setLayout(layout)
    window.resize(600, 480)



    path = '/home/mt/DATA/pyjamas'


    dirs = path.split('/')
#    dirs = ['', 'home', 'mt', 'DATA', 'software-verylong', 'DOCS', 'python_qt']
    butix = 0
    for but in dirs:
        bw = bar.addAction(but+'/')
        bw.setCheckable(True)
        actw = actg.addAction(bw)
        actw.xtag = but
        actw.xindex = butix
        butix += 1

    setlisting(path)

    window.show()

    sys.exit(app.exec_())
