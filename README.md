# Docker Hoster

A lightweight tool for dynamically injecting DNS entries into the host's `/etc/hosts` file to resolve names of local Docker containers.

Docker Hoster runs as a Docker container itself, monitoring Docker events to automatically add or remove host entries for running containers. This enables seamless name resolution without manual configuration.

## Quick Start

Run Docker Hoster with the following command:

```bash
docker run -d \
    --name docker-hoster \
    -v /var/run/docker.sock:/tmp/docker.sock \
    -v /etc/hosts:/tmp/hosts \
    ghcr.io/mrmohebi/docker-hoster:latest
```

- The `/var/run/docker.sock` volume allows Hoster to access Docker events and container metadata.
- The `/etc/hosts` volume (mounted to `/tmp/hosts` inside the container) enables Hoster to update the host's DNS resolution file.

Hoster will insert one entry per container IP, updating the file in real-time as containers start, stop, or are renamed.

## How It Works

- **Event Listening**: Hoster connects to the Docker daemon via the socket and listens for container events (e.g., start, stop, die, destroy, rename).
- **Hosts File Management**: Entries are added in a dedicated section of `/etc/hosts` (marked by `#-----------Docker-Hoster-Domains----------` and `#-----Do-not-add-hosts-after-this-line-----`). This section is safely updated or cleared without affecting other content.
- **Supported Docker Versions**: Compatible with recent Docker releases (tested up to Docker 29).
- **Built With**: Python 3.14 and the Docker SDK.

## Container Registration

By default, Hoster registers the following domains for each container:
- Container name (e.g., `--name mycontainer`)
- Hostname (e.g., `--hostname myhostname` or with domain if specified)
- Container ID (shortened)
- Network aliases (e.g., `--network-alias myserver.com`)

For example, running:

```bash
docker run -d \
    --name mycontainer \
    --hostname myhostname \
    --network somenetwork --network-alias "myserver.com" \
    alpine
```

Would make the container resolvable as `mycontainer`, `myhostname`, its ID (e.g., `abc123def456`), and `myserver.com`.

### Custom Domains via Labels
Add extra domains using the `hoster.domains` label with comma-separated values:

```bash
docker run -d \
    --name mycontainer \
    -l hoster.domains="example.com,api.example.com" \
    alpine
```

These will be appended to all default domains for broader resolution.


## Contributions
Contributions are welcome! Feel free to submit issues or pull requests on the [GitHub repository](https://github.com/MrMohebi/docker-hoster). The project includes GitHub Actions for automated image builds and publishing to GHCR on releases.