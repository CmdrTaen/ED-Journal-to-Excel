# ED-Journal-to-Excel
Python script to export all scan and related entries from the Elite Dangerous journal files to a multiple worksheet Excel file.

Currently all data is grouped into the following:

Sectors: 

- Coordinates (sector lower-left-bottom corner)
- Boxels visited (subsectors, eg. aa-a [a-h])
- Systems Visited

Boxels:

- Coordinates (boxel lower-left-bottom corner)
- System Address (as of 3.0)
- Systems Visited

- Nested relationship of boxels in same region of space

Systems:

- Coordinates (Exact)
- Timestamp (system arrival)
- Procgen Flag
- Primary Star (regardless of whether scanned or not, as of April 2017)
- BodyCount (number of bodies, as of 3.0)
- Local Boxel
- All boxel names that share the same region of space

Objects:  All standard object types and fields plus:

- Field to specify star or planet
- Field to break objects down into subgroups (gas giants, terrestrial, stellar remnants, carbon stars, main sequence, brown dwarf, wolf-rayet)
- Volcanism broken into three fields: Major|Minor; Material (eg. iron, silicates, etc.); Magma|geysers
- Atmosphere types broken into three fields: hot; density; elemental composition; rich
