bl_info = {
    "name": "IDENTILIBRARY PLUS",
    "author": "GABRIELE RANFAGNI 2025 ®IDENTIRIG®",
    "version": (4, 7),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > IDENTIRIG_PLUS",
    "description": "A FULL COMPLETE LIBRARY FOR IDENTIRIG PLUS WITH ULTRA FULL WIDTH UI AND VIEWPORT SNAPSHOTS",
    "category": "3D View"
}

import bpy
import json
import os
import ftplib
import threading
import tempfile
from bpy.props import (StringProperty, EnumProperty, BoolProperty, IntProperty, 
                      CollectionProperty, PointerProperty)
from bpy.types import Operator, Panel, AddonPreferences, PropertyGroup

ftp_file_list = []
local_file_list = []
character_origin_frames = {}
previous_character = None

TYPES = [
    ("HAIR", "Hair", ""),
    ("BEARD", "Beard", ""),
    ("EYEBROWS_GN", "Eyebrows", ""),
    ("ACCESSORIES", "Accessories", "")
]

# === CHARACTER PREVIEW ITEM CLASS ===
class CharacterPreviewItem(PropertyGroup):
    name: StringProperty()
    preview_path: StringProperty()
    has_preview: BoolProperty(default=False)
    is_cached: BoolProperty(default=False)
    is_ftp: BoolProperty(default=False)

class LibraryPreviewProps(PropertyGroup):
    show_thumbnails: BoolProperty(
        name="Show Character Previews",
        default=True,
        description="Show character preview snapshots instead of text list"
    )
    thumbnail_size: IntProperty(
        name="Preview Size",
        default=150,
        min=100,
        max=300,
        description="Size of character preview thumbnails"
    )
    
    # Character collections
    local_character_collection: CollectionProperty(type=CharacterPreviewItem)
    ftp_character_collection: CollectionProperty(type=CharacterPreviewItem)

# --- Scene properties for Identirig Library ---
bpy.types.Scene.library_path        = StringProperty(name="Library Path", subtype='DIR_PATH')
bpy.types.Scene.character_name      = StringProperty(name="Character Name")
bpy.types.Scene.chosen_type         = EnumProperty(name="Type", items=TYPES, default="HAIR")
bpy.types.Scene.ftp_selected_file   = EnumProperty(name="FTP Characters", items=lambda self, context: ftp_file_list)
bpy.types.Scene.local_selected_file = EnumProperty(name="Local Characters", items=lambda self, context: local_file_list)
bpy.types.Scene.replace_grooming    = BoolProperty(name="Replace Content", default=True)
bpy.types.Scene.transition_frames   = IntProperty(name="Transition Frames", default=10, min=0)
bpy.types.Scene.do_morphing         = BoolProperty(name="Morphing Transition", default=False)
bpy.types.Scene.save_preset         = BoolProperty(name="Save Preset", default=False)
bpy.types.Scene.save_displacement   = BoolProperty(name="Save Displacement", default=True)
bpy.types.Scene.load_displacement   = BoolProperty(name="Load Displacement", default=True)
bpy.types.Scene.auto_connect        = BoolProperty(name="Auto Connect to Rig", default=True)

