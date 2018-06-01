# from __future__ import print_function

import glob
import os
import math
import re
import jsonlines
import xlsxwriter
from xlsxwriter.utility import xl_col_to_name

# from glob import glob

# from edtslib import system
from allSectors import getSector
from formulas import helper_formulas
from formulas import table_stars
from formulas import object_formulas


# from time import gmtime
# from string import ascii_uppercase
#
# import Tkinter as tk
# import myNotebook as nb
# from config import config
# from os import environ



jdir = os.environ['USERPROFILE'] + os.path.join("\\Saved Games\\Frontier Developments\\Elite Dangerous\\journal.*.log")
# imageDir = os.environ['USERPROFILE'] + os.path.join("\\Pictures\\Frontier Developments\\Elite Dangerous\\")

print("This can take a couple of minutes depending on how much data you have.\n\n")

print("It looks like your Elite: Damgerous Journal directory is:\n")
print(os.environ['USERPROFILE'] + os.path.join("\\Saved Games\\Frontier Developments\\Elite Dangerous\\"))

# C:\Users\Max\Saved Games\Frontier Developments\Elite Dangerous
# journal_dir = os.path.join("c:/", "Users", "Saved Games", "Frontier Developments", "Elite Dangerous", "journal.*.log")
# jdir = os.path.join("C:\\Users\\Max\\Saved Games\\Frontier Developments\\Elite Dangerous\\journal.*.log")


# print(jdir)
# print(juserprofile)
# journal_dir = config.get('journaldir') or config.default_journal_dir
# out_dir = config.get('outdir') or config.default_out_dir
# outfilename = 'all_' + time.strftime("%Y-%m-%d" + "T" + "%H-%M-%S" + "Z", gmtime()) + ".csv"
# jdir = os.path.join(journal_dir + "\\journal.*.log")
# this = sys.modules[__name__]	# For holding module globals

table_bodies_header = (
    "oType",
    "oClass",
    "Object",
    "objCorrected",
    "Spectral",
    "MassMT",
    "Age_MY",
    "SurfaceGravity",
    "SurfacePressure",
    "InnerRadius",
    "Radius",
    "SurfaceTemperature",
    "AbsoluteMagnitude",
    "Luminosity"
)
table_bodies = (
    "StarType",
    "PlanetClass",
    "objCorrected",
    "Spectral",
    "StellarMass",
    "MassEM",
    "Age_MY",
    "SurfaceGravity",
    "SurfacePressure",
    "InnerRadius",
    "Radius",
    "SurfaceTemperature",
    "AbsoluteMagnitude",
    "Luminosity"
)

table_body = (
    "BodyName",
    "timestamp",
    "BodyID",
    "DistanceFromArrivalLS",
    "SystemName",
    # "Remainder",
    "BoxelName",
    "BoxelCode",
    "oType",
    "oClass",
    "Object",
    "Ring",
    # "objCorrected",
    # "Spectral",
    "MassMT",
    "Mass",
    "Density",
    "Age_MY",
    "SurfaceGravity",
    "SurfacePressure",
    "InnerRadius",
    "Radius",
    "SurfaceTemperature",
    "AbsoluteMagnitude",
    "Luminosity",
    "barycentre",
    "SemiMajorAxis",
    "Eccentricity",
    "OrbitalInclination",
    "Periapsis",
    "OrbitalPeriod",
    "OrbitalVelocity",
    "AxialTilt",
    "RotationPeriod",
    "TerraformState",
    "Landable",
    "TidalLock",
    # "isItHA",
    "Volcanism",
    "vLevel",
    "vMaterial",
    "vType",
    "Composition",
    "Ice",
    "Rock",
    "Metal",
    "Atmosphere",
    "aTemp",
    "aDensity",
    "aElements",
    "aRich"
)

table_orbit = (
    "SemiMajorAxis",
    "Eccentricity",
    "OrbitalInclination",
    "Periapsis",
    "OrbitalPeriod",
    "AxialTilt",
    "RotationPeriod",
    "TerraformState",
    "Landable",
    "TidalLock",
    "Volcanism",
    "vLevel",
    "vMaterial",
    "vType",
    "Atmosphere",
    "aTemp",
    "aDensity",
    "aElements",
    "aRich"
)


table_atmosphere = (
    "Iron",
    "Silicates",
    "SulphurDioxide",
    "CarbonDioxide",
    "Nitrogen",
    "Oxygen",
    "Water",
    "Argon",
    "Ammonia",
    "Methane",
    "Neon",
    "Hydrogen",
    "Helium"
)

table_materials = (
    "carbon",
    "iron",
    "nickel",
    "phosphorus",
    "sulphur",
    "arsenic",
    "chromium",
    "germanium",
    "manganese",
    "selenium",
    "vanadium",
    "zinc",
    "zirconium",
    "cadmium",
    "mercury",
    "molybdenum",
    "niobium",
    "tin",
    "tungsten",
    "antimony",
    "polonium",
    "ruthenium",
    "technetium",
    "tellurium",
    "yttrium"
)

table_sectors = (
    "SectorName",
    "SecX",
    "SecY",
    "SecZ",
    "BoxelsVisited",
    "SystemsVisited"
)

table_boxels = (
    "BoxelName",
    "BoxX",
    "BoxY",
    "BoxZ",
    "Sector",
    "posCode",
    "mCode",
    "mCodeMod",
    "G",
    "F",
    "E",
    "D",
    "C",
    "B",
    "A",
    "SystemsVisited"
)

