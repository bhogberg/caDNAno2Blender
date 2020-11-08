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
import subprocess
import importlib
from collections import namedtuple
from bpy.props import StringProperty, BoolProperty
from bpy_extras.io_utils import ImportHelper

Dependency = namedtuple("Dependency", ["module", "package", "name"])
# Declare all modules that this add-on depends on. The package and (global) name can be set to None,
# if they are equal to the module name. See import_module and ensure_and_import_module for the
# explanation of the arguments.
dependencies = (Dependency(module="simplejson", package=None, name=None),)

dependencies_installed = False

def import_module(module_name, global_name=None):
    """
    Import a module.
    :param module_name: Module to import.
    :param global_name: (Optional) Name under which the module is imported. If None the module_name will be used.
       This allows to import under a different name with the same effect as e.g. "import numpy as np" where "np" is
       the global_name under which the module can be accessed.
    :raises: ImportError and ModuleNotFoundError
    """
    if global_name is None:
        global_name = module_name

    # Attempt to import the module and assign it to globals dictionary. This allow to access the module under
    # the given name, just like the regular import would.
    globals()[global_name] = importlib.import_module(module_name)

def install_pip():
    """
    Installs pip if not already present. Please note that ensurepip.bootstrap() also calls pip, which adds the
    environment variable PIP_REQ_TRACKER. After ensurepip.bootstrap() finishes execution, the directory doesn't exist
    anymore. However, when subprocess is used to call pip, in order to install a package, the environment variables
    still contain PIP_REQ_TRACKER with the now nonexistent path. This is a problem since pip checks if PIP_REQ_TRACKER
    is set and if it is, attempts to use it as temp directory. This would result in an error because the
    directory can't be found. Therefore, PIP_REQ_TRACKER needs to be removed from environment variables.
    :return:
    """
    try:
        # Check if pip is already installed
        subprocess.run([bpy.app.binary_path_python, "-m", "pip", "--version"], check=True)
    except subprocess.CalledProcessError:
        import ensurepip

        ensurepip.bootstrap()
        os.environ.pop("PIP_REQ_TRACKER", None)

def install_and_import_module(module_name, package_name=None, global_name=None):
    """
    Installs the package through pip and attempts to import the installed module.
    :param module_name: Module to import.
    :param package_name: (Optional) Name of the package that needs to be installed. If None it is assumed to be equal
       to the module_name.
    :param global_name: (Optional) Name under which the module is imported. If None the module_name will be used.
       This allows to import under a different name with the same effect as e.g. "import numpy as np" where "np" is
       the global_name under which the module can be accessed.
    :raises: subprocess.CalledProcessError and ImportError
    """
    if package_name is None:
        package_name = module_name

    if global_name is None:
        global_name = module_name

    # Blender disables the loading of user site-packages by default. However, pip will still check them to determine
    # if a dependency is already installed. This can cause problems if the packages is installed in the user
    # site-packages and pip deems the requirement satisfied, but Blender cannot import the package from the user
    # site-packages. Hence, the environment variable PYTHONNOUSERSITE is set to disallow pip from checking the user
    # site-packages. If the package is not already installed for Blender's Python interpreter, it will then try to.
    # The paths used by pip can be checked with `subprocess.run([bpy.app.binary_path_python, "-m", "site"], check=True)`

    # Store the original environment variables
    environ_orig = dict(os.environ)
    os.environ["PYTHONNOUSERSITE"] = "1"

    try:
        # Try to install the package. This may fail with subprocess.CalledProcessError
        subprocess.run([bpy.app.binary_path_python, "-m", "pip", "install", package_name], check=True)
    finally:
        # Always restore the original environment variables
        os.environ.clear()
        os.environ.update(environ_orig)

    # The installation succeeded, attempt to import the module again
    import_module(module_name, global_name)


