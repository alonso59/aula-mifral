#!/usr/bin/env python3
"""
Script to validate that translation files have no empty values.
"""

import json
import glob
from pathlib import Path

def validate_translation_file(file_path):
    """Validate a single translation file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        empty_count = sum(1 for value in data.values() if value == "")
        total_keys = len(data)
        
        return {
            'file': file_path,
            'total_keys': total_keys,
            'empty_values': empty_count,
            'valid': empty_count == 0
        }
    except Exception as e:
        return {
            'file': file_path,
            'error': str(e),
            'valid': False
        }

def main():
    """Main function to validate all translation files."""
    locales_dir = Path("src/lib/i18n/locales")
    
    if not locales_dir.exists():
        print(f"Error: {locales_dir} directory not found")
        return
    
    # Find all translation.json files
    translation_files = glob.glob(str(locales_dir / "*" / "translation.json"))
    
    if not translation_files:
        print("No translation.json files found")
        return
    
    print(f"Validating {len(translation_files)} translation files...\n")
    
    all_valid = True
    total_empty = 0
    
    for file_path in sorted(translation_files):
        result = validate_translation_file(file_path)
        
        if 'error' in result:
            print(f"❌ {Path(file_path).parent.name}: ERROR - {result['error']}")
            all_valid = False
        elif result['valid']:
            print(f"✅ {Path(file_path).parent.name}: {result['total_keys']} keys, 0 empty values")
        else:
            print(f"❌ {Path(file_path).parent.name}: {result['total_keys']} keys, {result['empty_values']} empty values")
            total_empty += result['empty_values']
            all_valid = False
    
    print(f"\nValidation Results:")
    print(f"Files processed: {len(translation_files)}")
    print(f"Total empty values found: {total_empty}")
    print(f"All files valid: {'Yes' if all_valid else 'No'}")
    
    if all_valid:
        print("\n🎉 All translation files are valid! The i18n:parse step should now pass.")
    else:
        print(f"\n⚠️  Found issues in translation files. Please fix before running i18n:parse.")

if __name__ == "__main__":
    main()
