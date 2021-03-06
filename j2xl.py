# from __future__ import print_function
#
import glob
import os
import math
# import sys
# import time
# import webbrowser
import re
# from time import gmtime
# from string import ascii_uppercase
#
# import Tkinter as tk
# import myNotebook as nb
# from config import config

from allSectors import getSector
import jsonlines
import xlsxwriter

jdir = os.environ['USERPROFILE'] + os.path.join("\\Saved Games\\Frontier Developments\\Elite Dangerous\\journal.*.log")


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
    "BoxelName",
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
    "Luminosity",
    "barycentre",
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
    "SecZ"
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
    "",
    "HeliumAverage"
)

table_systems = (
    "StarSystem",
    "SysX",
    "SysY",
    "SysZ",
    "timestamp",
    "SystemAddress",
    "isProcGen",
    "PrimaryStarType",
    "G",
    "F",
    "E",
    "D",
    "C",
    "B",
    "A"
)

### Coordinates for the lowest left corner of the lowest leftmost sector that matters

galaxyX = int(-44865)
galaxyY = int(-3865)
galaxyZ = int(-18985)

# def export_data():

workbook = xlsxwriter.Workbook('journal.xlsx', {'strings_to_numbers': True})
main = workbook.add_worksheet('main')
sectors = workbook.add_worksheet('sectors')
boxels = workbook.add_worksheet('boxels')
systems = workbook.add_worksheet('systems')
objects = workbook.add_worksheet('objects')
helper = workbook.add_worksheet('helper')

row = 0
col = 0

def search(values, searchFor):
    for k in values:
        # print("V is",values[k][1])
        # print("searchFor - ",searchFor)
        if searchFor in values[k][1] and len(searchFor) == len(values[k][1]):
            # print(searchFor,values[k][1],"IT'S A DUP!")
            return True
    return False

def objectClass(objtype, object):
    if objtype == "Star":
        if re.search("O$|B$|A$|F$|G$|K$|M$|A[_]|F[_]|K[_]|M[_]",object):
            return "Main Sequence"
        elif re.search("L$|T$|Y$", object):
            return "Brown Dwarf"
        elif re.search("H$|N$|D$|D[A|B|C|Q]|SupermassiveBlackHole$", object):
            return "Remnant"
        elif re.search("TTS$|AeBe$", object):
            return "Proto"
        elif re.search("C$|S$|C[J|N|]$", object):
            return "Carbon"
        elif re.search("W$|W[C|N|O]", object):
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
        actualhasector = getSector(sysX, sysY, sysZ)
        boxelvals.append(boxelname)
        boxelname = ""
        boxelvals.append(boxelname)
        boxelname = actualhasector
        boxelvals.append(boxelname)
        boxelname = ""
        boxelvals.append(boxelname)
        boxelname = ""
        boxelvals.append(boxelname)
        boxelname = ""
        boxelvals.append(boxelname)
        boxelname = ""
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

