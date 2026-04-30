"""High-level router API helpers — discovered via real $post hooking."""
from __future__ import annotations
import json
from typing import Any
from api_client import RouterClient


# ═══════════════════════════════════════════════════════════════════════════
#                       Quick header (no-encrypt $get)
# ═══════════════════════════════════════════════════════════════════════════
def get_header(client: RouterClient) -> dict:
    js = """(async()=>{ try{ return JSON.stringify(await $get('get_header_info'));
            }catch(e){ return '{}'; } })()"""
    raw = client._eval(js, timeout=8)
    try:
        return json.loads(raw) if isinstance(raw, str) else {}
    except Exception:
        return {}


# ═══════════════════════════════════════════════════════════════════════════
#                       Radio + Cell + Neighbors
# ═══════════════════════════════════════════════════════════════════════════
RADIO_FIELDS = {
    "WorkMode":   "X_FH_MobileNetwork.RadioSignalParameter.WorkMode",
    # LTE 4G
    "RSRP":       "X_FH_MobileNetwork.RadioSignalParameter.RSRP",
    "RSRQ":       "X_FH_MobileNetwork.RadioSignalParameter.RSRQ",
    "RSSI":       "X_FH_MobileNetwork.RadioSignalParameter.RSSI",
    "SINR":       "X_FH_MobileNetwork.RadioSignalParameter.SINR",
    "PCI":        "X_FH_MobileNetwork.RadioSignalParameter.PCI",
    "BAND":       "X_FH_MobileNetwork.RadioSignalParameter.BAND",
    "LTE_Power":  "X_FH_MobileNetwork.RadioSignalParameter.LTE_Power",
    "LTE_CQI":    "X_FH_MobileNetwork.RadioSignalParameter.LTE_CQI",
    "QCI":        "X_FH_MobileNetwork.RadioSignalParameter.QCI",
    "ECGI":       "X_FH_MobileNetwork.RadioSignalParameter.ECGI",
    # 5G NR
    "SSB_RSRP":   "X_FH_MobileNetwork.RadioSignalParameter.SSB_RSRP",
    "SSB_RSRQ":   "X_FH_MobileNetwork.RadioSignalParameter.SSB_RSRQ",
    "SSB_RSSI":   "X_FH_MobileNetwork.RadioSignalParameter.SSB_RSSI",
    "SSB_SINR":   "X_FH_MobileNetwork.RadioSignalParameter.SSB_SINR",
    "NR_BAND":    "X_FH_MobileNetwork.RadioSignalParameter.NR_Band",
    "NR_Power":   "X_FH_MobileNetwork.RadioSignalParameter.NR_Power",
    "NR_CQI":     "X_FH_MobileNetwork.RadioSignalParameter.NR_CQI",
    "NR_QCI":     "X_FH_MobileNetwork.RadioSignalParameter.NR_QCI",
    "NR_PCI":     "X_FH_MobileNetwork.RadioSignalParameter.NR_PCI",
    "NCGI":       "X_FH_MobileNetwork.RadioSignalParameter.NCGI",
    # Common
    "TAC":        "X_FH_MobileNetwork.RadioSignalParameter.TAC",
    "PLMN":       "X_FH_MobileNetwork.RadioSignalParameter.PLMN",
    "DL_AMBR":    "X_FH_MobileNetwork.RadioSignalParameter.DL_AMBR",
    "UL_AMBR":    "X_FH_MobileNetwork.RadioSignalParameter.UL_AMBR",
    "EARFCN_NBR": "X_FH_MobileNetwork.RadioSignalParameter.EARFCN_NBR",
    "RSRP_NBR":   "X_FH_MobileNetwork.RadioSignalParameter.RSRP_NBR",
    "PCI_NBR":    "X_FH_MobileNetwork.RadioSignalParameter.PCI_NBR",
    "BAND_NBR":   "X_FH_MobileNetwork.RadioSignalParameter.BAND_NBR",
    "SINR_NBR":   "X_FH_MobileNetwork.RadioSignalParameter.SINR_NBR",
}


def get_radio(client: RouterClient) -> dict:
    return client._post_api("get_value_by_xmlnode", RADIO_FIELDS, timeout=10) or {}


def parse_neighbors(radio: dict) -> list[dict]:
    def _split(s):
        return [x.strip() for x in (s or "").split(",") if x.strip()]
    earfcns = _split(radio.get("EARFCN_NBR"))
    rsrps   = _split(radio.get("RSRP_NBR"))
    pcis    = _split(radio.get("PCI_NBR"))
    bands   = _split(radio.get("BAND_NBR"))
    sinrs   = _split(radio.get("SINR_NBR"))
    n = max(len(earfcns), len(rsrps), len(pcis), len(bands), len(sinrs))
    rows = []
    for i in range(n):
        rows.append({
            "earfcn": earfcns[i] if i < len(earfcns) else "",
            "rsrp":   rsrps[i]   if i < len(rsrps)   else "",
            "pci":    pcis[i]    if i < len(pcis)    else "",
            "band":   bands[i]   if i < len(bands)   else "",
            "sinr":   sinrs[i]   if i < len(sinrs)   else "",
        })
    return rows


# ═══════════════════════════════════════════════════════════════════════════
#                       Carrier Aggregation (PCC/SCC)
# ═══════════════════════════════════════════════════════════════════════════
PCC_FIELDS = ["pccType","pccBand","pccPci","pccArfcn","pccDlBandWidth",
              "pccUlBandWidth","pccDlModulation","pccUlModulation",
              "pccDlMimo","pccUlMimo","pccDlRB","pccUlRB","pccDlMCS",
              "pccUlMCS","rank","path_loss","pccPucchTxPower","pccCQI",
              "pccLTEDlTM","pccLTEUlTM"]


