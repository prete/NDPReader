# NDPReader
Parse NanoZoomer Digital Pathology Annotation (NDPA) files into a more generic format

# Requirments
[Tifffile](https://pypi.org/project/tifffile/) for reading the image data and metadata. Install with `pip install tifffile`.

# Usage:

### Default usage
```python
ndpi_path = "slide.ndpi"
ndp = NDPReader(ndpi_path)
ndp.info()
{
 'Image Filename': 'slide.ndpi',
 'Annotation Filename': 'slide.ndpi.ndpa',
 'Dimensions': (82432, 40320),
 'Date': '2020:09:21 13:00:32',
 'Maker': 'Hamamatsu',
 'Model': 'C13210',
 'Software': 'NDP.scan 3.3.2',
 'Annotations': 27
}
```

### Annotations to a list of Python dictionaries
```python
ndpi_path = "slide.ndpi"
ndp = NDPReader(ndpi_path)
d = [annotation.__dict__ for annotation in ndp.annotations]
[
  {
    'title': 'Ann1',
    'coordformat': 'nanometers',
    'lens': 5.406136,
    'type': 'freehand',
    'displayname': 'AnnotateFreehandLine',
    'color': '#000000',
    'points': [[17981.381441800004, 9921.903069400001],...]
  },
  ...
]
```

### Different NDPI and NDPA filenames
```python
ndpi_path = "slide.ndpi"
ndpa_path = "annotations.ndpa"
ndp = NDPReader(ndpi_path, ndpa_path)
ndp.info()
{
 'Image Filename': 'slide.ndpi',
 'Annotation Filename': 'annotations.ndpa',
 'Dimensions': (82432, 40320),
 'Date': '2020:09:21 13:00:32',
 'Maker': 'Hamamatsu',
 'Model': 'C13210',
 'Software': 'NDP.scan 3.3.2',
 'Annotations': 27
}
```

### Example: read NDP and import annotations as ROI in OMERO
```python
from ndpreader import NDPReader
import omero
from omero.model.enums import UnitsLength

ndpi_path = "slide.ndpi"
ndp = NDPReader(ndpi_path)

connection = BlitzGateway( ... )
update_service = connection.getUpdateService()

for annotation in ndp.annotations:
    # create shape (polygon)
    polygon = omero.model.PolygonI()
    polygon.theZ = omero.rtypes.rint(0)
    polygon.theC = omero.rtypes.rint(0)
    polygon.theT = omero.rtypes.rint(0)
    polygon.fillColor = omero.rtypes.rint(hex_to_int(annotation.color, 75))
    polygon.strokeColor = omero.rtypes.rint(hex_to_int(annotation.color))
    polygon.strokeWidth = omero.model.LengthI(5, UnitsLength.PIXEL)
    polygon.points = omero.rtypes.rstring(
        " ".join((f"{int(p[0])},{int(p[1])}" for p in annotation.points)))
    polygon.setTextValue(omero.rtypes.rstring(annotation.title))
    
    # create an ROI, add shape and link to image
    roi = omero.model.RoiI()
    roi.setImage(connection.getObject("Image", 123)._obj)
    roi.addShape(polygon)
    
    # save ROI and return it
    r = update_service.saveAndReturnObject(roi)
    print(f"{Annotation={annotation.title} -- ID={r.id.val}")
```

Additional function for OMERO color conversion:
```python
def hex_to_int(hexcolor,alpha=255):
    """ Return the color as an Integer in RGBA encoding """
    if hexcolor[0]=="#":
        hexcolor = hexcolor[1:]
    r = int(hexcolor[:2], 16) << 24
    g = int(hexcolor[3:4], 16) << 16
    b = int(hexcolor[4:6], 16) << 8
    a = alpha
    rgba_int = r+g+b+a
    if (rgba_int > (2**31-1)):
        rgba_int = rgba_int - 2**32
    return rgba_int
```