table_systems = (
    "StarSystem",
    "SysX",
    "SysY",
    "SysZ",
    "timestamp",
    "SystemAddress",
    "BoxelName",
    "isProcGen",
    "PrimaryStarType",
    "BodyCount",
    "G",
    "F",
    "E",
    "D",
    "C",
    "B",
    "A"
)

table_gps = (
    # "image",
    "Object",
    "Timestamp",
    # "Type",
    "Latitude",
    "Longitude"
    # "Declination",
    # "Altitude",
    # "Filename"
)

### Convert formulas to show proper Excel column locations

def header2column(oldFormula):
    newFormula = oldFormula
    for columnHeader in re.findall("\$(\w+)", newFormula):
        for column in [column for column, columnName in enumerate(table_body) if columnName == columnHeader]:
            newcolumnHeader = xl_col_to_name(column) + ":$" + xl_col_to_name(column)
            newFormula = newFormula.replace(columnHeader, newcolumnHeader)
    return newFormula

### Coordinates for the lowest left corner of the lowest leftmost sector that matters

galaxyX = int(-44865)
galaxyY = int(-3865)
galaxyZ = int(-18985)

# def export_data():

workbook = xlsxwriter.Workbook('journal.xlsx', {'strings_to_numbers': True})

main = workbook.add_worksheet('main')
main.set_column("A:A",26)
mainRow = 1
main.freeze_panes(1,1)


main.write(0,0,"Object Type") # write 0,col,header
# mainRow += 1
for mainObj in table_stars:
    mainCol = 0
    main.write(mainRow,mainCol,mainObj) # write row,col,objectname

    # print(mainRow,mainCol,mainObj)
    for formulas in object_formulas:
        mainCol += 1
        main.write(0,mainCol,formulas["FormulaType"])
        main.write_array_formula(mainRow, mainCol, mainRow, mainCol,header2column(formulas["default"]).format(mainRow+1))

        print(formulas["FormulaType"],header2column(formulas["default"]))

        if "(Terraformable)" in mainObj:
            main.write_array_formula(mainRow, mainCol, mainRow, mainCol,header2column(formulas["terraformable"]).format(mainRow))
        if "(Landable)" in mainObj:
            if mainObj == "Icy body (Landable)" or mainObj == "Rocky ice body (Landable)":
                main.write_array_formula(mainRow, mainCol, mainRow, mainCol, header2column(formulas["landable"]).format(mainRow))
            else:
                main.write_array_formula(mainRow, mainCol, mainRow, mainCol, header2column(formulas["landable"]).format(mainRow-1))


    # print(max(table_body,key=))
    mainRow += 1


# for mainObj in table_stars:
#     print(mainObj)
#     for formulas in object_formulas:
#         print(formulas["FormulaType"],"1",formulas["default"])
#         print(header2column(formulas["default"]))
        # newFormula = formulas["default"]
        # for columnHeader in re.findall("\$(\w+)", newFormula):
        #     for column in [column for column, columnName in enumerate(table_body) if columnName == columnHeader]:
        #         newcolumnHeader = xl_col_to_name(column) + ":$" + xl_col_to_name(column)
        #         newFormula = newFormula.replace(columnHeader, newcolumnHeader)
        # print(formulas["FormulaType"],"2",newFormula)

# testFormula = r'COUNTIFS(objects!$Object,$A{0:d})'
#
# print("1",testFormula)
# for columnHeader in re.findall("\$(\w+)",testFormula):
#     print(columnHeader)
#     for column in [column for column,columnName in enumerate(table_body) if columnName == columnHeader]:
#         newcolumnHeader = xl_col_to_name(column)+":$"+xl_col_to_name(column)
#         print(xl_col_to_name(column))
#         print(newcolumnHeader)
#         testFormula = testFormula.replace(columnHeader,newcolumnHeader)
# print("2",testFormula)
# columnHeader = re.findall("\[(\w+)]",testFormula)
# print("The columnheader is ",columnHeader)
#
# for columnHead in columnHeader:
#     print(columnHead)
#     columnLetter = list()
#     for column in [column for column,columnName in enumerate(table_body) if columnName == columnHead]:
#         columnLetter.append(xl_col_to_name(column))
        # print(xl_col_to_name(column))

# newFormula = re.sub(columnHeader,testFormula,columnLetter)
# print(testFormula)
# print(newFormula)

# print("The columnheader is ",columnHeader.group(1))
# # for column in table_body:
# #     if columnHeader == column:
# #         columnLetter =
# print(table_body.count(columnHeader.group(1)))
# formulaColumn = xl_col_to_name(table_body.count(columnHeader.group(1)))
# print(formulaColumn)

# for column in [column for column,columnName in enumerate(table_body) if columnName == columnHeader.group(1)]:
#     print(xl_col_to_name(column))




sectors = workbook.add_worksheet('sectors')
sectors.freeze_panes(1,1)
sectors.set_column("A:A",16)

boxels = workbook.add_worksheet('boxels')
boxels.freeze_panes(1,1)
boxels.set_column("A:A",26)
boxels.set_column("E:E",16)

systems = workbook.add_worksheet('systems')
systems.freeze_panes(1,1)
systems.set_column("A:A",28)
systems.set_column("B:B",20)
systems.set_column("E:F",20)
systems.set_column("G:G",26)

