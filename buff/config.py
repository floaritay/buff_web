"""BUFF 事件配置"""

from dataclasses import dataclass


@dataclass
class CharmEvent:
    """挂件事件配置"""
    name: str
    category: str
    default_max_pages: int
    tried_items_file: str


CHARM_EVENTS = {
    "austin": CharmEvent(
        name="austin",
        category="csgo_tool_keychain_austin_2025",
        default_max_pages=18,
        tried_items_file="charm_tried_items.json",
    ),
    "budapest": CharmEvent(
        name="budapest",
        category="csgo_tool_keychain_budapest_2025",
        default_max_pages=15,
        tried_items_file="charm_tried_items_budapest.json",
    ),
}