def get_ca(client: RouterClient) -> dict:
    """Returns {'pcc1', 'pcc2', 'sccs', 'count', 'lte_scc_n', 'nr_scc_n', 'ts'}.

    Returns ALL SCCs the firmware reports — callers filter by SCC_State
    ('actived'/'activated' = live, 'deactivated' = stale).  The router's
    own web UI reads SCC_State the same way, so we mirror that path.

    Earlier versions trimmed by header_info.{LTE,NR}_sccNumbers, but those
    counters can desync (return 0 even when SCCs are actively carrying
    traffic) — silently hiding live SCCs. SCC_State is reliable.

    Uses $multipost — same single-roundtrip path the router web UI uses."""
    pcc1_q = {f: f"X_FH_MobileNetwork.NetworkInfo.PCCInfo.{f}" for f in PCC_FIELDS}
    pcc2_q = {f: f"X_FH_MobileNetwork.NetworkInfo.PCCInfo2.{f}" for f in PCC_FIELDS}
    scc_q = {
        "url": "X_FH_MobileNetwork.NetworkInfo.SCCInfos.",
        "num": 8,
        "node": {
            "SCC_Type": "sccType", "SCC_State": "sccState",
            "SCC_Band": "sccBand", "SCC_Pci": "sccPci",
            "SCC_Arfcn": "sccArfcn", "SCC_DlBandWidth": "sccDlBandWidth",
            "SCC_UlBandWidth": "sccUlBandWidth", "SCC_DlMimo": "sccDlMimo",
            "SCC_UlMimo": "sccUlMimo", "SCC_DlModulation": "sccDlModulation",
            "SCC_UlModulation": "sccUlModulation", "SCC_DlRB": "sccDlRB",
            "SCC_UlRB": "sccUlRB", "SCC_DlMCS": "sccDlMCS",
            "SCC_UlMCS": "sccUlMCS",
            "SCC_PucchTxPower": "sccPucchTxPower",
            "SCC_LTEDlTM": "sccLTEDlTM", "SCC_LTEUlTM": "sccLTEUlTM",
        }
    }
    cnt_q = {"sccNumbers": "X_FH_MobileNetwork.NetworkInfo.SCCInfos.sccNumbers"}

    import time as _t
    bundle = client._post_multi([
        ("get_value_by_xmlnode",     pcc1_q),
        ("get_value_by_xmlnode",     pcc2_q),
        ("get_xml_childnode_value",  scc_q),
        ("get_value_by_xmlnode",     cnt_q),
    ], timeout=10) or {}

    pcc1     = bundle.get("data_1") or {}
    pcc2     = bundle.get("data_2") or {}
    scc_resp = bundle.get("data_3") or {}
    cnt_resp = bundle.get("data_4") or {}
    # Header counters kept for debugging only — caller no longer uses them
    # to filter, since they're unreliable.
    header   = client._post_api("get_header_info", timeout=5) or {}
    if not isinstance(header, dict): header = {}

    sccs_all = scc_resp.get("data", []) if isinstance(scc_resp, dict) else []
    lte_n = int(header.get("LTE_sccNumbers", 0) or 0)
    nr_n  = int(header.get("NR_sccNumbers",  0) or 0)

    return {
        "pcc1":      pcc1 if isinstance(pcc1, dict) else {},
        "pcc2":      pcc2 if isinstance(pcc2, dict) else {},
        "sccs":      sccs_all,          # ALL — filter downstream by SCC_State
        "sccs_raw":  sccs_all,
        "count":     int((cnt_resp or {}).get("sccNumbers", 0) or 0),
        "lte_scc_n": lte_n,
        "nr_scc_n":  nr_n,
        "ts":        _t.time(),
    }


# ═══════════════════════════════════════════════════════════════════════════
#                       SIM info + PIN
# ═══════════════════════════════════════════════════════════════════════════
SIM_FIELDS = {
    "SIMStatus":            "X_FH_MobileNetwork.SIM.1.SIMStatus",
    "IMEI":                 "X_FH_MobileNetwork.SIM.1.IMEI",
    "IMSI":                 "X_FH_MobileNetwork.SIM.1.IMSI",
    "ICCID":                "X_FH_MobileNetwork.SIM.1.ICCID",
    "NetworkMode":          "X_FH_MobileNetwork.SIM.1.NetworkMode",
    "CarrierName":          "X_FH_MobileNetwork.SIM.1.CarrierName",
    "SimPlmn":              "X_FH_MobileNetwork.SIM.1.plmn",
    "PhoneNumber":          "X_FH_MobileNetwork.SIM.1.PhoneNumber",
    "RegisterStatus":       "X_FH_MobileNetwork.SIM.1.RegisterStatus",
    "RoamingConnectStatus": "X_FH_MobileNetwork.SIM.1.RoamingConnectStatus",
}

PIN_FIELDS = {
    "PINLockEnable":     "X_FH_MobileNetwork.SIM.1.PINCodeManagement.PINLockEnable",
    "RemainingTimes":    "X_FH_MobileNetwork.SIM.1.PINCodeManagement.RemainingTimes",
    "RetCode":           "X_FH_MobileNetwork.SIM.1.PINCodeManagement.RetCode",
    "PINCodeEnable":     "X_FH_MobileNetwork.SIM.1.PINCodeManagement.PINCodeEnable",
    "PUKRemainingTimes": "X_FH_MobileNetwork.SIM.1.PINCodeManagement.PUKRemainingTimes",
}


def get_sim(client: RouterClient) -> dict:
    return client._post_api("get_value_by_xmlnode", SIM_FIELDS, timeout=8) or {}


def get_pin(client: RouterClient) -> dict:
    return client._post_api("get_value_by_xmlnode", PIN_FIELDS, timeout=6) or {}


def pin_unlock(client: RouterClient, pin_code: str) -> dict:
    """Unlock SIM with PIN code."""
    return client._post_api("set_pin_code_info", {
        "mode": "PINCodeEnable", "PINCode": pin_code
    }, timeout=10) or {}


def puk_unlock(client: RouterClient, puk_code: str, new_pin: str) -> dict:
    return client._post_api("set_pin_code_info", {
        "mode": "PUKCodeEnable",
        "PUKCode": puk_code,
        "PINCode": new_pin,
    }, timeout=10) or {}