class caDNAnoFileHandler():

    def __init__(self):
        self.jsonDecoder = simplejson.JSONDecoder()
        self.jsonEncoder = simplejson.JSONEncoder()
        self.data = []
        self.fileName = ""
        self.vstrandsSequence = {}
        self.strandi = {}

    def get_data(self):
        return self.data

    def read_caDNAno_file(self, file_n):
        # read in the file
        if not os.path.isfile(file_n):
            print("In method read_caDNAno_file: error reading the file '" + file_n + "'")
            return
        self.fileName = file_n
        file = open(self.fileName, 'r')
        lines = file.readlines()
        file.close()
        str = ""
        for line in lines:
            str += line

        # decode JSON data into a Python object
        self.data = self.jsonDecoder.decode(str)

        # Initiate sequence on virtual strands to '?'s at all bases
        totalBases = len(self.data["vstrands"][0]["skip"])
        strands = self.data["vstrands"]
        self.vstrandsSequence = {}
        for strand in strands:
            self.vstrandsSequence.update({strand["num"]: ['?' for i in range(totalBases)]})

        # Build dictionary of virtual helix numbers:indecies
        strands = self.data["vstrands"]
        i = 0
        for strand in strands:
            self.strandi.update({strand["num"]: i})
            i += 1

    def write_caDNAno_file(self, new_filename):
        # encodes into JSON and writes the file
        if os.path.isfile(new_filename):
            answer = "q"
            while answer != ("y" or "n"):
                print("Do you want to overwrite '" + new_filename + "' ? (y/n)")
                answer = input()
            if answer == "n":
                return
        # ready to encode and write
        self.data["name"] = time.strftime("%a %b %d %Y %H:%M:%S")
        encoded = self.jsonEncoder.encode(self.data)
        outputfile = open(new_filename, 'w')
        outputfile.write(encoded)
        outputfile.close()

    def print_basic_data(self):
        # extract virtual strand information from data
        strands = self.data["vstrands"]
        name = self.data["name"]

        print("caDNAno file: " + self.fileName)
        print("object name: " + name)
        print("Number of virtual strands: ", len(strands))

        for strand in strands:
            # row and column in the cross-sectional hexagonal lattice
            row = strand["row"]
            col = strand["col"]

            # number attached to virtual strand in the cross-sectional hexagonal lattice representation
            num = strand["num"]

            # token-pointer pair arrays representing traversal of scaffold and staple paths through structure
            scaf = strand["scaf"]
            stap = strand["stap"]

            print("\n---Virtual Strand---")
            print("Number: ", num)
            print("Lattice Row: ", row)
            print("Lattice Column: ", col)
            print("Number of scaffold bases: ", len(scaf))
            print("Number of staple bases: ", len(stap))
            print("Token-pointer array scaffold: ", scaf)
            print("Token-pointer array staples: ", stap)

    def object_concat(self, x):
        # concatenate the virtual scaffold and staple strands x-times along the z-axis (to the right)
        strands = self.data["vstrands"]
        for strand in strands:
            # ---------------------------------------------
            # Start with the scaffold strands:
            # ---------------------------------------------
            endbases = []
            startbases = []
            endLoops = []
            startLoops = []
            # find the number of empty bases at the end
            scaf = strand["scaf"]
            loops = strand["loop"]
            while scaf[-1] == [-1, -1, -1, -1]:
                endbases.append(scaf.pop())
                endLoops.append(loops.pop())
            # find the number of empty bases at the beginning
            scaf.reverse()
            loops.reverse()
            while scaf[-1] == [-1, -1, -1, -1]:
                startbases.append(scaf.pop())
                startLoops.append(loops.pop())
            scaf.reverse()
            loops.reverse()

            #  Loop bases

            newLoop = []
            newLoop.extend(startLoops)
            for i in range(x):
                newLoop.extend(loops)
            newLoop.extend(endLoops)
            strand["loop"] = newLoop

            # Continue with the scaffold

            insert_len = len(scaf)
            insert = []
            for i in range(x):
                for base in scaf:
                    b1 = -1
                    b3 = -1
                    if base[1] != -1:
                        b1 = base[1] + insert_len * i
                    if base[3] != -1:
                        b3 = base[3] + insert_len * i
                    insert.append([base[0], b1, base[2], b3])
            newscaf = []
            newscaf.extend(startbases)
            newscaf.extend(insert)
            newscaf.extend(endbases)
            strand["scaf"] = newscaf

            # ---------------------------------------------
            # The same procedure for the staple strands:
            # ---------------------------------------------
            endbases = []
            startbases = []
            # find the number of empty bases at the end
            stap = strand["stap"]
            while stap[-1] == [-1, -1, -1, -1]:
                endbases.append(stap.pop())
            # find the number of empty bases at the beginning
            stap.reverse()
            while stap[-1] == [-1, -1, -1, -1]:
                startbases.append(stap.pop())
            stap.reverse()
            insert_len = len(stap)
            insert = []
            for i in range(x):
                for base in stap:
                    b1 = -1
                    b3 = -1
                    if base[1] != -1:
                        b1 = base[1] + insert_len * i
                    if base[3] != -1:
                        b3 = base[3] + insert_len * i
                    insert.append([base[0], b1, base[2], b3])
            newstap = []
            newstap.extend(startbases)
            newstap.extend(insert)
            newstap.extend(endbases)
            strand["stap"] = newstap

            # Add zeros to the skip attributes

            strand["skip"] = [0 for j in range(len(newstap))]

    def scaffold_stitch(self):
        # Finds beakpoints in the scaffold strands and stitches them together
        # breakpoints look like this: on base b-1 [h,b-2,-1,-1] on base b [-1,-1,h,b+1]
        # or like this on base b-1 [-1,-1,h,b-2] and on base b [h,b+1,-1,-1]
        strands = self.data["vstrands"]
        for strand in strands:
            scaf = strand["scaf"]
            for b in range(len(scaf)):
                if b != 0:
                    if (scaf[b - 1][1] + scaf[b - 1][3] == b - 3) and (scaf[b][1] + scaf[b][3] == b):
                        # This is a breakpoint. Now, find directionality and stitch.
                        if scaf[b - 1][3] == -1:
                            scaf[b - 1][2] = scaf[b - 1][0]
                            scaf[b - 1][3] = b
                            scaf[b][0] = scaf[b][2]
                            scaf[b][1] = b - 1
                        if scaf[b - 1][1] == -1:
                            scaf[b - 1][0] = scaf[b - 1][2]
                            scaf[b - 1][1] = b
                            scaf[b][2] = scaf[b][0]
                            scaf[b][3] = b - 1

    def get_staples(self):
        # Returns a list of staples - a list of token pointer arrays
        # where each item is a list like this:
        #
        #  [ [ [startStrand,startBase], color, [ [-1,-1, .., ..], ... ]  ],   ]
        #
        # First find all 5' ends
        staples = []
        strands = self.data["vstrands"]
        for strand in strands:
            StapStarts = strand["stap_colors"]
            if len(StapStarts) > 0:
                strandNumber = strand["num"]
                for start in StapStarts:
                    k = [[strandNumber, start[0]], hex(start[1]), []]
                    staples.append(k)
        for staple in staples:
            currentBase = strands[self.strandi[staple[0][0]]]["stap"][staple[0][1]]
            staple[2].append(currentBase)
            threePrimeFound = False
            while not threePrimeFound:
                nextStrandIndex = currentBase[2]
                nextBaseIndex = currentBase[3]
                currentBase = strands[self.strandi[nextStrandIndex]]["stap"][nextBaseIndex]
                staple[2].append(currentBase)
                if currentBase[2] == -1 and currentBase[3] == -1:
                    threePrimeFound = True
        return staples

    def populateSequence(self, scaffold5prime, scaffoldSequence):
        # Populates the scaffold virtual strands with sequence data
        # scaffoldSequence is a string with the entire scaffold sequence
        # scaffold5prime is [strand, base] of the 5'-end of the scaffold
        # breakpoint
        #
        # Currently adds 'D' at deletion sites
        #
        strands = self.data["vstrands"]
        scaff = list(scaffoldSequence)
        currentBase = strands[self.strandi[scaffold5prime[0]]]["scaf"][scaffold5prime[1]]
        strand = scaffold5prime[0]
        base = scaffold5prime[1]
        while len(scaff) > 0:
            if strands[self.strandi[strand]]["skip"][base] == -1:
                # Deletion
                self.vstrandsSequence[strand][base] = 'D'
            else:
                self.vstrandsSequence[strand][base] = scaff.pop(0)
            nextStrand = currentBase[2]
            nextBase = currentBase[3]
            if nextStrand == -1 and nextBase == -1:
                break
            currentBase = strands[self.strandi[nextStrand]]["scaf"][nextBase]
            strand = nextStrand
            base = nextBase

    def getStapleSeq(self, startPt, stapPtArray):
        # Gives the sequence for one staple defined by the input stapPtArray
        # startPt is [strand,base]
        #
        #
        comp = {'a': 'T', 'A': 'T', 'c': 'G', 'C': 'G', 'g': 'C', 'G': 'C', 't': 'A', 'T': 'A', 'D': '', '?': '?'}
        strand = startPt[0]
        base = startPt[1]
        i = 0
        stapSeq = []
        nextStrand = stapPtArray[i][2]
        nextBase = stapPtArray[i][3]
        stapSeq.append(comp[self.vstrandsSequence[strand][base]])
        while nextStrand != -1 and nextBase != -1:
            i += 1
            strand = nextStrand
            base = nextBase
            nextStrand = stapPtArray[i][2]
            nextBase = stapPtArray[i][3]
            stapSeq.append(comp[self.vstrandsSequence[strand][base]])
        return (stapSeq)

    def getStapleSeqWithXs(self, startPt, stapPtArray):
        # Gives the sequence for one staple defined by the input stapPtArray
        # startPt is [strand,base]
        #
        # This version WithXs gives X at strand crossover positions
        # these can be replaced with TTs for UV welding of crossovers
        comp = {'a': 'T', 'A': 'T', 'c': 'G', 'C': 'G', 'g': 'C', 'G': 'C', 't': 'A', 'T': 'A', 'D': '', '?': '?'}
        strand = startPt[0]
        base = startPt[1]
        i = 0
        stapSeq = []
        nextStrand = stapPtArray[i][2]
        nextBase = stapPtArray[i][3]
        stapSeq.append(comp[self.vstrandsSequence[strand][base]])
        if nextStrand != strand:
            # Possible crossover
            if nextStrand != -1:
                stapSeq.append('X')
        while nextStrand != -1 and nextBase != -1:
            i += 1
            strand = nextStrand
            base = nextBase
            nextStrand = stapPtArray[i][2]
            nextBase = stapPtArray[i][3]
            stapSeq.append(comp[self.vstrandsSequence[strand][base]])
            if nextStrand != strand:
                # Possible crossover
                if nextStrand != -1:
                    stapSeq.append('X')
        return (stapSeq)

