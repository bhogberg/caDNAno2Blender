bl_info = {
    "name": "caDNAno2Blender",
    "author": "Björn Högberg",
    "version": (1, 0, 0),
    "blender": (2, 83, 0),
    "location": "View3D",
    "description": "Module for working with caDNAno files in Blender",
    "category": "Import-Export",
}

import bpy
import os

from bpy.props import StringProperty, BoolProperty
from bpy_extras.io_utils import ImportHelper
from bpy.types import Operator



class c2bPanel(bpy.types.Panel):
    bl_label = "caDNAno2Blend"
    bl_idname = "c2bPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'caDNAno2Blend'

    def draw(self, contex):
        layout = self.layout
        row = layout.row()
        row.label(text='caDNAno to Blender', icon='LIGHTPROBE_GRID')


class OT_TestOpenFilebrowser(Operator, ImportHelper):
    bl_idname = "test.open_filebrowser"
    bl_label = "Open the file browser (yay)"
    filter_glob: StringProperty(
        default='*.jpg;*.jpeg;*.png;*.tif;*.tiff;*.bmp', options={'HIDDEN'})

    some_boolean: BoolProperty(
        name='Do a thing', description='Do a thing with the file you\'ve selected', default=True, )

def execute(self, context):
    """Do something with the selected file(s)."""
    filename, extension = os.path.splitext(self.filepath)
    print('Selected file:', self.filepath)
    print('File name:', filename)
    print('File extension:', extension)
    print('Some Boolean:', self.some_boolean)

    return {'FINISHED'}

def register():
    bpy.utils.register_class(c2bPanel)

def unregister():
    bpy.utils.unregister_class(c2bPanel)

if __name__ == "__main__":
    register()