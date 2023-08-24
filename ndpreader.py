import os
from types import SimpleNamespace
import xml.etree.ElementTree as ET
import tifffile

class NDPReader(object):
    """
    Class for reading NDPI files and associated annotations (NDPA files).

    Attributes:
        ndpi_path (str): The path to the NDPI file.
        ndpa_path (str): The path to the associated NDPA file.
        slide (OpenSlide): An OpenSlide object representing the NDPI file.
        slide_properties (dict): Metadata properties extracted from the NDPI file.
        NDP_software (str): The software used to create the NDPI file.
        size_x (int): The width of the slide in pixels.
        size_y (int): The height of the slide in pixels.
        mpp_x (float): Microns per pixel in the x-direction.
        mpp_y (float): Microns per pixel in the y-direction.
        centre_x (float): The x-coordinate of the slide's center in nanometers.
        centre_y (float): The y-coordinate of the slide's center in nanometers.
        offset_from_centre_x (float): The x-offset from the slide's center in nanometers.
        offset_from_centre_y (float): The y-offset from the slide's center in nanometers.
        offset_x (float): The x-coordinate of the slide's top-left corner in nanometers.
        offset_y (float): The y-coordinate of the slide's top-left corner in nanometers.
        annotations (list): A list of parsed annotations from the NDPA file.

    Methods:
        __init__(self, ndpi_path, ndpa_path=None):
            Initializes the NDPReader object.
        
        info(self):
            Returns information about the NDPI file and associated annotations.

        _parse_image_detais(self):
            Parses image details from the NDPI file.
            
        nm_to_um_px_point(self, point):
            Converts a point in nanometers to micrometer pixel coordinates.

        _parse_annotations(self):
            Parses annotations from the NDPA file.
    """
    
    
    def __init__(self, ndpi_path:str, ndpa_path:str = None):
        """
        Initializes the NDPReader object.

        Args:
            ndpi_path (str): The path to the NDPI file.
            ndpa_path (str, optional): The path to the associated NDPA file. If not provided,
                it is assumed to be in the same directory as the NDPI file and named with
                a ".ndpa" extension.
        
        Raises:
            FileNotFoundError: If the NDPI file or the NDPA file is not found.
        """
        
        # extract image details from NDPI file
        if not os.path.isfile(ndpi_path):
            raise FileNotFoundError(ndpi_path)
        self.ndpi_path = ndpi_path
        self._parse_image_detais()
        
        # parse annotations from NDPA file
        ndpa_path = ndpa_path if ndpa_path is not None else ndpi_path+".ndpa"
        if not os.path.isfile(ndpa_path):
            raise FileNotFoundError(ndpa_path)
        self.ndpa_path = ndpa_path
        self._parse_annotations()


    def info(self):
        """
        Returns information about the NDPI file and associated annotations.

        Returns:
            dict: A dictionary containing information about the NDPI file, including
            dimensions, date, maker, model, software, and the number of annotations.
        """
        
        return {
            "Image Filename": os.path.basename(self.ndpi_path),
            "Annotation Filename": os.path.basename(self.ndpa_path),
            "Dimensions": (self.size_x,self.size_y),
            "Date":self.slide_properties['DateTime'],
            "Maker":self.slide_properties['Make'],
            "Model":self.slide_properties['Model'],
            "Software":self.slide_properties['Software'],
            "Annotations": len(self.annotations),
        }


    def _parse_image_detais(self):
        """
        Parses image details from the NDPI file.
        """
        with tifffile.TiffFile(self.ndpi_path) as tif:
            # get most tags
            self.slide_properties = {tag.name:tag.value for tag in tif.pages[0].tags}
            # get custom ndpi tags
            for key,value in tif.pages[0].ndpi_tags.items():
                self.slide_properties[key] = value
        
        # get slide size 
        self.size_x = self.slide_properties['ImageWidth']
        self.size_y = self.slide_properties['ImageLength']
        
        # microns per pixel (mpp) (resolution scale cm to um)
        self.mpp_x = 10000 / self.slide_properties['XResolution'][0]
        self.mpp_y = 10000 / self.slide_properties['YResolution'][0]

        # calculate centere from pixels to nanometers
        self.centre_x = self.size_x * self.mpp_x * 1000 / 2
        self.centre_y = self.size_y * self.mpp_y * 1000 / 2
        
        # get offset from metadata (in nm)
        self.offset_from_centre_x = self.slide_properties['XOffsetFromSlideCenter']
        self.offset_from_centre_y = self.slide_properties['YOffsetFromSlideCenter']
        self.offset_from_centre_z = self.slide_properties['ZOffsetFromSlideCenter']

        # translate from center to top left
        self.offset_x = self.centre_x - self.offset_from_centre_x
        self.offset_y = self.centre_y - self.offset_from_centre_y


    def nm_to_pixel(self, point):
        """
        Converts a point in nanometers to micrometer pixel coordinates.

        Args:
            point (list): A list containing x and y coordinates in nanometers.

        Returns:
            list: A list containing x and y coordinates in micrometer pixel units.
        """
        x = (point[0] + self.offset_x) / (1000 * self.mpp_x)
        y = (point[1] + self.offset_y) / (1000 * self.mpp_y)
        return [x,y]


    def _parse_annotations(self):
        """
        Parses annotations from the NDPA file.
        """
        self.xml_root = ET.parse(self.ndpa_path).getroot()
        self.annotations = []

        for ndpviewstate_element in self.xml_root.findall('ndpviewstate'):
            
            # parse view state details
            annotation = SimpleNamespace(xml_type='ndpviewstate')
            annotation.title = ndpviewstate_element.find('title').text
            details = ndpviewstate_element.find('details').text
            annotation.details = details if details else ""
            annotation.coordformat = ndpviewstate_element.find('coordformat').text
            annotation.lens = float(ndpviewstate_element.find('lens').text)
            annotation.showtitle = ndpviewstate_element.find('showtitle').text=="1"
            annotation.showhistogram = ndpviewstate_element.find('showhistogram').text=="1"
            annotation.showlineprofile = ndpviewstate_element.find('showlineprofile').text=="1"
            
            # parse annotation for this view state
            # it's flatten into the same level as the view state
            annotation_element = ndpviewstate_element.find('annotation')
            annotation.type = annotation_element.attrib['type']
            annotation.displayname = annotation_element.attrib['displayname']
            annotation.color = annotation_element.attrib['color']
            annotation.measuretype = annotation_element.find('measuretype').text
            annotation.closed = annotation_element.find('closed').text=="1"
            
            if annotation.type == "linearmeasure":
                x1= float(ndpviewstate_element.find('x1').text)
                x2= float(ndpviewstate_element.find('x2').text)
                y1= float(ndpviewstate_element.find('y1').text)
                y2= float(ndpviewstate_element.find('y2').text)
                # linearmeasure
                annotation.points = [
                    [self.nm_to_pixel([x1,y1])],
                    [self.nm_to_pixel([x2,y2])],
                ]
            else:
                # all others have x,y,z coords
                annotation.x = float(ndpviewstate_element.find('x').text)
                annotation.y = float(ndpviewstate_element.find('y').text)
                # convert
                annotation.x, annotation.y = self.nm_to_pixel([annotation.x,annotation.y])
                annotation.z = float(ndpviewstate_element.find('z').text)
                # circle type annotation
                radius = ndpviewstate_element.find('radius')
                if radius:
                    annotation.radius = float(radius.text)
                # all other annotation types
                points = annotation_element.findall('pointlist/point')
                if points:
                    annotation.points = [[float(p.find('x').text),float(p.find('y').text)] for p in points]
                    annotation.points = [self.nm_to_pixel(p) for p in annotation.points]

            self.annotations.append(annotation)
