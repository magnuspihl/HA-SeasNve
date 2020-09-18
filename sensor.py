#import logging
import requests, json, datetime

#import voluptuous as vol

#import homeassistant.helpers.config_validation as cv
#from homeassistant.components.sensor import PLATFORM_SCHEMA
#from homeassistant.const import CONF_NAME, ATTR_ATTRIBUTION
from homeassistant.helpers.entity import Entity

#_LOGGER = logging.getLogger(__name__)

ATTR_DAYS = 'days'
ATTR_CURRENT_MONTH = 'currentMonth'
ATTR_LAST_MONTH = 'lastMonth'
ATTR_CURRENT_YEAR = 'currentYear'
ATTR_LAST_YEAR = 'lastYear'
ATTR_TODAY_LAST_YEAR = 'todayLastYear'
ATTR_TOTAL = 'total'

#ATTRIBUTION = 'Data provided by msn-api.seas-nve.dk'

CONF_USERNAME = "username"
CONF_PASSWORD = "password"

DEFAULT_NAME = "Energy This Month"
ICON = "mdi:counter"

#SCAN_INTERVAL = timedelta(minutes=1)
"""
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
	{
		vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
		vol.Required(CONF_USERNAME): cv.string,
		vol.Required(CONF_PASSWORD): cv.string,
	}
)
"""
def setup_platform(hass, config, add_entities, discovery_info=None):
	"""Set up the SEAS-NVE sensor."""
	name = DEFAULT_NAME# config[CONF_NAME]
	username = config[CONF_USERNAME]
	password = config[CONF_PASSWORD]
	
	data = SeasNveData(username, password)
	add_entities([SeasNveSensor(data, username, password, name)], True)

class SeasNveSensor(Entity):
	"""Implementation of SEAS-NVE sensor"""
	
	def __init__(self, data, username, password, name):
		self.data = data
		self._name = name
		self._username = username
		self._password = password
		self._info = self._state = None

	@property
	def name(self):
		"""Returns the name of the sensor."""
		return self._name
	
	@property
	def state(self):
		"""Returns the state of the sensor."""
		return self._state
	
	@property
	def device_state_attributes(self):
		"""Returns the state attributes."""
		if not self._info:
			return {}#ATTR_ATTRIBUTION: ATTRIBUTION}
		
		return {
			#ATTR_ATTRIBUTION: ATTRIBUTION,
			ATTR_DAYS: self._info[ATTR_DAYS],
			ATTR_CURRENT_MONTH: self._info[ATTR_CURRENT_MONTH],
			ATTR_LAST_MONTH: self._info[ATTR_LAST_MONTH],
			ATTR_CURRENT_YEAR: self._info[ATTR_CURRENT_YEAR],
			ATTR_LAST_YEAR: self._info[ATTR_LAST_YEAR],
			ATTR_TODAY_LAST_YEAR: self._info[ATTR_TODAY_LAST_YEAR],
			ATTR_TOTAL: self._info[ATTR_TOTAL]
		}
	
	@property
	def unit_of_measurement(self):
		"""Return the unit this state is expressed in."""
		return "kWh"
	
	@property
	def icon(self):
		"""Icon to use in the frontend, if any."""
		return ICON
	
	def update(self):
		"""Get the latest data from the API and update the states."""
		self.data.update()
		self._info = self.data.info
		
		if not self._info:
			self._state = None
		else:
			try:
				self._state = self._info[ATTR_CURRENT_MONTH]
			except TypeError:
				pass


class SeasNveData:
	def __init__(self, username, password):
		"""Initialize the data object."""
		self.username = username
		self.password = password
	
	def getConsumptionValue(self, data, start = 0, stop = 1):
		mp = data['meteringPoints'][0]
		sum = 0
		for i in range(start, min(stop, len(mp['values']))):
			sum += mp['values'][i]['value']
		return sum
	def selectDateConsumption(self, data, start = 0, stop = 1):
		mp = data['meteringPoints'][0]
		result = []
		for i in range(start, min(stop, len(mp['values']))):
			result.append({'date': mp['values'][i]['start'], 'value': mp['values'][i]['value']})
		return result

	def firstDayOfMonth(self, d):
		return d.replace(day=1).strftime('%Y-%m-%d');
	def lastDayOfMonth(self, d):
		return (d.replace(month=d.month+1, day=1)-datetime.timedelta(days=1)).strftime('%Y-%m-%d');

	def update(self):
		api = SeasNveApi(self.username, self.password)
		now = datetime.datetime.now()
		lastMonth = now.replace(month=now.month-1)
		lastYear = now.replace(year=now.year-1)
		self.info = {
			ATTR_DAYS: self.selectDateConsumption(api.consumption('Day', now.replace(day=now.day-7).strftime('%Y-%m-%d'), now.strftime('%Y-%m-%d')), 0, 99),
			ATTR_CURRENT_MONTH: self.getConsumptionValue(api.consumption('Month', self.firstDayOfMonth(now), self.lastDayOfMonth(now))),
			ATTR_LAST_MONTH: self.getConsumptionValue(api.consumption('Month', self.firstDayOfMonth(lastMonth), self.lastDayOfMonth(lastMonth))),
			ATTR_CURRENT_YEAR: self.getConsumptionValue(api.consumption('Year', now.strftime('%Y')+'-01-01', now.strftime('%Y')+'-12-31')),
			ATTR_LAST_YEAR: self.getConsumptionValue(api.consumption('Year', lastYear.strftime('%Y')+'-01-01', lastYear.strftime('%Y')+'-12-31')),
			ATTR_TODAY_LAST_YEAR: self.getConsumptionValue(api.consumption('Year', lastYear.strftime('%Y')+'-01-01', lastYear.strftime('%Y-%m-%d')), 0, 99),
			ATTR_TOTAL: self.getConsumptionValue(api.consumption('Year', now.replace(year=now.year-9).strftime('%Y')+'-01-01', now.strftime('%Y-%m-%d')), 0, 99),
		}

base_url = 'https://msn-api.seas-nve.dk/api/v1.0'
class SeasNveApi:
	def __init__(self, EMAIL, PASSWORD):
		global authheader
		try:
			resp = requests.post(base_url + '/auth', json={'username': EMAIL, 'password': PASSWORD})
			Bearer = 'Bearer '+ resp.json()['accessToken']
			authheader = {'Authorization': Bearer}
		except Exception as e:
			error = 1
			print(e)

	def getMeteringPoint(self, type):
		m = requests.get(base_url+'/profile/metering/', headers=authheader)
		data = m.json()[0]	# TODO: Search meteringpoints for meterType == type
		meteringPoint = data['meteringPoint']
		return meteringPoint

	def consumption(self,aggr,start,end):
		# Valid aggr is Hour, Day, Month, Year
		mpn = self.getMeteringPoint('Power')
		m = requests.get(base_url+'/profile/consumption/?meteringpoints='+mpn+'&start='+start+'&end='+end+'&aggr='+aggr+'', headers=authheader)
		data = m.json()
		return data