# ═══════════════════════════════════════════════════════════════════════════
#                       Network Settings (mode, roaming, etc)
# ═══════════════════════════════════════════════════════════════════════════
NETWORK_SETTINGS_FIELDS = {
    "NetworkMode":         "X_FH_MobileNetwork.NetworkSettings.NetworkMode",
    "RoamingEnable":       "X_FH_MobileNetwork.NetworkSettings.RoamingEnable",
    "AirplaneEnable":      "X_FH_MobileNetwork.NetworkSettings.airplan_on",
    "SearchNetworkMode":   "X_FH_MobileNetwork.NetworkSettings.SearchNetworkMode",
    "VolteSwitch":         "X_FH_MobileNetwork.NetworkSettings.volte_switch",
    "ENDC":                "X_FH_MobileNetwork.NetworkSettings.ENDC",
    "CaEnable":            "X_FH_MobileNetwork.NetworkSettings.NetworkInfo.CaEnable",
    "LTECaEnable":         "X_FH_MobileNetwork.NetworkSettings.NetworkInfo.LTECaEnable",
    "AccessType":          "X_FH_MobileNetwork.NetworkSettings.AccessType",
    "PrivateNetwork":      "X_FH_MobileNetwork.NetworkSettings.PrivateNetwork",
    "AntennaOutterSwitch": "X_FH_MobileNetwork.NetworkSettings.AntennaOutterSwitch",
    "AntennaOutterType":   "X_FH_MobileNetwork.NetworkSettings.AntennaOutterSwitch_Type",
    "SMSDisable":          "X_FH_MobileNetwork.NetworkSettings.sms_disable",
    "SmsSwitch":           "X_FH_MobileNetwork.NetworkSettings.sms_switch",
}


def get_network_settings(client: RouterClient) -> dict:
    return client._post_api("get_value_by_xmlnode", NETWORK_SETTINGS_FIELDS, timeout=8) or {}


# ───── Advance page: unified read-all ─────
ADVANCE_FIELDS = {
    "NetworkMode":      "X_FH_MobileNetwork.NetworkSettings.NetworkMode",
    "ENDC":             "X_FH_MobileNetwork.NetworkSettings.ENDC",
    "AirplaneEnable":   "X_FH_MobileNetwork.NetworkSettings.airplan_on",
    "RoamingEnable":    "X_FH_MobileNetwork.NetworkSettings.RoamingEnable",
    "CaEnable":         "X_FH_MobileNetwork.NetworkInfo.CaEnable",
    "AntennaSwitch":    "X_FH_MobileNetwork.NetworkSettings.AntennaOutterSwitch",
    "AntennaType":      "X_FH_MobileNetwork.NetworkSettings.AntennaOutterSwitch_Type",
    "SmsDisable":       "X_FH_MobileNetwork.NetworkSettings.sms_disable",
    "SmsSwitch":        "X_FH_MobileNetwork.NetworkSettings.sms_switch",
    "VolteSwitch":      "X_FH_MobileNetwork.NetworkSettings.volte_switch",
    "DayTrafSwitch":    "X_FH_MobileNetwork.TrafficStats.TodayThresholdSwitch",
    "DayTrafBytes":     "X_FH_MobileNetwork.TrafficStats.TodayThresholdBytes",
    "MonthTrafSwitch":  "X_FH_MobileNetwork.TrafficStats.monthThresholdSwitch",
    "MonthTrafBytes":   "X_FH_MobileNetwork.TrafficStats.MonthThresholdBytes",
}


def get_advance(client: RouterClient) -> dict:
    return client._post_api("get_value_by_xmlnode", ADVANCE_FIELDS, timeout=8) or {}


# ───── Advance page: setters ─────
def set_airplane(client: RouterClient, on: bool) -> dict:
    return set_single_xmlnode(client,
        "X_FH_MobileNetwork.NetworkSettings.airplan_on", "1" if on else "0")


def set_roaming(client: RouterClient, on: bool) -> dict:
    return set_single_xmlnode(client,
        "X_FH_MobileNetwork.NetworkSettings.RoamingEnable", "1" if on else "0")


def set_carrier_aggregation(client: RouterClient, on: bool) -> dict:
    return set_single_xmlnode(client,
        "X_FH_MobileNetwork.NetworkInfo.CaEnable", "1" if on else "0")


def set_network_mode(client: RouterClient, code: str, endc: str | None = None) -> dict:
    """code: '0'=4G Only, '2'=5G Only, '3'=5G Pref, '4'=3G WCDMA.
    endc (5G Option): '1'=SA, '2'=NSA, '3'=SA+NSA. None to leave alone."""
    if endc is None:
        return set_single_xmlnode(client,
            "X_FH_MobileNetwork.NetworkSettings.NetworkMode", str(code))
    return set_xmlnode(client,
        {"NetworkMode": "X_FH_MobileNetwork.NetworkSettings.NetworkMode",
         "ENDC":        "X_FH_MobileNetwork.NetworkSettings.ENDC"},
        {"NetworkMode": str(code), "ENDC": str(endc)})


def set_volte(client: RouterClient, on: bool) -> dict:
    return set_single_xmlnode(client,
        "X_FH_MobileNetwork.NetworkSettings.volte_switch", "1" if on else "0")


def set_sms_enable(client: RouterClient, on: bool) -> dict:
    """SMS UI 'enabled' is the inverse of firmware sms_disable."""
    return set_single_xmlnode(client,
        "X_FH_MobileNetwork.NetworkSettings.sms_disable", "0" if on else "1")


def set_external_antenna(client: RouterClient, on: bool, band_code: str = "2") -> dict:
    """band_code: '1'=N77, '2'=N78 (firmware AntennaOutterSwitch_Type code)."""
    return set_xmlnode(client,
        {"sw":   "X_FH_MobileNetwork.NetworkSettings.AntennaOutterSwitch",
         "type": "X_FH_MobileNetwork.NetworkSettings.AntennaOutterSwitch_Type"},
        {"sw":   "1" if on else "0", "type": str(band_code)})


