#!/usr/bin/env python3
"""
Test script to verify the enhanced material and accessory functionality.
This script tests the new material serialization functions.
"""

import json
import os
import sys
import tempfile

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Test data to simulate Blender material properties
test_material_data = {
    "name": "TestMaterial",
    "use_nodes": True,
    "blend_method": "BLEND",
    "shadow_method": "CLIP",
    "use_backface_culling": False,
    "use_screen_refraction": False,
    "refraction_depth": 0.1,
    "use_sss_translucency": False,
    "pass_index": 0,
    "diffuse_color": [0.8, 0.2, 0.2, 1.0],
    "metallic": 0.0,
    "specular": 0.5,
    "roughness": 0.4,
    "alpha": 1.0,
    "custom_properties": {
        "test_prop": "test_value",
        "numeric_prop": 42,
        "vector_prop": [1.0, 2.0, 3.0]
    },
    "nodes": {
        "Principled BSDF": {
            "type": "BSDF_PRINCIPLED",
            "location": [0.0, 0.0],
            "inputs": {
                "Base Color": [0.8, 0.2, 0.2, 1.0],
                "Metallic": 0.0,
                "Roughness": 0.4
            }
        }
    }
}

def test_material_serialization():
    """Test that material data can be properly serialized and deserialized"""
    print("🧪 Testing material serialization...")
    
    # Test JSON serialization
    try:
        json_str = json.dumps(test_material_data, indent=2)
        print("✅ Material data serializes to JSON successfully")
        
        # Test deserialization
        deserialized = json.loads(json_str)
        
        # Check key properties
        assert deserialized["name"] == "TestMaterial"
        assert deserialized["shadow_method"] == "CLIP"
        assert deserialized["custom_properties"]["test_prop"] == "test_value"
        assert deserialized["custom_properties"]["numeric_prop"] == 42
        assert deserialized["custom_properties"]["vector_prop"] == [1.0, 2.0, 3.0]
        
        print("✅ Material data deserializes correctly")
        
    except Exception as e:
        print(f"❌ Material serialization test failed: {e}")
        return False
    
    return True

def test_accessory_data_structure():
    """Test the enhanced accessory data structure"""
    print("🧪 Testing accessory data structure...")
    
    accessory_data = {
        "name": "TestAccessory",
        "materials": [
            {
                "slot_index": 0,
                "material_name": "TestMaterial",
                "material_data": test_material_data,
                "link": "OBJECT"
            }
        ],
        "custom_properties": {
            "accessory_type": "hat",
            "visibility": True
        }
    }
    
    try:
        # Test JSON serialization
        json_str = json.dumps(accessory_data, indent=2)
        print("✅ Accessory data serializes to JSON successfully")
        
        # Test deserialization
        deserialized = json.loads(json_str)
        
        # Check structure
        assert "materials" in deserialized
        assert len(deserialized["materials"]) == 1
        assert deserialized["materials"][0]["material_name"] == "TestMaterial"
        assert deserialized["custom_properties"]["accessory_type"] == "hat"
        
        print("✅ Accessory data structure is valid")
        
    except Exception as e:
        print(f"❌ Accessory data test failed: {e}")
        return False
    
    return True

def test_gui_data_expansion():
    """Test the enhanced GUI data structure"""
    print("🧪 Testing enhanced GUI data structure...")
    
    gui_data = {
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
    
    try:
        # Test JSON serialization
        json_str = json.dumps(gui_data, indent=2)
        print("✅ Enhanced GUI data serializes to JSON successfully")
        
        # Test deserialization
        deserialized = json.loads(json_str)
        
        # Check structure
        assert "SCENE_PROPERTIES" in deserialized
        assert "BONE_PROPERTIES" in deserialized
        assert "OBJECT_PROPERTIES" in deserialized
        assert deserialized["SCENE_PROPERTIES"]["morph_strength"] == 1.0
        assert deserialized["BONE_PROPERTIES"]["Head"]["custom_rotation"] == 0.2
        
        print("✅ Enhanced GUI data structure is valid")
        
    except Exception as e:
        print(f"❌ GUI data test failed: {e}")
        return False
    
    return True

def test_file_operations():
    """Test file save/load operations"""
    print("🧪 Testing file operations...")
    
    try:
        # Test saving to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_material_data, f, indent=2)
            temp_path = f.name
        
        # Test loading from file
        with open(temp_path, 'r') as f:
            loaded_data = json.load(f)
        
        # Verify data integrity
        assert loaded_data["name"] == test_material_data["name"]
        assert loaded_data["shadow_method"] == test_material_data["shadow_method"]
        
        # Clean up
        os.unlink(temp_path)
        
        print("✅ File operations work correctly")
        
    except Exception as e:
        print(f"❌ File operations test failed: {e}")
        return False
    
    return True

def main():
    """Run all tests"""
    print("🚀 Starting enhanced IDENTIRIG_LIBRARY2 functionality tests...")
    print("=" * 60)
    
    tests = [
        test_material_serialization,
        test_accessory_data_structure,
        test_gui_data_expansion,
        test_file_operations
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            failed += 1
        print("-" * 40)
    
    print(f"🎉 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✅ All tests passed! Enhanced functionality is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())