# IDENTIRIG_LIBRARY2 Enhanced Functionality

## Overview

This document describes the enhanced save/load functionality for accessories, materials, and GUI sliders implemented in the IDENTIRIG_LIBRARY2 Blender addon.

## New Features

### 1. Enhanced Material Serialization

#### What's New:
- **Custom Properties**: Materials now save all custom properties in JSON-compatible format
- **Shadow Method Fallback**: Safe handling of `shadow_method` property with fallback for older Blender versions
- **Node Properties**: Basic material node properties are preserved
- **Safe Serialization**: Only JSON-compatible data is saved, preventing serialization errors

#### Implementation:
- `serialize_material_safe()`: Safely exports material data to JSON
- `deserialize_material_safe()`: Recreates materials from JSON data
- `serialize_material_nodes_safe()`: Handles material node tree serialization
- `restore_material_nodes_safe()`: Restores basic node properties

### 2. Enhanced Accessory Management

#### What's New:
- **Material Slot Mapping**: Each accessory saves its complete material slot configuration
- **Custom Properties**: Accessory objects preserve all custom properties
- **Material Data**: Full material data is embedded in accessory saves
- **Automatic Reapplication**: Materials are automatically reapplied during loading

#### Implementation:
- `get_object_materials_data()`: Extracts material slot information from objects
- `apply_materials_to_object()`: Reapplies materials to object slots during loading
- Enhanced JSON structure in `save_full_library()` and `load_full_library()`

### 3. Enhanced GUI Slider Management

#### What's New:
- **Complete Scene Properties**: All scene-level custom properties (morph controls) are saved
- **Bone Properties**: Individual bone custom properties are preserved
- **Object Properties**: All object custom properties are saved
- **Universal Controls**: All GUI sliders and morph controls are captured

#### Implementation:
- Scene properties saved in `SCENE_PROPERTIES` section
- Bone properties saved in `BONE_PROPERTIES` section  
- Object properties saved in `OBJECT_PROPERTIES` section
- Automatic restoration during character loading

## File Structure Changes

### _gui.json Format Enhancement

The GUI JSON files now include these new sections:

```json
{
  "WRINKLES_INTENSITY": {
    "primary_intensity": 0.75,
    "secondary_intensity": 0.50
  },
  "SCENE_PROPERTIES": {
    "morph_strength": 1.0,
    "expression_blend": 0.8,
    "custom_morph": [0.5, 0.3, 0.7]
  },
  "BONE_PROPERTIES": {
    "Head": {
      "custom_rotation": 0.2,
      "expression_factor": 0.9
    }
  },
  "OBJECT_PROPERTIES": {
    "Hair_Object": {
      "density": 0.8,
      "length": 1.2
    }
  }
}
```

### Character JSON Format Enhancement

The character JSON files now include:

```json
{
  "curves": ["HairCurve1", "HairCurve2"],
  "surfaces": ["AccessoryMesh1", "AccessoryMesh2"],
  "accessories": {
    "AccessoryMesh1": {
      "name": "AccessoryMesh1",
      "materials": [
        {
          "slot_index": 0,
          "material_name": "MaterialName",
          "material_data": { /* full material data */ },
          "link": "OBJECT"
        }
      ],
      "custom_properties": {
        "accessory_type": "hat",
        "visibility": true
      }
    }
  }
}
```

## Compatibility

- **Blender Version**: Compatible with Blender 3.0+ and 4.0+
- **Backward Compatibility**: Old save files still load correctly
- **Safe Fallbacks**: All new features have safe fallbacks if properties don't exist
- **JSON Compatibility**: Only JSON-compatible data types are serialized

## Benefits

1. **Complete State Preservation**: All GUI controls, materials, and accessory configurations are preserved
2. **Robust Material Handling**: Materials are recreated exactly as they were saved
3. **Enhanced Workflow**: No need to manually reconfigure materials or GUI settings after loading
4. **Future-Proof**: Safe fallbacks ensure compatibility across different Blender versions

## Usage

The enhanced functionality is automatically used when saving and loading characters:

1. **Saving**: Run the save operation as usual - all enhanced data is captured automatically
2. **Loading**: Load characters as usual - all materials, GUI settings, and properties are restored
3. **FTP Sync**: Enhanced data is included in FTP uploads and downloads

## Testing

Run the included test script to verify functionality:

```bash
python3 test_enhanced_functionality.py
```

This tests:
- Material serialization/deserialization
- Accessory data structure
- GUI data expansion
- File operations

All tests should pass for the enhanced functionality to work correctly.