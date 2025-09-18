#!/usr/bin/env python3

"""
A script to query a Canonical MaaS server and generate a report on machine status,
categorizing them into available, potentially problematic, and failed states.
"""

import os
import re
import sys
from maas.client import connect

# --- Configuration ---
# The script reads connection details from environment variables for security.
# Ensure MAAS_API_URL and MAAS_API_KEY are set in your shell.
MAAS_API_URL = os.environ.get("MAAS_API_URL")
MAAS_API_KEY = os.environ.get("MAAS_API_KEY")


def get_maas_client(url, api_key):
    """Connects to the MaaS API and returns a client object."""
    if not url or not api_key:
        print("Error: MAAS_API_URL and MAAS_API_KEY environment variables must be set.", file=sys.stderr)
        sys.exit(1)
    try:
        print(f"--> Connecting to MaaS at {url}...")
        client = connect(url, apikey=api_key)
        # A simple call to verify the connection is active
        client.users.list()
        print("--> Successfully connected to MaaS.")
        return client
    except Exception as e:
        print(f"Error connecting to MaaS: {e}", file=sys.stderr)
        sys.exit(1)


def generate_report(machines):
    """
    Analyzes a list of machine objects, categorizes them, and prints a
    formatted report to the console.
    """
    # Initialize lists for each report section
    available_servers = []
    potential_issue_servers = []
    failed_servers = []

    # Compile a regular expression to find 'DCOPS-*' tags (case-insensitive)
    dcops_pattern = re.compile(r'^DCOPS-.*', re.IGNORECASE)

    # Iterate over all machines to categorize them
    for machine in machines:
        # Category C: Machines in any kind of failed state
        # These are checked first, regardless of other conditions.
        if "failed" in machine.status_name.lower() or "broken" in machine.status_name.lower():
            failed_servers.append(machine)
            continue  # Once categorized as failed, move to the next machine

        # Categories A & B only apply to machines in the 'Ready' state
        if machine.status_name == 'Ready':
            machine_tags_lower = [tag.lower() for tag in machine.tags]
            
            # Category A: 'Ready' machines with an 'available' tag
            if 'available' in machine_tags_lower:
                available_servers.append(machine)

            # Category B: 'Ready' machines with a 'DCOPS-*' tag
            if any(dcops_pattern.match(tag) for tag in machine.tags):
                potential_issue_servers.append(machine)

    # --- Print the Formatted Report ---
    print("\n" + "="*60)
    print("        MaaS Machine Status Report")
    print("="*60 + "\n")

    # Section A: (servers available)
    print("="*30)
    print("(servers available)")
    print("="*30)
    if available_servers:
        for m in sorted(available_servers, key=lambda x: x.hostname):
            owner = m.owner.username if m.owner else "Unassigned"
            print(f"  - Host: {m.hostname:<25} System ID: {m.system_id:<12} Owner: {owner:<15} Tags: {m.tags}")
    else:
        print("  No machines in 'Ready' state found with the 'available' tag.")
    print("\n")

    # Section B: (servers with potential issues)
    print("="*30)
    print("(servers with potential issues)")
    print("="*30)
    if potential_issue_servers:
        for m in sorted(potential_issue_servers, key=lambda x: x.hostname):
            owner = m.owner.username if m.owner else "Unassigned"
            print(f"  - Host: {m.hostname:<25} System ID: {m.system_id:<12} Owner: {owner:<15} Tags: {m.tags}")
    else:
        print("  No machines in 'Ready' state found with a 'DCOPS-*' tag.")
    print("\n")

    # Section C: (Machines in any kind of failed state)
    print("="*40)
    print("(Machines in any kind of failed state)")
    print("="*40)
    if failed_servers:
        for m in sorted(failed_servers, key=lambda x: x.hostname):
            owner = m.owner.username if m.owner else "Unassigned"
            status_msg = f"Message: {m.status_message}" if m.status_message else ""
            print(f"  - Host: {m.hostname:<25} System ID: {m.system_id:<12} Status: {m.status_name:<20} {status_msg}")
    else:
        print("  No machines found in a failed or broken state.")
    print("\n")


def main():
    """
    Main execution function.
    """
    maas_client = get_maas_client(MAAS_API_URL, MAAS_API_KEY)

    try:
        print("--> Fetching all machines from MaaS... (This might take a moment on large systems)")
        all_machines = maas_client.machines.list()
        print(f"--> Found {len(all_machines)} total machines.")
    except Exception as e:
        print(f"Error fetching machines from MaaS: {e}", file=sys.stderr)
        sys.exit(1)

    generate_report(all_machines)
    print("--> Report generation complete.")


if __name__ == "__main__":
    main()