class c2bProperties(bpy.types.PropertyGroup):
    caDNAno_filepath = bpy.props.StringProperty(subtype="FILE_PATH")

class C2B_PT_c2bMainPanel(bpy.types.Panel):
    bl_label = "caDNAno2Blend"
    bl_idname = "C2B_PT_c2bMainPanelbl"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'caDNAno2Blend'

    def draw(self, context):
        scn = context.scene
        row = self.layout.row()
        row.label(text='caDNAno to Blender', icon='LIGHTPROBE_GRID')
        row = self.layout.row()
        row.operator("c2b.file_selector", icon="FILE_FOLDER", text="")
        row.label(text=scn.c2b_properties.caDNAno_filepath)
        row = self.layout.row()
        row.operator("c2b.file_printer", text="Print caDNAno")


class C2B_OT_FilePrinter(bpy.types.Operator):
    bl_idname = "c2b.file_printer"
    bl_label = "Print caDNAno"

    def execute(self, context):
        print('Testing caDNAno reading and printing:')
        caDNAno = caDNAnoFileHandler()
        caDNAno.read_caDNAno_file(context.scene.c2b_properties.caDNAno_filepath)
        caDNAno.print_basic_data()
        return{'FINISHED'}



class C2B_OT_FileSelector(bpy.types.Operator, ImportHelper):
    bl_idname = "c2b.file_selector"
    bl_label = "caDNAno file"

    filter_glob: StringProperty(
        default='*.json', options={'HIDDEN'})

    def execute(self, context):
        fdir = self.properties.filepath
        context.scene.c2b_properties.caDNAno_filepath = fdir
        return{'FINISHED'}

