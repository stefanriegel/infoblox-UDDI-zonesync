#!/usr/bin/env python3
"""
Test script to verify DNS sync configuration and connectivity.

This script validates:
- Configuration file is properly set up
- API connectivity to Infoblox
- View and zone existence
- Permissions to read DNS records

Usage:
    python3 test_connection.py
"""

import os
import sys
from sync_dns_zones import InfobloxConfig, InfobloxAPIClient

def test_configuration():
    """Test if all configuration is correct"""
    print("🔧 Testing Configuration...")
    
    try:
        config = InfobloxConfig()
        print("✅ Configuration loaded successfully")
        print(f"   Zone: {config.zone_name}")
        print(f"   Source View: {config.source_view}")
        print(f"   Target View: {config.target_view}")
        return config
    except SystemExit:
        print("❌ Configuration failed - check your config.py file")
        return None
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return None

def test_api_connectivity(config):
    """Test API connectivity to both views"""
    print("\n🌐 Testing API Connectivity...")
    
    results = {}
    
    # Test Source View
    print(f"\n   Testing Source View ({config.source_view})...")
    source_client = InfobloxAPIClient(config.api_url, config.api_token, config.source_view)
    
    try:
        view_id = source_client.get_view_id(config.source_view)
        if view_id:
            print(f"   ✅ View '{config.source_view}' found (ID: {view_id})")
            
            records = source_client.get_a_records(config.zone_name)
            if records is not None:
                print(f"   ✅ Zone access successful ({len(records)} records found)")
                results['source'] = {'status': 'success', 'records': len(records)}
            else:
                print("   ❌ Failed to fetch records from zone")
                results['source'] = {'status': 'zone_error', 'records': 0}
        else:
            print(f"   ❌ View '{config.source_view}' not found")
            results['source'] = {'status': 'view_error', 'records': 0}
    except Exception as e:
        print(f"   ❌ Source view error: {e}")
        results['source'] = {'status': 'error', 'records': 0}
    
    # Test Target View
    print(f"\n   Testing Target View ({config.target_view})...")
    target_client = InfobloxAPIClient(config.api_url, config.api_token, config.target_view)
    
    try:
        view_id = target_client.get_view_id(config.target_view)
        if view_id:
            print(f"   ✅ View '{config.target_view}' found (ID: {view_id})")
            
            records = target_client.get_a_records(config.zone_name)
            if records is not None:
                print(f"   ✅ Zone access successful ({len(records)} records found)")
                results['target'] = {'status': 'success', 'records': len(records)}
            else:
                print("   ❌ Failed to fetch records from zone")
                results['target'] = {'status': 'zone_error', 'records': 0}
        else:
            print(f"   ❌ View '{config.target_view}' not found")
            results['target'] = {'status': 'view_error', 'records': 0}
    except Exception as e:
        print(f"   ❌ Target view error: {e}")
        results['target'] = {'status': 'error', 'records': 0}
    
    return results

def print_summary(results):
    """Print test summary"""
    print("\n" + "="*50)
    print("📊 TEST SUMMARY")
    print("="*50)
    
    if not results:
        print("❌ Configuration failed - cannot proceed with tests")
        print("\n💡 Next steps:")
        print("   1. Copy config.py.example to config.py")
        print("   2. Add your API token and view names")
        print("   3. Run this test again")
        return False
    
    all_good = True
    
    for view, result in results.items():
        status_icon = "✅" if result['status'] == 'success' else "❌"
        print(f"{status_icon} {view.title()}: {result['status']} ({result['records']} records)")
        if result['status'] != 'success':
            all_good = False
    
    if all_good:
        print("\n🎉 All tests passed! Your DNS sync is ready to use.")
        print("\n▶️  Run the sync with: python3 sync_dns_zones.py")
    else:
        print("\n❌ Some tests failed. Please check your configuration.")
        print("\n💡 Common issues:")
        print("   - Verify API token is valid and has DNS permissions")
        print("   - Check view names are correct (case-sensitive)")
        print("   - Ensure zone exists in both views")
        print("   - Confirm network connectivity to Infoblox API")
    
    return all_good

def main():
    """Main test function"""
    print("🧪 DNS Sync Configuration Test")
    print("=" * 40)
    
    # Test configuration
    config = test_configuration()
    if not config:
        print_summary(None)
        sys.exit(1)
    
    # Test API connectivity
    results = test_api_connectivity(config)
    
    # Print summary
    success = print_summary(results)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()