import docker
import argparse
import shutil
import signal
import sys
import json

label_name = "hoster.domains"
start_pattern = "#-----------Docker-Hoster-Domains----------\n"
end_pattern = "#-----Do-not-add-hosts-after-this-line-----\n"
hosts_path = "/tmp/hosts"
hosts = {}

dockerClient = docker.DockerClient(base_url="unix:///var/run/docker.sock")


def signal_handler(sig, frame):
    global hosts
    hosts = {}
    update_hosts_file()
    sys.exit(0)


def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    args = parse_args()
    global hosts_path
    hosts_path = args.file

    global dockerClient
    dockerClient = docker.DockerClient(base_url=f"unix://{args.socket}")

    # load running containers
    for c in dockerClient.containers.list():
        hosts[c.id] = extract_container_info(c)

    update_hosts_file()

    print("Listening for Docker events...")

    # listen for container events
    for raw in dockerClient.events(decode=False):
        try:
            event = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue

        if event.get("Type") != "container":
            continue

        action = event.get("Action")
        container_id = event.get("id")

        if action == "start":
            c = get_container(container_id)
            if c:
                hosts[container_id] = extract_container_info(c)
                update_hosts_file()

        elif action in ("stop", "die", "destroy"):
            if container_id in hosts:
                hosts.pop(container_id)
                update_hosts_file()

        elif action == "rename":
            c = get_container(container_id)
            if c:
                hosts[container_id] = extract_container_info(c)
                update_hosts_file()


def get_container(container_id):
    try:
        return dockerClient.containers.get(container_id)
    except docker.errors.NotFound:
        return None


def extract_container_info(container):
    info = container.attrs

    name = info["Name"].strip("/")
    hostname = info["Config"]["Hostname"]
    domain = info["Config"]["Domainname"]

    if domain:
        hostname = f"{hostname}.{domain}"

    result = []

    networks = info["NetworkSettings"]["Networks"]
    for net_name, net in networks.items():
        ip = net.get("IPAddress")
        if not ip:
            continue

        aliases = net.get("Aliases") or []
        domains = set(aliases + [name, hostname])

        result.append({
            "ip": ip,
            "name": name,
            "domains": domains
        })

    # fallback IP
    default_ip = info["NetworkSettings"].get("IPAddress")
    if default_ip:
        result.append({
            "ip": default_ip,
            "name": name,
            "domains": set([name, hostname])
        })

    # add extra domains from label if present
    labels = info["Config"]["Labels"]
    extra_domains = []
    if label_name in labels:
        extra = labels[label_name]
        extra_domains = [d.strip() for d in extra.split(",") if d.strip()]

    for res in result:
        res["domains"].update(extra_domains)

    return result


def update_hosts_file():
    if len(hosts) == 0:
        print("Clearing hosts file...")
    else:
        print("Updating hosts file with:")

    for id, addresses in hosts.items():
        for addr in addresses:
            print(f"ip: {addr['ip']} domains: {addr['domains']}")

    # read existing hosts
    try:
        with open(hosts_path, "r") as f:
            lines = f.readlines()
    except FileNotFoundError:
        lines = []

    # remove existing section(s) properly
    clean_lines = []
    i = 0
    while i < len(lines):
        if lines[i] == start_pattern:
            # skip until after end_pattern
            while i < len(lines) and lines[i] != end_pattern:
                i += 1
            if i < len(lines) and lines[i] == end_pattern:
                i += 1  # skip the end_pattern
        else:
            clean_lines.append(lines[i])
            i += 1

    lines = clean_lines

    # trim trailing empty lines
    while lines and not lines[-1].strip():
        lines.pop()

    # add new entries
    if hosts:
        lines.append("\n")  # single empty line before section
        lines.append(start_pattern)
        for id, addrs in hosts.items():
            for addr in addrs:
                domains_str = " ".join(sorted(addr["domains"]))
                lines.append(f"{addr['ip']}\t{domains_str}\n")
        lines.append(end_pattern)

    aux = hosts_path + ".aux"
    with open(aux, "w") as f:
        f.writelines(lines)

    shutil.move(aux, hosts_path)


def parse_args():
    parser = argparse.ArgumentParser(description='Synchronize running docker container IPs with host /etc/hosts file.')
    parser.add_argument('socket', type=str, nargs="?", default="tmp/docker.sock", help='The docker socket to listen for docker events.')
    parser.add_argument('file', type=str, nargs="?", default="/tmp/hosts", help='The /etc/hosts file to sync the containers with.')
    return parser.parse_args()


if __name__ == "__main__":
    main()