objects = workbook.add_worksheet('objects')
objects.freeze_panes(1,1)
objects.set_column("A:A",30)
objects.set_column("B:B",20)
objects.set_column("E:F",28)
objects.set_column("H:H",14)
objects.set_column("I:I",30)
objects.set_column("J:AD",13)
objects.set_column("AH:AH",36)
objects.set_column("AI:AK",13)
objects.set_column("AP:AP",36)
objects.set_column("AQ:AT",13)
objects.set_column("AU:CF",10)


gps = workbook.add_worksheet('gps')
gps.freeze_panes(1,1)
# gps.set_default_row(97)
gps.set_column("A:A",30)
gps.set_column("B:B",18)
# gps.set_column("C:C",18)
gps.set_column("C:D",11)
# gps.set_column("I:I",42)
helper = workbook.add_worksheet('helper')
helperRow = 0
for formula in helper_formulas:
    # print(formula,helper_formulas[formula])
    helper.write(helperRow,0,formula)
    helper.write(helperRow,1,helper_formulas[formula])
    helperRow+=1


row = 0
col = 0

def search(values, searchFor):
    for k in values:
        if searchFor in values[k][1] and len(searchFor) == len(values[k][1]):
            return True
    return False

def objectClass(objtype, object):
    if objtype == "Star":
        if re.search("^O$|^B$|^A$|^F$|^G$|^K$|^M$|^A[_]|^F[_]|^K[_]|^M[_]",object):
            return "Main Sequence"
        elif re.search("L$|T$|Y$", object):
            return "Brown Dwarf"
        # elif re.search("[^H$|^N$|^D$|^D[A|B|C|Q]]|^SupermassiveBlackHole$", object):
        elif re.search("^H$|^N$|^D$|^D[A|B|C|Q]|^SupermassiveBlackHole$", object):
            return "Remnant"
        elif re.search("^TTS$|^AeBe$", object):
            return "Proto"
        elif re.search("^C$|S$|C[J|N|]$", object):
            return "Carbon"
        elif re.search("^W$|^WC$||^WN$|^WNC$|^WO$", object):
            return "Wolf-Rayet"
    elif objtype == "Planet":
        if re.search("[G|g]as", object):
            return "Gas Giant"
        if re.search("[body|world]", object):
            return "Terrestrial"
    else:
        pass

def volcanoRegex(volcanism):
    volcano = list()
    regex = r"(major+|minor+)?\s?(ammonia+|silicate vapour+|carbon dioxide+|metallic+|methane+|nitrogen+|water+|rocky+)?\s?(magma+|geysers+)"
    volcanovals = re.finditer(regex,volcanism)
    for volcanonum, volcanoval in enumerate(volcanovals):
        volcano.append(volcanoval.group(1))
        volcano.append(volcanoval.group(2))
        volcano.append(volcanoval.group(3))

    return volcano

def atmosphereRegex(atmosphereIN):
    atmosphere = list()

    regex = r"(hot+|)?\s?(thick+|thin+|)?\s?(ammonia+|argon+|neon+|helium+|methane+|nitrogen+|oxygen+|metallic vapour+|sulfur dioxide+|sulphur dioxide+|carbon dioxide+|silicate vapour+|water+|)?\s?(rich+|)? atmosphere$"

    atmospherevals = re.finditer(regex,atmosphereIN)
    for atmosphereNum, atmosphereVal in enumerate(atmospherevals):
        atmosphere.append(atmosphereVal.group(1))
        atmosphere.append(atmosphereVal.group(2))
        atmosphere.append(atmosphereVal.group(3))
        atmosphere.append(atmosphereVal.group(4))

    return atmosphere

# def objectParent(object):
#     objParent = str()
#
#     if

def systemRegex(boxelname):
    boxelvals = list()

    if re.search("\s[A-Za-z]{2}-[A-Za-z]\s",boxelname):
        if re.search("\w\d+\-\d+", boxelname):
            regex = r"(([\w\s'.()/-]+) ([A-Za-z]{2}-[A-Za-z]) ([a-h])(\d+))-(\d+)"
        else:
            regex = r"(([\w\s'.()/-]+) ([A-Za-z]{2}-[A-Za-z]) ([a-h]))()(\d+)"

        boxelvals.append(boxelname)
        boxels = re.finditer(regex, boxelname)
        for boxelNum, boxel in enumerate(boxels):

            boxelname = boxel.group(1)
            boxelvals.append(boxelname)
            boxelname = boxel.group(2)
            boxelvals.append(boxelname)
            boxelname = boxel.group(3)
            boxelvals.append(boxelname)
            boxelname = boxel.group(4)
            boxelvals.append(boxelname)
            boxelname = boxel.group(5)
            boxelvals.append(boxelname)
            boxelname = boxel.group(6)
            boxelvals.append(boxelname)
            boxelname = ""
            boxelvals.append(boxelname)

    else:
        # print("HA boxel is",boxelname)
        # print("But PG it's called: ",system.from_name(boxelname).pg_name)
        # PGName = system.from_name(boxelname).pg_name
        PGName = "idunnowhattocallit td-d d"

        if re.search("\w\d+\-\d+", PGName):
            regex = r"(([\w\s'.()/-]+) ([A-Za-z]{2}-[A-Za-z]) ([a-h])(\d+))-(\d+)"
        else:
            regex = r"(([\w\s'.()/-]+) ([A-Za-z]{2}-[A-Za-z]) ([a-h]))()(\d+)"

        boxelvals.append(boxelname)
        boxels = re.finditer(regex, PGName)

        for boxelNum, boxel in enumerate(boxels):

            boxelname = boxel.group(1)
            boxelvals.append(boxelname)
            boxelname = boxel.group(2)
            boxelvals.append(boxelname)
            boxelname = boxel.group(3)
            boxelvals.append(boxelname)
            boxelname = boxel.group(4)
            boxelvals.append(boxelname)
            boxelname = boxel.group(5)
            boxelvals.append(boxelname)
            boxelname = boxel.group(6)
            boxelvals.append(boxelname)
            boxelname = "x"
            boxelvals.append(boxelname)

    return boxelvals

    ##### Helium GG basically non-existant within 6000 or so ly of galactic centre. What else stops at around that point?

    ### So maybe make this take the HA systems and give them the correct sector and
    ### generic boxel on down for now? Can refine this as I get the subsector codes
    ### translated into Python

