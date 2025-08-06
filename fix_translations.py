#!/usr/bin/env python3
"""
Script to fix missing translation values in i18n files.
Replaces empty string values with the key itself as a fallback.
"""

import json
import os
import glob
from pathlib import Path

def fix_translation_file(file_path):
    """Fix a single translation file by replacing empty values with the key."""
    print(f"Processing {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    changes_made = 0
    for key, value in data.items():
        if value == "":
            data[key] = key  # Use the key itself as the fallback translation
            changes_made += 1
    
    if changes_made > 0:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent='\t')
        print(f"  Fixed {changes_made} empty values")
    else:
        print(f"  No changes needed")
    
    return changes_made

def main():
    """Main function to process all translation files."""
    locales_dir = Path("src/lib/i18n/locales")
    
    if not locales_dir.exists():
        print(f"Error: {locales_dir} directory not found")
        return
    
    # Find all translation.json files
    translation_files = glob.glob(str(locales_dir / "*" / "translation.json"))
    
    if not translation_files:
        print("No translation.json files found")
        return
    
    total_changes = 0
    for file_path in sorted(translation_files):
        changes = fix_translation_file(file_path)
        total_changes += changes
    
    print(f"\nTotal changes made: {total_changes}")
    print("All translation files have been processed!")

if __name__ == "__main__":
    main()
