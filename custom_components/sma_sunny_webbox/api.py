"""API client for SMA Sunny WebBox."""
import logging
import requests
import xml.etree.ElementTree as ET
from typing import Optional, Dict, Any
import time

_LOGGER = logging.getLogger(__name__)


class SMAWebBoxAPI:
    """Handle SMA WebBox authentication and data fetching."""

    def __init__(self, host: str, password: str, user_level: str = "installer"):
        """Initialize the API client."""
        self.host = host
        self.password = password
        self.user_level = user_level.capitalize()
        self.session = requests.Session()
        self._logged_in = False

        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:147.0) Gecko/20100101 Firefox/147.0',
            'Accept': '*/*',
            'Accept-Language': 'en-GB,en;q=0.9',
            'DNT': '1',
            'Connection': 'keep-alive'
        })

        self.login_url = f"http://{host}/culture/login"
        self.overview_url = f"http://{host}/culture/DeviceOverview.dml"
        self.process_data_url = f"http://{host}/culture/ProcessDataList.pdml"

    async def async_login(self) -> bool:
        """Login to WebBox (async wrapper)."""
        import asyncio
        return await asyncio.get_event_loop().run_in_executor(None, self.login)

    def login(self) -> bool:
        """Login to WebBox."""
        try:
            payload = {
                "Language": "LangEN",
                "Userlevels": self.user_level,
                "password": self.password,
            }

            response = self.session.post(self.login_url, data=payload, timeout=10)
            response.raise_for_status()

            if "invalidPassword" in response.text:
                _LOGGER.error("Invalid password for SMA WebBox")
                return False

            self._logged_in = True
            _LOGGER.info("Successfully logged into SMA WebBox")

            # Establish session context
            time.sleep(1)
            return True

        except Exception as e:
            _LOGGER.error(f"Login error: {e}")
            return False

    async def async_get_data(self, device_key: str) -> Optional[Dict[str, Any]]:
        """Fetch and parse data from WebBox (async wrapper)."""
        import asyncio
        return await asyncio.get_event_loop().run_in_executor(
            None, self.get_data, device_key
        )

    def get_data(self, device_key: str) -> Optional[Dict[str, Any]]:
        """Fetch and parse data from WebBox."""
        if not self._logged_in:
            if not self.login():
                return None

        try:
            # Establish session context
            params = {
                "__deviceKey": device_key,
                "__newTab": "hp.processDataOverview",
                "__selected": "hp.processDataOverview_"
            }
            self.session.get(self.overview_url, params=params, timeout=10)
            time.sleep(1)

            # Fetch DC process data
            dc_data = self._fetch_process_data(device_key)

            # Fetch AC/energy overview data
            time.sleep(0.5)
            overview_data = self._fetch_overview_data(device_key)

            # Merge both datasets
            if dc_data or overview_data:
                return {**dc_data, **overview_data}

            return None

        except Exception as e:
            _LOGGER.error(f"Error fetching data: {e}")
            return None

    def _fetch_process_data(self, device_key: str) -> Dict[str, Any]:
        """Fetch DC measurements from ProcessDataList.pdml."""
        try:
            timestamp = int(time.time() * 1000)

            params = {
                '__pageName': 'DeviceOverview',
                '__deviceKey': device_key,
                '__newTab': '',
                '__selected': 'hp.processDataOverview_',
                '__selectedCategory': '5',
                '__dd': str(timestamp)
            }

            self.session.headers.update({
                'Referer': f'http://{self.host}/culture/DeviceOverview.dml?__newTab=&__deviceKey={device_key}&__selected=hp.processDataOverview_&__selectedCategory=5',
                'X-Requested-With': 'XMLHttpRequest'
            })

            response = self.session.get(self.process_data_url, params=params, timeout=10)

            if b'<Page id="Login"' in response.content:
                _LOGGER.warning("Session expired during process data fetch")
                self._logged_in = False
                return {}

            response.raise_for_status()
            return self._parse_process_data(response.content)

        except Exception as e:
            _LOGGER.error(f"Error fetching process data: {e}")
            return {}

    def _fetch_overview_data(self, device_key: str) -> Dict[str, Any]:
        """Fetch AC power and energy from overview page."""
        try:
            params = {
                '__deviceKey': device_key,
                '__selected': 'hp.PlantOverview__',
            }

            response = self.session.get(self.overview_url, params=params, timeout=10)

            if 'Login' in response.text and 'UserLevels' in response.text:
                _LOGGER.warning("Session expired during overview fetch")
                self._logged_in = False
                return {}

            response.raise_for_status()
            return self._parse_overview_data(response.content)

        except Exception as e:
            _LOGGER.error(f"Error fetching overview data: {e}")
            return {}

    def _parse_process_data(self, xml_data: bytes) -> Dict[str, Any]:
        """Parse DC measurements from ProcessDataList.pdml."""
        try:
            root = ET.fromstring(xml_data)
            data = {}

            for item in root.findall('.//XmlItem'):
                tag_name = item.get('tagName', '')

                # DC Current (DcMs.Amp) - value in mA, convert to A
                if tag_name == 'DcMs.Amp':
                    avg = item.find(".//XmlItem[@tagName='Average']/Value")
                    if avg is not None and avg.text:
                        data['dc_current'] = float(avg.text) / 1000

                # DC Voltage (DcMs.Vol)
                elif tag_name == 'DcMs.Vol':
                    avg = item.find(".//XmlItem[@tagName='Average']/Value")
                    if avg is not None and avg.text:
                        data['dc_voltage'] = float(avg.text.replace(',', '.'))

                # DC Power (DcMs.Watt)
                elif tag_name == 'DcMs.Watt':
                    sum_val = item.find(".//XmlItem[@tagName='Sum']/Value")
                    if sum_val is not None and sum_val.text:
                        data['dc_power'] = int(sum_val.text)

                # Insulation Resistance
                elif tag_name == 'Isolation.LeakRis':
                    avg = item.find(".//XmlItem[@tagName='Average']/Value")
                    if avg is not None and avg.text:
                        val_str = avg.text.replace('.', '').replace(',', '.')
                        data['insulation_resistance'] = float(val_str)

            return data

        except ET.ParseError as e:
            _LOGGER.error(f"XML parsing error (process data): {e}")
            return {}

    def _parse_overview_data(self, xml_data: bytes) -> Dict[str, Any]:
        """Parse AC power and energy from overview page."""
        try:
            root = ET.fromstring(xml_data)
            data = {}

            for item in root.findall('.//XmlItem'):
                tag_name = item.get('tagName', '')

                # AC Power (GridMs.TotW)
                if tag_name == 'GridMs.TotW':
                    sum_val = item.find(".//XmlItem[@tagName='Sum']/Value")
                    if sum_val is not None and sum_val.text:
                        data['ac_power'] = int(sum_val.text)

                # Daily Energy (Metering.DyWhOut) - in Wh
                elif tag_name == 'Metering.DyWhOut':
                    value_elem = item.find('Value')
                    if value_elem is not None and value_elem.text:
                        # Convert Wh to kWh for Energy Dashboard
                        data['daily_energy'] = float(value_elem.text) / 1000

                # Total Energy (Metering.TotWhOut) - in MWh, convert to kWh
                elif tag_name == 'Metering.TotWhOut':
                    value_elem = item.find('Value')
                    if value_elem is not None and value_elem.text:
                        # Value is in MWh (e.g., "35,820"), convert to kWh
                        mwh_value = float(value_elem.text.replace(',', ''))
                        data['total_energy'] = mwh_value * 1000  # MWh to kWh

                # System Condition
                elif tag_name == 'Operation.Health':
                    value_elem = item.find('Value')
                    if value_elem is not None and value_elem.text:
                        data['condition'] = value_elem.text

            return data

        except ET.ParseError as e:
            _LOGGER.error(f"XML parsing error (overview data): {e}")
            return {}

    async def async_test_connection(self) -> bool:
        """Test if we can connect and authenticate."""
        return await self.async_login()
