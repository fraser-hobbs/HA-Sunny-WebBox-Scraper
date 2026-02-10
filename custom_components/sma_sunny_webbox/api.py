"""API client for SMA Sunny WebBox with persistent session management."""
import logging
import requests
import xml.etree.ElementTree as ET
from typing import Optional, Dict, Any
import time
from datetime import datetime, timedelta

_LOGGER = logging.getLogger(__name__)


class SMAWebBoxAPI:
    """Handle SMA WebBox authentication and data fetching with persistent sessions."""

    def __init__(self, host: str, password: str, user_level: str = "installer"):
        """Initialize the API client."""
        self.host = host
        self.password = password
        self.user_level = user_level.capitalize()
        self.session = requests.Session()
        self._logged_in = False
        self._last_login_time = None
        self._session_timeout = timedelta(minutes=30)  # Re-login after 30 min of inactivity

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

    def _is_session_valid(self) -> bool:
        """Check if current session is still valid."""
        if not self._logged_in:
            return False

        if self._last_login_time is None:
            return False

        # Check if session has timed out
        if datetime.now() - self._last_login_time > self._session_timeout:
            _LOGGER.info("Session timeout detected, will re-authenticate")
            self._logged_in = False
            return False

        return True

    async def async_login(self) -> bool:
        """Login to WebBox (async wrapper)."""
        import asyncio
        return await asyncio.get_event_loop().run_in_executor(None, self.login)

    def login(self) -> bool:
        """Login to WebBox and establish persistent session."""
        try:
            _LOGGER.info("Authenticating with SMA WebBox at %s", self.host)

            payload = {
                "Language": "LangEN",
                "Userlevels": self.user_level,
                "password": self.password,
            }

            response = self.session.post(self.login_url, data=payload, timeout=10)
            response.raise_for_status()

            if "invalidPassword" in response.text:
                _LOGGER.error("Invalid password for SMA WebBox")
                self._logged_in = False
                return False

            self._logged_in = True
            self._last_login_time = datetime.now()
            _LOGGER.info("Successfully authenticated with SMA WebBox")

            # Small delay to let session stabilize
            time.sleep(1)
            return True

        except requests.exceptions.RequestException as e:
            _LOGGER.error("Login error: %s", e)
            self._logged_in = False
            return False

    async def async_get_data(self, device_key: str) -> Optional[Dict[str, Any]]:
        """Fetch and parse data from WebBox (async wrapper)."""
        import asyncio
        return await asyncio.get_event_loop().run_in_executor(
            None, self.get_data, device_key
        )

    def get_data(self, device_key: str) -> Optional[Dict[str, Any]]:
        """Fetch and parse data from WebBox with automatic re-authentication."""
        # Check if we need to login or re-login
        if not self._is_session_valid():
            _LOGGER.debug("Session invalid, attempting to authenticate")
            if not self.login():
                _LOGGER.error("Failed to authenticate with WebBox")
                return None

        try:
            # Establish session context (only needed after fresh login)
            if datetime.now() - self._last_login_time < timedelta(seconds=5):
                _LOGGER.debug("Establishing session context")
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

            # Update last activity time
            self._last_login_time = datetime.now()

            # Merge both datasets
            if dc_data or overview_data:
                return {**dc_data, **overview_data}

            _LOGGER.warning("No data received from WebBox")
            return None

        except Exception as e:
            _LOGGER.error("Error fetching data: %s", e)
            # Mark session as invalid on error
            self._logged_in = False
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

            # Check if session expired
            if b'<Page id="Login"' in response.content:
                _LOGGER.warning("Session expired during process data fetch")
                self._logged_in = False
                return {}

            response.raise_for_status()
            return self._parse_process_data(response.content)

        except requests.exceptions.RequestException as e:
            _LOGGER.error("Error fetching process data: %s", e)
            return {}

    def _fetch_overview_data(self, device_key: str) -> Dict[str, Any]:
        """Fetch AC power and energy from overview page."""
        try:
            params = {
                '__deviceKey': device_key,
                '__selected': 'hp.PlantOverview__',
            }

            response = self.session.get(self.overview_url, params=params, timeout=10)

            # Check if session expired
            if 'Login' in response.text and 'UserLevels' in response.text:
                _LOGGER.warning("Session expired during overview fetch")
                self._logged_in = False
                return {}

            response.raise_for_status()
            return self._parse_overview_data(response.content)

        except requests.exceptions.RequestException as e:
            _LOGGER.error("Error fetching overview data: %s", e)
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
            _LOGGER.error("XML parsing error (process data): %s", e)
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

                # Daily Energy (Metering.DyWhOut) - in Wh, convert to kWh
                elif tag_name == 'Metering.DyWhOut':
                    value_elem = item.find('Value')
                    if value_elem is not None and value_elem.text:
                        data['daily_energy'] = float(value_elem.text) / 1000

                # Total Energy (Metering.TotWhOut) - in MWh, convert to kWh
                elif tag_name == 'Metering.TotWhOut':
                    value_elem = item.find('Value')
                    if value_elem is not None and value_elem.text:
                        mwh_value = float(value_elem.text.replace(',', ''))
                        data['total_energy'] = mwh_value * 1000

                # System Condition
                elif tag_name == 'Operation.Health':
                    value_elem = item.find('Value')
                    if value_elem is not None and value_elem.text:
                        data['condition'] = value_elem.text

            return data

        except ET.ParseError as e:
            _LOGGER.error("XML parsing error (overview data): %s", e)
            return {}

    async def async_test_connection(self) -> bool:
        """Test if we can connect and authenticate."""
        return await self.async_login()

    def close(self):
        """Close the session."""
        try:
            self.session.close()
            _LOGGER.debug("Session closed")
        except Exception as e:
            _LOGGER.debug("Error closing session: %s", e)
