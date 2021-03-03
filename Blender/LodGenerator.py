import bpy

from bpy.props import StringProperty, EnumProperty, BoolProperty, IntProperty

bl_info = {
    "name": "LOD Generator",
    "description": "Used to generate LODs for UE4 or Unity.",
    "author": "Lari Kivirinta",
    "version": (0, 1),
    "blender": (2, 90, 0),
    "location": "Properties > Scene Properties",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "support": "TESTING",
    "category": "Game Engine",
}

def GenerateUELods(lodtool, object, context):
    
    # Create empty object with custom property and link to collection 
    empty = bpy.data.objects.new("empty", None)
    empty['fbx_type'] = "LodGroup"
    object.users_collection[0].objects.link(empty)
    
    # Parent the original object to the empty and rename to create LOD0
    object.parent = empty
    object_name = object.name
    object.name = object_name + "_LOD0"
    empty.name = object_name
    
    #Duplicate object and create the LODs
    lod_level = 1
    while lod_level < lodtool.lod_count:
        
        duplicate_object = object.copy()
        duplicate_object.data = object.data.copy()
        duplicate_object.name = object_name + "_LOD" + str(lod_level)
        object.users_collection[0].objects.link(duplicate_object)
        duplicate_object.parent = empty
        
    
        #Triangulate object to improve Decimate
        Triangulate(lodtool, duplicate_object, context)
        
        # Using decimate modifier for now for testing
        Decimate(lodtool, duplicate_object, lod_level, context)
        
        lod_level += 1
        
    return

def GenerateUnityLods(lodtool, object, context):
    
    # Create new collection and move object to that collection
    collection_name = object.name
    object_name = object.name
    lod_collection = bpy.data.collections.new(collection_name)
    parent_collection = object.users_collection[0]
    parent_collection.children.link(lod_collection)
    parent_collection.objects.unlink(object)
    lod_collection.objects.link(object)
    object.name = object_name + "_LOD0"
    
    # Duplicate object and create the LODs
    lod_level = 1
    while lod_level < lodtool.lod_count:
        
        duplicate_object = object.copy()
        duplicate_object.data = object.data.copy()
        duplicate_object.name = object_name + "_LOD" + str(lod_level)
        lod_collection.objects.link(duplicate_object)
                
        #Triangulate object to improve Decimate
        Triangulate(lodtool, duplicate_object, context)
        
        # Using decimate modifier for now for testing
        Decimate(lodtool, duplicate_object, lod_level, context)
        
        lod_level += 1
        
    return

def Triangulate(lodtool, object, context):
    mod_triangulate = object.modifiers.new(name="Triangulate", type="TRIANGULATE")
    
    if lodtool.apply_modifiers:
        context.view_layer.objects.active = object
        bpy.ops.object.modifier_apply(modifier=mod_triangulate.name)
    
    return

def Decimate(lodtool, object, lod_level, context):
    mod_decimate = object.modifiers.new(name="LodDecimate" + "_LOD" + str(lod_level), type="DECIMATE")
    mod_decimate.decimate_type = "COLLAPSE"
    mod_decimate.ratio = 1 / pow(2, lod_level)
    
    if lodtool.apply_modifiers:
        context.view_layer.objects.active = object
        bpy.ops.object.modifier_apply(modifier=mod_decimate.name)
    
    return


class CreateProperties(bpy.types.PropertyGroup):
    
    lod_count : IntProperty(
        name="LOD count",
        description="How many LODs are created, including LOD0",
        default=3,
        min=1,
        soft_max=10)
    
    game_engine: EnumProperty(
        name="Game Engine",
        description="Select game engine",
        default="UE4",
        items= [("UE4", "UE4", "Unreal Engine 4"),
                ("Unity", "Unity", "Unity")])
    
    join_objects : BoolProperty(
        name="Join selected",
        description="Joins all selected objects. Otherwise create LODs separately for each.")
    
    apply_modifiers : BoolProperty(
        name="Apply Modifiers",
        description="Whether or not to apply modifiers created during the generation")


class CreatePanel(bpy.types.Panel):
    bl_label = "Generate LODs"
    bl_idname = "OBJECT_PT_lod_generator_panel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'scene'

    def draw(self, context):
        layout = self.layout
        if context.active_object is not None:
            if context.active_object.mode == 'OBJECT':
                scene = context.scene
                lodtool = scene.lodtool
                row = layout.row()
                layout.prop(lodtool, "game_engine")
                row = layout.row()
                layout.prop(lodtool, "lod_count")
                row = layout.row()
                layout.prop(lodtool, "join_objects")
                row = layout.row()
                layout.prop(lodtool, "apply_modifiers")
                row = layout.row()
                row.operator("lod_generator.generate")
            else:            
                layout.label(text="Available only in Object Mode")


class GenerateLods(bpy.types.Operator):
    bl_label = "Generate"
    bl_idname = "lod_generator.generate"
    bl_options = {"REGISTER", "UNDO"}
    
    def execute(self, context):
        scene = context.scene
        lodtool = scene.lodtool
        
        active_object = context.active_object
        selected_objects = context.selected_objects
        
        #  check we have an active object and objects selected
        if active_object is None:
            print("No active object")
            return {'CANCELLED'}
        
        if len(selected_objects) == 0:
            print("No selected objects")
            return {'CANCELLED'}        
        
        # Check all objects have data
        for object in selected_objects:
            if object.data is None:
                print("No data found in object: " + object.name)
                return {'CANCELLED'}
        
        #  Create backups from original files
        for object in selected_objects:
            duplicate_object = object.copy()
            duplicate_object.data = object.data.copy()
            duplicate_object.name = object.name + "_Backup"
            object.users_collection[0].objects.link(duplicate_object)
            duplicate_object.hide_set(True)
        
        #Either join objects or process each object separately
        if lodtool.join_objects and len(selected_objects) > 1:
            bpy.ops.object.join()
            if lodtool.game_engine == "UE4":
                GenerateUELods(lodtool, active_object, context)
            elif lodtool.game_engine == "Unity":
                GenerateUnityLods(lodtool, active_object, context)
                
        else:
            for object in selected_objects:
                if lodtool.game_engine == "UE4":
                    GenerateUELods(lodtool, object, context)    
                elif lodtool.game_engine == "Unity":
                    GenerateUnityLods(lodtool, object, context)
        
        context.view_layer.objects.active = None
        bpy.ops.object.select_all(action='DESELECT')
        
        return {'FINISHED'}

def register():
    bpy.utils.register_class(CreateProperties)
    bpy.types.Scene.lodtool = bpy.props.PointerProperty(type=CreateProperties)
    bpy.utils.register_class(CreatePanel)
    bpy.utils.register_class(GenerateLods)


def unregister():
    bpy.utils.unregister_class(CreateProperties)
    bpy.utils.unregister_class(CreatePanel)
    bpy.utils.unregister_class(GenerateLods)
    del bpy.types.Scene.lodtool


if __name__ == "__main__":
    register()