def set_traffic_threshold(client: RouterClient,
                           day_on: bool | None = None,
                           day_mb: int | None = None,
                           month_on: bool | None = None,
                           month_gb: int | None = None) -> dict:
    """Day limit accepts MB; month limit accepts GB.
    Firmware stores both as raw bytes."""
    url, val = {}, {}
    if day_on is not None:
        url["d_sw"] = "X_FH_MobileNetwork.TrafficStats.TodayThresholdSwitch"
        val["d_sw"] = "1" if day_on else "0"
    if day_mb is not None:
        url["d_b"] = "X_FH_MobileNetwork.TrafficStats.TodayThresholdBytes"
        val["d_b"] = str(int(day_mb) * 1048576)
    if month_on is not None:
        url["m_sw"] = "X_FH_MobileNetwork.TrafficStats.monthThresholdSwitch"
        val["m_sw"] = "1" if month_on else "0"
    if month_gb is not None:
        url["m_b"] = "X_FH_MobileNetwork.TrafficStats.MonthThresholdBytes"
        val["m_b"] = str(int(month_gb) * 1073741824)
    if not url: return {}
    return set_xmlnode(client, url, val)


def antenna_band_label(code) -> str:
    s = str(code or "")
    return {"1": "N77", "2": "N78"}.get(s, s)


# ───── UPnP ─────
def get_upnp(client: RouterClient) -> dict:
    return client._post_api("get_value_by_xmlnode", {
        "Enable": "X_FH_UPNP.Enable"}, timeout=5) or {}


def set_upnp(client: RouterClient, on: bool) -> dict:
    return set_single_xmlnode(client, "X_FH_UPNP.Enable", "1" if on else "0")


# ───── User account / password ─────
def change_admin_password(client: RouterClient, old: str, new: str) -> dict:
    return client._post_api("set_password_info",
        {"old_password": old, "new_password": new}, timeout=10) or {}


# ───── LAN setter (IPv4) ─────
def set_lan(client: RouterClient,
             ip: str | None = None, mask: str | None = None,
             dhcp_enable: bool | None = None,
             dhcp_min: str | None = None, dhcp_max: str | None = None,
             lease_sec: int | None = None) -> dict:
    url, val = {}, {}
    base = "LANDevice.1.LANHostConfigManagement"
    if ip is not None:
        url["ip"]   = f"{base}.IPInterface.1.IPInterfaceIPAddress";   val["ip"]   = ip
    if mask is not None:
        url["mask"] = f"{base}.IPInterface.1.IPInterfaceSubnetMask"; val["mask"] = mask
    if dhcp_enable is not None:
        url["dh"]   = f"{base}.DHCPServerEnable"; val["dh"] = "1" if dhcp_enable else "0"
    if dhcp_min is not None:
        url["dmin"] = f"{base}.MinAddress"; val["dmin"] = dhcp_min
    if dhcp_max is not None:
        url["dmax"] = f"{base}.MaxAddress"; val["dmax"] = dhcp_max
    if lease_sec is not None:
        url["lt"]   = f"{base}.DHCPLeaseTime"; val["lt"] = str(int(lease_sec))
    if not url: return {}
    return set_xmlnode(client, url, val)


# ───── TR-069 enable toggle ─────
def set_tr069_enable(client: RouterClient, on: bool) -> dict:
    return set_single_xmlnode(client, "ManagementServer.EnableCWMP",
                                "1" if on else "0")


def firewall_level_label(code) -> str:
    s = str(code or "")
    return {"0":"Off","1":"Low","2":"Medium","3":"High"}.get(s, s)


def set_xmlnode(client: RouterClient, key_to_path: dict, key_to_value: dict) -> dict:
    """Generic: set values via set_value_by_xmlnode."""
    return client._post_api("set_value_by_xmlnode",
                             {"url": key_to_path, "value": key_to_value},
                             timeout=15) or {}


def set_single_xmlnode(client: RouterClient, path: str, value: str) -> dict:
    return client._post_api("set_single_by_xmlnode",
                             {"url": path, "value": value}, timeout=10) or {}


# ═══════════════════════════════════════════════════════════════════════════
#                       Carrier Lock
# ═══════════════════════════════════════════════════════════════════════════
def get_carrier_lock(client: RouterClient) -> dict:
    return client._post_api("get_value_by_xmlnode", {
        "CarrierLockEnable": "X_FH_MobileNetwork.NetworkSettings.CarrierLockEnable",
        "CarrierSerialNum":  "X_FH_MobileNetwork.NetworkSettings.CarrierSerialNum",
    }, timeout=6) or {}


def set_carrier_lock(client: RouterClient, enable: bool, serial: str = "") -> dict:
    return set_xmlnode(client,
        {"CarrierLockEnable": "X_FH_MobileNetwork.NetworkSettings.CarrierLockEnable",
         "CarrierSerialNum":  "X_FH_MobileNetwork.NetworkSettings.CarrierSerialNum"},
        {"CarrierLockEnable": "1" if enable else "0",
         "CarrierSerialNum":  serial})


# ═══════════════════════════════════════════════════════════════════════════
#                       Cell Lock (LockCellList)
# ═══════════════════════════════════════════════════════════════════════════
def get_cell_lock(client: RouterClient) -> dict:
    """Returns {'enable': bool, 'cells': [{act, arfcn, pci, idx}], ...}."""
    state = client._post_api("get_value_by_xmlnode", {
        "LockEnable":      "X_FH_MobileNetwork.LockCellList.LockEnable",
        "LockBandEnable":  "X_FH_MobileNetwork.NetworkSettings.LockBandEnable",
        "AirplaneEnable":  "X_FH_MobileNetwork.NetworkSettings.airplan_on",
        "CarrierLockEnable":"X_FH_MobileNetwork.NetworkSettings.CarrierLockEnable",
        "IMSI":            "X_FH_MobileNetwork.SIM.1.IMSI",
    }, timeout=6) or {}
    cells_r = client._post_api("get_xml_childnode_value", {
        "url": "X_FH_MobileNetwork.LockCellList.LockCell.",
        "node": {"act": "act", "arfcn": "arfcn", "pci": "pci"}
    }, timeout=8) or {}
    return {
        "enable":           str(state.get("LockEnable")) == "1",
        "band_lock_enable": str(state.get("LockBandEnable")) == "1",
        "airplane":         str(state.get("AirplaneEnable")) == "1",
        "carrier_lock":     str(state.get("CarrierLockEnable")) == "1",
        "imsi":             state.get("IMSI", ""),
        "cells":            cells_r.get("data", []) if isinstance(cells_r, dict) else [],
    }


