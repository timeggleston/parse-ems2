# Parse EMS-2

## About

A Python program for parsing data recorded from the serial output of an MGL Avionics EMS-2 engine monitor, captured by an RSLogger module. Parsed data will be written to a CSV file suitable for ingestion into the Savvy Analysis online service.

This program was written for my own use. It is specific to my engine monitor and RSLogger config, although it's probably easily updated to work with other setups.

## Use

1.  Clone the repo.
2.  Run as follows, specifying a directory containing one or more RSLogger log files of EMS-2 format data:

        ./parse_ems.py INDIR
3.  The program will parse all files in `INDIR`, and for each file that contains a flight (oil pressure > 20 PSI at least once), it will write a CSV to the current directory containing the flight data.