# ----------------------
# VIEWPORT RENDER SNAPSHOT FUNCTIONS
# ----------------------
def capture_viewport_snapshot(character_name, library_path):
    """VIEWPORT RENDER DIRETTO - solo il frame 3D in 16:9"""
    try:
        print(f"📸 Capturing VIEWPORT RENDER for {character_name}...")
        
        # Crea path corretto
        preview_filename = f"{character_name}_preview.jpg"
        preview_path = os.path.join(library_path, preview_filename)
        
        print(f"🎯 Target path: {preview_path}")
        os.makedirs(library_path, exist_ok=True)
        
        # TROVA LA VIEW3D AREA ATTIVA
        view3d_area = None
        view3d_space = None
        view3d_region = None
        
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                view3d_area = area
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        view3d_space = space
                        break
                for region in area.regions:
                    if region.type == 'WINDOW':
                        view3d_region = region
                        break
                break
        
        if not view3d_area or not view3d_space or not view3d_region:
            print("❌ No valid View3D found for viewport render")
            return None
        
        print(f"🎬 Found View3D: {view3d_region.width}x{view3d_region.height}")
        
        # METODO 1: VIEWPORT RENDER DIRETTO
        try:
            # Override context per la view3d specifica
            override_context = {
                'area': view3d_area,
                'space_data': view3d_space,
                'region': view3d_region,
                'scene': bpy.context.scene,
                'view_layer': bpy.context.view_layer
            }
            
            # SALVA render settings originali
            original_filepath = bpy.context.scene.render.filepath
            original_resolution_x = bpy.context.scene.render.resolution_x
            original_resolution_y = bpy.context.scene.render.resolution_y
            original_file_format = bpy.context.scene.render.image_settings.file_format
            original_quality = bpy.context.scene.render.image_settings.quality
            
            # CALCOLA dimensioni 16:9 basate sulla viewport
            viewport_width = view3d_region.width
            viewport_height = view3d_region.height
            
            # Forza 16:9 aspect ratio
            target_width = 400  # Base width
            target_height = int(target_width * 9 / 16)  # 225 per 16:9
            
            print(f"📐 Viewport: {viewport_width}x{viewport_height}")
            print(f"📐 Target: {target_width}x{target_height} (16:9)")
            
            # Imposta render settings per viewport
            bpy.context.scene.render.filepath = preview_path
            bpy.context.scene.render.resolution_x = target_width
            bpy.context.scene.render.resolution_y = target_height
            bpy.context.scene.render.image_settings.file_format = 'JPEG'
            bpy.context.scene.render.image_settings.quality = 90
            
            # Update scene
            bpy.context.view_layer.update()
            
            # RENDER VIEWPORT con override context
            with bpy.context.temp_override(**override_context):
                bpy.ops.render.opengl(write_still=True)
            
            # RIPRISTINA settings immediatamente
            bpy.context.scene.render.filepath = original_filepath
            bpy.context.scene.render.resolution_x = original_resolution_x
            bpy.context.scene.render.resolution_y = original_resolution_y
            bpy.context.scene.render.image_settings.file_format = original_file_format
            bpy.context.scene.render.image_settings.quality = original_quality
            
            # Verifica risultato
            if os.path.exists(preview_path):
                file_size = os.path.getsize(preview_path)
                print(f"✅ VIEWPORT RENDER SUCCESS! Size: {file_size} bytes")
                print(f"✅ Preview saved: {preview_path}")
                return preview_path
            else:
                print("❌ Viewport render failed - file not created")
                
        except Exception as viewport_error:
            print(f"❌ Viewport render error: {viewport_error}")
            
            # Ripristina settings anche in caso di errore
            try:
                bpy.context.scene.render.filepath = original_filepath
                bpy.context.scene.render.resolution_x = original_resolution_x
                bpy.context.scene.render.resolution_y = original_resolution_y
                bpy.context.scene.render.image_settings.file_format = original_file_format
                bpy.context.scene.render.image_settings.quality = original_quality
            except:
                pass
        
        # FALLBACK: Screenshot diretto (ultimo tentativo)
        print("🔄 Trying direct screenshot fallback...")
        try:
            bpy.ops.screen.screenshot(filepath=preview_path)
            
            if os.path.exists(preview_path):
                # Ridimensiona a 16:9
                try:
                    temp_name = f"temp_resize_{character_name}"
                    if temp_name in bpy.data.images:
                        bpy.data.images.remove(bpy.data.images[temp_name])
                    
                    img = bpy.data.images.load(preview_path)
                    img.name = temp_name
                    img.scale(400, 225)  # 16:9
                    img.filepath_raw = preview_path
                    img.file_format = 'JPEG'
                    img.save()
                    
                    bpy.data.images.remove(img)
                    print(f"✅ Screenshot fallback success: {preview_path}")
                    return preview_path
                    
                except Exception as resize_error:
                    print(f"⚠️ Resize failed: {resize_error} - keeping original")
                    return preview_path
            
        except Exception as screenshot_error:
            print(f"❌ Screenshot fallback failed: {screenshot_error}")
        
        print("❌ All viewport render methods failed")
        return None
        
    except Exception as e:
        print(f"❌ Viewport render completely failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def load_character_preview_into_blender(preview_path, character_name, source_type="local"):
    """Load character preview image into Blender's image system"""
    try:
        if not os.path.exists(preview_path):
            print(f"❌ Preview not found: {preview_path}")
            return None
        
        thumb_name = f"library_preview_{source_type}_{character_name}"
        
        # Remove existing if any
        if thumb_name in bpy.data.images:
            bpy.data.images.remove(bpy.data.images[thumb_name])
        
        # Load fresh
        print(f"🖼️ Loading character preview: {thumb_name}")
        image = bpy.data.images.load(preview_path)
        image.name = thumb_name
        
        # Force preview generation
        image.reload()
        if hasattr(image, 'preview_ensure'):
            image.preview_ensure()
        
        print(f"✅ Character preview loaded: {thumb_name}")
        return image
        
    except Exception as e:
        print(f"❌ Failed to load character preview: {e}")
        return None

def scan_local_characters_with_previews(library_path):
    """Scan local library for characters and their previews"""
    try:
        if not os.path.isdir(library_path):
            print(f"⚠️ Library path not found: {library_path}")
            return []
        
        print(f"🔍 Scanning local library for characters...")
        
        character_files = []
        preview_files = []
        
        for file in os.listdir(library_path):
            if file.endswith('_gui.json'):
                character_files.append(file)
            elif file.endswith('_preview.jpg'):
                preview_files.append(file)
        
        print(f"✅ Found {len(character_files)} character files")
        print(f"✅ Found {len(preview_files)} preview files")
        
        # Match characters with previews
        matched_characters = []
        for char_file in character_files:
            char_name = char_file.replace('_gui.json', '')
            
            # Find corresponding preview
            preview_file = f"{char_name}_preview.jpg"
            has_preview = preview_file in preview_files
            
            if has_preview:
                print(f"🎯 Character with preview: {char_name}")
            else:
                print(f"⚠️ No preview for: {char_name}")
            
            matched_characters.append({
                'name': char_name,
                'preview': preview_file if has_preview else None,
                'has_preview': has_preview
            })
        
        return matched_characters
        
    except Exception as e:
        print(f"❌ Local character scan failed: {e}")
        return []

def scan_ftp_characters_with_previews():
    """Scan FTP for characters and their previews"""
    try:
        print("🔍 Scanning FTP server for characters...")
        ftp = ftplib.FTP('ftp.workshops.homepc.it')
        ftp.login()
        ftp.cwd('/FTP/LIBRARY')
        
        file_list = []
        ftp.retrlines('LIST', file_list.append)
        
        character_files = []
        preview_files = []
        
        for line in file_list:
            filename = line.split()[-1]
            if filename.endswith('_gui.json'):
                character_files.append(filename)
            elif filename.endswith('_preview.jpg'):
                preview_files.append(filename)
        
        ftp.quit()
        
        print(f"✅ Found {len(character_files)} FTP character files")
        print(f"✅ Found {len(preview_files)} FTP preview files")
        
        # Match characters with previews
        matched_characters = []
        for char_file in character_files:
            char_name = char_file.replace('_gui.json', '')
            
            # Find corresponding preview
            preview_file = f"{char_name}_preview.jpg"
            has_preview = preview_file in preview_files
            
            if has_preview:
                print(f"🎯 FTP Character with preview: {char_name}")
            else:
                print(f"⚠️ No FTP preview for: {char_name}")
            
            matched_characters.append({
                'name': char_name,
                'preview': preview_file if has_preview else None,
                'has_preview': has_preview
            })
        
        return matched_characters
        
    except Exception as e:
        print(f"❌ FTP character scan failed: {e}")
        return []

def download_ftp_preview(preview_filename):
    """Download single preview from FTP server"""
    try:
        ftp = ftplib.FTP('ftp.workshops.homepc.it')
        ftp.login()
        ftp.cwd('/FTP/LIBRARY')
        
        cache_dir = os.path.join(tempfile.gettempdir(), "identirig_library_cache")
        os.makedirs(cache_dir, exist_ok=True)
        local_path = os.path.join(cache_dir, preview_filename)
        
        if not os.path.exists(local_path):
            print(f"📥 Downloading FTP preview: {preview_filename}")
            with open(local_path, 'wb') as f:
                ftp.retrbinary(f'RETR {preview_filename}', f.write)
            print(f"✅ Downloaded FTP preview: {preview_filename}")
        else:
            print(f"💾 Using cached FTP preview: {preview_filename}")
        
        ftp.quit()
        return local_path
    except Exception as e:
        print(f"❌ FTP preview download failed for {preview_filename}: {e}")
        return None

def upload_preview_to_ftp(local_preview_path, character_name):
    """Upload character preview to FTP server"""
    try:
        if not os.path.exists(local_preview_path):
            print(f"❌ Local preview not found: {local_preview_path}")
            return False
        
        print(f"📤 Uploading preview to FTP: {character_name}_preview.jpg")
        
        ftp = ftplib.FTP('ftp.workshops.homepc.it')
        ftp.login()
        ftp.cwd('/FTP/LIBRARY')
        
        remote_filename = f"{character_name}_preview.jpg"
        
        with open(local_preview_path, 'rb') as f:
            ftp.storbinary(f'STOR {remote_filename}', f)
        
        ftp.quit()
        print(f"✅ Preview uploaded to FTP: {remote_filename}")
        return True
        
    except Exception as e:
        print(f"❌ FTP preview upload failed: {e}")
        return False

def download_complete_ftp_character(character_name, library_path):
    """Download complete character data from FTP server"""
    try:
        print(f"📥 Downloading complete character data: {character_name}")
        
        ftp = ftplib.FTP('ftp.workshops.homepc.it')
        ftp.login()
        ftp.cwd('/FTP/LIBRARY')
        
        # Download GUI file
        gui_file = f"{character_name}_gui.json"
        local_gui_path = os.path.join(library_path, gui_file)
        if gui_file in ftp.nlst():
            with open(local_gui_path, 'wb') as f:
                ftp.retrbinary(f'RETR {gui_file}', f.write)
            print(f"✅ Downloaded: {gui_file}")
        
        # Download character directory for each type
        for type_name in ["HAIR", "BEARD", "EYEBROWS_GN", "ACCESSORIES"]:
            remote_char_dir = f"{type_name}/{character_name}"
            local_char_dir = os.path.join(library_path, type_name, character_name)
            
            try:
                ftp.cwd(f'/FTP/LIBRARY/{remote_char_dir}')
                os.makedirs(local_char_dir, exist_ok=True)
                
                # Download all files in character directory
                file_list = ftp.nlst()
                for file_name in file_list:
                    if not file_name.startswith('.'):  # Skip hidden files
                        local_file_path = os.path.join(local_char_dir, file_name)
                        with open(local_file_path, 'wb') as f:
                            ftp.retrbinary(f'RETR {file_name}', f.write)
                        print(f"✅ Downloaded: {remote_char_dir}/{file_name}")
                
                ftp.cwd('/FTP/LIBRARY')  # Return to base directory
                
            except Exception as type_error:
                # Type directory doesn't exist - this is normal
                print(f"ℹ️ No {type_name} data for {character_name}")
        
        # Download displacement data if exists
        try:
            ftp.cwd('/FTP/LIBRARY/displacement')
            disp_file = f"{character_name}_displacement.json"
            if disp_file in ftp.nlst():
                local_disp_dir = os.path.join(library_path, "displacement")
                os.makedirs(local_disp_dir, exist_ok=True)
                local_disp_path = os.path.join(local_disp_dir, disp_file)
                with open(local_disp_path, 'wb') as f:
                    ftp.retrbinary(f'RETR {disp_file}', f.write)
                print(f"✅ Downloaded displacement: {disp_file}")
        except:
            print(f"ℹ️ No displacement data for {character_name}")
        
        ftp.quit()
        print(f"🎉 Complete character download finished: {character_name}")
        return True
        
    except Exception as e:
        print(f"❌ Complete character download failed: {e}")
        return False

# ----------------------
# RIG HELPER FUNCTIONS (UNCHANGED)
# ----------------------
def find_active_rig_collection(context):
    """Find active rig collection using STARTSWITH case insensitive for robustness"""
    active_rig = context.scene.identirig_active_library
    if not active_rig:
        return None
    
    rig_collection = None
    active_rig_lower = active_rig.split('.')[0].lower()
    for coll in bpy.data.collections:
        if coll.name.lower().startswith(active_rig_lower):
            rig_collection = coll
            break
    
    return rig_collection

def find_geo_collection_in_rig(rig_collection):
    """Find GEO collection inside a rig using STARTSWITH case insensitive"""
    if not rig_collection:
        return None
    
    for child_coll in rig_collection.children:
        if child_coll.name.lower().startswith("geo"):
            return child_coll
    return None

def find_gui_collection_in_rig(rig_collection):
    """Find GUI collection inside a rig using STARTSWITH case insensitive"""
    if not rig_collection:
        return None
    
    for child_coll in rig_collection.children:
        if child_coll.name.lower().startswith("gui"):
            return child_coll
    return None

def find_head_object_in_rig(rig_collection):
    """Find HEAD object in rig using STARTSWITH case insensitive"""
    if not rig_collection:
        return None
    
    geo_collection = find_geo_collection_in_rig(rig_collection)
    if geo_collection:
        for obj in geo_collection.objects:
            if obj.name.lower().startswith("head_master_mesh"):
                return obj
    
    for obj in rig_collection.all_objects:
        if obj.name.lower().startswith("head"):
            return obj
    return None

def find_grooming_collection_in_rig(rig_collection):
    """Find or create GROOMING collection inside rig's GEO"""
    if not rig_collection:
        return None
    
    geo_collection = find_geo_collection_in_rig(rig_collection)
    if not geo_collection:
        return None
    
    grooming_coll = None
    for child in geo_collection.children:
        if child.name.lower().startswith("grooming"):
            grooming_coll = child
            break
    
    if not grooming_coll:
        grooming_coll = bpy.data.collections.new("GROOMING")
        geo_collection.children.link(grooming_coll)
        print(f"✅ Created GROOMING collection in {geo_collection.name}")
    
    return grooming_coll

def find_accessories_collection_in_rig(rig_collection):
    """Find or create ACCESSORIES collection inside rig's GEO"""
    if not rig_collection:
        return None
    
    geo_collection = find_geo_collection_in_rig(rig_collection)
    if not geo_collection:
        return None
    
    accessories_coll = None
    for child in geo_collection.children:
        child_name_lower = child.name.lower()
        if child_name_lower.startswith("accessor"):
            accessories_coll = child
            break
    
    if not accessories_coll:
        accessories_coll = bpy.data.collections.new("ACCESSORIES")
        geo_collection.children.link(accessories_coll)
        print(f"✅ Created ACCESSORIES collection in {geo_collection.name}")
    
    return accessories_coll

def aggressive_surface_deform_bind(obj, head_obj, context, obj_name_lower):
    """AGGRESSIVE Surface Deform binding system"""
    
    for mod in obj.modifiers:
        if mod.type == 'SURFACE_DEFORM':
            print(f"🔍 ANALYZING SurfaceDeform on {obj.name}:")
            print(f"   - Modifier name: {mod.name}")
            print(f"   - Target: {mod.target.name if mod.target else 'NONE'}")
            print(f"   - Is bound: {mod.is_bound}")
            print(f"   - Show viewport: {mod.show_viewport}")
            print(f"   - Show render: {mod.show_render}")
            
            # Check for beard and hair specifically
            is_beard_or_hair = obj_name_lower.startswith("identirig_basebeard") or obj_name_lower.startswith("identirig_basehaircut")
            
            if is_beard_or_hair:
                print(f"   🎯 BEARD/HAIR detected - FORCING bind")
                
                # Ensure modifier is enabled and has target
                if mod.target:
                    # Force enable everything
                    mod.show_viewport = True
                    mod.show_render = True
                    mod.show_in_editmode = True
                    mod.show_on_cage = True
                    
                    # Ensure we're in object mode
                    if context.mode != 'OBJECT':
                        bpy.ops.object.mode_set(mode='OBJECT')
                    
                    # Select only this object
                    bpy.ops.object.select_all(action='DESELECT')
                    obj.select_set(True)
                    context.view_layer.objects.active = obj
                    
                    print(f"   🔄 Object selected: {context.view_layer.objects.active.name}")
                    
                    # Multiple unbind attempts if already bound
                    if mod.is_bound:
                        print(f"   🔓 Attempting to unbind existing...")
                        for attempt in range(3):
                            try:
                                bpy.ops.object.surfacedeform_bind(modifier=mod.name, unbind=True)
                                print(f"   ✅ Unbind attempt {attempt+1} successful")
                                break
                            except Exception as e:
                                print(f"   ⚠️ Unbind attempt {attempt+1} failed: {e}")
                    
                    # Force bind with multiple attempts
                    print(f"   🔗 Attempting to bind...")
                    bind_success = False
                    for attempt in range(5):
                        try:
                            # Ensure we're still selected
                            bpy.ops.object.select_all(action='DESELECT')
                            obj.select_set(True)
                            context.view_layer.objects.active = obj
                            
                            # Force refresh the scene
                            bpy.context.view_layer.update()
                            
                            # Attempt bind
                            bpy.ops.object.surfacedeform_bind(modifier=mod.name)
                            
                            # Check if it worked
                            if mod.is_bound:
                                print(f"   ✅ BIND SUCCESSFUL on attempt {attempt+1}!")
                                bind_success = True
                                break
                            else:
                                print(f"   ⚠️ Bind attempt {attempt+1} - modifier not bound")
                                
                        except Exception as e:
                            print(f"   ❌ Bind attempt {attempt+1} failed: {e}")
                    
                    if not bind_success:
                        print(f"   ❌ ALL BIND ATTEMPTS FAILED for {obj.name}")
                        # Try manual bind approach
                        print(f"   🔧 Trying manual bind approach...")
                        try:
                            # Clear and reset the modifier
                            mod.target = None
                            bpy.context.view_layer.update()
                            mod.target = head_obj
                            bpy.context.view_layer.update()
                            
                            # Try bind again
                            bpy.ops.object.surfacedeform_bind(modifier=mod.name)
                            if mod.is_bound:
                                print(f"   ✅ MANUAL BIND SUCCESSFUL!")
                            else:
                                print(f"   ❌ MANUAL BIND ALSO FAILED")
                        except Exception as e:
                            print(f"   ❌ Manual bind failed: {e}")
                            
                else:
                    print(f"   ❌ No target set for SurfaceDeform on {obj.name}")
            else:
                # For eyebrows - gentle approach
                if not mod.is_bound and mod.target:
                    bpy.ops.object.select_all(action='DESELECT')
                    obj.select_set(True)
                    context.view_layer.objects.active = obj
                    try:
                        bpy.ops.object.surfacedeform_bind(modifier=mod.name)
                        print(f"   ✅ SurfaceDeform gentle bind executed on {obj.name}")
                    except Exception as e:
                        print(f"   ⚠️ SurfaceDeform gentle bind failed on {obj.name}: {e}")
                else:
                    print(f"   ℹ️ SurfaceDeform already bound or no target on {obj.name}")

def auto_connect_objects_to_rig(context, char_col, rig_collection):
    """Auto-connect imported objects to rig - AGGRESSIVE BIND VERSION"""
    if not context.scene.auto_connect:
        print("🔌 Auto-connect disabled, skipping connection")
        return
    
    print("🔌 Starting auto-connection to rig...")
    
    head_obj = find_head_object_in_rig(rig_collection)
    
    if not head_obj:
        print("❌ HEAD object not found, skipping auto-connection")
        return
    
    original_mode = context.mode
    original_active = context.view_layer.objects.active
    original_selected = context.selected_objects.copy()
    
    count_connected = 0
    
    for obj in char_col.all_objects:
        if obj.type == 'MESH':
            obj_name_lower = obj.name.lower()
            
            grooming_patterns = ["identirig_basebeard", "identirig_eyebrowbase", "identirig_basehaircut"]
            accessory_patterns = ["hat", "cap", "glasses", "earring", "necklace", "accessory"]
            
            is_grooming = any(obj_name_lower.startswith(pattern) for pattern in grooming_patterns)
            is_accessory = any(pattern in obj_name_lower for pattern in accessory_patterns)
            
            if is_grooming or is_accessory:
                print(f"🔗 Auto-connecting: {obj.name}")
                
                # Update modifiers
                for mod in obj.modifiers:
                    if mod.type == 'SHRINKWRAP' and head_obj:
                        mod.target = head_obj
                        print(f"   ✅ SHRINKWRAP → {head_obj.name}")
                    elif mod.type == 'SURFACE_DEFORM' and head_obj:
                        mod.target = head_obj
                        print(f"   ✅ SURFACE_DEFORM → {head_obj.name}")
                    elif mod.type == 'SIMPLE_DEFORM' and head_obj:
                        mod.origin = head_obj
                        print(f"   ✅ SIMPLE_DEFORM origin → {head_obj.name}")

                # AGGRESSIVE SURFACE DEFORM BIND
                aggressive_surface_deform_bind(obj, head_obj, context, obj_name_lower)
                
                count_connected += 1
    
    # Restore original state
    try:
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        
        bpy.ops.object.select_all(action='DESELECT')
        for obj in original_selected:
            if obj and obj.name in bpy.data.objects:
                obj.select_set(True)
        
        if original_active and original_active.name in bpy.data.objects:
            context.view_layer.objects.active = original_active
            
    except Exception as e:
        print(f"⚠️ State restoration failed: {e}")
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
    
    print(f"🎉 Auto-connected {count_connected} objects to rig")

# ----------------------
# DISPLACEMENT FUNCTIONS (UNCHANGED)
# ----------------------
def get_displacement_data(obj):
    data = {"MICROSKIN": [], "WRINKLES": []}
    for mod in obj.modifiers:
        if mod.type == 'DISPLACE' and mod.texture and mod.texture.type == 'IMAGE':
            base_name = mod.name.split("_", 1)[-1] if "_" in mod.name else mod.name
            if "MicroSkin_" in mod.name:
                data["MICROSKIN"].append({
                    "name": base_name,
                    "region": mod.name.replace("MicroSkin_", ""),
                    "texture": mod.texture.image.filepath if mod.texture and mod.texture.image else "",
                    "strength": mod.strength,
                    "scale": getattr(mod.texture, "repeat_x", 1),
                    "coords": mod.texture_coords,
                })
            elif "Wrinkles_" in mod.name:
                data["WRINKLES"].append({
                    "name": base_name,
                    "region": mod.name.replace("Wrinkles_", ""),
                    "texture": mod.texture.image.filepath if mod.texture and mod.texture.image else "",
                    "strength": mod.strength,
                    "scale": getattr(mod.texture, "repeat_x", 1),
                    "coords": mod.texture_coords,
                })
    return data

def save_displacement_for_character(context, library_path, char_name):
    rig_collection = find_active_rig_collection(context)
    head_obj = find_head_object_in_rig(rig_collection)
    
    if not head_obj:
        print(f"[Displacement] HEAD object not found in active rig.")
        return
    
    disp_data = get_displacement_data(head_obj)
    disp_dir = os.path.join(library_path, "displacement")
    os.makedirs(disp_dir, exist_ok=True)
    json_path = os.path.join(disp_dir, f"{char_name}_displacement.json")
    with open(json_path, "w") as f:
        json.dump(disp_data, f, indent=4)
    print(f"[Displacement] Saved: {json_path}")

def load_displacement_json(library_path, char_name):
    disp_dir = os.path.join(library_path, "displacement")
    json_path = os.path.join(disp_dir, f"{char_name}_displacement.json")
    if not os.path.exists(json_path):
        return {}
    with open(json_path, "r") as f:
        return json.load(f)

def apply_displacement_from_json(context, library_path, char_name, set_keyframes=True, frame=None):
    rig_collection = find_active_rig_collection(context)
    head_obj = find_head_object_in_rig(rig_collection)
    
    if not head_obj:
        print(f"[Displacement] HEAD object not found in active rig.")
        return
    
    disp_data = load_displacement_json(library_path, char_name)
    if frame is None:
        frame = bpy.context.scene.frame_current
    
    for d_type in ["MICROSKIN", "WRINKLES"]:
        for disp in disp_data.get(d_type, []):
            base_name = disp["name"]
            mod_name = f"{char_name}_{base_name}"
            mod = head_obj.modifiers.get(mod_name)
            if not mod:
                mod = head_obj.modifiers.new(mod_name, 'DISPLACE')
                mod.texture_coords = disp.get("coords", "LOCAL")
                tex = bpy.data.textures.get(mod_name) or bpy.data.textures.new(mod_name, type='IMAGE')
                try:
                    tex.image = bpy.data.images.load(disp["texture"], check_existing=True)
                except Exception as e:
                    print(f"[Displacement] Could not load texture: {disp['texture']} ({e})")
                    continue
                tex.repeat_x = tex.repeat_y = disp.get("scale", 1)
                mod.texture = tex
                mod.vertex_group = f"{disp['region']}_DISPLACEMENT_TEX"
            mod.strength = disp["strength"]
            if set_keyframes:
                mod.keyframe_insert(data_path="strength", frame=frame)
    bpy.context.scene.frame_set(bpy.context.scene.frame_current)

def fadeout_displacements(context, personaggio, frame_origin, frame_morph_start, frame_morph_end, library_path):
    rig_collection = find_active_rig_collection(context)
    head_obj = find_head_object_in_rig(rig_collection)
    
    if not head_obj:
        return
    
    disp_data = load_displacement_json(library_path, personaggio)
    for d_type in ["MICROSKIN", "WRINKLES"]:
        for disp in disp_data.get(d_type, []):
            base_name = disp["name"]
            mod_name = f"{personaggio}_{base_name}"
            mod = head_obj.modifiers.get(mod_name)
            if not mod:
                mod = head_obj.modifiers.new(mod_name, 'DISPLACE')
                mod.texture_coords = disp.get("coords", "LOCAL")
                tex = bpy.data.textures.get(mod_name) or bpy.data.textures.new(mod_name, type='IMAGE')
                try:
                    tex.image = bpy.data.images.load(disp["texture"], check_existing=True)
                except Exception as e:
                    print(f"[Displacement] Could not load texture: {disp['texture']} ({e})")
                    continue
                tex.repeat_x = tex.repeat_y = disp.get("scale", 1)
                mod.texture = tex
                mod.vertex_group = f"{disp['region']}_DISPLACEMENT_TEX"
            mod.strength = disp["strength"]
            mod.keyframe_insert(data_path="strength", frame=frame_origin)
            mod.strength = disp["strength"]
            mod.keyframe_insert(data_path="strength", frame=frame_morph_start)
            mod.strength = 0
            mod.keyframe_insert(data_path="strength", frame=frame_morph_end)
    bpy.context.scene.frame_set(bpy.context.scene.frame_current)

# --------------------
# GROOMING FUNCTIONS - MORPHING FIXED!
# --------------------
def clear_content_collection(context, type_):
    """Clear GROOMING or ACCESSORIES collection in active rig"""
    rig_collection = find_active_rig_collection(context)
    
    if type_ == "ACCESSORIES":
        target_coll = find_accessories_collection_in_rig(rig_collection)
    else:
        target_coll = find_grooming_collection_in_rig(rig_collection)
    
    if target_coll:
        objects_to_remove = list(target_coll.all_objects)
        for obj in objects_to_remove:
            bpy.data.objects.remove(obj, do_unlink=True)
        children_to_remove = list(target_coll.children)
        for c in children_to_remove:
            target_coll.children.unlink(c)

def key_geometry_nodes_inputs(obj, frame, value=None):
    if not obj.modifiers:
        return
    for mod in obj.modifiers:
        if mod.type == 'NODES' and mod.node_group:
            for node in mod.node_group.nodes:
                if "Density_Ctl" in node.name or "TrimLength_Ctl" in node.name:
                    input_socket = node.inputs[0]
                    if value is not None:
                        input_socket.default_value = value
                    input_socket.keyframe_insert("default_value", frame=frame)
                if node.name == "FHTG_SetHairCurveProfile":
                    if len(node.inputs) > 5:
                        if value is not None:
                            node.inputs[3].default_value = value
                            node.inputs[4].default_value = value
                            node.inputs[5].default_value = value
                        node.inputs[3].keyframe_insert("default_value", frame=frame)
                        node.inputs[4].keyframe_insert("default_value", frame=frame)
                        node.inputs[5].keyframe_insert("default_value", frame=frame)

def save_preset_data(filepath, obj_list):
    data = {}
    for obj in obj_list:
        if obj.type != 'CURVES':
            continue
        entry = {}
        for mod in obj.modifiers:
            if mod.type == 'NODES' and mod.node_group:
                for node in mod.node_group.nodes:
                    if "Density_Ctl" in node.name:
                        entry["grooming_default_density"] = node.inputs[0].default_value
                    elif "TrimLength_Ctl" in node.name:
                        entry["grooming_default_length"] = node.inputs[0].default_value
                    elif node.name == "FHTG_SetHairCurveProfile":
                        entry["grooming_default_shape"] = node.inputs[3].default_value
                        entry["grooming_default_size"] = node.inputs[4].default_value
                        entry["grooming_default_root"] = node.inputs[5].default_value
        data[obj.name] = entry
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)

