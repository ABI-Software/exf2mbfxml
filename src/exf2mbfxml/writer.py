import xml.etree.ElementTree as ET
from exf2mbfxml import __version__ as package_version


def _write_contour(contour, parent_element):
    points = contour.get("points", [])
    metadata = contour.get("metadata", [])
    if not points:
        return

    current_metadata = metadata[0]
    top_level = parent_element.tag == 'mbf'
    labels = current_metadata.get('labels', [])
    attributes = {'colour': current_metadata.get('colour', '#000000'), 'shape': 'Contour'}
    closed_contour = current_metadata.get('closed', None)
    if closed_contour is not None:
        attributes['closed'] = str(closed_contour).lower()

    if labels:
        shortest = min(labels, key=len)
        labels.remove(shortest)
        attributes['name'] = shortest

    # Create the contour element
    contour_element = ET.SubElement(parent_element, "contour", attributes)

    # Add properties
    global_uid = current_metadata.get('GUID', '')
    if global_uid:
        guid_element = ET.SubElement(contour_element, "property", name="GUID")
        ET.SubElement(guid_element, "s").text = global_uid

    fill_density = current_metadata.get('FillDensity', False)
    if fill_density:
        fill_density_element = ET.SubElement(contour_element, "property", name="FillDensity")
        ET.SubElement(fill_density_element, "n").text = str(fill_density)

    resolution = current_metadata.get('resolution', None)
    if resolution is not None:
        ET.SubElement(contour_element, "resolution").text = str(resolution)

    for label in labels:
        set_property_element = ET.SubElement(contour_element, 'property', name='Set')
        ET.SubElement(set_property_element, 's').text = label

    # Add points
    for point in points:
        ET.SubElement(contour_element, "point", x=str(point[0]), y=str(point[1]), z=str(point[2]), d=str(point[3]), sid="S1072")


def write_mbfxml(output_mbf, data, options=None):
    # Create the root element
    root = ET.Element("mbf", version="4.0", xmlns="http://www.mbfbioscience.com/2007/neurolucida",
                      appname="Exf2MBFXML", appversion=package_version)

    for contour in data.get('contours', []):
        _write_contour(contour, root)

    # Create the XML tree and write to a file
    tree = ET.ElementTree(root)
    ET.indent(tree, level=0)
    tree.write(output_mbf, encoding="ISO-8859-1", xml_declaration=True)
