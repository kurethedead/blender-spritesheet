bl_info = {
    "name": "Spritesheet Renderer",
    "author": "Given Peace",
    "version": (1, 4),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > Spritesheet",
    "description": "Render a spritesheet from camera",
    "category": "Render",
}

import bpy
import math
import os
from mathutils import Euler
from bpy.props import (
    PointerProperty,
    StringProperty,
    IntProperty,
    FloatProperty,
    EnumProperty,
    BoolProperty,
)
from bpy.types import Panel, Operator, PropertyGroup
import numpy as np

class SpritesheetProperties(PropertyGroup):
    output_path: StringProperty(
        name="Output Path",
        description="Filepath to save the spritesheet",
        default="//spritesheet.png",
        subtype='FILE_PATH',
    )
    start_frame: IntProperty(
        name="Start Frame",
        description="Start frame of the animation",
        default=1,
        min=1,
    )
    end_frame: IntProperty(
        name="End Frame",
        description="End frame of the animation",
        default=64,
        min=1,
    )
    sprites_per_row: IntProperty(
        name="Sprites Per Row",
        description="Number of sprites per row",
        default=8,
        min=1,
    )
    sprites_per_column: IntProperty(
        name="Sprites Per Column",
        description="Number of sprites per column",
        default=8,
        min=1,
    )

class RENDER_OT_spritesheet(Operator):
    bl_idname = "render.spritesheet"
    bl_label = "Render Spritesheet"
    bl_description = "Render the spritesheet, using current render resolution as sprite size"

    def execute(self, context):
        props = context.scene.spritesheet_props

        scene = context.scene
        output_path = bpy.path.abspath(props.output_path)
        dir_path = os.path.dirname(output_path)
        
        if os.path.isdir(output_path):
            self.report({'ERROR'}, "Output path refers to a directory, must be a file path.")
            return {'CANCELLED'}

        # Set render settings
        sprite_width = scene.render.resolution_x
        sprite_height = scene.render.resolution_y
        scene.render.image_settings.file_format = 'PNG'
        scene.render.film_transparent = True

        # Spritesheet dimensions
        sprites_per_row = props.sprites_per_row
        sprites_per_column = props.sprites_per_column
        image_width = sprites_per_row * sprite_width
        image_height = sprites_per_column * sprite_height

        # Ensure output directory exists
        if not os.path.exists(dir_path):
            os.makedirs(os.path.dirname(dir_path))

        # Create a new image for the spritesheet
        spritesheet_name = "spritesheet_image"
        spritesheet = bpy.data.images.new(
            spritesheet_name,
            width=image_width,
            height=image_height,
            alpha=True,
            float_buffer=False
        )
        
        print(f"Spritesheet dimensions: {image_width}, {image_height}")

        # Store original frame and rotation
        original_frame = scene.frame_current
        
        # Calculate frames to render for animation
        start_frame = props.start_frame
        end_frame = props.end_frame
        total_frames = end_frame - start_frame + 1

        if total_frames > sprites_per_row * sprites_per_column:
            self.report({'ERROR'}, "Animation frame range is smaller than the number of sprites per row * column.")
            return {'CANCELLED'}

        block_array = []
        for i in range(total_frames):
            print(f"Frame {i}")
            row = math.floor(i / sprites_per_row)
            column = i % sprites_per_column
            
            if len(block_array) <= row:
                block_array.append([])
            block_row = block_array[row]
            
            scene.frame_set(i)

            # Update the scene
            context.view_layer.update()

            # Render
            scene.render.image_settings.file_format = 'OPEN_EXR'
            scene.render.image_settings.color_mode = 'RGBA'
            scene.render.image_settings.color_depth = '16'
            bpy.ops.render.render(write_still=False)

            render_result = bpy.data.images['Viewer Node']
            
            img = np.array(render_result.pixels[:])
            img = np.reshape(img, (sprite_height, sprite_width, 4))
            
            block_row.append(img)
            # print(f"Temp image dimensions: {img.shape}")
            
        while len(block_array[-1]) < sprites_per_row:
            block_array[-1].append(np.zeros((sprite_height, sprite_width, 4)))
            
        # print(f"First: {len(block_array[0])} - Last: {len(block_array[-1])}")
            
        # Restore original frame and rotation
        scene.frame_set(original_frame)
        
        # print(f"Block array: {block_array}")
        
        images_2d = [[np.asarray(img) for img in row] for row in block_array]
        
        # Stack images horizontally per row
        rows = [np.concatenate(row, axis=1) for row in images_2d]

        # Stack rows vertically
        grid = np.concatenate(rows, axis=0)
        
        # blender coords is upside down relative to numpy
        grid = np.flipud(grid)
        
        print(f"Block dimensions: {grid.shape}")
        spritesheet.pixels = grid.reshape(-1).tolist()  # flatten in 1 dimension, whatever size necessary

        # Save the spritesheet
        spritesheet.filepath_raw = output_path
        spritesheet.file_format = 'PNG'
        print(f"Saving final spritesheet...")
        spritesheet.save()

        # Report before removing the spritesheet
        self.report({'INFO'}, f"Spritesheet saved to {spritesheet.filepath_raw}")

        # Remove the spritesheet from memory
        bpy.data.images.remove(spritesheet)

        return {'FINISHED'}

class VIEW3D_PT_spritesheet_renderer(Panel):
    bl_label = "Spritesheet Renderer"
    bl_idname = "VIEW3D_PT_spritesheet_renderer"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Spritesheet'

    def draw(self, context):
        layout = self.layout
        props = context.scene.spritesheet_props

        layout.prop(props, "output_path")
        layout.prop(props, "sprites_per_row")
        layout.prop(props, "sprites_per_column")

        layout.prop(props, "start_frame")
        layout.prop(props, "end_frame")
        layout.operator("render.spritesheet", text="Render Spritesheet", icon='RENDER_STILL')

classes = (
    SpritesheetProperties,
    RENDER_OT_spritesheet,
    VIEW3D_PT_spritesheet_renderer,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.spritesheet_props = PointerProperty(type=SpritesheetProperties)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.spritesheet_props

if __name__ == "__main__":
    register()
