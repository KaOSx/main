#!/usr/bin/env python2
#

doprint = True

input_files = ( "larch_intro.html",
                "larch_features.html",
                "larch_quick-console.html",
                "larch_quick.html",
                "archin.html",
                "larchify.html",
                "medium.html",
                "profiles.html",
                "larch_live_system.html",
                "larch_ssh.html",
                "larch_running.html",
                "larch_gui.html",
                "gui_project_settings.html",
                "gui_installation.html",
                "gui_larchify.html",
                "gui_medium.html",
            )


import os
os.chdir(os.path.dirname(os.path.realpath(__file__)))

from xml.parsers.expat import ParserCreate

class Parser:

    def __init__(self):
        self.parser = ParserCreate("utf-8")
        self.stack = []
        self.collecting = False
        self.cname = None
        self.aname = None

        self.parser.StartElementHandler = self.start_element
        self.parser.EndElementHandler = self.end_element
        self.parser.CharacterDataHandler = self.char_data

    # 3 handler functions
    def start_element(self, name, attrs):
        if name == 'a':
            if self.stack[-1][0] == 'h':
                self.cname = self.stack[-1]
                self.collect = ""
                self.collecting = True
                self.aname = attrs.get('name')
        elif name[0] == 'h' and attrs.get('id') == 'pagetitle':
                self.level = attrs.get('level', '1')
                self.collect = ""
                self.cname = name
                self.collecting = True
                self.aname = '*pagetitle*'
        self.stack.append(name)

    def end_element(self, name):
        if name == self.cname and self.collecting:
            text = ' '.join(self.collect.split())
            if self.aname == '*pagetitle*':
                self.pagetitle = (self.cname, self.level, text)
            else:
                self.collected.append((self.cname, self.aname, text))
            self.collecting = False
        # Just in case (!), check valid xml:
        if self.stack and (self.stack[-1] == name):
            del(self.stack[-1])
        else:
            print "ERROR: no matching closing bracket for '%s'" % name
            assert False

    def char_data(self, data):
        if self.collecting:
            self.collect += data


    def parsefile(self, path):
        """Parse the file at the given path.
        """
        f = open(path)
        src = f.read()
        s = "<xml>\n%s\n<xml>\n" % src
        f.close()
        self.collected = []
        self.pagetitle = None
        self.parser.Parse(s)
        if not self.pagetitle:
            print "No pagetitle!"
            self.pagetitle = "???"

        dprint("pagetitle = (%s | %s | '%s')" % self.pagetitle)

        item = {
                "filename"  : os.path.basename(path),
                "pagetitle" : self.pagetitle[2],
                "source"    : src,
                "title-h"   : self.pagetitle[0],
                "level"     : self.pagetitle[1],
                "anchors"   : self.collected
                        # [(hN, reference, title), ...  ]
            }

        for c in self.collected:
            dprint("GOT: '%s#%s': %s" % c)
        dprint()

        return item



def generate(folder, webpage):
    os.system("rm -rf " + folder)
    os.mkdir(folder)
    os.system("cp -r css " + folder)
    index = 0
    for hfile in files:
        fpath = "%s/%s" % (folder, hfile["filename"])
        dprint("Generating " + fpath)
        if index > 0:
            hf = files[index-1]
            hfile["plink"] = hf["filename"]
            hfile["ptitle"] = hf["pagetitle"]
        else:
            hfile["plink"] = None
        index += 1
        if index < len(files):
            hf = files[index]
            hfile["nlink"] = hf["filename"]
            hfile["ntitle"] = hf["pagetitle"]
        else:
            hfile["nlink"] = None
        hfile["webpage"] = webpage
        output = engine.render("larchdocs_tmpl.pyhtml", hfile)
        fh = open(fpath, "w")
        fh.write(output)
        fh.close()


    tocfile = "%s/index.html" % folder
    dprint("Generating " + tocfile)
    output = engine.render("toc_tmpl.pyhtml", {"webpage": webpage, "items": files})
    fh = open(tocfile, "w")
    fh.write(output)
    fh.close()



def dprint(line=""):
    if doprint:
        print line


if __name__ == "__main__":
    parser = Parser()
    files = []
    for fn in input_files:
        dprint("Parsing " + fn)
        files.append(parser.parsefile("src/" + fn))

    import tenjin
    from tenjin.helpers import *
    engine = tenjin.Engine()

    generate("html", webpage=False)
    generate("web", webpage=True)

