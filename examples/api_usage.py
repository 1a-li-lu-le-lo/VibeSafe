#!/usr/bin/env python3
"""
Example of using VibeSafe programmatic API

This demonstrates how to use VibeSafe in scripts and automation
without any interactive prompts or stdout output.
"""

from vibesafe import create_api_client, VibeSafeError
import sys


def main():
    # Create a non-interactive API client
    print("Creating VibeSafe API client...")
    vs = create_api_client()

    # Check system status
    status = vs.get_status_info()
    print(f"VibeSafe initialized: {status['initialized']}")
    print(f"Number of secrets: {status['secret_count']}")
    print(f"Passkey enabled: {status['passkey_enabled']}")

    # Example 1: Store and retrieve a secret
    print("\n--- Example 1: Basic Operations ---")
    test_key = "EXAMPLE_API_KEY"
    test_value = "sk-example123abc"

    try:
        # Store a secret
        vs.store_secret(test_key, test_value, overwrite=True)
        print(f"✅ Stored secret '{test_key}'")

        # Check if it exists
        if vs.secret_exists(test_key):
            print(f"✅ Confirmed '{test_key}' exists")

        # Retrieve the secret
        retrieved = vs.fetch_secret(test_key)
        # Never print the actual secret! Just verify it worked
        print(f"✅ Successfully retrieved '{test_key}' (value hidden)")

        # List all secrets
        all_secrets = vs.list_secret_names()
        print(f"✅ Total secrets stored: {len(all_secrets)}")

    except VibeSafeError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

    # Example 2: Error handling
    print("\n--- Example 2: Error Handling ---")
    try:
        # Try to get a non-existent secret
        vs.fetch_secret("DOES_NOT_EXIST")
    except VibeSafeError as e:
        print(f"✅ Correctly caught error for missing secret: {e}")

    # Example 3: Using secrets in practice (with mock function)
    print("\n--- Example 3: Practical Usage ---")
    try:
        # This is how you'd use it in real code
        api_key = vs.fetch_secret(test_key)

        # Simulate using the API key (never actually print it!)
        def call_api(key):
            # In real code, you'd make an API call here
            return "API call successful" if key else "Failed"

        result = call_api(api_key)
        print(f"✅ {result}")

    except VibeSafeError as e:
        print(f"❌ Failed to retrieve secret: {e}")

    # Cleanup
    print("\n--- Cleanup ---")
    try:
        vs.remove_secret(test_key)
        print(f"✅ Removed test secret '{test_key}'")
    except VibeSafeError as e:
        print(f"⚠️  Could not remove secret: {e}")

    print("\n✨ API demonstration complete!")


if __name__ == "__main__":
    main()