def listdecomp(key,value):
    tempdict = dict()
    tempdict[key] = value

    return tempdict

def mass2size(value):
    masscode = {"a":10,"b":20,"c":40,"d":80,"e":160,"f":320,"g":640,"h":1280}
    return masscode[value]

dict_sectors = {}
dict_boxels = {}
dict_systems = {}
dict_objects = {}
dict_rings = {}

boxelname_obj = str()
systemprimarystar = str()
# systemBodies = int()
previousbodies = int()
systemBodiesAddress = int()
systemBodiesTime = ""
systemBodies = dict()
# discoveryscandelay = 1

size = 200, 200

for filename in glob.glob(jdir):
    with jsonlines.open(filename) as reader:
        for lineA in reader.iter(type=dict, skip_invalid=True):
            if lineA.get("event", None) == "DiscoveryScan":
                bodyCount = lineA["Bodies"]
                if lineA["SystemAddress"] in systemBodies:
                    systemBodies[lineA["SystemAddress"]] = systemBodies[lineA["SystemAddress"]] + bodyCount
                else:
                    systemBodies[lineA["SystemAddress"]] = bodyCount

gps.write_row(0,0,table_gps)
gpscol = 0
gpsrow = 1

for filename in glob.glob(jdir):
    with jsonlines.open(filename) as reader:
        for line in reader.iter(type=dict, skip_invalid=True):
            gpscol = 0
            if line.get("event", None) == "SupercruiseExit":
                localBody = line["Body"]

            if line.get("event", None) == "Touchdown" and line.get("PlayerControlled", None) == True:
                # print("touchdown",localBody,line.keys(),type(line))
                gpsline = list()
                # gpsline.append("")
                gpsline.append(localBody)
                gpsline.append(line["timestamp"])
                # gpsline.append(line["event"])
                gpsline.append(line["Latitude"])
                gpsline.append(line["Longitude"])
                # gps.write(gpsrow,gpscol,localBody)
                # gpscol += 1
                gps.write_row(gpsrow, gpscol, gpsline)
                gpsrow += 1
                gpscol = 1

            if line.get("event", None) == "StartJump":
                if line["JumpType"] == "Hyperspace":
                    systemprimarystar = line["StarClass"]
                else:
                    pass

            if line.get("event", None) == "FSDJump" or line.get("event", None) == "Location":

                sectorvalues = list()
                boxelvalues = list()
                systemvalues = list()
                boxelcontents = list()

                syscoordinates = line["StarPos"]

                ### Actual System Coordinates

                sysX = syscoordinates[0]
                sysY = syscoordinates[1]
                sysZ = syscoordinates[2]

                ### Sector LLC Coordinates

                secX = (galaxyX - int((galaxyX - sysX) / 1280) * 1280)
                secY = (galaxyY - int((galaxyY - sysY) / 1280) * 1280)
                secZ = (galaxyZ - int((galaxyZ - sysZ) / 1280) * 1280)

                # print(system.from_name(line["StarSystem"]).pg_name)
                boxelvals = systemRegex(line["StarSystem"])

                sectorvalues.append((secX,secY,secZ))

                boxelname_obj = ""

                if len(boxelvals) > 1:
                    boxelname_obj = boxelvals[1]
                    if boxelvals[2] not in dict_sectors:
                        dict_sectors[boxelvals[2]] = {}
                        dict_sectors[boxelvals[2]]["coordinates"] = sectorvalues
                        dict_sectors[boxelvals[2]]["boxels"] = {}

                    if boxelvals[1] not in dict_sectors[boxelvals[2]]["boxels"]:
                        boxelcoordinates = list()
                        systemnestedBoxels = list()
                        boxelnestedBoxels = list()

                        if boxelvals[5] is not "":
                            boxelvals[5] = int(boxelvals[5])
                        dict_sectors[boxelvals[2]]["boxels"][boxelvals[1]] = {}
                        dict_sectors[boxelvals[2]]["boxels"][boxelvals[1]]["systems"] = {}


                        if boxelvals[4] is not "":
                            boxelsize = mass2size(boxelvals[4])

                        ### Boxel LLC Coordinates

                        boxX = secX + (int((sysX - secX) / boxelsize) * boxelsize)
                        boxY = secY + (int((sysY - secY) / boxelsize) * boxelsize)
                        boxZ = secZ + (int((sysZ - secZ) / boxelsize) * boxelsize)

                        ### Legacy test code. Not quite ready to delete

                        # aBox1 = chr(int(math.fmod((math.floor(abs(secX - sysX / 80)+((math.floor(abs(secY - sysY) / 80))* 128)+((math.floor(abs(secZ - sysZ) / 80))* pow(128,2)))),26)+65))
                        # aBox2 = chr(int(math.fmod((math.floor(abs(secX - sysX / 80)+((math.floor(abs(secY - sysY) / 80))* 128)+((math.floor(abs(secZ - sysZ) / 80))* pow(128,2)))/26),26)+65))
                        # aBox3 = chr(int(math.fmod((math.floor(abs(secX - sysX / 80)+((math.floor(abs(secY - sysY) / 80))* 128)+((math.floor(abs(secZ - sysZ) / 80))* pow(128,2)))/pow(26,2)),26)+65))

                        for masscode,lycubeSize in {"g":640,"f":320,"e":160,"d":80,"c":40,"b":20,"a":10}.items():
                            singleBoxel = str()
                            massposcode = ""
                            allBoxX = math.floor(abs(secX - sysX) / lycubeSize)
                            allBoxY = math.floor(abs(secY - sysY) / lycubeSize) * 128
                            allBoxZ = math.floor(abs(secZ - sysZ) / lycubeSize) * pow(128,2)
                            mcodeMod = int((allBoxX + allBoxY + allBoxZ) / pow(26, 3))
                            if mcodeMod == 0:
                                massandpos = (" ",masscode)
                                massposcode = massposcode.join(massandpos)
                            else:
                                massandpos = (" ",masscode,str(mcodeMod))
                                massposcode = massposcode.join(massandpos)
                            singleBoxel = singleBoxel.join(((chr(int(math.fmod(allBoxX + allBoxY + allBoxZ,26)) + 65)),(chr(int(math.fmod(int((allBoxX + allBoxY + allBoxZ) / 26),26)) + 65)),"-",(chr(int(math.fmod(int((allBoxX + allBoxY + allBoxZ) / pow(26,2)),26))+65)),massposcode))
                            systemnestedBoxels.append(singleBoxel)
                            if lycubeSize >= boxelsize:
                                boxelnestedBoxels.append(singleBoxel)
                            else:
                                boxelnestedBoxels.append("")

                        boxelcoordinates.append((boxX,boxY,boxZ))
                        boxelvalues.append((boxelvals[2],boxelvals[3],boxelvals[4],boxelvals[5],(*boxelnestedBoxels)))
                        dict_sectors[boxelvals[2]]["boxels"][boxelvals[1]]["coordinates"] = list(boxelcoordinates)
                        dict_sectors[boxelvals[2]]["boxels"][boxelvals[1]]["contents"] = boxelvalues

                    if boxelvals[0] not in dict_sectors[boxelvals[2]]["boxels"][boxelvals[1]]["systems"]:
                        systemcoordinates = list()
                        dict_sectors[boxelvals[2]]["boxels"][boxelvals[1]]["systems"][boxelvals[0]] = {}

                        systemvalues.append(line["timestamp"])

                        systemAddress = int()

                        if "SystemAddress" in line:
                            # print(boxelvals[0],line["SystemAddress"])
                            # if line["SystemAddress"] == systemBodiesAddress:


                            systemvalues.append(line["SystemAddress"])
                            systemvalues.append(boxelvals[1])
                            systemvalues.append(boxelvals[7])
                            systemvalues.append(systemprimarystar)
                            if line["SystemAddress"] in systemBodies:
                                systemvalues.append(systemBodies[line["SystemAddress"]])
                                # print(systemBodies[line["SystemAddress"]])
                            else:
                                systemvalues.append("")
                                systemvalues.append("")
                            # systemAddress = line["SystemAddress"]
                            # print("sysadd from systembodies is ",systemBodiesAddress, "and sysadd from system is ", line["SystemAddress"])
                            # print(systemBodiesTime, " = ", line["timestamp"])
                            # print(boxelvals[0], "has the following bodycount:", systemBodies)
                        else:
                            systemvalues.append("")
                            systemvalues.append(boxelvals[1])
                            systemvalues.append(boxelvals[7])
                            systemvalues.append(systemprimarystar)
                            systemvalues.append("")

                        systemvalues = systemvalues + systemnestedBoxels
                        singlesystem = list()
                        systemcoordinates.append((sysX,sysY,sysZ))
                        dict_sectors[boxelvals[2]]["boxels"][boxelvals[1]]["systems"][boxelvals[0]]["coordinates"] = list(systemcoordinates)
                        dict_sectors[boxelvals[2]]["boxels"][boxelvals[1]]["systems"][boxelvals[0]]["contents"] = systemvalues

                else:
                    ### This needs LOTS of work and is generating bad results.

                    # Here is where we work out the actual sector for named systems... it's a work in progress.
                    actualhasector = getSector(sysX,sysY,sysZ)

                    HAsystem = boxelvals[0]

            if line.get("event", None) == "Scan" and "Cluster" not in line.get("BodyName"):
                if "Cluster" in line.get("BodyName"):
                    print("Clusterfuck in ",line.get("BodyName"))
                if "Belt" in line.get("BodyName"):
                    print("Belt in ",line.get("BodyName"))



                objectvalues = list()
                ringvalues = list()
                dict_singleobject = dict()
                dict_atmosphere = dict()
                objvals = list()

                for objectkey in table_body:
                    if objectkey == "BodyName":
                        bodyname = line[objectkey]
                        dict_objects[bodyname] = {}
                    elif objectkey is not "BodyName":
                        if objectkey == "BoxelName":
                            if len(boxelvals) > 1:
                                dict_singleobject["BoxelName"] = boxelvals[1]
                            else:
                                dict_singleobject["BoxelName"] = ""
                        elif objectkey == "BoxelCode":
                            if len(boxelvals) > 1:
                                dict_singleobject["BoxelCode"] = boxelvals[4]
                            else:
                                dict_singleobject["BoxelCode"] = ""
                        elif objectkey == "SystemName":
                            dict_singleobject["SystemName"] = boxelvals[0]
                        elif objectkey == "Remainder":
                            if bodyname == boxelvals[0]:
                                systemSpace = boxelvals[0]
                                remainder = ""
                            else:
                                systemSpace = boxelvals[0]+" "
                                remainder = str(bodyname).replace(systemSpace,"")
                            # print(boxelvals[0])
                            # print("The pre-remainder is: ", remainder)
                            # rem = re.match("([A-Z]+)",remainder)

                            # sep = " "
                                remainder = remainder.split(" ", 1)[0]
                            if remainder.isdigit():
                                remainder = "A"
                            elif str(bodyname).endswith("Belt"):
                                remainder = remainder
                                print(bodyname,remainder)
                            elif bodyname == systemSpace+remainder:
                                print("Remainder ",systemSpace+remainder,"is identical to ",bodyname)
                                remainder = "P"
                            print(bodyname,"The pre-remainder is: ", remainder)


                            # if remainder.isdigit():
                            #     remainder = "A"

                            # print("The remainder is: ", remainder2)
                            # print("The REGEX version is: ",rem)


                            dict_singleobject["Remainder"] = remainder

                        # elif objectkey == "objCorrected":
                        #     dict_singleobject["objCorrected"] = filename
                        elif objectkey == "oType":
                            if "StarType" in line.keys():
                                dict_singleobject["oType"] = "Star"
                                dict_singleobject["oClass"] = objectClass("Star", line["StarType"])
                                # print(line["StarType"],dict_singleobject["oClass"])
                                dict_singleobject["Object"] = line["StarType"]
                                ### If object is main sequence, check temperature and add entry into corrected
                            elif "PlanetClass" in line.keys():
                                dict_singleobject["oType"] = "Planet"
                                dict_singleobject["oClass"] = objectClass("Planet",line["PlanetClass"])
                                dict_singleobject["Object"] = line["PlanetClass"]
                            else:
                                dict_singleobject["oType"] = "Unknown - Belt?"
                                dict_singleobject["oClass"] = "COMINGSOON"
                                dict_singleobject["Object"] = "Unknown"
                        elif objectkey == "Object" or objectkey == "oClass":
                            pass
                        elif objectkey == "MassMT":
                            density = float()
                            if "StellarMass" in line.keys():
                                massSolar = float(line["StellarMass"])
                                # masskg = str("Mass")
                                massMT = massSolar * 1.9891E+21
                                # massMT = str("MassMT")
                                dict_singleobject["MassMT"] = massMT
                                dict_singleobject["Mass"] = massSolar
                            elif "MassEM" in line.keys():
                                massEM = float(line["MassEM"])
                                # masskg = str("Mass")
                                massMT = massEM * 5.9722E+15
                                # masskg = str("MassMT")
                                dict_singleobject["MassMT"] = massMT
                                dict_singleobject["Mass"] = massEM
                            else:
                                pass
                            density = (massMT / ((4/3) * math.pi * math.pow(line["Radius"],3))) * 1000000000
                            # print(bodyname, density,line["Radius"])
                            dict_singleobject["Density"] = density
                        elif objectkey == "OrbitalVelocity":
                            if "SemiMajorAxis" in line:
                                velocity = ((2 * math.pi * line["SemiMajorAxis"]) / line["OrbitalPeriod"])/1000
                                dict_singleobject["OrbitalVelocity"] = velocity
                                # print(bodyname,"travels at ",velocity)
                            else:
                                dict_singleobject["OrbitalVelocity"] = ""

                        elif objectkey == "barycentre":
                            if "Parents" in line.keys():
                                bary = list(line["Parents"][0].values())
                                dict_singleobject["barycentre"] = bary.pop()
                            else:
                                dict_singleobject["barycentre"] = ""

                        # elif objectkey == "isItHA":
                        #     if boxelvals[7] == "x":
                        #         dict_singleobject["isItHA"] = "x"
                        #     else:
                        #         dict_singleobject["isItHA"] = ""

                        elif objectkey == "Volcanism":
                            if objectkey in line and line[objectkey] is not "":
                                volcanisms = volcanoRegex(line[objectkey])

                                dict_singleobject["Volcanism"] = line[objectkey]
                                dict_singleobject["vLevel"] = volcanisms[0]
                                dict_singleobject["vMaterial"] = volcanisms[1]
                                dict_singleobject["vType"] = volcanisms[2]
                            else:
                                dict_singleobject["Volcanism"] = ""
                                dict_singleobject["vLevel"] = ""
                                dict_singleobject["vMaterial"] = ""
                                dict_singleobject["vType"] = ""

                        elif objectkey == "Composition":
                            # print(line["Composition"],type(line["Composition"]))
                            if "Composition" in line:
                                if line["Composition"] == {}:
                                    dict_singleobject["Composition"] = ""
                                    dict_singleobject["Ice"] = ""
                                    dict_singleobject["Rock"] = ""
                                    dict_singleobject["Metal"] = ""
                                else:
                                    dict_singleobject["Composition"] = ""
                                    dict_singleobject["Ice"] = line["Composition"]["Ice"]
                                    dict_singleobject["Rock"] = line["Composition"]["Rock"]
                                    dict_singleobject["Metal"] = line["Composition"]["Metal"]
                                # print(dict_singleobject["Ice"])
                            else:
                                dict_singleobject["Composition"] = ""
                                dict_singleobject["Ice"] = ""
                                dict_singleobject["Rock"] = ""
                                dict_singleobject["Metal"] = ""

                        elif objectkey == "Atmosphere":
                            if objectkey in line and line[objectkey] is not "":
                                atmosisms = atmosphereRegex(line[objectkey])

                                dict_singleobject["Atmosphere"] = line[objectkey]
                                dict_singleobject["aTemp"] = atmosisms[0]
                                dict_singleobject["aDensity"] = atmosisms[1]
                                dict_singleobject["aElements"] = atmosisms[2]
                                dict_singleobject["aRich"] = atmosisms[3]

                            else:
                                dict_singleobject["Atmosphere"] = ""
                                dict_singleobject["aTemp"] = ""
                                dict_singleobject["aDensity"] = ""
                                dict_singleobject["aElements"] = ""
                                dict_singleobject["aRich"] = ""

                        elif objectkey == "Ring":
                            if "Rings" in line:
                                if "Belt" in line["Rings"][0]["Name"]:
                                    # print("It's a belt!")
                                # print(line["Rings"])
                                # dict_singleobject["Ring"] = "x"
                                    dict_singleobject["Ring"] = ""
                                elif "Ring" in line["Rings"][0]["Name"]:
                                    # print("It's a RING!!!!!!")
                                    dict_singleobject["Ring"] = "x"
                                else:
                                    dict_singleobject["Ring"] = ""
                            else:
                                dict_singleobject["Ring"] = ""

                        elif objectkey not in line and objectkey != "BoxelName" and objectkey is not "isItHA" and objectkey is not "Density" and objectkey is not "Remainder" and objectkey is not "Mass" and objectkey is not "Rings" and objectkey is not "Ice"and objectkey is not "Rock"and objectkey is not "Metal" and objectkey is not "vLevel" and objectkey is not "vMaterial" and objectkey is not "vType" and objectkey is not "aTemp" and objectkey is not "aDensity" and objectkey is not "aElements" and objectkey is not "aRich":
                            # print(dict_singleobject["Ice"])
                            dict_singleobject[objectkey] = ""
                            # print(dict_singleobject["Ice"])
                        else:
                            if objectkey in line and objectkey is not "Remainder" and objectkey is not "Mass" and objectkey is not "vLevel" and objectkey is not "vMaterial" and objectkey is not "vType" and objectkey is not "Ice"and objectkey is not "Rock"and objectkey is not "Metal":
                                dict_singleobject[objectkey] = line[objectkey]

                if "AtmosphereComposition" in line:
                    for gasType in table_atmosphere:
                        for atmosphereGasElement in line["AtmosphereComposition"]:
                            if gasType == atmosphereGasElement["Name"]:
                                gasPercent = str(atmosphereGasElement["Percent"])
                                dict_atmosphere[gasType] = gasPercent
                        if gasType in dict_atmosphere.keys():
                            pass
                        else:
                            dict_atmosphere[gasType] = ""
                else:
                    for gasType in table_atmosphere:
                        dict_atmosphere[gasType] = ""


                dict_objects[bodyname]["Main"] = dict_singleobject
                dict_objects[bodyname]["Atmosphere"] = dict_atmosphere


                # print(type(dict_objects[bodyname]["Composition"]),dict_objects[bodyname]["Composition"])

                if "Rings" in line:
                    dict_rings = dict()
                    for singlering in line["Rings"]:
                        one_ring = dict()
                        for key in table_body:
                            if key == "BodyName":
                                pass
                            else:
                                one_ring[key] = ""
                        one_ring["timestamp"] = dict_singleobject["timestamp"]
                        one_ring["BoxelName"] = dict_singleobject["BoxelName"]
                        one_ring["BoxelCode"] = dict_singleobject["BoxelCode"]
                        one_ring["SystemName"] = dict_singleobject["SystemName"]
                        # one_ring["Remainder"] = dict_singleobject["Remainder"]
                        one_ring["barycentre"] = dict_singleobject["BodyID"]
                        # one_ring["IsItHA"] = dict_singleobject["isItHA"]

                        ringclass = singlering["RingClass"].replace("eRingClass_","")
                        if ringclass == "MetalRich":
                            ringclass = "Metal rich"

                        # if "Belt" in singlering["Name"]:
                        #     remainder = str(bodyname).replace(boxelvals[0]+" ", "")
                        #     if remainder == "":
                        #         remainder = "A"
                        #     one_ring["Remainder"] = remainder

                            # print(bodyname)
                            # print("belt remainder:",remainder)
                            one_ring["oType"] = "Belt"
                            ringclass = ringclass + " belt"
                            one_ring["oClass"] = "Belt"
                        else:
                            one_ring["oType"] = dict_singleobject["oType"]
                            ringclass = ringclass + " ring"
                            one_ring["oClass"] = dict_singleobject["oClass"]
                            # one_ring["oChild"] = "Ring"

                        one_ring["Object"] = ringclass
                        one_ring["MassMT"] = singlering["MassMT"]
                        one_ring["InnerRadius"] = singlering["InnerRad"]
                        one_ring["Radius"] = singlering["OuterRad"]

                        dict_objects[singlering["Name"]] = {}
                        dict_objects[singlering["Name"]]["Main"] = one_ring
                        dict_objects[singlering["Name"]]["Composition"] = {}
                        dict_objects[singlering["Name"]]["Atmosphere"] = {}

                if "Materials" in line:
                    dict_mats = dict()
                    matkeys = line.get("Materials")
                    ## Collect the materials as they were recorded in the journals prior to
                    ## 2017-04-11 (2.2 release? Or was it 2.3??)
                    if isinstance(line.get("Materials"), dict):
                        for mat in table_materials:
                            if mat not in matkeys:
                                dict_mats[mat] = ""
                            else:
                                matvalue = str(matkeys[mat])
                                dict_mats[mat] = matvalue
                    elif isinstance(line.get("Materials"), list):
                        materials = list(table_materials)
                        for i in range(len(list(table_materials))):
                            for j in range(len(list(matkeys))):
                                if materials[i] == matkeys[j]['Name']:
                                    dict_mats[materials[i]] = matkeys[j]['Percent']
                                    mathelper = matkeys[j]['Name']
                            if materials[i] != mathelper:
                                dict_mats[materials[i]] = ""
                    dict_objects[bodyname]["Materials"] = dict_mats

