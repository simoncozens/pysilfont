#!/usr/bin/env python
'Make the WOFF meatadata xml file based on input UFO and FONTLOG.txt'
__url__ = 'http://github.com/silnrsi/pysilfont'
__copyright__ = 'Copyright (c) 2017 SIL International (http://www.sil.org)'
__license__ = 'Released under the MIT License (http://opensource.org/licenses/MIT)'
__author__ = 'David Raymond'

from silfont.core import execute
#import silfont.etutil as ETU
#from xml.etree import cElementTree as ET
#from xml.dom import minidom
import re

argspec = [
    ('font',{'help': 'Source font file'}, {'type': 'infont'}),
    ('-n','--primaryname', {'help': 'Primary Font Name','required': True},{}),
    ('-i','--orgid', {'help': 'orgId','required': True},{}),
    ('-f','--fontlog',{'help': 'FONTLOG.txt file', 'default': 'FONTLOG.txt'}, {'type': 'infile'}),
    ('-l','--log',{'help': 'Log file'}, {'type': 'outfile', 'def': '_makewoff.log'})]

def doit(args) :
    font = args.font
    pfn = args.primaryname
    orgid = args.orgid
    fontlog = args.fontlog
    logger = args.logger

    # ****** Parse the fontlog file
    (section,match) = readuntil(fontlog,("Basic Font Information",)) # Skip until start of "Basic Font Information" section
    if match == None : logger.log("No 'Basic Font Information' section in fontlog", "S")
    (description,match) = readuntil(fontlog,("Information for C","Acknowledgements")) # Desciption ends when first of these sections is found
    if match == "Information for C" : (section,match) = readuntil(fontlog,("Acknowledgements",))# If Info... section present then skip on to Acknowledgements
    if match == None : logger.log("No 'Acknowledgements' section in fontlog", "S")
    (acksection,match) = readuntil(fontlog,("No match needed!!",))

    credits = []
    name = ""
    nexttype = "N"
    for line in acksection :
        match = re.match("^([NEWD]): (.*)",line)
        if match is None:
            if nexttype == "E" : name = name + line # Allow for name to be multiple names spread over multiple lines
        else :
            type = match.group(1)
            text = match.group(2)
            # Assumes all three exist in file in the order NWD
            if type <> nexttype : logger.log("Credit records in font log not in order N,E,W,D", "S")
            if type == "N" :
                name = text
                nexttype = "E"
            elif type == "E" :
                nexttype = "W"
            elif type == "W" :
                url = text
                nexttype = "D"
            else :
                designer = text
                credits.append((name,url,designer))
                nexttype = "N"
    if credits == [] : logger.log("No credits found in fontlog", "S")

    # ****** Find & process info required in the UFO

    fi = font.fontinfo

    ufofields= {}
    missing = None
    for field in ("versionMajor", "versionMinor", "openTypeNameManufacturer", "openTypeNameManufacturerURL", "openTypeNameLicense", "copyright", "trademark") :
        elem = fi[field][1] if field in fi else None
        if elem is None :
            missing = field if missing is None else missing + ", " + field
        else :
            ufofields[field] = elem.text
    if missing is not None : logger.log("Field(s) missing from fontinfo.plist: " + missing, "S")

    version = ufofields["versionMajor"] + "." + ufofields["versionMinor"].zfill(3)

    # Split the license into shorter lines, breaking on spaces.
    license = []
    for line in ufofields["openTypeNameLicense"].splitlines() :
        line = line.strip()
        while len(line) > 74 : ## Value of 74 might need adjusting!
            words = line[0:74].split(' ')
            l = ' '.join(words[0:len(words)-1])
            license.append(l)
            line = line[len(l):].strip()
        license.append(line)

    filename = pfn + "-WOFF-metadata.xml"
    try :
        file = open(filename,"w")
    except Exception as e :
        logger.log("Unable to open " + filename + " for writing:\n" + str(e), "S")

    file.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    file.write('<metadata version="' + version + '">\n')
    file.write('  <uniqueid id="' + orgid + '.' + pfn + '.' + version + '" />\n')
    file.write('  <vendor name="' +  ufofields["openTypeNameManufacturer"] + '" url="' + ufofields["openTypeNameManufacturerURL"] + '" />\n')

    file.write('  <credits>\n')
    for credit in credits :
        file.write('    <credit>\n')
        file.write('      name="' + credit[0] + '"\n')
        file.write('      url="' + credit[1] + '"\n')
        file.write('      role="' + credit[2] + '"\n')
        file.write('    </credit>\n')
    file.write('  </credits>\n')

    file.write('  <description>\n')
    file.write('    <text lang="en">\n')
    for line in description : file.write('      ' + line + '\n')
    file.write('    </text>\n')
    file.write('  </description>\n')

    file.write('  <license url="http://scripts.sil.org/OFL" id="org.sil.ofl.1.1">\n')
    file.write('    <text lang="en">\n')
    for line in license : file.write('      ' + line + '\n')
    file.write('    </text>\n')
    file.write('  </license>\n')

    file.write('  <copyright>\n')
    file.write('    <text lang="en">' + ufofields["copyright"] + '</text>\n')
    file.write('  </copyright>\n')

    file.write('  <trademark>\n')
    file.write('    <text lang="en">' + ufofields["trademark"] + '</text>\n')
    file.write('  </trademark>\n')








    file.close()


    # Create the XML item and write to disk

    #woffxml = ET.Element('metadata', version = version)
    #ET.SubElement(woffxml, 'uniqueid', id = orgid + "." + pfn + "." + version)
    #ET.SubElement(woffxml, 'vendor', name = ufofields["openTypeNameManufacturer"])
    #credelem = ET.SubElement(woffxml,"credits")
    #for credit in credits : ET.SubElement(credelem,'credit', name = credit[0], url = credit[1], role = credit[2])
    #descelem = ET.SubElement(woffxml,"description")
    #desctext = ET.SubElement(descelem, 'text', lang = "en")
    #desctext.text = description

    #attributeOrder = ETU.makeAttribOrder(["name","url","role"])
    #etwobj=ETU.ETWriter(woffxml, attributeOrder=attributeOrder)


    #xmlstr = minidom.parseString(ET.tostring(woffxml)).toprettyxml(indent="  ")
    #print xmlstr

    #filename = pfn + "-WOFF-metadata.xml"
    #ET.ElementTree(woffxml).write(filename)
    #try :
    #    woffxml.write(filename)
    #except Exception as e :
    #    print e
    #    logger.log("Unable to open " + filename + " for writing: " + str(e), "S")

    #etwobj.serialize_xml(file.write)

    #print ET.tostring(woffxml)


def readuntil(file,texts) : # Read through file until line is in text.  Return section up to there and the text matched
    skip = True
    match = None
    for line in file:
        line = line.strip()
        if skip : # Skip underlines and blank lines at start of section
            if line == "" or line[0:5] == "-----" :
                pass
            else:
                section = [line]
                skip = False
        else :
            for text in texts :
                if line[0:len(text)] == text : match = text
            if match : break
            section.append(line)
    while section[-1] == "" : section.pop() # Strip blank lines at end
    return (section, match)

def cmd() : execute("UFO",doit,argspec)
if __name__ == "__main__": cmd()