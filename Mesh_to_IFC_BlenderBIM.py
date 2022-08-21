bl_info = {
    "name": "Mesh to BIM",
    "author": "K. Tomova",
    "version": (1, 0),
    "blender": (3, 1, 2),
    "location": "",
    "description": "Fast IFC class, storey, and material assignment",
    "warning": "",
    "doc_url": "",
    "category": "",
}

import bpy
import ifcopenshell

# for IFC Classes
import blenderbim.bim.module.root.prop as root_prop
from blenderbim.bim.module.root.data import IfcClassData

# for Storeys
from bpy.types import Panel, UIList
from blenderbim.bim.ifc import IfcStore
from blenderbim.bim.module.spatial.data import SpatialData

# for Materials
import blenderbim.bim.helper_new
from bpy.types import Panel, UIList
from ifcopenshell.api.material.data import Data
from ifcopenshell.api.profile.data import Data as ProfileData
from blenderbim.bim.ifc import IfcStore
from blenderbim.bim.helper_new import draw_attributes
from blenderbim.bim.helper_new import prop_with_search
from blenderbim.bim.module.material.data import MaterialsData, ObjectMaterialData


# !!! I M P O R T A N T !!!   -   for this script to run you need the newest version of 'heper.py'
# best found here: https://github.com/IfcOpenShell/IfcOpenShell/blob/ffe9ac6614268e53f654e280f5f8e88cc8fea241/src/blenderbim/blenderbim/bim/helper.py
# please save it as 'helper_new.py'


class Mesh_to_IFC(bpy.types.Panel):
    bl_label = "Mesh to IFC"
    bl_idname = "PT_IFC_Class"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'QuickIFC'

    def draw(self, context):
        layout = self.layout

        obj = context.object


    @classmethod
    def poll(cls, context):
        if not context.active_object:
            return False
        return IfcStore.get_file()

    def draw(self, context):
        if not IfcClassData.is_loaded:
            IfcClassData.load()
        props = context.active_object.BIMObjectProperties
        if props.ifc_definition_id:
            if not IfcClassData.data["has_entity"]:
                row = self.layout.row(align=True)
                row.label(text="IFC Element Not Found")
                row.operator("bim.unlink_object", icon="UNLINKED", text="")
                return
            if props.is_reassigning_class:
                row = self.layout.row(align=True)
                row.operator("bim.reassign_class", icon="CHECKMARK")
                row.operator("bim.disable_reassign_class", icon="CANCEL", text="")
                self.draw_class_dropdowns(
                    context,
                    root_prop.getIfcPredefinedTypes(context.scene.BIMRootProperties, context),
                    is_reassigning_class=True,
                )
            else:
                row = self.layout.row(align=True)
                row.label(text=IfcClassData.data["name"])
                op = row.operator("bim.select_ifc_class", text="", icon="RESTRICT_SELECT_OFF")
                op.ifc_class = IfcClassData.data["ifc_class"]
                row.operator("bim.unlink_object", icon="UNLINKED", text="")
                if IfcStore.get_file().by_id(props.ifc_definition_id).is_a("IfcRoot"):
                    row.operator("bim.enable_reassign_class", icon="GREASEPENCIL", text="")
        else:
            ifc_predefined_types = root_prop.getIfcPredefinedTypes(context.scene.BIMRootProperties, context)
            self.draw_class_dropdowns(context, ifc_predefined_types)
            row = self.layout.row(align=True)
            op = row.operator("bim.assign_class")
            op.ifc_class = context.scene.BIMRootProperties.ifc_class
            op.predefined_type = context.scene.BIMRootProperties.ifc_predefined_type if ifc_predefined_types else ""
            op.userdefined_type = context.scene.BIMRootProperties.ifc_userdefined_type

    def draw_class_dropdowns(self, context, ifc_predefined_types, is_reassigning_class=False):
        props = context.scene.BIMRootProperties
        if not is_reassigning_class:
            row = self.layout.row()
            row.prop(props, "ifc_product")
        row = self.layout.row()
        row.prop(props, "ifc_class")
        if ifc_predefined_types:
            row = self.layout.row()
            row.prop(props, "ifc_predefined_type")
        if ifc_predefined_types == "USERDEFINED":
            row = self.layout.row()
            row.prop(props, "ifc_userdefined_type")
        if not is_reassigning_class:
            row = self.layout.row()
            row.prop(context.scene.BIMRootProperties, "contexts")
            


            