class EXAMPLE_PT_warning_panel(bpy.types.Panel):
    bl_label = "caDNAno2Blender Warning"
    bl_category = "caDNAno2Blend"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    @classmethod
    def poll(self, context):
        return not dependencies_installed

    def draw(self, context):
        layout = self.layout

        lines = [f"Please install the missing dependencies for the \"{bl_info.get('name')}\" add-on.",
                 f"1. Open the preferences (Edit > Preferences > Add-ons).",
                 f"2. Search for the \"{bl_info.get('name')}\" add-on.",
                 f"3. Open the details section of the add-on.",
                 f"4. Click on the \"{EXAMPLE_OT_install_dependencies.bl_label}\" button.",
                 f"   This will download and install the missing Python packages, if Blender has the required",
                 f"   permissions.",
                 f"If you're attempting to run the add-on from the text editor, you won't see the options described",
                 f"above. Please install the add-on properly through the preferences.",
                 f"1. Open the add-on preferences (Edit > Preferences > Add-ons).",
                 f"2. Press the \"Install\" button.",
                 f"3. Search for the add-on file.",
                 f"4. Confirm the selection by pressing the \"Install Add-on\" button in the file browser."]

        for line in lines:
            layout.label(text=line)


class EXAMPLE_OT_install_dependencies(bpy.types.Operator):
    bl_idname = "example.install_dependencies"
    bl_label = "Install dependencies"
    bl_description = ("Downloads and installs the required python packages for this add-on. "
                      "Internet connection is required. Blender may have to be started with "
                      "elevated permissions in order to install the package")
    bl_options = {"REGISTER", "INTERNAL"}

    @classmethod
    def poll(self, context):
        # Deactivate when dependencies have been installed
        return not dependencies_installed

    def execute(self, context):
        try:
            install_pip()
            for dependency in dependencies:
                install_and_import_module(module_name=dependency.module,
                                          package_name=dependency.package,
                                          global_name=dependency.name)
        except (subprocess.CalledProcessError, ImportError) as err:
            self.report({"ERROR"}, str(err))
            return {"CANCELLED"}

        global dependencies_installed
        dependencies_installed = True

        # Register the panels, operators, etc. since dependencies are installed
        for cls in __classes__:
            bpy.utils.register_class(cls)

        return {"FINISHED"}