def load_preset_data(filepath):
    if not os.path.exists(filepath):
        return {}
    with open(filepath, 'r') as f:
        return json.load(f)

def key_and_zero_previous(context, character, type_, offset=10):
    """FIXED MORPHING: Key all grooming of that character, then zero it"""
    if not character: 
        return
    
    frame = bpy.context.scene.frame_current
    rig_collection = find_active_rig_collection(context)
    
    if type_ == "ACCESSORIES":
        target_coll = find_accessories_collection_in_rig(rig_collection)
    else:
        target_coll = find_grooming_collection_in_rig(rig_collection)
    
    if not target_coll: 
        return
    
    # Find the character's grooming collection
    char_col = None
    for type_child in target_coll.children:
        for char_child in type_child.children:
            if char_child.name.lower().startswith(character.lower()):
                char_col = char_child
                break
        if char_col:
            break
    
    if not char_col: 
        print(f"🎬 MORPHING: Character grooming collection not found for: {character}")
        return
    
    print(f"🎬 MORPHING: Processing character {character} grooming at frame {frame}")
    print(f"🎬 MORPHING: Found character collection: {char_col.name}")
    
    # STEP 1: Key at (frame - offset) with current values
    bpy.context.scene.frame_set(frame - offset)
    
    grooming_objects = [obj for obj in char_col.all_objects if obj.type == 'CURVES']
    print(f"🎬 MORPHING: Found {len(grooming_objects)} grooming objects")
    
    for obj in grooming_objects:
        key_geometry_nodes_inputs(obj, frame - offset)  # Key current values
        print(f"✅ Keyed {obj.name} at frame {frame - offset}")
    
    # Key GUI elements if they exist
    gui = find_gui_collection_in_rig(rig_collection)
    if gui:
        for obj in gui.all_objects:
            if obj.type == 'MESH':
                for attr in ["location", "rotation_euler", "scale"]:
                    obj.keyframe_insert(data_path=attr, frame=frame - offset)
    
    # STEP 2: Key at current frame with zero values
    bpy.context.scene.frame_set(frame)
    
    for obj in grooming_objects:
        key_geometry_nodes_inputs(obj, frame, value=0.0)  # Zero out at current frame
        print(f"✅ Zeroed {obj.name} at frame {frame}")
    
    print(f"🎬 MORPHING: Character {character} fadeout complete: {frame - offset} → {frame}")

# --------------------
# FTP AND PREFERENCES
# --------------------
class UnifiedLibraryPreferences(AddonPreferences):
    bl_idname = "IDENTIRIG"
    last_path: StringProperty(name="Last Used Library Path", subtype='DIR_PATH')
    
    def draw(self, context):
        self.layout.prop(self, "last_path")

def save_prefs_library_path(context):
    prefs = bpy.context.preferences.addons["IDENTIRIG"].preferences
    props = context.scene
    prefs.last_path = props.library_path

def load_prefs_library_path(context):
    prefs = bpy.context.preferences.addons["IDENTIRIG"].preferences
    if prefs.last_path:
        context.scene.library_path = prefs.last_path

def ftp_upload_dir(ftp, local_dir, remote_dir):
    """Upload directory recursively to FTP server"""
    if not os.path.isdir(local_dir):
        return
    try:
        ftp.mkd(remote_dir)
        print(f"✅ Created FTP directory: {remote_dir}")
    except Exception as e:
        print(f"ℹ️ FTP directory exists or creation failed: {remote_dir} ({e})")
    
    for item in os.listdir(local_dir):
        local_path = os.path.join(local_dir, item)
        remote_path = f"{remote_dir}/{item}"
        
        if os.path.isdir(local_path):
            print(f"📁 Uploading directory: {local_path} → {remote_path}")
            ftp_upload_dir(ftp, local_path, remote_path)
        else:
            print(f"📄 Uploading file: {local_path} → {remote_path}")
            with open(local_path, 'rb') as f:
                try:
                    ftp.storbinary(f"STOR " + remote_path, f)
                    print(f"✅ Uploaded: {remote_path}")
                except Exception as e:
                    print(f"❌ FTP UPLOAD ERROR for {remote_path}: {e}")

