import yaml
import os
import glob
import shutil

# CONFIGURATION
INPUT_FOLDER = "stacks"
OUTPUT_FOLDER = "ready_to_deploy"
TRAEFIK_NETWORK = "traefik-public"
BASE_STORAGE_PATH = "/mnt/shared/swarm" # <--- defined your storage root

def process_file(filepath):
    filename = os.path.basename(filepath)
    stack_name = filename.replace('.yml', '') # Get "bambustudio" from "bambustudio.yml"
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
        print(f"   ℹ️  No auto-config found. Deploying in 'Raw Mode'.")
        output_path = os.path.join(OUTPUT_FOLDER, filename)
        with open(output_path, 'w') as f:
            yaml.dump(data, f, sort_keys=False)
        return

    # --- AUTO-GENERATION MODE ---
    print(f"   ✨ Auto-generating labels, volumes, and cleaning ports...")
    config = data.get('x-nodel-config', {})
    
    if 'services' in data and len(data['services']) > 0:
        first_service_name = list(data['services'].keys())[0]
        service = data['services'][first_service_name]

        url = config.get('url')
        port = config.get('port', 80)
        icon = config.get('icon', 'docker.png')
        group = config.get('group', 'My Apps')

        # 1. REMOVE PORTS (Security)
        # We remove ports because Traefik proxies to the container internally.
        if 'ports' in service:
            print(f"   🛡️  Removing exposed ports from {first_service_name} (GitOps standard)")
            del service['ports']

        # 2. STANDARDIZE VOLUMES & CREATE FOLDERS
        if 'volumes' in service:
            new_volumes = []
            for vol in service['volumes']:
                # Vol formats: "host_path:container_path" or just "container_path" (rare)
                parts = vol.split(':')
                
                if len(parts) >= 2:
                    host_part = parts[0]
                    container_part = parts[1]
                    
                    # Logic: If it starts with '/', it's an absolute path (like /etc/localtime). Keep it.
                    # If it doesn't (like 'config'), it's a relative/named volume. Convert it.
                    if host_part.startswith('/'):
                        new_volumes.append(vol)
                    else:
                        # Construct the standardized path
                        # e.g. /mnt/shared/swarm/bambustudio/config
                        full_host_path = os.path.join(BASE_STORAGE_PATH, stack_name, host_part)
                        
                        # CREATE THE DIRECTORY ON THE SERVER
                        try:
                            os.makedirs(full_host_path, exist_ok=True)
                            print(f"   wd  Ensured directory exists: {full_host_path}")
                        except OSError as e:
                            print(f"   ⚠️  Warning: Could not create folder {full_host_path}. Permission issue? {e}")

                        # Add the new string to the list
                        new_volumes.append(f"{full_host_path}:{container_part}")
            
            # Apply the updated list
            service['volumes'] = new_volumes

        # 3. APPLY LABELS (Traefik + Homepage)
        if url:
            if 'deploy' not in service: service['deploy'] = {}
            if 'labels' not in service['deploy']: service['deploy']['labels'] = []
            
            labels = service['deploy']['labels']
            
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
                f"homepage.href=https://{url}",
                f"homepage.siteMonitor=http://{first_service_name}:{port}"
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