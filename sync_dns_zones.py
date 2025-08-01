#!/usr/bin/env python3
"""
DNS Zone Synchronization Script for Infoblox Universal DDI

This script performs bi-directional synchronization of A records between two DNS views
in the same Infoblox Universal DDI region.

Features:
- Bi-directional sync between two views in the same zone
- Loop prevention using detailed comment field markers
- Conflict detection and resolution
- Console logging of all operations
- Single API token authentication

Usage:
    Set environment variables in .env file, then run:
    python sync_dns_zones.py

Configuration:
    Copy config.py.example to config.py and set the following values:
    - INFOBLOX_API_URL: API endpoint (e.g., https://csp.infoblox.com)
    - INFOBLOX_API_TOKEN: API token with DNS management permissions
    - DNS_VIEW_SOURCE: Source view name (e.g., AZURE-3)
    - DNS_VIEW_TARGET: Target view name (e.g., AZURE-9)
    - DNS_ZONE_NAME: Name of the zone to sync (e.g., privatelink.blob.core.windows.net.)
"""

import os
import sys
import json
import requests
from datetime import datetime, timezone
from typing import Dict, List, Optional
import logging

# Import configuration
try:
    import config
except ImportError:
    logger.error("Configuration file 'config.py' not found.")
    logger.error("Please copy 'config.py.example' to 'config.py' and update with your settings.")
    sys.exit(1)

# Configure logging to console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

class InfobloxConfig:
    """Configuration class for Infoblox API settings"""
    
    def __init__(self):
        # Load configuration from config.py
        self.api_url = getattr(config, 'INFOBLOX_API_URL', '')
        self.api_token = getattr(config, 'INFOBLOX_API_TOKEN', '')
        self.source_view = getattr(config, 'DNS_VIEW_SOURCE', '')
        self.target_view = getattr(config, 'DNS_VIEW_TARGET', '')
        self.zone_name = getattr(config, 'DNS_ZONE_NAME', 'privatelink.blob.core.windows.net.')
        
        # Validate required configuration
        if not all([self.api_url, self.api_token, self.source_view, self.target_view]):
            logger.error("Missing required configuration in config.py. Please set:")
            logger.error("- INFOBLOX_API_URL")
            logger.error("- INFOBLOX_API_TOKEN") 
            logger.error("- DNS_VIEW_SOURCE")
            logger.error("- DNS_VIEW_TARGET")
            logger.error("- DNS_ZONE_NAME (optional, defaults to privatelink.blob.core.windows.net.)")
            sys.exit(1)
        
        logger.info(f"Configuration loaded for zone: {self.zone_name}")
        logger.info(f"Source view: {self.source_view} → Target view: {self.target_view}")

