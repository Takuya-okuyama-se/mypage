#!/usr/local/bin/python
# -*- coding: utf-8 -*-

"""
improvement_filter_api.pyのテスト
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from improvement_filter_api import get_elementary_improved_students, get_middle_improved_students
    
    print("Content-Type: text/plain; charset=utf-8")
    print()
    
    # 小学生のテスト
    print("=== Testing Elementary Students ===")
    try:
        result = get_elementary_improved_students({
            'start_month': '4',
            'end_month': '5',
            'subject': 'all',
            'min_improvement': '0'
        })
        print(f"Success: {result.get('success')}")
        print(f"Students found: {len(result.get('students', []))}")
        if result.get('success') is False:
            print(f"Error: {result.get('message')}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    # 中学生の内申点テスト
    print("\n=== Testing Middle Students (Internal Points) ===")
    try:
        result = get_middle_improved_students({
            'from_internal': '1-1',
            'to_internal': '1-2',
            'subject': 'all',
            'min_improvement': '0'
        })
        print(f"Success: {result.get('success')}")
        print(f"Students found: {len(result.get('students', []))}")
        if result.get('success') is False:
            print(f"Error: {result.get('message')}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        
except ImportError as e:
    print("Content-Type: text/plain; charset=utf-8")
    print()
    print(f"Import Error: {e}")
    import traceback
    traceback.print_exc()