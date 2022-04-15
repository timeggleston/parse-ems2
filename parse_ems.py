#!/usr/bin/env python3
from construct import *
from datetime import datetime, timezone
import csv
import sys
import os
import argparse
import pathlib

parser = argparse.ArgumentParser(description="Parse MGL Avionics EMS-2 serial output into CSV files understood by the Savvy Analysis online service. One file per flight will be generated.")
parser.add_argument("indir", help="A directory containing binary recordings of EMS-2 serial output", type=pathlib.Path)
parser.add_argument("-o", "--outdir", help="Location to which output files should be written", default="./", type=pathlib.Path)
args = parser.parse_args()

# TODO: replace this with checksum validation
def ispacketvalid(packet):
    if (len(packet) == 68):
        return True
    else:
        #print('Invalid packet! Length is ' + str(len(packet)))
        return False


files = []
path = args.indir
for root, directories, file in os.walk(path):
    for file in file:
        # B.TXT is the suffix of EMS-2-related files on my specific RSLogger module
        if(file.endswith("B.TXT")):
            path = os.path.join(root, file)
            f = open(path, "r")
            if (len(f.read()) > 0):
                files.append(os.path.join(root, file))

csvswritten = 0

for path in files:
    print('Processing ' + path)
    file = open(path, "r")
    f = file.read()
    hex_pieces = f.split()
    b = bytearray([int(piece, 16) for piece in hex_pieces if len(piece) == 2])
    start = bytearray.fromhex('02 01 01')
    packets = b.split(start)
    packetformat = BitStruct(
        'length' / Bytewise(Int8ub),
        'localtime' / Bytewise(Int32ub),
        'hobbshours' / Bytewise(Int16ub),
        'hobbsmins' / Bytewise(Int8ub),
        'mainttime' / Bytewise(Int16ub),
        'volts' / Bytewise(Int16ub),
        'rpm1' / Bytewise(Int32ub),
        'rpm1pct' / Bytewise(Int16ub),
        'rpm2' / Bytewise(Int32ub),
        'rpm2pct' / Bytewise(Int16ub),
        'ch4type' / BitsInteger(4),
        'ch3type' / BitsInteger(4),
        'ch2type' / BitsInteger(4),
        'ch1type' / BitsInteger(4),
        'ch1' / Bytewise(Int16sb),
        'ch2' / Bytewise(Int16sb),
        'ch3' / Bytewise(Int16sb),
        'ch4' / Bytewise(Int16sb),
        'manpress' / Bytewise(Int16sb),
        'current' / Bytewise(Int16sb),
        'cjc' / Bytewise(Int16sb),
        'egt1' / Bytewise(Int16sb),
        'egt2' / Bytewise(Int16sb),
        'egt3' / Bytewise(Int16sb),
        'egt4' / Bytewise(Int16sb),
        'cht1' / Bytewise(Int16sb),
        'cht2' / Bytewise(Int16sb),
        'cht3' / Bytewise(Int16sb),
        'cht4' / Bytewise(Int16sb),
        'tc1' / Bytewise(Int16sb),
        'tc2' / Bytewise(Int16sb),
        'tc3' / Bytewise(Int16sb),
        'tc4' / Bytewise(Int16sb),
        'fuelflow' / Bytewise(Int16ub),
        'chksum' / Bytewise(Int8ub),
        'etx' / Bytewise(Int8ub)
        )
    csv_header = ["TIME","LAT","LON","PALT","E1","E2","E3","E4","E5","E6","C1","C2","C3","C4","C5","C6","OILT","OILP","RPM","OAT","MAP","FF","USED","AMPL","AMPR","LBUS","RBUS","CARBT"]

    # get all flight starts from file (may have more than one flight). 
    # flights are separated by gaps of more than 30 seconds in the timestamps
    print("Getting flights in file")
    starts = [0]
    prevdt = (packetformat.parse(packets[1]).localtime)-1
    currdt = packetformat.parse(packets[1]).localtime
    for idx, packet in enumerate(packets):
        if (ispacketvalid(packet)):
            currdt = packetformat.parse(packet).localtime
            delta = currdt-prevdt
            if (delta > 30):
                starts.append(idx)
            prevdt = currdt

    # for each flight create a file
    invalidpackets = 0
    for idx, start in enumerate(starts):
        print("...Processing flight " + str(idx))
        try:
            packetformat.parse(packets[start+1])
        except IndexError:
            print("...Index error")
            break
        flightdate = datetime.strftime(datetime.utcfromtimestamp(packetformat.parse(packets[start+1]).localtime), "%y/%m/%d %H:%M:%S")
        print("...Flight date " + flightdate)
        isrealflight = 0
        rows = []

        if (idx == len(starts)-1):
            finish = len(packets)
        else:
            finish = starts[idx+1]-1

        for i in range(start, finish):
            packet = packets[i]
            if (ispacketvalid(packet)):
                parsed = packetformat.parse(packet)
                ret = [str(datetime.time(datetime.utcfromtimestamp(parsed.localtime))),
                    "0",
                    "0",
                    "0",
                    parsed.egt1,
                    parsed.egt2,
                    parsed.egt3,
                    parsed.egt4,
                    "0",
                    "0",
                    parsed.cht1,
                    parsed.cht2,
                    parsed.cht3,
                    parsed.cht4,
                    "0",
                    "0",
                    parsed.ch1,
                    parsed.ch2/10,
                    parsed.rpm1,
                    "0",
                    parsed.manpress,
                    parsed.fuelflow/10,
                    "0",
                    "0",
                    "0",
                    parsed.volts/10,
                    "0",
                    parsed.ch3]
                rows.append(ret)
                # we only consider this to be a real flight if the oil pressure
                # goes over 20 psi at least once
                if ((parsed.ch2/10) > 20):
                    isrealflight = isrealflight + 1
            else:
                invalidpackets = invalidpackets + 1

        if (invalidpackets > 0):
            print("...[" + str(invalidpackets) + "/" + str(finish-start) + "] packets invalid")

        if (isrealflight > 0):
            csvpath = str(args.outdir)+'/'+'flight_'+datetime.strftime(datetime.utcfromtimestamp(packetformat.parse(packets[start+1]).localtime), '%Y%m%d-%H%M%S')+'.log'
            print('...Writing CSV ' + csvpath + '\n')
            flightdate = datetime.strftime(datetime.utcfromtimestamp(packetformat.parse(packets[start+1]).localtime), "%m/%d/%y %H:%M:%S")
            csvfile = csvfile = open(csvpath, 'w', newline = '')
            csvobj = csv.writer(csvfile)
            csvfile.write("Avidyne Engine Data Log -- MGL EMS-2 output by Tim Eggleston tim@eggleston.ca" + "\n")
            csvfile.write(flightdate + "\n")
            csvobj.writerow(csv_header)
            csvobj.writerows(rows)
            csvfile.close()
            csvswritten = csvswritten + 1
        else:
            print("...Not a real flight (no oil pressure)\n")

print("Wrote " + str(csvswritten) + " files")