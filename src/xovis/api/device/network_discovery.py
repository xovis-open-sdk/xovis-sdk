import asyncio
import os
import platform
import subprocess
from typing import Optional


class NetworkDiscoveryService:
    @staticmethod
    async def resolve_mac_to_ip(mac_address: str, known_proxy_ip: Optional[str] = None) -> Optional[str]:
        """
        DRY method to resolve a MAC to an IP using a cascading fallback strategy.
        """
        mac_address = mac_address.lower().replace("-", ":")

        # 1. Try Zero-Cost ARP
        ip = await NetworkDiscoveryService._check_arp_cache(mac_address)
        if ip:
            return ip

        # 2. Try Sensor-Assisted (if we have a proxy device)
        if known_proxy_ip:
            ip = await NetworkDiscoveryService._proxy_sensor_scan(mac_address, known_proxy_ip)
            if ip:
                return ip
            
        # 3. Future: Add active UDP/mDNS probe here as absolute last resort
        return None

    @staticmethod
    async def _check_arp_cache(mac_address: str) -> Optional[str]:
        loop = asyncio.get_running_loop()
        def _arp():
            try:
                cmd = ["arp", "-a"] if platform.system() == "Windows" else ["arp", "-n"]
                output = subprocess.check_output(cmd, text=True)
                for line in output.splitlines():
                    search_mac = mac_address.replace(":", "-") if platform.system() == "Windows" else mac_address
                    if search_mac in line.lower():
                        parts = line.split()
                        if parts:
                            return parts[0]
            except Exception:
                pass
            return None
        return await loop.run_in_executor(None, _arp)

    @staticmethod
    async def _proxy_sensor_scan(target_mac: str, proxy_ip: str) -> Optional[str]:
        from xovis.api.device.client import DeviceClient
        try:
            async with DeviceClient(proxy_ip, "admin", "pass") as client:
                nodes = await client.topology.localnetwork()
                for node in nodes:
                    if hasattr(node, 'host') and node.host.endswith(target_mac):
                        host_part = node.host.split("://")[-1].split(":")[0]
                        return host_part
        except Exception:
            pass
        return None

    @staticmethod
    async def scan_subnet(first_ip: str, count: int = 255, timeout: float = 1.5, max_concurrency: int = 100) -> list[dict]:
        """
        Actively scans a subnet for Xovis devices using a hybrid First-Responder strategy.

        Args:
            first_ip (str): The starting IP address for the scan.
            count (int, optional): The number of hosts to probe. Defaults to 255.
            timeout (float, optional): The connection timeout for each probe. Defaults to 1.5.
            max_concurrency (int, optional): The maximum number of concurrent requests. Defaults to 100.

        Returns:
            list[dict]: A list of dictionaries containing device information.
        """
        import ipaddress

        from xovis.api.core.auth import DeviceAuth
        from xovis.api.core.http import XovisHTTPClient

        start_ip_obj = ipaddress.IPv4Address(first_ip)
        sem = asyncio.Semaphore(max_concurrency)
        
        username = os.getenv("XOVIS_DEVICE_USERNAME", "admin")
        password = os.getenv("XOVIS_DEVICE_PASSWORD", "pass")
        auth = DeviceAuth(username, password)
        
        proxy_ip = None

        async def _find_proxy(ip: str) -> Optional[str]:
            nonlocal proxy_ip
            if proxy_ip:
                return None
            async with sem:
                if proxy_ip:
                    return None
                try:
                    async with XovisHTTPClient(base_url=f"http://{ip}", auth=auth) as hc:
                        await hc.get("/api/v5/device/info", timeout=timeout, max_retries=1)
                        if not proxy_ip:
                            proxy_ip = ip
                        return ip
                except Exception:
                    return None

        tasks = []
        for i in range(count):
            ip_str = str(start_ip_obj + i)
            tasks.append(asyncio.create_task(_find_proxy(ip_str)))

        # 1. Sweep to find just ONE proxy
        for task in asyncio.as_completed(tasks):
            found_ip = await task
            if found_ip:
                proxy_ip = found_ip
                break

        # Cancel remaining tasks to prevent socket exhaustion and device overload
        for t in tasks:
            if not t.done():
                t.cancel()
        
        # Yield to let cancellations process
        await asyncio.sleep(0)

        if not proxy_ip:
            return []

        # 2. Handoff to the Proxy for the rich L2 payload
        try:
            async with XovisHTTPClient(base_url=f"http://{proxy_ip}", auth=auth) as hc:
                resp = await hc.get("/api/v5/discover/localnetwork", timeout=5.0, max_retries=1)
                net_data = resp.json()
                
                devices = []
                for sensor in net_data.get("sensors", []):
                    devices.append({
                        "mac_address": sensor.get("mac", "00:00:00:00:00:00"),
                        "ip_address": sensor.get("ip", ""),
                        "name": sensor.get("name", "New Local Sensor"),
                        "group": sensor.get("group", "LAN"),
                        "type": sensor.get("model", "Unknown"),
                        "fw_version": sensor.get("fw_version", "Unknown")
                    })
                return devices
        except Exception:
            return []