for filename in glob.glob(jdir):
    with jsonlines.open(filename) as reader:
        for line in reader.iter(type=dict, skip_invalid=True):
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

                boxelvals = systemRegex(line["StarSystem"])
                syscoordinates = line["StarPos"]

                ### Actual System Coordinates

                sysX = syscoordinates[0]
                sysY = syscoordinates[1]
                sysZ = syscoordinates[2]

                ### Sector LLC Coordinates

                secX = (galaxyX - int((galaxyX - sysX) / 1280) * 1280)
                secY = (galaxyY - int((galaxyY - sysY) / 1280) * 1280)
                secZ = (galaxyZ - int((galaxyZ - sysZ) / 1280) * 1280)

                sectorvalues.append((secX,secY,secZ))

                boxelname_obj = ""

                if len(boxelvals) > 1:
                    boxelname_obj = boxelvals[1]
                    if boxelvals[2] not in dict_sectors:
                        dict_sectors[boxelvals[2]] = {}
                        dict_sectors[boxelvals[2]]["coordinates"] = sectorvalues
                        dict_sectors[boxelvals[2]]["boxels"] = {}

                    if boxelvals[1] not in dict_sectors[boxelvals[2]]["boxels"]:
                        if boxelvals[5] is not "":
                            boxelvals[5] = int(boxelvals[5])

                        ### Boxel LLC Coordinates

                        if boxelvals[4] is not "":
                            boxelsize = mass2size(boxelvals[4])
                        boxX = secX + (int((sysX - secX) / boxelsize) * boxelsize)
                        boxY = secY + (int((sysY - secY) / boxelsize) * boxelsize)
                        boxZ = secZ + (int((sysZ - secZ) / boxelsize) * boxelsize)

                        aBox1 = chr(int(math.fmod((math.floor(abs(secX - sysX / 80)+((math.floor(abs(secY - sysY) / 80))* 128)+((math.floor(abs(secZ - sysZ) / 80))* pow(128,2)))),26)+65))
                        aBox2 = chr(int(math.fmod((math.floor(abs(secX - sysX / 80)+((math.floor(abs(secY - sysY) / 80))* 128)+((math.floor(abs(secZ - sysZ) / 80))* pow(128,2)))/26),26)+65))
                        aBox3 = chr(int(math.fmod((math.floor(abs(secX - sysX / 80)+((math.floor(abs(secY - sysY) / 80))* 128)+((math.floor(abs(secZ - sysZ) / 80))* pow(128,2)))/pow(26,2)),26)+65))

                        systemnestedBoxels = list()
                        boxelnestedBoxels = list()
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

                        boxelvalues.append((boxX,boxY,boxZ,boxelvals[2],boxelvals[3],boxelvals[4],boxelvals[5],(*boxelnestedBoxels)))
                        dict_sectors[boxelvals[2]]["boxels"][boxelvals[1]] = boxelcontents
                        boxelcontents.append({"boxelcontents":boxelvalues})

                    if boxelvals[0] not in dict_systems:
                        systemvalues.append(boxelvals[0])
                        systemvalues.append(syscoordinates)
                        systemvalues.append(line["timestamp"])

                        if "SystemAddress" in line:
                            systemvalues.append(line["SystemAddress"])
                        else:
                            systemvalues.append("")

                        systemvalues.append(boxelvals[7])
                        systemvalues.append(systemprimarystar)
                        systemvalues.append(systemnestedBoxels)

                        singlesystem = list()
                        boxelcontents.append({boxelvals[6]:systemvalues})

                        if boxelvals[1] not in boxelvals[0]:
                            dict_systems[boxelvals[1]][boxelvals[0]]
                        dict_sectors[boxelvals[2]]["boxels"][boxelvals[1]]

                else:
                    # Here is where we work out the actual sector for named systems... it's a work in progress.
                    # print(systemvalues[0])
                    # print("Hand Authored:",boxelvals)
                    actualhasector = getSector(sysX,sysY,sysZ)
                    # print("actual sector is",actualhasector)

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
                        elif objectkey == "SystemName":
                            dict_singleobject["SystemName"] = boxelvals[0]
                        # elif objectkey == "objCorrected":
                        #     dict_singleobject["objCorrected"] = filename
                        elif objectkey == "oType":
                            if "StarType" in line.keys():
                                dict_singleobject["oType"] = "Star"
                                dict_singleobject["oClass"] = objectClass("Star", line["StarType"])
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
                            if "StellarMass" in line.keys():
                                masskg = float(line["StellarMass"])
                                masskg = masskg * 1.9891E+21
                                dict_singleobject["MassMT"] = masskg
                            elif "MassEM" in line.keys():
                                masskg = float(line["MassEM"])
                                masskg = masskg * 5.9722E+15
                                dict_singleobject["MassMT"] = masskg
                            else:
                                pass
                        elif objectkey == "barycentre":
                            if "Parents" in line.keys():
                                bary = list(line["Parents"][0].values())
                                dict_singleobject["barycentre"] = bary.pop()
                            else:
                                dict_singleobject["barycentre"] = ""
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

                        elif objectkey not in line and objectkey != "BoxelName"and objectkey is not "Rings" and objectkey is not "vLevel" and objectkey is not "vMaterial" and objectkey is not "vType" and objectkey is not "aTemp" and objectkey is not "aDensity" and objectkey is not "aElements" and objectkey is not "aRich":
                            dict_singleobject[objectkey] = ""
                        else:
                            if objectkey in line and objectkey is not "vLevel" and objectkey is not "vMaterial" and objectkey is not "vType":
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
                        one_ring["barycentre"] = dict_singleobject["BodyID"]

                        ringclass = singlering["RingClass"].replace("eRingClass_","")
                        # ringclass = ringclass.strip("eRingClass_")


                        if "Belt" in singlering["Name"]:
                            one_ring["oType"] = "Belt"
                            ringclass = "Belt - " + ringclass
                            one_ring["oClass"] = "Belt"
                        else:
                            one_ring["oType"] = dict_singleobject["oType"]
                            ringclass = "Ring - " + ringclass
                            one_ring["oClass"] = dict_singleobject["oClass"]



                        one_ring["Object"] = ringclass
                        one_ring["MassMT"] = singlering["MassMT"]
                        one_ring["InnerRadius"] = singlering["InnerRad"]
                        one_ring["Radius"] = singlering["OuterRad"]

                        dict_objects[singlering["Name"]] = {}
                        dict_objects[singlering["Name"]]["Main"] = one_ring
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