def ftp_upload_complete_library(library_path):
    """Upload complete library structure to FTP including all grooming and displacement data"""
    try:
        print(f"📤 Starting complete library upload to FTP...")
        
        ftp = ftplib.FTP("ftp.workshops.homepc.it")
        ftp.login()
        ftp.cwd("FTP/LIBRARY")
        
        # Upload all _gui.json files
        for file in os.listdir(library_path):
            if file.endswith('_gui.json') or file.endswith('_preview.jpg'):
                local_file_path = os.path.join(library_path, file)
                print(f"📄 Uploading: {file}")
                with open(local_file_path, 'rb') as f:
                    ftp.storbinary(f"STOR {file}", f)
                print(f"✅ Uploaded: {file}")
        
        # Upload all type directories (HAIR, BEARD, EYEBROWS_GN, ACCESSORIES)
        for type_name in ["HAIR", "BEARD", "EYEBROWS_GN", "ACCESSORIES"]:
            type_dir = os.path.join(library_path, type_name)
            if os.path.isdir(type_dir):
                print(f"📁 Uploading {type_name} directory...")
                ftp_upload_dir(ftp, type_dir, type_name)
        
        # Upload displacement directory
        displacement_dir = os.path.join(library_path, "displacement")
        if os.path.isdir(displacement_dir):
            print(f"📁 Uploading displacement directory...")
            ftp_upload_dir(ftp, displacement_dir, "displacement")
        
        ftp.quit()
        print(f"🎉 Complete library upload finished!")
        return True
        
    except Exception as e:
        print(f"❌ Complete library upload failed: {e}")
        return False

# === REFRESH OPERATORS WITH PREVIEW SUPPORT ===
class IDENTILIBRARY_OT_refresh_local_characters(Operator):
    bl_idname = "identilibrary.refresh_local_characters"
    bl_label = "Refresh Local Characters"
    bl_description = "Refresh local character list and load previews"
    
    def execute(self, context):
        props = context.scene.library_preview_props
        library_path = context.scene.library_path
        
        if not os.path.isdir(library_path):
            self.report({'WARNING'}, f"Library path not found: {library_path}")
            return {'CANCELLED'}
        
        try:
            print(f"🔄 Refreshing local character list...")
            
            # Scan local characters
            matched_characters = scan_local_characters_with_previews(library_path)
            
            # Clear and update collection
            props.local_character_collection.clear()
            
            for char_data in matched_characters:
                item = props.local_character_collection.add()
                item.name = char_data['name']
                item.has_preview = char_data['has_preview']
                item.is_cached = True  # Local files are always "cached"
                item.is_ftp = False
                
                # Set preview info
                if char_data['has_preview']:
                    preview_path = os.path.join(library_path, char_data['preview'])
                    if os.path.exists(preview_path):
                        item.preview_path = preview_path
                        
                        # Load preview into Blender
                        load_character_preview_into_blender(preview_path, char_data['name'], "local")
            
            print(f"✅ Refreshed {len(matched_characters)} local characters")
            
            # Force UI refresh
            for area in bpy.context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
            
            self.report({'INFO'}, f"Refreshed {len(matched_characters)} local characters")
                    
        except Exception as e:
            print(f"❌ Local character refresh failed: {e}")
            self.report({'ERROR'}, f"Local character refresh failed: {e}")
        
        return {'FINISHED'}

class IDENTILIBRARY_OT_refresh_ftp_characters(Operator):
    bl_idname = "identilibrary.refresh_ftp_characters"
    bl_label = "Refresh FTP Characters"
    bl_description = "Refresh FTP character list and download previews"
    
    def execute(self, context):
        def load_ftp_characters_and_previews():
            try:
                # Step 1: Scan FTP for characters and previews
                print("🚀 Step 1: Scanning FTP server for characters...")
                matched_characters = scan_ftp_characters_with_previews()
                if not matched_characters:
                    return
                
                # Step 2: Download all previews
                print("📥 Step 2: Downloading FTP previews...")
                cache_dir = os.path.join(tempfile.gettempdir(), "identirig_library_cache")
                os.makedirs(cache_dir, exist_ok=True)
                
                for char_data in matched_characters:
                    if char_data['has_preview']:
                        download_ftp_preview(char_data['preview'])
                
                # Step 3: Update addon data
                print("📋 Step 3: Updating FTP addon data...")
                props = context.scene.library_preview_props
                props.ftp_character_collection.clear()
                
                for char_data in matched_characters:
                    item = props.ftp_character_collection.add()
                    item.name = char_data['name']
                    item.has_preview = char_data['has_preview']
                    item.is_ftp = True
                    
                    # Check character cache (gui.json)
                    gui_cache_path = os.path.join(cache_dir, f"{char_data['name']}_gui.json")
                    item.is_cached = os.path.exists(gui_cache_path)
                    
                    # Set preview info
                    if char_data['has_preview']:
                        preview_cache_path = os.path.join(cache_dir, char_data['preview'])
                        if os.path.exists(preview_cache_path):
                            item.preview_path = preview_cache_path
                
                # Step 4: Load previews into Blender (main thread)
                def load_previews_main_thread():
                    print("🎨 Step 4: Loading FTP character previews into Blender...")
                    loaded_count = 0
                    
                    for item in props.ftp_character_collection:
                        if item.has_preview and item.preview_path:
                            image = load_character_preview_into_blender(item.preview_path, item.name, "ftp")
                            if image:
                                loaded_count += 1
                    
                    print(f"🎉 FTP character refresh complete! Loaded {loaded_count} previews")
                    
                    # Force UI refresh
                    for area in bpy.context.screen.areas:
                        if area.type == 'VIEW_3D':
                            area.tag_redraw()
                    
                    return None
                
                bpy.app.timers.register(load_previews_main_thread, first_interval=0.1)
                
                print(f"✅ Processed {len(matched_characters)} FTP character files")
                
            except Exception as e:
                print(f"❌ FTP character refresh failed: {e}")
                import traceback
                traceback.print_exc()
        
        thread = threading.Thread(target=load_ftp_characters_and_previews)
        thread.start()
        
        self.report({'INFO'}, "Refreshing FTP character list and previews...")
        return {'FINISHED'}

class IDENTILIBRARY_OT_ActivateRig(Operator):
    """Operator to activate a rig from integrated picker for Library"""
    bl_idname = "identilibrary.activate_rig_library"
    bl_label = "Activate Rig"
    bl_description = "Activate the selected IDENTIRIG rig for library"

    rig_name: StringProperty()

    def execute(self, context):
        context.scene.identirig_active_library = self.rig_name
        self.report({'INFO'}, f"[IDENTILIBRARY] ▶️ Active rig: {self.rig_name}")
        print(f"[IDENTILIBRARY] ▶️ Active rig: {self.rig_name}")
        return {'FINISHED'}

class UNIFIEDLIB_OT_save_ftp(Operator):
    bl_idname = "unified_lib.save_ftp"
    bl_label = "Save to FTP"
    
    def execute(self, context):
        props = context.scene
        
        def upload_complete_library():
            success = ftp_upload_complete_library(props.library_path)
            if success:
                print("🎉 Complete FTP upload successful!")
            else:
                print("❌ Complete FTP upload failed!")
        
        thread = threading.Thread(target=upload_complete_library)
        thread.start()
        
        self.report({'INFO'}, "Uploading complete library to FTP...")
        return {'FINISHED'}

def notify(msg):
    def draw(self, _context):
        self.layout.label(text=msg)
    bpy.context.window_manager.popup_menu(draw, title="INFO", icon='INFO')

def refresh_ftp_list():
    global ftp_file_list
    try:
        ftp = ftplib.FTP("ftp.workshops.homepc.it")
        ftp.login()
        ftp.cwd("FTP/LIBRARY")
        files = ftp.nlst()
        ftp.quit()
        ftp_file_list.clear()
        ftp_file_list.extend([(f, f, "") for f in files if f.endswith('.json')])
    except Exception as e:
        print(f"[FTP ERROR] {e}")

def refresh_local_list(path):
    global local_file_list
    if not os.path.isdir(path): 
        return
    files = [f for f in os.listdir(path) if f.endswith('_gui.json')]
    local_file_list.clear()
    local_file_list.extend([(f.replace('_gui.json', ''), f.replace('_gui.json', ''), "") for f in files])

# -------------
# SAVE/LOAD WITH AUTO-CONNECTION AND VIEWPORT SNAPSHOT
# -------------
def save_full_library(context):
    props = context.scene
    char, type_ = props.character_name, props.chosen_type
    
    rig_coll = find_active_rig_collection(context)
    gui = find_gui_collection_in_rig(rig_coll) if rig_coll else None
    
    # 📸 CAPTURE VIEWPORT SNAPSHOT BEFORE SAVING! (VIEWPORT RENDER VERSION)
    snapshot_path = capture_viewport_snapshot(char, props.library_path)
    if snapshot_path:
        print(f"📸 Character viewport snapshot captured successfully: {snapshot_path}")
    else:
        print(f"⚠️ Character viewport snapshot failed - saving without preview")
    
    gui_data = {}
    if gui:
        for o in gui.all_objects:
            if o.type == 'MESH':
                gui_data[o.name] = {"location": list(o.location)}
    # === 🎛️ SALVA TUTTI I CONTROLLI DELLA GUI IDENTIRIG_GUI ===
    print("🎛️ Capturing ALL IDENTIRIG_GUI panel controls...")
    
    # Wrinkles Intensity Panel
    if hasattr(context.scene, 'wrinkles_props'):
        wrinkles = context.scene.wrinkles_props
        gui_data['WRINKLES_INTENSITY'] = {
            'primary_intensity': wrinkles.primary_intensity,
            'secondary_intensity': wrinkles.secondary_intensity
        }
        print(f"✅ Saved Wrinkles Intensity: Primary {wrinkles.primary_intensity}, Secondary {wrinkles.secondary_intensity}")
    
    # Expression Intensity Panel (se esiste ancora)
    if hasattr(context.scene, 'expr_intensity_props'):
        expr = context.scene.expr_intensity_props
        gui_data['EXPRESSION_INTENSITY'] = {
            'expression_intensity': expr.expression_intensity
        }
        print(f"✅ Saved Expression Intensity: {expr.expression_intensity}")
    
    # Secondary Intensity Panel (se esiste ancora)  
    if hasattr(context.scene, 'secondary_intensity_props'):
        secondary = context.scene.secondary_intensity_props
        gui_data['SECONDARY_INTENSITY'] = {
            'secondary_intensity': secondary.secondary_intensity
        }
        print(f"✅ Saved Secondary Intensity: {secondary.secondary_intensity}")
    
    # 🚀 AGGIUNGI SISTEMA UNIVERSALE
    print("🚀 STARTING UNIVERSAL SYSTEM...")
    
    # Scansiona tutti gli sliders
    gui_sliders = scan_all_gui_sliders_universal(context)
    
    # Salva accessories completi
    accessories = save_accessories_complete(context, props.library_path, char, props.chosen_type)
    
    # Salva displacement esteso
    displacement = save_displacement_extended(context, props.library_path, char)
    
    # Salva materiali completi
    materials_data = {}
    for obj in context.scene.objects:
        if obj.type == 'MESH' and obj.material_slots:
            for slot in obj.material_slots:
                if slot.material and slot.material.name not in materials_data:
                    materials_data[slot.material.name] = save_material_complete(slot.material)
    
    # Combina con GUI data esistente
    gui_data['GUI_SLIDERS_UNIVERSAL'] = gui_sliders
    gui_data['ACCESSORIES_COMPLETE'] = accessories
    gui_data['DISPLACEMENT_EXTENDED'] = displacement
    gui_data['MATERIALS_COMPLETE'] = materials_data
    
    # Prepara morphing
    gui_data['MORPHING_DATA'] = prepare_morphing_universal(gui_data)
    
    print(f"🎉 UNIVERSAL SYSTEM SAVED: {len(gui_sliders)} slider categories, {len(materials_data)} materials")    
    gui_path = os.path.join(props.library_path, f"{char}_gui.json")
    with open(gui_path, 'w') as f:
        json.dump(gui_data, f, indent=4)
    
    preset_dir = os.path.join(props.library_path, type_, char)
    os.makedirs(preset_dir, exist_ok=True)
    blend_path = os.path.join(preset_dir, f"{char}.blend")
    json_path = os.path.join(preset_dir, f"{char}.json")
    preset_path = os.path.join(preset_dir, f"preset.json")
    
    if type_ == "ACCESSORIES":
        target_coll = find_accessories_collection_in_rig(rig_coll)
    else:
        target_coll = find_grooming_collection_in_rig(rig_coll)
    
    if target_coll:
        objs = [o for o in target_coll.all_objects if o.type in {"CURVES", "MESH"}]
        curves = [o for o in objs if o.type == "CURVES"]
        surfaces = [o for o in objs if o.type == "MESH"]
        node_groups = []
        for o in curves:
            for m in o.modifiers:
                if m.type == 'NODES' and m.node_group and m.node_group not in node_groups:
                    node_groups.append(m.node_group)
        bpy.data.libraries.write(blend_path, set(objs + [o.data for o in objs] + node_groups), path_remap='RELATIVE')
        with open(json_path, 'w') as f:
            json.dump({"curves": [o.name for o in curves], "surfaces": [o.name for o in surfaces]}, f, indent=4)
        if props.save_preset:
            save_preset_data(preset_path, curves)
    
    # Return snapshot path for potential FTP upload
    return snapshot_path

