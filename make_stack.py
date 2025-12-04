import yaml
import sys

# --- CONFIGURATION ---
# The name of the overlay network Traefik uses to talk to containers
TRAEFIK_NETWORK_NAME = "traefik-public" 
# ---------------------

def get_input(prompt, default=None):
    text = f"{prompt} [{default}]: " if default else f"{prompt}: "
    val = input(text)
    return val if val else default

def main():
    print("\n--- 🐳 Swarm Auto-Labeler ---")
    
    # 1. Load the "Lazy" File
    input_file = "docker-compose.yml"
    try:
        with open(input_file, 'r') as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"❌ Error: Could not find {input_file}")
        return

    # 2. Ensure Network Exists
    if 'networks' not in data:
        data['networks'] = {}
    
    # Add external Traefik network if missing
    if TRAEFIK_NETWORK_NAME not in data['networks']:
        data['networks'][TRAEFIK_NETWORK_NAME] = {'external': True}

    # 3. Loop through Services
    if 'services' in data:
        for service_name, config in data['services'].items():
            print(f"\n🔹 Configuring Service: {service_name}")
            modify = get_input("   Add Traefik/Homepage labels?", "y")
            
            if modify.lower() == 'y':
                # Ask Questions
                url = get_input(f"   URL (e.g. {service_name}.example.com)")
                port = get_input("   Container Port", "80")
                group = get_input("   Homepage Group", "Applications")
                icon = get_input("   Homepage Icon (e.g. docker.png)")
                
                # Create Deploy/Labels structure if missing
                if 'deploy' not in config: config['deploy'] = {}
                if 'labels' not in config['deploy']: config['deploy']['labels'] = []
                
                # Define Labels
                new_labels = [
                    # Traefik
                    "traefik.enable=true",
                    f"traefik.http.routers.{service_name}.rule=Host(`{url}`)",
                    f"traefik.http.routers.{service_name}.entrypoints=websecure",
                    f"traefik.http.routers.{service_name}.tls.certresolver=myresolver", # Change 'myresolver' to your actual resolver name in Traefik
                    f"traefik.http.services.{service_name}.loadbalancer.server.port={port}",
                    f"traefik.docker.network={TRAEFIK_NETWORK_NAME}",
                    
                    # Homepage
                    f"homepage.group={group}",
                    f"homepage.name={service_name.capitalize()}",
                    f"homepage.icon={icon}",
                    f"homepage.href=https://{url}"
                ]
                
                # Append Labels
                # We use a set logic to avoid duplicates if you run this twice
                existing_labels = config['deploy']['labels']
                for label in new_labels:
                    # Simple check to avoid exact duplicates
                    if label not in existing_labels:
                        existing_labels.append(label)

                # Add Network to Service
                if 'networks' not in config: config['networks'] = []
                # Handle if networks is a list or dict
                if isinstance(config['networks'], list):
                    if TRAEFIK_NETWORK_NAME not in config['networks']:
                        config['networks'].append(TRAEFIK_NETWORK_NAME)
                elif isinstance(config['networks'], dict):
                     if TRAEFIK_NETWORK_NAME not in config['networks']:
                        config['networks'][TRAEFIK_NETWORK_NAME] = {}

    # 4. Save the "Production" File
    output_file = "docker-compose.prod.yml"
    with open(output_file, 'w') as f:
        yaml.dump(data, f, sort_keys=False)
    
    print(f"\n✅ Success! Generated {output_file}")
    print(f"👉 Now commit {output_file} to GitHub to deploy.")

if __name__ == "__main__":
    main()