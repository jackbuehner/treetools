import importlib

# this convoluted way of importing the tools is required
# because ArcGIS does not reload imported modules
# unless the software is restarted
import DetectTrees
importlib.reload(DetectTrees)
from DetectTrees import DetectTrees as DetectTreesTool

class Toolbox(object):
  def __init__(self):
    self.label =  "Tree Tools"
    self.alias  = "treetools"

    # List of tool classes associated with this toolbox
    self.tools = [DetectTreesTool]