def load_full_library(context):
    props = context.scene
    char, type_ = props.character_name, props.chosen_type
    offset = props.transition_frames
    morphing = props.do_morphing
    frame = bpy.context.scene.frame_current
    
    gui_path = os.path.join(props.library_path, f"{char}_gui.json")
    preset_dir = os.path.join(props.library_path, type_, char)
    blend_path = os.path.join(preset_dir, f"{char}.blend")
    json_path = os.path.join(preset_dir, f"{char}.json")
    preset_path = os.path.join(preset_dir, "preset.json")
    preset_data = load_preset_data(preset_path)
    
    if morphing:
        for prev_char, frame_origin in character_origin_frames.items():
            if prev_char != char:
                fadeout_displacements(
                    context,
                    prev_char,
                    frame_origin,
                    frame - offset,
                    frame,
                    props.library_path
                )
    
    if props.replace_grooming:
        clear_content_collection(context, type_)
    
    # Load GUI data
    if os.path.exists(gui_path):
        with open(gui_path, 'r') as f:
            data = json.load(f)
        
        rig_coll = find_active_rig_collection(context)
        gui = find_gui_collection_in_rig(rig_coll) if rig_coll else None
        
        if not gui:
            print("[IDENTILIBRARY] ❌ GUI not found for active rig.")
            return
        
        for name, info in data.items():
            matches = [obj for obj in gui.all_objects if obj.name.startswith(name)]
            for o in matches:
                o.location = info["location"]
                o.keyframe_insert(data_path="location", frame=frame)
        
        # 2. 🆕 RIPRISTINA TUTTI I PANNELLI CONTROLLI
        print(f"🎛️ Loading ALL GUI controls for character: {char}")
        
        # Wrinkles Intensity
        if 'WRINKLES_INTENSITY' in data and hasattr(context.scene, 'wrinkles_props'):
            wrinkles_data = data['WRINKLES_INTENSITY']
            wrinkles = context.scene.wrinkles_props
            
            if 'primary_intensity' in wrinkles_data:
                wrinkles.primary_intensity = wrinkles_data['primary_intensity']
                print(f"✅ Restored Primary Wrinkles: {wrinkles_data['primary_intensity']}")
            
            if 'secondary_intensity' in wrinkles_data:
                wrinkles.secondary_intensity = wrinkles_data['secondary_intensity']
                print(f"✅ Restored Secondary Wrinkles: {wrinkles_data['secondary_intensity']}")
        
        # Expression Intensity (se esiste)
        if 'EXPRESSION_INTENSITY' in data and hasattr(context.scene, 'expr_intensity_props'):
            expr_data = data['EXPRESSION_INTENSITY']
            expr = context.scene.expr_intensity_props
            expr.expression_intensity = expr_data['expression_intensity']
            print(f"✅ Restored Expression Intensity: {expr_data['expression_intensity']}")
        
        # Secondary Intensity (se esiste)
        if 'SECONDARY_INTENSITY' in data and hasattr(context.scene, 'secondary_intensity_props'):
            secondary_data = data['SECONDARY_INTENSITY']
            secondary = context.scene.secondary_intensity_props
            secondary.secondary_intensity = secondary_data['secondary_intensity']
            print(f"✅ Restored Secondary Intensity: {secondary_data['secondary_intensity']}")
        
        # 🆕 CARICA SISTEMA UNIVERSALE
        if 'GUI_SLIDERS_UNIVERSAL' in data:
            print("🔄 Loading universal GUI sliders with manual updates...")
            load_all_gui_sliders_universal_with_updates(context, data['GUI_SLIDERS_UNIVERSAL'], frame)
        
        if 'MATERIALS_COMPLETE' in data:
            print("🖼️ Loading complete materials...")
            # Materials will be loaded when objects are loaded, this data is for reference
            print(f"✅ Material data available for {len(data['MATERIALS_COMPLETE'])} materials")
        
        # 📊 SUMMARY
        total_restored = sum(1 for key in data.keys() if key not in ['location', 'GUI_SLIDERS_UNIVERSAL', 'ACCESSORIES_COMPLETE', 'DISPLACEMENT_EXTENDED', 'MATERIALS_COMPLETE', 'MORPHING_DATA'])
        print(f"🎉 TOTAL GUI PANELS RESTORED: {total_restored}")    
    # Load content data
    if os.path.exists(blend_path) and os.path.exists(json_path):
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        obj_names = data.get("curves", []) + data.get("surfaces", [])
        with bpy.data.libraries.load(blend_path, link=False) as (from_, to_):
            to_.objects = [n for n in obj_names if n in from_.objects]
            to_.node_groups = from_.node_groups
        
        rig_coll = find_active_rig_collection(context)
        
        if type_ == "ACCESSORIES":
            target_coll = find_accessories_collection_in_rig(rig_coll)
        else:
            target_coll = find_grooming_collection_in_rig(rig_coll)
        
        if not target_coll:
            print(f"[IDENTILIBRARY] ❌ Could not create {type_} collection in active rig.")
            return
        
        type_col = None
        for child in target_coll.children:
            if child.name.lower().startswith(type_.lower()):
                type_col = child
                break
        
        if not type_col:
            type_col = bpy.data.collections.new(type_)
            target_coll.children.link(type_col)
        
        char_col = bpy.data.collections.new(char)
        type_col.children.link(char_col)
        
        for o in to_.objects:
            if o:
                char_col.objects.link(o)
            if o.type == 'MESH':
                o.hide_viewport = True
                o.hide_render = True
        
        # AGGRESSIVE AUTO-CONNECT!
        auto_connect_objects_to_rig(context, char_col, rig_coll)
        
        # FIXED MORPHING: Set up new character with zero values first, then preset values
        if morphing:
            # Set to zero at start frame for new character
            bpy.context.scene.frame_set(frame - offset)
            for obj in char_col.all_objects:
                if obj.type == 'CURVES':
                    key_geometry_nodes_inputs(obj, frame - offset, value=0.0)
        
        # Load character at current frame with preset values
        bpy.context.scene.frame_set(frame)
        for obj in char_col.all_objects:
            if obj.type == 'CURVES':
                defaults = preset_data.get(obj.name, {})
                for mod in obj.modifiers:
                    if mod.type == 'NODES' and mod.node_group:
                        nodes = mod.node_group.nodes
                        if "Density_Ctl" in nodes:
                            v = defaults.get("grooming_default_density", 1.0)
                            nodes["Density_Ctl"].inputs[0].default_value = v
                            nodes["Density_Ctl"].inputs[0].keyframe_insert("default_value", frame=frame)
                        if "TrimLength_Ctl" in nodes:
                            v = defaults.get("grooming_default_length", 1.0)
                            nodes["TrimLength_Ctl"].inputs[0].default_value = v
                            nodes["TrimLength_Ctl"].inputs[0].keyframe_insert("default_value", frame=frame)
                        if "FHTG_SetHairCurveProfile" in nodes:
                            p = nodes["FHTG_SetHairCurveProfile"]
                            p.inputs[3].default_value = defaults.get("grooming_default_shape", 0.3)
                            p.inputs[4].default_value = defaults.get("grooming_default_size", 0.3)
                            p.inputs[5].default_value = defaults.get("grooming_default_root", 0.3)
                            p.inputs[3].keyframe_insert("default_value", frame=frame)
                            p.inputs[4].keyframe_insert("default_value", frame=frame)
                            p.inputs[5].keyframe_insert("default_value", frame=frame)
    
    # Apply displacement and morphing
    apply_displacement_from_json(context, props.library_path, char, set_keyframes=True, frame=frame)
    
    # Morphing universale
    if frame is not None and 'MORPHING_DATA' in data:
        print("🎬 Applying universal morphing...")
        # The morphing data is prepared but actual application depends on the morphing system
        # This is mainly for keyframe setup and will work with existing morphing
        morphing_data = data['MORPHING_DATA']
        print(f"✅ Morphing ready for {len(morphing_data.get('keyframeable_properties', []))} properties")
    
    if char not in character_origin_frames:
        character_origin_frames[char] = frame

class UNIFIEDLIB_OT_save(Operator):
    bl_idname = "unified_lib.save"
    bl_label = "Save Character"
    
    def execute(self, context):
        global character_origin_frames
        props = context.scene
        
        if not context.scene.identirig_active_library:
            self.report({'ERROR'}, "No IDENTIRIG rig selected! Use picker to select one.")
            return {'CANCELLED'}
        
        if not props.character_name.strip():
            self.report({'ERROR'}, "Character name cannot be empty!")
            return {'CANCELLED'}
        
        save_prefs_library_path(context)
        char = props.character_name
        frame_now = bpy.context.scene.frame_current
        
        if char not in character_origin_frames:
            character_origin_frames[char] = frame_now
        
        if props.save_displacement:
            save_displacement_for_character(context, props.library_path, char)
        
        # Save library and get snapshot path
        snapshot_path = save_full_library(context)
        
        # Refresh local character list to show new preview
        bpy.ops.identilibrary.refresh_local_characters()
        
        if snapshot_path:
            notify(f"Character '{char}' saved successfully with viewport snapshot!")
        else:
            notify(f"Character '{char}' saved successfully (no snapshot)")
        
        return {'FINISHED'}

class UNIFIEDLIB_OT_save_ftp_with_preview(Operator):
    bl_idname = "unified_lib.save_ftp_with_preview"
    bl_label = "Save to FTP with Preview"
    bl_description = "Save to FTP including character preview snapshot"
    
    def execute(self, context):
        props = context.scene
        char = props.character_name
        
        if not char:
            self.report({'ERROR'}, "No character name specified!")
            return {'CANCELLED'}
        
        def upload_with_preview():
            try:
                print("📤 Starting FTP upload with preview...")
                success = ftp_upload_complete_library(props.library_path)
                if success:
                    print("🎉 FTP upload with preview completed!")
                else:
                    print("❌ FTP upload failed!")
                
            except Exception as e:
                print(f"❌ FTP upload failed: {e}")
        
        thread = threading.Thread(target=upload_with_preview)
        thread.start()
        
        self.report({'INFO'}, "Uploading to FTP with preview...")
        return {'FINISHED'}

class UNIFIEDLIB_OT_load(Operator):
    bl_idname = "unified_lib.load"
    bl_label = "Load Character"
    
    def execute(self, context):
        global previous_character
        global character_origin_frames
        props = context.scene
        
        if not context.scene.identirig_active_library:
            self.report({'ERROR'}, "No IDENTIRIG rig selected! Use picker to select one.")
            return {'CANCELLED'}
        
        char = props.character_name
        frame_now = bpy.context.scene.frame_current
        offset = props.transition_frames
        morphing = props.do_morphing

        if morphing and previous_character and previous_character != char:
            key_and_zero_previous(context, previous_character, props.chosen_type, offset)

        if morphing and len(character_origin_frames) > 0:
            for prev_char, frame_origin in character_origin_frames.items():
                if prev_char != char:
                    fadeout_displacements(
                        context,
                        prev_char,
                        frame_origin,
                        frame_now - offset,
                        frame_now,
                        props.library_path
                    )

        load_full_library(context)

        apply_displacement_from_json(context, props.library_path, char, set_keyframes=True, frame=frame_now)

        if char not in character_origin_frames:
            character_origin_frames[char] = frame_now

        previous_character = char

        notify("Character loaded successfully!")
        return {'FINISHED'}

class UNIFIEDLIB_OT_load_character_preview(Operator):
    bl_idname = "unified_lib.load_character_preview"
    bl_label = "Load Character"
    bl_description = "Load character from preview"
    
    character_name: StringProperty()
    
    def execute(self, context):
        context.scene.character_name = self.character_name
        bpy.ops.unified_lib.load()
        return {'FINISHED'}