def set_cell_lock_enable(client: RouterClient, enable: bool) -> dict:
    return set_single_xmlnode(client, "X_FH_MobileNetwork.LockCellList.LockEnable",
                                "1" if enable else "0")


# act: "1" = 4G LTE, "2" = 5G NR (matches the firmware/Vue dropdown values)
def add_cell_lock_entry(client: RouterClient, act: str,
                          arfcn: int, pci: int) -> dict:
    """Append a (act, arfcn, pci) entry to the locked-cells list.
    Mirrors what the developer page does in addData()."""
    return client._post_api("add_set_xmlnode", {
        "url": "X_FH_MobileNetwork.LockCellList.LockCell.",
        "setNode": {
            "url":   {"act": "act", "arfcn": "arfcn", "pci": "pci"},
            "value": {"act": str(act),
                       "arfcn": int(arfcn),
                       "pci":   int(pci)},
        }
    }, timeout=10) or {}


def del_cell_lock_entry(client: RouterClient, child_node_idx: int) -> dict:
    """Remove a single cell from the lock list, by its child_node_idx."""
    return client._post_api("del_xmlnode", {
        "url":   "X_FH_MobileNetwork.LockCellList.LockCell.",
        "index": int(child_node_idx),
    }, timeout=10) or {}


# ═══════════════════════════════════════════════════════════════════════════
#                       Band Lock (frequencyLockSet)
# ═══════════════════════════════════════════════════════════════════════════
LTE_BANDS = ["1","3","5","7","8","20","28","32","38","40","41","42","43"]
NR_BANDS  = ["1","3","5","7","8","20","28","38","40","41","77","78"]


def get_band_lock(client: RouterClient) -> dict:
    r = client._post_api("get_value_by_xmlnode", {
        "LockBandEnable": "X_FH_MobileNetwork.NetworkSettings.LockBandEnable",
        "LTELockBAND":    "X_FH_MobileNetwork.NetworkSettings.LTELockBAND",
        "NRLockBAND":     "X_FH_MobileNetwork.NetworkSettings.NRLockBAND",
        "LockBandDisplay":"X_FH_MobileNetwork.NetworkSettings.LockBandDisplay",
        "AirplaneEnable": "X_FH_MobileNetwork.NetworkSettings.airplan_on",
        "CellLockEnable": "X_FH_MobileNetwork.LockCellList.LockEnable",
    }, timeout=6) or {}
    return {
        "enable":            str(r.get("LockBandEnable")) == "1",
        "lte_locked":        str(r.get("LTELockBAND") or ""),
        "nr_locked":         str(r.get("NRLockBAND") or ""),
        "display":           r.get("LockBandDisplay", ""),
        "airplane":          str(r.get("AirplaneEnable")) == "1",
        "cell_lock_enable":  str(r.get("CellLockEnable")) == "1",
    }


def set_band_lock(client: RouterClient, enable: bool,
                   lte_bands: list[str] | None = None,
                   nr_bands: list[str] | None = None) -> dict:
    """lte_bands / nr_bands are lists of band numbers as strings (without B/N)."""
    url = {"enable": "X_FH_MobileNetwork.NetworkSettings.LockBandEnable"}
    val = {"enable": "1" if enable else "0"}
    if lte_bands is not None:
        url["band4"] = "X_FH_MobileNetwork.NetworkSettings.LTELockBAND"
        val["band4"] = ",".join(lte_bands) if lte_bands else ""
    if nr_bands is not None:
        url["band5"] = "X_FH_MobileNetwork.NetworkSettings.NRLockBAND"
        val["band5"] = ",".join(nr_bands) if nr_bands else ""
    return set_xmlnode(client, url, val)


# ═══════════════════════════════════════════════════════════════════════════
#                       Network Detection
# ═══════════════════════════════════════════════════════════════════════════
NETWORK_DETECT_FIELDS = {
    "enable":           "X_FH_MobileNetwork.NetworkDetection.enable",
    "destination1":     "X_FH_MobileNetwork.NetworkDetection.destination1",
    "destination2":     "X_FH_MobileNetwork.NetworkDetection.destination2",
    "destination3":     "X_FH_MobileNetwork.NetworkDetection.destination3",
    "SwitchAutoEnable": "DeviceInfo.X_FH_SwitchAutoEnable",
}


def get_network_detection(client: RouterClient) -> dict:
    return client._post_api("get_value_by_xmlnode", NETWORK_DETECT_FIELDS, timeout=6) or {}


def set_network_detection(client: RouterClient, enable: bool,
                           dst1: str = "", dst2: str = "", dst3: str = "") -> dict:
    url = {k: NETWORK_DETECT_FIELDS[k] for k in ("enable","destination1","destination2","destination3")}
    val = {"enable": "1" if enable else "0",
            "destination1": dst1, "destination2": dst2, "destination3": dst3}
    return set_xmlnode(client, url, val)


# ═══════════════════════════════════════════════════════════════════════════
#                       Traffic
# ═══════════════════════════════════════════════════════════════════════════
TRAFFIC_FIELDS = {
    "TodayTotalTxBytes": "X_FH_MobileNetwork.TrafficStats.TodayTotalTxBytes",
    "TodayTotalRxBytes": "X_FH_MobileNetwork.TrafficStats.TodayTotalRxBytes",
    "TodayTotalBytes":   "X_FH_MobileNetwork.TrafficStats.TodayTotalBytes",
    "MonthTxBytes":      "X_FH_MobileNetwork.TrafficStats.MonthTxBytes",
    "MonthRxBytes":      "X_FH_MobileNetwork.TrafficStats.MonthRxBytes",
    "MonthTotalBytes":   "X_FH_MobileNetwork.TrafficStats.MonthTotalBytes",
}


