"""Local per-game contexts, separate from the original four profile slots."""
import copy
from dataclasses import asdict
import json
import logging
from pathlib import Path
import os
import tempfile
import uuid

from core.config import PROFILE_KEYS, validated_config

log = logging.getLogger(__name__)
CONTEXT_KEYS = (*PROFILE_KEYS, "profiles", "active_profile", "target_window_title",
                "only_target_window", "game_assistant_notes")


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                         suffix=".tmp", delete=False) as stream:
            temporary = stream.name
            json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def context_values(config):
    data = asdict(config)
    return {key: data[key] for key in CONTEXT_KEYS}


def clean_context(data):
    if not isinstance(data, dict):
        raise ValueError("方案参数必须是对象")
    return context_values(validated_config({**data, "config_version": 4}))


class PresetLibrary:
    def __init__(self, manager):
        self.manager = manager
        self.path = Path(manager.config_dir) / "game-presets.json"
        self.entries = {}
        self.active_id = ""
        self.base = None
        self.error = ""
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                if not isinstance(data, dict) or data.get("version") != 1:
                    raise ValueError("不支持的游戏方案库格式")
                for entry in data.get("entries", [])[:100]:
                    if not isinstance(entry, dict) or not isinstance(entry.get("id"), str):
                        continue
                    ident = entry["id"][:80]
                    self.entries[ident] = {"id": ident, "name": str(entry.get("name", "游戏方案"))[:80],
                                           "match_title": str(entry.get("match_title", ""))[:512],
                                           "context": clean_context(entry.get("context", {}))}
                self.active_id = data.get("active_id", "")
                if self.active_id not in self.entries:
                    self.active_id = ""
                if isinstance(data.get("base"), dict):
                    self.base = clean_context(data["base"])
            except (OSError, ValueError, TypeError, AttributeError):
                log.exception("Cannot load game preset library; original file retained")
                self.error = "游戏方案库读取失败，原文件已保留"
                self.entries, self.active_id, self.base = {}, "", None
        manager._save_hooks.append(self.persist_current)
        manager._reset_hooks.append(self.prepare_reset)

    def snapshot(self):
        self.manager.remember_current_profile()
        return context_values(self.manager.config)

    def _write(self):
        if self.error:
            return False  # Do not overwrite an unreadable user library.
        try:
            atomic_json(self.path, dict(version=1, active_id=self.active_id,
                                       base=self.base, entries=list(self.entries.values())))
            return True
        except (OSError, ValueError):
            log.exception("Cannot save game preset library")
            return False

    def persist_current(self):
        if self.error:
            return not self.manager.config.game_library_enabled
        if self.active_id in self.entries:
            self.entries[self.active_id]["context"] = self.snapshot()
        elif self.base is not None:
            self.base = self.snapshot()
        else:
            return not bool(self.error)
        return self._write()

    def prepare_reset(self):
        if self.active_id and not self.persist_current():
            return False
        previous = (self.active_id, self.base)
        self.active_id, self.base = "", None
        saved = self._write() if self.path.exists() and not self.error else True
        if not saved:
            self.active_id, self.base = previous
        return saved

    def _apply(self, context):
        for key, value in clean_context(context).items():
            setattr(self.manager.config, key, copy.deepcopy(value))

    def create(self, name, match_title=""):
        name = name.strip()[:80]
        if not name:
            raise ValueError("请填写游戏方案名称")
        if len(self.entries) >= 100:
            raise ValueError("游戏方案最多支持 100 个")
        ident = uuid.uuid4().hex
        entry = dict(id=ident, name=name, match_title=match_title.strip()[:512], context=self.snapshot())
        if entry["match_title"] and entry["context"]["only_target_window"]:
            entry["context"]["target_window_title"] = entry["match_title"]
        self.entries[ident] = entry
        if not self._write():
            del self.entries[ident]
            raise OSError("游戏方案未保存，请检查目录权限")
        return ident

    def activate(self, ident):
        if not self.manager.config.game_library_enabled:
            raise ValueError("请先启用游戏方案库")
        if ident not in self.entries:
            raise ValueError("找不到游戏方案")
        if ident == self.active_id:
            return self.manager.save()
        if not self.manager.save():
            return False
        if not self.active_id:
            self.base = self.snapshot()
        before, previous = self.snapshot(), self.active_id
        self._apply(self.entries[ident]["context"])
        self.active_id = ident
        if not self.manager.save():
            self._apply(before)
            self.active_id = previous
            self.manager.save()
            return False
        self.manager.notify_listeners()
        return True

    def deactivate(self):
        if not self.active_id:
            return True
        if not self.persist_current():
            return False
        before, previous = self.snapshot(), self.active_id
        if self.base is not None:
            self._apply(self.base)
        self.active_id = ""
        if not self.manager.save():
            self._apply(before)
            self.active_id = previous
            self.manager.save()
            return False
        self.manager.notify_listeners()
        return True

    def delete(self, ident):
        if ident == self.active_id and not self.deactivate():
            return False
        entry = self.entries.pop(ident, None)
        if not self._write():
            if entry:
                self.entries[ident] = entry
            return False
        return True

    def match(self, title):
        title = title.casefold()
        # Ambiguous matches stay manual instead of loading an arbitrary context.
        matches = [key for key, item in self.entries.items()
                   if item["match_title"] and item["match_title"].casefold() in title]
        return matches[0] if len(matches) == 1 else None

    def update_match(self, ident, title):
        entry = self.entries[ident]
        before = copy.deepcopy(entry)
        title = title.strip()[:512]
        entry["match_title"] = title
        if title and entry["context"]["only_target_window"]:
            entry["context"]["target_window_title"] = title
        if not self._write():
            self.entries[ident] = before
            return False
        if ident == self.active_id and title and self.manager.config.only_target_window:
            self.manager.config.target_window_title = title
            saved = self.manager.save()
            self.manager.notify_listeners()
            return saved
        return True

    def export_preset(self, ident, path):
        if ident == self.active_id:
            self.persist_current()
        entry = self.entries[ident]
        context = copy.deepcopy(entry["context"])
        # Portable exports omit local window titles and personal notes.
        context.update(target_window_title="", only_target_window=False, game_assistant_notes="")
        atomic_json(path, dict(format="Care3D-preset", version=1, name=entry["name"], settings=context))

    def import_preset(self, path):
        if len(self.entries) >= 100:
            raise ValueError("游戏方案最多支持 100 个")
        path = Path(path)
        if path.stat().st_size > 1_000_000:
            raise ValueError("方案文件过大")
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("format") != "Care3D-preset" or data.get("version") != 1:
            raise ValueError("这不是受支持的 Care3D 方案文件")
        context = clean_context(data.get("settings"))
        name = data.get("name", "导入方案")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("方案名称无效")
        ident = uuid.uuid4().hex
        self.entries[ident] = dict(id=ident, name=name.strip()[:80], match_title="", context=context)
        if not self._write():
            del self.entries[ident]
            raise OSError("无法保存导入的方案")
        return ident