class UNIFIEDLIB_OT_load_ftp_character_preview(Operator):
    bl_idname = "unified_lib.load_ftp_character_preview"
    bl_label = "Load FTP Character"
    bl_description = "Load character from FTP preview"
    
    character_name: StringProperty()
    
    def execute(self, context):
        # Download complete character data
        success = download_complete_ftp_character(self.character_name, context.scene.library_path)
        
        if not success:
            self.report({'ERROR'}, f"Failed to download character: {self.character_name}")
            return {'CANCELLED'}
        
        # Set character name and load
        context.scene.character_name = self.character_name
        bpy.ops.unified_lib.load()
        
        self.report({'INFO'}, f"Loaded FTP character: {self.character_name}")
        return {'FINISHED'}

class UNIFIEDLIB_OT_refresh_local(Operator):
    bl_idname = "unified_lib.refresh_local"
    bl_label = "Refresh Local"
    
    def execute(self, context):
        refresh_local_list(context.scene.library_path)
        # Also refresh character previews
        bpy.ops.identilibrary.refresh_local_characters()
        return {'FINISHED'}

class UNIFIEDLIB_OT_refresh_ftp(Operator):
    bl_idname = "unified_lib.refresh_ftp"
    bl_label = "Refresh FTP"
    
    def execute(self, context):
        refresh_ftp_list()
        # Also refresh character previews
        bpy.ops.identilibrary.refresh_ftp_characters()
        return {'FINISHED'}

class UNIFIEDLIB_OT_set_from_local(Operator):
    bl_idname = "unified_lib.set_from_local"
    bl_label = "Load Local Character"
    
    def execute(self, context):
        p = context.scene
        p.character_name = p.local_selected_file
        bpy.ops.unified_lib.load()
        return {'FINISHED'}

class UNIFIEDLIB_OT_set_from_ftp(Operator):
    bl_idname = "unified_lib.set_from_ftp"
    bl_label = "Load FTP Character"
    
    def execute(self, context):
        p = context.scene
        char_name = p.ftp_selected_file.replace("_gui.json", "")
        
        if not char_name:
            self.report({'ERROR'}, "No FTP character selected!")
            return {'CANCELLED'}
        
        # Download complete character data
        success = download_complete_ftp_character(char_name, p.library_path)
        
        if not success:
            self.report({'ERROR'}, f"Failed to download character: {char_name}")
            return {'CANCELLED'}
        
        # Set character name and load
        p.character_name = char_name
        bpy.ops.unified_lib.load()
        
        self.report({'INFO'}, f"Loaded FTP character: {char_name}")
        return {'FINISHED'}

# === MAIN UI PANEL WITH ULTRA FULL WIDTH CHARACTER PREVIEW SUPPORT ===
class UNIFIEDLIB_PT_panel(Panel):
    bl_label = "IDENTIRIG CHARACTER LIBRARY"
    bl_idname = "UNIFIEDLIB_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "IDENTIRIG_PLUS"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        preview_props = scene.library_preview_props

        # RIG PICKER SECTION
        box = layout.box()
        box.label(text="RIG PICKER", icon='OUTLINER_OB_ARMATURE')
        
        if scene.identirig_active_library:
            row = box.row()
            row.label(text=f"Active: {scene.identirig_active_library}", icon='CHECKMARK')
        else:
            row = box.row()
            row.label(text="No rig selected", icon='ERROR')
        
        rig_found = False
        for coll in bpy.data.collections:
            if coll.name.lower().startswith("identirig"):
                if not rig_found:
                    box.label(text="Available rigs:")
                    rig_found = True
                row = box.row()
                op = row.operator("identilibrary.activate_rig_library", text=coll.name)
                op.rig_name = coll.name
                if scene.identirig_active_library == coll.name:
                    row.enabled = False

        if not rig_found:
            box.label(text="No IDENTIRIG rigs found", icon='INFO')

        layout.separator()

        # RIG STRUCTURE INFO
        if scene.identirig_active_library:
            info_box = layout.box()
            info_box.label(text="TARGET STRUCTURE", icon='OUTLINER')
            rig_coll = find_active_rig_collection(context)
            if rig_coll:
                geo_coll = find_geo_collection_in_rig(rig_coll)
                grooming_coll = find_grooming_collection_in_rig(rig_coll)
                accessories_coll = find_accessories_collection_in_rig(rig_coll)
                head_obj = find_head_object_in_rig(rig_coll)
                
                info_box.label(text=f"Rig: {rig_coll.name}")
                info_box.label(text=f"GEO: {geo_coll.name if geo_coll else 'NOT FOUND'}")
                info_box.label(text=f"GROOMING: {grooming_coll.name if grooming_coll else 'Will be created'}")
                info_box.label(text=f"ACCESSORIES: {accessories_coll.name if accessories_coll else 'Will be created'}")
                info_box.label(text=f"HEAD: {head_obj.name if head_obj else 'NOT FOUND'}")
            else:
                info_box.label(text="Rig collection not found")

        layout.separator()

        # MAIN LIBRARY CONTROLS
        p = context.scene
        layout.prop(p, "library_path")
        layout.prop(p, "character_name")
        layout.prop(p, "chosen_type")
        
        # Character Preview Settings
        preview_box = layout.box()
        preview_box.label(text="CHARACTER PREVIEW SETTINGS", icon='IMAGE_DATA')
        preview_box.prop(preview_props, "show_thumbnails")
        if preview_props.show_thumbnails:
            preview_box.prop(preview_props, "thumbnail_size", slider=True)
        
        # Auto-connection toggle
        auto_box = layout.box()
        auto_box.label(text="CONNECTION SETTINGS", icon='LINKED')
        auto_box.prop(p, "auto_connect")
        if p.auto_connect:
            auto_box.label(text="✅ AGGRESSIVE Surface Deform binding", icon='INFO')
            auto_box.label(text="✅ Multiple bind attempts + manual fallback", icon='INFO')
        else:
            auto_box.label(text="⚠️ Manual connection required", icon='ERROR')

        layout.separator()

        # SAVE/LOAD SECTION
        save_load_box = layout.box()
        save_load_box.label(text="SAVE/LOAD CONTROLS", icon='FILE')
        
        row = save_load_box.row(align=True)
        row.operator("unified_lib.save", text="SAVE", icon='FILE_TICK')
        row.operator("unified_lib.load", text="LOAD", icon='IMPORT')
        
        # Options
        options_row = save_load_box.row()
        options_row.prop(p, "replace_grooming")
        options_row.prop(p, "save_preset")
        
        displacement_row = save_load_box.row()
        displacement_row.prop(p, "save_displacement")
        displacement_row.prop(p, "load_displacement")
        
        # Morphing
        morph_box = save_load_box.box()
        morph_box.prop(p, "do_morphing")
        if p.do_morphing:
            morph_box.prop(p, "transition_frames")

        layout.separator()

        # LOCAL CHARACTERS SECTION
        local_box = layout.box()
        local_header = local_box.row()
        local_header.label(text="LOCAL CHARACTERS", icon='DISK_DRIVE')
        local_header.operator("unified_lib.refresh_local", text="", icon='FILE_REFRESH')
        
        if preview_props.show_thumbnails and len(preview_props.local_character_collection) > 0:
            # ULTRA FULL WIDTH CHARACTER PREVIEW GRID
            local_box.label(text=f"Found {len(preview_props.local_character_collection)} local characters:")
            
            # Calculate grid layout for ultra full width
            sidebar_width = 300  # Approximate sidebar width
            thumbnail_size = preview_props.thumbnail_size
            button_width = 50
            spacing = 5
            total_item_width = thumbnail_size + button_width + spacing
            columns = max(1, int(sidebar_width / total_item_width))
            
            grid = local_box.grid_flow(columns=columns, align=True)
            
            for item in preview_props.local_character_collection:
                item_col = grid.column(align=True)
                
                # Character preview image
                if item.has_preview and item.preview_path:
                    preview_name = f"library_preview_local_{item.name}"
                    if preview_name in bpy.data.images:
                        # Create preview row
                        preview_row = item_col.row(align=True)
                        preview_row.scale_y = thumbnail_size / 50  # Scale based on size
                        
                        # Preview image
                        preview_row.template_icon(icon_value=bpy.data.images[preview_name].preview.icon_id, scale=thumbnail_size/25)
                        
                        # Load button - QUADRATINO PICCOLO CON FRECCIA
                        load_col = preview_row.column(align=True)
                        load_col.scale_x = 0.7  # Più piccolo
                        load_col.scale_y = 0.7
                        load_op = load_col.operator("unified_lib.load_character_preview", text="↗", icon='NONE')
                        load_op.character_name = item.name
                        
                        # Character name
                        item_col.label(text=item.name, icon='USER')
                    else:
                        # No preview available
                        item_col.label(text=item.name, icon='USER')
                        load_op = item_col.operator("unified_lib.load_character_preview", text="LOAD", icon='IMPORT')
                        load_op.character_name = item.name
                else:
                    # No preview
                    item_col.label(text=item.name, icon='USER')
                    load_op = item_col.operator("unified_lib.load_character_preview", text="LOAD", icon='IMPORT')
                    load_op.character_name = item.name
        else:
            # Fallback dropdown list
            if len(local_file_list) > 0:
                local_box.prop(p, "local_selected_file")
                local_box.operator("unified_lib.set_from_local", text="Load Selected Character", icon='IMPORT')
            else:
                local_box.label(text="No local characters found", icon='INFO')

        layout.separator()

        # FTP CHARACTERS SECTION
        ftp_box = layout.box()
        ftp_header = ftp_box.row()
        ftp_header.label(text="FTP CHARACTERS", icon='URL')
        ftp_header.operator("unified_lib.refresh_ftp", text="", icon='FILE_REFRESH')
        
        if preview_props.show_thumbnails and len(preview_props.ftp_character_collection) > 0:
            # ULTRA FULL WIDTH FTP CHARACTER PREVIEW GRID
            ftp_box.label(text=f"Found {len(preview_props.ftp_character_collection)} FTP characters:")
            
            # Calculate grid layout for ultra full width
            grid = ftp_box.grid_flow(columns=columns, align=True)
            
            for item in preview_props.ftp_character_collection:
                item_col = grid.column(align=True)
                
                # Character preview image
                if item.has_preview and item.preview_path:
                    preview_name = f"library_preview_ftp_{item.name}"
                    if preview_name in bpy.data.images:
                        # Create preview row
                        preview_row = item_col.row(align=True)
                        preview_row.scale_y = thumbnail_size / 50  # Scale based on size
                        
                        # Preview image
                        preview_row.template_icon(icon_value=bpy.data.images[preview_name].preview.icon_id, scale=thumbnail_size/25)
                        
                        # Load button - QUADRATINO PICCOLO CON FRECCIA
                        load_col = preview_row.column(align=True)
                        load_col.scale_x = 0.7  # Più piccolo
                        load_col.scale_y = 0.7
                        load_op = load_col.operator("unified_lib.load_ftp_character_preview", text="↗", icon='NONE')
                        load_op.character_name = item.name
                        
                        # Character name with cache status
                        name_text = f"{item.name} {'💾' if item.is_cached else '☁️'}"
                        item_col.label(text=name_text, icon='USER')
                    else:
                        # No preview available
                        name_text = f"{item.name} {'💾' if item.is_cached else '☁️'}"
                        item_col.label(text=name_text, icon='USER')
                        load_op = item_col.operator("unified_lib.load_ftp_character_preview", text="LOAD", icon='IMPORT')
                        load_op.character_name = item.name
                else:
                    # No preview
                    name_text = f"{item.name} {'💾' if item.is_cached else '☁️'}"
                    item_col.label(text=name_text, icon='USER')
                    load_op = item_col.operator("unified_lib.load_ftp_character_preview", text="LOAD", icon='IMPORT')
                    load_op.character_name = item.name
        else:
            # Fallback dropdown list
            if len(ftp_file_list) > 0:
                ftp_box.prop(p, "ftp_selected_file")
                ftp_box.operator("unified_lib.set_from_ftp", text="Load Selected FTP Character", icon='IMPORT')
            else:
                ftp_box.label(text="No FTP characters found", icon='INFO')

        layout.separator()

        # FTP UPLOAD SECTION
        ftp_upload_box = layout.box()
        ftp_upload_box.label(text="FTP UPLOAD", icon='EXPORT')
        row = ftp_upload_box.row(align=True)
        row.operator("unified_lib.save_ftp", text="Upload Complete Library", icon='EXPORT')
        row.operator("unified_lib.save_ftp_with_preview", text="Upload with Preview", icon='IMAGE_DATA')

# ===============================
# 🚀 SISTEMA UNIVERSALE - UNIVERSAL SYSTEM
# ===============================