def get_traffic(client: RouterClient) -> dict:
    return client._post_api("get_value_by_xmlnode", TRAFFIC_FIELDS, timeout=6) or {}


# ═══════════════════════════════════════════════════════════════════════════
#                       System / Device
# ═══════════════════════════════════════════════════════════════════════════
SYSTEM_FIELDS = {
    "SerialNumber":        "DeviceInfo.SerialNumber",
    "SoftwareVersion":     "DeviceInfo.SoftwareVersion",
    "HardwareVersion":     "DeviceInfo.HardwareVersion",
    "ModelName":           "DeviceInfo.ModelName",
    "Manufacturer":        "DeviceInfo.Manufacturer",
    "UpTime":              "DeviceInfo.UpTime",
    "CPUUsage":            "DeviceInfo.ProcessStatus.CPUUsage",
    "MemoryTotal":         "DeviceInfo.MemoryStatus.Total",
    "MemoryFree":          "DeviceInfo.MemoryStatus.Free",
    "MobileSoftVersion":   "DeviceInfo.MobileModuleSoftwareVersion",
    "Modem5GTemperature":  "X_FH_MobileNetwork.Temperature.Modem5GTemperature",
}


def get_system(client: RouterClient) -> dict:
    return client._post_api("get_value_by_xmlnode", SYSTEM_FIELDS, timeout=8) or {}


def get_uptime(client: RouterClient) -> str:
    r = client._post_api("get_cmd_result_web", {"key": "UPTIME"}, timeout=6)
    return str(r.get("result", "")) if isinstance(r, dict) else ""


def get_date(client: RouterClient) -> str:
    r = client._post_api("get_cmd_result_web", {"key": "DATE"}, timeout=6)
    return str(r.get("result", "")) if isinstance(r, dict) else ""


def reboot_device(client: RouterClient) -> dict:
    """Reboot the router."""
    return client._post_api("device_reboot", {}, timeout=15) or {}


def factory_reset(client: RouterClient) -> dict:
    return client._post_api("factory_reset", {}, timeout=15) or {}


# ═══════════════════════════════════════════════════════════════════════════
#                       LAN / WAN
# ═══════════════════════════════════════════════════════════════════════════
LAN_FIELDS = {
    "IPInterfaceIPAddress":  "LANDevice.1.LANHostConfigManagement.IPInterface.1.IPInterfaceIPAddress",
    "IPInterfaceSubnetMask": "LANDevice.1.LANHostConfigManagement.IPInterface.1.IPInterfaceSubnetMask",
    "DHCPServerEnable":      "LANDevice.1.LANHostConfigManagement.DHCPServerEnable",
    "MinAddress":            "LANDevice.1.LANHostConfigManagement.MinAddress",
    "MaxAddress":            "LANDevice.1.LANHostConfigManagement.MaxAddress",
    "DHCPLeaseTime":         "LANDevice.1.LANHostConfigManagement.DHCPLeaseTime",
    "DNSConfigType":         "LANDevice.1.LANHostConfigManagement.X_FH_DNSManualEnable",
    "DNSServers":            "LANDevice.1.LANHostConfigManagement.DNSServers",
}


def get_lan(client: RouterClient) -> dict:
    return client._post_api("get_value_by_xmlnode", LAN_FIELDS, timeout=8) or {}


def get_wan_ip_info(client: RouterClient) -> dict:
    return client._post_api("get_value_by_xmlnode", {
        "ExternalIPAddress": "WANDevice.1.WANConnectionDevice.1.WANIPConnection.1.ExternalIPAddress",
        "ConnectionStatus":  "WANDevice.1.WANConnectionDevice.1.WANIPConnection.1.ConnectionStatus",
        "DefaultGateway":    "WANDevice.1.WANConnectionDevice.1.WANIPConnection.1.DefaultGateway",
        "DNSServers":        "WANDevice.1.WANConnectionDevice.1.WANIPConnection.1.DNSServers",
        "Uptime":            "WANDevice.1.WANConnectionDevice.1.WANIPConnection.1.Uptime",
        "SubnetMask":        "WANDevice.1.WANConnectionDevice.1.WANIPConnection.1.SubnetMask",
    }, timeout=8) or {}


# ═══════════════════════════════════════════════════════════════════════════
#                       WiFi
# ═══════════════════════════════════════════════════════════════════════════
def get_wifi_ssids(client: RouterClient) -> list[dict]:
    r = client._post_api("get_xml_childnode_value", {
        "url": "WiFi.SSID.",
        "num": 16,
        "node": {
            "Enable":              "Enable",
            "SSID":                "SSID",
            "TotalBytesReceived":  "Stats.BytesReceived",
            "TotalBytesSent":      "Stats.BytesSent",
        }
    }, timeout=12)
    if isinstance(r, dict) and isinstance(r.get("data"), list):
        return r["data"]
    return []


def get_wifi_aps(client: RouterClient) -> list[dict]:
    r = client._post_api("get_xml_childnode_value", {
        "url": "WiFi.AccessPoint.",
        "num": 16,
        "node": {
            "Enable":         "Enable",
            "SSIDReference":  "SSIDReference",
            "ModeEnabled":    "Security.ModeEnabled",
            "EncryptionMode": "Security.EncryptionMode",
            "PreSharedKey":   "Security.PreSharedKey",
            "AssociatedDeviceCount": "AssociatedDeviceNumberOfEntries",
        }
    }, timeout=12)
    if isinstance(r, dict) and isinstance(r.get("data"), list):
        return r["data"]
    return []


