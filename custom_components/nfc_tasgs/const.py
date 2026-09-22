"""Constants for NFC Tasgs integration."""

DOMAIN = "nfc_tasgs"

CONF_TAG_ID = "tag_id"
CONF_DEFAULT_ACTION = "default_action_key"
CONF_ACTIONS = "actions"
CONF_OWNERS = "owners"
CONF_ASSIGNEE = "assignee"
CONF_DOUBLE_SCAN_WINDOW = "double_scan_window_seconds"
CONF_TASK_LIST = "task_list"
CONF_SHOPPING_LIST = "shopping_list"
CONF_ICON = "icon"
CONF_AREA_ID = "area_id"

CONF_ACTION_KEY = "key"
CONF_ACTION_LABEL = "label"
CONF_ACTION_INTERVAL = "expected_interval_hours"
CONF_ACTION_PURCHASE = "triggers_purchase"
CONF_ACTION_TASK = "triggers_task"

ATTR_DEVICE_ID = "device_id"
ATTR_DEVICE_NAME = "device_name"
ATTR_ACTION_KEY = "action_key"
ATTR_ACTION_LABEL = "action_label"
ATTR_SCANNER = "scanner"
ATTR_SCANNER_DEVICE_ID = "scanner_device_id"
ATTR_TIMESTAMP = "timestamp"
ATTR_MODE = "mode"
ATTR_SCAN_COUNT = "scan_count"
ATTR_ACTION_SCAN_COUNT = "action_scan_count"
ATTR_INTERVAL_HOURS = "interval_hours"

EVENT_ACTION = f"{DOMAIN}_action"

SERVICE_SCAN = "scan"
SERVICE_LOG = "log"
SERVICE_RESET_ACTION = "reset_action"
SERVICE_SET_ASSIGNEE = "set_assignee"

PLATFORMS = ["sensor", "binary_sensor", "button"]

DEFAULT_DOUBLE_SCAN_WINDOW = 3

STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.history"

ACTION_SENSORS = [
    "last_scan",
    "interval_hours",
    "next_due",
    "last_scanner",
    "total_scans",
]
DEVICE_SENSORS = [
    "total_scans",
    "last_scan",
    "last_action",
    "last_scanner",
]