class Building_storey(bpy.types.Panel):
    bl_label = "Building storey"
    bl_idname = "PT_Building_storey"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'QuickIFC'

    def draw(self, context):
        layout = self.layout

        layout.operator("wm.template_operator")
    
    
    @classmethod
    def poll(cls, context):
        if not context.active_object:
            return False
        oprops = context.active_object.BIMObjectProperties
        if not oprops.ifc_definition_id:
            return True
        if not IfcStore.get_element(oprops.ifc_definition_id):
            return False
        return True

    def draw(self, context):
        if not SpatialData.is_loaded:
            SpatialData.load()

        props = context.scene.BIMSpatialProperties
        osprops = context.active_object.BIMObjectSpatialProperties

        if osprops.is_editing:
            row = self.layout.row(align=True)
            if SpatialData.data["parent_container_id"]:
                op = row.operator("bim.change_spatial_level", text="", icon="FRAME_PREV")
                op.parent = SpatialData.data["parent_container_id"]
            if props.containers and props.active_container_index < len(props.containers):
                op = row.operator("bim.assign_container", icon="CHECKMARK")
                op.structure = props.containers[props.active_container_index].ifc_definition_id
            row.operator("bim.disable_editing_container", icon="CANCEL", text="")

            self.layout.template_list("BIM_UL_containers", "", props, "containers", props, "active_container_index")
        
        else:
            row = self.layout.row(align=True)
            if SpatialData.data["is_contained"]:
                row.label(text=SpatialData.data["label"])
                row.operator("bim.enable_editing_container", icon="GREASEPENCIL", text="")
                if SpatialData.data["is_directly_contained"]:
                    row.operator("bim.remove_container", icon="X", text="")
            else:
                row.label(text="No storey assigned yet")
                row.operator("bim.enable_editing_container", icon="GREASEPENCIL", text="")            
            
            
