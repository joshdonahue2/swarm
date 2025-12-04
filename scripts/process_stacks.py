import yaml
import os
import glob
import shutil

# CONFIGURATION
INPUT_FOLDER = "stacks"
OUTPUT_FOLDER = "ready_to_deploy"
TRAEFIK_NETWORK = "traefik-public"

def process_file(filepath):
    filename = os.path.basename(filepath)
    print(f"🔹 Processing: {filename}...")

    with open(filepath, 'r') as f:
        try:
            data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            print(f"❌ Error reading {filename}: {e}")
            return

    # --- MODE CHECK ---
    # If no x-nodel-config, we treat this as a "Raw" file (Power User Mode)
    if 'x-nodel-config' not in data:
        print(f"   ℹ️  No auto-config found. Deploying in 'Raw Mode' (Preserving your custom labels).")
        
        # Just ensure the network exists, then save and exit
        if 'networks' not in data: data['networks'] = {}
        if TRAEFIK_NETWORK not in data['networks']:
            data['networks'][TRAEFIK_NETWORK] = {'external': True}
            
        output_path = os.path.join(OUTPUT_FOLDER, filename)
        with open(output_path, 'w') as f:
            yaml.dump(data, f, sort_keys=False)
        return

    # --- AUTO-GENERATION MODE ---
    # This runs ONLY if x-nodel-config IS present
    print(f"   ✨ Auto-generating labels...")
    config = data.get('x-nodel-config', {})
    
    # We look for the first service to apply labels to
    if 'services' in data and len(data['services']) > 0:
        first_service_name = list(data['services'].keys())[0]
        service = data['services'][first_service_name]

        url = config.get('url')
        port = config.get('port', 80)
        icon = config.get('icon', 'docker.png')
        group = config.get('group', 'My Apps')

        if url:
            if 'deploy' not in service: service['deploy'] = {}
            if 'labels' not in service['deploy']: service['deploy']['labels'] = []
            
            labels = service['deploy']['labels']
            
            # Standard Labels
            new_labels = [
                "traefik.enable=true",
                f"traefik.docker.network={TRAEFIK_NETWORK}",
                f"traefik.http.routers.{first_service_name}.rule=Host(`{url}`)",
                f"traefik.http.routers.{first_service_name}.entrypoints=websecure",
                f"traefik.http.routers.{first_service_name}.tls.certresolver=myresolver",
                f"traefik.http.services.{first_service_name}.loadbalancer.server.port={port}",
                f"homepage.group={group}",
                f"homepage.name={first_service_name.capitalize()}",
                f"homepage.icon={icon}",
                f"homepage.href=https://{url}"
            ]
            
            for l in new_labels:
                if l not in labels: labels.append(l)

            # Add Network
            if 'networks' not in service: service['networks'] = []
            if isinstance(service['networks'], list):
                if TRAEFIK_NETWORK not in service['networks']:
                    service['networks'].append(TRAEFIK_NETWORK)
            elif isinstance(service['networks'], dict):
                 if TRAEFIK_NETWORK not in service['networks']:
                    service['networks'][TRAEFIK_NETWORK] = {}

    # Cleanup Config
    del data['x-nodel-config']

    # Ensure global network exists
    if 'networks' not in data: data['networks'] = {}
    if TRAEFIK_NETWORK not in data['networks']:
        data['networks'][TRAEFIK_NETWORK] = {'external': True}

    # Save
    output_path = os.path.join(OUTPUT_FOLDER, filename)
    with open(output_path, 'w') as f:
        yaml.dump(data, f, sort_keys=False)

def main():
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)

    files = glob.glob(os.path.join(INPUT_FOLDER, "*.yml"))
    for f in files:
        process_file(f)

if __name__ == "__main__":
    main()