def scan_all_gui_sliders_universal(context):
    """🔍 SCANSIONA TUTTI GLI SLIDERS GUI AUTOMATICAMENTE"""
    print("🔍 Starting universal GUI slider scan...")
    
    sliders_data = {
        'SCENE_PROPERTIES': {},
        'OBJECT_PROPERTIES': {},
        'BONE_PROPERTIES': {},
        'PROPERTY_GROUPS': {},
        'WRINKLES_INTENSITY': {},
        'EXPRESSION_INTENSITY': {},
        'SECONDARY_INTENSITY': {}
    }
    
    # 1. Scene Properties Scanning
    scene = context.scene
    
    # Wrinkles Intensity Panel
    if hasattr(scene, 'wrinkles_props'):
        wrinkles = scene.wrinkles_props
        sliders_data['WRINKLES_INTENSITY'] = {
            'primary_intensity': wrinkles.primary_intensity,
            'secondary_intensity': wrinkles.secondary_intensity
        }
        print(f"✅ Found Wrinkles: Primary {wrinkles.primary_intensity}, Secondary {wrinkles.secondary_intensity}")
    
    # Expression Intensity Panel
    if hasattr(scene, 'expr_intensity_props'):
        expr = scene.expr_intensity_props
        sliders_data['EXPRESSION_INTENSITY'] = {
            'expression_intensity': expr.expression_intensity
        }
        print(f"✅ Found Expression Intensity: {expr.expression_intensity}")
    
    # Secondary Intensity Panel
    if hasattr(scene, 'secondary_intensity_props'):
        secondary = scene.secondary_intensity_props
        sliders_data['SECONDARY_INTENSITY'] = {
            'secondary_intensity': secondary.secondary_intensity
        }
        print(f"✅ Found Secondary Intensity: {secondary.secondary_intensity}")
    
    # 2. GUI Objects Location (existing system)
    rig_coll = find_active_rig_collection(context)
    gui = find_gui_collection_in_rig(rig_coll) if rig_coll else None
    
    if gui:
        for obj in gui.all_objects:
            if obj.type == 'MESH':
                sliders_data['OBJECT_PROPERTIES'][obj.name] = {
                    "location": list(obj.location),
                    "rotation_euler": list(obj.rotation_euler),
                    "scale": list(obj.scale)
                }
        print(f"✅ Found {len(sliders_data['OBJECT_PROPERTIES'])} GUI objects")
    
    # 3. Bone Properties Scanning (for armature-based sliders)
    for obj in scene.objects:
        if obj.type == 'ARMATURE' and obj.data.bones:
            for bone in obj.data.bones:
                if bone.name.startswith("GUI_") or "control" in bone.name.lower() or "ctl" in bone.name.lower():
                    pose_bone = obj.pose.bones.get(bone.name)
                    if pose_bone:
                        sliders_data['BONE_PROPERTIES'][f"{obj.name}.{bone.name}"] = {
                            "location": list(pose_bone.location),
                            "rotation_euler": list(pose_bone.rotation_euler),
                            "scale": list(pose_bone.scale)
                        }
    
    print(f"✅ Found {len(sliders_data['BONE_PROPERTIES'])} bone controls")
    
    # 4. Property Groups Scanning (custom properties)
    for obj in scene.objects:
        if obj.keys():
            for key in obj.keys():
                if not key.startswith("_"):  # Skip hidden properties
                    if obj.name not in sliders_data['PROPERTY_GROUPS']:
                        sliders_data['PROPERTY_GROUPS'][obj.name] = {}
                    sliders_data['PROPERTY_GROUPS'][obj.name][key] = obj[key]
    
    total_sliders = sum(len(category) for category in sliders_data.values() if isinstance(category, dict))
    print(f"🎉 Universal scan complete! Found {total_sliders} total properties")
    
    return sliders_data

def load_all_gui_sliders_universal_with_updates(context, data, frame=None):
    """🎚️ CARICA E AGGIORNA TUTTI GLI SLIDERS COME MOVIMENTO MANUALE"""
    print("🔄 Loading universal GUI sliders with manual updates...")
    
    if frame is None:
        frame = context.scene.frame_current
    
    scene = context.scene
    
    # 1. Load Wrinkles Intensity
    if 'WRINKLES_INTENSITY' in data and hasattr(scene, 'wrinkles_props'):
        wrinkles_data = data['WRINKLES_INTENSITY']
        wrinkles = scene.wrinkles_props
        
        if 'primary_intensity' in wrinkles_data:
            wrinkles.primary_intensity = wrinkles_data['primary_intensity']
            # Force update callbacks if they exist
            context.view_layer.update()
            print(f"✅ Restored Primary Wrinkles: {wrinkles_data['primary_intensity']}")
        
        if 'secondary_intensity' in wrinkles_data:
            wrinkles.secondary_intensity = wrinkles_data['secondary_intensity']
            context.view_layer.update()
            print(f"✅ Restored Secondary Wrinkles: {wrinkles_data['secondary_intensity']}")
    
    # 2. Load Expression Intensity
    if 'EXPRESSION_INTENSITY' in data and hasattr(scene, 'expr_intensity_props'):
        expr_data = data['EXPRESSION_INTENSITY']
        expr = scene.expr_intensity_props
        expr.expression_intensity = expr_data['expression_intensity']
        context.view_layer.update()
        print(f"✅ Restored Expression Intensity: {expr_data['expression_intensity']}")
    
    # 3. Load Secondary Intensity
    if 'SECONDARY_INTENSITY' in data and hasattr(scene, 'secondary_intensity_props'):
        secondary_data = data['SECONDARY_INTENSITY']
        secondary = scene.secondary_intensity_props
        secondary.secondary_intensity = secondary_data['secondary_intensity']
        context.view_layer.update()
        print(f"✅ Restored Secondary Intensity: {secondary_data['secondary_intensity']}")
    
    # 4. Load GUI Objects (existing system)
    rig_coll = find_active_rig_collection(context)
    gui = find_gui_collection_in_rig(rig_coll) if rig_coll else None
    
    if gui and 'OBJECT_PROPERTIES' in data:
        for name, info in data['OBJECT_PROPERTIES'].items():
            matches = [obj for obj in gui.all_objects if obj.name.startswith(name)]
            for obj in matches:
                obj.location = info["location"]
                obj.keyframe_insert(data_path="location", frame=frame)
                if "rotation_euler" in info:
                    obj.rotation_euler = info["rotation_euler"]
                    obj.keyframe_insert(data_path="rotation_euler", frame=frame)
                if "scale" in info:
                    obj.scale = info["scale"]
                    obj.keyframe_insert(data_path="scale", frame=frame)
        print(f"✅ Restored {len(data['OBJECT_PROPERTIES'])} GUI objects")
    
    # 5. Load Bone Properties
    if 'BONE_PROPERTIES' in data:
        for bone_path, bone_data in data['BONE_PROPERTIES'].items():
            obj_name, bone_name = bone_path.split('.', 1)
            obj = scene.objects.get(obj_name)
            if obj and obj.type == 'ARMATURE':
                pose_bone = obj.pose.bones.get(bone_name)
                if pose_bone:
                    pose_bone.location = bone_data["location"]
                    pose_bone.rotation_euler = bone_data["rotation_euler"]
                    pose_bone.scale = bone_data["scale"]
                    pose_bone.keyframe_insert(data_path="location", frame=frame)
                    pose_bone.keyframe_insert(data_path="rotation_euler", frame=frame)
                    pose_bone.keyframe_insert(data_path="scale", frame=frame)
        print(f"✅ Restored {len(data['BONE_PROPERTIES'])} bone controls")
    
    # 6. Load Property Groups
    if 'PROPERTY_GROUPS' in data:
        for obj_name, properties in data['PROPERTY_GROUPS'].items():
            obj = scene.objects.get(obj_name)
            if obj:
                for key, value in properties.items():
                    obj[key] = value
                    # Try to keyframe custom properties
                    try:
                        obj.keyframe_insert(data_path=f'["{key}"]', frame=frame)
                    except:
                        pass  # Some properties may not be keyframeable
        print(f"✅ Restored property groups for {len(data['PROPERTY_GROUPS'])} objects")
    
    # Force scene update to trigger all callbacks
    context.view_layer.update()
    scene.frame_set(scene.frame_current)
    
    print("🎉 Universal GUI slider loading complete!")

def save_accessories_complete(context, library_path, char_name, type_):
    """🎭 SALVA ACCESSORIES COMPLETI CON MORPHING"""
    print(f"🎭 Saving complete accessories for {char_name}...")
    
    accessories_data = {
        'objects': [],
        'materials': {},
        'modifiers': {},
        'morphing_data': {}
    }
    
    rig_coll = find_active_rig_collection(context)
    accessories_coll = find_accessories_collection_in_rig(rig_coll)
    
    if accessories_coll:
        for obj in accessories_coll.all_objects:
            if obj.type == 'MESH':
                obj_data = {
                    'name': obj.name,
                    'location': list(obj.location),
                    'rotation_euler': list(obj.rotation_euler),
                    'scale': list(obj.scale),
                    'modifiers': []
                }
                
                # Save all modifiers
                for mod in obj.modifiers:
                    mod_data = {
                        'name': mod.name,
                        'type': mod.type
                    }
                    # Add specific modifier properties based on type
                    if mod.type == 'SURFACE_DEFORM':
                        mod_data['target'] = mod.target.name if mod.target else None
                        mod_data['is_bound'] = mod.is_bound
                    elif mod.type == 'SHRINKWRAP':
                        mod_data['target'] = mod.target.name if mod.target else None
                        mod_data['wrap_method'] = mod.wrap_method
                    
                    obj_data['modifiers'].append(mod_data)
                
                # Save materials
                if obj.material_slots:
                    obj_data['materials'] = []
                    for slot in obj.material_slots:
                        if slot.material:
                            obj_data['materials'].append(slot.material.name)
                            # Save complete material data
                            accessories_data['materials'][slot.material.name] = save_material_complete(slot.material)
                
                accessories_data['objects'].append(obj_data)
        
        print(f"✅ Saved {len(accessories_data['objects'])} accessories with complete data")
    
    return accessories_data

def save_material_complete(material):
    """🖼️ SALVA MATERIALE COMPLETO CON NODE TREE"""
    print(f"🖼️ Saving complete material: {material.name}")
    
    material_data = {
        'name': material.name,
        'use_nodes': material.use_nodes,
        'nodes': {},
        'links': [],
        'properties': {}
    }
    
    # Basic material properties
    material_data['properties'] = {
        'metallic': material.metallic,
        'roughness': material.roughness,
        'use_backface_culling': material.use_backface_culling,
        'blend_method': material.blend_method,
        'shadow_method': material.shadow_method
    }
    
    # Node tree data
    if material.use_nodes and material.node_tree:
        for node in material.node_tree.nodes:
            node_data = {
                'name': node.name,
                'type': node.type,
                'location': list(node.location),
                'inputs': {},
                'outputs': {}
            }
            
            # Save input values
            for input_socket in node.inputs:
                if input_socket.type == 'VALUE':
                    node_data['inputs'][input_socket.name] = input_socket.default_value
                elif input_socket.type == 'RGBA':
                    node_data['inputs'][input_socket.name] = list(input_socket.default_value)
                elif input_socket.type == 'VECTOR':
                    node_data['inputs'][input_socket.name] = list(input_socket.default_value)
            
            # Save image paths for texture nodes
            if node.type == 'TEX_IMAGE' and node.image:
                node_data['image_path'] = node.image.filepath
                node_data['image_name'] = node.image.name
            
            material_data['nodes'][node.name] = node_data
        
        # Save links
        for link in material.node_tree.links:
            link_data = {
                'from_node': link.from_node.name,
                'from_socket': link.from_socket.name,
                'to_node': link.to_node.name,
                'to_socket': link.to_socket.name
            }
            material_data['links'].append(link_data)
    
    print(f"✅ Saved material {material.name} with {len(material_data['nodes'])} nodes")
    return material_data