row = 0
col = 0

boxrow = 0
boxcol = 0

sysrow = 0
syscol = 0

objrow = 0
objcol = 0

ringrow = 0
ringcol = 0

sectors.write_row(row, col, table_sectors)
systems.write_row(row, col, table_systems)
boxels.write_row(row, col, table_boxels)
lastBoxcol = len(table_boxels)-1

print("Adding all scanned bodies.")
objects.write_row(objrow, objcol, (table_body + table_atmosphere + table_materials))
for objkey in dict_objects:
    objcol = 0
    objrow += 1
    objects.write(objrow,objcol,str(objkey))
    objcol += 1
    objectattributes = list(dict_objects[objkey]["Main"].values())
    # print(dict_objects[objkey])
    # if dict_objects[objkey]["Composition"] == {}:
    #     pass
    # else:
    #     CompositionAttributes = list(dict_objects[objkey]["Composition"])
    #     print(type(CompositionAttributes),CompositionAttributes)
    #     objectattributes = objectattributes + CompositionAttributes
    if dict_objects[objkey]["Atmosphere"] == {}:
        pass
    else:
        atmosphereAttributes = list(dict_objects[objkey]["Atmosphere"].values())
        objectattributes = objectattributes + atmosphereAttributes
    matsline = dict_objects[objkey].get("Materials")
    if matsline == None:
        pass
    else:
        materialAttributes = list(dict_objects[objkey]["Materials"].values())
        objectattributes = objectattributes + materialAttributes

    objects.write_row(objrow, objcol, objectattributes)
    objcol += 1
