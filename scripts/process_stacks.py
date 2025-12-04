import yaml
import os
import glob

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

    # Ensure basics exist
    if 'networks' not in data: data['networks'] = {}
    
    # 1. READ CONFIG (The "Form" Answers)
    # We look for 'x-nodel-config' at the top of the file
    config = data.get('x-nodel-config', {})
    
    # If no config is present, we just save the file as-is and exit
    if not config:
        print(f"   ℹ️  No x-nodel-config found. Deploying as plain compose.")
    else:
        # 2. INJECT LABELS
        # We assume the first service listed is the "Main" one to label
        first_service_name = list(data['services'].keys())[0]
        service = data['services'][first_service_name]

        url = config.get('url')
        port = config.get('port', 80)
        icon = config.get('icon', 'docker.png')
        group = config.get('group', 'My Apps')

        if url:
            print(f"   ✨ Injecting Traefik & Homepage for: {url}")
            
            # Ensure deploy/labels structure
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
                f"homepage.href=https://{url}"
            ]
            
            # Add unique labels
            for l in new_labels:
                if l not in labels: labels.append(l)

            # Ensure Network
            if TRAEFIK_NETWORK not in data['networks']:
                data['networks'][TRAEFIK_NETWORK] = {'external': True}
            
            if 'networks' not in service: service['networks'] = []
            # Handle list vs dict network format
            if isinstance(service['networks'], list):
                if TRAEFIK_NETWORK not in service['networks']:
                    service['networks'].append(TRAEFIK_NETWORK)
            elif isinstance(service['networks'], dict):
                 if TRAEFIK_NETWORK not in service['networks']:
                    service['networks'][TRAEFIK_NETWORK] = {}

    # 3. CLEANUP
    # Remove the x-nodel-config so Docker doesn't complain (though it usually ignores x-)
    if 'x-nodel-config' in data:
        del data['x-nodel-config']

    # 4. SAVE
    output_path = os.path.join(OUTPUT_FOLDER, filename)
    with open(output_path, 'w') as f:
        yaml.dump(data, f, sort_keys=False)

def main():
    # Create output folder
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)

    # Loop through all .yml files in stacks/
    files = glob.glob(os.path.join(INPUT_FOLDER, "*.yml"))
    for f in files:
        process_file(f)

if __name__ == "__main__":
    main()