class InfobloxAPIClient:
    """Client for interacting with Infoblox Universal DDI REST API"""
    
    def __init__(self, base_url: str, token: str, view_name: str):
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.view_name = view_name
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Token {token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
    def _make_request(self, method: str, endpoint: str, data: dict = None) -> Optional[dict]:
        """Make HTTP request to Infoblox API"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data)
            elif method.upper() == 'PATCH':
                response = self.session.patch(url, json=data)
            else:
                logger.error(f"Unsupported HTTP method: {method}")
                return None
                
            response.raise_for_status()
            
            if response.content:
                return response.json()
            return {}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed for {method} {url}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    logger.error(f"Error details: {error_detail}")
                except:
                    logger.error(f"Response content: {e.response.text}")
            return None
    
    def get_view_id(self, view_name: str) -> Optional[str]:
        """Get the view ID for a given view name"""
        endpoint = "api/ddi/v1/dns/view"
        
        params = {
            '_filter': f'name=="{view_name}"',
            '_fields': 'id,name',
            '_limit': 10
        }
        
        url_params = '&'.join([f"{k}={v}" for k, v in params.items()])
        full_endpoint = f"{endpoint}?{url_params}"
        
        result = self._make_request('GET', full_endpoint)
        
        if result and isinstance(result, dict) and 'results' in result:
            views = result['results']
            if views:
                view_id = views[0]['id']
                logger.debug(f"Found view '{view_name}' with ID: {view_id}")
                return view_id
        
        logger.error(f"Could not find view '{view_name}'")
        return None
    
    def get_a_records(self, zone_name: str) -> List[Dict]:
        """Fetch all A records from a DNS zone using the correct API endpoint"""
        endpoint = "api/ddi/v1/dns/record"
        
        logger.info(f"Fetching A records from zone '{zone_name}' in view '{self.view_name}'")
        
        # Query parameters to filter for A records in the specified zone
        # Note: API doesn't support filtering by view, so we'll get all records in zone and filter client-side
        params = {
            '_filter': f'type=="A" and absolute_zone_name=="{zone_name}"',
            '_fields': 'id,name_in_zone,absolute_zone_name,rdata,comment,type,view,view_name,created_at,updated_at',
            '_limit': 1000
        }
        
        # Build URL with parameters
        url_params = '&'.join([f"{k}={v}" for k, v in params.items()])
        full_endpoint = f"{endpoint}?{url_params}"
        
        records = self._make_request('GET', full_endpoint)
        
        if records is not None:
            logger.debug(f"Successfully fetched records from {endpoint}")
            if isinstance(records, dict) and 'results' in records:
                all_records = records['results']
                # Filter records by view_name client-side since API doesn't support view filtering
                view_records = [r for r in all_records if r.get('view_name') == self.view_name]
                logger.info(f"Found {len(all_records)} total A records in zone {zone_name}, {len(view_records)} in view '{self.view_name}'")
                return view_records
            elif isinstance(records, list):
                # Filter records by view_name client-side
                view_records = [r for r in records if r.get('view_name') == self.view_name]
                logger.info(f"Found {len(records)} total A records in zone {zone_name}, {len(view_records)} in view '{self.view_name}'")
                return view_records
            else:
                logger.warning(f"Unexpected response format: {type(records)}")
                return []
        
        logger.error(f"Failed to fetch A records from zone {zone_name} (view: {self.view_name})")
        return []
    
    def create_a_record(self, name_in_zone: str, ip_address: str, zone_name: str, description: str) -> bool:
        """Create a new A record using the correct API structure"""
        # First get the view ID
        view_id = self.get_view_id(self.view_name)
        if not view_id:
            logger.error(f"Cannot create record without view ID for view '{self.view_name}'")
            return False
        
        # Based on swagger (2).yaml, create A record with proper structure
        # Using absolute_name_spec and view approach as recommended in swagger docs
        absolute_name = f"{name_in_zone}.{zone_name}" if name_in_zone and not name_in_zone.endswith('.') else zone_name
        
        record_data = {
            'type': 'A',
            'rdata': {
                'address': ip_address
            },
            'comment': description,
            'absolute_name_spec': absolute_name,
            'view': view_id
        }
        
        endpoint = "api/ddi/v1/dns/record"
        
        logger.info(f"Creating A record: {name_in_zone}.{zone_name} -> {ip_address} (view: {self.view_name})")
        result = self._make_request('POST', endpoint, record_data)
        
        if result is not None:
            logger.info(f"Successfully created A record: {name_in_zone}.{zone_name} -> {ip_address} (view: {self.view_name})")
            return True
        
        logger.error(f"Failed to create A record: {name_in_zone}.{zone_name} -> {ip_address} (view: {self.view_name})")
        return False
    
    def update_a_record(self, record_id: str, ip_address: str, description: str) -> bool:
        """Update an existing A record using PATCH method"""
        # Based on swagger (2).yaml, update record using PATCH with proper structure
        update_data = {
            'rdata': {
                'address': ip_address
            },
            'comment': description
        }
        
        endpoint = f"api/ddi/v1/dns/record/{record_id}"
        
        logger.info(f"Updating A record {record_id} to IP {ip_address} (view: {self.view_name})")
        result = self._make_request('PATCH', endpoint, update_data)
        
        if result is not None:
            logger.info(f"Successfully updated A record {record_id} to IP {ip_address} (view: {self.view_name})")
            return True
        
        logger.error(f"Failed to update A record {record_id} (view: {self.view_name})")
        return False

class DNSRecordSync:
    """Main class for DNS record synchronization between two views"""
    
    def __init__(self, config: InfobloxConfig):
        self.config = config
        self.source_client = InfobloxAPIClient(
            config.api_url, 
            config.api_token, 
            config.source_view
        )
        self.target_client = InfobloxAPIClient(
            config.api_url,
            config.api_token, 
            config.target_view
        )
        
    def _get_sync_marker(self, source_view: str, created_timestamp: str = None) -> str:
        """Generate detailed sync marker for comment field"""
        sync_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        created_info = f", created: {created_timestamp}" if created_timestamp else ""
        return f"Synced from {source_view} on {sync_time}{created_info}"
    
    def _is_synced_from_view(self, comment: str, view_name: str) -> bool:
        """Check if record was last synced from a specific view"""
        if not comment:
            return False
        return f"Synced from {view_name}" in comment
    
    def _extract_record_key(self, record: Dict) -> str:
        """Extract unique key for record comparison"""
        # Use name_in_zone which is the relative name within the zone
        name_in_zone = record.get('name_in_zone', '')
        # If name_in_zone is empty, this might be the zone apex record
        if not name_in_zone:
            name_in_zone = '@'  # Common notation for zone apex
        return name_in_zone
    
    def sync_records_one_way(self, source_client: InfobloxAPIClient, 
                           target_client: InfobloxAPIClient,
                           source_view: str, target_view: str) -> int:
        """Sync records from source to target view"""
        logger.info(f"Syncing records from {source_view} to {target_view}")
        
        # Fetch records from both views
        source_records = source_client.get_a_records(self.config.zone_name)
        target_records = target_client.get_a_records(self.config.zone_name)
        
        if source_records is None or target_records is None:
            logger.error("Failed to fetch records from one or both views")
            return 0
        
        logger.info(f"Found {len(source_records)} records in {source_view}")
        logger.info(f"Found {len(target_records)} records in {target_view}")
        
        # Build lookup dict for target records
        target_lookup = {}
        for record in target_records:
            key = self._extract_record_key(record)
            target_lookup[key] = record
        
        synced_count = 0
        
        # Process each source record
        for source_record in source_records:
            source_key = self._extract_record_key(source_record)
            # Extract IP address from rdata structure
            source_ip = ''
            if 'rdata' in source_record and isinstance(source_record['rdata'], dict):
                source_ip = source_record['rdata'].get('address', '')
            source_comment = source_record.get('comment', '')
            source_created = source_record.get('created_at', '')
            
            # Skip if this record was synced from target view (prevent loops)
            if self._is_synced_from_view(source_comment, target_view):
                logger.debug(f"Skipping {source_key} - originally from {target_view}")
                continue
            
            if source_key in target_lookup:
                # Record exists in target - check if update needed
                target_record = target_lookup[source_key]
                # Extract IP address from rdata structure
                target_ip = ''
                if 'rdata' in target_record and isinstance(target_record['rdata'], dict):
                    target_ip = target_record['rdata'].get('address', '')
                target_comment = target_record.get('comment', '')
                
                if source_ip != target_ip:
                    # IPs differ - check sync direction to avoid conflicts
                    if self._is_synced_from_view(target_comment, source_view):
                        # Target was last synced from source, so update target
                        new_comment = self._get_sync_marker(source_view, source_created)
                        record_id = target_record.get('id')
                        
                        if record_id and target_client.update_a_record(record_id, source_ip, new_comment):
                            logger.info(f"Updated {source_key}: {target_ip} -> {source_ip}")
                            synced_count += 1
                        else:
                            logger.error(f"Failed to update {source_key}")
                    else:
                        # Potential conflict - both records changed
                        logger.warning(f"CONFLICT: {source_key} has different IPs - "
                                     f"source: {source_ip}, target: {target_ip}. Skipping.")
                else:
                    logger.debug(f"Record {source_key} already in sync")
            else:
                # Record missing in target - create it
                new_comment = self._get_sync_marker(source_view, source_created)
                
                if target_client.create_a_record(source_key, source_ip, self.config.zone_name, new_comment):
                    logger.info(f"Created {source_key}: {source_ip}")
                    synced_count += 1
                else:
                    logger.error(f"Failed to create {source_key}")
        
        return synced_count
    
    def run_sync(self) -> None:
        """Run bi-directional synchronization"""
        logger.info("=" * 60)
        logger.info("Starting DNS Zone Synchronization")
        logger.info(f"Zone: {self.config.zone_name}")
        logger.info(f"Views: {self.config.source_view} ↔ {self.config.target_view}")
        logger.info("=" * 60)
        
        try:
            # Sync source -> target
            count1 = self.sync_records_one_way(
                self.source_client, self.target_client, 
                self.config.source_view, self.config.target_view
            )
            
            # Sync target -> source  
            count2 = self.sync_records_one_way(
                self.target_client, self.source_client,
                self.config.target_view, self.config.source_view
            )
            
            total_synced = count1 + count2
            logger.info("=" * 60)
            logger.info(f"Synchronization completed")
            logger.info(f"Records synced {self.config.source_view}→{self.config.target_view}: {count1}")
            logger.info(f"Records synced {self.config.target_view}→{self.config.source_view}: {count2}")
            logger.info(f"Total records synced: {total_synced}")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"Synchronization failed with error: {e}")
            raise

def main():
    """Main entry point"""
    try:
        # Load configuration
        config = InfobloxConfig()
        
        # Create and run synchronizer
        sync = DNSRecordSync(config)
        sync.run_sync()
        
    except KeyboardInterrupt:
        logger.info("Synchronization interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()