class BIM_UL_containers(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if item:
            if item.has_decomposition:
                op = layout.operator("bim.change_spatial_level", text="", icon="DISCLOSURE_TRI_RIGHT", emboss=False)
                op.parent = item.ifc_definition_id
            layout.label(text=item.name)
            layout.label(text=item.long_name)
            
            
            
class IFC_Material(Panel):
    bl_label = "IFC Object Material"
    bl_idname = "BIM_PT_object_material_1"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'QuickIFC'
               
    @classmethod
      
    def poll(cls, context):
        if not context.active_object:
            return False
        props = context.active_object.BIMObjectProperties
        if not props.ifc_definition_id:
            return False
        if not IfcStore.get_element(props.ifc_definition_id):
            return False
        if not hasattr(IfcStore.get_file().by_id(props.ifc_definition_id), "HasAssociations"):
            return False
        return True
    

    def draw(self, context):
        if not ObjectMaterialData.is_loaded:
            ObjectMaterialData.load()

        self.file = IfcStore.get_file()
        self.oprops = context.active_object.BIMObjectProperties
        self.props = context.active_object.BIMObjectMaterialProperties
        if not Data.is_loaded:
            Data.load(IfcStore.get_file())
        if self.oprops.ifc_definition_id not in Data.products:
            Data.load(IfcStore.get_file(), self.oprops.ifc_definition_id)
        if not ProfileData.is_loaded:
            ProfileData.load(self.file)
        self.product_data = Data.products[self.oprops.ifc_definition_id]

        if ObjectMaterialData.data["type_material"]:
            row = self.layout.row(align=True)
            row.label(text="Inherited Material: " + ObjectMaterialData.data["type_material"], icon="FILE_PARENT")

        if self.product_data:
            if self.product_data["type"] == "IfcMaterialConstituentSet":
                self.material_set_id = self.product_data["id"]
                self.material_set_data = Data.constituent_sets[self.material_set_id]
                self.set_items = self.material_set_data["MaterialConstituents"] or []
                self.set_data = Data.constituents
                self.set_item_name = "constituent"
            elif self.product_data["type"] == "IfcMaterialLayerSet":
                self.material_set_id = self.product_data["id"]
                self.material_set_data = Data.layer_sets[self.material_set_id]
                self.set_items = self.material_set_data["MaterialLayers"] or []
                self.set_data = Data.layers
                self.set_item_name = "layer"
            elif self.product_data["type"] == "IfcMaterialLayerSetUsage":
                self.material_set_usage = Data.layer_set_usages[self.product_data["id"]]
                self.material_set_id = self.material_set_usage["ForLayerSet"]
                self.material_set_data = Data.layer_sets[self.material_set_id]
                self.set_items = self.material_set_data["MaterialLayers"] or []
                self.set_data = Data.layers
                self.set_item_name = "layer"
            elif self.product_data["type"] == "IfcMaterialProfileSet":
                self.material_set_id = self.product_data["id"]
                self.material_set_data = Data.profile_sets[self.material_set_id]
                self.set_items = self.material_set_data["MaterialProfiles"] or []
                self.set_data = Data.profiles
                self.set_item_name = "profile"
            elif self.product_data["type"] == "IfcMaterialProfileSetUsage":
                self.material_set_usage = Data.profile_set_usages[self.product_data["id"]]
                self.material_set_id = self.material_set_usage["ForProfileSet"]
                self.material_set_data = Data.profile_sets[self.material_set_id]
                self.set_items = self.material_set_data["MaterialProfiles"] or []
                self.set_data = Data.profiles
                self.set_item_name = "profile"
            elif self.product_data["type"] == "IfcMaterialList":
                self.material_set_id = self.product_data["id"]
                self.material_set_data = Data.lists[self.material_set_id]
                self.set_items = self.material_set_data["Materials"] or []
                self.set_item_name = "list_item"
            else:
                self.material_set_id = 0
            return self.draw_material_ui()

        row = self.layout.row(align=True)
        if self.props.material_type == "IfcMaterial" or self.props.material_type == "IfcMaterialList":
            row.label(text="No material assigned yet")
        row = self.layout.row(align=True)
        prop_with_search(row, self.props, "material", text="")
        row.operator("bim.assign_material", icon="ADD", text="")

    def draw_material_ui(self):
        row = self.layout.row(align=True)
        row.label(text=self.product_data["type"])

        if self.props.is_editing:
            op = row.operator("bim.edit_assigned_material", icon="CHECKMARK", text="")
            op.material_set = self.material_set_id
            if "Usage" in self.product_data["type"]:
                op.material_set_usage = self.product_data["id"]
            row.operator("bim.disable_editing_assigned_material", icon="CANCEL", text="")
        else:
            if self.product_data["type"] == "IfcMaterial":
                row.operator("bim.unassign_material", icon="UNLINKED", text="")
                row.operator("bim.enable_editing_assigned_material", icon="GREASEPENCIL", text="")

        if self.product_data["type"] == "IfcMaterial":
            self.draw_single_ui()
        else:
            self.draw_set_ui()

    def draw_single_ui(self):
        if self.props.is_editing:
            return self.draw_editable_single_ui()
        return self.draw_read_only_single_ui()

    def draw_editable_single_ui(self):
        prop_with_search(self.layout, self.props, "material", text="")

    def draw_read_only_single_ui(self):
        material = Data.materials[self.product_data["id"]]
        row = self.layout.row(align=True)
        row.label(text="Material name")
        row.label(text=material["Name"])
 


classes = [Mesh_to_IFC, Building_storey, BIM_UL_containers, IFC_Material]
 
 
 
def register():
    for cls in classes:
        bpy.utils.register_class(cls)
 
def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
 
 
 
if __name__ == "__main__":
    register()  