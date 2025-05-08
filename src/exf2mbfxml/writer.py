import xml.etree.ElementTree as ET
from exf2mbfxml import __version__ as package_version


def write_mbfxml(output_mbf, contents, options):
    if contents["contours"]["points"]:
        data = contents["contours"]
    else:
        data = contents["trees"]
    data = {
        'contours': {
            'points': [[[2.0, 1.0, 5.0], [3.0, 1.0, 4.2], [3.0, 3.0, 4.0], [2.0, 1.0, 5.0]]],
            'metadata': [{'closed': True}]
        }
    }

    # Create the root element
    root = ET.Element("mbf", version="4.0", xmlns="http://www.mbfbioscience.com/2007/neurolucida",
                      appname="Exf2MBFXML", appversion=package_version)

    # Create the contour element
    contour = ET.SubElement(root, "contour", name="Heart (7088)", color="#FF0000", closed=str(data['contours']['metadata'][0]['closed']).lower(), shape="Contour")

    # Add properties
    property_guid = ET.SubElement(contour, "property", name="GUID")
    ET.SubElement(property_guid, "s").text = ""

    property_fill_density = ET.SubElement(contour, "property", name="FillDensity")
    ET.SubElement(property_fill_density, "n").text = "0"

    # Add resolution
    ET.SubElement(contour, "resolution").text = "1.297297"

    # Add points
    for point in data['contours']['points'][0]:
        ET.SubElement(contour, "point", x=str(point[0]), y=str(point[1]), z=str(point[2]), d="1.00", sid="S1072")

    # Create the XML tree and write to a file
    tree = ET.ElementTree(root)
    ET.indent(tree, level=0)
    tree.write(output_mbf, encoding="ISO-8859-1", xml_declaration=True)

    print("XML file has been created successfully.")