def get_wifi_radios(client: RouterClient) -> list[dict]:
    r = client._post_api("get_xml_childnode_value", {
        "url": "WiFi.Radio.",
        "num": 4,
        "node": {
            "Enable":                "Enable",
            "Channel":               "Channel",
            "OperatingChannelBandwidth": "X_FH_ChannelWidth",
            "OperatingStandards":    "OperatingStandards",
            "TransmitPower":         "TransmitPower",
            "AutoChannelEnable":     "AutoChannelEnable",
            "RegulatoryDomain":      "RegulatoryDomain",
        }
    }, timeout=10)
    if isinstance(r, dict) and isinstance(r.get("data"), list):
        return r["data"]
    return []


def set_wifi_ssid(client: RouterClient, ssid_idx: int,
                   ssid_name: str, password: str | None = None,
                   enable: bool | None = None,
                   encryption_mode: str = "AES",
                   security_mode: str = "WPA2-Personal") -> dict:
    """Update SSID/password for given AccessPoint index (1..8)."""
    url, val = {}, {}
    url["SSID"] = f"WiFi.SSID.{ssid_idx}.SSID"
    val["SSID"] = ssid_name
    if enable is not None:
        url["Enable"] = f"WiFi.SSID.{ssid_idx}.Enable"
        val["Enable"] = "1" if enable else "0"
    if password is not None:
        url["PreSharedKey"] = f"WiFi.AccessPoint.{ssid_idx}.Security.PreSharedKey"
        val["PreSharedKey"] = password
        url["ModeEnabled"] = f"WiFi.AccessPoint.{ssid_idx}.Security.ModeEnabled"
        val["ModeEnabled"] = security_mode
        url["EncryptionMode"] = f"WiFi.AccessPoint.{ssid_idx}.Security.EncryptionMode"
        val["EncryptionMode"] = encryption_mode
    return set_xmlnode(client, url, val)


def set_wifi_radio_enable(client: RouterClient, radio_idx: int, enable: bool) -> dict:
    return set_single_xmlnode(client, f"WiFi.Radio.{radio_idx}.Enable",
                                "1" if enable else "0")


# ═══════════════════════════════════════════════════════════════════════════
#                       Devices (Hosts)
# ═══════════════════════════════════════════════════════════════════════════
def get_devices(client: RouterClient) -> list[dict]:
    r = client._post_api("get_xml_childnode_value", {
        "url": "LANDevice.1.Hosts.Host.",
        "num": 50,
        "node": {
            "hostname":  "HostName",
            "mac":       "MACAddress",
            "ip":        "IPAddress",
            "active":    "Active",
            "interface": "InterfaceType",
            "layer2":    "Layer2Interface",
        }
    }, timeout=15)
    if isinstance(r, dict) and isinstance(r.get("data"), list):
        return r["data"]
    return []


# ═══════════════════════════════════════════════════════════════════════════
#                       Firewall
# ═══════════════════════════════════════════════════════════════════════════
def get_firewall(client: RouterClient) -> dict:
    return client._post_api("get_value_by_xmlnode", {
        "Firewall_Level": "X_FH_FireWall.LEVEL",
        "DOSFEnable":     "X_FH_FireWall.DOSFEnable",
        "IPv6Enable":     "X_FH_FireWall.IPv6FirewallEnable",
        "NATType":        "X_FH_FireWall.X_FH_NATType",
    }, timeout=6) or {}


def set_firewall_level(client: RouterClient, level: int) -> dict:
    """level: 0=off, 1=low, 2=medium, 3=high"""
    return set_single_xmlnode(client, "X_FH_FireWall.LEVEL", str(level))


# ═══════════════════════════════════════════════════════════════════════════
#                       ALG
# ═══════════════════════════════════════════════════════════════════════════
ALG_FIELDS = {
    "L2TPEnable":  "DeviceInfo.X_FH_ALGAbility.L2TPEnable",
    "IPSECEnable": "DeviceInfo.X_FH_ALGAbility.IPSECEnable",
    "SIPEnable":   "DeviceInfo.X_FH_ALGAbility.SIPEnable",
    "FTPEnable":   "DeviceInfo.X_FH_ALGAbility.FTPEnable",
}


def get_alg(client: RouterClient) -> dict:
    return client._post_api("get_value_by_xmlnode", ALG_FIELDS, timeout=6) or {}


def set_alg(client: RouterClient, l2tp=None, ipsec=None, sip=None, ftp=None) -> dict:
    url, val = {}, {}
    for name, en, key in [("L2TPEnable", l2tp, "L2TPEnable"),
                           ("IPSECEnable", ipsec, "IPSECEnable"),
                           ("SIPEnable", sip, "SIPEnable"),
                           ("FTPEnable", ftp, "FTPEnable")]:
        if en is not None:
            url[name] = ALG_FIELDS[name]
            val[name] = "1" if en else "0"
    return set_xmlnode(client, url, val) if url else {}


# ═══════════════════════════════════════════════════════════════════════════
#                       Debug Info / Private Network
# ═══════════════════════════════════════════════════════════════════════════
def get_debug_state(client: RouterClient) -> dict:
    return client._post_api("get_value_by_xmlnode", {
        "debugInfoEnable": "X_FH_MobileNetwork.elt.output"
    }, timeout=5) or {}


def set_debug_state(client: RouterClient, enable: bool) -> dict:
    return set_single_xmlnode(client, "X_FH_MobileNetwork.elt.output",
                                "1" if enable else "0")


def get_private_network(client: RouterClient) -> dict:
    return client._post_api("get_value_by_xmlnode", {
        "PrivateNetwork": "X_FH_MobileNetwork.NetworkSettings.PrivateNetwork"
    }, timeout=5) or {}


def set_private_network(client: RouterClient, value: str) -> dict:
    return set_single_xmlnode(client,
        "X_FH_MobileNetwork.NetworkSettings.PrivateNetwork", value)