print("Adding Sectors, Boxels, and Systems")
for sector in sorted(dict_sectors):
    sectsysCount = 0
    col = 0
    row += 1
    sectors.write(row,col,sector)
    col += 1
    sectboxCount = len(dict_sectors[sector]["boxels"])
    sectorcoordinates = list(*dict_sectors[sector]["coordinates"])
    sectorcoordinates.append(sectboxCount)
    for boxkey in sorted(dict_sectors[sector]["boxels"]):
        boxcount = int()
        boxelinfo = list()
        boxelinfo = list(*dict_sectors[sector]["boxels"][boxkey]["coordinates"])
        boxelinfo.append(*dict_sectors[sector]["boxels"][boxkey]["contents"])
        boxcount = len(dict_sectors[sector]["boxels"][boxkey]["systems"].keys())
        sectsysCount = sectsysCount + boxcount
        boxelinfo.append(boxcount)
        # print("Number of systems in ",boxkey,"is",boxcount)
        boxcol = 0
        boxrow += 1
        boxels.write(boxrow,boxcol,str(boxkey))
        boxcol += 1
        for boxcrap in boxelinfo:
            if isinstance(boxcrap,tuple):
                for boxelDetails in boxcrap:
                    boxels.write(boxrow,boxcol,boxelDetails)
                    boxcol += 1
            else:
                boxels.write(boxrow,boxcol,boxcrap)
                boxcol += 1

        syscol = 0
        for syskey in dict_sectors[sector]["boxels"][boxkey]["systems"]:
            systeminfo = list(*dict_sectors[sector]["boxels"][boxkey]["systems"][syskey]["coordinates"])
            systeminfo = systeminfo + dict_sectors[sector]["boxels"][boxkey]["systems"][syskey]["contents"]
            syscol = 0
            sysrow += 1
            systems.write(sysrow,syscol,str(syskey))
            syscol += 1

            for syscrap in systeminfo:
                if isinstance(syscrap, tuple):
                    for systemDetails in syscrap:
                        systems.write(sysrow, syscol, systemDetails)
                        syscol += 1
                else:
                    systems.write(sysrow, syscol, syscrap)
                    syscol += 1
    sectorcoordinates.append(sectsysCount)
    sectors.write_row(row, col, (sectorcoordinates))

        # systems.write_formula(sysrow,syscol,'=IFERROR(AVERAGEIFS(objects!AZ$2:AZ${},objects!$A$2:$A${},$A{}&"*",objects!$H$2:$H${},"Gas Giant"),"")'.format(objrow,objrow,sysrow+1,objrow))
        # boxels.write_formula(boxrow,lastBoxcol,'=IFERROR(AVERAGEIFS(objects!AZ$2:AZ${},objects!$A$2:$A${},$A{}&"*",objects!$H$2:$H${},"Gas Giant"),"")'.format(objrow,objrow,boxrow+1,objrow))



workbook.close()