class EXAMPLE_preferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    def draw(self, context):
        layout = self.layout
        layout.operator(EXAMPLE_OT_install_dependencies.bl_idname, icon="CONSOLE")


preference_classes = (EXAMPLE_PT_warning_panel,
                      EXAMPLE_OT_install_dependencies,
                      EXAMPLE_preferences)

__classes__ = (
    c2bProperties, C2B_OT_FileSelector, C2B_OT_FilePrinter, C2B_PT_c2bMainPanel
)

def register():
    global dependencies_installed
    dependencies_installed = False

    for cls in preference_classes:
        bpy.utils.register_class(cls)

    try:
        for dependency in dependencies:
            import_module(module_name=dependency.module, global_name=dependency.name)
        dependencies_installed = True
    except ModuleNotFoundError:
        # Don't register other panels, operators etc.
        return
    for c in __classes__:
        bpy.utils.register_class(c)
    bpy.types.Scene.c2b_properties = bpy.props.PointerProperty(type=c2bProperties)

def unregister():
    for cls in preference_classes:
        bpy.utils.unregister_class(cls)
    if dependencies_installed:
        for c in reversed(__classes__):
            bpy.utils.unregister_class(c)
        del bpy.types.Object.c2b_properties

if __name__ == "__main__":
    register()