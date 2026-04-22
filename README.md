# SMaRC Mission Control Plugin for QGIS

[WARA-PS API](https://api-docs.waraps.org/#/) compliant mission planning in the open-source GIS software [QGIS](https://qgis.org/).

## Installation instructions
Supported QGIS version: v3.44 LTR  
Supported Ubuntu version(s): 22.04 (Python 3.10)

1. Install QGIS v3.44 LTR from [qgis.org](https://qgis.org/download)

2. Install the SMaRC Mission Control Plugin
   - Clone the repository into the QGIS Python library folder:
     - Windows: `C:\Users\<user>\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins`
     - Ubuntu: `/usr/lib/qgis/plugins`
   - Download the repository as a zip file and load it via the plugin manager: *Plugins* -> *Manage and install plugins ...* -> *Install from ZIP*
  
3. Install other useful plugins via the plugin manager, for example
   -  Plugin Reloader
   -  Basemaps
   -  Cruise Tools
  
4. Add a base layer either via the *Basemaps* plugin or via
   - *Layer* -> *Add Layer ...* -> *Add XYZ Layer ...*
     - OpenStreetMaps: `https://tile.openstreetmap.org/{z}/{x}/{y}.png`
     - Google Maps (Satellite): `https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}`
     - Google Maps (Hybrid): `https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}`
     - Google Maps (Roadmap): `https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}`
   - *Layer* -> *Add Layer ...* -> *Add WMS/WMTS Layer ...*

5. Start betatesting the plugin :-)