# ═══════════════════════════════════════════════════════════════════════════
#                       TR-069 / Antenna
# ═══════════════════════════════════════════════════════════════════════════
def get_tr069(client: RouterClient) -> dict:
    return client._post_api("get_value_by_xmlnode", {
        "EnableCWMP":             "ManagementServer.EnableCWMP",
        "URL":                    "ManagementServer.URL",
        "Username":               "ManagementServer.Username",
        "PeriodicInformEnable":   "ManagementServer.PeriodicInformEnable",
        "PeriodicInformInterval": "ManagementServer.PeriodicInformInterval",
        "ConnectionRequestUsername":"ManagementServer.ConnectionRequestUsername",
        "X_FH_ConnectionRequestPath":"ManagementServer.X_FH_ConnectionRequestPath",
        "X_FH_ConnectionRequestPort":"ManagementServer.X_FH_ConnectionRequestPort",
    }, timeout=8) or {}


def get_antenna(client: RouterClient) -> dict:
    return client._post_api("get_value_by_xmlnode", {
        "AntennaOutterSwitch": "X_FH_MobileNetwork.NetworkSettings.AntennaOutterSwitch",
        "AntennaOutterType":   "X_FH_MobileNetwork.NetworkSettings.AntennaOutterSwitch_Type",
    }, timeout=5) or {}


def set_antenna(client: RouterClient, switch: bool, ant_type: str = "Auto") -> dict:
    return set_xmlnode(client,
        {"AntennaOutterSwitch": "X_FH_MobileNetwork.NetworkSettings.AntennaOutterSwitch",
         "AntennaOutterType":   "X_FH_MobileNetwork.NetworkSettings.AntennaOutterSwitch_Type"},
        {"AntennaOutterSwitch": "1" if switch else "0",
         "AntennaOutterType":   ant_type})


# ═══════════════════════════════════════════════════════════════════════════
#                       Helpers / formatting
# ═══════════════════════════════════════════════════════════════════════════
def fmt_bytes(b) -> str:
    if b is None or b == "":
        return "—"
    try:
        n = float(b)
    except Exception:
        return str(b)
    for u in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or u == "TB":
            return f"{n:.0f} {u}" if u == "B" else f"{n:.2f} {u}"
        n /= 1024
    return f"{n:.2f} TB"


def fmt_uptime_seconds(s) -> str:
    if s is None or s == "":
        return "—"
    try:
        sec = int(float(s))
    except Exception:
        return str(s)
    d, sec = divmod(sec, 86400)
    h, sec = divmod(sec, 3600)
    m, sec = divmod(sec, 60)
    if d > 0:
        return f"{d}d {h:02d}h {m:02d}m"
    return f"{h:02d}h {m:02d}m {sec:02d}s"


def temp_celsius(raw):
    if raw is None or raw == "":
        return None
    try:
        v = float(raw)
        if v > 1000:
            return round(v / 1000.0, 1)
        return round(v, 1)
    except Exception:
        return None


def network_mode_label(code) -> str:
    """Match router web /mobileNetwork/networkSet dropdown values."""
    s = str(code or "")
    return {"0":"4G Only","2":"5G Only","3":"5G Pref",
            "4":"3G Only(WCDMA)"}.get(s, s)


def endc_label(code) -> str:
    """5G Option dropdown on /mobileNetwork/networkSet."""
    s = str(code or "")
    return {"1":"SA","2":"NSA","3":"SA+NSA"}.get(s, s)


def sim_status_label(code) -> str:
    s = str(code or "")
    return {"0":"Ready","1":"Not Ready","2":"PIN Required",
            "3":"PUK Required","4":"Locked"}.get(s, s)


def register_status_label(code) -> str:
    s = str(code or "")
    return {"0":"Registered","1":"Searching","2":"Denied",
            "3":"Unknown","4":"Roaming"}.get(s, s)


# ═══════════════════════════════════════════════════════════════════════════
#                       SCIENTIFIC SIGNAL QUALITY (color & label)
# ═══════════════════════════════════════════════════════════════════════════
# Standard 4G/5G signal thresholds (3GPP)
RSRP_THRESHOLDS = [(-80, "Excellent", "#10B981"),
                   (-90, "Good",      "#22C55E"),
                   (-100, "Fair",     "#F59E0B"),
                   (-110, "Poor",     "#F97316"),
                   (-200, "Very Poor","#EF4444")]
SINR_THRESHOLDS = [(20, "Excellent", "#10B981"),
                   (13, "Good",      "#22C55E"),
                   (0,  "Fair",      "#F59E0B"),
                   (-5, "Poor",      "#F97316"),
                   (-100,"Very Poor","#EF4444")]
RSRQ_THRESHOLDS = [(-10, "Excellent", "#10B981"),
                   (-15, "Good",      "#22C55E"),
                   (-17, "Fair",      "#F59E0B"),
                   (-19, "Poor",      "#F97316"),
                   (-100,"Very Poor", "#EF4444")]
RSSI_THRESHOLDS = [(-65, "Excellent", "#10B981"),
                   (-75, "Good",      "#22C55E"),
                   (-85, "Fair",      "#F59E0B"),
                   (-95, "Poor",      "#F97316"),
                   (-200,"Very Poor", "#EF4444")]


def _classify(value, thresholds, gte=True):
    try:
        v = float(value)
    except Exception:
        return ("—", "#6E89AC")
    for thr, label, color in thresholds:
        if (gte and v >= thr) or (not gte and v <= thr):
            return (label, color)
    return ("—", "#6E89AC")


def rsrp_quality(v): return _classify(v, RSRP_THRESHOLDS)
def sinr_quality(v): return _classify(v, SINR_THRESHOLDS)
def rsrq_quality(v): return _classify(v, RSRQ_THRESHOLDS)
def rssi_quality(v): return _classify(v, RSSI_THRESHOLDS)


def signal_bars(rsrp) -> int:
    try:
        v = float(rsrp)
    except Exception:
        return 0
    if v >= -80: return 5
    if v >= -90: return 4
    if v >= -100: return 3
    if v >= -110: return 2
    if v >= -120: return 1
    return 0


def safe_int(v, d=0):
    try: return int(float(v))
    except Exception: return d


def safe_float(v, d=0.0):
    try: return float(v)
    except Exception: return d
