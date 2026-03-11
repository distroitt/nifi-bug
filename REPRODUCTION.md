# Reproduction Guide

This guide describes how to reproduce the NiFi Python bridge startup hang using
the synthetic artifacts in this repository.

## Prerequisites

- Linux x86_64
- Docker
- Docker Compose
- Python 3 available on the host to run the helper scripts
- a clean NiFi `flow.json.gz` to use as the generation baseline

## Where the Baseline `flow.json.gz` Comes From

The synthetic `repro-flow.json.gz` is not generated from scratch.

Instead, `scripts/generate_repro_flow.py` takes a clean persisted
`flow.json.gz` created by NiFi itself and adds synthetic process groups and
Python processors on top of it.

This is important because `flow.json.gz` is an internal NiFi format and should
match the exact NiFi version used for reproduction.

For this repository, the baseline file should come from a fresh start of the
official `apache/nifi:2.6.0` image with empty state.

One practical way to obtain it:

```bash
docker compose down -v
docker compose pull
docker compose up -d
```

Wait until NiFi initializes its configuration, then copy the generated
baseline flow out of the container:

```bash
docker cp nifi_python_bridge:/opt/nifi/nifi-current/conf/flow.json.gz \
  dist/base-flow.json.gz
```

That `dist/base-flow.json.gz` file is then used as the `--base-flow` input for
`scripts/generate_repro_flow.py`.

## Build the Synthetic Artifacts

Build the Python extension NAR:

```bash
python3 scripts/build_repro_nar.py \
  --output dist/py4j-repro-python-extensions.nar
```

Generate the persisted flow:

```bash
python3 scripts/generate_repro_flow.py \
  --base-flow dist/base-flow.json.gz \
  --output dist/repro-flow.json.gz
```

If the default load is not enough, increase it:

```bash
python3 scripts/generate_repro_flow.py \
  --base-flow dist/base-flow.json.gz \
  --output dist/repro-flow.json.gz \
  --group-count 6 \
  --instances-per-group 40
```

## Runtime Assumptions

The reproducer uses:

- the official `apache/nifi:2.6.0` image;
- the default Python runtime bundled in that image (`3.11.x`);
- persisted `flow.json.gz` rather than UI import.

The compose file for this repository is:

- `docker-compose.yml`

### Step 1. Recreate the stand

```bash
docker compose down -v
docker compose pull
docker compose create
```

### Step 2. Copy the synthetic persisted flow

```bash
docker cp dist/repro-flow.json.gz \
  nifi_python_bridge:/opt/nifi/nifi-current/conf/flow.json.gz
```

### Step 3. Start NiFi

```bash
docker start nifi_python_bridge
docker logs -f nifi_python_bridge
```

### Step 4. Observe the failing startup

Expected observation on `2.6.0`:

- the initial cold start can hang immediately with the synthetic persisted
  flow.
- the failure may be nondeterministic, so it may not reproduce on the first
  attempt.

If the startup completes successfully on the first try, restart the same
container several times and watch the logs after each start:

```bash
docker restart nifi_python_bridge
docker logs --since 2m nifi_python_bridge
```

The bug is still considered reproduced if one of these restarts stalls before
NiFi reaches full startup. Requiring multiple restart attempts is itself part
of the abnormal behavior.

## Success Criteria

The reproduction is considered successful when the failing start shows all of
the following:

- the container is still alive;
- startup logs stop during Python processor initialization;
- the log does not reach the `Started Server` line;
- there is no `Started Application` line for the failing start;
- repeated restart attempts may alternate between successful and stalled
  startup, which is also considered a reproduction of the bug.

For this reproducer, startup is considered complete once the logs contain the
`Started Server` line.

## Minimal Checks

Check whether the start reached `Started Application`:

```bash
docker logs nifi_python_bridge 2>&1 | grep 'Started Application'
```

Check whether the start reached `Started Server`:

```bash
docker logs nifi_python_bridge 2>&1 | grep 'Started Server'
```

## Optional Diagnostics

```bash
docker exec nifi_python_bridge \
  sh -lc '$JAVA_HOME/bin/jcmd $(pgrep -f org.apache.nifi.NiFi | head -n1) Thread.print'
```

Typical blocking points seen in failing dumps:

- `org.apache.nifi.py4j.client.NiFiPythonGateway.endInvocation(...)`
- `PythonProxyInvocationHandler.invoke(...)`
- `StandardPythonBridge.createProcessor(...)`
- `NiFiPythonGateway.putNewObject(...)`
