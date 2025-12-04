import yaml
import sys

# --- STANDARDS ---
DOMAIN_ROOT = "donahuenet.xyz"
TZ = "America/Indiana/Indianapolis"
PUID = "1000"
PGID = "1000"
NETWORK = "traefik-public"
VOL_LOCALTIME = "/etc/localtime:/etc/localtime:ro"
VOL_DATA = "/mnt/data:/data"
VOL_CONFIG_BASE = "/mnt/shared/swarm"

def transform_service(name, source_config):
    # --- CHECK: IS THIS ALREADY STANDARDIZED? ---
    # If the user already defined deploy labels, trust the user and return as-is.
    if 'deploy' in source_config and 'labels' in source_config['deploy']:
        print(f"  [INFO] Service '{name}' appears pre-formatted. Skipping standardization.")
        return source_config

    # --- STANDARDIZATION LOGIC (For generic services) ---
    print(f"  [INFO] Standardizing generic service '{name}'...")
    
    image = source_config.get('image', 'unknown')
    
    # Port Logic: Grab the first port defined
    ports = source_config.get('ports', [])
    main_port = "80"
    if ports:
        p = str(ports[0])
        main_port = p.split(":")[0] if ":" in p else p
            
    # Preserve specific flags
    extras = {k: source_config[k] for k in ['shm_size', 'cap_add', 'command'] if k in source_config}

    service_slug = name.lower().replace(" ", "")
    router_name = service_slug[:10]
    
    new_service = {
        'image': image,
        'environment': {
            'PGID': PGID,
            'PUID': PUID,
            'TZ': TZ
        },
        'ports': [f"{main_port}:{main_port}"],
        'volumes': [
            VOL_LOCALTIME,
            f"{VOL_CONFIG_BASE}/{service_slug}:/config",
            VOL_DATA
        ],
        'networks': [NETWORK],
        'logging': {'driver': 'json-file'},
        'deploy': {
            'restart_policy': {'condition': 'on-failure'},
            'labels': {
                'homepage.group': 'Download',
                'homepage.name': name.capitalize(),
                'homepage.icon': f"{service_slug}.png",
                'homepage.href': f"https://{service_slug}.{DOMAIN_ROOT}",
                'homepage.description': f"{name.capitalize()} Service",
                'homepage.siteMonitor': f"http://{service_slug}:{main_port}",
                'homepage.widget.type': service_slug,
                'homepage.widget.url': f"http://{service_slug}:{main_port}",
                'traefik.enable': 'true',
                f'traefik.http.routers.{router_name}.entrypoints': 'websecure',
                f'traefik.http.routers.{router_name}.rule': f"Host(`{service_slug}.{DOMAIN_ROOT}`)",
                f'traefik.http.routers.{router_name}.tls': 'true',
                f'traefik.http.routers.{router_name}.service': f"{router_name}-svc",
                f'traefik.http.services.{router_name}-svc.loadbalancer.server.port': main_port,
                f'traefik.http.routers.{router_name}.middlewares': f"{router_name}-ratelimit,{router_name}-inflight",
                f'traefik.http.middlewares.{router_name}-ratelimit.ratelimit.average': '100',
                f'traefik.http.middlewares.{router_name}-ratelimit.ratelimit.burst': '50',
                f'traefik.http.middlewares.{router_name}-inflight.inflightreq.amount': '50'
            }
        }
    }
    new_service.update(extras)
    return new_service

def process_file(filepath):
    with open(filepath, 'r') as f:
        data = yaml.safe_load(f)

    if not data or 'services' not in data:
        return

    new_services = {}
    for svc_name, svc_config in data['services'].items():
        new_services[svc_name] = transform_service(svc_name, svc_config)

    final_compose = {
        'version': '3.3',
        'services': new_services,
        'networks': {NETWORK: {'external': True}}
    }

    print(yaml.dump(final_compose, sort_keys=False))

if __name__ == "__main__":
    process_file(sys.argv[1])