def save_displacement_extended(context, library_path, char_name):
    """🎨 SALVA TUTTI I DISPLACEMENT ESTESI"""
    print(f"🎨 Saving extended displacement for {char_name}...")
    
    displacement_data = {
        'head_displacement': {},
        'body_displacement': {},
        'shape_keys': {},
        'material_displacement': {}
    }
    
    rig_collection = find_active_rig_collection(context)
    head_obj = find_head_object_in_rig(rig_collection)
    
    # Save head displacement (existing system)
    if head_obj:
        displacement_data['head_displacement'] = get_displacement_data(head_obj)
        
        # Save shape keys
        if head_obj.data.shape_keys:
            shape_keys = {}
            for key_block in head_obj.data.shape_keys.key_blocks:
                if key_block.name != 'Basis':
                    shape_keys[key_block.name] = key_block.value
            displacement_data['shape_keys'] = shape_keys
            print(f"✅ Saved {len(shape_keys)} shape keys")
    
    # Save displacement for all mesh objects in rig
    if rig_collection:
        for obj in rig_collection.all_objects:
            if obj.type == 'MESH' and obj != head_obj:
                obj_displacement = get_displacement_data(obj)
                if obj_displacement['MICROSKIN'] or obj_displacement['WRINKLES']:
                    displacement_data['body_displacement'][obj.name] = obj_displacement
    
    # Save material-based displacement
    for obj in context.scene.objects:
        if obj.type == 'MESH' and obj.material_slots:
            for slot in obj.material_slots:
                if slot.material and slot.material.use_nodes:
                    material = slot.material
                    disp_nodes = []
                    for node in material.node_tree.nodes:
                        if node.type == 'DISPLACEMENT' or 'displace' in node.name.lower():
                            disp_nodes.append({
                                'name': node.name,
                                'type': node.type,
                                'inputs': {inp.name: inp.default_value for inp in node.inputs if inp.type == 'VALUE'}
                            })
                    if disp_nodes:
                        displacement_data['material_displacement'][material.name] = disp_nodes
    
    print(f"✅ Saved extended displacement data for {char_name}")
    return displacement_data

def prepare_morphing_universal(all_data):
    """🎬 PREPARA MORPHING UNIVERSALE PER TUTTO"""
    print("🎬 Preparing universal morphing data...")
    
    morphing_data = {
        'keyframeable_properties': [],
        'animation_curves': {},
        'morph_targets': {},
        'transition_data': {}
    }
    
    # Collect all keyframeable properties from universal data
    if 'GUI_SLIDERS_UNIVERSAL' in all_data:
        gui_data = all_data['GUI_SLIDERS_UNIVERSAL']
        
        # Add GUI object properties
        if 'OBJECT_PROPERTIES' in gui_data:
            for obj_name, properties in gui_data['OBJECT_PROPERTIES'].items():
                for prop_name in ['location', 'rotation_euler', 'scale']:
                    if prop_name in properties:
                        morphing_data['keyframeable_properties'].append(f"{obj_name}.{prop_name}")
        
        # Add bone properties
        if 'BONE_PROPERTIES' in gui_data:
            for bone_path, properties in gui_data['BONE_PROPERTIES'].items():
                for prop_name in ['location', 'rotation_euler', 'scale']:
                    if prop_name in properties:
                        morphing_data['keyframeable_properties'].append(f"{bone_path}.{prop_name}")
        
        # Add intensity properties
        for intensity_type in ['WRINKLES_INTENSITY', 'EXPRESSION_INTENSITY', 'SECONDARY_INTENSITY']:
            if intensity_type in gui_data:
                for prop_name in gui_data[intensity_type]:
                    morphing_data['keyframeable_properties'].append(f"scene.{intensity_type}.{prop_name}")
    
    # Add displacement properties
    if 'DISPLACEMENT_EXTENDED' in all_data:
        disp_data = all_data['DISPLACEMENT_EXTENDED']
        if 'shape_keys' in disp_data:
            for key_name in disp_data['shape_keys']:
                morphing_data['keyframeable_properties'].append(f"shape_key.{key_name}")
    
    # Add material properties
    if 'MATERIALS_COMPLETE' in all_data:
        materials_data = all_data['MATERIALS_COMPLETE']
        for mat_name, mat_data in materials_data.items():
            if 'nodes' in mat_data:
                for node_name, node_data in mat_data['nodes'].items():
                    if 'inputs' in node_data:
                        for input_name in node_data['inputs']:
                            morphing_data['keyframeable_properties'].append(f"material.{mat_name}.{node_name}.{input_name}")
    
    print(f"✅ Prepared morphing for {len(morphing_data['keyframeable_properties'])} properties")
    return morphing_data

def test_universal_system(context):
    """🧪 TEST COMPLETO DEL SISTEMA UNIVERSALE"""
    print("🧪 TESTING UNIVERSAL SYSTEM...")
    
    # Test scan
    sliders = scan_all_gui_sliders_universal(context)
    total_sliders = sum(len(category) for category in sliders.values() if isinstance(category, dict))
    print(f"✅ SLIDERS SCANNED: {total_sliders}")
    
    # Test morphing
    mock_data = {'GUI_SLIDERS_UNIVERSAL': sliders}
    morphing_data = prepare_morphing_universal(mock_data)
    print(f"✅ MORPHING PREPARED: {len(morphing_data.get('keyframeable_properties', []))} properties")
    
    # Test materials
    materials_count = len([obj for obj in context.scene.objects if obj.type == 'MESH' and obj.material_slots])
    print(f"✅ MATERIALS READY: {materials_count} objects with materials")
    
    # Test displacement
    rig_collection = find_active_rig_collection(context)
    head_obj = find_head_object_in_rig(rig_collection)
    displacement_ready = head_obj is not None
    print(f"✅ DISPLACEMENT READY: {displacement_ready}")
    
    # Test accessories
    accessories_coll = find_accessories_collection_in_rig(rig_collection) if rig_collection else None
    accessories_count = len(accessories_coll.all_objects) if accessories_coll else 0
    print(f"✅ ACCESSORIES READY: {accessories_count} objects")
    
    print("🎉 SISTEMA UNIVERSALE TEST COMPLETATO!")
    
    return {
        'total_sliders': total_sliders,
        'morphing_properties': len(morphing_data.get('keyframeable_properties', [])),
        'materials_count': materials_count,
        'displacement_ready': displacement_ready,
        'accessories_count': accessories_count
    }

# New Universal System Operators
class UNIFIEDLIB_OT_test_universal_system(Operator):
    bl_idname = "unified_lib.test_universal_system"
    bl_label = "Test Sistema Universale"
    bl_description = "Test complete universal system functionality"
    
    def execute(self, context):
        try:
            results = test_universal_system(context)
            message = f"Universal System Test Complete!\n"
            message += f"Sliders: {results['total_sliders']}\n"
            message += f"Morphing Properties: {results['morphing_properties']}\n"
            message += f"Materials: {results['materials_count']}\n"
            message += f"Displacement: {'Ready' if results['displacement_ready'] else 'Not Ready'}\n"
            message += f"Accessories: {results['accessories_count']}"
            
            self.report({'INFO'}, message)
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Universal system test failed: {e}")
            return {'CANCELLED'}

class UNIFIEDLIB_OT_scan_all_sliders(Operator):
    bl_idname = "unified_lib.scan_all_sliders"
    bl_label = "Scan All Sliders"
    bl_description = "Scan all GUI sliders in the scene"
    
    def execute(self, context):
        try:
            sliders = scan_all_gui_sliders_universal(context)
            total = sum(len(cat) for cat in sliders.values() if isinstance(cat, dict))
            self.report({'INFO'}, f"Found {total} sliders across all categories")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Slider scan failed: {e}")
            return {'CANCELLED'}

# New Universal System Panel
class UNIFIEDLIB_PT_universal_panel(Panel):
    bl_label = "SISTEMA UNIVERSALE"
    bl_idname = "UNIFIEDLIB_PT_universal"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "IDENTIRIG_PLUS"
    
    def draw(self, context):
        layout = self.layout
        
        # Test sistema
        box = layout.box()
        box.label(text="🧪 Test Sistema Universale", icon='EXPERIMENTAL')
        box.operator("unified_lib.test_universal_system", text="Run Complete Test", icon='PLAY')
        
        # Scan sliders
        box = layout.box()
        box.label(text="🔍 Scan Sliders", icon='VIEWZOOM')
        box.operator("unified_lib.scan_all_sliders", text="Scan All GUI Sliders", icon='BORDERMOVE')
        
        # Status
        box = layout.box()
        box.label(text="📊 Status Sistema", icon='INFO')
        
        # Check if rig is active
        if context.scene.identirig_active_library:
            box.label(text=f"✅ Active Rig: {context.scene.identirig_active_library}", icon='CHECKMARK')
            
            # Check components
            rig_collection = find_active_rig_collection(context)
            if rig_collection:
                gui_coll = find_gui_collection_in_rig(rig_collection)
                accessories_coll = find_accessories_collection_in_rig(rig_collection)
                head_obj = find_head_object_in_rig(rig_collection)
                
                box.label(text=f"GUI Collection: {'✅' if gui_coll else '❌'}")
                box.label(text=f"Accessories Collection: {'✅' if accessories_coll else '❌'}")
                box.label(text=f"Head Object: {'✅' if head_obj else '❌'}")
            else:
                box.label(text="❌ Rig collection not found", icon='ERROR')
        else:
            box.label(text="❌ No active rig selected", icon='ERROR')

# Registration
def register():
    # Register property groups
    bpy.utils.register_class(CharacterPreviewItem)
    bpy.utils.register_class(LibraryPreviewProps)
    
    # Register operators
    bpy.utils.register_class(IDENTILIBRARY_OT_refresh_local_characters)
    bpy.utils.register_class(IDENTILIBRARY_OT_refresh_ftp_characters)
    bpy.utils.register_class(IDENTILIBRARY_OT_ActivateRig)
    bpy.utils.register_class(UNIFIEDLIB_OT_save)
    bpy.utils.register_class(UNIFIEDLIB_OT_save_ftp)
    bpy.utils.register_class(UNIFIEDLIB_OT_save_ftp_with_preview)
    bpy.utils.register_class(UNIFIEDLIB_OT_load)
    bpy.utils.register_class(UNIFIEDLIB_OT_load_character_preview)
    bpy.utils.register_class(UNIFIEDLIB_OT_load_ftp_character_preview)
    bpy.utils.register_class(UNIFIEDLIB_OT_refresh_local)
    bpy.utils.register_class(UNIFIEDLIB_OT_refresh_ftp)
    bpy.utils.register_class(UNIFIEDLIB_OT_set_from_local)
    bpy.utils.register_class(UNIFIEDLIB_OT_set_from_ftp)
    bpy.utils.register_class(UNIFIEDLIB_PT_panel)
    bpy.utils.register_class(UnifiedLibraryPreferences)
    
    # 🆕 REGISTRA SISTEMA UNIVERSALE
    bpy.utils.register_class(UNIFIEDLIB_PT_universal_panel)
    bpy.utils.register_class(UNIFIEDLIB_OT_test_universal_system)
    bpy.utils.register_class(UNIFIEDLIB_OT_scan_all_sliders)
    
    # Register scene properties
    bpy.types.Scene.library_preview_props = PointerProperty(type=LibraryPreviewProps)
    bpy.types.Scene.identirig_active_library = StringProperty(name="Active Library Rig")
    
    print("✅ IDENTILIBRARY PLUS registered successfully!")
    print("✅ SISTEMA UNIVERSALE REGISTRATO!")

def unregister():
    # Unregister in reverse order
    # 🆕 UNREGISTER SISTEMA UNIVERSALE
    bpy.utils.unregister_class(UNIFIEDLIB_OT_scan_all_sliders)
    bpy.utils.unregister_class(UNIFIEDLIB_OT_test_universal_system)
    bpy.utils.unregister_class(UNIFIEDLIB_PT_universal_panel)
    
    bpy.utils.unregister_class(UnifiedLibraryPreferences)
    bpy.utils.unregister_class(UNIFIEDLIB_PT_panel)
    bpy.utils.unregister_class(UNIFIEDLIB_OT_set_from_ftp)
    bpy.utils.unregister_class(UNIFIEDLIB_OT_set_from_local)
    bpy.utils.unregister_class(UNIFIEDLIB_OT_refresh_ftp)
    bpy.utils.unregister_class(UNIFIEDLIB_OT_refresh_local)
    bpy.utils.unregister_class(UNIFIEDLIB_OT_load_ftp_character_preview)
    bpy.utils.unregister_class(UNIFIEDLIB_OT_load_character_preview)
    bpy.utils.unregister_class(UNIFIEDLIB_OT_load)
    bpy.utils.unregister_class(UNIFIEDLIB_OT_save_ftp_with_preview)
    bpy.utils.unregister_class(UNIFIEDLIB_OT_save_ftp)
    bpy.utils.unregister_class(UNIFIEDLIB_OT_save)
    bpy.utils.unregister_class(IDENTILIBRARY_OT_ActivateRig)
    bpy.utils.unregister_class(IDENTILIBRARY_OT_refresh_ftp_characters)
    bpy.utils.unregister_class(IDENTILIBRARY_OT_refresh_local_characters)
    bpy.utils.unregister_class(LibraryPreviewProps)
    bpy.utils.unregister_class(CharacterPreviewItem)
    
    # Unregister scene properties
    del bpy.types.Scene.library_preview_props
    del bpy.types.Scene.identirig_active_library
    
    print("✅ IDENTILIBRARY PLUS unregistered successfully!")

if __name__ == "__main__":
    register()