sysrow = 1
syscol = 0

objrow = 0
objcol = 0

ringrow = 0
ringcol = 0

sectors.write_row(row, col, table_sectors)
systems.write_row(row, col, table_systems)
boxels.write_row(row, col, table_boxels)
lastBoxcol = len(table_boxels)-1

objects.write_row(objrow, objcol, (table_body + table_atmosphere + table_materials))
for objkey in dict_objects:
    objcol = 0
    objrow += 1
    objects.write(objrow,objcol,str(objkey))
    objcol += 1
    objectattributes = list(dict_objects[objkey]["Main"].values())
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

for key in sorted(dict_sectors):
    col = 0
    row += 1
    sectors.write(row,col,key)
    col += 1
    sectorloc = list(*dict_sectors[key]["coordinates"])
    sectors.write_row(row, col, (sectorloc)) # changed to just key instead of sector_key
    boxel_temp = dict_sectors[key] # changed to just key instead of sector_key

    # TODO - add unique list of primary star types to boxels
    # add formula with generated last row number?

    for boxkey in sorted(boxel_temp["boxels"]):
        boxelinfo = list(boxel_temp["boxels"][boxkey][0]["boxelcontents"])
        boxcol = 0
        boxrow += 1
        boxels.write(boxrow,boxcol,str(boxkey))
        boxcol += 1
        boxels.write_row(boxrow,boxcol,(*boxelinfo))
        syscol = 0
        for syskey in boxel_temp["boxels"][boxkey][1]:
            sysvals = (boxel_temp["boxels"][boxkey][1][syskey])
            system = str().join([boxkey,"-",syskey])
            for items in sysvals:
                if isinstance(items,list):
                    for coordinates in items:
                        systems.write(sysrow,syscol,coordinates)
                        syscol += 1
                else:
                    systems.write(sysrow,syscol,items)
                    syscol += 1
            # systems.write_formula(sysrow,syscol,'=IFERROR(AVERAGEIFS(objects!AZ$2:AZ${},objects!$A$2:$A${},$A{}&"*",objects!$H$2:$H${},"Gas Giant"),"")'.format(objrow,objrow,sysrow+1,objrow))
            sysrow += 1
        boxels.write_formula(boxrow,lastBoxcol,'=IFERROR(AVERAGEIFS(objects!AZ$2:AZ${},objects!$A$2:$A${},$A{}&"*",objects!$H$2:$H${},"Gas Giant"),"")'.format(objrow,objrow,boxrow+1,objrow))

workbook.close()