from __future__ import annotations

import json
import os
import tempfile
import threading
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class HardwareFileSystem:
    """Materialize hardware identity, state, telemetry and intents as JSON files."""

    def __init__(self, profile_root: Path, runtime_root: Path) -> None:
        self.profile_root = profile_root
        self.runtime_root = runtime_root
        self.devices_root = runtime_root / "devices"
        self.intents_root = runtime_root / "intents"
        self.events_path = runtime_root / "events.jsonl"
        self._lock = threading.RLock()
        self.profiles = self._load_profiles()
        self.state: dict[str, dict[str, Any]] = {}
        self.materialize()

    def _load_profiles(self) -> dict[str, dict[str, Any]]:
        profiles: dict[str, dict[str, Any]] = {}
        for path in sorted(self.profile_root.glob("*.json")):
            profile = json.loads(path.read_text(encoding="utf-8"))
            profiles[str(profile["device_id"])] = profile
        return profiles

    def _atomic_write(self, path: Path, value: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
        fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def _append_event(self, event: dict[str, Any]) -> None:
        self.runtime_root.mkdir(parents=True, exist_ok=True)
        with self.events_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")

    def materialize(self) -> None:
        with self._lock:
            self.runtime_root.mkdir(parents=True, exist_ok=True)
            self.intents_root.mkdir(parents=True, exist_ok=True)
            inventory = {"schema": 1, "updated_at": utc_now(), "devices": []}
            for device_id, profile in self.profiles.items():
                root = self.devices_root / device_id
                default_state = {
                    "device_id": device_id,
                    "online": False,
                    "connection": "unplugged or not probed",
                    "updated_at": utc_now(),
                    "cpu": {"load_percent": None, "clock_mhz": profile["cpu"].get("configured_mhz")},
                    "telemetry": {},
                    "controls": {},
                    "tasks": [dict(context, state="offline", load_percent=None) for context in profile.get("execution_contexts", [])],
                }
                self.state.setdefault(device_id, default_state)
                self._atomic_write(root / "identity.json", {key: value for key, value in profile.items() if key not in ("pins", "memory", "execution_contexts", "peripherals")})
                self._atomic_write(root / "pins.json", {"device_id": device_id, "pins": profile.get("pins", [])})
                self._atomic_write(root / "storage.json", {"device_id": device_id, "resources": profile.get("memory", [])})
                self._atomic_write(root / "tasks.json", {"device_id": device_id, "contexts": self.state[device_id]["tasks"]})
                self._atomic_write(root / "peripherals.json", {"device_id": device_id, "peripherals": profile.get("peripherals", [])})
                self._atomic_write(root / "state.json", self.state[device_id])
                self._atomic_write(root / "telemetry.json", {"device_id": device_id, "updated_at": None, "values": {}})
                self._atomic_write(root / "controls" / "desired.json", {"device_id": device_id, "updated_at": None, "values": {}})
                self._atomic_write(root / "controls" / "actual.json", {"device_id": device_id, "updated_at": None, "values": {}})
                inventory["devices"].append({"device_id": device_id, "name": profile["name"], "path": f"devices/{device_id}"})
            self._atomic_write(self.runtime_root / "inventory.json", inventory)

    def update_connectivity(self, discovered: dict[str, Any]) -> None:
        with self._lock:
            for device_id in self.profiles:
                incoming = discovered.get(device_id, {})
                state = self.state[device_id]
                state["online"] = bool(incoming.get("online", False))
                state["connection"] = str(incoming.get("detail", "Not detected"))
                state["updated_at"] = utc_now()
                for task in state["tasks"]:
                    task["state"] = "available" if state["online"] else "offline"
                self._atomic_write(self.devices_root / device_id / "state.json", state)
                self._atomic_write(self.devices_root / device_id / "tasks.json", {"device_id": device_id, "contexts": state["tasks"]})
            self._append_event({"time": utc_now(), "type": "connectivity", "devices": {key: value.get("online", False) for key, value in discovered.items() if key in self.profiles}})

    def update_h7_snapshot(self, snapshot: dict[str, Any]) -> None:
        with self._lock:
            state = self.state["h7"]
            state["online"] = True
            state["connection"] = "live ST-Link RAM snapshot"
            state["updated_at"] = utc_now()
            state["telemetry"] = deepcopy(snapshot)
            state["controls"] = deepcopy(snapshot.get("pwm", {}))
            for task in state["tasks"]:
                task["state"] = "running"
            root = self.devices_root / "h7"
            self._atomic_write(root / "state.json", state)
            self._atomic_write(root / "tasks.json", {"device_id": "h7", "contexts": state["tasks"]})
            self._atomic_write(root / "telemetry.json", {"device_id": "h7", "updated_at": utc_now(), "values": snapshot})
            self._atomic_write(root / "controls" / "actual.json", {"device_id": "h7", "updated_at": utc_now(), "values": snapshot.get("pwm", {})})
            self._append_event({"time": utc_now(), "type": "telemetry", "device_id": "h7", "seq": snapshot.get("seq")})

    def create_intent(self, device_id: str, action: str, parameters: dict[str, Any]) -> str:
        with self._lock:
            intent_id = f"{datetime.now().strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:8]}"
            intent = {
                "schema": 1,
                "intent_id": intent_id,
                "device_id": device_id,
                "action": action,
                "parameters": parameters,
                "status": "pending",
                "created_at": utc_now(),
                "updated_at": utc_now(),
            }
            self._atomic_write(self.intents_root / f"{intent_id}.json", intent)
            self._atomic_write(self.devices_root / device_id / "controls" / "desired.json", {"device_id": device_id, "updated_at": utc_now(), "values": {"action": action, **parameters}})
            self._append_event({"time": utc_now(), "type": "intent", "intent_id": intent_id, "device_id": device_id, "action": action})
            return intent_id

    def finish_intent(self, intent_id: str, status: str, result: Any = None) -> None:
        with self._lock:
            path = self.intents_root / f"{intent_id}.json"
            if not path.exists():
                return
            intent = json.loads(path.read_text(encoding="utf-8"))
            intent["status"] = status
            intent["updated_at"] = utc_now()
            intent["result"] = result
            self._atomic_write(path, intent)
            self._append_event({"time": utc_now(), "type": "intent_status", "intent_id": intent_id, "status": status})

    def model(self) -> dict[str, Any]:
        with self._lock:
            devices = {}
            for device_id, profile in self.profiles.items():
                devices[device_id] = {"profile": deepcopy(profile), "state": deepcopy(self.state[device_id])}
            return {"runtime_root": str(self.runtime_root), "updated_at": utc_now(), "devices": devices}
